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

ESTRATEGIA DE 3 NIVELES (igual que contraloria.py, ver aviso "Data API" en
common.py): 1) Data API (datastore) sobre el resource_id real que devuelve
package_show, 2) descarga de la URL en vivo que reporta package_show para
ese recurso, 3) descarga de CSV_URL fija de abajo si package_show falla.
En los 3 casos las columnas se detectan en tiempo de ejecución, nunca se
asumen fijas.
"""

import io
import os
import sys
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(__file__))
from common import (
    datastore_search_all,
    detect_column,
    find_resource,
    http_get,
    package_show,
    smart_decode,
    sniff_csv_reader,
    write_summary,
)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "inei_renamu.json")

DATASET_URL = "https://www.datosabiertos.gob.pe/dataset/registro-nacional-de-municipalidades-renamu-2023-instituto-nacional-de-estad%C3%ADstica-e"
CSV_URL = "https://www.datosabiertos.gob.pe/sites/default/files/BD_Muestra_2023.csv"

REGION_CANDIDATES = ["departamento", "region", "dpto", "nombdep"]
PROVINCIA_CANDIDATES = ["provincia", "nombprov"]
DISTRITO_CANDIDATES = ["distrito", "nombdist", "municipalidad"]


def dataset_slug(dataset_url):
    path = urlparse(dataset_url).path
    return unquote(path.rstrip("/").split("/")[-1])


def process_rows(rows, fieldnames):
    region_col = detect_column(fieldnames, REGION_CANDIDATES)
    provincia_col = detect_column(fieldnames, PROVINCIA_CANDIDATES)
    distrito_col = detect_column(fieldnames, DISTRITO_CANDIDATES)

    total = 0
    municipios_por_region = {}
    for row in rows:
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


def process_csv(csv_bytes):
    text = smart_decode(csv_bytes)
    reader = sniff_csv_reader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    return process_rows(reader, fieldnames)


def main():
    resource = None
    try:
        slug = dataset_slug(DATASET_URL)
        pkg = package_show(slug)
        resource = find_resource(pkg, hint="muestra", formato="csv")
    except Exception as exc:
        print(f"package_show falló ({exc}) — se usará la URL fija.", file=sys.stderr)

    result = None

    if resource is not None:
        resource_id = resource.get("id")
        try:
            print(f"Probando Data API (datastore) para resource_id={resource_id} ...", file=sys.stderr)
            ds_data = datastore_search_all(resource_id)
            if not ds_data["records"]:
                raise RuntimeError("la Data API respondió sin registros")
            result = process_rows(ds_data["records"], ds_data["fields"])
            result["metodo"] = "data_api"
            result["resource_id"] = resource_id
            result["estado"] = "ok"
            result["csv_url"] = CSV_URL
        except Exception as exc:
            print(f"  Data API no disponible ({exc}) — se baja el archivo.", file=sys.stderr)

        if result is None:
            live_url = resource.get("url")
            if live_url:
                try:
                    resp = http_get(live_url)
                    data = resp.read()
                    print(f"  {len(data):,} bytes descargados (URL en vivo)", file=sys.stderr)
                    result = process_csv(data)
                    result["metodo"] = "descarga_url_en_vivo"
                    result["estado"] = "ok"
                    result["csv_url"] = live_url
                except Exception as exc:
                    print(f"  Descarga de la URL en vivo falló ({exc}) — se usará la URL fija.", file=sys.stderr)

    if result is None:
        print("Descargando muestra RENAMU 2023 (URL fija) ...", file=sys.stderr)
        try:
            resp = http_get(CSV_URL)
            data = resp.read()
            print(f"  {len(data):,} bytes descargados", file=sys.stderr)
            result = process_csv(data)
            result["metodo"] = "descarga_url_fija"
            result["estado"] = "ok"
            result["csv_url"] = CSV_URL
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            result = {"estado": "error", "error": str(exc), "csv_url": CSV_URL}

    summary = {
        "fuente": "INEI — Registro Nacional de Municipalidades (RENAMU) 2023, muestra",
        "atribucion": "Instituto Nacional de Estadística e Informática (INEI), vía Portal Nacional de Datos Abiertos.",
        "dataset_url": DATASET_URL,
        "nota": "Esta es la 'data de muestra' publicada por el portal, no el registro completo — más rápida de procesar para esta primera versión. La data completa está en un .zip servido por INEI, pendiente de una segunda fase.",
        **result,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, summary)


if __name__ == "__main__":
    main()
