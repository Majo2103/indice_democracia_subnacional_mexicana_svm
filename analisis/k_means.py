"""
k_means.py
----------
Agrupa a los 32 estados según la forma de sus trayectorias 2000-2024 en
todas las variables de panel_analisis.csv, probando varias definiciones
de "centro" (media) del cluster, y elige el número de clusters.

Uso:
    python k_means.py                                  # 2000-2024, k = 2..8
    python k_means.py --inicio 2012 --fin 2024         # otra ventana
    python k_means.py --kmin 2 --kmax 6 --semillas 30

Cada estado es una serie de tiempo multivariada: una matriz de T años x d
variables. Dos estados "se parecen" si sus trayectorias se parecen.

Definiciones de centro que se comparan
--------------------------------------
1. media_aritmetica  k-means clásico. El centro es el promedio, año por
                     año y variable por variable. Distancia euclidiana.
2. mediana           k-medianas. El centro es la mediana año por año.
                     Distancia L1 (Manhattan). Menos sensible a estados
                     atípicos (p. ej., CDMX en protesta).
3. medoide_dtw       k-medoides con DTW. El centro es un estado real del
                     cluster: el que está más cerca de los demás. DTW
                     (dynamic time warping) permite que dos trayectorias
                     con la misma forma pero desfasadas un par de años
                     (p. ej., instalar el SEA en 2017 o en 2019) se
                     consideren parecidas.
4. baricentro_dba    k-means con DTW: el centro es el baricentro DBA
                     (DTW Barycenter Averaging), la "media" que minimiza
                     la suma de distancias DTW. Requiere tslearn.
5. baricentro_softdtw  Igual, con soft-DTW (versión suavizada y
                     diferenciable de DTW). Requiere tslearn.

Si tslearn no está instalado, se corren solo 1-3 (pip install tslearn).

Cómo se elige k
---------------
Para cada método y cada k se calculan:
  - inercia: suma de distancias de cada estado a su centro (método del codo)
  - silueta: con la distancia propia de cada método (alta = mejor)
  - Calinski-Harabasz y Davies-Bouldin (euclidianas, comparables entre métodos)
  - estabilidad: ARI promedio entre corridas con distintas semillas
  - tamaño del cluster más chico
El k elegido es el de mayor silueta entre los k cuyos clusters tienen al
menos MIN_TAM_CLUSTER estados y cuya estabilidad es >= MIN_ESTABILIDAD.
También se reporta el k del codo como referencia.

Preparación de los datos (todo se documenta en preparacion.txt)
------------------------------------------------------------------
- Conteos (variables *_n) -> tasas por 100 mil habitantes, con poblacion.
- Se agrega el % de protestas con intervención si existen las columnas.
- Se descartan: claves, población, metadatos, montos absolutos cuando
  existe la versión por habitante, y variables sin variación entre
  estados (p. ej., ley_fomento_federal_vigente, igual para todos).
- Se descartan variables con menos de COBERTURA_MIN de datos en la ventana.
- Vacíos restantes: interpolación lineal dentro de cada estado a lo largo
  del tiempo (útil para los Censos Económicos quinquenales) y, en los
  extremos, se repite el valor más cercano. Nota: esto es solo para el
  agrupamiento; el panel original no se modifica.
- Variables no negativas muy sesgadas (asimetría > 1) -> log(1 + x).
- Estandarización z sobre todas las entidades-año de la ventana, de modo
  que se conservan tanto las diferencias entre estados como la tendencia.

Salidas (carpeta resultados_kmeans/)
------------------------------------
metricas_por_k.csv         todas las métricas por método y k
k_optimo.csv               k elegido por método y por qué
asignaciones.csv           cluster de cada estado en cada método (etiquetas
                           alineadas entre métodos para poder compararlas)
centroides.csv             trayectoria del centro de cada cluster, en z
ari_entre_metodos.csv      qué tanto coinciden los métodos entre sí
coasignacion.csv           % de métodos en que cada par de estados queda junto
preparacion.txt            variables usadas, descartadas, imputadas y transformadas
graficas/                  métricas por k, trayectorias de centros y coasignación
"""

import argparse
import itertools
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, silhouette_score)

try:
    from tslearn.clustering import TimeSeriesKMeans
    from tslearn.metrics import cdist_dtw
    TSLEARN = True
except ImportError:
    TSLEARN = False

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
COBERTURA_MIN = 0.70      # fracción mínima de celdas con dato en la ventana
MIN_TAM_CLUSTER = 2       # un cluster de un solo estado no es un "grupo"
MIN_ESTABILIDAD = 0.60    # ARI promedio mínimo entre semillas
UMBRAL_ASIMETRIA = 1.0    # por encima, se aplica log(1 + x)
POR_HABITANTES = 100_000
SEMILLAS_MAX_DTW = 5      # semillas para baricentro_dba y baricentro_softdtw

NO_ANALIZAR = {"cve_ent", "entidad", "anio", "poblacion", "fuente_auditorias"}
# Montos absolutos que se reemplazan por su versión por habitante
ABSOLUTOS_CON_VERSION_PC = {"monto_observado_mdp_2024": "monto_observado_pc_2024"}

COLORES = ["#2f6db3", "#d9822b", "#3a9b5c", "#c2423f", "#7c5cb3",
           "#8c6a4f", "#c75fa3", "#6b6b6b"]


# ---------------------------------------------------------------------------
# 1. Preparación de los datos
# ---------------------------------------------------------------------------
def preparar(panel: pd.DataFrame, inicio: int, fin: int):
    log = []
    df = panel[panel["anio"].between(inicio, fin)].copy()
    df = df.sort_values(["cve_ent", "anio"])
    log.append(f"Ventana: {inicio}-{fin} ({df['anio'].nunique()} años, "
               f"{df['cve_ent'].nunique()} entidades)")

    # Variables candidatas: numéricas que no son claves ni metadatos
    candidatas = [c for c in df.columns
                  if c not in NO_ANALIZAR and pd.api.types.is_numeric_dtype(df[c])]

    # % de protestas con intervención (mide represión, no volumen)
    if {"eventos_protesta_n", "protestas_con_intervencion_n"} <= set(df.columns):
        ev = df["eventos_protesta_n"]
        df["pct_protestas_intervencion"] = np.where(
            ev > 0, 100 * df["protestas_con_intervencion_n"] / ev, np.nan)
        candidatas.append("pct_protestas_intervencion")
        log.append("Creada: pct_protestas_intervencion = intervención / protestas x 100")

    # Montos absolutos con versión por habitante
    for absoluto, pc in ABSOLUTOS_CON_VERSION_PC.items():
        if absoluto in candidatas and pc in df.columns:
            candidatas.remove(absoluto)
            log.append(f"Descartada: {absoluto} (se usa {pc})")

    # Conteos -> tasas por 100 mil habitantes
    variables = []
    if "poblacion" not in df.columns:
        log.append("AVISO: no hay columna poblacion; los conteos se usan sin normalizar")
    for v in candidatas:
        if v.endswith("_n") and "poblacion" in df.columns:
            nueva = v[:-2] + "_por100k"
            df[nueva] = df[v] / df["poblacion"] * POR_HABITANTES
            variables.append(nueva)
            log.append(f"Tasa: {v} -> {nueva}")
        else:
            variables.append(v)

    # Filtro de cobertura: fracción de entidades-año que caen entre el primer
    # y el último dato observado de cada estado (es decir, que se pueden
    # interpolar). Así una serie quinquenal 2003-2023 cuenta como cubierta,
    # pero una que empieza en 2018 no cubre una ventana 2000-2024.
    def cobertura(v):
        obs = df["anio"].where(df[v].notna())
        primero = obs.groupby(df["cve_ent"]).transform("min")
        ultimo = obs.groupby(df["cve_ent"]).transform("max")
        return df["anio"].between(primero, ultimo).mean()

    usadas, descartadas = [], []
    for v in variables:
        cob = cobertura(v)
        (usadas if cob >= COBERTURA_MIN else descartadas).append((v, cob))
    for v, cob in descartadas:
        log.append(f"Descartada por cobertura ({cob:.0%} < {COBERTURA_MIN:.0%}): {v}")
    variables = [v for v, _ in usadas]

    # Imputación dentro de cada estado a lo largo del tiempo
    n_vacias_antes = int(df[variables].isna().sum().sum())
    df[variables] = (df.groupby("cve_ent")[variables]
                       .transform(lambda s: s.interpolate(limit_direction="both")))
    # Si un estado no tiene ningún dato de una variable: mediana de ese año
    resto = df[variables].isna().sum().sum()
    if resto:
        df[variables] = df.groupby("anio")[variables].transform(
            lambda s: s.fillna(s.median()))
    log.append(f"Imputadas {n_vacias_antes} celdas por interpolación temporal "
               f"({resto} de ellas con la mediana del año)")

    # Variables sin variación entre estados en ningún año
    sin_variacion = [v for v in variables
                     if (df.groupby("anio")[v].std(ddof=0).fillna(0) < 1e-12).all()]
    for v in sin_variacion:
        log.append(f"Descartada sin variación entre estados: {v}")
    variables = [v for v in variables if v not in sin_variacion]
    if not variables:
        sys.exit("No quedó ninguna variable después de los filtros. Revisa la ventana.")

    # Transformación logarítmica de variables sesgadas
    for v in variables:
        x = df[v]
        if (x >= 0).all() and x.nunique() > 2 and x.skew() > UMBRAL_ASIMETRIA:
            df[v] = np.log1p(x)
            log.append(f"log(1+x): {v} (asimetría {x.skew():.2f})")

    # Estandarización z sobre todas las entidades-año
    medias, desv = df[variables].mean(), df[variables].std(ddof=0)
    df[variables] = (df[variables] - medias) / desv

    log.append(f"\nVariables usadas ({len(variables)}):")
    log.extend(f"  {v}" for v in variables)

    # Tensor (estados, años, variables)
    estados = df.drop_duplicates("cve_ent")[["cve_ent", "entidad"]].reset_index(drop=True)
    anios = sorted(df["anio"].unique())
    X = np.stack([df[df["cve_ent"] == e][variables].to_numpy()
                  for e in estados["cve_ent"]])
    return X, estados, anios, variables, log


# ---------------------------------------------------------------------------
# 2. Distancias
# ---------------------------------------------------------------------------
def dtw(a: np.ndarray, b: np.ndarray) -> float:
    """DTW multivariado con costo euclidiano (respaldo si no hay tslearn)."""
    n, m = len(a), len(b)
    costo = cdist(a, b) ** 2
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = costo[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(np.sqrt(D[n, m]))


def matriz_dtw(X: np.ndarray) -> np.ndarray:
    if TSLEARN:
        return cdist_dtw(X)
    n = len(X)
    D = np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        D[i, j] = D[j, i] = dtw(X[i], X[j])
    return D


# ---------------------------------------------------------------------------
# 3. Algoritmos (cada uno devuelve etiquetas, centros e inercia)
# ---------------------------------------------------------------------------
def kmeans_media(X, k, semilla):
    plano = X.reshape(len(X), -1)
    km = KMeans(n_clusters=k, n_init=10, random_state=semilla).fit(plano)
    return km.labels_, km.cluster_centers_.reshape(k, *X.shape[1:]), km.inertia_


def kmedianas(X, k, semilla, max_iter=100):
    plano = X.reshape(len(X), -1)
    rng = np.random.default_rng(semilla)
    mejor = None
    for _ in range(10):  # 10 inicios, como n_init de KMeans
        # Inicio tipo k-means++ con distancia L1
        centros = [plano[rng.integers(len(plano))]]
        for _ in range(1, k):
            d = cdist(plano, np.array(centros), "cityblock").min(axis=1)
            centros.append(plano[rng.choice(len(plano), p=d / d.sum())])
        centros = np.array(centros)
        for _ in range(max_iter):
            etiquetas = cdist(plano, centros, "cityblock").argmin(axis=1)
            nuevos = np.array([np.median(plano[etiquetas == c], axis=0)
                               if (etiquetas == c).any() else centros[c]
                               for c in range(k)])
            if np.allclose(nuevos, centros):
                break
            centros = nuevos
        inercia = cdist(plano, centros, "cityblock").min(axis=1).sum()
        if mejor is None or inercia < mejor[2]:
            mejor = (etiquetas, centros, inercia)
    etiquetas, centros, inercia = mejor
    return etiquetas, centros.reshape(k, *X.shape[1:]), inercia


def kmedoides(X, k, semilla, D, max_iter=100):
    rng = np.random.default_rng(semilla)
    n = len(D)
    mejor = None
    for _ in range(10):
        medoides = [int(rng.integers(n))]
        for _ in range(1, k):
            d = D[:, medoides].min(axis=1)
            medoides.append(int(rng.choice(n, p=d / d.sum())) if d.sum() > 0
                            else int(rng.integers(n)))
        medoides = np.array(medoides)
        for _ in range(max_iter):
            etiquetas = D[:, medoides].argmin(axis=1)
            nuevos = medoides.copy()
            for c in range(k):
                miembros = np.where(etiquetas == c)[0]
                if len(miembros):
                    nuevos[c] = miembros[D[np.ix_(miembros, miembros)].sum(axis=1).argmin()]
            if np.array_equal(nuevos, medoides):
                break
            medoides = nuevos
        etiquetas = D[:, medoides].argmin(axis=1)
        inercia = D[np.arange(n), medoides[etiquetas]].sum()
        if mejor is None or inercia < mejor[2]:
            mejor = (etiquetas, medoides, inercia)
    etiquetas, medoides, inercia = mejor
    return etiquetas, X[medoides], inercia


def kmeans_dtw(X, k, semilla, metrica):
    # En pruebas, DTW es más rápido en paralelo y soft-DTW en un solo núcleo
    km = TimeSeriesKMeans(n_clusters=k, metric=metrica, n_init=3, max_iter=50,
                          random_state=semilla, n_jobs=-1 if metrica == "dtw" else 1)
    etiquetas = km.fit_predict(X)
    return etiquetas, km.cluster_centers_, km.inertia_


# ---------------------------------------------------------------------------
# 4. Evaluación de k
# ---------------------------------------------------------------------------
def alinear(etiquetas, referencia, k):
    """Renombra clusters para que coincidan lo más posible con la referencia
    (algoritmo húngaro). Así 'cluster 1' significa lo mismo entre métodos."""
    tabla = np.zeros((k, k))
    for a, b in zip(etiquetas, referencia):
        if a < k and b < k:
            tabla[a, b] += 1
    filas, cols = linear_sum_assignment(-tabla)
    mapa = dict(zip(filas, cols))
    return np.array([mapa.get(e, e) for e in etiquetas])


def k_codo(ks, inercias):
    """Punto más alejado de la recta entre el primer y el último k."""
    x = np.array(ks, float)
    y = np.array(inercias, float)
    if len(x) < 3:
        return int(x[0])
    xn = (x - x.min()) / (x.max() - x.min())
    yn = (y - y.min()) / (y.max() - y.min() + 1e-12)
    dist = np.abs(yn - (yn[0] + (yn[-1] - yn[0]) * xn))
    return int(x[dist.argmax()])


def evaluar(X, metodos, ks, semillas):
    plano = X.reshape(len(X), -1)
    filas, ajustes = [], {}
    for nombre, (funcion, matriz_dist) in metodos.items():
        print(f"\n== {nombre} ==")
        # Los baricentros DTW son lentos (segundos por ajuste): menos semillas
        semillas_m = semillas[:SEMILLAS_MAX_DTW] if nombre.startswith("baricentro") else semillas
        for k in ks:
            corridas = [funcion(X, k, s) for s in semillas_m]
            # La mejor corrida (menor inercia) es la que se reporta
            etiquetas, centros, inercia = min(corridas, key=lambda r: r[2])
            ajustes[(nombre, k)] = (etiquetas, centros, inercia)
            n_grupos = len(np.unique(etiquetas))
            tam_min = np.bincount(etiquetas, minlength=k).min()
            if n_grupos > 1:
                sil = silhouette_score(matriz_dist, etiquetas, metric="precomputed")
                ch = calinski_harabasz_score(plano, etiquetas)
                db = davies_bouldin_score(plano, etiquetas)
            else:
                sil = ch = db = np.nan
            aris = [adjusted_rand_score(a[0], b[0])
                    for a, b in itertools.combinations(corridas, 2)]
            estab = float(np.mean(aris)) if aris else np.nan
            filas.append({"metodo": nombre, "k": k, "inercia": inercia,
                          "silueta": sil, "calinski_harabasz": ch,
                          "davies_bouldin": db, "estabilidad_ari": estab,
                          "tam_cluster_min": int(tam_min)})
            print(f"  k={k}: silueta={sil:.3f}  estabilidad={estab:.2f}  "
                  f"cluster más chico={tam_min}")
    return pd.DataFrame(filas), ajustes


def elegir_k(metricas):
    filas = []
    for metodo, g in metricas.groupby("metodo", sort=False):
        codo = k_codo(g["k"].tolist(), g["inercia"].tolist())
        validos = g[(g["tam_cluster_min"] >= MIN_TAM_CLUSTER)
                    & (g["estabilidad_ari"] >= MIN_ESTABILIDAD)]
        if len(validos):
            mejor = validos.loc[validos["silueta"].idxmax()]
            razon = "mayor silueta entre los k con clusters >= 2 estados y estables"
        else:
            mejor = g.loc[g["silueta"].idxmax()]
            razon = "ningún k cumple los criterios; se usa la mayor silueta (revisar)"
        filas.append({"metodo": metodo, "k_optimo": int(mejor["k"]),
                      "silueta": round(mejor["silueta"], 3),
                      "estabilidad_ari": round(mejor["estabilidad_ari"], 2),
                      "k_codo": codo, "criterio": razon})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 5. Gráficas
# ---------------------------------------------------------------------------
def graficar_metricas(metricas, carpeta):
    fig, ejes = plt.subplots(1, 3, figsize=(15, 4.2))
    for i, (metodo, g) in enumerate(metricas.groupby("metodo", sort=False)):
        c = COLORES[i % len(COLORES)]
        inercia_rel = g["inercia"] / g["inercia"].iloc[0]
        ejes[0].plot(g["k"], inercia_rel, "o-", color=c, label=metodo)
        ejes[1].plot(g["k"], g["silueta"], "o-", color=c, label=metodo)
        ejes[2].plot(g["k"], g["estabilidad_ari"], "o-", color=c, label=metodo)
    titulos = ["Inercia (relativa a k mínimo)", "Silueta", "Estabilidad (ARI entre semillas)"]
    for eje, t in zip(ejes, titulos):
        eje.set_title(t, fontsize=11)
        eje.set_xlabel("Número de clusters (k)")
        eje.set_xticks(sorted(metricas["k"].unique()))
        eje.grid(alpha=0.3)
        eje.spines[["top", "right"]].set_visible(False)
    ejes[2].axhline(MIN_ESTABILIDAD, color="grey", ls="--", lw=1)
    ejes[1].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(carpeta / "metricas_por_k.png", dpi=200)
    plt.close(fig)


def graficar_centroides(metodo, etiquetas, centros, presentes, X, anios, variables, carpeta):
    d = len(variables)
    cols = min(4, d)
    filas = int(np.ceil(d / cols))
    fig, ejes = plt.subplots(filas, cols, figsize=(4 * cols, 2.8 * filas),
                             squeeze=False, sharex=True)
    for j, v in enumerate(variables):
        eje = ejes[j // cols][j % cols]
        for i in range(len(X)):  # estados en gris claro
            eje.plot(anios, X[i, :, j], color=COLORES[etiquetas[i] % len(COLORES)],
                     alpha=0.12, lw=0.8)
        for c in presentes:
            eje.plot(anios, centros[c, :, j], color=COLORES[c % len(COLORES)],
                     lw=2.2, label=f"Cluster {c + 1} (n={np.sum(etiquetas == c)})")
        eje.set_title(v, fontsize=9)
        eje.grid(alpha=0.3)
        eje.spines[["top", "right"]].set_visible(False)
    for j in range(d, filas * cols):
        ejes[j // cols][j % cols].axis("off")
    ejes[0][0].legend(fontsize=7, frameon=False)
    fig.suptitle(f"Trayectorias de los centros (z) — {metodo}", fontsize=12)
    fig.tight_layout()
    fig.savefig(carpeta / f"centroides_{metodo}.png", dpi=200)
    plt.close(fig)


def graficar_coasignacion(co, carpeta):
    # Ordenar estados por agrupamiento jerárquico para que se vean los bloques
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    orden = leaves_list(linkage(squareform(1 - co.to_numpy(), checks=False), "average"))
    co = co.iloc[orden, orden]
    fig, eje = plt.subplots(figsize=(10, 9))
    im = eje.imshow(co.to_numpy(), cmap="Blues", vmin=0, vmax=1)
    eje.set_xticks(range(len(co)), co.columns, rotation=90, fontsize=7)
    eje.set_yticks(range(len(co)), co.index, fontsize=7)
    fig.colorbar(im, ax=eje, shrink=0.8, label="Fracción de métodos en que quedan juntos")
    eje.set_title("Coasignación de estados entre métodos")
    fig.tight_layout()
    fig.savefig(carpeta / "coasignacion.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Clusters de estados por trayectoria.")
    p.add_argument("--panel", default="panel_analisis.csv")
    p.add_argument("--inicio", type=int, default=2000)
    p.add_argument("--fin", type=int, default=2024)
    p.add_argument("--kmin", type=int, default=2)
    p.add_argument("--kmax", type=int, default=8)
    p.add_argument("--semillas", type=int, default=20,
                   help="Corridas con distintas semillas para medir estabilidad")
    p.add_argument("--salida", default="resultados_kmeans")
    args = p.parse_args()

    salida = Path(args.salida)
    (salida / "graficas").mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(args.panel)
    X, estados, anios, variables, log = preparar(panel, args.inicio, args.fin)
    (salida / "preparacion.txt").write_text("\n".join(log), encoding="utf-8")
    print("\n".join(log))
    print(f"\nTensor: {X.shape[0]} estados x {X.shape[1]} años x {X.shape[2]} variables")

    # Matrices de distancia (para silueta y k-medoides)
    plano = X.reshape(len(X), -1)
    D_euc = cdist(plano, plano)
    D_l1 = cdist(plano, plano, "cityblock")
    print("Calculando distancias DTW...")
    D_dtw = matriz_dtw(X)

    metodos = {
        "media_aritmetica": (kmeans_media, D_euc),
        "mediana": (kmedianas, D_l1),
        "medoide_dtw": (lambda X, k, s: kmedoides(X, k, s, D_dtw), D_dtw),
    }
    if TSLEARN:
        metodos["baricentro_dba"] = (lambda X, k, s: kmeans_dtw(X, k, s, "dtw"), D_dtw)
        metodos["baricentro_softdtw"] = (lambda X, k, s: kmeans_dtw(X, k, s, "softdtw"), D_dtw)
    else:
        print("\nAVISO: tslearn no está instalado; se omiten baricentro_dba y "
              "baricentro_softdtw (pip install tslearn)")

    ks = list(range(args.kmin, min(args.kmax, len(X) - 1) + 1))
    semillas = list(range(args.semillas))
    metricas, ajustes = evaluar(X, metodos, ks, semillas)
    metricas.to_csv(salida / "metricas_por_k.csv", index=False)

    elegidos = elegir_k(metricas)
    elegidos.to_csv(salida / "k_optimo.csv", index=False)
    print("\nk elegido por método:")
    print(elegidos.to_string(index=False))

    # Asignaciones finales, alineadas contra el primer método
    asign = estados.copy()
    centros_largos = []
    referencia = None
    for _, fila in elegidos.iterrows():
        metodo, k = fila["metodo"], fila["k_optimo"]
        etiquetas, centros, _ = ajustes[(metodo, k)]
        if referencia is not None:
            k_tabla = max(k, referencia.max() + 1)
            nuevas = alinear(etiquetas, referencia, k_tabla)
            # Reordenar los centros con el mismo renombre
            orden = {old: new for old, new in zip(etiquetas, nuevas)}
            centros_alineados = np.zeros((k_tabla, *centros.shape[1:])) * np.nan
            for old, new in orden.items():
                centros_alineados[new] = centros[old]
            presentes = sorted(set(nuevas))
            etiquetas = nuevas
            centros = centros_alineados
        else:
            referencia = etiquetas
            presentes = list(range(k))
        asign[metodo] = etiquetas + 1
        for c in presentes:
            for t, anio in enumerate(anios):
                for j, v in enumerate(variables):
                    centros_largos.append({"metodo": metodo, "cluster": c + 1,
                                           "anio": anio, "variable": v,
                                           "valor_z": centros[c, t, j]})
        graficar_centroides(metodo, etiquetas, centros, presentes, X, anios,
                            variables, salida / "graficas")

    asign.to_csv(salida / "asignaciones.csv", index=False)
    pd.DataFrame(centros_largos).to_csv(salida / "centroides.csv", index=False)

    # Coincidencia entre métodos
    nombres = list(elegidos["metodo"])
    ari = pd.DataFrame(index=nombres, columns=nombres, dtype=float)
    for a, b in itertools.product(nombres, repeat=2):
        ari.loc[a, b] = adjusted_rand_score(asign[a], asign[b])
    ari.round(3).to_csv(salida / "ari_entre_metodos.csv")

    # Coasignación: fracción de métodos en que cada par de estados queda junto
    etiquetas_todas = asign[nombres].to_numpy()
    co = np.mean([(etiquetas_todas[:, [m]] == etiquetas_todas[:, m]).astype(float)
                  for m in range(len(nombres))], axis=0)
    co = pd.DataFrame(co, index=estados["entidad"], columns=estados["entidad"])
    co.round(2).to_csv(salida / "coasignacion.csv")

    graficar_metricas(metricas, salida / "graficas")
    graficar_coasignacion(co, salida / "graficas")

    print("\nCoincidencia entre métodos (ARI):")
    print(ari.round(2).to_string())
    print("\nAsignaciones:")
    print(asign.to_string(index=False))
    print(f"\nResultados en {salida.resolve()}")


if __name__ == "__main__":
    main()
