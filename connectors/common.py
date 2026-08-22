#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common.py — utilidades compartidas por los conectores de "Perú en Datos".

CONTEXTO IMPORTANTE (léelo antes de tocar cualquier conector)
----------------------------------------------------------------
Estos conectores se escribieron SIN poder inspeccionar los archivos reales
byte a byte: el entorno donde se escribieron no tiene salida de red hacia
estos dominios, y la herramienta de investigación disponible (un fetch que
convierte HTML a texto) no puede leer contenido binario/CSV crudo — solo
confirmó que los archivos EXISTEN y responden (no dan 404), no su contenido
exacto. Por eso:

  1. Los nombres de columna NO se asumen fijos. `detect_column()` busca por
     coincidencia aproximada (normalizada, sin tildes, en minúsculas) contra
     una lista de nombres candidatos plausibles en español. Si el portal usa
     un nombre distinto al esperado, esto puede no encontrar la columna —
     en ese caso el conector debe reportarlo explícitamente, nunca inventar
     un valor.
  2. Cada conector guarda, además del resumen, la lista real de columnas que
     encontró en el archivo (`columnas_detectadas`) — así, en la primera
     corrida real (GitHub Actions, que sí tiene salida de red), se puede
     verificar de un vistazo si la detección funcionó o si hay que ajustar
     los nombres candidatos.
  3. Todo el pipeline debe seguir funcionando (sin reventar) aunque una
     columna no se detecte — debe degradar a "no disponible", nunca a un
     número inventado.

Descubrimiento de dataset: la API de búsqueda de este portal
(`api/3/action/package_search`) no está enrutada (404 verificado). Solo
funciona `api/3/action/package_show?id=<id>` con un id de dataset ya
conocido. Los ids/URLs usados por cada conector se obtuvieron navegando el
catálogo manualmente (vía búsqueda web, ya que `/search/` está bloqueado por
robots.txt) y verificando cada página de dataset con fetch real — no son
adivinados.
"""

import csv
import io
import json
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request

PNDA_API = "https://www.datosabiertos.gob.pe/api/3/action/package_show"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 PeruEnDatos/1.0"
)


def normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def http_get(url, timeout=60, max_retries=3, stream=False):
    """GET defensivo: reintenta con backoff, manda un User-Agent de navegador
    real (varios portales .gob.pe devuelven 403 a clientes sin UA), y no
    revienta el proceso completo si un solo recurso falla — quien llama
    decide qué hacer con la excepción."""
    req_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            resp = urllib.request.urlopen(req, timeout=timeout)
            return resp
        except (urllib.error.URLError, TimeoutError) as exc:
            last_err = exc
            print(f"  intento {attempt}/{max_retries} falló para {url}: {exc}", file=sys.stderr)
            if attempt < max_retries:
                time.sleep(2 * attempt)
    raise last_err


def package_show(dataset_id):
    """Llama a la API CKAN/DKAN de metadatos (package_show) — la única de
    búsqueda/consulta confirmada funcional en este portal (package_search y
    datastore/search.json están rotos o no enrutados, verificado)."""
    url = f"{PNDA_API}?id={dataset_id}"
    resp = http_get(url)
    payload = json.loads(resp.read().decode("utf-8"))
    if not payload.get("success"):
        raise RuntimeError(f"package_show para {dataset_id} respondió success=false")
    return payload["result"]


def download_to_file(url, dest_path, max_bytes=None):
    """Descarga en streaming (no carga todo en memoria) — necesario porque
    algunos archivos de este portal pesan varios GB (ej. el CSV de
    ejecución de gasto del MEF). Si max_bytes se especifica, corta la
    descarga ahí (útil para tomar solo una muestra de un archivo enorme sin
    bajarlo completo — el archivo quedará truncado a propósito)."""
    resp = http_get(url, stream=True)
    total = 0
    with open(dest_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if max_bytes and total >= max_bytes:
                break
    return total


def detect_column(fieldnames, candidates):
    """Busca en `fieldnames` (las columnas reales de un CSV) el primer nombre
    que se parezca a alguno de `candidates` (nombres plausibles en español,
    normalizados). Coincidencia por substring en ambos sentidos, sin tildes
    ni mayúsculas — porque no sabemos el nombre exacto que usa cada
    portal. Devuelve el nombre REAL de la columna (tal cual aparece en el
    archivo), o None si no se encontró nada parecido."""
    norm_fields = {f: normalize(f) for f in fieldnames}
    for cand in candidates:
        cand_n = normalize(cand)
        for real_name, norm_name in norm_fields.items():
            if cand_n == norm_name or cand_n in norm_name or norm_name in cand_n:
                return real_name
    return None


def sniff_csv_reader(file_obj):
    """Abre un csv.DictReader intentando adivinar el delimitador real
    (algunos portales peruanos usan '|' en vez de ',', como ya vimos con el
    CSV de SEACE) en vez de asumir uno fijo."""
    sample = file_obj.read(8192)
    file_obj.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
    except csv.Error:
        dialect = csv.excel  # separador ',' por defecto si el sniffer no logra decidir
    return csv.DictReader(file_obj, dialect=dialect)


def write_summary(out_path, summary):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Listo: resumen guardado en {out_path}", file=sys.stderr)
