#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contraloria.py — Conector para datos de la Contraloría General de la
República publicados en el Portal Nacional de Datos Abiertos (PNDA).

FUENTE Y VERIFICACIÓN
----------------------
La Contraloría no tiene una API REST propia y documentada para sus informes
de auditoría (su buscador de informes es una aplicación web sin endpoint de
datos abiertos conocido). Lo que SÍ se encontró y verificó en esta sesión
son datasets reales de "Monitores Ciudadanos de Control" (control social,
no auditorías) publicados en PNDA, confirmados por dos vías independientes
(la página del dataset y la API package_show devolviendo la misma URL):

  - Resultados de intervenciones 2021:
    https://www.datosabiertos.gob.pe/dataset/resultados-de-las-intervenciones-realizadas-por-los-monitores-ciudadanos-de-control-en-el
  - Información general de los monitores:
    https://www.datosabiertos.gob.pe/dataset/informaci%C3%B3n-general-de-los-monitores-ciudadanos-de-control

No se pudo leer el contenido real de estos CSV desde el entorno donde se
escribió este conector (ver common.py) — así que las columnas se detectan
en tiempo de ejecución, no se asumen. Corre esto una vez con salida de red
real (GitHub Actions) y revisa `columnas_detectadas` en el JSON de salida
para confirmar que la detección funcionó.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import detect_column, download_to_file, http_get, normalize, sniff_csv_reader, write_summary

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contraloria.json")

DATASETS = [
    {
        "titulo": "Resultados de intervenciones de Monitores Ciudadanos de Control 2021",
        "dataset_url": "https://www.datosabiertos.gob.pe/dataset/resultados-de-las-intervenciones-realizadas-por-los-monitores-ciudadanos-de-control-en-el",
        "csv_url": "https://www.datosabiertos.gob.pe/sites/default/files/DATOS%20ABIERTOS%20-%20RESULTADOS%20DE%20INTERVENCIONES%202021_3.csv",
    },
    {
        "titulo": "Información general de los Monitores Ciudadanos de Control",
        "dataset_url": "https://www.datosabiertos.gob.pe/dataset/informaci%C3%B3n-general-de-los-monitores-ciudadanos-de-control",
        "csv_url": "https://www.datosabiertos.gob.pe/sites/default/files/DATOS%20ABIERTOS%20-%20MONITORES%20CIUDADANOS%20DE%20CONTROL.csv",
    },
]

REGION_CANDIDATES = ["departamento", "region", "dpto", "ubigeo departamento"]
FECHA_CANDIDATES = ["fecha", "anio", "año", "periodo", "fecha de intervencion"]


def process_csv(csv_bytes, titulo):
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = sniff_csv_reader(io.StringIO(text))
    fieldnames = reader.fieldnames or []

    region_col = detect_column(fieldnames, REGION_CANDIDATES)
    fecha_col = detect_column(fieldnames, FECHA_CANDIDATES)

    total = 0
    por_region = {}
    for row in reader:
        total += 1
        if region_col:
            val = (row.get(region_col) or "").strip().title()
            if val:
                por_region[val] = por_region.get(val, 0) + 1

    top_regiones = sorted(por_region.items(), key=lambda kv: -kv[1])[:10]

    return {
        "titulo": titulo,
        "filas_totales": total,
        "columnas_detectadas": fieldnames,
        "columna_region_usada": region_col,
        "columna_fecha_usada": fecha_col,
        "top_regiones": [{"region": r, "conteo": c} for r, c in top_regiones] if region_col else None,
    }


def main():
    results = []
    for ds in DATASETS:
        print(f"Descargando {ds['titulo']} ...", file=sys.stderr)
        try:
            resp = http_get(ds["csv_url"])
            data = resp.read()
            print(f"  {len(data):,} bytes descargados", file=sys.stderr)
            parsed = process_csv(data, ds["titulo"])
            parsed["dataset_url"] = ds["dataset_url"]
            parsed["csv_url"] = ds["csv_url"]
            parsed["estado"] = "ok"
            results.append(parsed)
        except Exception as exc:
            print(f"  ERROR con {ds['titulo']}: {exc}", file=sys.stderr)
            results.append({
                "titulo": ds["titulo"],
                "dataset_url": ds["dataset_url"],
                "csv_url": ds["csv_url"],
                "estado": "error",
                "error": str(exc),
            })

    summary = {
        "fuente": "Contraloría General de la República — Monitores Ciudadanos de Control",
        "atribucion": "Datos publicados por la Contraloría General de la República en el Portal Nacional de Datos Abiertos (PNDA).",
        "datasets": results,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, summary)


if __name__ == "__main__":
    main()
