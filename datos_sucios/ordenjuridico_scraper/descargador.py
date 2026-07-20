# ============================================================
# descargador.py — Descarga y guarda archivos del sitio
# ============================================================

import os
import time
import logging
import requests
from urllib.parse import urljoin, urlparse
from config import BASE_URL, CARPETA_PDFS, CARPETA_HTMLS, CARPETA_DOCS, PAUSA_ENTRE_REQUESTS

# Cabeceras para simular un navegador normal
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
}


def get_pagina(url, session, reintentos=3):
    """
    Descarga el HTML de una URL.
    Reintenta hasta 3 veces si hay error de red.
    Devuelve el texto HTML o None si falla.
    """
    for intento in range(reintentos):
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            # El sitio usa iso-8859-1, respetar lo que declare el servidor
            if not resp.encoding or resp.encoding.lower() in ("utf-8", "none"):
                resp.encoding = "iso-8859-1"
            resp.raise_for_status()
            time.sleep(PAUSA_ENTRE_REQUESTS)
            return resp.text
        except requests.RequestException as e:
            logging.warning(f"Intento {intento+1}/{reintentos} fallido para {url}: {e}")
            time.sleep(PAUSA_ENTRE_REQUESTS * 2)  # espera doble antes de reintentar
    logging.error(f"No se pudo descargar: {url}")
    return None


def descargar_archivo(url, session, carpeta_destino, reintentos=3):
    """
    Descarga un archivo binario (PDF, DOC) y lo guarda en disco.
    Devuelve la ruta local donde se guardó, o None si falla.
    """
    # Construir nombre de archivo limpio desde la URL
    nombre = os.path.basename(urlparse(url).path)
    if not nombre:
        logging.warning(f"No se pudo determinar nombre para: {url}")
        return None

    ruta_local = os.path.join(carpeta_destino, nombre)

    # Si ya existe el archivo, no lo vuelve a descargar
    if os.path.exists(ruta_local):
        logging.info(f"Ya existe, omitiendo: {nombre}")
        return ruta_local

    for intento in range(reintentos):
        try:
            resp = session.get(url, headers=HEADERS, timeout=60, stream=True)
            resp.raise_for_status()

            # Guardar el archivo en chunks para no cargar todo en memoria
            with open(ruta_local, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            logging.info(f"Descargado: {nombre}")
            time.sleep(PAUSA_ENTRE_REQUESTS)
            return ruta_local

        except requests.RequestException as e:
            logging.warning(f"Intento {intento+1}/{reintentos} fallido para {url}: {e}")
            # Borrar archivo parcial si quedó corrupto
            if os.path.exists(ruta_local):
                os.remove(ruta_local)
            time.sleep(PAUSA_ENTRE_REQUESTS * 2)

    logging.error(f"No se pudo descargar archivo: {url}")
    return None


def guardar_html(contenido_html, nombre_archivo, carpeta_destino):
    """
    Guarda una página HTML en disco.
    Devuelve la ruta local.
    """
    ruta_local = os.path.join(carpeta_destino, nombre_archivo)
    with open(ruta_local, "w", encoding="utf-8") as f:
        f.write(contenido_html)
    return ruta_local


def decidir_carpeta_y_descargar(url_archivo, session):
    """
    Detecta el tipo de archivo por su extensión
    y lo guarda en la carpeta correspondiente.
    Devuelve la ruta local o None.
    """
    url_lower = url_archivo.lower()

    if url_lower.endswith(".pdf"):
        return descargar_archivo(url_archivo, session, CARPETA_PDFS)
    elif url_lower.endswith(".doc") or url_lower.endswith(".docx"):
        return descargar_archivo(url_archivo, session, CARPETA_DOCS)
    else:
        # Si no tiene extensión clara, intentar descargar igual como PDF
        logging.info(f"Extensión desconocida, intentando como binario: {url_archivo}")
        return descargar_archivo(url_archivo, session, CARPETA_PDFS)
