# ============================================================
# extractor.py — Extrae texto de PDFs y DOCs
#
# Uso:
#   python extractor.py
#
# Genera una carpeta textos/ con un .txt por cada documento.
# ============================================================

import os
import subprocess
import tempfile
import shutil
import logging
import pdfplumber

CARPETA_PDFS   = "descargas/pdfs"
CARPETA_DOCS   = "descargas/docs"
CARPETA_TEXTOS = "textos"  # aquí caen los .txt extraídos


def configurar_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )


def extraer_texto_pdf(ruta_pdf):
    """
    Extrae texto de un PDF con pdfplumber.
    Devuelve el texto completo como string, o None si falla.
    """
    try:
        texto = []
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto.append(t)
        return "\n".join(texto)
    except Exception as e:
        logging.warning(f"PDF falló ({os.path.basename(ruta_pdf)}): {e}")
        return None


def extraer_texto_doc(ruta_doc):
    """
    Convierte un .doc viejo a texto usando soffice (LibreOffice).
    Usa una carpeta temporal para no ensuciar el proyecto.
    Devuelve el texto completo como string, o None si falla.
    """
    nombre = os.path.basename(ruta_doc)
    nombre_txt = os.path.splitext(nombre)[0] + ".txt"

    # Carpeta temporal para la conversión
    tmp = tempfile.mkdtemp()
    try:
        resultado = subprocess.run(
            ["soffice", "--headless", "--convert-to", "txt",
             os.path.abspath(ruta_doc), "--outdir", tmp],
            capture_output=True, text=True, timeout=60
        )

        ruta_txt_tmp = os.path.join(tmp, nombre_txt)
        if os.path.exists(ruta_txt_tmp):
            with open(ruta_txt_tmp, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            logging.warning(f"DOC sin output ({nombre}): {resultado.stderr[:100]}")
            return None
    except subprocess.TimeoutExpired:
        logging.warning(f"DOC timeout ({nombre})")
        return None
    except Exception as e:
        logging.warning(f"DOC falló ({nombre}): {e}")
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # limpiar carpeta temporal


def guardar_texto(texto, nombre_base):
    """Guarda el texto extraído en textos/nombre_base.txt"""
    os.makedirs(CARPETA_TEXTOS, exist_ok=True)
    ruta = os.path.join(CARPETA_TEXTOS, nombre_base + ".txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)
    return ruta


def main():
    configurar_logging()
    os.makedirs(CARPETA_TEXTOS, exist_ok=True)

    ok = 0
    fallos = 0

    # --- Procesar PDFs ---
    pdfs = [f for f in os.listdir(CARPETA_PDFS) if f.endswith(".pdf")]
    logging.info(f"PDFs a procesar: {len(pdfs)}")

    for nombre in pdfs:
        ruta = os.path.join(CARPETA_PDFS, nombre)
        nombre_base = os.path.splitext(nombre)[0]

        # Si ya existe el .txt, omitir
        if os.path.exists(os.path.join(CARPETA_TEXTOS, nombre_base + ".txt")):
            logging.info(f"Ya existe, omitiendo: {nombre}")
            ok += 1
            continue

        texto = extraer_texto_pdf(ruta)
        if texto and len(texto.strip()) > 50:
            guardar_texto(texto, nombre_base)
            logging.info(f"✓ PDF: {nombre} ({len(texto)} chars)")
            ok += 1
        else:
            logging.warning(f"✗ PDF vacío: {nombre}")
            fallos += 1

    # --- Procesar DOCs ---
    docs = [f for f in os.listdir(CARPETA_DOCS) if f.endswith(".doc")]
    logging.info(f"DOCs a procesar: {len(docs)}")

    for nombre in docs:
        ruta = os.path.join(CARPETA_DOCS, nombre)
        nombre_base = os.path.splitext(nombre)[0]

        if os.path.exists(os.path.join(CARPETA_TEXTOS, nombre_base + ".txt")):
            logging.info(f"Ya existe, omitiendo: {nombre}")
            ok += 1
            continue

        texto = extraer_texto_doc(ruta)
        if texto and len(texto.strip()) > 50:
            guardar_texto(texto, nombre_base)
            logging.info(f"✓ DOC: {nombre} ({len(texto)} chars)")
            ok += 1
        else:
            logging.warning(f"✗ DOC vacío: {nombre}")
            fallos += 1

    logging.info(f"Listo. ✓ {ok} extraídos, ✗ {fallos} fallidos")
    logging.info(f"Textos en: {CARPETA_TEXTOS}/")


if __name__ == "__main__":
    main()
