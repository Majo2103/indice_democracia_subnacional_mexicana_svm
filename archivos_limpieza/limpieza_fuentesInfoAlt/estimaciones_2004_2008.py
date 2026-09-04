#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
estimaciones_2004_2008.py
=========================
SCRIPT 1 de 2.

Estima, por entidad federativa y ano (2004-2008), el porcentaje de hogares con
internet, television y radio, desde los microdatos de hogares de la
EDUTIH / ENDUTIH del INEGI.

SALIDA
------
    estimaciones_2004_2008.csv

    Una fila por ano x entidad x indicador, mas la fila nacional (cve_ent = 0).
    Columnas: estimacion puntual, error estandar, coeficiente de variacion,
    intervalo de Wilson al 95%, y dos escenarios de sensibilidad con efecto
    de diseno supuesto (deff 1.5 y 2.0).

DECISIONES METODOLOGICAS
------------------------
* Intervalo de Wilson, no normal simetrico. Con proporciones cercanas a cero
  (Oaxaca ~2.7% en 2008) el normal produce limites inferiores negativos, que
  son imposibles para una proporcion. Wilson respeta la frontera y queda
  asimetrico: se estira hacia arriba y se comprime hacia abajo.
* Varianza con tamano efectivo de Kish. Los archivos no traen UPM ni estrato,
  asi que se corrige la dispersion de los factores de expansion pero NO la
  conglomeracion. Los intervalos son un PISO de la incertidumbre real.
* Escenarios deff 1.5 y 2.0 para acotar el orden de magnitud de lo que falta.
* Codigo 9 ("no sabe") -> NA. Pesa menos de 0.5% ponderado en todos los anos.
* 2004: el codigo 0 de internet es "no aplica" (hogar sin computadora) y se
  cuenta como SIN internet. Ver config_endutih.py.

USO
---
    python estimaciones_2004_2008.py --dir ruta/a/los/dbf --salida resultados/

Corre este script ANTES que diagnostico_2004_2008.py, que consume su salida.

Dependencias: pip install pandas numpy dbfread
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

from config_endutih import (CONFIG, DEFFS, ENTIDADES, INDICADORES, Z95,
                            columna, leer_dbf, recodificar)


# ---------------------------------------------------------------------------
# Precision
# ---------------------------------------------------------------------------

def n_efectivo_kish(w):
    """Tamano efectivo de muestra de Kish: (sum w)^2 / sum(w^2).

    Corrige la perdida de precision por dispersion de los factores de
    expansion. NO corrige conglomeracion, porque no hay UPM en estos archivos.
    """
    s1, s2 = w.sum(), (w ** 2).sum()
    return (s1 ** 2 / s2) if s2 > 0 else 0.0


def wilson(p, n, z=Z95):
    """Intervalo de Wilson al nivel dado por z. Siempre dentro de [0, 1]."""
    if n <= 0 or not np.isfinite(p):
        return np.nan, np.nan
    d = 1 + z ** 2 / n
    centro = (p + z ** 2 / (2 * n)) / d
    medio = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return max(centro - medio, 0.0), min(centro + medio, 1.0)


def estimar(y, w):
    """Proporcion ponderada y medidas de precision para un subconjunto."""
    ok = y.notna() & w.notna() & (w > 0)
    y, w = y[ok], w[ok]
    n = int(ok.sum())
    if n == 0 or w.sum() == 0:
        return None

    p = float((w * y).sum() / w.sum())
    neff = n_efectivo_kish(w)
    ee = float(np.sqrt(max(p * (1 - p), 0) / neff)) if neff > 0 else np.nan
    li, ls = wilson(p, neff)

    fila = {
        "pct": round(p * 100, 2),
        "ee": round(ee * 100, 3) if np.isfinite(ee) else np.nan,
        "cv": round(ee / p * 100, 1) if (p > 0 and np.isfinite(ee)) else np.nan,
        "ic95_inf": round(li * 100, 2),
        "ic95_sup": round(ls * 100, 2),
        "n_muestra": n,
        "n_efectivo": round(neff, 1),
        "hogares_exp": int((w * y).sum()),
        "hogares_exp_total": int(w.sum()),
    }

    # Sensibilidad: un deff de k equivale a dividir el n efectivo entre k
    for deff in DEFFS:
        ne = neff / deff
        li_d, ls_d = wilson(p, ne)
        ee_d = np.sqrt(max(p * (1 - p), 0) / ne) if ne > 0 else np.nan
        fila[f"ic95_inf_deff{deff}"] = round(li_d * 100, 2)
        fila[f"ic95_sup_deff{deff}"] = round(ls_d * 100, 2)
        fila[f"cv_deff{deff}"] = round(ee_d / p * 100, 1) if (
            p > 0 and np.isfinite(ee_d)) else np.nan
    return fila


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".", help="Carpeta con los .dbf de hogares")
    ap.add_argument("--salida", default=".", help="Carpeta de salida")
    args = ap.parse_args()

    filas = []
    for anio in sorted(CONFIG):
        cfg = CONFIG[anio]
        ruta = os.path.join(args.dir, cfg["archivo"])
        if not os.path.exists(ruta):
            print(f"[{anio}] FALTA {ruta}. Se omite el ano.")
            continue

        df = leer_dbf(ruta)
        w = pd.to_numeric(columna(df, cfg["factor"]), errors="coerce")
        ent = pd.to_numeric(columna(df, "ENT"), errors="coerce").astype("Int64")
        print(f"[{anio}] {cfg['programa']}: {len(df):,} registros, "
              f"{w.sum():,.0f} hogares expandidos, {ent.nunique()} entidades")

        for ind in INDICADORES:
            var = cfg["vars"].get(ind)
            if not var:
                print(f"         '{ind}': no existe este ano, se omite.")
                continue

            y = recodificar(pd.to_numeric(columna(df, var), errors="coerce"), anio, ind)

            nac = estimar(y, w)
            if nac:
                filas.append({"anio": anio, "cve_ent": 0, "entidad": "Nacional",
                              "indicador": ind, "variable": var, **nac})

            for cve, nombre in ENTIDADES.items():
                m = (ent == cve)
                if not m.any():
                    continue
                r = estimar(y[m], w[m])
                if r:
                    filas.append({"anio": anio, "cve_ent": cve, "entidad": nombre,
                                  "indicador": ind, "variable": var, **r})

    if not filas:
        sys.exit("No se genero ninguna estimacion. Revisa rutas y nombres de archivo.")

    est = pd.DataFrame(filas).sort_values(["indicador", "anio", "cve_ent"])
    os.makedirs(args.salida, exist_ok=True)
    ruta = os.path.join(args.salida, "estimaciones_2004_2008.csv")
    est.to_csv(ruta, index=False, encoding="utf-8-sig")

    print(f"\n{len(est):,} estimaciones generadas.")
    print(f"Archivo: {ruta}")
    print("\nSiguiente paso: python diagnostico_2004_2008.py")


if __name__ == "__main__":
    main()
