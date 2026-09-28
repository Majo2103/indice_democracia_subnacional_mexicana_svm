"""
analizar_panel.py
==================

Lee panel_libertad_asociacion.csv (generado por construir_panel.py) y produce
cuatro gráficas descriptivas a nivel NACIONAL (suma de las 32 entidades) y
tres mapas coropléticos por entidad:

  1. grafica_1_organizaciones.png
     Unidades económicas del sector 813: total, laborales/sindicales y civiles.
     Sólo hay dato en los 5 cortes censales (2003, 2008, 2013, 2018, 2023).

  2. grafica_2_emplazamientos.png
     Emplazamientos a huelga, 2000-2024.

  3. grafica_3_huelgas_estalladas.png
     Huelgas estalladas, 2000-2024. Van en un PNG aparte del anterior
     (nunca juntas en un mismo eje): la escala es dos órdenes de magnitud
     más chica y compartir eje las habría vuelto ilegibles. Marca 2014,
     2015 y 2018 como "sin dato": esos años no vienen en el archivo fuente
     de la STPS, no es que hayan sido cero.

  4. grafica_4_protestas_intervencion.png
     Gráfica de área: total de eventos de protesta vs. protestas con
     intervención del Estado (ACLED), 2018-2024. Dos series superpuestas
     desde cero (no apiladas): como con intervención <= total siempre, la
     serie de intervención queda "dentro" de la serie total y se ve el
     contraste directamente, sin necesidad de calcular un porcentaje.
     Lleva una nota pequeña y gris, alineada a la derecha, aclarando que
     ACLED sólo cubre esos años.

  5. mapa_1_protestas_totales.png
     Mapa de México, suma de eventos de protesta por entidad, 2018-2024.

  6. mapa_2_protestas_con_intervencion.png
     Mapa de México, suma de protestas con intervención del Estado por
     entidad, 2018-2024.

  7. mapa_3_pct_protestas_con_intervencion.png
     Mapa de México, % de los eventos de protesta de cada entidad que
     tuvieron intervención del Estado, 2018-2024 (protestas_con_intervencion_n
     / eventos_protesta_n * 100). Ninguna entidad tiene cero eventos en el
     periodo, así que el porcentaje está definido en las 32.

Los tres mapas usan sólo 2018-2024 porque es el único periodo con dato real
de ACLED (cobertura_eventos_protesta == "dato_real"); no se suma el resto
del panel porque ahí no hay evento que contar, sino ausencia de fuente.

CÓMO USARLO
-----------
1. Deja panel_libertad_asociacion.csv y mexico_estados.geojson en la misma
   carpeta que este script (o cambia PANEL_FILE / GEOJSON_FILE abajo).
2. Corre: python3 analizar_panel.py
   (los mapas requieren geopandas: pip install geopandas --break-system-packages)
3. Las siete imágenes se guardan en la misma carpeta, en PNG a 150 dpi.

FUENTE DEL GEOJSON
-------------------
mexico_estados.geojson viene de github.com/angelnmara/geojson
(mexicoHigh.json), una geometría comunitaria de los 32 estados. Es
suficiente para visualización a nivel estatal; no es el Marco
Geoestadístico oficial del INEGI, así que no debe usarse para análisis
espacial de precisión (áreas, distancias, colindancias).
"""

import unicodedata
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

PANEL_FILE = Path("datos/libertad_asociacion_panel.csv")
GEOJSON_FILE = Path("datos/mexico_estados.geojson")
OUTPUT_DIR = Path(".")
DPI = 150

# Paleta categórica de referencia (orden fijo, validado para no confundirse
# entre sí en daltonismo — nunca se reordena por serie)
AZUL = "#2a78d6"
NARANJA = "#eb6834"
AQUA = "#1baf7a"
ROJO = "#e34948"
MORADO = "#7c4dbd"
GRIS_AUSENCIA = "#c9c8c3"

# Rampas secuenciales para los mapas (un solo tono, claro -> oscuro),
# construidas a partir de esos mismos colores categóricos en vez de usar
# un colormap genérico, para que el lenguaje visual sea el mismo en todo
# el conjunto de gráficas.
CMAP_NARANJA = LinearSegmentedColormap.from_list("naranja_seq", ["#fdf1ea", NARANJA])
CMAP_AZUL = LinearSegmentedColormap.from_list("azul_seq", ["#eaf1fb", AZUL])
CMAP_MORADO = LinearSegmentedColormap.from_list("morado_seq", ["#f3ecfa", MORADO])

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e5e4e0",
    "grid.linewidth": 0.8,
    "axes.edgecolor": "#9a9990",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def cargar_panel():
    return pd.read_csv(PANEL_FILE)


def agregar_nacional(panel, columnas):
    """Suma a nivel nacional por año. min_count=1 asegura que un año sin
    NINGÚN dato real quede en NaN (no en 0) — así el hueco se ve en la
    gráfica en vez de leerse como 'no pasó nada'."""
    return panel.groupby("anio")[columnas].sum(min_count=1)


# ---------------------------------------------------------------------------
# Gráfica 1 — Organizaciones y asociaciones (Censos Económicos)
# ---------------------------------------------------------------------------

def graficar_organizaciones(panel):
    cols = [
        "asociaciones_organizaciones_n",
        "organizaciones_laborales_sindicales_n",
        "organizaciones_civiles_n",
    ]
    nat = agregar_nacional(panel, cols).dropna(how="all")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    series = [
        (cols[0], "Total sector 813 (todas las asociaciones y organizaciones)", AZUL),
        (cols[1], "Laborales y sindicales", NARANJA),
        (cols[2], "Civiles", AQUA),
    ]
    for col, etiqueta, color in series:
        ax.plot(
            nat.index, nat[col], marker="o", markersize=7,
            linewidth=2, color=color, label=etiqueta,
        )

    ax.set_title("Unidades económicas del sector 813, nacional", fontsize=14, fontweight="bold", loc="left")
    ax.set_xlabel("Año censal")
    ax.set_ylabel("Unidades económicas (conteo)")
    ax.set_xticks(nat.index)
    ax.legend(frameon=False, loc="upper left")
    fig.text(
        0.01, -0.02,
        "Cada punto es un corte del Censo Económico (2003, 2008, 2013, 2018, 2023).\n"
        "No hay dato entre cortes: la línea conecta observaciones reales, no interpola años intermedios.",
        fontsize=8.5, color="#52514e", ha="left",
    )
    fig.tight_layout()
    ruta = OUTPUT_DIR / "grafica_1_organizaciones.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


# ---------------------------------------------------------------------------
# Gráficas 2 y 3 — Huelgas: emplazamientos y estalladas, en PNGs separados
# (nunca en el mismo eje: la escala de una es dos órdenes de magnitud más
# grande que la otra, y compartir eje aplanaría la más chica hasta hacerla
# ilegible — por eso van en archivos distintos, no sólo en paneles distintos)
# ---------------------------------------------------------------------------

def graficar_emplazamientos(panel):
    nat = agregar_nacional(panel, ["emplazamientos_huelga_n"])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(nat.index, nat["emplazamientos_huelga_n"], marker="o", markersize=6,
            linewidth=2, color=AZUL)
    ax.set_title("Emplazamientos a huelga, nacional, 2000-2024", fontsize=14, fontweight="bold", loc="left")
    ax.set_xlabel("Año")
    ax.set_ylabel("Emplazamientos (conteo nacional)")
    fig.tight_layout()
    ruta = OUTPUT_DIR / "grafica_2_emplazamientos.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


def graficar_huelgas_estalladas(panel):
    nat = agregar_nacional(panel, ["huelgas_estalladas_n"])
    anios_sin_dato = nat.index[nat["huelgas_estalladas_n"].isna()].tolist()

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(nat.index, nat["huelgas_estalladas_n"], marker="o", markersize=6,
            linewidth=2, color=NARANJA)
    for anio in anios_sin_dato:
        ax.axvspan(anio - 0.5, anio + 0.5, color=GRIS_AUSENCIA, alpha=0.5,
                   label="Sin dato en el archivo fuente" if anio == anios_sin_dato[0] else None)
    ax.set_title("Huelgas estalladas, nacional, 2000-2024", fontsize=14, fontweight="bold", loc="left")
    ax.set_xlabel("Año")
    ax.set_ylabel("Huelgas estalladas (conteo nacional)")
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.text(
        0.01, -0.02,
        f"Sin dato en {', '.join(str(a) for a in anios_sin_dato)}: el archivo fuente de la STPS "
        "no incluye esos años para ninguna entidad. No se interpola ni se asume cero.",
        fontsize=8.5, color="#52514e", ha="left",
    )
    fig.tight_layout()
    ruta = OUTPUT_DIR / "grafica_3_huelgas_estalladas.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


# ---------------------------------------------------------------------------
# Gráfica 4 — Protestas totales vs. con intervención del Estado (ACLED)
# Dos áreas superpuestas desde cero, NO apiladas: como "con intervención"
# es siempre un subconjunto de "total", la serie de arriba (total) se ve
# como un contorno alrededor de la serie de abajo (con intervención), en
# vez de sumarse una encima de la otra.
# ---------------------------------------------------------------------------

def graficar_protestas(panel):
    nat = agregar_nacional(panel, ["eventos_protesta_n", "protestas_con_intervencion_n"]).dropna(how="all")

    fig, ax = plt.subplots(figsize=(9, 5.5))

    # Total de eventos de protesta: se dibuja primero, al fondo.
    ax.fill_between(nat.index, nat["eventos_protesta_n"], color=NARANJA, alpha=0.55, zorder=1,
                     label="Total de eventos de protesta")
    ax.plot(nat.index, nat["eventos_protesta_n"], linewidth=1.5, color=NARANJA, zorder=2)

    # Con intervención del Estado: subconjunto del total, se dibuja encima.
    ax.fill_between(nat.index, nat["protestas_con_intervencion_n"], color=AZUL, alpha=0.85, zorder=3,
                     label="Con intervención del Estado")
    ax.plot(nat.index, nat["protestas_con_intervencion_n"], linewidth=1.5, color=AZUL, zorder=4)

    ax.set_ylim(bottom=0)
    ax.set_xticks(nat.index)

    ax.set_title(
        "Protestas: total vs. con intervención del Estado, nacional, 2018-2024",
        fontsize=13, fontweight="bold", loc="left",
    )
    ax.set_xlabel("Año")
    ax.set_ylabel("Eventos de protesta (conteo nacional)")
    ax.legend(frameon=False, loc="upper left")

    # nota pequeña, gris, alineada a la derecha
    ax.text(
        0.99, 0.97,
        "ACLED sólo cubre 2018-2024;\nno hay dato para 2000-2017.",
        transform=ax.transAxes, fontsize=8, color="#8a8980",
        ha="right", va="top",
    )

    fig.tight_layout()
    ruta = OUTPUT_DIR / "grafica_4_protestas_intervencion.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


# ---------------------------------------------------------------------------
# Mapas 1-3 — Protestas por entidad (coropléticos), 2018-2024
# ---------------------------------------------------------------------------

def _quitar_acentos(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def agregar_por_entidad_protestas(panel):
    """Suma 2018-2024 por entidad, sólo donde hay dato real de ACLED, más
    el % de esas protestas que tuvieron intervención."""
    real = panel[panel["cobertura_eventos_protesta"] == "dato_real"]
    agregado = real.groupby("entidad", as_index=False)[
        ["eventos_protesta_n", "protestas_con_intervencion_n"]
    ].sum()
    agregado["pct_protestas_con_intervencion"] = (
        agregado["protestas_con_intervencion_n"] / agregado["eventos_protesta_n"] * 100
    )
    agregado["clave_normalizada"] = agregado["entidad"].apply(
        lambda s: _quitar_acentos(s).strip().lower()
    )
    return agregado


def cargar_geometrias_entidades():
    geo = gpd.read_file(GEOJSON_FILE)
    geo["clave_normalizada"] = geo["name"].apply(
        lambda s: _quitar_acentos(s).strip().lower()
    )
    return geo


def unir_protestas_y_geometria(panel):
    datos = agregar_por_entidad_protestas(panel)
    geo = cargar_geometrias_entidades()
    unido = geo.merge(datos, on="clave_normalizada", how="left", validate="one_to_one")

    faltantes = unido[unido["eventos_protesta_n"].isna()]["name"].tolist()
    if faltantes:
        print(
            "AVISO: no se encontró dato de protestas para estas entidades "
            f"del geojson (revisar nombres): {faltantes}"
        )
    return unido


def _mapa_base(ax):
    ax.set_axis_off()
    ax.set_aspect("equal")


def _nota_cobertura_mapa(fig):
    fig.text(
        0.02, 0.03,
        "Fuente: ACLED. Suma/porcentaje sobre 2018-2024 (único periodo con "
        "cobertura); no incluye 2000-2017.",
        fontsize=8, color="#8a8980", ha="left",
    )


def graficar_mapa_protestas_totales(unido):
    fig, ax = plt.subplots(figsize=(8, 6.5))
    unido.plot(
        column="eventos_protesta_n",
        cmap=CMAP_NARANJA,
        linewidth=0.5,
        edgecolor="white",
        legend=True,
        legend_kwds={"label": "Eventos de protesta (suma 2018-2024)", "shrink": 0.6},
        missing_kwds={"color": "#e5e4e0", "label": "Sin dato"},
        ax=ax,
    )
    _mapa_base(ax)
    ax.set_title(
        "Total de eventos de protesta por entidad, 2018-2024",
        fontsize=14, fontweight="bold", loc="left",
    )
    _nota_cobertura_mapa(fig)
    fig.tight_layout()
    ruta = OUTPUT_DIR / "mapa_1_protestas_totales.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


def graficar_mapa_protestas_con_intervencion(unido):
    fig, ax = plt.subplots(figsize=(8, 6.5))
    unido.plot(
        column="protestas_con_intervencion_n",
        cmap=CMAP_AZUL,
        linewidth=0.5,
        edgecolor="white",
        legend=True,
        legend_kwds={"label": "Protestas con intervención (suma 2018-2024)", "shrink": 0.6},
        missing_kwds={"color": "#e5e4e0", "label": "Sin dato"},
        ax=ax,
    )
    _mapa_base(ax)
    ax.set_title(
        "Protestas con intervención del Estado por entidad, 2018-2024",
        fontsize=14, fontweight="bold", loc="left",
    )
    _nota_cobertura_mapa(fig)
    fig.tight_layout()
    ruta = OUTPUT_DIR / "mapa_2_protestas_con_intervencion.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


def graficar_mapa_pct_intervencion(unido):
    fig, ax = plt.subplots(figsize=(8, 6.5))
    unido.plot(
        column="pct_protestas_con_intervencion",
        cmap=CMAP_MORADO,
        linewidth=0.5,
        edgecolor="white",
        legend=True,
        legend_kwds={"label": "% de protestas con intervención (2018-2024)", "shrink": 0.6},
        missing_kwds={"color": "#e5e4e0", "label": "Sin dato"},
        ax=ax,
    )
    _mapa_base(ax)
    ax.set_title(
        "% de protestas con intervención del Estado por entidad, 2018-2024",
        fontsize=14, fontweight="bold", loc="left",
    )
    _nota_cobertura_mapa(fig)
    fig.tight_layout()
    ruta = OUTPUT_DIR / "mapa_3_pct_protestas_con_intervencion.png"
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardada: {ruta}")


if __name__ == "__main__":
    panel = cargar_panel()
    graficar_organizaciones(panel)
    graficar_emplazamientos(panel)
    graficar_huelgas_estalladas(panel)
    graficar_protestas(panel)

    unido = unir_protestas_y_geometria(panel)
    graficar_mapa_protestas_totales(unido)
    graficar_mapa_protestas_con_intervencion(unido)
    graficar_mapa_pct_intervencion(unido)
