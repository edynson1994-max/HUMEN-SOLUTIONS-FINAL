#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
print_summary.py — lee todos los data/*.json que dejaron los conectores y
imprime un resumen en Markdown (pensado para $GITHUB_STEP_SUMMARY, pero
funciona igual de bien corrido a mano en la terminal).

Se separó a su propio archivo a propósito: meter un script de Python de
varias líneas directamente dentro de un bloque `run: |` de un workflow de
GitHub Actions es frágil (la indentación de YAML y la de Python chocan) —
así se evita ese problema por completo.
"""

import glob
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def resumir_archivo(path):
    nombre = os.path.basename(path)
    print(f"- **{nombre}**")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as exc:
        print(f"  - no se pudo leer: {exc}")
        return

    if "estado" in d:
        print(f"  - estado: {d.get('estado')}")
        if d.get("estado") == "error":
            print(f"  - error: {d.get('error')}")
        if "columnas_detectadas" in d:
            print(f"  - columnas detectadas: {d.get('columnas_detectadas')}")
    elif "datasets" in d:
        for ds in d["datasets"]:
            linea = f"  - {ds.get('titulo')}: {ds.get('estado')}"
            if ds.get("estado") == "error":
                linea += f" ({ds.get('error')})"
            print(linea)


def main():
    archivos = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    print("### Estado de cada fuente\n")
    if not archivos:
        print("- no se encontró ningún data/*.json")
        return
    for path in archivos:
        resumir_archivo(path)


if __name__ == "__main__":
    main()
