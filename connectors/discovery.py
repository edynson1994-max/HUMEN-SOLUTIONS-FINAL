#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discovery.py — Fase 3 de "Perú en Datos": descubrimiento del catálogo
completo de la Plataforma Nacional de Datos Abiertos (PNDA).

QUÉ HACE
--------
1. Llama a `package_list` (lista TODOS los datasets del portal, sin
   filtro de categoría — es el único endpoint de listado que funciona;
   ver más abajo por qué no se usa otro).
2. Para cada slug, llama a `package_show` (metadata completa) y clasifica
   el dataset como "Economía y Finanzas" o no, con una heurística
   transparente y ajustable (ver `clasificar_categoria`).
3. Para los recursos de los datasets clasificados como Economía y
   Finanzas (por defecto — ver `--probar-data-api`), prueba EN VIVO si
   cada recurso tiene la Data API (datastore) activada.
4. Escribe `data/catalog.json` con el catálogo completo del portal (todas
   las categorías quedan registradas, aunque solo se sondee Data API para
   Economía y Finanzas en el MVP) — así las categorías futuras (sección
   20 del pedido original: Gobernabilidad, Salud, etc.) ya tienen su
   metadata lista sin tener que volver a recorrer los ~1,050 datasets.

ENDPOINTS VERIFICADOS EN VIVO (no adivinados — probados contra el portal
real antes de escribir este archivo, uno por uno, con fetch real):
--------------------------------------------------------------------------
  - `api/3/action/package_search`         → 404, NO enrutado (confirmado
                                             en sesiones anteriores).
  - `api/3/action/package_list`           → SÍ funciona. Devuelve
                                             {"success": true, "result":
                                             [slugs...]}. Corrida real
                                             (2026-08-22): 1,051 slugs.
                                             Los slugs vienen con
                                             tildes/ñ SIN codificar (ej.
                                             "viáticos-de-entidades") —
                                             coincide con lo que ya espera
                                             `package_show()` en
                                             common.py (usa quote() antes
                                             de armar la URL).
  - `api/3/action/package_show?id=<slug>` → SÍ funciona (ya usado por
                                             mef.py/contraloria.py/
                                             inei_renamu.py). Confirmado
                                             además, para este módulo:
                                               * `result["groups"]` es una
                                                 lista de dicts con
                                                 "title" (nombre completo
                                                 de la entidad
                                                 publicadora) — NO la
                                                 categoría temática.
                                               * `result["tags"]` es una
                                                 lista de dicts con
                                                 "name".
                                               * `result["metadata_created"]`
                                                 y `["metadata_modified"]`
                                                 vienen como texto en
                                                 español NO estándar (ej.
                                                 "Miércoles, 08/02/2023 -
                                                 15:41"), no ISO-8601. Por
                                                 eso este módulo los
                                                 guarda TAL CUAL (crudos)
                                                 en vez de intentar
                                                 parsearlos a una fecha —
                                                 parsear mal una fecha y
                                                 mostrarla como si fuera
                                                 confiable sería peor que
                                                 no parsearla.
  - `/search/field_topic/<categoría>`     → Bloqueado por robots.txt del
                                             portal (la página que
                                             muestra "1,330 datasets" de
                                             Economía y Finanzas es esta).
                                             NO se scrapea — violaría las
                                             reglas del propio portal.
  - `api/action/datastore/search.json`    → Ya usado por common.py
                                             (`has_data_api`,
                                             `datastore_search_all`).

POR QUÉ NO HAY UN CAMPO "CATEGORÍA" DIRECTO
--------------------------------------------
`field_topic` (la taxonomía que usa la página de búsqueda por categoría,
la misma que el usuario mostró en su captura de pantalla con "1,330
Distribución de Datos") es una taxonomía de Drupal que esta API de
metadata (CKAN/DKAN `package_show`) no expone. Por eso se clasifica cada
dataset con una heurística verificable (ver `clasificar_categoria`) en
vez de inventar un campo que no existe o scrapear la página bloqueada.

POR QUÉ SOLO SE PRUEBA DATA API PARA "ECONOMÍA Y FINANZAS" POR DEFECTO
-------------------------------------------------------------------------
Probar `has_data_api()` es 1 petición HTTP por recurso. Con ~1,050
datasets (varios con más de un recurso), probarlo para TODO el portal en
cada corrida de descubrimiento sería lento y poco respetuoso con el
servidor del portal, y el MVP (sección 10 del plan) solo necesita esto
para Economía y Finanzas. `--probar-data-api todos` está disponible para
cuando se quiera extender a otras categorías (Fase futura, sección 20 del
pedido original) — nunca hace falta tocar este archivo para eso, solo
cambiar el flag.

QUÉ NO HACE (a propósito)
--------------------------
No reemplaza a mef.py/contraloria.py/inei_renamu.py — sus 3 datasets ya
conectados siguen sincronizándose exactamente igual que hoy. Este módulo
solo descubre y clasifica; la sincronización genérica de cualquier
dataset descubierto es la Fase 4 (`sync_dataset.py`, todavía no
construido).
"""

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(__file__))
from common import has_data_api, http_get, normalize, package_show, write_summary

PNDA_PACKAGE_LIST_URL = "https://www.datosabiertos.gob.pe/api/3/action/package_list"
PNDA_DATASET_BASE_URL = "https://www.datosabiertos.gob.pe/dataset/"

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "catalog.json")

# Lista de entidades económico-financieras conocidas (sección 2 del plan
# de Fase 1). Los nombres completos se comparan como substring normalizado
# (sin tildes, minúsculas); las siglas cortas se comparan por PALABRA
# COMPLETA (con límites de palabra vía regex) para no matchear por
# accidente una sigla de 3-4 letras dentro de otra palabra más larga —
# ej. "mef" no debe matchear si apareciera dentro de otro nombre que
# simplemente contuviera esas letras seguidas.
ENTIDADES_ECONOMIA_FINANZAS_NOMBRES = [
    "ministerio de economia y finanzas",
    "superintendencia nacional de aduanas y de administracion tributaria",
    "banco central de reserva del peru",
    "banco de la nacion",
    "oficina de normalizacion previsional",
    "corporacion financiera de desarrollo",
    "fondo nacional de financiamiento de la actividad empresarial del estado",
    "superintendencia de banca, seguros y afp",
]
ENTIDADES_ECONOMIA_FINANZAS_SIGLAS = ["mef", "sunat", "bcrp", "onp", "cofide", "fonafe", "sbs"]

# Palabras clave para el segundo paso de clasificación (cuando la entidad
# publicadora no está en la lista de arriba, pero el contenido del
# dataset es claramente económico-financiero — ej. un dataset de
# presupuesto publicado por un gobierno regional, no por el MEF).
PALABRAS_CLAVE_ECONOMIA_FINANZAS = [
    "presupuesto", "gasto publico", "gasto público", "tributacion",
    "tributario", "recaudacion", "deuda publica", "deuda pública",
    "inversion publica", "inversión pública", "ejecucion presupuestal",
    "ejecución presupuestal", "canon", "ingresos publicos",
    "ingresos públicos", "devengado", "presupuestal", "fiscal",
    "financiero", "financiera", "impuesto", "arancel", "aduana",
    "regalia", "regalía", "endeudamiento",
]


def clasificar_categoria(dataset_result):
    """Devuelve (categoria, metodo) — metodo es "entidad" o "palabra_clave"
    — o (None, None) si el dataset no matchea Economía y Finanzas con
    ninguno de los dos criterios. Nunca asume "sí" por defecto: la
    ausencia de match es un resultado válido y esperado para la mayoría
    del portal (el MVP es solo una categoría de ~1,050)."""
    groups = dataset_result.get("groups") or []
    entidad_norm = normalize(groups[0].get("title", "")) if groups else ""
    for candidato in ENTIDADES_ECONOMIA_FINANZAS_NOMBRES:
        if normalize(candidato) in entidad_norm:
            return "Economía y Finanzas", "entidad"
    for sigla in ENTIDADES_ECONOMIA_FINANZAS_SIGLAS:
        if re.search(r"\b" + re.escape(sigla) + r"\b", entidad_norm):
            return "Economía y Finanzas", "entidad"

    tags_txt = " ".join((t.get("name") or "") for t in (dataset_result.get("tags") or []))
    texto = normalize(" ".join([
        dataset_result.get("title", "") or "",
        dataset_result.get("notes", "") or "",
        tags_txt,
    ]))
    for kw in PALABRAS_CLAVE_ECONOMIA_FINANZAS:
        if normalize(kw) in texto:
            return "Economía y Finanzas", "palabra_clave"

    return None, None


def obtener_lista_slugs():
    resp = http_get(PNDA_PACKAGE_LIST_URL, timeout=60, max_retries=3)
    payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    if not payload.get("success"):
        raise RuntimeError(f"package_list respondió success=false: {payload.get('error')}")
    return payload["result"]


def construir_entrada_dataset(slug, dataset_result, probar_data_api_este):
    groups = dataset_result.get("groups") or []
    entidad = groups[0].get("title") if groups else None
    categoria, categoria_metodo = clasificar_categoria(dataset_result)

    resources = []
    for r in (dataset_result.get("resources") or []):
        resource_id = r.get("id")
        tiene_data_api = None
        detalle_data_api = None
        if probar_data_api_este and resource_id:
            tiene_data_api, detalle_data_api = has_data_api(resource_id)
        resources.append({
            "resource_id": resource_id,
            "nombre": r.get("name"),
            "formato": r.get("format"),
            "resource_url": r.get("url"),
            "tiene_data_api": tiene_data_api,
            "detalle_data_api": detalle_data_api,
        })

    return {
        "dataset_id": slug,
        "titulo": dataset_result.get("title"),
        "descripcion": dataset_result.get("notes"),
        "entidad": entidad,
        "categoria": categoria,
        "categoria_metodo": categoria_metodo,
        "dataset_url": PNDA_DATASET_BASE_URL + quote(slug, safe=""),
        "resources": resources,
        # Crudos a propósito — ver docstring del módulo (no son ISO-8601,
        # vienen en español desde el portal; parsearlos mal sería peor
        # que no parsearlos).
        "fecha_creacion_portal": dataset_result.get("metadata_created"),
        "fecha_modificacion_portal": dataset_result.get("metadata_modified"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                         help="Procesar solo los primeros N datasets del portal (para pruebas rápidas; el catálogo resultante quedará incompleto a propósito).")
    parser.add_argument("--pausa", type=float, default=0.2,
                         help="Segundos de espera entre peticiones a package_show (ser respetuosos con el servidor del portal). Default: 0.2s.")
    parser.add_argument("--probar-data-api", choices=["economia-finanzas", "todos", "ninguno"], default="economia-finanzas",
                         help="Para qué datasets probar en vivo si sus recursos tienen Data API. Default: solo los clasificados como Economía y Finanzas (ver docstring del módulo).")
    parser.add_argument("--out", default=OUT_PATH, help="Ruta de salida del catalog.json (para pruebas, sin pisar el real).")
    args = parser.parse_args()

    try:
        slugs = obtener_lista_slugs()
    except Exception as exc:
        print(f"ERROR: no se pudo obtener package_list: {exc}", file=sys.stderr)
        write_summary(args.out, {
            "fuente": "Catálogo del Portal Nacional de Datos Abiertos (PNDA)",
            "estado": "error",
            "error": f"package_list falló: {exc}",
            "datasets": [],
        })
        sys.exit(1)

    total_portal = len(slugs)
    if args.limit:
        slugs = slugs[:args.limit]
    print(f"package_list: {total_portal} datasets en el portal. Procesando {len(slugs)}...", file=sys.stderr)

    datasets = []
    errores = []
    for i, slug in enumerate(slugs, 1):
        try:
            resultado = package_show(slug)
        except Exception as exc:
            print(f"  [{i}/{len(slugs)}] ERROR en {slug!r}: {exc}", file=sys.stderr)
            errores.append({"dataset_id": slug, "error": str(exc)})
            time.sleep(args.pausa)
            continue

        categoria_preview, _ = clasificar_categoria(resultado)
        probar_este = (
            args.probar_data_api == "todos"
            or (args.probar_data_api == "economia-finanzas" and categoria_preview == "Economía y Finanzas")
        )
        entrada = construir_entrada_dataset(slug, resultado, probar_este)
        datasets.append(entrada)

        if i % 50 == 0 or i == len(slugs):
            econ_hasta_ahora = sum(1 for d in datasets if d["categoria"] == "Economía y Finanzas")
            print(f"  [{i}/{len(slugs)}] procesados · {econ_hasta_ahora} clasificados como Economía y Finanzas hasta ahora", file=sys.stderr)

        time.sleep(args.pausa)

    total_economia_finanzas = sum(1 for d in datasets if d["categoria"] == "Economía y Finanzas")
    con_data_api = sum(
        1 for d in datasets for r in d["resources"] if r["tiene_data_api"] is True
    )

    summary = {
        "fuente": "Catálogo del Portal Nacional de Datos Abiertos (PNDA) — descubrimiento propio, no oficial",
        "atribucion": "Datos originales de cada entidad publicadora, vía Portal Nacional de Datos Abiertos (PNDA).",
        "estado": "ok",
        "total_datasets_portal": total_portal,
        "total_datasets_procesados": len(datasets),
        "total_clasificados_economia_finanzas": total_economia_finanzas,
        "total_recursos_con_data_api_confirmada": con_data_api,
        "metodo_clasificacion": "entidad publicadora conocida (ver ENTIDADES_ECONOMIA_FINANZAS); si no matchea, palabras clave en título/notas/tags (ver PALABRAS_CLAVE_ECONOMIA_FINANZAS)",
        "data_api_probado_para": args.probar_data_api,
        "errores": errores,
        "datasets": datasets,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_summary(args.out, summary)
    print(
        f"Listo: {len(datasets)} datasets procesados, {total_economia_finanzas} clasificados como "
        f"Economía y Finanzas, {con_data_api} recursos con Data API confirmada, {len(errores)} errores.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
