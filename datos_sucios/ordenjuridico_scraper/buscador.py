# ============================================================
# buscador.py — Busca términos clave en los textos extraídos
#               y genera la tabla de variables binarias
#
# Uso:
#   python buscador.py
#
# Genera datos/panel_binario.csv con una fila por documento
# y columnas binarias para cada término buscado.
# ============================================================

import os
import re
import csv
import logging

CARPETA_TEXTOS = "textos"
CARPETA_DATOS  = "datos"

# -------------------------------------------------------
# Términos a buscar dentro del texto de cada documento
# Cada término tiene una lista de variantes para capturar
# diferencias de acentuación, singular/plural, etc.
# -------------------------------------------------------
TERMINOS = {
    # Variables que AUMENTAN libertad (existencia = bueno)
    "ley_transparencia": [
        "ley de transparencia",
        "acceso a la información",
        "transparencia e información",
        "transparencia y acceso",
    ],

    # Variables que REDUCEN libertad (existencia = malo)
    "difamacion": [
        "difamación",
        "difamacion",
        "calumnia",
    ],
    "injurias": [
        "injuria",
        "injurias",
    ],
    "ultrajes": [
        "ultraje",
        "ultrajes a la autoridad",
        "ultrajes a funcionario",
    ],
    "desacato": [
        "desacato",
        "desobediencia a la autoridad",
    ],
}

# -------------------------------------------------------
# Palabras clave que indican DEROGACIÓN de un artículo
# Si el texto menciona estas palabras cerca del término,
# puede indicar que el tipo penal fue eliminado
# -------------------------------------------------------
PALABRAS_DEROGACION = [
    "se deroga",
    "quedan derogados",
    "deróganse",
    "derogado",
    "derogados",
    "se abroga",
]


def configurar_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )


def leer_texto(ruta_txt):
    """Lee un archivo .txt y devuelve su contenido en minúsculas."""
    try:
        with open(ruta_txt, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().lower()
    except Exception as e:
        logging.warning(f"No se pudo leer {ruta_txt}: {e}")
        return ""


def buscar_termino(texto, variantes):
    """
    Busca si alguna variante del término aparece en el texto.
    Devuelve True/False y el fragmento donde lo encontró.
    """
    for variante in variantes:
        patron = re.escape(variante.lower())
        match = re.search(patron, texto)
        if match:
            # Extraer contexto: 150 chars antes y después
            inicio = max(0, match.start() - 150)
            fin = min(len(texto), match.end() + 150)
            contexto = texto[inicio:fin].replace("\n", " ").strip()
            return True, contexto
    return False, ""


def detectar_derogacion(contexto):
    """
    Revisa si el contexto donde aparece el término
    contiene palabras de derogación.
    Útil para decretos que derogan artículos.
    """
    contexto_lower = contexto.lower()
    return any(p in contexto_lower for p in PALABRAS_DEROGACION)


def extraer_fecha_del_texto(texto):
    """
    Intenta extraer una fecha de publicación del texto.
    Busca patrones como 'P.O. 15 de octubre de 2013'
    o encabezados con año.
    """
    # Patrón: día de mes de año
    patron = r'\b(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\b'
    matches = re.findall(patron, texto[:2000])  # solo en los primeros 2000 chars
    if matches:
        dia, mes, año = matches[0]
        return f"{dia} de {mes} de {año}"

    # Patrón: año solo en encabezado
    patron_año = r'\b(200[0-9]|201[0-9]|202[0-9])\b'
    match_año = re.search(patron_año, texto[:500])
    if match_año:
        return match_año.group(1)

    return ""


def main():
    configurar_logging()
    os.makedirs(CARPETA_DATOS, exist_ok=True)

    archivos_txt = sorted([
        f for f in os.listdir(CARPETA_TEXTOS)
        if f.endswith(".txt")
    ])

    logging.info(f"Archivos a analizar: {len(archivos_txt)}")

    # Construir encabezados del CSV
    columnas_terminos = list(TERMINOS.keys())
    columnas_contexto = [f"contexto_{t}" for t in columnas_terminos]
    columnas_derogacion = [f"derogacion_{t}" for t in columnas_terminos]

    encabezado = (
        ["archivo", "fecha_detectada"] +
        columnas_terminos +
        columnas_derogacion +
        columnas_contexto
    )

    ruta_csv = os.path.join(CARPETA_DATOS, "panel_binario.csv")

    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(encabezado)

        for nombre_txt in archivos_txt:
            ruta = os.path.join(CARPETA_TEXTOS, nombre_txt)
            texto = leer_texto(ruta)

            if not texto:
                continue

            fecha = extraer_fecha_del_texto(texto)

            # Buscar cada término
            resultados = {}
            contextos = {}
            derogaciones = {}

            for termino, variantes in TERMINOS.items():
                encontrado, contexto = buscar_termino(texto, variantes)
                resultados[termino] = 1 if encontrado else 0
                contextos[termino] = contexto
                derogaciones[termino] = 1 if (encontrado and detectar_derogacion(contexto)) else 0

            fila = (
                [nombre_txt, fecha] +
                [resultados[t] for t in columnas_terminos] +
                [derogaciones[t] for t in columnas_terminos] +
                [contextos[t] for t in columnas_terminos]
            )

            writer.writerow(fila)

            # Log resumido
            flags = " | ".join([
                f"{t}={'✓' if resultados[t] else '✗'}"
                for t in columnas_terminos
            ])
            logging.info(f"{nombre_txt[:30]} → {flags}")

    logging.info(f"CSV generado: {ruta_csv}")
    logging.info("Siguiente paso: revisar panel_binario.csv y cruzar con el inventario.csv")


if __name__ == "__main__":
    main()
