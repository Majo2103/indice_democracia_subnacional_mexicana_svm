"""
limpieza_sed_seed.py
====================
Genera el panel integrado (estado x año) uniendo SED y SEED.

Salida: datos/panel_SED_SEED.csv
"""

import warnings
import pandas as pd

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------

SED_PATH  = "datos_sucios/SED.csv"
SEED_PATH = "datos_sucios/SEED.csv"
OUT_PATH  = "datos/panel_SED_SEED.csv"

YEAR_MIN  = 2000
YEAR_MAX  = 2024

SED_VARS = [
    "term_length_in_years_sub_exe",
    "turnover_head_sub_exe",
    "consecutive_reelection_sub_exe",
    "cumulative_years_in_power_sub_exe",
    "head_party_sub_exe",
    "cumulative_years_in_power_party_sub_exe",
    "ideo_party_sub_exe",
    "concurrent_with_nat_election_sub_exe",
]

SEED_VARS = [
    "perc_voter_sub_exe",
    "perc_valid_votes_sub_exe",
    "perc_invalid_votes_sub_exe",
    "perc_votes_winner_candidate_sub_exe",
    "perc_second_place_sub_exe",
    "margin_victory_sub_exe",
    "num_parties_election_contest_sub_exe",
    "snap_election_sub_exe",
    "enp_sub_exe",
]

ID_COLS = ["country_name", "state_name", "state_code", "year"]


def limpiar_sed(path: str) -> pd.DataFrame:
    """Carga SED, filtra México y selecciona variables."""
    raw = pd.read_csv(path, low_memory=False)

    df = (
        raw
        .query("country_name == 'MEXICO'")
        .query(f"{YEAR_MIN} <= year <= {YEAR_MAX}")
        [ID_COLS + SED_VARS]
        .reset_index(drop=True)
    )

    print(
        f"SED  → {df.shape[0]:,} filas x {df.shape[1]} columnas "
        f"| {df['state_name'].nunique()} estados "
        f"| años {df['year'].min()}–{df['year'].max()}"
    )

    return df


def limpiar_seed(path: str) -> pd.DataFrame:
    """
    Carga SEED, filtra México y conserva elecciones reales.

    Importante:
    No se filtra desde YEAR_MIN porque necesitamos elecciones anteriores a 2000
    para hacer forward-fill hacia el panel 2000–2024.
    """
    raw = pd.read_csv(path, low_memory=False)
    df = raw.query("country_name == 'MEXICO'").copy()

    df["year"] = pd.to_datetime(
        df["date_election_sub_exe"],
        errors="coerce",
        dayfirst=True
    ).dt.year

    df = (
        df
        .dropna(subset=["date_election_sub_exe"])
        .dropna(subset=["year"])
        .query(f"year <= {YEAR_MAX}")
        [["state_name", "state_code", "year"] + SEED_VARS]
        .reset_index(drop=True)
    )

    df["year"] = df["year"].astype(int)

    print(
        f"SEED → {df.shape[0]:,} filas x {df.shape[1]} columnas "
        f"| {df['state_name'].nunique()} estados "
        f"| años electorales {df['year'].min()}–{df['year'].max()}"
    )

    print(f"  Elecciones por año:\n{df.groupby('year').size().to_string()}")

    return df


def integrar(sed: pd.DataFrame, seed: pd.DataFrame) -> pd.DataFrame:
    """
    Une SED anual con SEED electoral.

    Para cada estado:
    - toma los datos electorales disponibles, incluso si son previos a 2000;
    - hace forward-fill para propagar la elección vigente;
    - después conserva solo el panel 2000–2024.
    """

    # Para no perder elecciones previas al YEAR_MIN, necesitamos una base anual
    # que cubra desde el primer año de SEED hasta YEAR_MAX.
    estados = sed[["country_name", "state_name", "state_code"]].drop_duplicates()

    year_start = min(YEAR_MIN, seed["year"].min())
    years = pd.DataFrame({"year": range(year_start, YEAR_MAX + 1)})

    base = estados.merge(years, how="cross")

    df = base.merge(
        seed,
        on=["state_name", "state_code", "year"],
        how="left",
    )

    df = df.sort_values(["state_name", "year"]).reset_index(drop=True)

    df[SEED_VARS] = (
        df.groupby("state_name")[SEED_VARS]
        .transform(lambda g: g.ffill())
    )

    # Ahora sí dejamos solo el periodo del panel final
    df = df.query(f"{YEAR_MIN} <= year <= {YEAR_MAX}").reset_index(drop=True)

    # Unimos SED
    df = sed.merge(
        df[["state_name", "state_code", "year"] + SEED_VARS],
        on=["state_name", "state_code", "year"],
        how="left",
    )

    filas_antes = len(df)
    mask_sin_seed = df[SEED_VARS].isna().any(axis=1)
    estados_sin_seed = sorted(df.loc[mask_sin_seed, "state_name"].unique())

    df = df[~mask_sin_seed].reset_index(drop=True)
    filas_eliminadas = filas_antes - len(df)

    print(f"\nPanel integrado → {df.shape[0]:,} filas x {df.shape[1]} columnas")

    if filas_eliminadas > 0:
        print(f"  ({filas_eliminadas} filas eliminadas sin datos SEED tras forward-fill)")
        print(f"  Estados todavía sin elección previa suficiente ({len(estados_sin_seed)}):")

        for estado in estados_sin_seed:
            print(f"    - {estado}")

    nan_counts = df[SED_VARS + SEED_VARS].isna().sum()
    nan_remaining = nan_counts[nan_counts > 0]

    if len(nan_remaining) > 0:
        print("\nNaN remanentes:")
        print(nan_remaining.to_string())
    else:
        print("  Sin NaN remanentes.")

    return df


def main():
    print("=" * 60)
    print("LIMPIEZA SED + SEED — México 2000-2024")
    print("=" * 60)

    print("\n[1] Cargando y limpiando SED...")
    sed = limpiar_sed(SED_PATH)

    print("\n[2] Cargando y limpiando SEED...")
    seed = limpiar_seed(SEED_PATH)

    print("\n[3] Integrando datasets...")
    panel = integrar(sed, seed)

    panel.to_csv(OUT_PATH, index=False)

    print(f"\n✓ Archivo guardado: {OUT_PATH}")
    print(f"  Columnas: {list(panel.columns)}")
    print("=" * 60)


if __name__ == "__main__":
    main()