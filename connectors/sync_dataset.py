#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_dataset.py — Fase 4 de "Perú en Datos": sincronización GENÉRICA de
UN dataset ya descubierto por discovery.py (Fase 3).

QUÉ RESUELVE
------------
Hasta ahora, cada fuente conectada (`mef.py`, `contraloria.py`,
`inei_renamu.py`) es un archivo escrito a mano: cada uno repite el mismo
patrón de 3 niveles (Data API → URL en vivo → URL fija) pero con el
dataset, las columnas y la lógica de agregación hardcodeadas adentro del
propio archivo. Eso funciona bien para 3-4 fuentes elegidas a dedo, pero
no escala a los ~500 datasets que `discovery.py` encuentra — no se puede
escribir un `.py` nuevo por cada uno.

Este módulo generaliza el patrón de 3 niveles (ya probado y funcionando
en los conectores existentes, reutilizando las mismas funciones de
`common.py` sin cambiarlas) para que reciba CUALQUIER `dataset_id` del
catálogo y lo sincronice sin necesitar código nuevo.

QUÉ NO HACE (a propósito, por diseño)
--------------------------------------
NO intenta entender el SIGNIFICADO de las columnas de cada dataset (a
diferencia de `mef.py`, que sabe que existen columnas
`MONTO_DEVENGADO_ENERO..DICIEMBRE`, o de `contraloria.py`, que busca una
columna de región). Con ~500 datasets de estructuras completamente
distintas, adivinar el significado de cada columna sería inventar —
justo lo que este proyecto evita en todas sus reglas. En su lugar, este
módulo hace lo que SÍ se puede afirmar con certeza para cualquier CSV:
cuántas filas tiene, qué columnas reales trae (`columnas_detectadas`,
igual que los demás conectores) y guarda una MUESTRA de las primeras
filas tal cual vinieron — la interpretación semántica (qué columna es
"monto", cuál es "región") queda para una fase posterior (Analytics
Engine, Fase 7 del plan), dataset por dataset, cuando haga falta.

FORMATOS SOPORTADOS
--------------------
Por ahora, CSV (con autodetección de separador y de codificación
UTF-8/cp1252, reutilizando `sniff_csv_reader`/`smart_decode` de
`common.py` — el mismo mecanismo que ya usan los otros conectores). Un
recurso en otro formato (xlsx, pdf, json, shapefile, etc.) queda
reportado con `"estado": "formato_no_soportado"` y su `formato` real —
nunca se intenta parsear a la fuerza ni se inventa contenido.

MODELO DE DATOS DE SALIDA (sección 3 del plan de Fase 1)
-----------------------------------------------------------
data/sources/<dataset_id>/
  latest.json        - resultado de la sincronización más reciente
  raw/<fecha>.json    - copia de ESE MISMO resultado, con nombre de
                        archivo por fecha — nunca se sobreescribe, así
                        se acumula un historial de snapshots crudos
  history.jsonl       - una línea por corrida (fecha, estado, filas,
                        nivel_usado) — la serie de tiempo barata que
                        alimenta gráficos de tendencia sin base de datos

USO
---
  # Un solo dataset, por su dataset_id (tal como aparece en catalog.json)
  python3 connectors/sync_dataset.py <dataset_id>

  # Todos los datasets de una categoría del catálogo (utilidad simple
  # para probar hoy — el workflow programado que orquesta esto de forma
  # robusta, con reintentos y límite de tiempo propio, es la Fase 5)
  python3 connectors/sync_dataset.py --todos-de-categoria "Economía y Finanzas" --limit 5
"""

import argparse
import io
import json
import os
import sys
import time
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(__file__))
from common import (
    datastore_search_all,
    has_data_api,
    http_get,
    package_show,
    smart_decode,
    sniff_csv_reader,
    write_summary,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")

FORMATOS_CSV_RECONOCIDOS = {"csv", "text/csv", "csv " , ""}  # "" cubre datasets donde el portal no especifica formato


def cargar_catalogo(catalog_path):
    with open(catalog_path, encoding="utf-8") as f:
        return json.load(f)


def buscar_en_catalogo(catalogo, dataset_id):
    for ds in catalogo.get("datasets", []):
        if ds["dataset_id"] == dataset_id:
            return ds
    return None


def elegir_recurso(entrada_catalogo, resource_id=None):
    """Elige qué recurso del dataset sincronizar. Si se pide un
    resource_id específico, lo busca exacto (y falla explícitamente si no
    existe — nunca sincroniza "cualquiera" en su lugar). Si no, prioriza
    un recurso con Data API ya confirmada por discovery.py; si ninguno la
    tiene, el primero que tenga URL de descarga."""
    resources = entrada_catalogo.get("resources") or []
    if resource_id:
        for r in resources:
            if r.get("resource_id") == resource_id:
                return r
        raise RuntimeError(f"resource_id {resource_id!r} no existe en el catálogo para este dataset.")
    con_data_api = [r for r in resources if r.get("tiene_data_api") is True]
    if con_data_api:
        return con_data_api[0]
    con_url = [r for r in resources if r.get("resource_url")]
    if con_url:
        return con_url[0]
    return resources[0] if resources else None


def resolver_url_en_vivo(dataset_id, resource_id, url_respaldo):
    """Nivel 2 del patrón de 3 niveles (ver common.py): refresca la URL de
    descarga llamando a package_show EN VIVO — el catálogo puede tener
    horas o días de antigüedad, y `package_show` es la fuente de verdad
    en el momento de la corrida (mismo razonamiento que ya usan
    mef.py/contraloria.py). Nunca lanza: si falla, cae a `url_respaldo`
    (la URL que ya traía el catálogo) sin frenar la sincronización."""
    try:
        pkg = package_show(dataset_id)
        for r in (pkg.get("resources") or []):
            if r.get("id") == resource_id:
                return (r.get("url") or url_respaldo), "url_en_vivo"
    except Exception as exc:
        print(f"    package_show en vivo falló ({exc}) — se usa la URL del catálogo.", file=sys.stderr)
    return url_respaldo, "url_catalogo"


def parsear_csv_generico(raw_bytes, max_filas_muestra=20):
    """Parsea CUALQUIER CSV sin asumir columnas — solo cuenta filas y
    guarda una muestra. Ver docstring del módulo sobre por qué no se
    interpreta el significado de las columnas aquí."""
    texto = smart_decode(raw_bytes)
    reader = sniff_csv_reader(io.StringIO(texto))
    fieldnames = reader.fieldnames or []
    filas = list(reader)
    return {
        "columnas_detectadas": fieldnames,
        "filas_leidas": len(filas),
        "muestra": filas[:max_filas_muestra],
    }


def descargar_y_parsear(url, formato, max_mb=None):
    formato_norm = (formato or "").strip().lower()
    if formato_norm not in FORMATOS_CSV_RECONOCIDOS:
        raise FormatoNoSoportado(formato or "(sin especificar)")
    max_bytes = int(max_mb * 1024 * 1024) if max_mb else None
    resp = http_get(url, timeout=120, max_retries=2)
    raw = resp.read(max_bytes) if max_bytes else resp.read()
    resultado = parsear_csv_generico(raw)
    resultado["muestra_parcial"] = bool(max_bytes and len(raw) >= max_bytes)
    return resultado


class FormatoNoSoportado(Exception):
    pass


def sincronizar(dataset_id, catalogo, resource_id=None, max_mb=None):
    """Sincroniza UN dataset. Devuelve el dict de resultado — nunca
    lanza por un fallo de red o de parseo (los refleja en el resultado,
    con `estado` y detalle); SÍ lanza si el dataset/resource_id pedido
    explícitamente no existe en el catálogo, porque eso es un error de
    quien llama, no una falla transitoria de la fuente."""
    entrada = buscar_en_catalogo(catalogo, dataset_id)
    if entrada is None:
        raise RuntimeError(f"{dataset_id!r} no está en el catálogo — corre discovery.py primero, o revisa el dataset_id.")

    recurso = elegir_recurso(entrada, resource_id)
    if recurso is None:
        return {
            "dataset_id": dataset_id,
            "titulo": entrada.get("titulo"),
            "dataset_url": entrada.get("dataset_url"),
            "estado": "error",
            "error": "el dataset no tiene ningún recurso en el catálogo",
        }

    errores_por_nivel = {}
    datos = None
    nivel_usado = None

    # Nivel 1: Data API, solo si discovery.py ya la confirmó para este
    # recurso — evita gastar una petición extra probándola de nuevo aquí
    # cuando ya sabemos la respuesta (y si cambió desde el descubrimiento,
    # el nivel 2 la vuelve a intentar como descarga directa de todos
    # modos).
    if recurso.get("tiene_data_api") is True and recurso.get("resource_id"):
        try:
            r = datastore_search_all(
                recurso["resource_id"],
                max_records=(int(max_mb * 2000) if max_mb else None),
            )
            datos = {
                "columnas_detectadas": r["fields"],
                "filas_leidas": len(r["records"]),
                "muestra": r["records"][:20],
                "muestra_parcial": bool(max_mb),
            }
            nivel_usado = "data_api"
        except Exception as exc:
            errores_por_nivel["data_api"] = str(exc)
            print(f"    Data API falló para {dataset_id} ({exc}) — se intenta descarga directa.", file=sys.stderr)

    # Nivel 2: URL en vivo (package_show fresco).
    if datos is None:
        url_viva, origen = resolver_url_en_vivo(dataset_id, recurso.get("resource_id"), recurso.get("resource_url"))
        try:
            datos = descargar_y_parsear(url_viva, recurso.get("formato"), max_mb=max_mb)
            nivel_usado = origen
        except FormatoNoSoportado as exc:
            return {
                "dataset_id": dataset_id,
                "titulo": entrada.get("titulo"),
                "dataset_url": entrada.get("dataset_url"),
                "resource_id": recurso.get("resource_id"),
                "estado": "formato_no_soportado",
                "formato": str(exc),
            }
        except Exception as exc:
            errores_por_nivel[origen] = str(exc)
            print(f"    Descarga ({origen}) falló para {dataset_id} ({exc}).", file=sys.stderr)

    # Nivel 3: URL guardada en el catálogo, si el nivel 2 usó otra URL y
    # falló (si el nivel 2 YA usaba la del catálogo porque package_show
    # falló, reintentar la misma URL no serviría de nada, así que se
    # salta).
    if datos is None and recurso.get("resource_url") and "url_catalogo" not in errores_por_nivel:
        try:
            datos = descargar_y_parsear(recurso["resource_url"], recurso.get("formato"), max_mb=max_mb)
            nivel_usado = "url_catalogo_respaldo"
        except FormatoNoSoportado as exc:
            return {
                "dataset_id": dataset_id,
                "titulo": entrada.get("titulo"),
                "dataset_url": entrada.get("dataset_url"),
                "resource_id": recurso.get("resource_id"),
                "estado": "formato_no_soportado",
                "formato": str(exc),
            }
        except Exception as exc:
            errores_por_nivel["url_catalogo_respaldo"] = str(exc)

    if datos is None:
        return {
            "dataset_id": dataset_id,
            "titulo": entrada.get("titulo"),
            "dataset_url": entrada.get("dataset_url"),
            "resource_id": recurso.get("resource_id"),
            "estado": "error",
            "errores_por_nivel": errores_por_nivel,
        }

    return {
        "dataset_id": dataset_id,
        "titulo": entrada.get("titulo"),
        "dataset_url": entrada.get("dataset_url"),
        "resource_id": recurso.get("resource_id"),
        "estado": "ok",
        "nivel_usado": nivel_usado,
        **datos,
    }


def guardar_resultado(resultado, sources_dir=SOURCES_DIR):
    """Guarda latest.json + raw/<fecha>.json + agrega una línea a
    history.jsonl — ver docstring del módulo sobre el modelo de datos.
    El timestamp se calcula UNA vez aquí y se usa en los 3 lugares, para
    que latest.json y el archivo en raw/ correspondientes a esta misma
    corrida queden con exactamente la misma fecha."""
    import datetime
    generado_en = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    resultado = {**resultado, "generado_en": generado_en}

    carpeta = os.path.join(sources_dir, resultado["dataset_id"])
    os.makedirs(os.path.join(carpeta, "raw"), exist_ok=True)

    with open(os.path.join(carpeta, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    nombre_archivo_raw = generado_en.replace(":", "-") + ".json"
    with open(os.path.join(carpeta, "raw", nombre_archivo_raw), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    linea = {
        "fecha": generado_en,
        "estado": resultado["estado"],
        "filas": resultado.get("filas_leidas"),
        "nivel_usado": resultado.get("nivel_usado"),
    }
    with open(os.path.join(carpeta, "history.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")

    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset_id", nargs="?", help="dataset_id exacto tal como aparece en catalog.json")
    parser.add_argument("--todos-de-categoria", help="En vez de un dataset_id, sincroniza TODOS los del catálogo con esta categoría (ej. 'Economía y Finanzas').")
    parser.add_argument("--limit", type=int, default=None, help="Con --todos-de-categoria: procesar solo los primeros N (contados desde --empezar-en).")
    parser.add_argument("--empezar-en", type=int, default=0, help="Con --todos-de-categoria: saltar los primeros N datasets de la categoría — para CONTINUAR una corrida anterior que se cortó por tiempo (ver 'siguiente_empezar_en' en el resumen de esa corrida).")
    parser.add_argument("--max-minutos", type=float, default=None, help="Con --todos-de-categoria: detenerse ordenadamente (cada dataset ya se guarda individualmente al procesarse, así que nada se pierde) si supera este tiempo, en vez de esperar a que GitHub Actions lo mate de golpe.")
    parser.add_argument("--resource-id", help="Forzar un resource_id específico en vez del que se elige automáticamente (solo tiene sentido con un dataset_id único, no con --todos-de-categoria).")
    parser.add_argument("--max-mb", type=float, default=None, help="Cortar la descarga a los primeros N MB (muestra parcial) — recomendado en corridas grandes para no bajar archivos enormes sin querer (ver mef.py, que sí necesita el archivo completo aparte).")
    parser.add_argument("--catalogo", default=CATALOG_PATH, help="Ruta a catalog.json (default: data/catalog.json).")
    parser.add_argument("--out-dir", default=SOURCES_DIR, help="Carpeta base de salida (default: data/sources/).")
    parser.add_argument("--resumen-out", default=None, help="Con --todos-de-categoria: ruta donde guardar un resumen JSON de la corrida (totales, siguiente_empezar_en). Default: <out-dir>/_resumen_ultima_corrida.json.")
    parser.add_argument("--pausa", type=float, default=0.5, help="Segundos de espera entre datasets en modo --todos-de-categoria.")
    args = parser.parse_args()

    if not args.dataset_id and not args.todos_de_categoria:
        parser.error("hace falta un dataset_id, o --todos-de-categoria")

    try:
        catalogo = cargar_catalogo(args.catalogo)
    except FileNotFoundError:
        print(f"ERROR: no existe {args.catalogo} — corre discovery.py primero.", file=sys.stderr)
        sys.exit(1)

    if args.dataset_id:
        resultado = sincronizar(args.dataset_id, catalogo, resource_id=args.resource_id, max_mb=args.max_mb)
        resultado = guardar_resultado(resultado, sources_dir=args.out_dir)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        sys.exit(0 if resultado["estado"] == "ok" else 1)

    todos_los_de_la_categoria = [
        ds["dataset_id"] for ds in catalogo.get("datasets", [])
        if ds.get("categoria") == args.todos_de_categoria
    ]
    total_categoria = len(todos_los_de_la_categoria)
    objetivo = todos_los_de_la_categoria[args.empezar_en:]
    if args.limit:
        objetivo = objetivo[:args.limit]
    print(
        f"{total_categoria} datasets en la categoría {args.todos_de_categoria!r}. "
        f"Empezando en el índice {args.empezar_en}, procesando {len(objetivo)}...",
        file=sys.stderr,
    )

    inicio = time.time()
    ok, errores, no_soportados = 0, 0, 0
    cortado_por_tiempo = False
    procesados = 0
    for i, dataset_id in enumerate(objetivo, 1):
        if args.max_minutos is not None and (time.time() - inicio) / 60 >= args.max_minutos:
            print(f"  Se alcanzó --max-minutos ({args.max_minutos}) en {i}/{len(objetivo)} — deteniendo.", file=sys.stderr)
            cortado_por_tiempo = True
            break
        print(f"[{i}/{len(objetivo)}] {dataset_id}", file=sys.stderr)
        try:
            resultado = sincronizar(dataset_id, catalogo, max_mb=args.max_mb)
            resultado = guardar_resultado(resultado, sources_dir=args.out_dir)
            if resultado["estado"] == "ok":
                ok += 1
                print(f"    OK — {resultado.get('filas_leidas')} filas, nivel={resultado.get('nivel_usado')}", file=sys.stderr)
            elif resultado["estado"] == "formato_no_soportado":
                no_soportados += 1
                print(f"    formato no soportado: {resultado.get('formato')}", file=sys.stderr)
            else:
                errores += 1
                print(f"    ERROR: {resultado.get('errores_por_nivel') or resultado.get('error')}", file=sys.stderr)
        except Exception as exc:
            errores += 1
            print(f"    ERROR inesperado: {exc}", file=sys.stderr)
        procesados = i
        time.sleep(args.pausa)

    siguiente_empezar_en = args.empezar_en + procesados
    corrida_completa = (not cortado_por_tiempo) and siguiente_empezar_en >= total_categoria
    resumen = {
        "categoria": args.todos_de_categoria,
        "total_en_categoria": total_categoria,
        "empezar_en_usado": args.empezar_en,
        "procesados_esta_corrida": procesados,
        "ok": ok,
        "errores": errores,
        "no_soportados": no_soportados,
        "cortado_por_tiempo": cortado_por_tiempo,
        "corrida_completa": corrida_completa,
        "siguiente_empezar_en": None if corrida_completa else siguiente_empezar_en,
    }
    resumen_out = args.resumen_out or os.path.join(args.out_dir, "_resumen_ultima_corrida.json")
    os.makedirs(os.path.dirname(resumen_out), exist_ok=True)
    with open(resumen_out, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print(
        f"\nListo: {ok} ok, {errores} con error, {no_soportados} con formato no soportado, "
        f"de {procesados} procesados en esta corrida ({total_categoria} en la categoría). "
        + ("CORRIDA COMPLETA." if corrida_completa else f"PARCIAL — continuar con --empezar-en {siguiente_empezar_en}."),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
