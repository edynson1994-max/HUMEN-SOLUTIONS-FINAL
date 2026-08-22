#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
csv_to_data.py — Convierte una exportación CSV descargada a mano desde el
portal oficial "Oportunidades de Negocio" del SEACE/OECE
(https://prod4.seace.gob.pe/openegocio/#/georeferenciacion, botón "CSV") al mismo
data.json que consume index.html.

Es la ruta MANUAL de actualización: no depende de que ningún servidor externo
deje pasar descargas automáticas (el mirror OCDS que usa sync.py sí está
automatizado, pero esta fuente es más completa y más "en vivo" porque es la
oficial). Cuando quieras refrescar los datos con esta fuente:

  1. Entra a https://prod4.seace.gob.pe/openegocio/#/georeferenciacion
  2. Aplica los filtros que quieras (o ninguno) y dale clic a "CSV".
  3. Corre este script sobre el archivo descargado:

     python3 csv_to_data.py archivo1.csv [archivo2.csv ...] --region "Cusco"

     El --region se aplica solo a las filas donde no se pudo adivinar la
     región a partir del nombre de la entidad (ver REGIONES abajo). Si
     descargaste varios departamentos por separado, corre el script una vez
     por archivo con su --region correspondiente, o pásalos todos juntos si
     el archivo ya mezcla regiones y confías en la detección automática.

FORMATO DE ORIGEN
------------------
El CSV real que exporta el portal usa "|" como separador, viene con BOM UTF-8,
y (importante) trae una fila por ITEM del proceso, no una fila por proceso —
un proceso con 3 ítems aparece en 3 filas que comparten el mismo identificador
interno (columna 17, un UUID) y la misma "Nomenclatura del proceso". Este
script agrupa por ese identificador para mostrar UNA tarjeta por convocatoria,
no una por cada ítem.

La cabecera que trae el propio archivo no coincide en cantidad de columnas con
los datos reales (quedaron algunas etiquetas de más, aparentemente un defecto
del exportador del portal) — por eso este script identifica cada columna por
POSICIÓN, verificada contra un archivo real, en vez de confiar en la cabecera.
Si el portal cambia el formato de exportación en el futuro y este script deja
de funcionar, avisa para reajustar las posiciones.
"""

import argparse
import csv
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data.json")
SOURCE_LABEL = "SEACE / Oportunidades de Negocio (exportación oficial CSV)"
SOURCE_URL = "https://prod4.seace.gob.pe/openegocio/#/georeferenciacion"

ATTRIBUTION = (
    "Datos exportados manualmente desde el portal oficial Oportunidades de "
    "Negocio del organismo peruano a cargo del SEACE. Banco de información "
    "pública — no requiere afiliación con Humen Solutions para consultarlo."
)

# Posiciones verificadas contra un archivo real (ver docstring arriba).
COL = {
    "entidad": 0,
    "tipo_proceso": 1,
    "modalidad": 2,
    "sintesis": 6,
    "nomenclatura": 7,
    "detalle_objeto": 8,
    "monto_a": 9,
    "moneda_a": 10,
    "fecha_convocatoria": 11,
    "fecha_fin_registro": 13,
    "proceso_id": 16,
    "detalle_item": 18,
    "moneda_item": 21,
    "monto_b": 23,
}
MIN_COLUMNS = 24

FALLBACK_LOOKBACK_DAYS = 30

HUMEN_KEYWORDS = {
    "cont": [
        "contabilidad", "contable", "auditoria", "auditor",
        "estados financieros", "balance general", "conciliacion",
        "tributari", "presupuestal",
    ],
    "inv": [
        "inventario fisico", "toma de inventario", "bienes patrimoniales",
        "control patrimonial", "activos fijos", "existencias de almacen",
        "saneamiento patrimonial", "codificacion de activos",
        "verificacion fisica",
    ],
    "rec": [
        "reclutamiento", "seleccion de personal", "evaluacion psicolaboral",
        "intermediacion laboral", "convocatoria cas", "gestion de personal",
        "bolsa de trabajo", "proceso de seleccion", "personal cas",
    ],
}

PROC_CATEGORY_MAP = {
    "bien": "Bienes",
    "servicio": "Servicios",
    "obra": "Obras",
    "consultoria de obra": "Consultoría de Obras",
}

# Departamentos del Perú, para adivinar la región a partir del nombre de la
# entidad cuando el archivo no trae una columna de región explícita.
REGIONES = [
    "Amazonas", "Ancash", "Apurimac", "Arequipa", "Ayacucho", "Cajamarca",
    "Callao", "Cusco", "Huancavelica", "Huanuco", "Ica", "Junin",
    "La Libertad", "Lambayeque", "Lima", "Loreto", "Madre de Dios",
    "Moquegua", "Pasco", "Piura", "Puno", "San Martin", "Tacna", "Tumbes",
    "Ucayali",
]


def clean_text(text):
    """El exportador del portal corrompe algunos caracteres especiales (comillas,
    ñ, guiones) como '¿' sueltos dentro del texto — nunca son signos de
    interrogación reales en estos títulos, así que se eliminan junto con
    espacios duplicados que puedan quedar."""
    if not text:
        return text
    text = text.replace("¿", "")
    text = " ".join(text.split())
    return text.strip()


def normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def guess_region(entidad, default_region):
    hay = normalize(entidad)
    for region in REGIONES:
        if normalize(region) in hay:
            return region
    return default_region or "No especificado"


def match_humen_tags(*texts):
    haystack = normalize(" ".join(t for t in texts if t))
    tags = []
    for tag, words in HUMEN_KEYWORDS.items():
        if any(w in haystack for w in words):
            tags.append(tag)
    return tags


def parse_dt(value):
    value = (value or "").strip()
    if not value or value.lower() == "null":
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(value, "%d/%m/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def parse_amount(value):
    value = (value or "").strip().replace(",", "")
    if not value or value == "---":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_csv_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="|")
        rows = list(reader)
    if not rows:
        return []
    data_rows = [r for r in rows[1:] if len(r) >= MIN_COLUMNS]
    skipped = len(rows) - 1 - len(data_rows)
    if skipped:
        print(f"  ({skipped} filas de {path} se omitieron por tener menos columnas de las esperadas)", file=sys.stderr)
    return data_rows


def group_rows(rows):
    """Agrupa las filas de ítem por proceso (mismo id interno)."""
    groups = {}
    order = []
    for r in rows:
        key = r[COL["proceso_id"]] or r[COL["nomenclatura"]]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)
    return [groups[k] for k in order]


def build_item(group, default_region):
    head = group[0]

    entidad = clean_text(head[COL["entidad"]])
    tipo_proceso = head[COL["tipo_proceso"]].strip()
    sintesis = clean_text(head[COL["sintesis"]])
    nomenclatura = head[COL["nomenclatura"]].strip()
    detalle_objeto = normalize(head[COL["detalle_objeto"]].strip())

    due_dt = parse_dt(head[COL["fecha_fin_registro"]])
    pub_dt = parse_dt(head[COL["fecha_convocatoria"]])

    # Mismo criterio de vigencia que sync.py: si hay fecha límite y ya pasó,
    # fuera. Si no hay fecha límite, exigir publicación reciente.
    now = datetime.now(timezone.utc)
    if due_dt is not None:
        if due_dt.date() < now.date():
            return None
    else:
        if pub_dt is None or (now - pub_dt).days > FALLBACK_LOOKBACK_DAYS:
            return None

    amount = None
    currency = None
    for row in group:
        for amt_col, cur_col in ((COL["monto_a"], COL["moneda_a"]), (COL["monto_b"], COL["moneda_item"])):
            if amount is None:
                a = parse_amount(row[amt_col])
                if a is not None:
                    amount = a
                    currency = row[cur_col].strip() if cur_col < len(row) else None

    if currency:
        currency_norm = normalize(currency)
        currency = "PEN" if "sol" in currency_norm else ("USD" if "dolar" in currency_norm else currency)
    else:
        currency = "PEN"

    objeto = sintesis
    if len(group) == 1:
        detalle_item = clean_text(head[COL["detalle_item"]]) if COL["detalle_item"] < len(head) else ""
        if detalle_item and detalle_item not in ("---", sintesis):
            objeto = f"{sintesis} — {detalle_item}"

    humen_tags = match_humen_tags(sintesis, *(g[COL["detalle_item"]] for g in group if COL["detalle_item"] < len(g)))

    return {
        "id": head[COL["proceso_id"]] or nomenclatura,
        "procCategory": PROC_CATEGORY_MAP.get(detalle_objeto, "No especificado"),
        "humenTags": humen_tags,
        "title": sintesis or nomenclatura,
        "entidad": entidad or "Entidad no especificada",
        "region": guess_region(entidad, default_region),
        "tipoProc": tipo_proceso or "No especificado",
        "code": nomenclatura,
        "monto": amount,
        "moneda": currency,
        "pubDate": pub_dt.strftime("%Y-%m-%d") if pub_dt else None,
        "dueDate": due_dt.strftime("%Y-%m-%d") if due_dt else None,
        "objeto": objeto,
        "url": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_files", nargs="+", help="Uno o más archivos CSV exportados del portal.")
    parser.add_argument("--region", default=None, help="Región a usar cuando no se pueda adivinar del nombre de la entidad.")
    args = parser.parse_args()

    all_rows = []
    for path in args.csv_files:
        print(f"Leyendo {path} ...", file=sys.stderr)
        rows = read_csv_rows(path)
        print(f"  {len(rows)} filas de ítem", file=sys.stderr)
        all_rows.extend(rows)

    groups = group_rows(all_rows)
    print(f"{len(groups)} procesos únicos detectados", file=sys.stderr)

    items = []
    seen = {}
    for group in groups:
        item = build_item(group, args.region)
        if item is None:
            continue
        key = item["id"]
        if key not in seen:
            seen[key] = item
            items.append(item)

    items.sort(key=lambda r: (r["dueDate"] is None, r["dueDate"] or ""))

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
        "dropped_by_cap": 0,
        "items": items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Listo: {len(items)} convocatorias vigentes guardadas en {OUTPUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
