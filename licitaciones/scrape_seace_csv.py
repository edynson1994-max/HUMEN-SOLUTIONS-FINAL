#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_seace_csv.py — Descarga automáticamente, con un navegador real
(Playwright), el CSV que exporta directamente el propio portal SEACE
"Oportunidades de Negocio v2.0":

    https://prod4.seace.gob.pe/openegocio/#/georeferenciacion

Esta es LA MISMA fuente que el CSV que subiste a mano (mismo formato exacto
que ya entiende csv_to_data.py — el mismo parser probado con tus 197
convocatorias reales de Cusco). La diferencia es que este script hace clic en
el botón "CSV" de la página por ti, en vez de que lo descargues y me lo subas
a mano cada vez.

POR QUÉ TODAVÍA NO ESTÁ CONFIRMADO QUE FUNCIONE EN GITHUB ACTIONS
--------------------------------------------------------------------
Este dominio (prod4.seace.gob.pe) devolvió error 403 cuando lo probé desde mi
propio entorno de trabajo, igual que contratacionesabiertas.oece.gob.pe — pero
ese otro sí logró abrir la página real desde GitHub Actions (falló más
adelante, esperando un elemento). Es razonable pensar que este dominio se
comporte parecido: puede que SÍ cargue desde GitHub Actions aunque no cargue
desde mi entorno. Aun así, los selectores de abajo (el botón "CSV" en
particular) son un borrador basado únicamente en tus capturas de pantalla, no
en inspección real del DOM — puede hacer falta ajustar tras la primera
corrida real, igual que pasó con scrape_oece.py.

QUÉ HACE
--------
1. Abre la página de "Oportunidades de Negocio v2.0" (sin aplicar ningún
   filtro — para traer cobertura nacional completa, no solo un departamento,
   como corresponde al banco de información público para todos).
2. Espera a que la tabla de resultados termine de cargar.
3. Le da clic al botón "CSV" e intercepta la descarga.
4. Guarda el .csv descargado en la carpeta de salida.

El .csv resultante se pasa después DIRECTO a csv_to_data.py — no hace falta
ningún conversor nuevo, porque el formato ya es exactamente el que ese script
espera:

    python3 scrape_seace_csv.py --out descargas/
    python3 csv_to_data.py descargas/*.csv

USO
---
    python3 scrape_seace_csv.py --out descargas/
    python3 scrape_seace_csv.py --out descargas/ --headed   # SOLO con pantalla
                                                              # real, nunca en CI

Si algo falla, siempre se guardan descargas/screenshot_error.png y
descargas/page_error.html con el estado de la página en ese momento, además
de imprimir el título y el texto visible de la página en el log.
"""

import argparse
import os
import sys

RESULTS_URL = "https://prod4.seace.gob.pe/openegocio/#/georeferenciacion"


def find_chromium():
    candidate = "/opt/pw-browsers/chromium"
    return candidate if os.path.exists(candidate) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="descargas", help="Carpeta donde guardar el .csv descargado.")
    parser.add_argument("--headed", action="store_true", help="Navegador visible, SOLO para depurar con pantalla real. NO usar en CI.")
    parser.add_argument("--timeout", type=int, default=90000, help="Timeout en ms para cada espera de Playwright (la tabla puede tardar; 234+ filas).")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Falta playwright. Instala con: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)

    launch_kwargs = {"headless": not args.headed}
    chromium_path = find_chromium()
    if chromium_path:
        launch_kwargs["executable_path"] = chromium_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(
            viewport={"width": 1400, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page.set_default_timeout(args.timeout)

        try:
            print(f"Abriendo {RESULTS_URL} ...", file=sys.stderr)
            page.goto(RESULTS_URL, wait_until="networkidle")

            # Esperamos el texto que la propia página muestra cuando termina de
            # cargar resultados ("Se encontraron N oportunidades de negocio...").
            # Si el sitio cambia esa frase, esto va a fallar y el diagnóstico de
            # abajo (título + texto visible) va a mostrar qué dice en realidad.
            print("Esperando a que carguen los resultados ...", file=sys.stderr)
            page.wait_for_selector("text=oportunidades de negocio", timeout=args.timeout)

            print("Descargando CSV ...", file=sys.stderr)
            csv_button = page.locator("text=CSV").first
            with page.expect_download(timeout=args.timeout) as download_info:
                csv_button.click()
            download = download_info.value

            suggested = download.suggested_filename or "seace_openegocio.csv"
            out_path = os.path.join(args.out, suggested)
            download.save_as(out_path)
            print(f"Listo: guardado en {out_path}", file=sys.stderr)
            print(out_path)

        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            try:
                print(f"  URL final: {page.url}", file=sys.stderr)
                print(f"  Título de la página: {page.title()!r}", file=sys.stderr)
                body_text = page.evaluate("document.body ? document.body.innerText : ''")
                snippet = " ".join(body_text.split())[:600]
                print(f"  Primeros ~600 caracteres de texto visible: {snippet!r}", file=sys.stderr)
            except Exception as diag_exc:
                print(f"  (no se pudo leer título/texto de la página: {diag_exc})", file=sys.stderr)

            shot_path = os.path.join(args.out, "screenshot_error.png")
            try:
                page.screenshot(path=shot_path, full_page=True)
                print(f"  (screenshot guardada en {shot_path} para depurar)", file=sys.stderr)
            except Exception:
                pass

            html_path = os.path.join(args.out, "page_error.html")
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"  (HTML completo guardado en {html_path} para depurar)", file=sys.stderr)
            except Exception:
                pass

            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
