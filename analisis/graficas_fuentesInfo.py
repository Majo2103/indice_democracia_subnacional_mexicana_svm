#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graficas_capitulo.py
====================
Genera las figuras del capitulo "Fuentes alternativas de informacion" a partir
de panel_completo.csv.

Figuras:
  fig1_series_nacionales   Evolucion nacional de radio, television e internet,
                           2004-2024, con los anos sin dato dejados en blanco.
  fig2_brecha_estatal      Banda entre la entidad con mayor y menor cobertura
                           cada ano, para internet, radio y television.
  fig3_disponibilidad      Que anos tienen dato, de que fuente y con que tipo
                           de medida de precision.
  fig4_fragilidad          Relacion entre nivel del indicador y coeficiente de
                           variacion. Es el sustento de la seccion sobre
                           desigualdad de los datos.

DECISION DE DISENO 
-----------------------------
Las series NO se interpolan sobre los anos faltantes. Matplotlib corta la linea
donde hay NaN, y eso es deliberado: unir 2011 con 2013 con una recta sugeriria
que sabemos que paso en 2012, y no lo sabemos. Los huecos deben verse.

Uso:
    python graficas_capitulo.py

Las rutas se configuran en el bloque RUTAS, justo abajo. No se pasan por
linea de comandos.

Dependencias: pip install pandas numpy matplotlib
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ---------------------------------------------------------------------------
# RUTAS  <-- lo unico que normalmente hay que tocar
# ---------------------------------------------------------------------------

PANEL = "datos/panel_fuentesInfo.csv"      # archivo de entrada
SALIDA = "graficas"                # carpeta donde se guardan las figuras


# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------

COLOR = {"internet": "#1f4e79", "television": "#c55a11",
         "radio": "#548235", "electricidad": "#7f7f7f"}
ETIQ = {"internet": "Internet", "television": "Televisión",
        "radio": "Radio", "electricidad": "Energía eléctrica"}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

ANIOS = list(range(2000, 2025))


def serie_nacional(p, ind):
    """Serie nacional reindexada a todos los anos, con NaN en los faltantes."""
    s = (p[(p.cve_ent == 0) & (p.indicador == ind)]
         .set_index("anio")["pct"].reindex(ANIOS))
    return s


def marcar_huecos(ax, p):
    """Sombrea los anos sin dato para que el hueco sea visible, no invisible."""
    sin = sorted(p[p.bloque == "sin dato"]["anio"].unique())
    for a in sin:
        ax.axvspan(a - 0.5, a + 0.5, color="#000000", alpha=0.05, zorder=0, lw=0)
    return sin


# ---------------------------------------------------------------------------
# Figura 1: series nacionales
# ---------------------------------------------------------------------------

def fig1(p, salida):
    fig, ax = plt.subplots(figsize=(9, 5))
    sin = marcar_huecos(ax, p)

    for ind in ["television", "radio", "internet"]:
        s = serie_nacional(p, ind)
        ax.plot(s.index, s.values, marker="o", markersize=3.5, linewidth=2,
                color=COLOR[ind], label=ETIQ[ind])

    # anotar el cruce entre internet y radio
    inter, rad = serie_nacional(p, "internet"), serie_nacional(p, "radio")
    dif = (inter - rad).dropna()
    cruces = [a for a in dif.index[1:] if dif.loc[a] * dif.loc[dif.index[dif.index.get_loc(a) - 1]] < 0]
    if cruces:
        a = cruces[0]
        ax.axvline(a, color="#999999", linestyle=":", linewidth=1, zorder=1)
        ax.annotate(f"Internet supera\na la radio ({a})", xy=(a, 55),
                    xytext=(a - 5.5, 68), fontsize=8.5, color="#555555",
                    arrowprops=dict(arrowstyle="->", color="#999999", lw=0.8))

    ax.set_xlabel("Año")
    ax.set_ylabel("Hogares con acceso (%)")
    ax.set_title("Acceso de los hogares a medios de información en México, 2004-2024")
    ax.set_xlim(2003, 2025)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(2004, 2025, 2))
    ax.legend(frameon=False, loc="center left")

    manejadores = ax.get_legend_handles_labels()[0]
    ax.legend(handles=manejadores + [Patch(facecolor="#000000", alpha=0.05,
                                           label="Años sin dato")],
              frameon=False, loc="center left", fontsize=9)
    ax.text(0.01, -0.16,
            "Años sin dato: " + ", ".join(str(a) for a in sin) +
            ". Las líneas se interrumpen deliberadamente; no se interpola.",
            transform=ax.transAxes, fontsize=7.5, color="#666666")

    fig.savefig(os.path.join(salida, "serie_accesoMedios_nacional.png"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 2: brecha entre entidades
# ---------------------------------------------------------------------------

def fig2(p, salida):
    d = p[(p.cve_ent > 0) & p.pct.notna()]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharex=True)

    for ax, ind in zip(axes, ["internet", "radio", "television"]):
        g = d[d.indicador == ind].groupby("anio")["pct"]
        mn, mx, md = g.min().reindex(ANIOS), g.max().reindex(ANIOS), g.median().reindex(ANIOS)
        ax.fill_between(ANIOS, mn, mx, color=COLOR[ind], alpha=0.18,
                        label="Rango entre entidades")
        ax.plot(ANIOS, md, color=COLOR[ind], linewidth=2, marker="o",
                markersize=3, label="Mediana estatal")
        ax.plot(ANIOS, mn, color=COLOR[ind], linewidth=0.8, alpha=0.7)
        ax.plot(ANIOS, mx, color=COLOR[ind], linewidth=0.8, alpha=0.7)
        marcar_huecos(ax, p)
        ax.set_title(ETIQ[ind])
        ax.set_xlabel("Año")
        ax.set_xlim(2003, 2025)
        ax.set_ylim(0, 100)
        ax.set_xticks(range(2004, 2025, 4))
        ax.legend(frameon=False, fontsize=8.5)

    axes[0].set_ylabel("Hogares con acceso (%)")
    fig.suptitle("Dispersión entre entidades federativas: internet, radio y televisión",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.savefig(os.path.join(salida, "brecha_medios_estatal.png"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 3: disponibilidad y calidad de los datos
# ---------------------------------------------------------------------------

def fig3(p, salida):
    """Un panel por indicador donde cada ano se pinta segun la calidad del dato.

    Cuatro categorias, de peor a mejor:
      0 sin dato
      1 con dato pero sin medida de precision publicada
      2 con dato y con precision, pero mayoria de entidades fragiles (CV > 15%)
      3 con dato, con precision, y sin fragilidad
    """
    inds = ["internet", "television", "radio", "electricidad"]
    m = np.zeros((len(inds), len(ANIOS)))

    for i, ind in enumerate(inds):
        for j, a in enumerate(ANIOS):
            d = p[(p.anio == a) & (p.indicador == ind) & (p.cve_ent > 0)]
            con = d[d.pct.notna()]
            if len(con) == 0:
                m[i, j] = 0
            elif con.cv.notna().sum() == 0:
                m[i, j] = 1
            else:
                frag = (con.cv > 15).mean()
                m[i, j] = 2 if frag > 0.5 else 3

    cmap = matplotlib.colors.ListedColormap(
        ["#e8e8e8", "#f6c9a0", "#e8825a", "#4a7ba7"])
    fig, ax = plt.subplots(figsize=(11, 3.2))
    ax.imshow(m, aspect="auto", cmap=cmap, vmin=-0.5, vmax=3.5,
              extent=[ANIOS[0] - 0.5, ANIOS[-1] + 0.5, len(inds) - 0.5, -0.5])

    ax.set_yticks(range(len(inds)))
    ax.set_yticklabels([ETIQ[i] for i in inds])
    ax.set_xticks(range(2000, 2025, 2))
    ax.set_xticklabels(range(2000, 2025, 2), rotation=45, ha="right")
    ax.set_xlabel("Año")
    ax.grid(False)
    for k in range(len(inds) + 1):
        ax.axhline(k - 0.5, color="white", linewidth=2)

    leyenda = [
        Patch(facecolor="#e8e8e8", label="Sin dato"),
        Patch(facecolor="#f6c9a0", label="Dato sin medida de precisión"),
        Patch(facecolor="#e8825a", label="Mayoría de entidades frágiles (CV > 15%)"),
        Patch(facecolor="#4a7ba7", label="Dato con precisión aceptable"),
    ]
    ax.legend(handles=leyenda, frameon=False, fontsize=8.5,
              loc="upper center", bbox_to_anchor=(0.5, -0.42), ncol=2)
    ax.set_title("Disponibilidad y calidad del dato estatal, por indicador y año")
    fig.savefig(os.path.join(salida, "disponibilidad_datos_medios.png"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figura 4: fragilidad contra nivel
# ---------------------------------------------------------------------------

def fig4(p, salida):
    d = p[(p.cve_ent > 0) & p.cv.notna() & p.pct.notna()].copy()
    d["micro"] = d.tipo_fuente == "microdatos"

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for ind in ["internet", "television", "radio"]:
        s = d[d.indicador == ind]
        ax.scatter(s.pct, s.cv, s=13, alpha=0.5, color=COLOR[ind],
                   edgecolors="none", label=ETIQ[ind])

    ax.axhline(15, color="#c00000", linestyle="--", linewidth=1)
    ax.text(97, 16.5, "Umbral de fragilidad (CV = 15%)", fontsize=8,
            color="#c00000", ha="right")

    r = np.corrcoef(d[d.indicador == "internet"].pct,
                    d[d.indicador == "internet"].cv)[0, 1]
    #nota de la correlacion cv internet.
    #ax.text(0.98, 0.95, f"Internet: correlación nivel-CV = {r:+.2f}",
            #transform=ax.transAxes, ha="right", fontsize=9, color="#1f4e79")

    ax.set_yscale("log")
    ax.set_xlabel("Cobertura estimada (% de hogares)")
    ax.set_ylabel("Coeficiente de variación (%, escala logarítmica)")
    ax.set_title("Donde el acceso es menor, la estimación es menos confiable")
    ax.legend(frameon=False, fontsize=9)
    ax.text(0.01, -0.15,
            "Cada punto es una entidad-año. Solo se grafican las observaciones "
            "que cuentan con medida de precisión publicada o estimada.",
            transform=ax.transAxes, fontsize=7.5, color="#666666")

    fig.savefig(os.path.join(salida, "fragilidad_datos_medios.png"))
    plt.close(fig)


# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(PANEL):
        raise SystemExit(
            f"No encuentro '{PANEL}'.\n"
            f"Ajusta la variable PANEL al inicio del script o corre el script "
            f"desde la carpeta donde esta el archivo.")

    p = pd.read_csv(PANEL)
    p["anio"] = pd.to_numeric(p["anio"], errors="coerce").astype("Int64")
    os.makedirs(SALIDA, exist_ok=True)

    fig1(p, SALIDA)
    fig2(p, SALIDA)
    fig3(p, SALIDA)
    fig4(p, SALIDA)

    print(f"Panel leido: {PANEL} ({len(p):,} filas)")
    print(f"Figuras generadas en: {os.path.abspath(SALIDA)}")
    for f in sorted(os.listdir(SALIDA)):
        print("  ", f)


if __name__ == "__main__":
    main()
