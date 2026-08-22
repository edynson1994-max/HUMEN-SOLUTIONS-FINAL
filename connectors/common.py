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

ACTUALIZACIÓN — Data API (datastore) confirmada por el instructivo oficial
--------------------------------------------------------------------------
El "Instructivo para el Registro de Datasets en la Plataforma Nacional de
Datos Abiertos" (PCM/Secretaría de Gobierno Digital, 2021) confirma que la
plataforma es DKAN y que cada RECURSO (no cada dataset) puede tener una
"Data API" propia — un botón que aparece junto a "Descargar" cuando el
recurso se registró con la opción "Grilla" activada al subirlo. Eso es
exactamente el endpoint `api/action/datastore/search.json?resource_id=...`
que antes se probó y pareció roto — pero se probó con un resource_id
adivinado/incorrecto, no con uno real. Ahora sí se puede intentar bien:

  1. `package_show(<slug o id del dataset>)` (ya confirmado funcional)
     devuelve `result["resources"]`, una lista donde cada recurso trae su
     propio `id` (el resource_id real) y su `url` de descarga actual.
  2. Con ese `id` real, `datastore_search_all()` intenta la Data API.
  3. Si el recurso NO tiene datastore activado (no todos lo tienen — solo
     los que se subieron con "Grilla" marcada), la API responde con error
     y el conector debe caer de vuelta a descargar el archivo y parsearlo
     como CSV — nunca asumir que existe.

Esto NO requiere usuario ni clave: el login que pide el instructivo es solo
para las entidades que PUBLICAN datasets nuevos (sección "Iniciar sesión"),
no para leer datos públicos ya publicados — package_show y datastore_search
son de lectura pública, sin autenticación.
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
PNDA_DATASTORE_API = "https://www.datosabiertos.gob.pe/api/action/datastore/search.json"
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
    datastore/search.json están rotos o no enrutados, verificado).

    `dataset_id` puede venir con tildes/ñ sin codificar (algunos slugs de
    este portal las tienen, ej. "información-general-...") — se
    codifica aquí con quote() antes de armar la URL. Sin esto, urlopen()
    revienta con UnicodeEncodeError en cuanto la URL tiene un caracter no
    ASCII (confirmado corriendo esto de verdad, no solo con mocks)."""
    from urllib.parse import quote
    url = f"{PNDA_API}?id={quote(dataset_id, safe='')}"
    resp = http_get(url)
    raw = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(raw)

    # Confirmado en una corrida real (2026-08-22): para algunos slugs esta
    # API respondió con una LISTA en la raíz en vez del sobre
    # {"success":..., "result":...} que documenta CKAN — probablemente el
    # slug no matchea ningún dataset y el portal devuelve algo distinto al
    # error estándar de CKAN. Antes esto reventaba con "'list' object has
    # no attribute 'get'"; ahora se reporta con contexto (los primeros
    # ~300 caracteres de la respuesta) para poder diagnosticarlo en el
    # próximo intento, y sigue cayendo al respaldo (descarga directa) sin
    # romper nada.
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"package_show para {dataset_id} devolvió {type(payload).__name__} en vez de un objeto — "
            f"respuesta cruda: {raw[:300]!r}"
        )
    if not payload.get("success"):
        raise RuntimeError(f"package_show para {dataset_id} respondió success=false: {payload.get('error')}")
    return payload["result"]


def datastore_search_all(resource_id, page_size=5000, max_records=None):
    """Pagina sobre la Data API real (datastore/search.json) para un
    resource_id concreto y devuelve TODOS los registros ya como dicts
    (nombre de columna -> valor), sin necesidad de parsear CSV a mano.

    Confirmado como mecanismo real por el instructivo oficial (ver el
    aviso arriba en este archivo) — pero solo funciona para recursos que
    se registraron con datastore activado. Si el recurso no lo tiene,
    esto lanza una excepción (típicamente con success=false o un error de
    HTTP) y quien llama debe usar la descarga directa + CSV como respaldo.

    `max_records` corta la paginación temprano (útil para no bajar
    millones de filas de un recurso enorme por esta vía — para eso sigue
    siendo mejor el streaming de archivo directo)."""
    offset = 0
    records = []
    fields = None
    while True:
        limit = page_size
        if max_records:
            limit = min(limit, max_records - len(records))
            if limit <= 0:
                break
        from urllib.parse import quote
        url = f"{PNDA_DATASTORE_API}?resource_id={quote(str(resource_id), safe='')}&limit={limit}&offset={offset}"
        resp = http_get(url)
        payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("success"):
            raise RuntimeError(f"datastore_search para {resource_id} respondió success=false: {payload.get('error')}")
        result = payload["result"]
        if fields is None:
            fields = [f["id"] for f in result.get("fields", []) if f.get("id") != "_id"]
        batch = result.get("records", [])
        records.extend(batch)
        if not batch or len(batch) < limit:
            break
        offset += limit
        if max_records and len(records) >= max_records:
            break
    return {"fields": fields or [], "records": records}


def has_data_api(resource_id, timeout=20):
    """Prueba EN VIVO (una sola petición, `limit=1`, sin paginar) si un
    recurso concreto tiene la Data API (datastore) activada.

    Generalización del mismo mecanismo que ya usaba `contraloria.py` de
    forma ad-hoc: no hay ningún campo en `package_show` que diga de
    antemano si un recurso tiene datastore activado (confirmado revisando
    la respuesta real de dos datasets distintos) — la única forma
    confiable es intentar `datastore/search.json?resource_id=...` y ver si
    responde con éxito o con error.

    Nunca lanza excepción: quien llama (p.ej. `discovery.py`, sync futuro)
    necesita poder probar cientos de recursos sin que uno solo tumbe todo
    el proceso. Devuelve `(tiene_data_api: bool, detalle: str)` — el
    detalle sirve para diagnosticar por qué un recurso no tiene Data API
    (útil al revisar `data/catalog.json` a mano)."""
    if not resource_id:
        return False, "sin resource_id"
    try:
        from urllib.parse import quote
        url = f"{PNDA_DATASTORE_API}?resource_id={quote(str(resource_id), safe='')}&limit=1"
        resp = http_get(url, timeout=timeout, max_retries=2)
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        if payload.get("success"):
            return True, "datastore activo"
        return False, str(payload.get("error") or "success=false")
    except Exception as exc:
        return False, str(exc)


def find_resource(dataset_result, hint=None, formato=None):
    """Dado el `result` de package_show(), elige un recurso de su lista
    `resources`. Si `hint` se da, prioriza el recurso cuyo nombre/título
    contiene ese texto (normalizado); si `formato` se da, filtra por
    formato (csv, xlsx, etc., insensible a mayúsculas). Devuelve el primer
    recurso que matchee, o None si no hay ninguno — nunca inventa uno."""
    resources = dataset_result.get("resources", []) or []
    candidatos = resources
    if formato:
        candidatos = [r for r in candidatos if normalize(r.get("format", "")) == normalize(formato)] or candidatos
    if hint:
        hint_n = normalize(hint)
        con_hint = [r for r in candidatos if hint_n in normalize(r.get("name", "") + " " + r.get("title", ""))]
        if con_hint:
            return con_hint[0]
    return candidatos[0] if candidatos else None


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
    """Busca en `fieldnames` (las columnas reales de un CSV) el nombre que
    mejor se parezca a alguno de `candidates` (nombres plausibles en
    español, normalizados, sin tildes ni mayúsculas).

    DOS PASADAS — corregido tras un bug real con datos del MEF: cuando un
    dataset tiene pares "código" / "código_nombre" (ej.
    DEPARTAMENTO_EJECUTORA vs DEPARTAMENTO_EJECUTORA_NOMBRE), una sola
    pasada por substring-en-cualquier-sentido agarraba el campo de código
    por error, porque "departamento_ejecutora" (el campo corto) queda
    "contenido dentro" del candidato largo "departamento_ejecutora_nombre"
    igual que si fuera al revés. Por eso ahora:
      1) Primero se busca una coincidencia EXACTA (recorriendo todos los
         candidatos, en su orden de prioridad) — esto es inequívoco y
         resuelve el caso de arriba, porque "departamento_ejecutora_nombre"
         solo empata exacto con el campo que de verdad se llama así.
      2) Solo si ningún candidato tuvo coincidencia exacta, se cae a
         substring en cualquier sentido (comportamiento anterior), para
         seguir tolerando nombres de columna parcialmente distintos."""
    norm_fields = {f: normalize(f) for f in fieldnames}

    for cand in candidates:
        cand_n = normalize(cand)
        for real_name, norm_name in norm_fields.items():
            if cand_n == norm_name:
                return real_name

    for cand in candidates:
        cand_n = normalize(cand)
        for real_name, norm_name in norm_fields.items():
            if cand_n in norm_name or norm_name in cand_n:
                return real_name

    return None


def smart_decode(raw_bytes):
    """Decodifica bytes de CSV a texto, adivinando entre UTF-8 y
    Windows-1252 (cp1252).

    CONFIRMADO CON DATOS REALES (corrida del 2026-08-22): los CSV de
    Contraloría en este portal vienen en cp1252, no UTF-8 — forzarlos como
    UTF-8 produce encabezados rotos tipo 'N�MERO DE INFORME DE CONTROL' en
    vez de 'NÚMERO DE INFORME DE CONTROL'. cp1252 es tristemente común en
    exportaciones de sistemas del Estado peruano (típicamente Excel/SQL
    Server en Windows). Esta función intenta UTF-8 primero (por si un
    dataset sí viene bien) y solo cae a cp1252 si UTF-8 dejó caracteres de
    reemplazo (el síntoma de que la codificación no era esa) — cp1252
    nunca lanza excepción (mapea cualquier byte a algún caracter), así que
    es un respaldo seguro que no puede fallar."""
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    if "�" in text:
        text = raw_bytes.decode("cp1252", errors="replace")
    return text


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
    """Guarda el resumen como JSON, agregando siempre `generado_en` (hora
    UTC de esta corrida) si no lo trae ya — así el frontend (o cualquier
    revisión manual) puede mostrar honestamente cuándo se sincronizó por
    última vez, en vez de inventar un "actualizado hace X minutos"."""
    import datetime
    if "generado_en" not in summary:
        summary = {**summary, "generado_en": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Listo: resumen guardado en {out_path}", file=sys.stderr)
