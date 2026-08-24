#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bcrp_indicadores.py — Conector para "Indicadores para contabilidad": tipo
de cambio del día, tasa de referencia de política monetaria e inflación
(IPC), todos desde el API público de Series Estadísticas del Banco Central
de Reserva del Perú (BCRP).

POR QUÉ ESTA FUENTE (y no otra)
--------------------------------
Este conector nace de un problema real encontrado en `licitaciones/`: el
portal SEACE bloquea con HTTP 403 cualquier acceso automatizado, tanto
desde este entorno de desarrollo como desde los runners de GitHub Actions
— confirmado con dos corridas reales, no solo sospechado. El API del BCRP
es la fuente contraria: está construida para que cualquiera la consuma
por programa, sin llave, sin registro y sin bloqueo. Se verificó en vivo
antes de escribir este conector (con fetch real, no solo por documentación)
que responde JSON válido con valores reales.

Documentación oficial: https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api

CÓDIGOS DE SERIE USADOS (verificados uno por uno con una consulta real)
--------------------------------------------------------------------------
  PD04637PD / PD04638PD  - Tipo de cambio interbancario S/ por US$,
                            compra / venta (diaria). Confirmado: valores
                            entre 3.34 y 3.36 para agosto de 2026, con
                            huecos "n.d." en fines de semana y feriados
                            (normal — el BCRP no reporta esos días).
  PD04722MM              - Tasa de Referencia de la Política Monetaria
                            del BCRP (mensual). Confirmado: 4.25% para
                            jun/jul/ago 2026.
  PN01273PM / PN01271PM  - IPC Lima Metropolitana, variación % mensual y
                            variación % últimos 12 meses (mensual).
                            Confirmado: 0.29% mensual y 4.07% interanual
                            para julio 2026.

Por qué estos códigos y no otros: el API del BCRP no tiene una búsqueda
por texto que se pueda llamar por programa (existe una página de búsqueda
interactiva, no una API de búsqueda), así que cada código se obtuvo
navegando las páginas de "series mensuales/diarias" del propio BCRP y se
confirmó pidiendo ese código exacto al API — no se adivinó ninguno.

QUÉ NO HACE (a propósito)
--------------------------
No interpreta ni proyecta nada: si un indicador no viene en la ventana de
fechas consultada (por ejemplo, si el BCRP todavía no publicó el dato del
mes en curso), ese indicador queda en `null` en la salida — nunca se
repite el último valor conocido haciéndolo pasar por el dato de hoy, ni
se inventa una tendencia. Cada indicador que sí se pudo obtener trae su
propio `periodo` (la fecha/mes que el BCRP le asignó), así que el
frontend siempre puede mostrar honestamente de cuándo es el dato.

SALIDA
------
data/indicadores_bcrp.json — un resumen con como mucho 3 indicadores
(tipo_cambio, tasa_referencia, inflacion), cada uno con su período real o
`null` si no se pudo obtener, más `generado_en` (agregado automáticamente
por `write_summary`).

USO
---
  python3 connectors/bcrp_indicadores.py
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import http_get, write_summary

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "indicadores_bcrp.json")

BCRP_BASE = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
BCRP_SERIES_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/"

SERIES_TC = ["PD04637PD", "PD04638PD"]          # compra, venta (diaria)
SERIES_TASA_REFERENCIA = ["PD04722MM"]          # mensual
SERIES_IPC = ["PN01273PM", "PN01271PM"]         # var% mensual, var% 12 meses (mensual)


def fmt_fecha(d):
    """Formatea una fecha al formato que espera el API del BCRP
    (AAAA-M-D, sin ceros a la izquierda)."""
    return f"{d.year}-{d.month}-{d.day}"


def fetch_bcrp_series(codigos, date_ini, date_fin):
    """Descarga una o más series del API público del BCRP para una ventana
    de fechas. Nunca lanza: si algo falla (red, formato inesperado), avisa
    por stderr y devuelve None — quien llama decide cómo degradar.

    Devuelve {"series_names": [...], "periodos": [{"periodo": str,
    "valores": [float|None, ...]}, ...]} en el mismo orden que `codigos`.
    """
    codigo_url = "-".join(codigos)
    url = f"{BCRP_BASE}/{codigo_url}/json/{date_ini}/{date_fin}/esp"
    try:
        resp = http_get(url, timeout=30, max_retries=3)
        data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"  ERROR consultando BCRP ({codigo_url}): {exc}", file=sys.stderr)
        return None

    try:
        series_names = [s.get("name") for s in data.get("config", {}).get("series", [])]
        periodos = []
        for p in data.get("periods", []):
            valores = []
            for v in p.get("values", []):
                try:
                    valores.append(float(v))
                except (TypeError, ValueError):
                    valores.append(None)  # "n.d." u otro valor no numérico
            periodos.append({"periodo": p.get("name"), "valores": valores})
        return {"series_names": series_names, "periodos": periodos}
    except Exception as exc:
        print(f"  ERROR interpretando la respuesta del BCRP ({codigo_url}): {exc}", file=sys.stderr)
        return None


def ultimo_periodo_completo(resultado, cuantos_valores):
    """Devuelve (periodo, [valores]) del período MÁS RECIENTE que tenga
    los primeros `cuantos_valores` valores presentes (no None) — así, para
    series que se muestran juntas (compra+venta, mensual+anual), nunca se
    mezclan dos fechas distintas. Si no hay ninguno así, (None, None)."""
    if not resultado:
        return None, None
    for p in reversed(resultado["periodos"]):
        valores = p["valores"][:cuantos_valores]
        if len(valores) == cuantos_valores and all(v is not None for v in valores):
            return p["periodo"], valores
    return None, None


def main():
    ahora = datetime.datetime.now(datetime.timezone.utc)
    ini_diaria = ahora - datetime.timedelta(days=30)
    ini_mensual = ahora - datetime.timedelta(days=150)

    resultado = {
        "fuente": "Banco Central de Reserva del Perú (BCRP) — API pública de Series Estadísticas",
        "atribucion": "Banco Central de Reserva del Perú (BCRP).",
        "dataset_url": BCRP_SERIES_URL,
    }

    tc = fetch_bcrp_series(SERIES_TC, fmt_fecha(ini_diaria), fmt_fecha(ahora))
    periodo_tc, valores_tc = ultimo_periodo_completo(tc, 2)
    if periodo_tc is not None:
        resultado["tipo_cambio"] = {
            "periodo": periodo_tc,
            "compra": round(valores_tc[0], 3),
            "venta": round(valores_tc[1], 3),
            "unidad": "S/ por US$",
            "descripcion": "Tipo de cambio interbancario, BCRP",
        }
    else:
        resultado["tipo_cambio"] = None
        print("  AVISO: no se pudo obtener un tipo de cambio válido del BCRP en los últimos 30 días.", file=sys.stderr)

    tasa = fetch_bcrp_series(SERIES_TASA_REFERENCIA, fmt_fecha(ini_mensual), fmt_fecha(ahora))
    periodo_tasa, valores_tasa = ultimo_periodo_completo(tasa, 1)
    if periodo_tasa is not None:
        resultado["tasa_referencia"] = {
            "periodo": periodo_tasa,
            "valor_pct": round(valores_tasa[0], 2),
            "descripcion": "Tasa de Referencia de la Política Monetaria, BCRP",
        }
    else:
        resultado["tasa_referencia"] = None
        print("  AVISO: no se pudo obtener la tasa de referencia del BCRP en los últimos 5 meses.", file=sys.stderr)

    ipc = fetch_bcrp_series(SERIES_IPC, fmt_fecha(ini_mensual), fmt_fecha(ahora))
    periodo_ipc, valores_ipc = ultimo_periodo_completo(ipc, 2)
    if periodo_ipc is not None:
        resultado["inflacion"] = {
            "periodo": periodo_ipc,
            "variacion_mensual_pct": round(valores_ipc[0], 2),
            "variacion_12_meses_pct": round(valores_ipc[1], 2),
            "descripcion": "IPC Lima Metropolitana (INEI, vía BCRP)",
        }
    else:
        resultado["inflacion"] = None
        print("  AVISO: no se pudo obtener la inflación del BCRP en los últimos 5 meses.", file=sys.stderr)

    indicadores_ok = [k for k in ("tipo_cambio", "tasa_referencia", "inflacion") if resultado.get(k)]
    resultado["estado"] = "ok" if indicadores_ok else "sin_datos"
    resultado["indicadores_disponibles"] = indicadores_ok

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    write_summary(OUT_PATH, resultado)
    print(f"Indicadores obtenidos: {indicadores_ok or '(ninguno)'}", file=sys.stderr)


if __name__ == "__main__":
    main()
