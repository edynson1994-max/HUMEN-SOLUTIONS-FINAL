#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catalogo_indice.py — Fase 13 de "Perú en Datos": índice completo y
navegable de una categoría del catálogo, para el Catálogo de datos
abiertos de la página (antes mostraba solo 4 datasets escritos a mano,
sin relación con los datasets realmente sincronizados).

QUÉ RESUELVE
------------
El Catálogo mostraba 4 tarjetas escritas a mano en app.html
(CATALOGO_CONECTADOS/CATALOGO_DISPONIBLES) que nunca se actualizaron
para reflejar los 505 datasets reales que discovery.py ya descubrió ni
los 213 que sync_dataset.py ya sincronizó. Resultado: alguien navegando
el Catálogo no podía ver más que un puñado fijo de datasets, y no había
forma de saber ANTES de hacer clic si un dataset realmente tiene datos
utilizables o si va a caer en "formato no soportado" — exactamente el
problema que reportó el cliente.

Este script cruza data/catalog.json (todo lo que discovery.py conoce de
la categoría) con el `estado` real de la ÚLTIMA corrida de cada uno en
data/sources/<id>/history.jsonl (lo que sync_dataset.py ya sincronizó,
si acaso) y escribe UN SOLO archivo compacto con los 505 (o los que
haya) listos para que el frontend arme un catálogo navegable completo,
con badges honestos (Datos disponibles / Formato no soportado / Error /
Todavía no sincronizado) ANTES de que alguien haga clic.

QUÉ NO HACE
-----------
No sincroniza nada nuevo (eso lo sigue haciendo sync_dataset.py) ni
reinterpreta el contenido de ningún dataset — solo lee el `estado` que
sync_dataset.py ya calculó y lo expone en un formato que el frontend
pueda paginar/buscar/filtrar sin tener que pedir 505 archivos JSON
distintos.

USO
---
  python3 connectors/catalogo_indice.py [--categoria "Economía y Finanzas"]
  # -> escribe data/catalogo_indice.json
"""
import argparse
import datetime
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
OUT_PATH = os.path.join(DATA_DIR, "catalogo_indice.json")

CATEGORIA = "Economía y Finanzas"


def cargar_catalogo(catalog_path):
    if not os.path.isfile(catalog_path):
        return None
    try:
        with open(catalog_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"AVISO: no se pudo leer {catalog_path} ({exc}).", file=sys.stderr)
        return None


def _ultimo_estado_real(dataset_id, sources_dir):
    """Lee history.jsonl del dataset y devuelve (estado, filas, formato)
    de su corrida MÁS RECIENTE. Si nunca se sincronizó, estado es
    "no_sincronizado_aun" — nunca se inventa un estado."""
    history_path = os.path.join(sources_dir, dataset_id, "history.jsonl")
    if not os.path.isfile(history_path):
        return "no_sincronizado_aun", None, None
    ultima = None
    try:
        with open(history_path, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    ultima = json.loads(linea)
                except Exception:
                    continue
    except Exception as exc:
        print(f"  AVISO: no se pudo leer {history_path} ({exc}).", file=sys.stderr)
        return "no_sincronizado_aun", None, None
    if ultima is None:
        return "no_sincronizado_aun", None, None
    return (ultima.get("estado") or "desconocido"), ultima.get("filas"), ultima.get("formato")


def calcular(catalog_path=CATALOG_PATH, sources_dir=SOURCES_DIR, categoria=CATEGORIA):
    generado_en = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalogo = cargar_catalogo(catalog_path)

    datasets_salida = []
    conteos = {}

    if catalogo:
        for ds in catalogo.get("datasets", []):
            if ds.get("categoria") != categoria:
                continue
            dataset_id = ds["dataset_id"]
            estado, filas, formato = _ultimo_estado_real(dataset_id, sources_dir)
            conteos[estado] = conteos.get(estado, 0) + 1
            datasets_salida.append({
                "dataset_id": dataset_id,
                "titulo": ds.get("titulo") or dataset_id,
                "entidad": ds.get("entidad"),
                "categoria": categoria,
                "dataset_url": ds.get("dataset_url"),
                "fecha_modificacion_portal": ds.get("fecha_modificacion_portal"),
                "estado": estado,
                "filas": filas,
                "formato": formato,
            })

    return {
        "generado_en": generado_en,
        "categoria": categoria,
        "total_catalogo": len(datasets_salida),
        "total_datasets_portal": catalogo.get("total_datasets_portal") if catalogo else None,
        "catalogo_corrida_completa": catalogo.get("corrida_completa") if catalogo else None,
        "conteos_por_estado": conteos,
        "datasets": datasets_salida,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", default=CATEGORIA)
    parser.add_argument("--catalog", default=CATALOG_PATH)
    parser.add_argument("--sources-dir", default=SOURCES_DIR)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    resultado = calcular(args.catalog, args.sources_dir, args.categoria)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(
        f"Listo: {resultado['total_catalogo']} datasets indexados en {args.out} — "
        f"{resultado['conteos_por_estado']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
