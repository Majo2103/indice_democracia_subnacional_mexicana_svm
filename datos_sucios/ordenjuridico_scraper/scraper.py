# ============================================================
# scraper.py — Script principal.
#
# Uso:
#   python scraper.py                        → estados de prueba (config.py)
#   python scraper.py --todos                → 32 estados
#   python scraper.py --estado 14            → solo Jalisco
#   python scraper.py --estado 21 --termino "codigo penal"
# ============================================================

import os
import csv
import logging
import argparse
import requests
from datetime import datetime

from config import (
    ESTADOS, TERMINOS_BUSQUEDA, ESTADOS_PRUEBA,
    CARPETA_PDFS, CARPETA_HTMLS, CARPETA_DOCS,
    CARPETA_LOGS, CARPETA_DATOS, BASE_URL
)
from parser import (
    construir_url_busqueda, parsear_resultados_busqueda,
    parsear_ficha, extraer_paginacion
)
from descargador import decidir_carpeta_y_descargar, guardar_html, get_pagina


# -------------------------------------------------------
# Crear carpetas necesarias
# -------------------------------------------------------
def crear_carpetas():
    """Crea todas las carpetas si no existen."""
    for carpeta in [CARPETA_PDFS, CARPETA_HTMLS, CARPETA_DOCS, CARPETA_LOGS, CARPETA_DATOS]:
        os.makedirs(carpeta, exist_ok=True)


# -------------------------------------------------------
# Logging: archivo + consola
# -------------------------------------------------------
def configurar_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_log = os.path.join(CARPETA_LOGS, f"scraper_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(archivo_log, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Log: {archivo_log}")


# -------------------------------------------------------
# CSV de inventario
# -------------------------------------------------------
def iniciar_csv():
    """Crea el CSV donde se registra cada documento."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(CARPETA_DATOS, f"inventario_{timestamp}.csv")

    with open(ruta, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "estado", "id_estado", "termino", "id_archivo",
            "titulo", "url_ficha", "url_documento",
            "tipo", "fecha_publicacion", "ruta_local"
        ])

    logging.info(f"CSV: {ruta}")
    return ruta


def registrar_en_csv(ruta_csv, estado, id_estado, termino, ordenamiento, ficha, ruta_local):
    """Agrega una fila al CSV."""
    with open(ruta_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            estado,
            id_estado,
            termino,
            ordenamiento.get("id_archivo", ""),
            ordenamiento.get("titulo", ""),
            ordenamiento.get("url_ficha", ""),
            ficha.get("url_documento", ""),
            ficha.get("tipo", ""),
            ficha.get("fecha_publicacion", ""),
            ruta_local or "",
        ])


# -------------------------------------------------------
# Lógica principal de scraping
# -------------------------------------------------------
def scrapear_estado_termino(session, id_estado, nombre_estado, termino, ruta_csv):
    """
    Flujo completo para un estado y término:
      1. Página de búsqueda  → extrae idArchivo de los links JS
      2. Página de ficha     → extrae URL del documento real
      3. Descarga el archivo → lo guarda en disco
    """
    logging.info(f"--- '{termino}' en {nombre_estado} ---")

    url_busqueda = construir_url_busqueda(termino, id_estado)
    urls_pendientes = [url_busqueda]
    urls_vistas = set()
    docs_descargados = 0

    while urls_pendientes:
        url_actual = urls_pendientes.pop(0)
        if url_actual in urls_vistas:
            continue
        urls_vistas.add(url_actual)

        # --- PASO 1: descargar y guardar página de resultados ---
        logging.info(f"Resultados: {url_actual}")
        html_resultados = get_pagina(url_actual, session)
        if not html_resultados:
            continue

        # Guardar HTML de la página de resultados
        nombre_html = (
            f"{nombre_estado.replace(' ','_')}_"
            f"{termino.replace(' ','_')}_"
            f"pag{len(urls_vistas)}.html"
        )
        guardar_html(html_resultados, nombre_html, CARPETA_HTMLS)

        # Extraer ordenamientos (id_archivo + titulo + url_ficha)
        ordenamientos = parsear_resultados_busqueda(html_resultados)
        logging.info(f"  → {len(ordenamientos)} ordenamientos encontrados")

        for ord_item in ordenamientos:

            # --- PASO 2: descargar y parsear la ficha ---
            url_ficha = ord_item["url_ficha"]
            html_ficha = get_pagina(url_ficha, session)

            if not html_ficha:
                registrar_en_csv(ruta_csv, nombre_estado, id_estado,
                                 termino, ord_item, {}, None)
                continue

            # Guardar HTML de la ficha
            nombre_ficha_html = f"ficha_{ord_item['id_archivo']}.html"
            guardar_html(html_ficha, nombre_ficha_html, CARPETA_HTMLS)

            # Extraer URL del documento real
            ficha = parsear_ficha(html_ficha, ord_item["id_archivo"])

            # --- PASO 3: descargar el documento ---
            ruta_local = None
            if ficha.get("url_documento"):
                ruta_local = decidir_carpeta_y_descargar(
                    ficha["url_documento"], session
                )
                if ruta_local:
                    docs_descargados += 1

            registrar_en_csv(ruta_csv, nombre_estado, id_estado,
                             termino, ord_item, ficha, ruta_local)

            logging.info(
                f"  [{ord_item['id_archivo']}] {ord_item['titulo'][:60]} "
                f"→ {ficha.get('tipo','?')} {'✓' if ruta_local else '✗'}"
            )

        # Verificar paginación
        for pag in extraer_paginacion(html_resultados):
            if pag not in urls_vistas:
                urls_pendientes.append(pag)

    logging.info(f"Documentos descargados: {docs_descargados}")
    return docs_descargados


def main(estados_a_correr, terminos_a_buscar):
    crear_carpetas()
    configurar_logging()
    ruta_csv = iniciar_csv()

    session = requests.Session()
    total = 0

    for id_estado, nombre_estado in estados_a_correr.items():
        logging.info(f"======== {nombre_estado} ========")
        for termino in terminos_a_buscar:
            try:
                n = scrapear_estado_termino(
                    session, id_estado, nombre_estado, termino, ruta_csv
                )
                total += n
            except Exception as e:
                logging.error(f"Error en {nombre_estado}/{termino}: {e}")

    logging.info(f"======== FIN. Total: {total} documentos ========")
    print(f"\n✓ Listo. {total} documentos descargados.")
    print(f"  PDFs/DOCs → descargas/")
    print(f"  HTMLs     → descargas/htmls/")
    print(f"  CSV       → {CARPETA_DATOS}")


# -------------------------------------------------------
# Argumentos de línea de comandos
# -------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scraper Orden Jurídico Nacional")
    ap.add_argument("--todos", action="store_true", help="32 estados completos")
    ap.add_argument("--estado", type=int, help="ID de un solo estado (ej: 14)")
    ap.add_argument("--termino", type=str, help="Buscar solo este término")
    args = ap.parse_args()

    if args.todos:
        estados_sel = ESTADOS
    elif args.estado:
        if args.estado not in ESTADOS:
            print(f"ID {args.estado} no válido. Usa 1-32.")
            exit(1)
        estados_sel = {args.estado: ESTADOS[args.estado]}
    elif ESTADOS_PRUEBA:
        estados_sel = {k: ESTADOS[k] for k in ESTADOS_PRUEBA if k in ESTADOS}
    else:
        estados_sel = ESTADOS

    terminos_sel = [args.termino] if args.termino else TERMINOS_BUSQUEDA

    print(f"Estados:  {list(estados_sel.values())}")
    print(f"Términos: {terminos_sel}\n")

    main(estados_sel, terminos_sel)
