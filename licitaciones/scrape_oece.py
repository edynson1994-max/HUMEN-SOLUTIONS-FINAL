#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_oece.py — Descarga automáticamente, con un navegador real (Playwright),
el archivo mensual de "entregas compiladas" (compiled releases) en formato
OCDS que publica el propio portal oficial peruano:

    https://contratacionesabiertas.oece.gob.pe/descargas

Por qué un navegador real y no un simple `requests.get()`
-----------------------------------------------------------
Ya se comprobó (para el portal SEACE "Oportunidades de Negocio" y también
para este mismo dominio oece.gob.pe) que las peticiones HTTP simples reciben
403 — hay protección anti-bot delante. Un navegador real (headless) tiene
muchas más chances de pasar esa protección porque ejecuta JavaScript, manda
las cabeceras típicas de un navegador de verdad, etc. Aun así, ESTO NO SE HA
PODIDO PROBAR EN VIVO desde el entorno donde se escribió este script — no hay
salida de red hacia este dominio desde ahí. Los selectores de abajo son un
borrador basado únicamente en capturas de pantalla de la página, no en una
inspección real del DOM. Es muy probable que haga falta un round de ajustes
mirando el error real (correrlo en GitHub Actions con `workflow_dispatch` y
revisar el log/artifact de depuración, o localmente con `--headed` si hay una
pantalla real disponible — nunca `--headed` en CI, ver más abajo).

QUÉ HACE
--------
1. Abre https://contratacionesabiertas.oece.gob.pe/descargas con Playwright.
2. Localiza, en la tabla de archivos disponibles, la fila que corresponde al
   año/mes pedido (por defecto: la fila más reciente, que la propia página ya
   muestra primero — no hace falta tocar los filtros de Año/Mes).
3. Le da clic al link "JSON" de esa fila e intercepta la descarga (según el
   texto de la propia página, el archivo baja comprimido en .zip).
4. Guarda el .zip descargado en la carpeta de salida.

El .zip resultante se pasa luego a oece_json_to_data.py, que reutiliza el
mismo parser de OCDS que ya usa sync.py (misma lógica de vigencia, etiquetas
Humen, etc. — sin duplicar código ni volver a introducir los mismos bugs que
ya se corrigieron ahí).

USO
---
    pip install playwright
    playwright install chromium   # (en este sandbox NO hace falta: ya está
                                   #  preinstalado en /opt/pw-browsers)

    python3 scrape_oece.py --out descargas/
    python3 scrape_oece.py --out descargas/ --year 2026 --month 8
    python3 scrape_oece.py --out descargas/ --headed    # SOLO con pantalla real
                                                          # (no en GitHub Actions)

Si algo falla, siempre se guarda descargas/screenshot_error.png con el estado
de la página en ese momento — corra o no con --headed.
"""

import argparse
import os
import sys
import time

DESCARGAS_URL = "https://contratacionesabiertas.oece.gob.pe/descargas"

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Setiembre", 10: "Octubre", 11: "Noviembre",
    12: "Diciembre",
}


def find_chromium():
    # En este sandbox el navegador viene preinstalado en esta ruta fija
    # (ver notas del entorno). En GitHub Actions no existirá — ahí Playwright
    # debe correr `playwright install --with-deps chromium` primero, y en ese
    # caso simplemente se usa el Chromium que Playwright gestiona por su cuenta.
    candidate = "/opt/pw-browsers/chromium"
    return candidate if os.path.exists(candidate) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="descargas", help="Carpeta donde guardar el .zip descargado.")
    parser.add_argument("--year", type=int, default=None, help="Año a buscar en la tabla (por defecto: el más reciente disponible).")
    parser.add_argument("--month", type=int, default=None, help="Mes (1-12) a buscar en la tabla (por defecto: el más reciente disponible).")
    parser.add_argument("--formato", default="JSON", choices=["JSON", "CSV", "XLSX"], help="Formato de archivo a descargar.")
    parser.add_argument("--headed", action="store_true", help="Corre con el navegador visible (no headless), SOLO para depurar en una máquina con pantalla real. NO usar en GitHub Actions / CI: no hay servidor X y el navegador falla al abrir (TargetClosedError).")
    parser.add_argument("--timeout", type=int, default=60000, help="Timeout en ms para cada espera de Playwright.")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Falta playwright. Instala con: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)

    target_year = str(args.year) if args.year else None
    target_month_name = MESES[args.month] if args.month else None

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
        page.set_default_timeout(args.timeout)

        try:
            print(f"Abriendo {DESCARGAS_URL} ...", file=sys.stderr)
            page.goto(DESCARGAS_URL, wait_until="networkidle")

            # Esperamos a que aparezca al menos una fila con un link "JSON"
            # (evita interactuar con los selects de filtro, que son el punto
            # más frágil/incierto de la página — no hace falta tocarlos si
            # simplemente queremos la fila más reciente, que ya sale primero).
            page.wait_for_selector("text=JSON", timeout=args.timeout)

            # Buscamos la fila (tr, o el contenedor equivalente) que contiene
            # el año y mes buscados. Si no se pidió año/mes específico, se usa
            # la primera fila con un link "JSON" — la tabla ya viene ordenada
            # con lo más reciente arriba, según las capturas de la página.
            rows = page.locator("tr").filter(has=page.locator("text=JSON"))
            row_count = rows.count()
            print(f"  {row_count} filas con descarga JSON encontradas", file=sys.stderr)
            if row_count == 0:
                raise RuntimeError("No se encontró ninguna fila con un link 'JSON' en la tabla de descargas.")

            target_row = None
            if target_year or target_month_name:
                for i in range(row_count):
                    row = rows.nth(i)
                    text = row.inner_text()
                    if target_year and target_year not in text:
                        continue
                    if target_month_name and target_month_name not in text:
                        continue
                    target_row = row
                    break
                if target_row is None:
                    raise RuntimeError(
                        f"No se encontró una fila para {target_month_name or ''} {target_year or ''} "
                        "en la primera página de la tabla. Puede que haga falta paginar "
                        "(la tabla tiene más de una página) — no implementado aún."
                    )
            else:
                target_row = rows.nth(0)
                print(f"  usando la fila más reciente: {target_row.inner_text()[:80]!r}", file=sys.stderr)

            link = target_row.locator(f"text={args.formato}").first

            print(f"Descargando formato {args.formato} ...", file=sys.stderr)
            with page.expect_download(timeout=args.timeout) as download_info:
                link.click()
            download = download_info.value

            suggested = download.suggested_filename or f"oece_{args.formato.lower()}.zip"
            out_path = os.path.join(args.out, suggested)
            download.save_as(out_path)
            print(f"Listo: guardado en {out_path}", file=sys.stderr)
            print(out_path)  # también a stdout, para que un script llamador lo capture fácilmente

        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            # Intento de screenshot SIEMPRE (no solo en --headed) — es la principal
            # pista para depurar cuando esto corre en CI, donde nadie está mirando
            # el navegador en vivo. Es un intento "best effort": si la página ya
            # se cerró (p.ej. el propio error fue que el navegador no pudo abrir),
            # simplemente no habrá screenshot y no debe tumbar el script por eso.
            shot_path = os.path.join(args.out, "screenshot_error.png")
            try:
                page.screenshot(path=shot_path, full_page=True)
                print(f"  (screenshot guardada en {shot_path} para depurar)", file=sys.stderr)
            except Exception:
                pass
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
