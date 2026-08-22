#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py — Sincroniza TODAS las convocatorias de licitación pública vigentes del
Perú, como banco de información pública abierto a cualquiera (no solo a Humen
Solutions SACS). Las convocatorias afines a las 3 líneas de negocio de Humen
(contabilidad y auditoría, inventarios físicos, reclutamiento de personal)
quedan marcadas con una etiqueta informativa, pero ya NO se usan para excluir
al resto — todo lo demás también se publica.

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
1. Descarga el archivo del año en curso y el del año anterior (para no perder
   procesos que sigan vigentes pero cuyo "release" en OCDS quedó registrado el
   año pasado).
2. Recorre cada "release" OCDS línea por línea.
3. Descarta lo que ya cerró: si hay fecha límite y ya pasó, fuera — sin
   depender del campo "status" (poco confiable en registros migrados).
4. A lo que queda abierto, le asigna una categoría de contratación (Bienes /
   Servicios / Obras / Consultoría de Obras) tomada del propio estándar OCDS,
   y además una o más etiquetas "humenTags" si el título/descripción coincide
   con palabras clave de contabilidad, inventarios físicos o reclutamiento —
   solo como distintivo visual, no como filtro de exclusión.
5. Escribe licitaciones/data.json con una estructura simple que consume index.html.
6. Guarda además sample_raw_release.json con UN registro crudo de ejemplo, para
   poder ajustar el mapeo de campos si el esquema real difiere del asumido aquí.

IMPORTANTE — AJUSTE PENDIENTE EN LA PRIMERA CORRIDA REAL
-----------------------------------------------------------
Este script fue escrito sin poder probarlo contra un archivo real (el entorno donde se
escribió no tiene salida a internet hacia estos dominios). La extracción de campos
(región, tipo de proceso, etc.) sigue la estructura estándar de OCDS y hace fallback a
"No especificado" cuando un campo no existe, así que no debería romperse — pero conviene
revisar sample_raw_release.json después de cada corrida real para confirmar que los
campos se están leyendo del lugar correcto y afinar el mapeo si hace falta.
"""

import gzip
import io
import json
import os
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
    "organismo peruano a cargo del SEACE. Licencia CC BY 4.0. Banco de información "
    "pública — no requiere afiliación con Humen Solutions para consultarlo."
)

# Máximo total de convocatorias a conservar (evita un data.json descontrolado si
# en algún momento hay muchos miles de procesos abiertos a la vez). Se
# conservan las de plazo más próximo primero, así que un tope alto casi nunca
# debería recortar nada relevante.
MAX_ITEMS = 4000

# Días hacia atrás a considerar "reciente" si un proceso no trae fecha límite.
FALLBACK_LOOKBACK_DAYS = 30

# Etiquetas informativas (NO filtran nada, solo destacan tarjetas en la interfaz).
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

# Categoría de contratación estándar de OCDS → etiqueta en español.
PROC_CATEGORY_LABELS = {
    "goods": "Bienes",
    "works": "Obras",
    "services": "Servicios",
    "consultingServices": "Consultoría de Obras",
}

CLOSED_STATUSES = {"complete", "cancelled", "unsuccessful", "withdrawn"}


def normalize(text):
    """minúsculas y sin tildes, para comparar palabras clave sin depender de acentos."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def match_humen_tags(title, description):
    """Etiquetas informativas de afinidad con Humen Solutions. No excluyen nada."""
    haystack = normalize((title or "") + " " + (description or ""))
    tags = []
    for tag, words in HUMEN_KEYWORDS.items():
        if any(w in haystack for w in words):
            tags.append(tag)
    return tags


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


def get_process_url(release, tender):
    """Enlace verificado para 'entrar' al proceso.

    Prioridad:
    1. Un documento del propio tender que ya traiga URL (a veces apunta
       directo al PDF de bases o a la ficha en SEACE) — es el más específico
       cuando existe.
    2. La ficha del proceso en el portal público de datos abiertos de
       contrataciones, construida a partir del OCID:
           https://contratacionesabiertas.osce.gob.pe/proceso/{ocid}
       Este patrón está VERIFICADO (se confirmó contra un resultado de
       búsqueda real en ese portal) — no es un patrón inventado.
    Si no hay ni documento ni ocid, no se inventa nada: se deja en None y el
    frontend cae de vuelta al buscador general.
    """
    doc_url = get_document_url(tender)
    if doc_url:
        return doc_url
    ocid = release.get("ocid")
    if ocid:
        return f"https://contratacionesabiertas.osce.gob.pe/proceso/{ocid}"
    return None


def parse_release(release):
    tender = release.get("tender") or {}
    status = (tender.get("status") or "").lower()
    if status in CLOSED_STATUSES:
        return None

    title = tender.get("title") or release.get("title") or ""
    description = tender.get("description") or ""

    due_date = None
    tender_period = tender.get("tenderPeriod") or {}
    if tender_period.get("endDate"):
        due_date = tender_period["endDate"][:10]

    pub_date = None
    if release.get("date"):
        pub_date = release["date"][:10]

    # Filtro clave: si ya sabemos la fecha límite y ya pasó, el proceso está
    # cerrado — sin importar lo que diga (o no diga) el campo "status". Los
    # registros históricos migrados a OCDS muchas veces no traen un status
    # confiable, y por eso procesos de hace 10+ años se colaban como "vigentes".
    if due_date:
        try:
            due_dt = datetime.strptime(due_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if due_dt.date() < datetime.now(timezone.utc).date():
                return None
        except ValueError:
            pass

    # Si no hay fecha límite conocida (frecuente en Contratación Directa, que no
    # tiene periodo de postulación), exigimos que la publicación sea reciente
    # para no arrastrar procesos históricos ya cerrados. Si TAMPOCO hay fecha de
    # publicación, no hay forma de saber si sigue vigente — antes esos casos se
    # colaban sin filtro alguno (así se filtró un proceso de 2015); ahora se
    # descartan directamente, por precaución.
    if due_date is None:
        if not pub_date:
            return None
        try:
            pub_dt = datetime.strptime(pub_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - pub_dt).days
            if age_days > FALLBACK_LOOKBACK_DAYS:
                return None
        except ValueError:
            return None

    value = tender.get("value") or {}
    buyer_name = (release.get("buyer") or {}).get("name") or "Entidad no especificada"
    proc_category = PROC_CATEGORY_LABELS.get(
        tender.get("mainProcurementCategory"), "No especificado"
    )

    return {
        "id": release.get("ocid") or release.get("id"),
        "procCategory": proc_category,
        "humenTags": match_humen_tags(title, description),
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
        "url": get_process_url(release, tender),
    }


def collect(years):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "HumenSolutions-LicitacionesSync/1.0 (+contacto empresa)"
    })

    items = []
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
                items.append(item)

        print(f"  {count} registros revisados en {year}", file=sys.stderr)

    return items


def main():
    now = datetime.now(timezone.utc)
    # Siempre se descargan el año en curso y el anterior: un proceso puede
    # seguir vigente hoy aunque su "release" en OCDS haya quedado registrado
    # en el archivo del año pasado. El filtro de fecha límite (arriba) se
    # encarga de descartar lo que ya cerró, así que ampliar el rango es
    # seguro y evita perder convocatorias realmente abiertas.
    years = [now.year, now.year - 1]

    items = collect(years)

    # Deduplicar por id/ocid (un mismo proceso puede aparecer más de una vez
    # si tuvo varias actualizaciones registradas como releases distintos).
    seen = {}
    for item in items:
        key = item["id"] or item["code"]
        if key not in seen:
            seen[key] = item
    items = list(seen.values())

    items.sort(key=lambda r: (r["dueDate"] is None, r["dueDate"] or ""))
    dropped = max(0, len(items) - MAX_ITEMS)
    items = items[:MAX_ITEMS]

    humen_counts = {"cont": 0, "inv": 0, "rec": 0}
    for item in items:
        for tag in item["humenTags"]:
            humen_counts[tag] += 1

    output = {
        "generated_at": now.isoformat(timespec="seconds"),
        "attribution": ATTRIBUTION,
        "source_url": "https://data.open-contracting.org/en/publication/135",
        "total_count": len(items),
        "humen_counts": humen_counts,
        "dropped_by_cap": dropped,
        "items": items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Listo: {len(items)} convocatorias guardadas en {OUTPUT_PATH}", file=sys.stderr)
    if dropped:
        print(f"  ({dropped} quedaron fuera por el tope de {MAX_ITEMS})", file=sys.stderr)


if __name__ == "__main__":
    main()
