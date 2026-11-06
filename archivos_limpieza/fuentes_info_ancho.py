"""
fuentes_info_ancho.py
---------------------
Convierte panel_fuentesInfo.csv de formato largo (una fila por
entidad-año-indicador) a formato ancho (una fila por entidad-año, con una
columna pct_<indicador> por indicador), para que se pueda unir con
join_final.py.

Entrada (largo):
    anio, cve_ent, entidad, indicador, pct, ee, cv, ..., fragil, motivo_na

Salida (ancho):
    anio, cve_ent, entidad, pct_electricidad, pct_internet, pct_radio, pct_television

Uso:
    python fuentes_info_ancho.py
    python fuentes_info_ancho.py --entrada datos_procesados/panel_fuentesInfo.csv \
                                 --salida datos_procesados/panel_fuentesInfo_ancho.csv
    python fuentes_info_ancho.py --con-fragil      # agrega fragil_<indicador>
    python fuentes_info_ancho.py --incluir-nacional  # conserva cve_ent = 0

Decisiones:
- Se descarta el renglón Nacional (cve_ent = 0) salvo que se pida lo
  contrario: el panel de análisis es solo de las 32 entidades.
- Las celdas sin dato siguen vacías (NA). El motivo de cada vacío está en
  la columna motivo_na del archivo largo, que no se modifica.
- Se arma la malla completa entidad x año, de modo que las combinaciones
  que no existen en el archivo largo (p. ej., electricidad 2004-2009)
  quedan como NA en lugar de desaparecer.
- Con --con-fragil se agrega fragil_<indicador> (1 = estimación frágil,
  0 = no frágil, vacío = sin estimación), por si se quiere filtrar o
  ponderar en el análisis.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

CLAVES = ["anio", "cve_ent", "entidad"]


def a_ancho(largo: pd.DataFrame, con_fragil: bool, incluir_nacional: bool) -> pd.DataFrame:
    faltan = {"anio", "cve_ent", "entidad", "indicador", "pct"} - set(largo.columns)
    if faltan:
        sys.exit(f"Faltan columnas en el archivo de entrada: {sorted(faltan)}")

    if not incluir_nacional:
        largo = largo[largo["cve_ent"] != 0]

    dup = largo.duplicated(["anio", "cve_ent", "indicador"])
    if dup.any():
        sys.exit(f"Hay {dup.sum()} filas duplicadas en (anio, cve_ent, indicador). "
                 "Revisa el archivo antes de convertirlo.")

    # Nombres de indicador limpios para usarlos como nombre de columna
    largo = largo.assign(indicador=largo["indicador"].str.strip().str.lower()
                         .str.replace(r"\s+", "_", regex=True))

    valores = ["pct"] + (["fragil"] if con_fragil else [])
    ancho = largo.pivot(index=["anio", "cve_ent"], columns="indicador", values=valores)
    ancho.columns = [f"{valor}_{ind}" for valor, ind in ancho.columns]

    # Malla completa entidad x año y nombre de la entidad
    entidades = largo[["cve_ent", "entidad"]].drop_duplicates("cve_ent")
    malla = pd.MultiIndex.from_product(
        [sorted(largo["anio"].unique()), sorted(entidades["cve_ent"])],
        names=["anio", "cve_ent"])
    ancho = (ancho.reindex(malla).reset_index()
             .merge(entidades, on="cve_ent", how="left"))

    # Orden: claves, pct_* en orden alfabético, luego fragil_*
    pct = sorted(c for c in ancho.columns if c.startswith("pct_"))
    fragil = sorted(c for c in ancho.columns if c.startswith("fragil_"))
    ancho = ancho[CLAVES + pct + fragil].sort_values(["cve_ent", "anio"])
    for c in fragil:
        ancho[c] = ancho[c].astype("Int64")
    return ancho.reset_index(drop=True)


def main():
    p = argparse.ArgumentParser(description="panel_fuentesInfo largo -> ancho")
    p.add_argument("--entrada", default="panel_fuentesInfo.csv")
    p.add_argument("--salida", default="panel_fuentesInfo_ancho.csv")
    p.add_argument("--con-fragil", action="store_true",
                   help="Agregar columnas fragil_<indicador>")
    p.add_argument("--incluir-nacional", action="store_true",
                   help="Conservar el renglón Nacional (cve_ent = 0)")
    args = p.parse_args()

    largo = pd.read_csv(args.entrada, encoding="utf-8-sig")
    ancho = a_ancho(largo, args.con_fragil, args.incluir_nacional)

    # Validación: una fila por entidad-año
    assert not ancho.duplicated(["anio", "cve_ent"]).any()
    n_ent, n_anios = ancho["cve_ent"].nunique(), ancho["anio"].nunique()
    assert len(ancho) == n_ent * n_anios

    ancho.to_csv(args.salida, index=False, encoding="utf-8")
    print(f"Escrito {args.salida}: {len(ancho)} filas "
          f"({n_ent} entidades x {n_anios} años)")
    print("\nCobertura por indicador (años con dato):")
    for c in [c for c in ancho.columns if c.startswith("pct_")]:
        anios = sorted(ancho.loc[ancho[c].notna(), "anio"].unique())
        print(f"  {c:<18} {ancho[c].notna().mean():6.1%}  "
              f"{len(anios)} años: {anios[0]}-{anios[-1]}" if anios else f"  {c}: sin datos")


if __name__ == "__main__":
    main()
