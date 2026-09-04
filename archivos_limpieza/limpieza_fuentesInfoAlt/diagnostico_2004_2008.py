#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_2004_2008.py
========================
SCRIPT 2 de 2.

Diagnostica la calidad de los microdatos y de las estimaciones generadas por
estimaciones_2004_2008.py. Responde tres preguntas distintas:

  1. Estan limpios los archivos?  (distribucion de codigos crudos, vacios,
     codigos fuera del mapa de recodificacion, pases condicionales)
  2. Es correcto el universo?     (los factores expanden al total de hogares?
     incluyen hogares sin electricidad?)
  3. Que tan confiables son las estimaciones? (CV, amplitud de intervalos,
     banderas de fragilidad, y la relacion entre nivel del indicador y
     precision, que es el insumo de la seccion de analisis)

SALIDAS
-------
    diagnostico_2004_2008.csv        precision por ano x entidad x indicador
    codigos_crudos_2004_2008.csv     distribucion de codigos, cruda y ponderada
    diagnostico_2004_2008.txt        reporte legible con las advertencias

USO
---
    python diagnostico_2004_2008.py --dir ruta/a/los/dbf \
        --estimaciones resultados/estimaciones_2004_2008.csv \
        --salida resultados/

Requiere haber corrido antes estimaciones_2004_2008.py.

Dependencias: pip install pandas numpy dbfread
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

from config_endutih import (ADVERTENCIA, CONFIG, INDICADORES, RECODE_DEFAULT,
                            UMBRAL_FRAGIL, UMBRAL_MUY_FRAGIL,
                            columna, leer_dbf)


# ---------------------------------------------------------------------------
# Parte 1 y 2: integridad de los archivos y del universo
# ---------------------------------------------------------------------------

def revisar_archivos(directorio, log):
    """Recorre los DBF y reporta codigos crudos, pases condicionales y
    consistencia del universo. Devuelve la tabla de codigos."""
    registros = []

    for anio in sorted(CONFIG):
        cfg = CONFIG[anio]
        ruta = os.path.join(directorio, cfg["archivo"])
        if not os.path.exists(ruta):
            log.append(f"[{anio}] FALTA {ruta}. Se omite el ano.")
            continue

        df = leer_dbf(ruta)
        w = pd.to_numeric(columna(df, cfg["factor"]), errors="coerce")
        ent = pd.to_numeric(columna(df, "ENT"), errors="coerce")

        log.append("")
        log.append(f"[{anio}] {cfg['programa']}  |  anfitriona: {cfg['anfitriona']}")
        log.append(f"        {len(df):,} registros | {w.sum():,.0f} hogares expandidos "
                   f"| {ent.nunique()} entidades")
        log.append(f"        n por entidad: min {ent.value_counts().min()}, "
                   f"mediana {int(ent.value_counts().median())}, "
                   f"max {ent.value_counts().max()}")
        if cfg["nota"]:
            log.append(f"        NOTA: {cfg['nota']}")

        # --- Universo: incluye hogares sin electricidad? ---
        if cfg["electricidad"]:
            e = pd.to_numeric(columna(df, cfg["electricidad"]), errors="coerce")
            sin_luz = float(w[e == 2].sum() / w.sum() * 100)
            log.append(f"        Hogares SIN energia electrica dentro del universo: "
                       f"{sin_luz:.2f}%")
            log.append(f"        -> El denominador NO esta restringido a hogares "
                       f"electrificados. El problema de denominador de los tabulados "
                       f"publicados no aplica aqui.")
        else:
            log.append(f"        Sin variable de electricidad este ano: no se puede "
                       f"verificar el universo desde el microdato.")

        # --- Pase condicional: internet depende de tener computadora? ---
        if cfg.get("computadora") and cfg["vars"].get("internet"):
            pc = pd.to_numeric(columna(df, cfg["computadora"]), errors="coerce")
            net = pd.to_numeric(columna(df, cfg["vars"]["internet"]), errors="coerce")
            sin_pc = pc == 2
            net_valido = net.isin([1, 2])
            n_omitidos = int((sin_pc & ~net_valido).sum())
            n_net_sin_pc = int((sin_pc & (net == 1)).sum())
            if n_omitidos > len(df) * 0.05:
                log.append(f"        PASE CONDICIONAL DETECTADO: {n_omitidos:,} hogares "
                           f"sin computadora ({n_omitidos/len(df)*100:.1f}%) no tienen "
                           f"respuesta valida de internet.")
                log.append(f"        -> Esos casos se cuentan como SIN internet. "
                           f"Tratarlos como faltantes multiplicaria la estimacion.")
            else:
                log.append(f"        Sin pase condicional: internet se pregunto a todos. "
                           f"{n_net_sin_pc} hogares reportan internet sin computadora.")

        # --- Distribucion de codigos crudos ---
        for ind in INDICADORES:
            var = cfg["vars"].get(ind)
            if not var:
                log.append(f"        '{ind}': reactivo inexistente este ano.")
                continue

            cruda = pd.to_numeric(columna(df, var), errors="coerce")
            mapa = (cfg["recode"] or {}).get(ind, RECODE_DEFAULT)

            for codigo, idx in cruda.fillna(-999).groupby(cruda.fillna(-999)).groups.items():
                registros.append({
                    "anio": anio, "indicador": ind, "variable": var,
                    "codigo": "vacio" if codigo == -999 else int(codigo),
                    "en_mapa": codigo in mapa,
                    "n": len(idx),
                    "pct_muestra": round(len(idx) / len(df) * 100, 3),
                    "pct_ponderado": round(w[idx].sum() / w.sum() * 100, 3),
                })

            fuera = cruda[cruda.notna() & ~cruda.isin(mapa.keys())]
            if len(fuera):
                log.append(f"        AVISO '{ind}': {len(fuera)} registros con codigos "
                           f"fuera del mapa: {sorted(fuera.unique())[:8]}")

    return pd.DataFrame(registros)


# ---------------------------------------------------------------------------
# Parte 3: confiabilidad de las estimaciones
# ---------------------------------------------------------------------------

def revisar_estimaciones(est, log):
    """Anade banderas de fragilidad y resume la precision."""
    d = est[est.cve_ent > 0].copy()
    d["fragil"] = d["cv"] > UMBRAL_FRAGIL
    d["muy_fragil"] = d["cv"] > UMBRAL_MUY_FRAGIL
    d["amplitud_ic"] = (d["ic95_sup"] - d["ic95_inf"]).round(2)
    d["amplitud_relativa"] = (d["amplitud_ic"] / d["pct"]).round(2)

    log.append("")
    log.append("=" * 74)
    log.append("PRECISION POR ANO E INDICADOR (solo entidades, excluye nacional)")
    log.append("=" * 74)
    res = d.groupby(["indicador", "anio"]).agg(
        cv_mediano=("cv", "median"),
        fragiles=("fragil", "sum"),
        muy_fragiles=("muy_fragil", "sum"),
        n_ef_mediano=("n_efectivo", "median"),
        amplitud_ic_mediana=("amplitud_ic", "median"),
    ).round(1)
    log.append(res.to_string())
    log.append("")
    log.append(f"fragiles      = CV > {UMBRAL_FRAGIL}%  (umbral tipico de no publicacion)")
    log.append(f"muy_fragiles  = CV > {UMBRAL_MUY_FRAGIL}%")

    log.append("")
    log.append("=" * 74)
    log.append("RELACION ENTRE NIVEL DEL INDICADOR Y FRAGILIDAD")
    log.append("=" * 74)
    log.append("Insumo directo para la seccion que analiza este fenomeno.")
    log.append("")
    for ind in sorted(d.indicador.unique()):
        s = d[d.indicador == ind].dropna(subset=["pct", "cv"])
        if len(s) > 2:
            r = np.corrcoef(s["pct"], s["cv"])[0, 1]
            log.append(f"  {ind:<12} corr(nivel, CV) = {r:+.2f}   "
                       f"CV mediano {s['cv'].median():5.1f}%   "
                       f"amplitud IC mediana {s['amplitud_ic'].median():.1f} pp")
    log.append("")
    log.append("  Una correlacion negativa fuerte indica que la precision es peor")
    log.append("  justamente donde la penetracion es baja. Es decir, los estados que")
    log.append("  sostendrian el argumento sobre desigualdad territorial son aquellos")
    log.append("  cuyo dato es menos confiable.")

    # Los 15 casos mas fragiles
    peores = d.nlargest(15, "cv")[["anio", "entidad", "indicador", "pct",
                                   "ic95_inf", "ic95_sup", "cv", "n_muestra"]]
    log.append("")
    log.append("Las 15 estimaciones menos confiables:")
    log.append(peores.to_string(index=False))

    return d


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".", help="Carpeta con los .dbf de hogares")
    ap.add_argument("--estimaciones", default="estimaciones_2004_2008.csv",
                    help="Salida del script 1")
    ap.add_argument("--salida", default=".", help="Carpeta de salida")
    args = ap.parse_args()

    if not os.path.exists(args.estimaciones):
        sys.exit(f"No encuentro {args.estimaciones}. "
                 f"Corre primero estimaciones_2004_2008.py")

    est = pd.read_csv(args.estimaciones)
    os.makedirs(args.salida, exist_ok=True)

    log = ["=" * 74,
           "DIAGNOSTICO DE MICRODATOS Y ESTIMACIONES, EDUTIH/ENDUTIH 2004-2008",
           "=" * 74]

    codigos = revisar_archivos(args.dir, log)
    diag = revisar_estimaciones(est, log)

    log.append("")
    log.append("=" * 74)
    log.append("ADVERTENCIA QUE DEBE ACOMPANAR CUALQUIER USO DE ESTAS CIFRAS")
    log.append("=" * 74)
    log.extend(ADVERTENCIA)

    ruta_diag = os.path.join(args.salida, "diagnostico_2004_2008.csv")
    diag[["anio", "cve_ent", "entidad", "indicador", "pct", "ee", "cv",
          "ic95_inf", "ic95_sup", "amplitud_ic", "amplitud_relativa",
          "cv_deff1.5", "cv_deff2.0", "n_muestra", "n_efectivo",
          "fragil", "muy_fragil"]].to_csv(ruta_diag, index=False, encoding="utf-8-sig")

    ruta_cod = os.path.join(args.salida, "codigos_crudos_2004_2008.csv")
    codigos.to_csv(ruta_cod, index=False, encoding="utf-8-sig")

    ruta_txt = os.path.join(args.salida, "diagnostico_2004_2008.txt")
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    print("\n".join(log))
    print(f"\nGenerados:\n  {ruta_diag}\n  {ruta_cod}\n  {ruta_txt}")


if __name__ == "__main__":
    main()
