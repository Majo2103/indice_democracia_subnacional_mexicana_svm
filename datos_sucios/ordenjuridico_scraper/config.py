# ============================================================
# config.py — Configuración central del scraper
# Aquí defines qué buscar y en qué estados
# ============================================================

# URL base del sitio
BASE_URL = "http://www.ordenjuridico.gob.mx"

# Carpetas de salida
CARPETA_PDFS  = "descargas/pdfs"
CARPETA_HTMLS = "descargas/htmls"
CARPETA_DOCS  = "descargas/docs"
CARPETA_LOGS  = "logs"
CARPETA_DATOS = "datos"

# Segundos de espera entre requests (no saturar el servidor)
PAUSA_ENTRE_REQUESTS = 2

# -------------------------------------------------------
# Estados de México con su código numérico en el sitio
# (edo=1 es Aguascalientes, edo=9 es CDMX, etc.)
# -------------------------------------------------------
ESTADOS = {
    1:  "Aguascalientes",
    2:  "Baja California",
    3:  "Baja California Sur",
    4:  "Campeche",
    5:  "Chiapas",
    6:  "Chihuahua",
    7:  "Coahuila",
    8:  "Colima",
    9:  "Ciudad de Mexico",
    10: "Durango",
    11: "Guanajuato",
    12: "Guerrero",
    13: "Hidalgo",
    14: "Jalisco",
    15: "Estado de Mexico",
    16: "Michoacan",
    17: "Morelos",
    18: "Nayarit",
    19: "Nuevo Leon",
    20: "Oaxaca",
    21: "Puebla",
    22: "Queretaro",
    23: "Quintana Roo",
    24: "San Luis Potosi",
    25: "Sinaloa",
    26: "Sonora",
    27: "Tabasco",
    28: "Tamaulipas",
    29: "Tlaxcala",
    30: "Veracruz",
    31: "Yucatan",
    32: "Zacatecas",
}

# -------------------------------------------------------
# Términos de búsqueda relevantes para el proyecto
# Puedes agregar o quitar según lo que necesites
# -------------------------------------------------------
TERMINOS_BUSQUEDA = [
    "codigo penal",
    "ley de transparencia",
    "acceso a la informacion",
    "ultrajes a la autoridad",
    "difamacion",
    "injurias",
    "desacato",
    "libertad de expresion",
]

# -------------------------------------------------------
# Si solo quieres probar con algunos estados primero,
# cambia ESTADOS_PRUEBA a una lista de números.
# Para correr todos, deja ESTADOS_PRUEBA = None
# -------------------------------------------------------
ESTADOS_PRUEBA = [14, 15, 21]  # Jalisco, Estado de México, Puebla
