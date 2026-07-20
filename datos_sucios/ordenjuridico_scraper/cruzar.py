# ============================================================
# cruzar.py — Cruza panel_binario.csv con inventario.csv
#             para generar la tabla final estado-año
#
# Uso:
#   python cruzar.py
#
# Genera datos/tabla_estado_año.csv
# ============================================================

import os
import re
import csv
import glob
import logging

CARPETA_DATOS  = "datos"
ARCHIVO_PANEL  = os.path.join(CARPETA_DATOS, "panel_binario.csv")
ARCHIVO_SALIDA = os.path.join(CARPETA_DATOS, "tabla_estado_anio.csv")

# Meses en español para parsear fechas
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}


def configurar_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )


def extraer_anio(fecha_str):
    """
    Extrae el año de una cadena de fecha como:
    '2 de septiembre de 1982' o '2011' o '15-10-2013'
    Devuelve int o None.
    """
    if not fecha_str:
        return None

    # Buscar año de 4 dígitos (entre 1990 y 2030)
    matches = re.findall(r'\b(19[9]\d|20[0-2]\d)\b', fecha_str)
    if matches:
        return int(matches[-1])  # tomar el último año mencionado

    return None


def nombre_sin_extension(nombre_archivo):
    """
    Convierte 'wo77048.txt' → 'wo77048'
    para hacer match con la columna ruta_local del inventario.
    """
    return os.path.splitext(nombre_archivo)[0]


def cargar_inventarios():
    """
    Carga y consolida todos los inventario_*.csv de la carpeta datos/.
    Devuelve un dict: {nombre_archivo_base: {estado, id_estado, termino, titulo, fecha_titulo}}
    El nombre_archivo_base es el nombre del archivo sin ruta ni extensión.
    """
    inventario = {}

    archivos_inv = glob.glob(os.path.join(CARPETA_DATOS, "inventario_*.csv"))
    logging.info(f"Inventarios encontrados: {len(archivos_inv)}")

    for ruta_inv in archivos_inv:
        with open(ruta_inv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for fila in reader:
                # El nombre del archivo está en ruta_local: 'descargas/pdfs/wo77048.pdf'
                ruta_local = fila.get("ruta_local", "")
                if not ruta_local:
                    continue

                nombre_base = os.path.splitext(os.path.basename(ruta_local))[0]

                # Guardar info del inventario (el primero gana si hay duplicados)
                if nombre_base not in inventario:
                    inventario[nombre_base] = {
                        "estado":      fila.get("estado", ""),
                        "id_estado":   fila.get("id_estado", ""),
                        "termino":     fila.get("termino", ""),
                        "titulo":      fila.get("titulo", ""),
                        "fecha_titulo": extraer_anio_de_titulo(fila.get("titulo", "")),
                    }

    logging.info(f"Total entradas en inventario consolidado: {len(inventario)}")
    return inventario


def extraer_anio_de_titulo(titulo):
    """
    Intenta extraer el año de publicación del título del decreto.
    Ej: 'Decreto 23559/LIX/11' → 2011
    Ej: '(P.O. 15-10-2013)' → 2013
    """
    if not titulo:
        return None

    # Patrón: P.O. con fecha
    match = re.search(r'P\.O\.\s*[\d-]+[-/](\d{4})', titulo)
    if match:
        return int(match.group(1))

    # Patrón: año de 4 dígitos entre 2000 y 2024
    matches = re.findall(r'\b(200[0-9]|201[0-9]|202[0-4])\b', titulo)
    if matches:
        return int(matches[-1])

    # Patrón: /XX/ donde XX es año abreviado (ej: /LIX/11 → 2011, /LX/15 → 2015)
    match = re.search(r'/[A-Z]+/(\d{2})\b', titulo)
    if match:
        año_corto = int(match.group(1))
        return 2000 + año_corto if año_corto <= 30 else 1900 + año_corto

    return None


def cargar_panel():
    """
    Carga el panel_binario.csv.
    Devuelve dict: {nombre_base: {variables binarias y contextos}}
    """
    panel = {}
    with open(ARCHIVO_PANEL, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            nombre_txt = fila.get("archivo", "")
            nombre_base = nombre_sin_extension(nombre_txt)
            panel[nombre_base] = fila
    logging.info(f"Registros en panel_binario: {len(panel)}")
    return panel


def main():
    configurar_logging()

    inventario = cargar_inventarios()
    panel = cargar_panel()

    # Cruzar por nombre de archivo
    filas_salida = []
    sin_match = 0
    con_match = 0

    for nombre_base, datos_panel in panel.items():
        info_inv = inventario.get(nombre_base)

        if not info_inv:
            sin_match += 1
            logging.debug(f"Sin match en inventario: {nombre_base}")
            continue

        # Determinar año: primero del inventario (título del decreto),
        # si no hay, usar el detectado en el texto del documento
        anio = info_inv.get("fecha_titulo")
        if not anio:
            anio = extraer_anio(datos_panel.get("fecha_detectada", ""))

        fila = {
            "estado":           info_inv["estado"],
            "id_estado":        info_inv["id_estado"],
            "anio":             anio or "",
            "termino_busqueda": info_inv["termino"],
            "titulo":           info_inv["titulo"][:80],  # truncar para legibilidad
            "archivo":          nombre_base,
            # Variables binarias
            "ley_transparencia": datos_panel.get("ley_transparencia", ""),
            "difamacion":        datos_panel.get("difamacion", ""),
            "injurias":          datos_panel.get("injurias", ""),
            "ultrajes":          datos_panel.get("ultrajes", ""),
            "desacato":          datos_panel.get("desacato", ""),
            # Flags de derogación
            "derogacion_difamacion": datos_panel.get("derogacion_difamacion", ""),
            "derogacion_injurias":   datos_panel.get("derogacion_injurias", ""),
            "derogacion_ultrajes":   datos_panel.get("derogacion_ultrajes", ""),
        }
        filas_salida.append(fila)
        con_match += 1

    logging.info(f"Cruzados: {con_match} | Sin match: {sin_match}")

    # Ordenar por estado y año
    filas_salida.sort(key=lambda x: (x["estado"], str(x["anio"])))

    # Escribir CSV de salida
    if not filas_salida:
        logging.error("No se generaron filas. Revisa los nombres de archivos.")
        return

    encabezado = list(filas_salida[0].keys())
    with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=encabezado)
        writer.writeheader()
        writer.writerows(filas_salida)

    logging.info(f"Tabla generada: {ARCHIVO_SALIDA}")
    logging.info(f"Total filas: {len(filas_salida)}")

    # Resumen por estado
    estados = {}
    for fila in filas_salida:
        e = fila["estado"]
        if e not in estados:
            estados[e] = 0
        estados[e] += 1

    print("\nResumen por estado:")
    for estado, n in sorted(estados.items()):
        print(f"  {estado}: {n} documentos")


if __name__ == "__main__":
    main()
