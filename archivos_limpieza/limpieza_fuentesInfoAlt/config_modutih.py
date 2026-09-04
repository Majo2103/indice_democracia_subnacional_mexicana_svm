#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_endutih.py
=================
Configuracion compartida por estimaciones_2004_2008.py y
diagnostico_2004_2008.py. No se ejecuta solo.

Aqui viven los nombres de variables, verificados uno por uno contra los
diccionarios oficiales del INEGI de cada edicion. Si algo cambia, se cambia
aqui y ambos scripts lo recogen.
"""

import numpy as np
import pandas as pd

try:
    from dbfread import DBF
except ImportError:  # pragma: no cover
    raise SystemExit("Falta dbfread. Instala con: pip install dbfread")


# ---------------------------------------------------------------------------
# Variables por ano
# ---------------------------------------------------------------------------
# Ojo con los prefijos: cambian de edicion en edicion.
#   2004        -> COMP_
#   2005, 2006  -> ENDU_
#   2007        -> TI_
#   2008        -> TIH_

CONFIG = {
    2004: {
        "archivo": "hogares2004.dbf",
        "programa": "EDUTIH 2004",
        "anfitriona": "Encuesta Nacional de Empleo, II trimestre",
        "factor": "FAC_VIV",
        "vars": {"internet": "COMP_P13", "television": "COMP_P1_1", "radio": None},
        "electricidad": None,
        "computadora": "COMP_P2",
        # El 0 es "no aplica" (hogar sin computadora), NO es "no sabe".
        # Tratarlo como faltante inflaria la estimacion de ~8.7% a ~48%.
        "recode": {"internet": {1: 1.0, 2: 0.0, 0: 0.0, 9: np.nan},
                   "television": {1: 1.0, 2: 0.0}},
        "nota": ("Internet condicionado a tener computadora; codigo 0 = no aplica. "
                 "Sin reactivo de radio. Muestra 30% menor que los demas anos."),
    },
    2005: {
        "archivo": "hogares2005.dbf",
        "programa": "ENDUTIH 2005",
        "anfitriona": "Modulo de caracteristicas laborales",
        "factor": "FAC_VIV",
        "vars": {"internet": "ENDU_P9A", "television": "ENDU_P1B1", "radio": "ENDU_P1A1"},
        "electricidad": None,
        "computadora": "ENDU_P2A",
        "recode": None,
        "nota": "",
    },
    2006: {
        "archivo": "hogares2006.dbf",
        "programa": "ENDUTIH 2006",
        "anfitriona": "ENOE, II trimestre",
        "factor": "FAC_VIV",
        "vars": {"internet": "ENDU_P9A", "television": "ENDU_P1B1", "radio": "ENDU_P1A1"},
        "electricidad": None,
        "computadora": "ENDU_P2A",
        "recode": None,
        "nota": "",
    },
    2007: {
        "archivo": "hogares2007.dbf",
        "programa": "ENDUTIH 2007",
        "anfitriona": "ENOE, I trimestre",
        "factor": "FAC_VIV",
        "vars": {"internet": "TI_P8A", "television": "TI_P1B1", "radio": "TI_P1A1"},
        "electricidad": "TI_P1F",
        "computadora": "TI_P2A",
        "recode": None,
        "nota": "",
    },
    2008: {
        "archivo": "hogares2008.dbf",
        "programa": "ENDUTIH 2008",
        "anfitriona": "ENOE, I trimestre",
        "factor": "FACTOR",
        "vars": {"internet": "TIH_8A", "television": "TIH_1B1", "radio": "TIH_1A1"},
        "electricidad": "TIH_1F",
        "computadora": "TIH_2A",
        "recode": None,
        "nota": "",
    },
}

# Recodificacion cuando el ano no declara una propia
RECODE_DEFAULT = {1: 1.0, 2: 0.0, 9: np.nan}

INDICADORES = ["internet", "television", "radio"]

ENTIDADES = {
    1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur",
    4: "Campeche", 5: "Coahuila", 6: "Colima", 7: "Chiapas", 8: "Chihuahua",
    9: "Ciudad de Mexico", 10: "Durango", 11: "Guanajuato", 12: "Guerrero",
    13: "Hidalgo", 14: "Jalisco", 15: "Mexico", 16: "Michoacan",
    17: "Morelos", 18: "Nayarit", 19: "Nuevo Leon", 20: "Oaxaca",
    21: "Puebla", 22: "Queretaro", 23: "Quintana Roo", 24: "San Luis Potosi",
    25: "Sinaloa", 26: "Sonora", 27: "Tabasco", 28: "Tamaulipas",
    29: "Tlaxcala", 30: "Veracruz", 31: "Yucatan", 32: "Zacatecas",
}

Z95 = 1.959964
DEFFS = [1.5, 2.0]
UMBRAL_FRAGIL = 15.0
UMBRAL_MUY_FRAGIL = 30.0

ADVERTENCIA = [
    "Los archivos 2004-2008 no contienen UPM ni estrato, asi que la varianza se",
    "estima con el tamano efectivo de Kish e IGNORA la conglomeracion del diseno.",
    "Los intervalos reportados son un PISO de la incertidumbre real. Las columnas",
    "cv_deff1.5 y cv_deff2.0 acotan el orden de magnitud bajo efectos de diseno",
    "tipicos de encuestas de hogares por conglomerados.",
    "",
    "Ademas, la muestra no fue disenada para estimaciones por entidad federativa.",
    "Estas cifras no son oficiales y el INEGI no las publica a ese nivel.",
]


# ---------------------------------------------------------------------------
# Utilidades de lectura
# ---------------------------------------------------------------------------

def leer_dbf(ruta):
    """Lee un DBF probando codificaciones. Los archivos viejos del INEGI
    suelen venir en latin-1 y truenan con utf-8."""
    ultimo = None
    for enc in ("latin-1", "cp1252", "utf-8"):
        try:
            return pd.DataFrame(iter(
                DBF(ruta, encoding=enc, load=True, char_decode_errors="replace")))
        except Exception as e:  # noqa: BLE001
            ultimo = e
    raise RuntimeError(f"No se pudo leer {ruta}: {ultimo}")


def columna(df, nombre):
    """Recupera una columna tolerando mayusculas y espacios."""
    mapa = {str(c).strip().upper(): c for c in df.columns}
    real = mapa.get(str(nombre).strip().upper())
    if real is None:
        raise KeyError(f"No existe la columna '{nombre}'. "
                       f"Disponibles: {list(df.columns)[:12]}...")
    return df[real]


def recodificar(cruda, anio, indicador):
    """Convierte el reactivo a 1 / 0 / NaN segun el mapa del ano."""
    cfg = CONFIG[anio]
    mapa = (cfg["recode"] or {}).get(indicador, RECODE_DEFAULT)
    return cruda.map(mapa)
