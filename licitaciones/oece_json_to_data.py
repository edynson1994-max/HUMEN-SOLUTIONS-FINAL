#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oece_json_to_data.py — Convierte el/los archivo(s) .zip descargados por
scrape_oece.py (entregas OCDS compiladas del portal oficial oece.gob.pe) al
mismo data.json que consume index.html.

Reutiliza a propósito la MISMA lógica de parseo que sync.py (parse_release,
match_humen_tags, el filtro de vigencia, get_process_url, etc.) importándola
directamente de ahí, en vez de copiarla: esa lógica ya pasó por dos rondas de
corrección de bugs reales (licitaciones vencidas que se colaban) y no tiene
sentido arriesgarse a reintroducir los mismos errores por mantener dos copias
del mismo filtro.

FORMATO DE ENTRADA
-------------------
Según el propio portal, cada descarga es un .zip que contiene un archivo
.json con la lista de "entregas compiladas" (compiled releases) — o bien un
único release package (con clave "releases": [...]) o, según el mes, una
lista de releases sueltos. Este script acepta ambas formas.

USO
---
    python3 oece_json_to_data.py descargas/*.zip
    python3 oece_json_to_data.py descargas/2026-08.zip --region-fallback Cusco
"""

import argparse
import glob
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import sync  # reutiliza parse_release, match_humen_tags, get_process_url, etc.

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data.json")

ATTRIBUTION = (
    "Datos del Portal de Contrataciones Abiertas de la Compra Pública del "
    "Perú (OECE), descargados en formato OCDS desde la sección Descargas del "
    "propio portal oficial. Banco de información pública — no requiere "
    "afiliación con Humen Solutions para consultarlo."
)
SOURCE_URL = "https://contratacionesabiertas.oece.gob.pe/descargas"


def iter_releases_from_zip(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        json_names = [n for n in zf.namelist() if n.lower().endswith(".json")]
        if not json_names:
            print(f"  (aviso: {zip_path} no trae ningún .json adentro, se omite)", file=sys.stderr)
            return
        for name in json_names:
            with zf.open(name) as f:
                raw = f.read()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"  (aviso: {name} dentro de {zip_path} no es JSON válido: {exc}, se omite)", file=sys.stderr)
                continue

            if isinstance(payload, dict) and "releases" in payload:
                for release in payload["releases"]:
                    yield release
            elif isinstance(payload, list):
                for release in payload:
                    yield release
            elif isinstance(payload, dict) and "tender" in payload:
                # un único release suelto, no envuelto en un package
                yield payload
            else:
                print(f"  (aviso: no se reconoce la forma del JSON en {name}, se omite)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip_files", nargs="+", help="Uno o más .zip descargados por scrape_oece.py.")
    args = parser.parse_args()

    all_paths = []
    for pattern in args.zip_files:
        matched = glob.glob(pattern)
        all_paths.extend(matched if matched else [pattern])

    items = []
    sample_saved = False
    for path in all_paths:
        if not os.path.exists(path):
            print(f"  (aviso: {path} no existe, se omite)", file=sys.stderr)
            continue
        print(f"Leyendo {path} ...", file=sys.stderr)
        count = 0
        for release in iter_releases_from_zip(path):
            count += 1
            if not sample_saved:
                with open(sync.SAMPLE_RAW_PATH, "w", encoding="utf-8") as f:
                    json.dump(release, f, ensure_ascii=False, indent=2)
                sample_saved = True
            item = sync.parse_release(release)
            if item:
                items.append(item)
        print(f"  {count} releases leídos", file=sys.stderr)

    seen = {}
    for item in items:
        key = item["id"] or item["code"]
        if key not in seen:
            seen[key] = item
    items = list(seen.values())

    items.sort(key=lambda r: (r["dueDate"] is None, r["dueDate"] or ""))
    dropped = max(0, len(items) - sync.MAX_ITEMS)
    items = items[: sync.MAX_ITEMS]

    humen_counts = {"cont": 0, "inv": 0, "rec": 0}
    for item in items:
        for tag in item["humenTags"]:
            humen_counts[tag] += 1

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attribution": ATTRIBUTION,
        "source_url": SOURCE_URL,
        "total_count": len(items),
        "humen_counts": humen_counts,
        "dropped_by_cap": dropped,
        "items": items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Listo: {len(items)} convocatorias vigentes guardadas en {OUTPUT_PATH}", file=sys.stderr)
    if dropped:
        print(f"  ({dropped} quedaron fuera por el tope de {sync.MAX_ITEMS})", file=sys.stderr)


if __name__ == "__main__":
    main()
