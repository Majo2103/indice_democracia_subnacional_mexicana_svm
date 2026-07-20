# ============================================================
# limpieza_libertad_expresion.py
#
# Lee:
#   - panel_libertad_expresion_leyes.csv  (variables legales por estado-año)
#   - periodistasAsesinados.csv           (periodistas asesinados)
#   - periodistasDesaparecidos.csv        (periodistas desaparecidos)
#
# Genera:
#   libertad_expresion.csv con columnas:
#   state_name, state_code, year,
#   num_periodistas_desaparecidos, num_periodistas_asesinados,
#   ley_transparencia, difamacion_penal, injurias_penal, ultrajes_autoridad
# ============================================================

import pandas as pd
import re

# -------------------------------------------------------
# RUTAS 
# -------------------------------------------------------
RUTA_LEYES       = "datos_sucios/panel_libertad_expresion_leyes.csv"
RUTA_ASESINADOS  = "datos_sucios/periodistasAsesinados.csv"
RUTA_DESAPAREC   = "datos_sucios/periodistasDesaparecidos.csv"
RUTA_SALIDA      = "datos/libertad_expresion.csv"

# -------------------------------------------------------
# Catálogo de estados
# -------------------------------------------------------
ESTADO_A_CODIGO = {
    "Aguascalientes":      "01",
    "Baja California":     "02",
    "Baja California Sur": "03",
    "Campeche":            "04",
    "Chiapas":             "05",
    "Chihuahua":           "06",
    "Ciudad de Mexico":    "09",
    "Ciudad de México":    "09",
    "CDMX":                "09",
    "Coahuila":            "07",
    "Colima":              "08",
    "Durango":             "10",
    "Estado de Mexico":    "15",
    "Estado de México":    "15",
    "Guanajuato":          "11",
    "Guerrero":            "12",
    "Hidalgo":             "13",
    "Jalisco":             "14",
    "Mexico":              "15",
    "México":              "15",
    "Michoacan":           "16",
    "Michoacán":           "16",
    "Morelos":             "17",
    "Nayarit":             "18",
    "Nuevo Leon":          "19",
    "Nuevo León":          "19",
    "Oaxaca":              "20",
    "Puebla":              "21",
    "Queretaro":           "22",
    "Querétaro":           "22",
    "Quintana Roo":        "23",
    "San Luis Potosi":     "24",
    "San Luis Potosí":     "24",
    "Sinaloa":             "25",
    "Sonora":              "26",
    "Tabasco":             "27",
    "Tamaulipas":          "28",
    "Tlaxcala":            "29",
    "Veracruz":            "30",
    "Yucatan":             "31",
    "Yucatán":             "31",
    "Zacatecas":           "32",
}

# Nombre canónico por código (para state_name en el output)
CODIGO_A_NOMBRE = {v: k for k, v in ESTADO_A_CODIGO.items()}
# Preferir el nombre sin acento para consistencia con el panel de leyes
NOMBRES_CANONICOS = {
    "09": "Ciudad de Mexico",
    "15": "Estado de Mexico",
    "16": "Michoacan",
    "19": "Nuevo Leon",
    "22": "Queretaro",
    "24": "San Luis Potosi",
    "31": "Yucatan",
}


def normalizar_nombre_estado(nombre):
    """
    Intenta encontrar el código INEGI para un string de estado.
    Maneja variantes de acentuación, mayúsculas y sufijos.
    Devuelve el código (str de 2 dígitos) o None si no encuentra.
    """
    if not nombre or pd.isna(nombre):
        return None

    nombre = str(nombre).strip()

    # Búsqueda directa
    if nombre in ESTADO_A_CODIGO:
        return ESTADO_A_CODIGO[nombre]

    # Sin acento y minúsculas para comparación flexible
    nombre_lower = nombre.lower()
    for clave, codigo in ESTADO_A_CODIGO.items():
        if clave.lower() == nombre_lower:
            return codigo

    # Buscar si alguna clave está contenida en el string
    # (útil para "Reynosa, Tamaulipas" → Tamaulipas)
    for clave, codigo in sorted(ESTADO_A_CODIGO.items(),
                                key=lambda x: len(x[0]), reverse=True):
        if clave.lower() in nombre_lower:
            return codigo

    return None


def extraer_estado_de_municipio(municipio_estado):
    """
    Para desaparecidos: extrae el estado de strings como
    'Martínez de la Torre, Veracruz' o 'Veracruz'.
    Toma la última parte después de la última coma.
    """
    if not municipio_estado or pd.isna(municipio_estado):
        return None
    partes = str(municipio_estado).split(",")
    estado_candidato = partes[-1].strip()
    return normalizar_nombre_estado(estado_candidato)


def extraer_anio_asesinados(fecha_str):
    """
    Parsea fechas tipo '2000/2/1' o '2000/04/09'.
    Devuelve el año como int o None.
    """
    if not fecha_str or pd.isna(fecha_str):
        return None
    match = re.match(r"(\d{4})", str(fecha_str).strip())
    if match:
        return int(match.group(1))
    return None


def extraer_anio_desaparecidos(fecha_str):
    """
    Parsea fechas tipo '10 de Julio de 2003'.
    Devuelve el año como int o None.
    """
    if not fecha_str or pd.isna(fecha_str):
        return None
    match = re.search(r"\b(\d{4})\b", str(fecha_str))
    if match:
        return int(match.group(1))
    return None


# ============================================================
# 1. Cargar el panel de leyes
# ============================================================
print("Leyendo panel de leyes...")
leyes = pd.read_csv(RUTA_LEYES, dtype=str, encoding="latin-1")

# Normalizar nombres de columnas
leyes.columns = leyes.columns.str.strip()

# Convertir año a int
leyes["anio"] = leyes["anio"].astype(int)

# Agregar código de estado
leyes["state_code"] = leyes["estado"].apply(normalizar_nombre_estado)

# Nombre canónico
leyes["state_name"] = leyes["state_code"].map(
    lambda c: NOMBRES_CANONICOS.get(c, CODIGO_A_NOMBRE.get(c, "")) if c else ""
)

# Convertir variables binarias a int (pueden venir como "0", "1", "0.0")
for col in ["ley_transparencia", "difamacion_penal", "injurias_penal", "ultrajes_autoridad"]:
    leyes[col] = pd.to_numeric(leyes[col], errors="coerce").fillna(0).astype(int)

print(f"  {len(leyes)} filas, {leyes['state_code'].nunique()} estados")

# ============================================================
# 2. Cargar y procesar periodistas asesinados
# ============================================================
print("Leyendo periodistas asesinados...")
asesinos = pd.read_csv(RUTA_ASESINADOS, dtype=str, encoding="latin-1")
asesinos.columns = asesinos.columns.str.strip()

# Estado: columna 'Title'
asesinos["state_code"] = asesinos["Title"].apply(normalizar_nombre_estado)

# Año: columna 'FECHA'
asesinos["year"] = asesinos["FECHA"].apply(extraer_anio_asesinados)

# Filtrar filas sin estado o año
asesinos_validos = asesinos.dropna(subset=["state_code", "year"]).copy()
asesinos_validos["year"] = asesinos_validos["year"].astype(int)

# Contar por estado-año
conteo_asesinados = (
    asesinos_validos
    .groupby(["state_code", "year"])
    .size()
    .reset_index(name="num_periodistas_asesinados")
)
print(f"  {len(asesinos_validos)} registros válidos")

# ============================================================
# 3. Cargar y procesar periodistas desaparecidos
# ============================================================
print("Leyendo periodistas desaparecidos...")
desapar = pd.read_csv(RUTA_DESAPAREC, dtype=str, encoding="utf-8")
desapar.columns = desapar.columns.str.strip()

# Estado: extraer de 'municipio_estado'
desapar["state_code"] = desapar["municipio_estado"].apply(extraer_estado_de_municipio)

# Año: de 'fecha_desaparicion'
desapar["year"] = desapar["fecha_desaparicion"].apply(extraer_anio_desaparecidos)

# Filtrar filas sin estado o año
desapar_validos = desapar.dropna(subset=["state_code", "year"]).copy()
desapar_validos["year"] = desapar_validos["year"].astype(int)

# Contar por estado-año
conteo_desaparecidos = (
    desapar_validos
    .groupby(["state_code", "year"])
    .size()
    .reset_index(name="num_periodistas_desaparecidos")
)
print(f"  {len(desapar_validos)} registros válidos")

# ============================================================
# 4. Construir el panel base desde leyes (32 estados × 25 años)
# ============================================================
print("Construyendo panel final...")
panel = leyes[["state_name", "state_code", "anio",
               "ley_transparencia", "difamacion_penal",
               "injurias_penal", "ultrajes_autoridad"]].copy()
panel.rename(columns={"anio": "year"}, inplace=True)

# ============================================================
# 5. Unir conteos de periodistas (left join para mantener todos
#    los estados-año aunque no haya casos ese año)
# ============================================================
panel = panel.merge(conteo_asesinados, on=["state_code", "year"], how="left")
panel = panel.merge(conteo_desaparecidos, on=["state_code", "year"], how="left")

# Rellenar NaN con 0 (sin casos ese año)
panel["num_periodistas_asesinados"]   = panel["num_periodistas_asesinados"].fillna(0).astype(int)
panel["num_periodistas_desaparecidos"] = panel["num_periodistas_desaparecidos"].fillna(0).astype(int)

# ============================================================
# 6. Ordenar columnas y filas
# ============================================================
columnas_finales = [
    "state_name", "state_code", "year",
    "num_periodistas_desaparecidos", "num_periodistas_asesinados",
    "ley_transparencia", "difamacion_penal", "injurias_penal", "ultrajes_autoridad"
]
panel = panel[columnas_finales]
panel = panel.sort_values(["state_name", "year"]).reset_index(drop=True)

# ============================================================
# 7. Guardar
# ============================================================
import os
os.makedirs(os.path.dirname(RUTA_SALIDA), exist_ok=True)
panel.to_csv(RUTA_SALIDA, index=False, encoding="utf-8")

print(f"\n✓ Guardado: {RUTA_SALIDA}")
print(f"  Filas:   {len(panel)}")
print(f"  Estados: {panel['state_name'].nunique()}")
print(f"  Años:    {panel['year'].min()} – {panel['year'].max()}")
print()
print("Muestra de casos con periodistas:")
print(panel[(panel["num_periodistas_asesinados"] > 0) |
            (panel["num_periodistas_desaparecidos"] > 0)].head(10).to_string(index=False))