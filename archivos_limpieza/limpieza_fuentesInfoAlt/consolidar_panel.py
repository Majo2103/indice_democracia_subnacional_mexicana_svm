#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolidar_panel.py
===================
Une los cuatro bloques de la serie en un solo panel largo:

    2004-2008   microdatos EDUTIH/ENDUTIH   estimaciones_2004_2008.csv
    2009        microdatos ENDUTIH          estimaciones_2009.csv
    2010-2014   tabulados MODUTIH           tabulados_2010_2014.xlsx
    2015-2024   tabulados ENDUTIH           tabulados_2015_2024.xlsx


SALIDA
------
    panel_completo.csv    panel largo, una fila por ano x entidad x indicador
    panel_ancho.csv       una fila por entidad, columnas indicador_ano
    consolidacion.txt     reporte de cobertura, huecos y verificaciones

USO
---
    python consolidar_panel.py

Las rutas y las opciones se configuran en el bloque RUTAS Y OPCIONES, justo
abajo. 

"""

import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# RUTAS Y OPCIONES  <-- lo unico que normalmente hay que tocar
# ---------------------------------------------------------------------------

ARCHIVO_2004 = "estimaciones_2004_2008.csv"    # microdatos 2004-2008
ARCHIVO_2009 = "estimaciones_2009.csv"         # microdatos 2009
ARCHIVO_2010 = "tabulados_2010_2014.xlsx"      # tabulados MODUTIH
ARCHIVO_2015 = "tabulados_2015_2024.xlsx"      # tabulados ENDUTIH

SALIDA = "panel"        # carpeta donde se escriben los tres archivos de salida

# True  -> los anos sin dato entran como filas con pct vacio y su motivo_na.
#          Asi los NA son visibles y contabilizables.
# False -> esos anos simplemente no aparecen en el panel.
INCLUIR_FALTANTES = True


# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------

BASE = ['anio', 'cve_ent', 'entidad', 'indicador', 'pct', 'ee', 'cv',
        'ic95_inf', 'ic95_sup', 'n_muestra', 'n_efectivo',
        'hogares_exp', 'hogares_exp_total',
        'ic95_inf_deff1.5', 'ic95_sup_deff1.5', 'cv_deff1.5',
        'ic95_inf_deff2.0', 'ic95_sup_deff2.0', 'cv_deff2.0']

EXTRA = ['n_upm', 'deff_estimado', 'variable']

TRAZA = ['bloque', 'tipo_fuente', 'metodo_varianza', 'fragil', 'motivo_na']

FINAL = BASE + EXTRA + TRAZA

INDICADORES = ['internet', 'television', 'radio', 'electricidad']

ENTIDADES = {
    0: "Nacional",
    1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur",
    4: "Campeche", 5: "Coahuila", 6: "Colima", 7: "Chiapas", 8: "Chihuahua",
    9: "Ciudad de Mexico", 10: "Durango", 11: "Guanajuato", 12: "Guerrero",
    13: "Hidalgo", 14: "Jalisco", 15: "Mexico", 16: "Michoacan",
    17: "Morelos", 18: "Nayarit", 19: "Nuevo Leon", 20: "Oaxaca",
    21: "Puebla", 22: "Queretaro", 23: "Quintana Roo", 24: "San Luis Potosi",
    25: "Sinaloa", 26: "Sonora", 27: "Tabasco", 28: "Tamaulipas",
    29: "Tlaxcala", 30: "Veracruz", 31: "Yucatan", 32: "Zacatecas",
}

# Metadatos de cada bloque
BLOQUES = {
    'b2004': dict(nombre='2004-2008 microdatos', anios=range(2004, 2009),
                  tipo_fuente='microdatos',
                  metodo_varianza='Kish (ignora conglomeracion, es un piso)'),
    'b2009': dict(nombre='2009 microdatos con UPM', anios=[2009],
                  tipo_fuente='microdatos',
                  metodo_varianza='conglomerado ultimo (varianza de diseno)'),
    'b2010': dict(nombre='2010-2014 tabulados MODUTIH', anios=[2010, 2011, 2013, 2014],
                  tipo_fuente='tabulado',
                  metodo_varianza='no disponible'),
    'b2015': dict(nombre='2015-2024 tabulados ENDUTIH', anios=[2015, 2016, 2017, 2018,
                                                               2020, 2021, 2022, 2023, 2024],
                  tipo_fuente='tabulado',
                  metodo_varianza='CV publicado por INEGI; IC95 recalculado (Wilson)'),
}

# Anos sin dato y su motivo. Se insertan como filas explicitas con pct vacio
# para que los NA sean visibles y contabilizables, no huecos silenciosos.
FALTANTES = {
    2000: 'Sin levantamiento. El MODUTIH inicia en 2001.',
    2001: 'Base urbana (encuesta anfitriona ENCO). Sin representatividad estatal ni variable de entidad.',
    2002: 'Base urbana (encuesta anfitriona ENCO). Sin representatividad estatal ni variable de entidad.',
    2003: 'El MODUTIH no se levanto ese ano.',
    2012: 'El MODUTIH 2012 no publica desglose por entidad federativa.',
    2019: 'Excluido por decision del usuario.',
}

UMBRAL_FRAGIL = 15.0


# ---------------------------------------------------------------------------
# Lectura y alineacion
# ---------------------------------------------------------------------------

def leer(ruta):
    if not os.path.exists(ruta):
        return None
    if ruta.lower().endswith(('.xlsx', '.xlsm')):
        return pd.read_excel(ruta, sheet_name='estimaciones')
    return pd.read_csv(ruta)


def alinear(df, clave, log):
    """Deja el DataFrame con el esquema comun y le pega la trazabilidad."""
    meta = BLOQUES[clave]
    d = df.copy()

    # columnas del esquema que este bloque no trae
    for c in BASE + EXTRA:
        if c not in d.columns:
            d[c] = np.nan

    d['bloque'] = meta['nombre']
    d['tipo_fuente'] = meta['tipo_fuente']
    d['metodo_varianza'] = meta['metodo_varianza']
    d['motivo_na'] = ""
    d['fragil'] = np.nan   # se calcula al final, ya con todos los bloques juntos

    # entidad homologada por CLAVE, nunca por nombre
    d['cve_ent'] = pd.to_numeric(d['cve_ent'], errors='coerce').astype('Int64')
    d['entidad'] = d['cve_ent'].map(ENTIDADES)
    if d['entidad'].isna().any():
        malas = d.loc[d['entidad'].isna(), 'cve_ent'].unique()
        log.append(f"  AVISO: claves de entidad no reconocidas: {list(malas)}")

    d['indicador'] = d['indicador'].astype(str).str.strip().str.lower()
    desconocidos = set(d['indicador']) - set(INDICADORES)
    if desconocidos:
        log.append(f"  AVISO: indicadores fuera del catalogo: {desconocidos}")

    anios = sorted(pd.to_numeric(d['anio'], errors='coerce').dropna().astype(int).unique())
    esperados = sorted(meta['anios'])
    if anios != esperados:
        log.append(f"  AVISO: anios encontrados {anios}, esperados {esperados}")

    log.append(f"  {len(d):,} filas | anios {anios[0]}-{anios[-1]} "
               f"| indicadores {sorted(set(d['indicador']))}")
    return d[FINAL]


def filas_faltantes(indicadores, log):
    """Filas explicitas para los anos sin dato."""
    out = []
    for anio, motivo in FALTANTES.items():
        for cve, nombre in ENTIDADES.items():
            for ind in indicadores:
                fila = {c: np.nan for c in FINAL}
                fila.update(anio=anio, cve_ent=cve, entidad=nombre, indicador=ind,
                            bloque='sin dato', tipo_fuente='sin dato',
                            metodo_varianza='no aplica', fragil=np.nan,
                            motivo_na=motivo, variable='')
                out.append(fila)
    log.append(f"  {len(out):,} filas de NA explicito para {sorted(FALTANTES)}")
    return pd.DataFrame(out)[FINAL]


# ---------------------------------------------------------------------------
# Verificaciones
# ---------------------------------------------------------------------------

def verificar(p, log):
    log.append("")
    log.append("=" * 74)
    log.append("VERIFICACIONES")
    log.append("=" * 74)

    dup = p.duplicated(subset=['anio', 'cve_ent', 'indicador'], keep=False)
    if dup.any():
        log.append(f"ERROR: {int(dup.sum())} filas duplicadas en (anio, cve_ent, indicador).")
        log.append(p[dup].head(10)[['anio', 'entidad', 'indicador', 'bloque']].to_string(index=False))
    else:
        log.append("Sin duplicados en la llave (anio, cve_ent, indicador). OK")

    con = p[p['pct'].notna()]
    fuera = con[(con['pct'] < 0) | (con['pct'] > 100)]
    log.append(f"Porcentajes fuera de [0, 100]: {len(fuera)}")

    # coherencia entre pct y los absolutos, donde ambos existen
    m = con['hogares_exp'].notna() & con['hogares_exp_total'].notna() & (con['hogares_exp_total'] > 0)
    if m.any():
        calc = con.loc[m, 'hogares_exp'] / con.loc[m, 'hogares_exp_total'] * 100
        dif = (calc - con.loc[m, 'pct']).abs()
        log.append(f"Coherencia pct vs absolutos: max discrepancia {dif.max():.3f} pp "
                   f"en {int(m.sum()):,} filas comparables")

    log.append("")
    log.append("COBERTURA (numero de entidades con dato, de 33 incluyendo nacional)")
    cob = (p[p['pct'].notna()]
           .groupby(['anio', 'indicador'])['cve_ent'].nunique()
           .unstack(fill_value=0))
    for ind in INDICADORES:
        if ind not in cob.columns:
            cob[ind] = 0
    log.append(cob[INDICADORES].to_string())

    log.append("")
    log.append("FRAGILIDAD (CV > %.0f%%, solo entidades, excluye nacional)" % UMBRAL_FRAGIL)
    d = p[(p['cve_ent'] > 0) & p['cv'].notna()]
    if len(d):
        fr = d.groupby(['anio', 'indicador'])['fragil'].agg(['sum', 'count'])
        fr['pct_fragil'] = (fr['sum'] / fr['count'] * 100).round(0)
        log.append(fr['pct_fragil'].unstack(fill_value=np.nan).to_string())
        log.append("(vacio = ese bloque no publica medidas de precision)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log = ["=" * 74, "CONSOLIDACION DEL PANEL", "=" * 74]
    partes = []

    for clave, ruta in [('b2004', ARCHIVO_2004), ('b2009', ARCHIVO_2009),
                        ('b2010', ARCHIVO_2010), ('b2015', ARCHIVO_2015)]:
        log.append("")
        log.append(f"[{BLOQUES[clave]['nombre']}]  {ruta}")
        d = leer(ruta)
        if d is None:
            log.append("  NO ENCONTRADO. Se omite este bloque.")
            continue
        partes.append(alinear(d, clave, log))

    if not partes:
        print("\n".join(log))
        sys.exit("\nNo se cargo ningun bloque. Revisa las variables ARCHIVO_* "
                 "al inicio del script, o corre el script desde la carpeta "
                 "donde estan los archivos.")

    p = pd.concat(partes, ignore_index=True)
    p['fragil'] = np.where(p['cv'].notna(), p['cv'] > UMBRAL_FRAGIL, np.nan)

    if INCLUIR_FALTANTES:
        log.append("")
        log.append("[anos sin dato]")
        p = pd.concat([p, filas_faltantes(sorted(set(p['indicador'])), log)],
                      ignore_index=True)

    p['anio'] = pd.to_numeric(p['anio'], errors='coerce').astype('Int64')
    p = p.sort_values(['indicador', 'anio', 'cve_ent']).reset_index(drop=True)

    verificar(p, log)

    os.makedirs(SALIDA, exist_ok=True)
    r_largo = os.path.join(SALIDA, "panel_completo.csv")
    p.to_csv(r_largo, index=False, encoding="utf-8-sig")

    ancho = p.pivot_table(index=['cve_ent', 'entidad'],
                          columns=['indicador', 'anio'], values='pct')
    ancho.columns = [f"{i}_{a}" for i, a in ancho.columns]
    ancho = ancho.reindex(sorted(ancho.columns), axis=1).reset_index()
    r_ancho = os.path.join(SALIDA, "panel_ancho.csv")
    ancho.to_csv(r_ancho, index=False, encoding="utf-8-sig")

    log.append("")
    log.append("=" * 74)
    log.append(f"RESULTADO: {len(p):,} filas | "
               f"{int(p['pct'].notna().sum()):,} con dato | "
               f"{int(p['pct'].isna().sum()):,} NA")
    log.append("=" * 74)
    log.append("RECORDATORIO: los bloques no son comparables en precision.")
    log.append("Antes de calcular cualquier medida de dispersion interestatal, filtra o")
    log.append("pondera por la columna fragil, y no mezcles intervalos de bloques distintos")
    log.append("sin decir que se calcularon con metodos diferentes.")

    r_log = os.path.join(SALIDA, "consolidacion.txt")
    with open(r_log, "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    print("\n".join(log))
    print(f"\nGenerados en {os.path.abspath(SALIDA)}:")
    for r in (r_largo, r_ancho, r_log):
        print("  ", os.path.basename(r))


if __name__ == "__main__":
    main()