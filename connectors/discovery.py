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
   metadata lista sin tener que volver a recorrer los ~4,600 datasets.

ENDPOINTS VERIFICADOS EN VIVO (no adivinados — probados contra el portal
real antes de escribir este archivo, uno por uno, con fetch real):
--------------------------------------------------------------------------
  - `api/3/action/package_search`         → 404, NO enrutado (confirmado
                                             en sesiones anteriores).
  - `api/3/action/package_list`           → SÍ funciona. Devuelve
                                             {"success": true, "result":
                                             [slugs...]}. Una prueba con
                                             la herramienta de fetch (que
                                             resume el HTML/JSON con un
                                             modelo, no lo lee crudo)
                                             reportó 1,051 slugs — pero la
                                             primera corrida real en
                                             GitHub Actions (2026-08-22)
                                             confirmó 4,646. El número
                                             correcto es el que reporta
                                             cada corrida en
                                             `total_datasets_portal`, no
                                             ninguna cifra fija de este
                                             comentario. Los slugs vienen con
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
Probar `has_data_api()` es 1 petición HTTP por recurso. Con ~4,600
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
#
# "fiscal" fue quitada a propósito — revisé la corrida real completa
# (2026-08-23, 706 datasets clasificados) descargando el catalog.json real
# y analizándolo con Python, no una muestra: esa sola palabra generó 131
# coincidencias, de las cuales 107 eran falsos positivos claros que no
# tienen nada que ver con Economía y Finanzas — "año fiscal" (una fecha,
# no el tema del dataset), "distrito fiscal"/"fiscalía" (Ministerio
# Público = fiscales = PROCURADORES, no finanzas), e "Insumos Químicos
# Fiscalizados"/"Producción Fiscalizada" (OEFA/MINEM = FISCALIZACIÓN
# ambiental o regulatoria = supervisión, no finanzas). "fiscal" en
# español es ambiguo entre "relativo al fisco/impuestos" y "relativo a la
# fiscalía/persecución penal" o "fiscalización/supervisión regulatoria" —
# los otros 24 casos donde SÍ había contenido de Economía y Finanzas real
# ya quedaban cubiertos por otras palabras clave más específicas de esta
# lista (presupuesto/impuesto/etc.), así que quitar "fiscal" no pierde
# cobertura real, solo el ruido.
PALABRAS_CLAVE_ECONOMIA_FINANZAS = [
    "presupuesto", "gasto publico", "gasto público", "tributacion",
    "tributario", "recaudacion", "deuda publica", "deuda pública",
    "inversion publica", "inversión pública", "ejecucion presupuestal",
    "ejecución presupuestal", "canon", "ingresos publicos",
    "ingresos públicos", "devengado", "presupuestal",
    "financiero", "financiera", "impuesto", "arancel", "aduana",
    "regalia", "regalía", "endeudamiento",
]

# Entidades cuyo NOMBRE o TAGS suelen colisionar con las palabras clave de
# arriba pero cuya actividad principal no es Economía y Finanzas — se
# excluyen del paso por palabra_clave (no del paso por entidad, que de
# todos modos no las incluye). Encontradas revisando la corrida real:
#   - OEFA ("Organismo de Evaluación y FISCALIZACIÓN Ambiental"): 46+
#     datasets ambientales quedaron adentro solo por la palabra
#     "fiscalización"/tags compartidos — es supervisión ambiental, no
#     finanzas.
#   - PRONABEC ("Programa Nacional de Becas y CRÉDITO Educativo"): 33
#     datasets de becas/personal/convocatorias quedaron adentro — el
#     programa tiene "crédito" en el nombre pero es un programa de becas
#     educativas, no una entidad financiera.
#   - Contraloría General de la República (CGR): sus datasets de
#     "Monitores Ciudadanos de Control" quedaron adentro por tags — esos
#     mismos datasets ya están conectados y categorizados como
#     "Gobernabilidad" en el resto de Perú en Datos (ver peru-datos/app.html,
#     sección Catálogo), no como Economía y Finanzas.
ENTIDADES_EXCLUIDAS_DE_PALABRA_CLAVE = [
    "organismo de evaluacion y fiscalizacion ambiental",
    "programa nacional de becas y credito educativo",
    "contraloria general de la republica",
]


def clasificar_categoria(dataset_result):
    """Devuelve (categoria, metodo) — metodo es "entidad" o "palabra_clave"
    — o (None, None) si el dataset no matchea Economía y Finanzas con
    ninguno de los dos criterios. Nunca asume "sí" por defecto: la
    ausencia de match es un resultado válido y esperado para la mayoría
    del portal (el MVP es solo una categoría de ~4,600)."""
    groups = dataset_result.get("groups") or []
    entidad_norm = normalize(groups[0].get("title", "")) if groups else ""
    for candidato in ENTIDADES_ECONOMIA_FINANZAS_NOMBRES:
        if normalize(candidato) in entidad_norm:
            return "Economía y Finanzas", "entidad"
    for sigla in ENTIDADES_ECONOMIA_FINANZAS_SIGLAS:
        if re.search(r"\b" + re.escape(sigla) + r"\b", entidad_norm):
            return "Economía y Finanzas", "entidad"

    # Ver ENTIDADES_EXCLUIDAS_DE_PALABRA_CLAVE arriba — estas entidades NO
    # pasan al paso por palabra clave, aunque su nombre o tags coincidan
    # con alguna (confirmado con la corrida real que sí colisionaban).
    if any(excluida in entidad_norm for excluida in ENTIDADES_EXCLUIDAS_DE_PALABRA_CLAVE):
        return None, None

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


def cargar_catalogo_existente(out_path):
    """Carga el catalog.json ya existente (si lo hay) como dos dicts
    indexados por dataset_id: uno para los datasets ya descubiertos con
    éxito, otro para los que quedaron en error. Nunca levanta excepción —
    si el archivo no existe, está vacío, corrupto, o no tiene la forma
    esperada, se trata como "primera corrida" (dicts vacíos).

    FIX DEL BUG DE ACUMULACIÓN (ver README de connectors/): antes,
    main() siempre empezaba con datasets=[] y errores=[] en blanco, así
    que CADA corrida — sobre todo cada corrida de continuación con
    --empezar-en, que es el caso normal de uso — pisaba el catalog.json
    entero con SOLO el lote de esa corrida, borrando en silencio todo lo
    descubierto en corridas anteriores. Confirmado en producción: una
    corrida completa (2026-08-23) había dejado 706 datasets clasificados
    como Economía y Finanzas; corridas posteriores de continuación lo
    fueron pisando hasta dejar el catálogo real en solo 530 datasets
    totales (65 clasificados) pese a reportar "corrida_completa: true".
    Cargar lo que ya había, indexado por dataset_id, permite que cada
    corrida se SUME a lo anterior en vez de reemplazarlo."""
    if not os.path.isfile(out_path):
        return {}, {}, None
    try:
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(
            f"AVISO: no se pudo leer {out_path} para acumular sobre él ({exc}) — "
            f"esta corrida empieza desde un catálogo vacío.",
            file=sys.stderr,
        )
        return {}, {}, None

    datasets_por_id = {}
    for d in (data.get("datasets") or []):
        did = d.get("dataset_id")
        if did:
            datasets_por_id[did] = d

    errores_por_id = {}
    for e in (data.get("errores") or []):
        did = e.get("dataset_id")
        if did:
            errores_por_id[did] = e

    total_portal_anterior = data.get("total_datasets_portal")

    print(
        f"Catálogo existente cargado desde {out_path}: {len(datasets_por_id)} datasets y "
        f"{len(errores_por_id)} errores de corridas anteriores — esta corrida se SUMA a esto, no lo reemplaza.",
        file=sys.stderr,
    )
    return datasets_por_id, errores_por_id, total_portal_anterior


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

    # Se guardan los tags — corregido tras la primera revisión manual del
    # catalog.json real (2026-08-23): la clasificación por palabra_clave
    # también mira los tags (no solo título/notas), pero como antes no se
    # guardaban en la salida, ~99 datasets clasificados así no se podían
    # auditar sin volver a llamar a la API para ver qué tag disparó el
    # match. Ahora quedan en el archivo, así cualquier revisión futura es
    # 100% reproducible localmente, sin red.
    tags = [t.get("name") for t in (dataset_result.get("tags") or []) if t.get("name")]

    return {
        "dataset_id": slug,
        "titulo": dataset_result.get("title"),
        "descripcion": dataset_result.get("notes"),
        "entidad": entidad,
        "tags": tags,
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


def armar_summary(args, total_portal, empezar_en, intentados_esta_corrida, datasets, errores,
                   cortado_por_tiempo, minutos_transcurridos, nuevos_esta_corrida=None, errores_esta_corrida=None):
    """Arma el dict que se guarda en catalog.json — usado tanto para
    checkpoints intermedios como para el resultado final, así ambos tienen
    exactamente la misma forma (ver docstring de `main` sobre por qué hay
    checkpoints).

    IMPORTANTE (fix del bug de acumulación, ver cargar_catalogo_existente
    y el README): `datasets` y `errores` son ahora CUMULATIVOS — incluyen
    lo descubierto en TODAS las corridas anteriores, no solo la actual.
    Por eso `siguiente_empezar_en` ya NO puede calcularse con
    len(datasets)/len(errores) como antes (cuando esas listas eran del
    tamaño del lote de esta corrida nada más) — eso daría un número cada
    vez más inflado y rompería el avance por el portal. Se usa
    `intentados_esta_corrida`, un contador aparte que sí cuenta solo los
    slugs tocados en ESTA corrida (con éxito o con error), que es lo que
    realmente determina cuántos índices de package_list se avanzaron."""
    total_economia_finanzas = sum(1 for d in datasets if d["categoria"] == "Economía y Finanzas")
    con_data_api = sum(1 for d in datasets for r in d["resources"] if r["tiene_data_api"] is True)
    siguiente_empezar_en = empezar_en + intentados_esta_corrida
    corrida_completa = (not cortado_por_tiempo) and siguiente_empezar_en >= total_portal
    return {
        "fuente": "Catálogo del Portal Nacional de Datos Abiertos (PNDA) — descubrimiento propio, no oficial",
        "atribucion": "Datos originales de cada entidad publicadora, vía Portal Nacional de Datos Abiertos (PNDA).",
        "estado": "ok" if corrida_completa else "parcial",
        "corrida_completa": corrida_completa,
        "cortado_por_tiempo": cortado_por_tiempo,
        "minutos_que_tomo_esta_corrida": round(minutos_transcurridos, 1),
        "empezar_en_usado_esta_corrida": empezar_en,
        "siguiente_empezar_en": None if corrida_completa else siguiente_empezar_en,
        "total_datasets_portal": total_portal,
        # Acumulado: todo lo descubierto hasta ahora, sumando todas las
        # corridas (no solo esta). "datasets_nuevos_o_actualizados_en_esta_corrida"
        # de más abajo es el que describe SOLO el lote de esta corrida.
        "total_datasets_procesados": len(datasets),
        "total_clasificados_economia_finanzas": total_economia_finanzas,
        "total_recursos_con_data_api_confirmada": con_data_api,
        "datasets_nuevos_o_actualizados_en_esta_corrida": nuevos_esta_corrida,
        "errores_nuevos_en_esta_corrida": errores_esta_corrida,
        "metodo_clasificacion": "entidad publicadora conocida (ver ENTIDADES_ECONOMIA_FINANZAS); si no matchea, palabras clave en título/notas/tags (ver PALABRAS_CLAVE_ECONOMIA_FINANZAS)",
        "data_api_probado_para": args.probar_data_api,
        "errores": errores,
        "datasets": datasets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                         help="Procesar solo los primeros N datasets (contados desde --empezar-en) — para pruebas rápidas; el catálogo resultante quedará incompleto a propósito.")
    parser.add_argument("--empezar-en", type=int, default=0,
                         help="Saltar los primeros N datasets de package_list. Úsalo para CONTINUAR una corrida anterior que se cortó por tiempo: revisa 'siguiente_empezar_en' en el catalog.json de esa corrida y pásalo aquí.")
    parser.add_argument("--max-minutos", type=float, default=None,
                         help="Detener la corrida (guardando ordenadamente lo procesado hasta ese punto, con 'siguiente_empezar_en' listo para continuar) si supera este tiempo — en vez de dejar que GitHub Actions la mate de golpe sin guardar nada al llegar a su propio timeout-minutes. Recomendado: unos 10-15 minutos MENOS que el timeout-minutes del workflow.")
    parser.add_argument("--checkpoint-cada", type=int, default=200,
                         help="Guardar un catalog.json parcial cada N datasets procesados, además de al terminar — así una cancelación manual o una caída del runner (no solo el límite de tiempo, que ya se maneja con --max-minutos) pierde como máximo este número de datasets, no la corrida completa. 0 desactiva los checkpoints intermedios.")
    parser.add_argument("--pausa", type=float, default=0.2,
                         help="Segundos de espera entre peticiones a package_show (ser respetuosos con el servidor del portal). Default: 0.2s.")
    parser.add_argument("--probar-data-api", choices=["economia-finanzas", "todos", "ninguno"], default="economia-finanzas",
                         help="Para qué datasets probar en vivo si sus recursos tienen Data API. Default: solo los clasificados como Economía y Finanzas (ver docstring del módulo).")
    parser.add_argument("--out", default=OUT_PATH, help="Ruta de salida del catalog.json (para pruebas, sin pisar el real).")
    parser.add_argument("--reiniciar", action="store_true",
                         help="Ignora cualquier catalog.json existente y empieza desde un catálogo vacío (comportamiento del wipe-and-restart de antes del fix de acumulación). Uso raro — normalmente NO hace falta: el comportamiento por defecto ahora ya es acumular sobre lo existente, así que --empezar-en 0 también es seguro sin este flag.")
    args = parser.parse_args()

    inicio = time.time()

    if args.reiniciar:
        datasets_por_id, errores_por_id, total_portal_anterior = {}, {}, None
        print("--reiniciar: se ignora cualquier catalog.json existente, esta corrida empieza desde cero.", file=sys.stderr)
    else:
        datasets_por_id, errores_por_id, total_portal_anterior = cargar_catalogo_existente(args.out)

    try:
        todos_los_slugs = obtener_lista_slugs()
    except Exception as exc:
        print(f"ERROR: no se pudo obtener package_list: {exc}", file=sys.stderr)
        # OJO: si ya había un catálogo acumulado de corridas anteriores, NO
        # se pisa con un estado de error vacío — sería el mismo bug de
        # pérdida de datos que se acaba de arreglar, solo que disparado por
        # una falla de red en vez de por una corrida de continuación. Se
        # conserva tal cual estaba, con el error visible en el resumen.
        if datasets_por_id or errores_por_id:
            print(
                f"El catálogo ya tenía {len(datasets_por_id)} datasets y {len(errores_por_id)} errores "
                f"acumulados de corridas anteriores — se conservan tal cual.",
                file=sys.stderr,
            )
            summary = armar_summary(
                args,
                total_portal_anterior if total_portal_anterior is not None else (len(datasets_por_id) + len(errores_por_id)),
                args.empezar_en, 0,
                list(datasets_por_id.values()), list(errores_por_id.values()),
                cortado_por_tiempo=False,
                minutos_transcurridos=(time.time() - inicio) / 60,
                nuevos_esta_corrida=0, errores_esta_corrida=0,
            )
            summary["estado"] = "error"
            summary["error"] = f"package_list falló: {exc}"
            summary["corrida_completa"] = False
            summary["siguiente_empezar_en"] = args.empezar_en
        else:
            summary = {
                "fuente": "Catálogo del Portal Nacional de Datos Abiertos (PNDA)",
                "estado": "error",
                "error": f"package_list falló: {exc}",
                "datasets": [],
                "errores": [],
            }
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        write_summary(args.out, summary)
        sys.exit(1)

    total_portal = len(todos_los_slugs)
    slugs = todos_los_slugs[args.empezar_en:]
    if args.limit:
        slugs = slugs[:args.limit]
    print(
        f"package_list: {total_portal} datasets en el portal. Empezando en el índice {args.empezar_en}, "
        f"procesando {len(slugs)}... (catálogo acumulado ya tiene {len(datasets_por_id)} datasets de corridas anteriores)",
        file=sys.stderr,
    )

    cortado_por_tiempo = False
    intentados_esta_corrida = 0
    nuevos_esta_corrida = 0
    errores_esta_corrida = 0
    for i, slug in enumerate(slugs, 1):
        # NOTA: no se puede usar time.time() dentro de un script de workflow
        # de la herramienta Workflow (ahí está prohibido) — pero ESTE es un
        # script Python normal que corre como su propio proceso en GitHub
        # Actions, así que time.time() es válido y necesario aquí para el
        # límite de tiempo propio.
        if args.max_minutos is not None:
            minutos_transcurridos = (time.time() - inicio) / 60
            if minutos_transcurridos >= args.max_minutos:
                print(
                    f"  Se alcanzó --max-minutos ({args.max_minutos}) en el dataset {i}/{len(slugs)} "
                    f"— deteniendo ordenadamente y guardando lo procesado.",
                    file=sys.stderr,
                )
                cortado_por_tiempo = True
                break

        # TODO el procesamiento de un dataset (no solo el package_show) va
        # en un único try/except. Bug real encontrado en la primera corrida
        # contra el portal real (2026-08-22): para al menos un dataset,
        # package_show() respondió success=true pero su "result" vino como
        # una LISTA en vez de un objeto — algo que common.py no validaba
        # (solo validaba que el sobre {"success":...} fuera un dict, no que
        # "result" también lo fuera). Como clasificar_categoria() y
        # construir_entrada_dataset() esperan un dict y llamaban
        # .get(...) sobre él, esto tumbaba TODO el run con un
        # AttributeError sin capturar, en vez de registrarse como el error
        # de un solo dataset y seguir con los demás. Corregido en dos
        # frentes: aquí (todo el cuerpo del loop protegido) y en
        # common.py (package_show ahora valida el tipo de "result" antes
        # de devolverlo, con un error explícito y diagnosticable).
        intentados_esta_corrida += 1
        try:
            resultado = package_show(slug)
            categoria_preview, _ = clasificar_categoria(resultado)
            probar_este = (
                args.probar_data_api == "todos"
                or (args.probar_data_api == "economia-finanzas" and categoria_preview == "Economía y Finanzas")
            )
            entrada = construir_entrada_dataset(slug, resultado, probar_este)
            datasets_por_id[slug] = entrada
            errores_por_id.pop(slug, None)  # si antes había fallado y ahora funcionó, ya no es un error
            nuevos_esta_corrida += 1
        except Exception as exc:
            print(f"  [{i}/{len(slugs)}] ERROR en {slug!r}: {exc}", file=sys.stderr)
            errores_esta_corrida += 1
            if slug not in datasets_por_id:
                # Solo se registra el error si NO había ya un dato bueno
                # para este slug de una corrida anterior — así una falla
                # transitoria (ej. un timeout puntual) no borra un dataset
                # que ya se había descubierto bien antes.
                errores_por_id[slug] = {"dataset_id": slug, "error": str(exc)}
            else:
                print(f"    (ya había un dato bueno para {slug!r} de una corrida anterior — se conserva, no se pisa con este error)", file=sys.stderr)
            time.sleep(args.pausa)
            continue

        if i % 50 == 0 or i == len(slugs):
            econ_hasta_ahora = sum(1 for d in datasets_por_id.values() if d["categoria"] == "Economía y Finanzas")
            print(
                f"  [{i}/{len(slugs)}] procesados en esta corrida · {len(datasets_por_id)} acumulados en total · "
                f"{econ_hasta_ahora} clasificados como Economía y Finanzas hasta ahora",
                file=sys.stderr,
            )

        # Checkpoint intermedio — ver el --help de --checkpoint-cada. Se
        # guarda con cortado_por_tiempo=False y minutos_transcurridos
        # actuales; si la corrida sigue después sin cortarse, el archivo
        # final simplemente lo sobreescribe con el resultado completo.
        if args.checkpoint_cada and i % args.checkpoint_cada == 0 and i != len(slugs):
            minutos_transcurridos = (time.time() - inicio) / 60
            checkpoint = armar_summary(
                args, total_portal, args.empezar_en, intentados_esta_corrida,
                list(datasets_por_id.values()), list(errores_por_id.values()),
                cortado_por_tiempo=False, minutos_transcurridos=minutos_transcurridos,
                nuevos_esta_corrida=nuevos_esta_corrida, errores_esta_corrida=errores_esta_corrida,
            )
            checkpoint["estado"] = "parcial"
            checkpoint["corrida_completa"] = False
            checkpoint["siguiente_empezar_en"] = args.empezar_en + i  # checkpoint: "vamos en i", no el final
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
            write_summary(args.out, checkpoint)
            print(f"  [checkpoint guardado en {i}/{len(slugs)} — {len(datasets_por_id)} datasets acumulados en total]", file=sys.stderr)

        time.sleep(args.pausa)

    minutos_transcurridos = (time.time() - inicio) / 60
    summary = armar_summary(
        args, total_portal, args.empezar_en, intentados_esta_corrida,
        list(datasets_por_id.values()), list(errores_por_id.values()),
        cortado_por_tiempo, minutos_transcurridos,
        nuevos_esta_corrida=nuevos_esta_corrida, errores_esta_corrida=errores_esta_corrida,
    )
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_summary(args.out, summary)

    if summary["corrida_completa"]:
        print(
            f"Listo, CORRIDA COMPLETA: {len(datasets_por_id)} datasets acumulados en total "
            f"({nuevos_esta_corrida} nuevos/actualizados en esta corrida), "
            f"{summary['total_clasificados_economia_finanzas']} clasificados como Economía y Finanzas, "
            f"{summary['total_recursos_con_data_api_confirmada']} recursos con Data API confirmada, "
            f"{len(errores_por_id)} errores acumulados ({errores_esta_corrida} nuevos en esta corrida).",
            file=sys.stderr,
        )
    else:
        print(
            f"Corrida PARCIAL ({'cortada por --max-minutos' if cortado_por_tiempo else 'terminó su lote pero quedan datasets'}): "
            f"{nuevos_esta_corrida} datasets nuevos/actualizados en esta corrida ({len(datasets_por_id)} acumulados en total), "
            f"{errores_esta_corrida} errores nuevos en esta corrida. "
            f"Para continuar, vuelve a correr con --empezar-en {summary['siguiente_empezar_en']}.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
