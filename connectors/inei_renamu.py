#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inei_renamu.py — Conector para el Registro Nacional de Municipalidades
(RENAMU) del INEI, publicado en el Portal Nacional de Datos Abiertos.

FUENTE Y VERIFICACIÓN
----------------------
Página del dataset (verificada, responde con contenido real):
  https://www.datosabiertos.gob.pe/dataset/registro-nacional-de-municipalidades-renamu-2023-instituto-nacional-de-estad%C3%ADstica-e

Desde esa página se confirmaron dos recursos:
  - "Data de muestra" (CSV, más manejable):
    https://www.datosabiertos.gob.pe/sites/default/files/BD_Muestra_2023.csv
  - "Data completa" (ZIP, servido por INEI directamente — no descargado ni
    inspeccionado en esta sesión, se deja para una segunda fase):
    https://www.inei.gob.pe/media/DATOS_ABIERTOS/RENAMU/DATA/2023.zip

Este conector usa la muestra por ahora — es la opción verificada más simple.
Igual que en contraloria.py, las columnas NO se asumen: se detectan en
tiempo de ejecución (ver common.py) porque no fue posible leer el contenido
real del CSV desde el entorno donde se escribió esto.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import detect_column, http_get, sniff_csv_reader, write_summary

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "inei_renamu.json")

DATASET_URL = "https://www.datosabiertos.gob.pe/dataset/registro-nacional-de-municipalidades-renamu-2023-instituto-nacional-de-estad%C3%ADstica-e"
CSV_URL = "https://www.datosabiertos.gob.pe/sites/default/files/BD_Muestra_2023.csv"

REGION_CANDIDATES = ["departamento", "region", "dpto", "nombdep"]
PROVINCIA_CANDIDATES = ["provincia", "nombprov"]
DISTRITO_CANDIDATES = ["distrito", "nombdist", "municipalidad"]


def process_csv(csv_bytes):
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = sniff_csv_reader(io.StringIO(text))
    fieldnames = reader.fieldnames or []

    region_col = detect_column(fieldnames, REGION_CANDIDATES)
    provincia_col = detect_column(fieldnames, PROVINCIA_CANDIDATES)
    distrito_col = detect_column(fieldnames, DISTRITO_CANDIDATES)

    total = 0
    municipios_por_region = {}
    for row in reader:
        total += 1
        if region_col:
            val = (row.get(region_col) or "").strip().title()
            if val:
                municipios_por_region[val] = municipios_por_region.get(val, 0) + 1

    ranking = sorted(municipios_por_region.items(), key=lambda kv: -kv[1])

    return {
        "filas_totales": total,
        "columnas_detectadas": fieldnames,
        "columna_region_usada": region_col,
        "columna_provincia_usada": provincia_col,
        "columna_distrito_usada": distrito_col,
        "municipalidades_por_region": [{"region": r, "conteo": c} for r, c in ranking] if region_col else None,
    }


def main():
    print(f"Descargando muestra RENAMU 2023 ...", file=sys.stderr)
    try:
        resp = http_get(CSV_URL)
        data = resp.read()
        print(f"  {len(data):,} bytes descargados", file=sys.stderr)
        result = process_csv(data)
        result["estado"] = "ok"
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        result = {"estado": "error", "error": str(exc)}

    summary = {
        "fuente": "INEI — Registro Nacional de Municipalidades (RENAMU) 2023, muestra",
        "atribucion": "Instituto Nacional de Estadística e Informática (INEI), vía Portal Nacional de Datos Abiertos.",
        "dataset_url": DATASET_URL,
        "csv_url": CSV_URL,
        "nota": "Esta es la 'data de muestra' publicada por el portal, no el registro completo — más rápida de procesar para esta primera versión. La data completa está en un .zip servido por INEI, pendiente de una segunda fase.",
        **result,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, summary)


if __name__ == "__main__":
    main()
