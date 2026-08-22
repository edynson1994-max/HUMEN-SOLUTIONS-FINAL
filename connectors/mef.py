#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mef.py — Conector para datos de ejecución de gasto público del MEF,
publicados en el Portal Nacional de Datos Abiertos (PNDA).

FUENTE Y VERIFICACIÓN
----------------------
Dataset (página verificada):
  https://www.datosabiertos.gob.pe/dataset/presupuesto-y-ejecuci%C3%B3n-de-gasto-%E2%80%93-devengado-mensual

Archivo confirmado como real y descargable (servido por el propio MEF, no
por datosabiertos.gob.pe):
  https://fs.datosabiertos.mef.gob.pe/datastorefiles/2025-Gasto-Devengado-Mensual.csv

ADVERTENCIA — RIESGO MÁS ALTO QUE LOS OTROS CONECTORES
-----------------------------------------------------------
Este archivo pesa ~2.3 GB. No se pudo verificar su contenido/columnas desde
el entorno donde se escribió esto (sin salida de red hacia el dominio), así
que:

  1. La detección de columnas es 100% dinámica (ver common.py) — nada de
     nombres de columna está hardcodeado como verdad asumida.
  2. NO se carga el archivo completo en memoria en ningún momento — se
     procesa línea por línea en streaming y solo se acumulan sumas/conteos
     (un diccionario pequeño por región), así que el uso de memoria se
     mantiene bajo sin importar el tamaño del archivo.
  3. Por defecto SÍ procesa el archivo completo (puede tardar varios
     minutos en GitHub Actions, con timeout generoso). Para pruebas rápidas
     o si el runner tiene problemas de tiempo/red, usa --max-mb para cortar
     la descarga a los primeros N megabytes (el resultado será una muestra
     parcial, no el total real — se marca explícitamente como tal en el
     JSON de salida).
  4. La API package_show de un recurso de este MEF confirmó al menos un
     enlace roto (404) en otro archivo del mismo catálogo durante la
     investigación — por eso este conector valida el status HTTP antes de
     comprometerse a procesar, y reporta error explícito si el archivo no
     responde, en vez de fallar silenciosamente.
"""

import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import detect_column, http_get, normalize, write_summary

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mef.json")

DATASET_URL = "https://www.datosabiertos.gob.pe/dataset/presupuesto-y-ejecuci%C3%B3n-de-gasto-%E2%80%93-devengado-mensual"
CSV_URL = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/2025-Gasto-Devengado-Mensual.csv"

REGION_CANDIDATES = ["departamento", "region", "dpto", "nombre departamento"]
MONTO_CANDIDATES = ["monto devengado", "devengado", "monto_devengado", "importe devengado"]
MES_CANDIDATES = ["mes", "mes_eje", "periodo"]
ENTIDAD_CANDIDATES = ["entidad", "pliego", "nombre pliego", "unidad ejecutora"]


def parse_amount(value):
    if value is None:
        return None
    value = str(value).strip().replace(",", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def stream_process(resp, max_bytes=None):
    """Lee la respuesta HTTP línea por línea (streaming real, sin cargar todo
    en memoria) y va acumulando sumas por región. Corta en max_bytes si se
    especifica (modo muestra)."""
    raw = resp  # objeto tipo file-like devuelto por urllib
    text_stream = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")

    # Sniff manual de la primera línea para detectar el delimitador, sin
    # tener que leer todo el archivo en memoria para csv.Sniffer.
    first_line = text_stream.readline()
    delim = "|" if first_line.count("|") > first_line.count(",") else ","
    fieldnames = next(csv.reader(io.StringIO(first_line), delimiter=delim))

    region_col = detect_column(fieldnames, REGION_CANDIDATES)
    monto_col = detect_column(fieldnames, MONTO_CANDIDATES)
    mes_col = detect_column(fieldnames, MES_CANDIDATES)
    entidad_col = detect_column(fieldnames, ENTIDAD_CANDIDATES)

    reader = csv.DictReader(text_stream, fieldnames=fieldnames, delimiter=delim)

    total_filas = 0
    total_monto = 0.0
    filas_con_monto = 0
    por_region = {}
    bytes_leidos = len(first_line.encode("utf-8"))
    truncado = False

    for row in reader:
        total_filas += 1
        if monto_col:
            monto = parse_amount(row.get(monto_col))
            if monto is not None:
                total_monto += monto
                filas_con_monto += 1
                if region_col:
                    region = (row.get(region_col) or "No especificado").strip().title()
                    por_region[region] = por_region.get(region, 0.0) + monto

        if max_bytes:
            # Estimación aproximada del avance leído (no exacta, pero evita
            # tener que instrumentar cada línea con su tamaño en bytes real).
            bytes_leidos += sum(len(str(v or "")) for v in row.values()) + len(row)
            if bytes_leidos >= max_bytes:
                truncado = True
                break

    top_regiones = sorted(por_region.items(), key=lambda kv: -kv[1])[:15]

    return {
        "columnas_detectadas": fieldnames,
        "columna_region_usada": region_col,
        "columna_monto_usada": monto_col,
        "columna_mes_usada": mes_col,
        "columna_entidad_usada": entidad_col,
        "filas_leidas": total_filas,
        "filas_con_monto_valido": filas_con_monto,
        "monto_devengado_total": round(total_monto, 2) if monto_col else None,
        "top_regiones_por_monto": (
            [{"region": r, "monto_devengado": round(m, 2)} for r, m in top_regiones]
            if region_col and monto_col else None
        ),
        "muestra_parcial": truncado,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-mb", type=float, default=None, help="Cortar la lectura a los primeros N MB (para pruebas rápidas; el resultado será una muestra parcial).")
    args = parser.parse_args()
    max_bytes = int(args.max_mb * 1024 * 1024) if args.max_mb else None

    print(f"Descargando (streaming) {CSV_URL} ...", file=sys.stderr)
    try:
        resp = http_get(CSV_URL, timeout=300, max_retries=2)
        result = stream_process(resp, max_bytes=max_bytes)
        result["estado"] = "ok"
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        result = {"estado": "error", "error": str(exc)}

    summary = {
        "fuente": "MEF — Presupuesto y Ejecución de Gasto (Devengado Mensual) 2025",
        "atribucion": "Ministerio de Economía y Finanzas (MEF), vía Portal Nacional de Datos Abiertos.",
        "dataset_url": DATASET_URL,
        "csv_url": CSV_URL,
        **result,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, summary)


if __name__ == "__main__":
    main()
