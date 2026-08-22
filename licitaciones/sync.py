#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py — Sincroniza convocatorias de licitación relevantes para Humen Solutions SACS
(contabilidad y auditoría, inventarios físicos, reclutamiento de personal) a partir de
los datos abiertos de contrataciones públicas del Perú.

FUENTE DE DATOS
----------------
No se consulta directamente al SEACE (ese portal no expone una API pública estable y
bloquea el acceso automático). En su lugar se usa el mirror oficial en formato OCDS
(Open Contracting Data Standard) publicado por Open Contracting Partnership, que se
actualiza a diario a partir de la misma fuente:

    https://data.open-contracting.org/en/publication/135

Descarga masiva por año, formato JSON Lines comprimido:
    https://data.open-contracting.org/en/publication/135/download?name=<AÑO>.jsonl.gz

Licencia: Creative Commons Attribution 4.0 International (CC BY 4.0) — se debe
mantener la atribución a la fuente (ver ATTRIBUTION más abajo).

QUÉ HACE ESTE SCRIPT
---------------------
1. Descarga el archivo del año en curso (y, en enero, también el del año anterior,
   para no perder procesos que sigan vigentes de diciembre).
2. Recorre cada "release" OCDS línea por línea.
3. Se queda solo con procesos cuyo título/descripción coincide con las palabras clave
   de las 3 líneas de negocio de Humen Solutions.
4. Filtra procesos que ya cerraron (cuando el dato de fecha límite está disponible).
5. Escribe licitaciones/data.json con una estructura simple que consume index.html.
6. Guarda además sample_raw_release.json con UN registro crudo de ejemplo, para poder
   ajustar el mapeo de campos si el esquema real difiere de lo asumido aquí (ver nota
   al final de este archivo).

IMPORTANTE — AJUSTE PENDIENTE EN LA PRIMERA CORRIDA REAL
-----------------------------------------------------------
Este script fue escrito sin poder probarlo contra un archivo real (el entorno donde se
escribió no tiene salida a internet hacia estos dominios). La extracción de campos
(región, tipo de proceso, etc.) sigue la estructura estándar de OCDS y hace fallback a
"No especificado" cuando un campo no existe, así que no debería romperse — pero conviene
revisar sample_raw_release.json después de la primera corrida real en GitHub Actions
para confirmar que los campos se están leyendo del lugar correcto y afinar el mapeo si
hace falta.
"""

import gzip
import io
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

import requests

BASE_URL = "https://data.open-contracting.org/en/publication/135/download"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data.json")
SAMPLE_RAW_PATH = os.path.join(os.path.dirname(__file__), "sample_raw_release.json")

ATTRIBUTION = (
    "Datos derivados del Registro de Datos Abiertos de Contrataciones "
    "(Open Contracting Partnership), a partir de información publicada por el "
    "organismo peruano a cargo del SEACE. Licencia CC BY 4.0."
)

# Máximo de convocatorias a conservar por categoría (evita un data.json gigante).
MAX_PER_CATEGORY = 150

# Días hacia atrás a considerar "reciente" si un proceso no trae fecha de publicación.
FALLBACK_LOOKBACK_DAYS = 30

KEYWORDS = {
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

CATEGORY_LABELS = {
    "cont": "Contabilidad y Auditoría",
    "inv": "Inventarios Físicos",
    "rec": "Reclutamiento y Personal",
}

CLOSED_STATUSES = {"complete", "cancelled", "unsuccessful", "withdrawn"}


def normalize(text):
    """minúsculas y sin tildes, para comparar palabras clave sin depender de acentos."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def match_category(title, description):
    haystack = normalize((title or "") + " " + (description or ""))
    for cat, words in KEYWORDS.items():
        for w in words:
            if w in haystack:
                return cat
    return None


def download_year(year, session):
    url = f"{BASE_URL}?name={year}.jsonl.gz"
    resp = session.get(url, stream=True, timeout=120)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return gzip.GzipFile(fileobj=io.BytesIO(resp.content))


def get_buyer_region(release):
    buyer = release.get("buyer") or {}
    buyer_id = buyer.get("id")
    for party in release.get("parties") or []:
        if buyer_id and party.get("id") == buyer_id:
            address = party.get("address") or {}
            return address.get("region") or address.get("locality") or None
        if not buyer_id and "buyer" in (party.get("roles") or []):
            address = party.get("address") or {}
            return address.get("region") or address.get("locality") or None
    return None


def get_document_url(tender):
    for doc in tender.get("documents") or []:
        if doc.get("url"):
            return doc["url"]
    return None


def parse_release(release):
    tender = release.get("tender") or {}
    status = (tender.get("status") or "").lower()
    if status in CLOSED_STATUSES:
        return None

    title = tender.get("title") or release.get("title") or ""
    description = tender.get("description") or ""
    cat = match_category(title, description)
    if cat is None:
        return None

    due_date = None
    tender_period = tender.get("tenderPeriod") or {}
    if tender_period.get("endDate"):
        due_date = tender_period["endDate"][:10]

    pub_date = None
    if release.get("date"):
        pub_date = release["date"][:10]

    # Si no hay fecha límite conocida, exigimos que sea razonablemente reciente
    # para no arrastrar procesos históricos ya cerrados sin marcarlo explícitamente.
    if due_date is None and pub_date:
        try:
            pub_dt = datetime.strptime(pub_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - pub_dt).days
            if age_days > FALLBACK_LOOKBACK_DAYS:
                return None
        except ValueError:
            pass

    value = tender.get("value") or {}
    buyer_name = (release.get("buyer") or {}).get("name") or "Entidad no especificada"

    return {
        "id": release.get("ocid") or release.get("id"),
        "cat": cat,
        "title": title.strip(),
        "entidad": buyer_name,
        "region": get_buyer_region(release) or "No especificado",
        "tipoProc": tender.get("procurementMethodDetails") or tender.get("procurementMethod") or "No especificado",
        "code": tender.get("id") or release.get("ocid") or "",
        "monto": value.get("amount"),
        "moneda": value.get("currency") or "PEN",
        "pubDate": pub_date,
        "dueDate": due_date,
        "objeto": description.strip() or title.strip(),
        "url": get_document_url(tender),
    }


def collect(years):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "HumenSolutions-LicitacionesSync/1.0 (+contacto empresa)"
    })

    by_cat = {"cont": [], "inv": [], "rec": []}
    sample_saved = False

    for year in years:
        print(f"Descargando {year}.jsonl.gz ...", file=sys.stderr)
        gz = download_year(year, session)
        if gz is None:
            print(f"  (sin archivo para {year}, se omite)", file=sys.stderr)
            continue

        count = 0
        for raw_line in gz:
            count += 1
            try:
                release = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            if not sample_saved:
                with open(SAMPLE_RAW_PATH, "w", encoding="utf-8") as f:
                    json.dump(release, f, ensure_ascii=False, indent=2)
                sample_saved = True

            item = parse_release(release)
            if item:
                by_cat[item["cat"]].append(item)

        print(f"  {count} registros revisados en {year}", file=sys.stderr)

    return by_cat


def main():
    now = datetime.now(timezone.utc)
    years = [now.year]
    if now.month == 1:
        years.append(now.year - 1)

    by_cat = collect(years)

    items = []
    for cat, records in by_cat.items():
        records.sort(key=lambda r: (r["dueDate"] is None, r["dueDate"] or ""))
        items.extend(records[:MAX_PER_CATEGORY])

    output = {
        "generated_at": now.isoformat(timespec="seconds"),
        "attribution": ATTRIBUTION,
        "source_url": "https://data.open-contracting.org/en/publication/135",
        "counts": {cat: len(recs[:MAX_PER_CATEGORY]) for cat, recs in by_cat.items()},
        "items": items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Listo: {len(items)} convocatorias guardadas en {OUTPUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
