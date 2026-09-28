"""
construir_panel.py
===================

Construye el panel estatal (32 entidades x 2000-2024) del proyecto de tesis
"Libertad de asociación en México", a partir de cinco archivos fuente:

  1. CONAPO   - proyeccionesCONAPO.csv           -> población a mitad de año
  2. INEGI    - datosSAIC.csv                     -> Censos Económicos, sector 813
  3. STPS     - Emplazamientos_a_Huelgas_por_Entidad_Federativa.xls
  4. STPS     - Huelgas_por_Entidad_Federativa.xls
  5. ACLED    - ACLED_data.csv                    -> eventos de protesta

Y agrega una variable de contexto normativo:
  - ley_fomento_federal_vigente: 1 a partir de 2004 (publicación de la Ley
    Federal de Fomento a las Actividades Realizadas por Organizaciones de la
    Sociedad Civil, DOF 9 de febrero de 2004), 0 antes. Es una variable
    nacional (no varía por entidad).

USO
-----------
python3 construir_panel.py

"""

import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 0. CONFIGURACIÓN — ajusta estas rutas a donde tengas los archivos
# ---------------------------------------------------------------------------

INPUT_DIR = Path("datos_sucios/libertadAsociacion")  # carpeta donde están los 5 archivos fuente
OUTPUT_FILE = Path("datos/libertad_asociacion_panel.csv")  # ruta de salida del panel final

ARCHIVO_CONAPO = INPUT_DIR / "proyeccionesCONAPO.csv"
ARCHIVO_SAIC = INPUT_DIR / "datosSAIC.csv"
ARCHIVO_EMPLAZAMIENTOS = INPUT_DIR / "Emplazamientos_a_Huelgas_por_Entidad_Federativa.xls"
ARCHIVO_HUELGAS = INPUT_DIR / "Huelgas_por_Entidad_Federativa.xls"
ARCHIVO_ACLED = INPUT_DIR / "ACLED_data.csv"    

ANIO_INICIO, ANIO_FIN = 2000, 2024
ANIOS_CENSO_ECONOMICO = [2003, 2008, 2013, 2018, 2023]
ANIOS_ACLED_COBERTURA = list(range(2018, 2025))  # 2017 se descarta: sólo trae la última semana del año
ANIO_LEY_FOMENTO_FEDERAL = 2004  # DOF, 9 de febrero de 2004

# ---------------------------------------------------------------------------
# 1. CATÁLOGO MAESTRO DE ENTIDADES
#    Cada fuente escribe los nombres de estado distinto (con/sin acentos,
#    "Coahuila de Zaragoza" vs "Coahuila", etc.). Todo se homologa aquí,
#    una sola vez, para no repetir la lógica de nombres en cada fuente.
# ---------------------------------------------------------------------------

CATALOGO_ENTIDADES = {
    "01": "Aguascalientes", "02": "Baja California", "03": "Baja California Sur",
    "04": "Campeche", "05": "Coahuila", "06": "Colima", "07": "Chiapas",
    "08": "Chihuahua", "09": "Ciudad de Mexico", "10": "Durango",
    "11": "Guanajuato", "12": "Guerrero", "13": "Hidalgo", "14": "Jalisco",
    "15": "Mexico", "16": "Michoacan", "17": "Morelos", "18": "Nayarit",
    "19": "Nuevo Leon", "20": "Oaxaca", "21": "Puebla", "22": "Queretaro",
    "23": "Quintana Roo", "24": "San Luis Potosi", "25": "Sinaloa",
    "26": "Sonora", "27": "Tabasco", "28": "Tamaulipas", "29": "Tlaxcala",
    "30": "Veracruz", "31": "Yucatan", "32": "Zacatecas",
}

# variantes de nombre que aparecen en las fuentes y no matchean directo
ALIAS_ENTIDADES = {
    "coahuila de zaragoza": "05",
    "michoacan de ocampo": "16",
    "veracruz de ignacio de la llave": "30",
}


def _quitar_acentos(texto):
    if not isinstance(texto, str):
        return texto
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _normalizar_nombre(texto):
    t = _quitar_acentos(str(texto)).lower().strip()
    for sufijo in (" de zaragoza", " de ignacio de la llave", " de ocampo"):
        t = t.replace(sufijo, "")
    return t.strip()


_NOMBRE_A_CLAVE = {_normalizar_nombre(n): c for c, n in CATALOGO_ENTIDADES.items()}
_NOMBRE_A_CLAVE.update({_normalizar_nombre(n): c for n, c in ALIAS_ENTIDADES.items()})


def clave_de_entidad(nombre_crudo):
    """Devuelve la clave de entidad (01-32) a partir de cualquier variante de nombre."""
    return _NOMBRE_A_CLAVE.get(_normalizar_nombre(nombre_crudo))


# ---------------------------------------------------------------------------
# 2. POBLACIÓN A MITAD DE AÑO (CONAPO) — denominador de todas las tasas
# ---------------------------------------------------------------------------

def cargar_poblacion():
    df = pd.read_csv(ARCHIVO_CONAPO, usecols=["ANIO", "ENTIDAD", "POBLACION"])
    df = df[(df["ANIO"] >= ANIO_INICIO) & (df["ANIO"] <= ANIO_FIN)].copy()
    df["clave_entidad"] = df["ENTIDAD"].apply(clave_de_entidad)
    sin_match = df[df["clave_entidad"].isna()]["ENTIDAD"].unique()
    if len(sin_match):
        raise ValueError(f"CONAPO: entidades sin homologar: {sin_match}")
    pob = (
        df.groupby(["clave_entidad", "ANIO"], as_index=False)["POBLACION"]
        .sum()
        .rename(columns={"ANIO": "anio", "POBLACION": "poblacion_mitad_anio"})
    )
    return pob


# ---------------------------------------------------------------------------
# 3. CENSOS ECONÓMICOS (SAIC) — sector 813 "Asociaciones y organizaciones"
#    Sólo hay dato en años censales: 2003, 2008, 2013, 2018, 2023.
# ---------------------------------------------------------------------------

def cargar_censo_economico():
    df = pd.read_csv(ARCHIVO_SAIC, skiprows=4, encoding="latin1")
    df.columns = ["anio_censal", "entidad_cruda", "actividad", "unidades_economicas", "_extra"]
    df = df[df["anio_censal"].astype(str).str.match(r"^\d{4}$", na=False)].copy()
    df["anio_censal"] = df["anio_censal"].astype(int)
    df["clave_entidad"] = df["entidad_cruda"].str.extract(r"^(\d+)")[0]

    def sumar_actividad(contiene_texto):
        d = df[df["actividad"].str.contains(contiene_texto, case=False, na=False, regex=False)]
        return (
            d.groupby(["clave_entidad", "anio_censal"], as_index=False)["unidades_economicas"]
            .sum()
            .rename(columns={"anio_censal": "anio"})
        )

    total = sumar_actividad("Subsector 813").rename(
        columns={"unidades_economicas": "asociaciones_organizaciones_n"}
    )
    laborales = sumar_actividad("81312").rename(
        columns={"unidades_economicas": "organizaciones_laborales_sindicales_n"}
    )
    civiles = sumar_actividad("81323").rename(
        columns={"unidades_economicas": "organizaciones_civiles_n"}
    )
    return total, laborales, civiles


# ---------------------------------------------------------------------------
# 4. STPS — EMPLAZAMIENTOS A HUELGA Y HUELGAS ESTALLADAS (mensual -> anual)
#    Los archivos vienen como texto UTF-16 separado por tabuladores, en
#    formato ancho (una columna por entidad), con filas mensuales
#    ("2024/Ene", etc.) y filas de resumen anual ("Total") que se descartan
#    aquí porque el resumen anual se recalcula sumando los meses.
# ---------------------------------------------------------------------------

def cargar_serie_stps(archivo, nombre_columna):
    df = pd.read_csv(archivo, sep="\t", encoding="utf-16")
    df = df.rename(columns={df.columns[1]: "periodo"})
    df = df[df["periodo"].astype(str).str.contains("/", na=False)].copy()
    df["anio"] = df["periodo"].str.slice(0, 4).astype(int)

    columnas_entidad = [
        c for c in df.columns
        if c not in ("Número de Emplazamientos", "Huelgas", "Unnamed: 1",
                     "periodo", "Total", "Más de una entidad", "anio")
    ]
    largo = df.melt(
        id_vars=["anio"], value_vars=columnas_entidad,
        var_name="entidad_cruda", value_name=nombre_columna,
    )
    largo[nombre_columna] = largo[nombre_columna].fillna(0)
    largo["clave_entidad"] = largo["entidad_cruda"].apply(clave_de_entidad)

    sin_match = largo[largo["clave_entidad"].isna()]["entidad_cruda"].unique()
    if len(sin_match):
        raise ValueError(f"{archivo}: columnas sin homologar: {sin_match}")

    return largo.groupby(["clave_entidad", "anio"], as_index=False)[nombre_columna].sum()


def detectar_anios_faltantes(serie_anual, nombre_columna):
    """Devuelve la lista de años que NO aparecen para ninguna entidad
    (es decir, el archivo simplemente no trae ese año, no que haya sido cero)."""
    anios_presentes = set(serie_anual["anio"].unique())
    todos = set(range(ANIO_INICIO, ANIO_FIN + 1))
    faltantes = sorted(todos - anios_presentes)
    if faltantes:
        print(f"  aviso: {nombre_columna} no trae los años {faltantes} en ninguna entidad "
              f"(hueco real del archivo, no se va a inventar el dato)")
    return faltantes


# ---------------------------------------------------------------------------
# 5. ACLED — EVENTOS DE PROTESTA (semanal -> anual)
#    Cobertura real: 2018-2024. Se descarta 2017 porque el extracto sólo
#    trae la semana del 30 de diciembre de ese año (dato parcial, no un año).
# ---------------------------------------------------------------------------

def cargar_acled():
    df = pd.read_csv(ARCHIVO_ACLED)
    df["anio"] = pd.to_datetime(df["week"]).dt.year
    df = df[df["anio"] >= 2018].copy()
    df["clave_entidad"] = df["admin1"].apply(clave_de_entidad)

    sin_match = df[df["clave_entidad"].isna()]["admin1"].unique()
    if len(sin_match):
        raise ValueError(f"ACLED: admin1 sin homologar: {sin_match}")

    total = (
        df.groupby(["clave_entidad", "anio"], as_index=False)["events"]
        .sum()
        .rename(columns={"events": "eventos_protesta_n"})
    )

    # sub_event_type que implican respuesta/intervención del Estado frente a la protesta
    tipos_intervencion = ["Protest with intervention", "Excessive force against protesters"]
    con_intervencion = (
        df[df["sub_event_type"].isin(tipos_intervencion)]
        .groupby(["clave_entidad", "anio"], as_index=False)["events"]
        .sum()
        .rename(columns={"events": "protestas_con_intervencion_n"})
    )
    return total, con_intervencion


# ---------------------------------------------------------------------------
# 6. ENSAMBLADO DEL PANEL
# ---------------------------------------------------------------------------

def _fusionar_con_cobertura(panel, tabla, columna, anios_con_cobertura, nombre_cobertura):
    """Une `tabla` al panel. Dentro de los años con cobertura, una celda sin
    fila en `tabla` es un cero real (la fuente cubría y no hubo eventos).
    Fuera de esos años, la celda queda en NaN: la fuente no llega ahí."""
    panel = panel.merge(tabla, on=["clave_entidad", "anio"], how="left")
    dentro_de_cobertura = panel["anio"].isin(anios_con_cobertura)
    panel.loc[dentro_de_cobertura & panel[columna].isna(), columna] = 0
    panel[nombre_cobertura] = np.where(dentro_de_cobertura, "dato_real", "fuera_de_cobertura")
    return panel


def construir_panel():
    print("Cargando fuentes...")
    poblacion = cargar_poblacion()
    total_813, laborales_sindicales, civiles = cargar_censo_economico()

    print("Procesando STPS (emplazamientos)...")
    emplazamientos = cargar_serie_stps(ARCHIVO_EMPLAZAMIENTOS, "emplazamientos_huelga_n")
    detectar_anios_faltantes(emplazamientos, "emplazamientos_huelga_n")

    print("Procesando STPS (huelgas estalladas)...")
    huelgas = cargar_serie_stps(ARCHIVO_HUELGAS, "huelgas_estalladas_n")
    anios_faltantes_huelgas = detectar_anios_faltantes(huelgas, "huelgas_estalladas_n")

    print("Procesando ACLED...")
    protestas, protestas_intervencion = cargar_acled()

    # --- base del panel: 32 entidades x 25 años, siempre completa ---
    panel = poblacion.copy()
    panel["entidad"] = panel["clave_entidad"].map(CATALOGO_ENTIDADES)

    # --- dimensión A: sociedad civil organizada (sólo años censales) ---
    panel = panel.merge(
        total_813.rename(columns={"anio": "anio"}), on=["clave_entidad", "anio"], how="left"
    )
    panel = panel.merge(laborales_sindicales, on=["clave_entidad", "anio"], how="left")
    panel = panel.merge(civiles, on=["clave_entidad", "anio"], how="left")
    panel["cobertura_censo_economico"] = np.where(
        panel["anio"].isin(ANIOS_CENSO_ECONOMICO), "dato_real", "fuera_de_cobertura"
    )

    # --- dimensión B: libertad sindical (huelgas / emplazamientos) ---
    panel = panel.merge(emplazamientos, on=["clave_entidad", "anio"], how="left")
    panel["cobertura_emplazamientos"] = "dato_real"  # cobertura completa 2000-2024

    anios_con_huelgas = [a for a in range(ANIO_INICIO, ANIO_FIN + 1) if a not in anios_faltantes_huelgas]
    panel = _fusionar_con_cobertura(
        panel, huelgas, "huelgas_estalladas_n", anios_con_huelgas, "cobertura_huelgas_estalladas"
    )

    # --- dimensión C: protesta y reunión (ACLED) ---
    panel = _fusionar_con_cobertura(
        panel, protestas, "eventos_protesta_n", ANIOS_ACLED_COBERTURA, "cobertura_eventos_protesta"
    )
    panel = _fusionar_con_cobertura(
        panel, protestas_intervencion, "protestas_con_intervencion_n",
        ANIOS_ACLED_COBERTURA, "_cobertura_protestas_intervencion",
    )
    panel = panel.drop(columns=["_cobertura_protestas_intervencion"])  # redundante con la anterior

    # --- variable de contexto normativo: Ley Federal de Fomento a OSC ---
    # DOF, 9 de febrero de 2004. Es una ley federal: el valor es el mismo
    # para las 32 entidades en un año dado, pero marca un cambio de régimen
    # relevante para toda la dimensión A.
    panel["ley_fomento_federal_vigente"] = (panel["anio"] >= ANIO_LEY_FOMENTO_FEDERAL).astype(int)

    # --- tasas por 100 mil habitantes y proporciones derivadas ---
    pob = panel["poblacion_mitad_anio"]
    panel["asociaciones_organizaciones_tasa100k"] = panel["asociaciones_organizaciones_n"] / pob * 1e5
    panel["organizaciones_laborales_sindicales_tasa100k"] = (
        panel["organizaciones_laborales_sindicales_n"] / pob * 1e5
    )
    panel["organizaciones_civiles_tasa100k"] = panel["organizaciones_civiles_n"] / pob * 1e5
    panel["emplazamientos_huelga_tasa100k"] = panel["emplazamientos_huelga_n"] / pob * 1e5
    panel["huelgas_estalladas_tasa100k"] = panel["huelgas_estalladas_n"] / pob * 1e5
    panel["proporcion_huelgas_estalladas"] = np.where(
        panel["emplazamientos_huelga_n"] > 0,
        panel["huelgas_estalladas_n"] / panel["emplazamientos_huelga_n"],
        np.nan,
    )
    panel["eventos_protesta_tasa100k"] = panel["eventos_protesta_n"] / pob * 1e5
    panel["proporcion_protestas_con_intervencion"] = np.where(
        panel["eventos_protesta_n"] > 0,
        panel["protestas_con_intervencion_n"] / panel["eventos_protesta_n"],
        np.nan,
    )

    # --- orden final de columnas, con nombres legibles ---
    columnas_finales = [
        "clave_entidad", "entidad", "anio", "poblacion_mitad_anio",
        "asociaciones_organizaciones_n", "asociaciones_organizaciones_tasa100k",
        "organizaciones_laborales_sindicales_n", "organizaciones_laborales_sindicales_tasa100k",
        "organizaciones_civiles_n", "organizaciones_civiles_tasa100k",
        "cobertura_censo_economico",
        "emplazamientos_huelga_n", "emplazamientos_huelga_tasa100k", "cobertura_emplazamientos",
        "huelgas_estalladas_n", "huelgas_estalladas_tasa100k", "cobertura_huelgas_estalladas",
        "proporcion_huelgas_estalladas",
        "eventos_protesta_n", "eventos_protesta_tasa100k", "cobertura_eventos_protesta",
        "protestas_con_intervencion_n", "proporcion_protestas_con_intervencion",
        "ley_fomento_federal_vigente",
    ]
    panel = panel[columnas_finales].sort_values(["clave_entidad", "anio"]).reset_index(drop=True)
    return panel


def imprimir_resumen_cobertura(panel):
    total_celdas = len(panel)
    print(f"\nResumen de cobertura ({total_celdas} filas = 32 entidades x "
          f"{ANIO_FIN - ANIO_INICIO + 1} años):")
    variables = [
        "asociaciones_organizaciones_n",
        "organizaciones_laborales_sindicales_n",
        "organizaciones_civiles_n",
        "emplazamientos_huelga_n",
        "huelgas_estalladas_n",
        "eventos_protesta_n",
        "protestas_con_intervencion_n",
    ]
    for v in variables:
        n = panel[v].notna().sum()
        print(f"  {v}: {n}/{total_celdas} ({n / total_celdas:.0%})")


if __name__ == "__main__":
    panel = construir_panel()
    panel.to_csv(OUTPUT_FILE, index=False)
    imprimir_resumen_cobertura(panel)
    print(f"\nPanel guardado en: {OUTPUT_FILE.resolve()}")
