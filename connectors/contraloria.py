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

ESTRATEGIA DE 3 NIVELES (ver aviso "Data API" en common.py)
-------------------------------------------------------------
Para cada dataset se intenta, en orden, cayendo al siguiente solo si el
anterior falla:

  1. Data API real (datastore/search.json) sobre el resource_id que
     devuelve package_show — la vía más limpia, sin parsear CSV a mano,
     PERO solo funciona si ese recurso se registró con datastore activado.
  2. Descarga directa de la URL que package_show reporta como actual para
     ese recurso (más confiable que una URL fija porque viene de la fuente
     de verdad en el momento de la corrida, no de lo que se capturó al
     escribir este conector).
  3. Descarga directa de la URL fija verificada abajo (csv_url), por si
     package_show mismo falla (por ejemplo si el "slug" del dataset
     cambió).

En cualquiera de los 3 casos, las columnas se detectan en tiempo de
ejecución, nunca se asumen fijas — y el resultado incluye "metodo" para
que quede claro cuál de los 3 niveles funcionó en cada corrida real.
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
    normalize,
    package_show,
    sniff_csv_reader,
    write_summary,
)

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


def dataset_slug(dataset_url):
    """El 'id' que espera package_show — el último segmento de la URL del
    dataset, decodificado (el propio portal usa el alias con acentos
    codificados como parte del slug, ej. 'informaci%C3%B3n-general-...')."""
    path = urlparse(dataset_url).path
    return unquote(path.rstrip("/").split("/")[-1])


def process_rows(rows, fieldnames, titulo):
    """Núcleo de la agregación — funciona igual si las filas vinieron de
    parsear un CSV a mano o ya vinieron como dicts de la Data API."""
    region_col = detect_column(fieldnames, REGION_CANDIDATES)
    fecha_col = detect_column(fieldnames, FECHA_CANDIDATES)

    total = 0
    por_region = {}
    for row in rows:
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


def process_csv(csv_bytes, titulo):
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = sniff_csv_reader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    return process_rows(reader, fieldnames, titulo)


def procesar_dataset(ds):
    """Intenta los 3 niveles en orden. Devuelve el dict de resultado (con
    'estado' y 'metodo') — nunca lanza, cualquier fallo total queda
    reflejado como estado":"error"."""

    # Nivel 1 y 2 dependen de package_show — si eso falla, se salta directo
    # al nivel 3 con la URL fija.
    resource = None
    try:
        slug = dataset_slug(ds["dataset_url"])
        pkg = package_show(slug)
        resource = find_resource(pkg, formato="csv")
    except Exception as exc:
        print(f"  package_show falló para {ds['titulo']} ({exc}) — se usará la URL fija.", file=sys.stderr)

    if resource is not None:
        # Nivel 1: Data API (datastore) sobre el resource_id real.
        try:
            resource_id = resource.get("id")
            print(f"  Probando Data API (datastore) para resource_id={resource_id} ...", file=sys.stderr)
            ds_data = datastore_search_all(resource_id)
            if not ds_data["records"]:
                raise RuntimeError("la Data API respondió sin registros")
            parsed = process_rows(ds_data["records"], ds_data["fields"], ds["titulo"])
            parsed["metodo"] = "data_api"
            parsed["resource_id"] = resource_id
            parsed["estado"] = "ok"
            return {**parsed, "dataset_url": ds["dataset_url"], "csv_url": ds["csv_url"]}
        except Exception as exc:
            print(f"  Data API no disponible para este recurso ({exc}) — se baja el archivo.", file=sys.stderr)

        # Nivel 2: URL en vivo que reporta package_show para ese recurso.
        live_url = resource.get("url")
        if live_url:
            try:
                resp = http_get(live_url)
                data = resp.read()
                print(f"  {len(data):,} bytes descargados (URL en vivo)", file=sys.stderr)
                parsed = process_csv(data, ds["titulo"])
                parsed["metodo"] = "descarga_url_en_vivo"
                parsed["estado"] = "ok"
                return {**parsed, "dataset_url": ds["dataset_url"], "csv_url": live_url}
            except Exception as exc:
                print(f"  Descarga de la URL en vivo falló ({exc}) — se usará la URL fija.", file=sys.stderr)

    # Nivel 3: URL fija verificada manualmente (último recurso).
    try:
        resp = http_get(ds["csv_url"])
        data = resp.read()
        print(f"  {len(data):,} bytes descargados (URL fija)", file=sys.stderr)
        parsed = process_csv(data, ds["titulo"])
        parsed["metodo"] = "descarga_url_fija"
        parsed["estado"] = "ok"
        return {**parsed, "dataset_url": ds["dataset_url"], "csv_url": ds["csv_url"]}
    except Exception as exc:
        print(f"  ERROR con {ds['titulo']}: {exc}", file=sys.stderr)
        return {
            "titulo": ds["titulo"],
            "dataset_url": ds["dataset_url"],
            "csv_url": ds["csv_url"],
            "estado": "error",
            "error": str(exc),
        }


def main():
    results = []
    for ds in DATASETS:
        print(f"Procesando {ds['titulo']} ...", file=sys.stderr)
        results.append(procesar_dataset(ds))

    summary = {
        "fuente": "Contraloría General de la República — Monitores Ciudadanos de Control",
        "atribucion": "Datos publicados por la Contraloría General de la República en el Portal Nacional de Datos Abiertos (PNDA).",
        "datasets": results,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, summary)


if __name__ == "__main__":
    main()
