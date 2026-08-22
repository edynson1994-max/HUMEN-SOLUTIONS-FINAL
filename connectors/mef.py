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

SOBRE LA DATA API (datastore) — por qué este conector NO la usa
------------------------------------------------------------------
El instructivo oficial confirma que existe una Data API real por recurso
(ver el aviso en common.py) — pero paginar ~millones de filas a través de
esa API sería mucho más lento (y más peticiones HTTP) que un solo streaming
del CSV, que es lo que ya hace este conector de forma eficiente. Por eso
aquí solo se usa `package_show` para refrescar la URL de descarga (por si
la fija de abajo quedó desactualizada), no para leer los datos en sí.
"""

import csv
import io
import os
import sys
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(__file__))
from common import detect_column, find_resource, http_get, normalize, package_show, write_summary

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mef.json")

DATASET_URL = "https://www.datosabiertos.gob.pe/dataset/presupuesto-y-ejecuci%C3%B3n-de-gasto-%E2%80%93-devengado-mensual"
CSV_URL = "https://fs.datosabiertos.mef.gob.pe/datastorefiles/2025-Gasto-Devengado-Mensual.csv"


def dataset_slug(dataset_url):
    path = urlparse(dataset_url).path
    return unquote(path.rstrip("/").split("/")[-1])


def resolve_csv_url():
    """Intenta refrescar la URL vía package_show; si falla por cualquier
    motivo, cae a la URL fija verificada manualmente. Nunca lanza."""
    try:
        pkg = package_show(dataset_slug(DATASET_URL))
        resource = find_resource(pkg, formato="csv")
        if resource and resource.get("url"):
            return resource["url"], "package_show"
    except Exception as exc:
        print(f"package_show falló ({exc}) — se usará la URL fija.", file=sys.stderr)
    return CSV_URL, "url_fija"

# IMPORTANTE — corregido tras ver datos reales (corrida real del
# 2026-08-22): el archivo real viene en formato "ancho": una columna de
# CÓDIGO y otra de NOMBRE para región/entidad (ej. DEPARTAMENTO_EJECUTORA
# vs DEPARTAMENTO_EJECUTORA_NOMBRE), y el monto NO es una sola columna —
# son 12 columnas mensuales (MONTO_DEVENGADO_ENERO..DICIEMBRE) más una
# columna MONTO_DEVENGADO_ANUAL con el total del año. La primera versión
# de este conector no sabía esto (se escribió sin poder ver el archivo) y
# por eso agarraba la columna de CÓDIGO en vez de NOMBRE, y el monto de
# ENERO en vez del total anual — ambos ya corregidos: los candidatos más
# específicos van primero para que el emparejamiento por substring de
# detect_column() los encuentre antes que la variante genérica/de código.
REGION_CANDIDATES = ["departamento_ejecutora_nombre", "nombre departamento", "departamento_nombre", "departamento", "region", "dpto"]
MONTO_ANUAL_CANDIDATES = ["monto_devengado_anual", "devengado_anual", "monto devengado anual"]
ENTIDAD_CANDIDATES = ["pliego_nombre", "nombre pliego", "entidad_nombre", "entidad", "pliego", "unidad ejecutora"]

# Nombres reales de los 12 meses tal como aparecen en las columnas
# MONTO_DEVENGADO_<MES> — se usan para armar una serie mensual nacional
# (útil para un gráfico de tendencia real en vez de inventar una).
MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
         "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


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
    especifica (modo muestra).

    Windows-1252, no UTF-8: se confirmó con datos reales de este mismo
    portal (ver smart_decode en common.py) que estos CSV de entidades
    peruanas vienen en cp1252 — se usa ese encoding acá también aunque el
    encabezado de este archivo en particular resultó ser ASCII puro (así
    que no se notaba), por si las columnas *_NOMBRE traen tildes/ñ."""
    raw = resp  # objeto tipo file-like devuelto por urllib
    text_stream = io.TextIOWrapper(raw, encoding="cp1252", errors="replace", newline="")

    # Sniff manual de la primera línea para detectar el delimitador, sin
    # tener que leer todo el archivo en memoria para csv.Sniffer.
    first_line = text_stream.readline()
    delim = "|" if first_line.count("|") > first_line.count(",") else ","
    fieldnames = next(csv.reader(io.StringIO(first_line), delimiter=delim))

    region_col = detect_column(fieldnames, REGION_CANDIDATES)
    monto_anual_col = detect_column(fieldnames, MONTO_ANUAL_CANDIDATES)
    entidad_col = detect_column(fieldnames, ENTIDAD_CANDIDATES)

    # Columnas mensuales: se buscan por nombre exacto de mes (no por
    # substring genérico) para no confundirlas entre sí ni con la anual.
    mes_cols = {}
    for mes in MESES:
        col = detect_column(fieldnames, [f"monto_devengado_{mes.lower()}"])
        if col:
            mes_cols[mes] = col

    reader = csv.DictReader(text_stream, fieldnames=fieldnames, delimiter=delim)

    total_filas = 0
    total_monto = 0.0
    filas_con_monto = 0
    por_region = {}
    gasto_mensual_nacional = {mes: 0.0 for mes in mes_cols}
    bytes_leidos = len(first_line.encode("cp1252", errors="replace"))
    truncado = False

    for row in reader:
        total_filas += 1
        if monto_anual_col:
            monto = parse_amount(row.get(monto_anual_col))
            if monto is not None:
                total_monto += monto
                filas_con_monto += 1
                if region_col:
                    region = (row.get(region_col) or "No especificado").strip().title()
                    por_region[region] = por_region.get(region, 0.0) + monto

        for mes, col in mes_cols.items():
            m = parse_amount(row.get(col))
            if m is not None:
                gasto_mensual_nacional[mes] += m

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
        "columna_monto_anual_usada": monto_anual_col,
        "columna_entidad_usada": entidad_col,
        "meses_detectados": list(mes_cols.keys()),
        "filas_leidas": total_filas,
        "filas_con_monto_valido": filas_con_monto,
        "monto_devengado_total": round(total_monto, 2) if monto_anual_col else None,
        "top_regiones_por_monto": (
            [{"region": r, "monto_devengado": round(m, 2)} for r, m in top_regiones]
            if region_col and monto_anual_col else None
        ),
        "gasto_mensual_nacional": (
            [{"mes": mes, "monto_devengado": round(gasto_mensual_nacional[mes], 2)} for mes in MESES if mes in gasto_mensual_nacional]
            if mes_cols else None
        ),
        "muestra_parcial": truncado,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-mb", type=float, default=None, help="Cortar la lectura a los primeros N MB (para pruebas rápidas; el resultado será una muestra parcial).")
    args = parser.parse_args()
    max_bytes = int(args.max_mb * 1024 * 1024) if args.max_mb else None

    csv_url, url_origen = resolve_csv_url()
    print(f"Descargando (streaming) {csv_url} [{url_origen}] ...", file=sys.stderr)
    try:
        resp = http_get(csv_url, timeout=300, max_retries=2)
        result = stream_process(resp, max_bytes=max_bytes)
        result["estado"] = "ok"
        result["url_origen"] = url_origen
    except Exception as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        result = {"estado": "error", "error": str(exc), "url_origen": url_origen}

    summary = {
        "fuente": "MEF — Presupuesto y Ejecución de Gasto (Devengado Mensual) 2025",
        "atribucion": "Ministerio de Economía y Finanzas (MEF), vía Portal Nacional de Datos Abiertos.",
        "dataset_url": DATASET_URL,
        "csv_url": csv_url,
        **result,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, summary)


if __name__ == "__main__":
    main()
