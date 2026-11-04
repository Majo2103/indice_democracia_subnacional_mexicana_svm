"""Gráficas nacionales del panel "Políticas que dependen del voto" (garantía 8 de Dahl).

Uso:
    python3 analisis_PDV.py panel_politicas_dependen_voto_2000_2024.csv [carpeta_salida]

Lee el panel (32 entidades x 2000-2024) y guarda en la carpeta de salida
(por defecto: graficas_PDV/):

    g1_ley_participacion.png      Estados con ley de participación ciudadana vigente
    g2_ley_vs_comite.png          Estados con ley del sistema anticorrupción vs. con Comité Coordinador
    g3_rezago_ley_comite.png      Años entre la ley y la instalación del Comité Coordinador
    g4_auditorias.png             Auditorías de la ASF al gasto federalizado, por fuente
    g5_monto_observado.png        Monto observado nacional (pesos de 2024)
    g6_proporcion_observada.png   Monto observado / muestra auditada (mediana y rango intercuartil)
    g6b_proporcion_media.png      Monto observado / muestra auditada (promedio simple de los estados)
    g7_monto_por_habitante.png    Monto observado por habitante (pesos de 2024)
    g7b_extremos_por_habitante.png  Estado con el monto por habitante más alto y más bajo, cada año
    resumen_PDV.txt               Números que respaldan la descripción de cada gráfica

Celdas vacías (NA): en las variables 1/0 se grafican como una banda entre el
mínimo (todas las vacías valen 0) y el máximo (todas valen 1).

Las gráficas no llevan título ni fuente dentro de la imagen: van como pie de
figura en el documento. Están pensadas para leerse también en blanco y negro.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# ---------------------------------------------------------------- estilo
NEGRO, GRIS_OSCURO, GRIS, GRIS_CLARO, BANDA = "#1a1a1a", "#555555", "#8c8c8c", "#c8c8c8", "#d9d9d9"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": GRIS_OSCURO, "axes.labelcolor": NEGRO,
    "xtick.color": GRIS_OSCURO, "ytick.color": GRIS_OSCURO,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e6e6e6", "grid.linewidth": 0.6,
    "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
    "lines.linewidth": 2, "lines.markersize": 5,
})
TAM = (6.5, 3.8)  # pulgadas: cabe en una página carta con márgenes de 2.5 cm


def miles(x, _=None):
    return f"{x:,.0f}"


def leyenda_abajo(ax, ncol=1):
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=ncol, fontsize=9)


def guarda(fig, carpeta, nombre):
    ruta = carpeta / nombre
    fig.savefig(ruta)
    plt.close(fig)
    return ruta


def conteo_con_banda(p, col):
    """Por año: estados con 1 (mínimo, vacías = 0) y máximo posible (vacías = 1)."""
    g = p.groupby("anio")[col]
    minimo = g.apply(lambda s: (s == 1).sum())
    maximo = g.apply(lambda s: ((s == 1) | s.isna()).sum())
    return minimo, maximo


# ---------------------------------------------------------------- gráficas
def g1_ley_participacion(p, carpeta, res):
    mn, mx = conteo_con_banda(p, "ley_participacion_ciudadana")
    fig, ax = plt.subplots(figsize=TAM)
    hay_banda = (mx != mn).any()   # solo si quedan celdas vacías
    if hay_banda:
        ax.fill_between(mn.index, mn, mx, color=BANDA, step="mid", label="Rango posible")
    ax.step(mn.index, mn, where="mid", color=NEGRO, label="Estados con ley vigente")
    ax.set_ylim(0, 32)
    ax.set_xlim(1999.5, 2024.5)
    ax.set_ylabel("Número de estados")
    ax.set_xticks(range(2000, 2025, 2))
    # Salidas: estados que pasan de 1 a 0
    salidas = []
    for cve, s in p.sort_values("anio").groupby("cve_ent"):
        v = s.set_index("anio")["ley_participacion_ciudadana"]
        for a in v.index[1:]:
            if v.get(a - 1) == 1 and v.get(a) == 0:
                salidas.append((s.entidad.iloc[0], a))
    for n, (ent, a) in enumerate(sorted(salidas, key=lambda t: t[1])):
        ax.annotate(f"{ent} pierde su ley ({a})", xy=(a, mn[a] - 0.3), xytext=(a + 0.3, 6 + 5 * n),
                    ha="center", fontsize=8.5, color=GRIS_OSCURO,
                    arrowprops=dict(arrowstyle="->", color=GRIS, lw=0.8))
    if hay_banda:
        ax.legend(loc="upper left")
    res.append("G1. Estados con ley de participación ciudadana vigente (mín.–máx.)")
    for a in [2000, 2005, 2010, 2015, 2020, 2024]:
        res.append(f"  {a}: {mn[a]}" + (f"–{mx[a]}" if mx[a] != mn[a] else ""))
    res.append("  Salidas (1 -> 0): " + "; ".join(f"{e} {a}" for e, a in salidas))
    sin_ley = p[(p.anio == 2024) & (p.ley_participacion_ciudadana == 0)].entidad.tolist()
    res.append(f"  Sin ley en 2024: {', '.join(sin_ley)}")
    return guarda(fig, carpeta, "g1_ley_participacion.png")


def g2_ley_vs_comite(p, carpeta, res):
    q = p[p.anio >= 2014]
    ley = q.groupby("anio")["ley_sistema_anticorrupcion"].apply(lambda s: (s == 1).sum())
    mn, mx = conteo_con_banda(q, "sistema_anticorrupcion")
    fig, ax = plt.subplots(figsize=TAM)
    if (mx != mn).any():   # solo si quedan celdas vacías
        ax.fill_between(mn.index, mn, mx, color=BANDA, label="Rango posible del Comité")
    ax.plot(ley.index, ley, color=GRIS, ls="--", marker="s", label="Con ley del sistema anticorrupción")
    ax.plot(mn.index, mn, color=NEGRO, marker="o", label="Con Comité Coordinador instalado")
    ax.set_ylim(0, 33)
    ax.set_xticks(range(2014, 2025))
    ax.set_ylabel("Número de estados")
    leyenda_abajo(ax)
    res.append("G2. Estados con ley del sistema anticorrupción / con Comité Coordinador (mín.–máx.)")
    for a in range(2016, 2025):
        res.append(f"  {a}: ley {ley[a]}; comité {mn[a]}" + (f"–{mx[a]}" if mx[a] != mn[a] else ""))
    return guarda(fig, carpeta, "g2_ley_vs_comite.png")


def g3_rezago(p, carpeta, res):
    filas = []
    for cve, s in p.sort_values("anio").groupby("cve_ent"):
        ley = s[s.ley_sistema_anticorrupcion == 1].anio.min()
        primero = s[s.sistema_anticorrupcion == 1].anio.min()          # primer año con 1
        vacios = s[s.sistema_anticorrupcion.isna()].anio
        temprano = vacios.min() if len(vacios) else primero              # instalación más temprana posible
        filas.append({"entidad": s.entidad.iloc[0], "ley": ley,
                      "rezago_min": temprano - ley, "rezago_max": primero - ley,
                      "conocido": len(vacios) == 0})
    r = pd.DataFrame(filas)
    k = np.arange(0, r.rezago_max.max() + 1)
    conocidos = r[r.conocido].rezago_max.value_counts().reindex(k, fill_value=0)
    inciertos = r[~r.conocido]
    extra = pd.Series([((inciertos.rezago_min <= x) & (inciertos.rezago_max >= x)).sum() for x in k], index=k)
    fig, ax = plt.subplots(figsize=TAM)
    ax.bar(k, conocidos, width=0.6, color=GRIS_OSCURO, label="Estados con fecha confirmada")
    hay = extra > 0
    ax.vlines(k[hay], conocidos[hay], conocidos[hay] + extra[hay], color=NEGRO, lw=1.2,
              label="Máximo posible si se suman los estados sin fecha")
    ax.hlines(conocidos[hay] + extra[hay], k[hay] - 0.12, k[hay] + 0.12, color=NEGRO, lw=1.2)
    for x, v in zip(k, conocidos):
        if v >= 2:
            ax.text(x, v - 0.4, str(v), ha="center", va="top", fontsize=9.5, color="white", weight="bold")
        elif v:
            ax.text(x + 0.33, v, str(v), ha="left", va="center", fontsize=9.5, color=NEGRO)
    ax.set_xticks(k)
    ax.set_xticklabels([f"{x}" for x in k])
    ax.set_xlabel("Años entre la ley y la instalación del Comité Coordinador")
    ax.set_ylabel("Número de estados")
    ax.set_ylim(0, conocidos.max() + extra.max() + 1)
    ax.yaxis.get_major_locator().set_params(integer=True)
    leyenda_abajo(ax)
    res.append("G3. Rezago ley -> Comité Coordinador (estados con fecha confirmada)")
    for x in k:
        res.append(f"  {x} años: {conocidos[x]}" + (f" (hasta {conocidos[x] + extra[x]} con los estados sin fecha)" if extra[x] else ""))
    for _, f in r[r.conocido & (r.rezago_max >= 3)].iterrows():
        res.append(f"  Rezago largo: {f.entidad} ({f.rezago_max} años)")
    for _, f in inciertos.iterrows():
        res.append(f"  Sin fecha: {f.entidad}, rezago entre {f.rezago_min} y {f.rezago_max} años")
    return guarda(fig, carpeta, "g3_rezago_ley_comite.png")


def g4_auditorias(p, carpeta, res):
    t = p.groupby(["anio", "fuente_auditorias"])["auditorias_asf_n"].sum().unstack(fill_value=0)
    estilos = {  # (etiqueta, color, trama)
        "Recurrencia": ("2000–2006: solo directas de la ASF (Ramo 33 y Seguro Popular)", "white", "////"),
        "Tomo Ejecutivo": ("2007–2011: directas + coordinadas (Tomo Ejecutivo)", GRIS, ""),
        "Matriz de Datos": ("2012–2024: directas + coordinadas (Matriz de Datos Básicos)", GRIS_OSCURO, ""),
    }
    fig, ax = plt.subplots(figsize=TAM)
    for clave, (etq, color, trama) in estilos.items():
        cols = [c for c in t.columns if c.startswith(clave)]
        if not cols:
            continue
        v = t[cols].sum(axis=1)
        v = v[v > 0]
        ax.bar(v.index, v, width=0.75, color=color, edgecolor=NEGRO if trama else color,
               linewidth=0.6, hatch=trama, label=etq)
    total = t.sum(axis=1)
    ax.axvline(2006.5, color=GRIS, ls=":", lw=1)
    ax.text(2006.3, total.max() * 0.45, "cambio de fuente\ny de cobertura", ha="right", va="bottom",
            fontsize=8.5, color=GRIS_OSCURO)
    ax.yaxis.set_major_formatter(miles)
    ax.set_xticks(range(2000, 2025, 2))
    ax.set_xlabel("Año de la cuenta pública fiscalizada")
    ax.set_ylabel("Auditorías")
    leyenda_abajo(ax)
    res.append("G4. Auditorías de la ASF al gasto federalizado (suma de los 32 estados)")
    for a in [2000, 2006, 2007, 2011, 2012, 2016, 2018, 2019, 2021, 2023, 2024]:
        res.append(f"  {a}: {total[a]:,.0f}")
    res.append(f"  Máximo: {total.idxmax()} ({total.max():,.0f})")
    pc = (p.groupby("anio").auditorias_asf_n.sum() / p.groupby("anio").poblacion.sum() * 1e6)
    res.append(f"  Por millón de habitantes: 2012 {pc[2012]:.1f}; 2024 {pc[2024]:.1f}")
    return guarda(fig, carpeta, "g4_auditorias.png")


def g5_monto(p, carpeta, res):
    q = p[p.anio >= 2012]
    vacios = q.monto_observado_mdp_2024.isna().sum()
    m = q.groupby("anio").monto_observado_mdp_2024.sum() / 1000  # miles de millones
    fig, ax = plt.subplots(figsize=TAM)
    ax.bar(m.index, m, width=0.7, color=GRIS_OSCURO)
    for a in [m.index.min(), m.idxmax(), m.index.max()]:
        ax.text(a, m[a] + m.max() * 0.015, f"{m[a]:,.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(m.index)
    ax.tick_params(axis="x", labelsize=9)
    ax.set_xlabel("Año de la cuenta pública fiscalizada")
    ax.set_ylabel("Miles de millones de pesos de 2024")
    res.append(f"G5. Monto observado nacional, miles de millones de pesos de 2024 (celdas vacías 2012–2024: {vacios})")
    for a, v in m.items():
        res.append(f"  {a}: {v:,.1f}")
    res.append(f"  Variación 2012 -> 2024: {(m[2024] / m[2012] - 1) * 100:+.1f}%")
    res.append(f"  Promedio 2012–2024 sin 2018: {m.drop(2018).mean():,.1f}")
    return guarda(fig, carpeta, "g5_monto_observado.png")


def techo_proporcion(p):
    """Mismo eje vertical para G6 y G6b, para que se puedan comparar."""
    g = p[p.anio >= 2012].groupby("anio").proporcion_observada_muestra
    return max(g.quantile(0.75).max(), g.mean().max()) * 100 * 1.08


def g6_proporcion(p, carpeta, res):
    q = p[p.anio >= 2012]
    g = q.groupby("anio").proporcion_observada_muestra
    med, p25, p75 = g.median() * 100, g.quantile(0.25) * 100, g.quantile(0.75) * 100
    fig, ax = plt.subplots(figsize=TAM)
    ax.fill_between(med.index, p25, p75, color=BANDA, label="Rango intercuartil (50% central de los estados)")
    ax.plot(med.index, med, color=NEGRO, marker="o", label="Mediana de los estados")
    ax.set_xticks(med.index)
    ax.tick_params(axis="x", labelsize=9)
    ax.set_ylim(0, techo_proporcion(p))
    ax.set_xlabel("Año de la cuenta pública fiscalizada")
    ax.set_ylabel("% de la muestra auditada")
    leyenda_abajo(ax, ncol=2)
    res.append("G6. Monto observado / muestra auditada (%): mediana [p25–p75]")
    for a in med.index:
        res.append(f"  {a}: {med[a]:.1f} [{p25[a]:.1f}–{p75[a]:.1f}]")
    return guarda(fig, carpeta, "g6_proporcion_observada.png")


def g6b_proporcion_media(p, carpeta, res):
    q = p[p.anio >= 2012].copy()
    g = q.groupby("anio")
    media = g.proporcion_observada_muestra.mean() * 100
    mediana = g.proporcion_observada_muestra.median() * 100
    # Proporción nacional (ponderada): suma de montos / suma de muestras.
    # La muestra se recupera del panel: muestra = monto observado / proporción.
    q["muestra_2024"] = q.monto_observado_mdp_2024 / q.proporcion_observada_muestra
    nacional = g.monto_observado_mdp_2024.sum() / q.groupby("anio").muestra_2024.sum() * 100
    fig, ax = plt.subplots(figsize=TAM)
    ax.plot(media.index, media, color=NEGRO, marker="o")
    for a in [media.index.min(), media.idxmax(), media.index.max()]:
        ax.annotate(f"{media[a]:.1f}%", (a, media[a]), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=9)
    ax.set_xticks(media.index)
    ax.tick_params(axis="x", labelsize=9)
    ax.set_ylim(0, techo_proporcion(p))
    ax.set_xlabel("Año de la cuenta pública fiscalizada")
    ax.set_ylabel("% de la muestra auditada (promedio de los estados)")
    res.append("G6b. Monto observado / muestra auditada (%): promedio simple de los estados")
    res.append("     (para comparar: mediana de los estados y proporción nacional = suma montos / suma muestras)")
    for a in media.index:
        d = q[q.anio == a]
        top = d.loc[d.proporcion_observada_muestra.idxmax()]
        res.append(f"  {a}: promedio {media[a]:.1f} | mediana {mediana[a]:.1f} | nacional {nacional[a]:.1f}"
                   f" | máximo {top.proporcion_observada_muestra * 100:.1f} ({top.entidad})")
    return guarda(fig, carpeta, "g6b_proporcion_media.png")


def g7_por_habitante(p, carpeta, res):
    q = p[p.anio >= 2012].groupby("anio")
    pc = q.monto_observado_mdp_2024.sum() * 1e6 / q.poblacion.sum()
    fig, ax = plt.subplots(figsize=TAM)
    ax.plot(pc.index, pc, color=NEGRO, marker="o")
    for a in [pc.index.min(), pc.idxmax(), pc.index.max()]:
        ax.annotate(f"{pc[a]:,.0f}", (a, pc[a]), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=9)
    ax.set_xticks(pc.index)
    ax.tick_params(axis="x", labelsize=9)
    ax.set_ylim(0, pc.max() * 1.15)
    ax.yaxis.set_major_formatter(miles)
    ax.set_xlabel("Año de la cuenta pública fiscalizada")
    ax.set_ylabel("Pesos de 2024 por habitante")
    res.append("G7. Monto observado por habitante, nacional (pesos de 2024)")
    for a, v in pc.items():
        res.append(f"  {a}: {v:,.0f}")
    e = p[p.anio == 2024].set_index("entidad").monto_observado_pc_2024
    res.append(f"  2024, por estado: máximo {e.idxmax()} ({e.max():,.0f}); mínimo {e.idxmin()} ({e.min():,.0f})")
    return guarda(fig, carpeta, "g7_monto_por_habitante.png")


def g7b_extremos(p, carpeta, res):
    q = p[p.anio >= 2012]
    filas = []
    for a, d in q.groupby("anio"):
        v = d.set_index("entidad").monto_observado_pc_2024
        filas.append((a, v.idxmin(), v.min(), v.idxmax(), v.max()))
    t = pd.DataFrame(filas, columns=["anio", "ent_min", "min", "ent_max", "max"]).set_index("anio")
    x = np.arange(len(t))
    w = 0.38
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    # A color (paleta categórica validada para daltonismo: azul y naranja)
    AZUL, NARANJA = "#2a78d6", "#eb6834"
    ax.bar(x - w / 2, t["max"], width=w, color=AZUL, label="Estado con el monto más alto")
    ax.bar(x + w / 2, t["min"], width=w, color=NARANJA, edgecolor=NARANJA, linewidth=0.8,
           label="Estado con el monto más bajo")
    tope = t["max"].max()
    for i, (a, f) in enumerate(t.iterrows()):
        for dx, ent, val in [(-w / 2, f.ent_max, f["max"]), (w / 2, f.ent_min, f["min"])]:
            ax.text(i + dx, val + tope * 0.015, f"{ent} ({val:,.1f})" if val < 1 else f"{ent} ({val:,.0f})", rotation=90, ha="center",
                    va="bottom", fontsize=7, color=NEGRO)
    ax.set_xticks(x)
    ax.set_xticklabels(t.index, fontsize=9)
    ax.set_ylim(0, tope * 1.32)
    ax.yaxis.set_major_formatter(miles)
    ax.set_xlabel("Año de la cuenta pública fiscalizada")
    ax.set_ylabel("Pesos de 2024 por habitante")
    leyenda_abajo(ax, ncol=2)
    res.append("G7b. Monto observado por habitante: estado más alto y más bajo de cada año (pesos de 2024)")
    for a, f in t.iterrows():
        res.append(f"  {a}: máx. {f.ent_max} {f['max']:,.0f} | mín. {f.ent_min} {f['min']:,.1f}"
                   f" | diferencia {f['max'] - f['min']:,.0f}")
    return guarda(fig, carpeta, "g7b_extremos_por_habitante.png")


# ---------------------------------------------------------------- principal
def main(ruta_csv, carpeta):
    p = pd.read_csv(ruta_csv)
    assert len(p) == 32 * 25 and not p.duplicated(["cve_ent", "anio"]).any(), "El panel no es 32 x 25"
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    res = [f"Resumen de {Path(ruta_csv).name}", ""]
    for f in (g1_ley_participacion, g2_ley_vs_comite, g3_rezago, g4_auditorias,
              g5_monto, g6_proporcion, g6b_proporcion_media, g7_por_habitante, g7b_extremos):
        ruta = f(p, carpeta, res)
        res.append(f"  -> {ruta.name}\n")
    texto = "\n".join(res)
    (carpeta / "resumen_PDV.txt").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "graficas_PDV")