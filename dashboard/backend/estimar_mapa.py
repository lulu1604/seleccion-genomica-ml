"""Estima en qué cromosoma y posición está cada marcador (correr UNA vez).

    python dashboard/backend/estimar_mapa.py

El archivo público de Zhang et al. (2015) anonimiza los marcadores (SNP1..SNP42551),
pero vienen ordenados por cromosoma y posición. Este script:

1. Encuentra dónde termina cada cromosoma: los marcadores vecinos del mismo
   cromosoma se heredan juntos (r² alto); entre cromosomas distintos, no.
   Se buscan los 28 cortes con r² cruzado más bajo, separados al menos 400
   marcadores, y se comprueba que la proporción nuestros/chip sea estable.
2. Asigna una posición aproximada (Mb, ensamblaje UMD3.1) a cada marcador con el
   mapa oficial del chip BovineSNP50 v1 (SNPchiMp), por cuantiles dentro de su
   cromosoma.

Necesita data/processed/holstein/X.parquet y data/raw/mapa_chip/bovinesnp50_v1_umd3.tsv.gz.
Escribe results/mapa_snp.csv (snp, cromosoma, mb_aprox).
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
N_CROMOSOMAS = 29
SEPARACION_MIN = 400
DISTANCIA_MAX = 15


def puntaje_cortes(Z: np.ndarray) -> np.ndarray:
    """r² medio de los pares (i, i+k), k<=DISTANCIA_MAX, que cruzan cada corte j|j+1."""
    m = Z.shape[1]
    suma = np.zeros(m - 1)
    cuenta = np.zeros(m - 1)
    for k in range(1, DISTANCIA_MAX + 1):
        r2 = np.empty(m - k, dtype=np.float32)
        for a in range(0, m - k, 3000):
            b = min(a + 3000, m - k)
            r2[a:b] = ((Z[:, a:b] * Z[:, a + k:b + k]).mean(axis=0)) ** 2
        for d in range(k):
            i = np.arange(m - 1) - d
            ok = (i >= 0) & (i < m - k)
            suma[ok] += r2[i[ok]]
            cuenta[ok] += 1
    return suma / cuenta


def elegir_cortes(puntaje: np.ndarray, n: int) -> list[int]:
    elegidos: list[int] = []
    for j in np.argsort(puntaje):
        if all(abs(j - e) > SEPARACION_MIN for e in elegidos):
            elegidos.append(int(j))
        if len(elegidos) == n:
            break
    return sorted(e + 1 for e in elegidos)   # último marcador (1-based) de cada cromosoma


def main():
    X = pd.read_parquet(RAIZ / "data" / "processed" / "holstein" / "X.parquet")
    snps = [c for c in X.columns if c != "id_animal"]
    A = X[snps].to_numpy(np.float32)
    sd = A.std(axis=0)
    sd[sd == 0] = 1
    Z = (A - A.mean(axis=0)) / sd
    del A
    cortes = elegir_cortes(puntaje_cortes(Z), N_CROMOSOMAS - 1) + [len(snps)]

    mapa = pd.read_csv(RAIZ / "data" / "raw" / "mapa_chip" / "bovinesnp50_v1_umd3.tsv.gz", sep="\t")
    mapa = mapa[mapa["chromosome"].astype(str).str.fullmatch(r"\d+")]
    mapa["chromosome"] = mapa["chromosome"].astype(int)
    mapa = mapa[mapa["chromosome"].between(1, N_CROMOSOMAS) & (mapa["position"] > 0)]
    mapa = mapa.drop_duplicates("SNP_name")

    cromosoma = np.zeros(len(snps), dtype=int)
    mb = np.zeros(len(snps))
    inicio = 0
    for c, fin in enumerate(cortes, start=1):
        pos = np.sort(mapa.loc[mapa["chromosome"] == c, "position"].to_numpy())
        n = fin - inicio
        k = np.arange(1, n + 1)
        idx = np.clip(np.round((k - 0.5) * len(pos) / n).astype(int), 0, len(pos) - 1)
        cromosoma[inicio:fin] = c
        mb[inicio:fin] = pos[idx] / 1e6
        print(f"BTA{c:<2} marcadores {inicio + 1}-{fin}  nuestros/chip = {n / len(pos):.3f}")
        inicio = fin

    salida = RAIZ / "results" / "mapa_snp.csv"
    pd.DataFrame({"snp": snps, "cromosoma": cromosoma, "mb_aprox": np.round(mb, 3)}).to_csv(salida, index=False)
    print(f"Guardado: {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
