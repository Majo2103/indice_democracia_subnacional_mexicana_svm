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


# %% Alternancia / turnover (0/1)
var = "turnover_head_sub_exe"
s, scope = pick(var)
counts = s.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(counts.index.astype(str), counts.values, color="#4C72B0", edgecolor="white")
ax.set_ylabel("Frecuencia")
ax.set_title(f"Alternancia (turnover)  (n={len(s)}, {scope})")
ax.spines[["top", "right"]].set_visible(False)
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


# %% Años acumulados del partido (%)
var = "cumulative_years_in_power_party_sub_exe"
s, scope = pick(var)
fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(s, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
ax.axvline(s.mean(),   color="#B0413E", lw=1.4, ls="--", label=f"media={s.mean():.1f}")
ax.axvline(s.median(), color="#DD8452", lw=1.4, ls=":",  label=f"mediana={s.median():.1f}")
ax.legend(frameon=False)
ax.set_xlabel("Años acumulados (partido)"); ax.set_ylabel("Frecuencia")
ax.set_title(f"Años acumulados (partido)  (n={len(s)}, {scope})")
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
