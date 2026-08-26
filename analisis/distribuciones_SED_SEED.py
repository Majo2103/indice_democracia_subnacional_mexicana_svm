# %% [Configuración] — ejecutar primero
# Una gráfica por celda (separadas con "# %%"). Edita cada bloque libremente.
#
# Nota: las variables ELECTORALES (SEED) vienen forward-filled en el panel
# estado-año. Para no contar cada elección varias veces se grafican con UNA
# observación por elección (SEED_EVENTS_ONLY = True). Las variables ANUALES
# del ejecutivo (SED) van sobre el panel completo.

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CSV_PATH = "datos/panel_SED_SEED.csv"   
SEED_EVENTS_ONLY = True           # True = una obs. por elección; False = panel completo

df = pd.read_csv(CSV_PATH)

# Variables electorales sujetas a la deduplicación por elección
SEED_VARS = [
    "perc_voter_sub_exe", "perc_valid_votes_sub_exe", "perc_invalid_votes_sub_exe",
    "perc_votes_winner_candidate_sub_exe", "perc_second_place_sub_exe",
    "margin_victory_sub_exe", "num_parties_election_contest_sub_exe",
    "snap_election_sub_exe", "enp_sub_exe",
]

# Una fila por elección: conserva los años en que el bloque SEED cambia
# respecto al año previo dentro de cada estado (deshace el forward-fill).
_d = df.sort_values(["state_name", "year"]).copy()
_prev = _d.groupby("state_name")[SEED_VARS].shift()
df_events = _d[(_d[SEED_VARS] != _prev).any(axis=1)]

def pick(var):
    """Devuelve (serie_sin_NA, alcance) usando la fuente correcta."""
    if var in SEED_VARS and SEED_EVENTS_ONLY:
        return df_events[var].dropna(), "por elección"
    return df[var].dropna(), "panel estado-año"


# %% Participación (%)
var = "perc_voter_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Participación (%)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Participación (%)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Votos válidos (%)
var = "perc_valid_votes_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Votos válidos (%)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Votos válidos (%)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Votos inválidos (%)
var = "perc_invalid_votes_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Votos inválidos (%)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Votos inválidos (%)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Votos del ganador (%)
var = "perc_votes_winner_candidate_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Votos del ganador (%)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Votos del ganador (%)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Votos del 2.º lugar (%)
var = "perc_second_place_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Votos del 2.º lugar (%)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Votos del 2.º lugar (%)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Margen de victoria (%)
var = "margin_victory_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Margen de victoria (%)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Margen de victoria (%)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Número efectivo de partidos (ENP)
var = "enp_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Número efectivo de partidos (ENP)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Número efectivo de partidos (ENP)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Partidos en competencia (conteo)
var = "num_parties_election_contest_sub_exe"
s, scope = pick(var)
counts = s.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(counts.index, counts.values, color="grey", edgecolor="white", width=0.8)
ax.set_xlabel("Partidos en competencia"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Partidos en competencia  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Elección anticipada (0/1)
var = "snap_election_sub_exe"
s, scope = pick(var)
counts = s.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(counts.index.astype(str), counts.values, color="#4C72B0", edgecolor="white")
ax.set_ylabel("Frecuencia")
ax.set_title(f"Elección anticipada  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()

# %% Alternancia por año (número de estados con alternancia en la elección)
var = "turnover_head_sub_exe"
d = df_events.dropna(subset=[var]).copy()          # una fila por elección
d = d[(d["year"] >= 2000) & (d["year"] <= 2024)]   # ventana de análisis

by_year = d.groupby("year")[var].sum()             # estados con alternancia por año
by_year = by_year.reindex(range(2000, 2025), fill_value=0)  # años sin alternancia = 0

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(by_year.index, by_year.values, marker="o", color="#4C72B0")
ax.set_xlabel("Año"); ax.set_ylabel("Estados con alternancia")
ax.set_title("Alternancia en la titularidad del ejecutivo por año")
ax.set_xticks(range(2000, 2025, 2))
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.3)
plt.show()


# %% Años acumulados del gobernador (conteo)
var = "cumulative_years_in_power_sub_exe"
s, scope = pick(var)
counts = s.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(counts.index, counts.values, color="grey", edgecolor="white", width=0.8)
ax.set_xlabel("Años acumulados (gobernador)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Años acumulados (gobernador)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Años acumulados del partido — conteo por valor entero
var = "cumulative_years_in_power_party_sub_exe"
s, scope = pick(var)

counts = s.value_counts().sort_index()   # una barra por año entero

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(counts.index, counts.values, width=0.9, color="#4C72B0", edgecolor="white")
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Años acumulados (partido)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Años acumulados (partido)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Años acumulados del partido, coloreado por partido
# %% Años acumulados del partido — conteo entero, apilado por partido
var = "cumulative_years_in_power_party_sub_exe"
pcol = "head_party_sub_exe"

d = df.dropna(subset=[var, pcol]).copy()          # panel estado-año
scope = "panel estado-año"

short = {
    "PARTIDO REVOLUCIONARIO INSTITUCIONAL": "PRI",
    "PARTIDO ACCIÓN NACIONAL": "PAN",
    "PARTIDO DE LA REVOLUCIÓN DEMOCRÁTICA": "PRD",
    "MOVIMIENTO DE REGENERACIÓN NACIONAL": "Morena",
    "MOVIMIENTO CIUDADANO": "MC",
    "PARTIDO VERDE ECOLOGISTA DE MÉXICO": "PVEM",
    "PARTIDO ENCUENTRO SOCIAL": "PES",
    "PARTIDO INDEPENDIENTE": "Indep.",
}
colors = {
    "PRI": "#009150", "PAN": "#05338D", "PRD": "#FFD700",
    "Morena": "#B5261E", "Otros": "#BBBBBB",
}
d["party"] = d[pcol].map(short)

# Agrupar partidos pequeños en "Otros" (conserva PRI/PAN/PRD/Morena)
principales = ["PRI", "PAN", "PRD", "Morena"]
d["party"] = d["party"].where(d["party"].isin(principales), "Otros")

# Conteo por año entero (índice) x partido (columnas)
orden = [p for p in principales + ["Otros"] if p in d["party"].unique()]
tab = (d.groupby([var, "party"]).size()
         .unstack("party", fill_value=0)
         .reindex(columns=orden, fill_value=0))
tab = tab.reindex(range(int(d[var].min()), int(d[var].max()) + 1), fill_value=0)

fig, ax = plt.subplots(figsize=(7, 4))
bottom = np.zeros(len(tab))
for p in orden:
    ax.bar(tab.index, tab[p], bottom=bottom, width=0.9,
           color=colors[p], edgecolor="white", linewidth=0.3, label=p)
    bottom += tab[p].values

ax.axvline(d[var].mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={d[var].mean():.1f}")
ax.axvline(d[var].median(), color="#555555", lw=1.4, ls=":",  label=f"mediana={d[var].median():.1f}")
ax.legend(frameon=False, fontsize=8)
ax.set_xlabel("Años acumulados (partido)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Años acumulados (partido)  (n={len(d)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()


# %% Duración del mandato (años)  — ojo: tiene NA
var = "term_length_in_years_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Duración del mandato (años)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Duración del mandato (años)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()




# %% Reelección consecutiva (0/1) — constante = 0 para la gubernatura
var = "consecutive_reelection_sub_exe"
s, scope = pick(var)
counts = s.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(counts.index.astype(str), counts.values, color="#4C72B0", edgecolor="white")
if s.nunique() <= 1:
    ax.text(0.5, 0.85, "constante", transform=ax.transAxes,
            ha="center", va="top", color="#B0413E")
ax.set_ylabel("Frecuencia")
ax.set_title(f"Reelección consecutiva  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
plt.show()
