# ============================================================
# graficas_libertad_expresion.py
#
# Genera 6 gráficas separadas:
#   - 4 de líneas (una por variable legal)
#   - 2 de barras (asesinados y desaparecidos por año)
#
# Uso:
#   python graficas_libertad_expresion.py
#
# Requiere: pandas, matplotlib
# ============================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os

# ── Rutas ────────────────────────────────────────────────────
RUTA_CSV    = "datos/libertad_expresion.csv"
RUTA_SALIDA = "graficas"
os.makedirs(RUTA_SALIDA, exist_ok=True)

# ── Colores ───────────────────────────────────────────────────
COLOR_LINEA      = "#2C5F8A"
COLOR_ASESINADOS = "#B5322A"
COLOR_DESAPAREC  = "#D4872B"

# ── Tipografía ────────────────────────────────────────────────
FONT_TITULO = 13
FONT_EJE    = 10
FONT_NOTA   = 8   # tamaño del texto de la nota al pie

# ── Distancia de la nota al borde inferior del gráfico ───────
# Modifica este valor para subir (+) o bajar (-) la nota.
# -0.18 es el default; valores más negativos = más abajo.
NOTA_Y = -0.14   # <── AJUSTA AQUÍ si la nota se amontona

# ── Estilo global ─────────────────────────────────────────────
plt.rcParams.update({
    "font.family":         "sans-serif",
    "axes.spines.top":     False,
    "axes.spines.right":   False,
    "axes.facecolor":      "white",   # fondo del área de ploteo: blanco
    "figure.facecolor":    "white",   # fondo de la figura: blanco
})

# ── Cargar datos ──────────────────────────────────────────────
print("Leyendo datos...")
df = pd.read_csv(RUTA_CSV, encoding="utf-8")
df.columns = df.columns.str.strip()
print(f"  {len(df)} filas | años: {df['year'].min()}–{df['year'].max()}")

# ── Series legales ────────────────────────────────────────────
vars_legales = {
    "ley_transparencia":  "Ley de transparencia vigente",
    "difamacion_penal":   "Difamación como delito penal",
    "injurias_penal":     "Injurias como delito penal",
    #"ultrajes_autoridad": "Ultrajes a la autoridad como delito penal",
}

serie_legales = {}
for var, label in vars_legales.items():
    serie = (
        df.groupby("year")[var]
        .apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
        .reset_index()
    )
    serie.columns = ["year", "n_estados"]
    serie_legales[var] = (serie, label)

# ── Series de periodistas ─────────────────────────────────────
asesinados = (
    df.groupby("year")["num_periodistas_asesinados"]
    .apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
    .reset_index()
)
asesinados.columns = ["year", "total"]

desaparecidos = (
    df.groupby("year")["num_periodistas_desaparecidos"]
    .apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
    .reset_index()
)
desaparecidos.columns = ["year", "total"]

# ── Función de nota al pie ────────────────────────────────────
def agregar_nota(fig, ax, texto):
    """
    Coloca la nota debajo del eje x.
    Para ajustar la posición vertical: modifica NOTA_Y arriba.
    Para ajustar posición horizontal: cambia el primer valor de xy (0 = izquierda).
    """
    fig.text(
        0.1,                          # posición horizontal (0=izquierda, 1=derecha)
        ax.get_position().y0 + NOTA_Y, # posición vertical relativa a la figura
        texto,
        fontsize=FONT_NOTA,
        color="#555555",
        ha="left", va="top",
        transform=fig.transFigure
    )

# ═══════════════════════════════════════════════════════════════
# FIGURAS 1–4: una gráfica de líneas por variable legal
# ═══════════════════════════════════════════════════════════════
nombres_archivo = {
    "ley_transparencia":  "legal_ley_transparencia.png",
    "difamacion_penal":   "legal_difamacion_penal.png",
    "injurias_penal":     "legal_injurias_penal.png",
    #"ultrajes_autoridad": "legal_ultrajes_autoridad.png",
}

for var, (serie, label) in serie_legales.items():

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.subplots_adjust(bottom=0.22)  # espacio extra abajo para la nota

    ax.plot(
        serie["year"], serie["n_estados"],
        color=COLOR_LINEA, linewidth=2.2,
        marker="o", markersize=4,
        markerfacecolor="white",
        markeredgewidth=1.5,
        markeredgecolor=COLOR_LINEA
    )
    ax.fill_between(
        serie["year"], serie["n_estados"],
        alpha=0.10, color=COLOR_LINEA
    )
    ax.axhline(
        y=32, color="#AAAAAA", linewidth=0.8, linestyle=":",
        label="32 estados"
    )

    # Etiqueta del máximo
    max_row = serie.loc[serie["n_estados"].idxmax()]
    ax.annotate(
        f"{int(max_row['n_estados'])}",
        xy=(max_row["year"], max_row["n_estados"]),
        xytext=(6, 4), textcoords="offset points",
        fontsize=FONT_NOTA, color=COLOR_LINEA, fontweight="bold"
    )

    ax.set_title(label, fontsize=FONT_TITULO, fontweight="bold", pad=10)
    ax.set_xlabel("Año", fontsize=FONT_EJE)
    ax.set_ylabel("Número de estados", fontsize=FONT_EJE)
    ax.set_xlim(serie["year"].min() - 0.5, serie["year"].max() + 0.5)
    ax.set_ylim(0, 35)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(4))
    ax.tick_params(axis="x", rotation=45, labelsize=FONT_EJE - 1)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    agregar_nota(fig, ax, "Elaboración propia con base en códigos penales estatales y Orden Jurídico Nacional (2024).")

    ruta = os.path.join(RUTA_SALIDA, nombres_archivo[var])
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    print(f"✓ Guardada: {ruta}")
    plt.close()

# ═══════════════════════════════════════════════════════════════
# FIGURA 5 — Periodistas asesinados
# ═══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 5.5))
fig.subplots_adjust(bottom=0.22)

bars = ax.bar(
    asesinados["year"], asesinados["total"],
    color=COLOR_ASESINADOS, width=0.7, alpha=0.88,
    edgecolor="white", linewidth=0.5
)

for bar, val in zip(bars, asesinados["total"]):
    if val > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.15,
            str(int(val)),
            ha="center", va="bottom",
            fontsize=FONT_NOTA, color="#333333"
        )

ax.set_title(
    "Periodistas asesinados en México por año (2000–2024)",
    fontsize=FONT_TITULO + 1, fontweight="bold", pad=12
)
ax.set_xlabel("Año", fontsize=FONT_EJE)
ax.set_ylabel("Número de periodistas asesinados", fontsize=FONT_EJE)
ax.set_xlim(asesinados["year"].min() - 0.7, asesinados["year"].max() + 0.7)
ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
ax.tick_params(axis="x", rotation=45, labelsize=FONT_EJE - 1)
ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

agregar_nota(
    fig, ax,
    "Fuente: Artículo 19 Oficina para México y Centroamérica (2026). "
    "Solo casos en relación con labor informativa. Elaboración propia."
)

ruta = os.path.join(RUTA_SALIDA, "periodistas_asesinados.png")
fig.savefig(ruta, dpi=150, bbox_inches="tight")
print(f"✓ Guardada: {ruta}")
plt.close()

# ═══════════════════════════════════════════════════════════════
# FIGURA 6 — Periodistas desaparecidos
# ═══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 5.5))
fig.subplots_adjust(bottom=0.22)

bars = ax.bar(
    desaparecidos["year"], desaparecidos["total"],
    color=COLOR_DESAPAREC, width=0.7, alpha=0.88,
    edgecolor="white", linewidth=0.5
)

for bar, val in zip(bars, desaparecidos["total"]):
    if val > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            str(int(val)),
            ha="center", va="bottom",
            fontsize=FONT_NOTA, color="#333333"
        )

ax.set_title(
    "Periodistas desaparecidos en México por año (2003–2026)",
    fontsize=FONT_TITULO + 1, fontweight="bold", pad=12
)
ax.set_xlabel("Año", fontsize=FONT_EJE)
ax.set_ylabel("Número de periodistas desaparecidos", fontsize=FONT_EJE)
ax.set_xlim(desaparecidos["year"].min() - 0.7, desaparecidos["year"].max() + 0.7)
ax.xaxis.set_major_locator(ticker.MultipleLocator(2))
ax.tick_params(axis="x", rotation=45, labelsize=FONT_EJE - 1)
ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

agregar_nota(
    fig, ax,
    "Fuente: Artículo 19 Oficina para México y Centroamérica (2026). "
    "Solo casos en relación con labor informativa. Elaboración propia."
)

ruta = os.path.join(RUTA_SALIDA, "periodistas_desaparecidos.png")
fig.savefig(ruta, dpi=150, bbox_inches="tight")
print(f"✓ Guardada: {ruta}")
plt.close()

print("\nListo. 6 archivos en:", RUTA_SALIDA)