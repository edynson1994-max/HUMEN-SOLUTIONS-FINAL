#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py — corre todos los conectores de "Perú en Datos" en orden y
reporta un resumen final de qué funcionó y qué no. Pensado para correr
tanto localmente como desde GitHub Actions.

No revienta si un conector falla — cada uno ya maneja sus propios errores y
escribe "estado":"error" en su JSON de salida en vez de lanzar una
excepción sin capturar. Este script solo orquesta y da un resumen legible.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")

CONECTORES = [
    ("Contraloría", "contraloria.py", "contraloria.json"),
    ("INEI — RENAMU", "inei_renamu.py", "inei_renamu.json"),
    ("MEF — Gasto devengado", "mef.py", "mef.json"),
]


def main():
    mef_max_mb = os.environ.get("MEF_MAX_MB")  # útil para acotar en pruebas/CI limitado
    resultados = []

    for nombre, script, out_file in CONECTORES:
        print(f"\n=== {nombre} ===", file=sys.stderr)
        cmd = [sys.executable, os.path.join(HERE, script)]
        if script == "mef.py" and mef_max_mb:
            cmd += ["--max-mb", mef_max_mb]
        proc = subprocess.run(cmd)
        out_path = os.path.join(DATA_DIR, out_file)
        estado = "desconocido"
        if os.path.exists(out_path):
            try:
                with open(out_path, encoding="utf-8") as f:
                    payload = json.load(f)
                # el estado puede estar en la raíz (mef/inei) o por dataset (contraloría)
                if "estado" in payload:
                    estado = payload["estado"]
                elif "datasets" in payload:
                    estados = {d.get("estado") for d in payload["datasets"]}
                    estado = "ok" if estados == {"ok"} else f"parcial ({estados})"
            except Exception as exc:
                estado = f"json inválido: {exc}"
        elif proc.returncode != 0:
            estado = f"el script terminó con código {proc.returncode} y no escribió salida"
        resultados.append((nombre, estado))

    print("\n=== Resumen ===", file=sys.stderr)
    for nombre, estado in resultados:
        print(f"  {nombre}: {estado}", file=sys.stderr)


if __name__ == "__main__":
    main()
