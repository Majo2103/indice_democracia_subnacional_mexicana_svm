"""
join_final.py
-------------
Une todos los paneles procesados (entidad x año) en un solo archivo:
panel_analisis.csv, con una fila por (cve_ent, anio).

Uso:
    python join_final.py                       # busca en ./datos
    python join_final.py --dir ruta/a/datos    # otra carpeta
    python join_final.py --salida panel_analisis.csv

    
Este archivo une los CSVs de las variables.
Valida que no haya duplicados y da un "reporte de cobertura"
Qué hace:


Nota: Las celdas vacías se conservan vacías (NA)
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ANIO_INICIO, ANIO_FIN = 2000, 2024
N_ENTIDADES = 32

# Nombres que se aceptan como clave de entidad y de año
ALIAS_ENTIDAD = ["cve_ent", "cve_entidad", "clave_ent", "clave_entidad", "cve_edo", "id_entidad"]
ALIAS_ANIO = ["anio", "año", "ano", "year", "anio_cp"]
ALIAS_NOMBRE = ["entidad", "nombre_entidad", "estado", "nom_ent"]

# Archivos que no se unen porque ya están dentro de un panel consolidado
# (p. ej., lpc_panel y sea_panel ya forman parte de
# panel_politicas_dependen_voto_2000_2024.csv) o porque son catálogos.
EXCLUIR_ARCHIVOS = {
    "panel_analisis.csv",
    "lpc_panel.csv",
    "lpc_leyes.csv",
    "sea_panel.csv",
    "sea_fechas.csv",
    "proyeccionesconapo.csv",
    "cobertura_panel_analisis.csv",
}
PATRON_RESPALDO = re.compile(r"(_v\d+|_backup|_respaldo|_old)\.csv$", re.IGNORECASE)

# Columnas de texto/metadatos que no son variables de análisis pero se
# conservan para trazabilidad (se ponen al final del archivo).
COLUMNAS_METADATOS = {"fuente_auditorias"}

# Catálogo INEGI de entidades (para rellenar el nombre si falta)
CATALOGO = {
    1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur",
    4: "Campeche", 5: "Coahuila", 6: "Colima", 7: "Chiapas", 8: "Chihuahua",
    9: "Ciudad de México", 10: "Durango", 11: "Guanajuato", 12: "Guerrero",
    13: "Hidalgo", 14: "Jalisco", 15: "México", 16: "Michoacán",
    17: "Morelos", 18: "Nayarit", 19: "Nuevo León", 20: "Oaxaca",
    21: "Puebla", 22: "Querétaro", 23: "Quintana Roo", 24: "San Luis Potosí",
    25: "Sinaloa", 26: "Sonora", 27: "Tabasco", 28: "Tamaulipas",
    29: "Tlaxcala", 30: "Veracruz", 31: "Yucatán", 32: "Zacatecas",
}


# ---------------------------------------------------------------------------
# Lectura y normalización
# ---------------------------------------------------------------------------
def leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee un CSV probando codificaciones comunes (utf-8 y latin-1)."""
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(ruta, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {ruta.name} con utf-8 ni latin-1")


def encontrar_columna(df: pd.DataFrame, alias: list[str]) -> str | None:
    columnas = {c.strip().lower(): c for c in df.columns}
    for a in alias:
        if a in columnas:
            return columnas[a]
    return None


def normalizar(df: pd.DataFrame, nombre_archivo: str) -> pd.DataFrame | None:
    """Devuelve el panel con claves cve_ent/anio normalizadas, o None si no
    es un panel entidad-año."""
    col_ent = encontrar_columna(df, ALIAS_ENTIDAD)
    col_anio = encontrar_columna(df, ALIAS_ANIO)
    if col_ent is None or col_anio is None:
        print(f"  - {nombre_archivo}: sin clave entidad/año, se omite")
        return None

    df = df.rename(columns={col_ent: "cve_ent", col_anio: "anio"})
    col_nom = encontrar_columna(df, ALIAS_NOMBRE)
    if col_nom and col_nom != "entidad":
        df = df.rename(columns={col_nom: "entidad"})

    # Claves a entero ("01" -> 1). Se descartan filas nacionales (0 o 33).
    df["cve_ent"] = pd.to_numeric(df["cve_ent"], errors="coerce")
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.dropna(subset=["cve_ent", "anio"])
    df["cve_ent"] = df["cve_ent"].astype(int)
    df["anio"] = df["anio"].astype(int)
    fuera = ~df["cve_ent"].between(1, N_ENTIDADES)
    if fuera.any():
        print(f"  - {nombre_archivo}: se descartan {fuera.sum()} filas con "
              f"cve_ent fuera de 1-32 (totales nacionales u otras)")
    df = df[~fuera]
    df = df[df["anio"].between(ANIO_INICIO, ANIO_FIN)]

    dup = df.duplicated(["cve_ent", "anio"])
    if dup.any():
        raise ValueError(
            f"{nombre_archivo}: {dup.sum()} filas duplicadas en (cve_ent, anio). "
            "Revisa el archivo antes de unirlo."
        )
    # Nombres de columnas sin espacios
    df.columns = [c.strip() for c in df.columns]
    return df


def valores_iguales(a: pd.Series, b: pd.Series) -> bool:
    """Compara dos columnas alineadas, tratando NA == NA como iguales y
    usando tolerancia para números."""
    ambos_na = a.isna() & b.isna()
    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
        cerca = np.isclose(a.astype(float), b.astype(float), rtol=1e-6, atol=1e-9)
        return bool((cerca | ambos_na).all())
    return bool(((a.astype(str) == b.astype(str)) | ambos_na).all())


# ---------------------------------------------------------------------------
# Unión
# ---------------------------------------------------------------------------
def unir(carpeta: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    archivos = sorted(p for p in carpeta.rglob("*.csv"))
    if not archivos:
        sys.exit(f"No hay archivos CSV en {carpeta.resolve()}")

    # Malla completa 32 x 25
    malla = pd.MultiIndex.from_product(
        [range(1, N_ENTIDADES + 1), range(ANIO_INICIO, ANIO_FIN + 1)],
        names=["cve_ent", "anio"],
    ).to_frame(index=False)
    panel = malla.copy()
    origen = {}  # variable -> archivo del que salió

    print(f"Leyendo paneles de {carpeta.resolve()}")
    for ruta in archivos:
        nombre = ruta.name
        if nombre.lower() in EXCLUIR_ARCHIVOS or PATRON_RESPALDO.search(nombre):
            print(f"  - {nombre}: excluido (respaldo o ya incluido en otro panel)")
            continue

        df = normalizar(leer_csv(ruta), nombre)
        if df is None:
            continue

        variables = [c for c in df.columns if c not in ("cve_ent", "anio", "entidad")]
        print(f"  + {nombre}: {len(df)} filas, {len(variables)} variables")

        # El nombre de la entidad solo se usa para rellenar
        if "entidad" in df.columns and "entidad" not in panel.columns:
            panel = panel.merge(df[["cve_ent", "anio", "entidad"]],
                                on=["cve_ent", "anio"], how="left")

        nuevas = []
        for v in variables:
            if v not in panel.columns:
                nuevas.append(v)
                continue
            # Variable repetida: comparar contra lo ya unido
            comparar = panel[["cve_ent", "anio", v]].merge(
                df[["cve_ent", "anio", v]], on=["cve_ent", "anio"],
                how="inner", suffixes=("_ya", "_nuevo"))
            if valores_iguales(comparar[f"{v}_ya"], comparar[f"{v}_nuevo"]):
                print(f"      · {v}: repetida en {origen[v]}, valores idénticos; "
                      "se conserva una")
            else:
                n_dif = (~np.isclose(
                    pd.to_numeric(comparar[f"{v}_ya"], errors="coerce"),
                    pd.to_numeric(comparar[f"{v}_nuevo"], errors="coerce"),
                    equal_nan=True)).sum()
                print(f"      ! {v}: repetida en {origen[v]} con {n_dif} valores "
                      f"distintos; se conserva la de {origen[v]}. REVISAR.")
        if nuevas:
            panel = panel.merge(df[["cve_ent", "anio"] + nuevas],
                                on=["cve_ent", "anio"], how="left")
            for v in nuevas:
                origen[v] = nombre

    # Nombre de entidad desde el catálogo cuando falte
    if "entidad" not in panel.columns:
        panel["entidad"] = np.nan
    panel["entidad"] = panel["entidad"].fillna(panel["cve_ent"].map(CATALOGO))

    # Orden de columnas: claves, variables, metadatos
    variables = [c for c in panel.columns
                 if c not in ("cve_ent", "entidad", "anio") and c not in COLUMNAS_METADATOS]
    metadatos = [c for c in panel.columns if c in COLUMNAS_METADATOS]
    panel = panel[["cve_ent", "entidad", "anio"] + variables + metadatos]
    panel = panel.sort_values(["cve_ent", "anio"]).reset_index(drop=True)

    # Reporte de cobertura
    total = len(panel)
    filas = []
    for v in variables + metadatos:
        no_vacias = panel[v].notna()
        anios = panel.loc[no_vacias, "anio"]
        filas.append({
            "variable": v,
            "archivo_origen": origen.get(v, ""),
            "celdas_con_dato": int(no_vacias.sum()),
            "celdas_totales": total,
            "cobertura_pct": round(100 * no_vacias.mean(), 1),
            "primer_anio": int(anios.min()) if len(anios) else None,
            "ultimo_anio": int(anios.max()) if len(anios) else None,
        })
    cobertura = pd.DataFrame(filas)
    return panel, cobertura


def validar(panel: pd.DataFrame) -> None:
    esperado = N_ENTIDADES * (ANIO_FIN - ANIO_INICIO + 1)
    assert len(panel) == esperado, f"Se esperaban {esperado} filas, hay {len(panel)}"
    assert not panel.duplicated(["cve_ent", "anio"]).any(), "Hay duplicados"
    assert panel["entidad"].notna().all(), "Hay entidades sin nombre"
    print(f"\nValidación OK: {len(panel)} filas (32 entidades x "
          f"{ANIO_FIN - ANIO_INICIO + 1} años), sin duplicados.")


def main():
    parser = argparse.ArgumentParser(description="Une los paneles procesados.")
    parser.add_argument("--dir", default="datos",
                        help="Carpeta con los CSV procesados (default: datos")
    parser.add_argument("--salida", default="panel_analisis.csv")
    args = parser.parse_args()

    carpeta = Path(args.dir)
    if not carpeta.exists():
        sys.exit(f"No existe la carpeta {carpeta.resolve()}. Usa --dir para indicarla.")

    panel, cobertura = unir(carpeta)
    validar(panel)

    salida = Path(args.salida)
    panel.to_csv(salida, index=False, encoding="utf-8")
    ruta_cob = salida.with_name("cobertura_" + salida.name)
    cobertura.to_csv(ruta_cob, index=False, encoding="utf-8")

    print(f"\nEscrito {salida} ({panel.shape[1] - 3} variables)")
    print(f"Escrito {ruta_cob}")
    print("\nCobertura por variable:")
    print(cobertura[["variable", "cobertura_pct", "primer_anio", "ultimo_anio"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
