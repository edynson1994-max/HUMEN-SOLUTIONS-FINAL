#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detectar_cambios.py — Fase 6 (segunda mitad) de "Perú en Datos".

sync_dataset.py (ver `_calcular_cambio` en ese archivo) ya calcula, POR
DATASET, si cambió el conteo de filas entre su corrida más reciente y la
anterior, y lo guarda en la última línea de
data/sources/<dataset_id>/history.jsonl.

Este script recorre TODOS los data/sources/*/history.jsonl, toma la
ÚLTIMA línea de cada uno (el resultado de la corrida más reciente de
CADA dataset — no reprocesa nada, solo lee lo que sync_dataset.py ya
calculó) y arma un único archivo agregado, data/cambios_recientes.json,
para que el frontend no tenga que hacer cientos de fetch() (uno por
carpeta) para mostrar la sección "¿Qué cambió?" (Fase 9).

QUÉ CUENTA COMO "CAMBIO" AQUÍ
------------------------------
Solo entran a la lista detallada los datasets cuya última corrida SÍ se
pudo comparar contra la anterior (`cambio.tipo` en
{"aumento","disminucion"} — con una diferencia de filas real, distinta
de cero). Los "sin_cambio", "no_comparable" y "primera_sincronizacion"
se cuentan en las estadísticas agregadas (para que el resumen sea
honesto sobre cuánto del catálogo se pudo comparar de verdad) pero no
aparecen en la lista — mostrar "esto no cambió" en una sección que se
llama "¿Qué cambió?" no aporta nada al lector.

La lista se ordena por MAGNITUD del cambio (|diferencia|), no por fecha
— es lo más útil para alguien que entra a ver "qué pasó", y evita tener
que inventar un criterio editorial de qué cambio es "importante" más
allá del número real. Se recorta a MAX_MOSTRADOS (ver más abajo) para
no mandar un archivo enorme al navegador — el recorte SIEMPRE queda
explícito en el propio JSON (`total_con_cambio_detectado` vs.
`total_mostrados`), nunca es un corte silencioso.

USO
---
  python3 connectors/detectar_cambios.py
  # -> escribe data/cambios_recientes.json
"""
import argparse
import datetime
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
OUT_PATH = os.path.join(DATA_DIR, "cambios_recientes.json")

MAX_MOSTRADOS = 40


def _leer_ultima_linea(path):
    """Igual que common: nunca lanza — un history.jsonl vacío, ausente o
    con la última línea corrupta simplemente se ignora (ese dataset no
    aporta ningún cambio a este reporte, pero no rompe el resto)."""
    try:
        with open(path, encoding="utf-8") as f:
            lineas = [l for l in f if l.strip()]
        if not lineas:
            return None
        return json.loads(lineas[-1])
    except Exception:
        return None


def cargar_titulos_catalogo(catalog_path):
    """dataset_id -> {titulo, dataset_url, entidad} — para no repetir esa
    info en cada history.jsonl. Si el catálogo no existe o falla, se
    sigue igual: el dataset_id crudo sirve de título de respaldo."""
    try:
        with open(catalog_path, encoding="utf-8") as f:
            catalogo = json.load(f)
    except Exception:
        return {}
    return {
        ds["dataset_id"]: {
            "titulo": ds.get("titulo") or ds["dataset_id"],
            "dataset_url": ds.get("dataset_url"),
            "entidad": ds.get("entidad"),
        }
        for ds in catalogo.get("datasets", [])
    }


def detectar(sources_dir=SOURCES_DIR, catalog_path=CATALOG_PATH, max_mostrados=MAX_MOSTRADOS):
    titulos = cargar_titulos_catalogo(catalog_path)

    resultado_vacio = {
        "generado_en": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_datasets_con_historial": 0,
        "total_con_cambio_detectado": 0,
        "total_mostrados": 0,
        "total_primera_sincronizacion": 0,
        "total_sin_cambio_o_no_comparable": 0,
        "cambios": [],
    }
    if not os.path.isdir(sources_dir):
        return resultado_vacio

    entradas_cambio = []
    n_total = 0
    n_primera = 0
    n_sin_cambio_o_no_comparable = 0

    for dataset_id in sorted(os.listdir(sources_dir)):
        carpeta = os.path.join(sources_dir, dataset_id)
        history_path = os.path.join(carpeta, "history.jsonl")
        if not os.path.isfile(history_path):
            continue
        ultima = _leer_ultima_linea(history_path)
        if ultima is None:
            continue
        n_total += 1
        cambio = ultima.get("cambio") or {}
        tipo = cambio.get("tipo")

        if tipo == "primera_sincronizacion":
            n_primera += 1
            continue
        if tipo not in ("aumento", "disminucion"):
            n_sin_cambio_o_no_comparable += 1
            continue

        meta = titulos.get(dataset_id, {})
        entradas_cambio.append({
            "dataset_id": dataset_id,
            "titulo": meta.get("titulo") or dataset_id,
            "dataset_url": meta.get("dataset_url"),
            "entidad": meta.get("entidad"),
            "fecha": ultima.get("fecha"),
            "tipo": tipo,
            "filas_antes": cambio.get("filas_antes"),
            "filas_despues": cambio.get("filas_despues"),
            "diferencia": cambio.get("diferencia"),
            "diferencia_pct": cambio.get("diferencia_pct"),
        })

    entradas_cambio.sort(key=lambda e: abs(e["diferencia"] or 0), reverse=True)
    mostrados = entradas_cambio[:max_mostrados]

    return {
        "generado_en": resultado_vacio["generado_en"],
        "total_datasets_con_historial": n_total,
        "total_con_cambio_detectado": len(entradas_cambio),
        "total_mostrados": len(mostrados),
        "total_primera_sincronizacion": n_primera,
        "total_sin_cambio_o_no_comparable": n_sin_cambio_o_no_comparable,
        "cambios": mostrados,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources-dir", default=SOURCES_DIR)
    parser.add_argument("--catalogo", default=CATALOG_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    parser.add_argument("--max-mostrados", type=int, default=MAX_MOSTRADOS)
    args = parser.parse_args()

    resultado = detectar(sources_dir=args.sources_dir, catalog_path=args.catalogo, max_mostrados=args.max_mostrados)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(
        f"{resultado['total_datasets_con_historial']} datasets con historial · "
        f"{resultado['total_con_cambio_detectado']} con cambio detectado "
        f"({resultado['total_mostrados']} mostrados) · "
        f"{resultado['total_primera_sincronizacion']} primera sincronización · "
        f"{resultado['total_sin_cambio_o_no_comparable']} sin cambio/no comparable",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
