#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analytics.py — Fase 7 de "Perú en Datos".

Lee data/catalog.json (Fase 3) + TODOS los data/sources/<dataset_id>/
history.jsonl (Fase 4-6, ya con `cambio` calculado por sync_dataset.py)
y calcula, para la categoría Economía y Finanzas, variaciones %,
rankings y tendencias -> data/analytics/economia-finanzas.json.

QUÉ NO HACE (a propósito, mismo principio que sync_dataset.py)
-----------------------------------------------------------------
No interpreta el SIGNIFICADO de ninguna columna de ningún dataset — con
~500-700 datasets de estructuras totalmente distintas, no hay forma
honesta de calcular "cuánto gastó el Estado" o "cuánto subió la
recaudación" sin adivinar qué columna es cuál en cada uno. Lo único que
se puede afirmar con certeza para CUALQUIER dataset es su CONTEO DE
FILAS a lo largo del tiempo (lo que ya calcula `_calcular_cambio` en
sync_dataset.py) — así que TODO en este archivo (variaciones, rankings,
tendencias) se basa exclusivamente en filas_leidas y en metadata del
catálogo (entidad, tiene_data_api, etc.), nunca en el contenido de las
columnas. Interpretar columnas específicas (montos, regiones) queda
para conectores dedicados por dataset (como ya hacen mef.py/
contraloria.py) o para una fase posterior si se decide invertir en ello
dataset por dataset.

TENDENCIA POR DATASET
----------------------
Se calcula sobre las últimas `VENTANA_TENDENCIA` corridas con
estado "ok" de cada dataset (no todo el historial — así una racha vieja
no determina la tendencia "actual"): si son menos de 2 puntos, la
tendencia es "insuficiente_historial" (nunca se inventa una dirección
con un solo dato); si no, se compara el primer y el último punto de esa
ventana.

USO
---
  python3 connectors/analytics.py
  # -> escribe data/analytics/economia-finanzas.json
"""
import argparse
import datetime
import json
import os
import statistics
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
OUT_PATH = os.path.join(DATA_DIR, "analytics", "economia-finanzas.json")

CATEGORIA = "Economía y Finanzas"
VENTANA_TENDENCIA = 5
TOP_N = 10


def cargar_catalogo(catalog_path):
    try:
        with open(catalog_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _leer_lineas_historial(history_path):
    """Todas las líneas válidas de un history.jsonl, en orden cronológico
    (el archivo ya se escribe con append, así que el orden del archivo ES
    el orden cronológico). Nunca lanza: una línea corrupta se descarta,
    no invalida el resto."""
    lineas = []
    try:
        with open(history_path, encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if not l:
                    continue
                try:
                    lineas.append(json.loads(l))
                except Exception:
                    continue
    except Exception:
        return []
    return lineas


def _tendencia(lineas_ok, ventana=VENTANA_TENDENCIA):
    """lineas_ok: lista de `filas` (int) de las corridas con estado ok,
    en orden cronológico. Devuelve "creciente"/"decreciente"/"estable"/
    "insuficiente_historial"."""
    puntos = lineas_ok[-ventana:]
    if len(puntos) < 2:
        return "insuficiente_historial"
    primero, ultimo = puntos[0], puntos[-1]
    if ultimo > primero:
        return "creciente"
    if ultimo < primero:
        return "decreciente"
    return "estable"


def calcular(catalog_path=CATALOG_PATH, sources_dir=SOURCES_DIR, categoria=CATEGORIA):
    generado_en = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalogo = cargar_catalogo(catalog_path)

    catalogo_stats = {
        "categoria": categoria,
        "total_datasets_portal": catalogo.get("total_datasets_portal") if catalogo else None,
        "total_clasificados_en_categoria": None,
        "catalogo_corrida_completa": catalogo.get("corrida_completa") if catalogo else None,
        "catalogo_generado_en": catalogo.get("generado_en") if catalogo else None,
    }

    datasets_categoria = []
    entidad_por_id = {}
    titulo_por_id = {}
    resources_con_api_por_id = {}
    if catalogo:
        for ds in catalogo.get("datasets", []):
            if ds.get("categoria") != categoria:
                continue
            datasets_categoria.append(ds["dataset_id"])
            entidad_por_id[ds["dataset_id"]] = ds.get("entidad")
            titulo_por_id[ds["dataset_id"]] = ds.get("titulo") or ds["dataset_id"]
            resources_con_api_por_id[ds["dataset_id"]] = any(
                r.get("tiene_data_api") is True for r in (ds.get("resources") or [])
            )
        catalogo_stats["total_clasificados_en_categoria"] = len(datasets_categoria)

    por_estado = {}
    filas_ok = []  # (dataset_id, filas) — última corrida ok de cada dataset
    variaciones = []  # última corrida con cambio real (aumento/disminucion)
    tendencia_conteo = {"creciente": 0, "decreciente": 0, "estable": 0, "insuficiente_historial": 0}
    entidad_sincronizados_ok = {}
    total_con_historial = 0
    total_con_data_api_confirmada = 0

    ids_a_revisar = datasets_categoria if catalogo else (
        sorted(os.listdir(sources_dir)) if os.path.isdir(sources_dir) else []
    )

    for dataset_id in ids_a_revisar:
        history_path = os.path.join(sources_dir, dataset_id, "history.jsonl")
        if not os.path.isfile(history_path):
            continue
        lineas = _leer_lineas_historial(history_path)
        if not lineas:
            continue
        total_con_historial += 1

        ultima = lineas[-1]
        estado = ultima.get("estado") or "desconocido"
        por_estado[estado] = por_estado.get(estado, 0) + 1

        if resources_con_api_por_id.get(dataset_id):
            total_con_data_api_confirmada += 1

        entidad = entidad_por_id.get(dataset_id)
        titulo = titulo_por_id.get(dataset_id, dataset_id)

        if estado == "ok" and ultima.get("filas") is not None:
            filas_ok.append({"dataset_id": dataset_id, "titulo": titulo, "entidad": entidad, "filas": ultima["filas"]})
            if entidad:
                entidad_sincronizados_ok[entidad] = entidad_sincronizados_ok.get(entidad, 0) + 1

        cambio = ultima.get("cambio") or {}
        if cambio.get("tipo") in ("aumento", "disminucion") and cambio.get("diferencia_pct") is not None:
            variaciones.append({
                "dataset_id": dataset_id,
                "titulo": titulo,
                "entidad": entidad,
                "tipo": cambio["tipo"],
                "filas_antes": cambio.get("filas_antes"),
                "filas_despues": cambio.get("filas_despues"),
                "diferencia": cambio.get("diferencia"),
                "diferencia_pct": cambio.get("diferencia_pct"),
            })

        puntos_ok = [l.get("filas") for l in lineas if l.get("estado") == "ok" and l.get("filas") is not None]
        tendencia_conteo[_tendencia(puntos_ok)] += 1

    filas_ok.sort(key=lambda d: d["filas"], reverse=True)
    ranking_mas_filas = filas_ok[:TOP_N]

    aumentos = sorted(
        [v for v in variaciones if v["tipo"] == "aumento"],
        key=lambda v: v["diferencia_pct"], reverse=True,
    )[:TOP_N]
    disminuciones = sorted(
        [v for v in variaciones if v["tipo"] == "disminucion"],
        key=lambda v: v["diferencia_pct"],
    )[:TOP_N]

    top_entidades = sorted(entidad_sincronizados_ok.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]

    valores_filas = [d["filas"] for d in filas_ok]

    return {
        "generado_en": generado_en,
        "catalogo": catalogo_stats,
        "sincronizacion": {
            "total_con_historial": total_con_historial,
            "por_estado": por_estado,
            "total_con_data_api_confirmada": total_con_data_api_confirmada,
        },
        "filas": {
            "total_datasets_con_filas_ok": len(filas_ok),
            "total_filas_ok": sum(valores_filas) if valores_filas else 0,
            "promedio_filas_ok": round(statistics.mean(valores_filas), 1) if valores_filas else None,
            "mediana_filas_ok": statistics.median(valores_filas) if valores_filas else None,
            "ranking_mas_filas": ranking_mas_filas,
        },
        "variaciones": {
            "total_con_variacion_detectada": len(variaciones),
            "ranking_mayor_aumento_pct": aumentos,
            "ranking_mayor_disminucion_pct": disminuciones,
        },
        "tendencias": {
            "ventana_corridas": VENTANA_TENDENCIA,
            "conteo": tendencia_conteo,
        },
        "entidades": {
            "top_por_datasets_sincronizados_ok": [{"entidad": e, "conteo": c} for e, c in top_entidades],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogo", default=CATALOG_PATH)
    parser.add_argument("--sources-dir", default=SOURCES_DIR)
    parser.add_argument("--categoria", default=CATEGORIA)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    resultado = calcular(catalog_path=args.catalogo, sources_dir=args.sources_dir, categoria=args.categoria)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(
        f"{resultado['sincronizacion']['total_con_historial']} datasets con historial · "
        f"{resultado['filas']['total_datasets_con_filas_ok']} con filas ok · "
        f"{resultado['variaciones']['total_con_variacion_detectada']} con variación detectada",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
