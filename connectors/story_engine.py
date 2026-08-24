#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
story_engine.py — Fase 12 de "Perú en Datos": historias candidatas.

Lee data/analytics/economia-finanzas.json (Fase 7) y
data/cambios_recientes.json (Fase 6) — ambos YA calculados, este script
no vuelve a tocar ningún dataset ni recalcula nada — y arma
data/stories/candidatas.json: una lista de "historias candidatas"
ESTRUCTURADAS, cada una con sus hechos numéricos reales por separado
(`hechos`) y una frase armada por plantilla (`resumen_estructurado`) que
solo rellena números ya calculados, sin agregar ninguna interpretación
nueva.

QUÉ ES Y QUÉ NO ES ESTO (a propósito, según el plan de Fase 1, sección
5, fila de la Fase 12)
-----------------------------------------------------------------------
Esto NO es redacción de historias — no hay ningún texto "creativo" ni
generado por un modelo de lenguaje aquí, a propósito. Es la etapa
anterior: transformar los rankings/variaciones ya calculados por
analytics.py en candidatas discretas y priorizadas, cada una con TODOS
los números que la sustentan expuestos por separado en `hechos` (para
que una redacción asistida por IA, en una fase posterior, tenga de
dónde tomar cifras exactas en vez de inventarlas). `resumen_estructurado`
es deliberadamente mecánico (una plantilla con espacios en blanco
rellenados), no una historia — lo suficiente para mostrar algo legible
en la sección "Estelares"/"Descubre" sin esperar a la fase de redacción.

TIPOS DE CANDIDATA
-------------------
- "mayor_aumento" / "mayor_disminucion": de analytics.variaciones
  (hasta TOP_POR_TIPO cada una).
- "mas_datos": los datasets con más filas sincronizadas
  (analytics.filas.ranking_mas_filas).
- "cobertura_catalogo": UNA candidata sobre el estado del catálogo
  mismo (cuántos datasets de Economía y Finanzas se conocen, si el
  descubrimiento está completo) — se omite si no hay datos de catálogo.
- "nuevas_conexiones": UNA candidata sobre cuántos datasets se
  sincronizaron por primera vez en la corrida más reciente (de
  cambios_recientes.json) — se omite si es 0.

Cada candidata trae `prioridad` (para que el frontend elija cuáles
mostrar primero sin tener que reordenar nada) — mayor |diferencia_pct|
o mayor conteo, sin ningún criterio editorial no verificable.

USO
---
  python3 connectors/story_engine.py
  # -> escribe data/stories/candidatas.json
"""
import argparse
import datetime
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
ANALYTICS_PATH = os.path.join(DATA_DIR, "analytics", "economia-finanzas.json")
CAMBIOS_PATH = os.path.join(DATA_DIR, "cambios_recientes.json")
OUT_PATH = os.path.join(DATA_DIR, "stories", "candidatas.json")

TOP_POR_TIPO = 3


def _cargar(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _pct_fmt(pct):
    if pct is None:
        return "—"
    signo = "+" if pct >= 0 else ""
    return f"{signo}{pct:.1f}%".replace(".", ",")


def _candidatas_variacion(analytics, tipo, etiqueta_direccion):
    var = (analytics or {}).get("variaciones", {})
    clave = "ranking_mayor_aumento_pct" if tipo == "mayor_aumento" else "ranking_mayor_disminucion_pct"
    out = []
    for v in var.get(clave, [])[:TOP_POR_TIPO]:
        hechos = {
            "dataset_id": v["dataset_id"],
            "filas_antes": v.get("filas_antes"),
            "filas_despues": v.get("filas_despues"),
            "diferencia": v.get("diferencia"),
            "diferencia_pct": v.get("diferencia_pct"),
        }
        out.append({
            "id": f"{tipo}-{v['dataset_id']}",
            "tipo": tipo,
            "dataset_id": v["dataset_id"],
            "titulo": v.get("titulo") or v["dataset_id"],
            "entidad": v.get("entidad"),
            "hechos": hechos,
            "resumen_estructurado": (
                f"\"{v.get('titulo') or v['dataset_id']}\""
                + (f" ({v['entidad']})" if v.get("entidad") else "")
                + f" {etiqueta_direccion} de {hechos['filas_antes']} a {hechos['filas_despues']} filas "
                + f"({_pct_fmt(hechos['diferencia_pct'])}) en su última sincronización."
            ),
            "prioridad": abs(hechos["diferencia_pct"]) if hechos["diferencia_pct"] is not None else 0,
        })
    return out


def _candidatas_mas_datos(analytics):
    filas = (analytics or {}).get("filas", {})
    out = []
    for d in filas.get("ranking_mas_filas", [])[:TOP_POR_TIPO]:
        out.append({
            "id": f"mas_datos-{d['dataset_id']}",
            "tipo": "mas_datos",
            "dataset_id": d["dataset_id"],
            "titulo": d.get("titulo") or d["dataset_id"],
            "entidad": d.get("entidad"),
            "hechos": {"filas": d.get("filas")},
            "resumen_estructurado": (
                f"\"{d.get('titulo') or d['dataset_id']}\""
                + (f" ({d['entidad']})" if d.get("entidad") else "")
                + f" es, por ahora, el dataset con más filas sincronizadas: {d.get('filas'):,}".replace(",", ".")
                + "."
            ),
            "prioridad": d.get("filas") or 0,
        })
    return out


def _candidata_cobertura(analytics):
    cat = (analytics or {}).get("catalogo", {})
    total_portal = cat.get("total_datasets_portal")
    total_categoria = cat.get("total_clasificados_en_categoria")
    if total_portal is None or total_categoria is None:
        return None
    completa = cat.get("catalogo_corrida_completa")
    estado_txt = "completo" if completa else "parcial — todavía se está descubriendo el resto del portal"
    return {
        "id": "cobertura_catalogo",
        "tipo": "cobertura_catalogo",
        "dataset_id": None,
        "titulo": "Cobertura del catálogo de Economía y Finanzas",
        "entidad": None,
        "hechos": {
            "total_datasets_portal": total_portal,
            "total_clasificados_en_categoria": total_categoria,
            "catalogo_corrida_completa": bool(completa),
        },
        "resumen_estructurado": (
            f"Perú en Datos conoce {total_categoria} datasets de Economía y Finanzas "
            f"de los {total_portal} que tiene registrados el Portal Nacional de Datos Abiertos "
            f"(descubrimiento {estado_txt})."
        ),
        "prioridad": total_categoria,
    }


def _candidata_nuevas_conexiones(cambios):
    n = (cambios or {}).get("total_primera_sincronizacion")
    if not n:
        return None
    return {
        "id": "nuevas_conexiones",
        "tipo": "nuevas_conexiones",
        "dataset_id": None,
        "titulo": "Nuevos datasets sincronizados",
        "entidad": None,
        "hechos": {"total_primera_sincronizacion": n},
        "resumen_estructurado": f"{n} dataset(s) se sincronizaron por primera vez en la corrida más reciente.",
        "prioridad": n,
    }


def generar(analytics_path=ANALYTICS_PATH, cambios_path=CAMBIOS_PATH):
    analytics = _cargar(analytics_path)
    cambios = _cargar(cambios_path)

    candidatas = []
    candidatas += _candidatas_variacion(analytics, "mayor_aumento", "aumentó")
    candidatas += _candidatas_variacion(analytics, "mayor_disminucion", "disminuyó")
    candidatas += _candidatas_mas_datos(analytics)
    c = _candidata_cobertura(analytics)
    if c:
        candidatas.append(c)
    c = _candidata_nuevas_conexiones(cambios)
    if c:
        candidatas.append(c)

    candidatas.sort(key=lambda c: c["prioridad"], reverse=True)

    return {
        "generado_en": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuentes": {
            "analytics_generado_en": (analytics or {}).get("generado_en"),
            "cambios_generado_en": (cambios or {}).get("generado_en"),
        },
        "total_candidatas": len(candidatas),
        "candidatas": candidatas,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--analytics", default=ANALYTICS_PATH)
    parser.add_argument("--cambios", default=CAMBIOS_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    resultado = generar(analytics_path=args.analytics, cambios_path=args.cambios)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"{resultado['total_candidatas']} historias candidatas generadas.", file=sys.stderr)


if __name__ == "__main__":
    main()
