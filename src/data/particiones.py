"""Particiones (folds) por parentesco genomico.

Todos los modelos se evaluan con los mismos 5 folds. Para que una vaca del
test no tenga hermanas en el train (lo que inflaria el r), los folds se arman
asi:

1. Se calcula la matriz de parentesco genomico G (VanRaden, 2008).
2. Se agrupan los animales emparentados con clustering jerarquico de enlace
   promedio sobre la distancia 1 - G. Quedan en el mismo grupo los animales
   cuyo parentesco promedio es >= ``UMBRAL_PARENTESCO``.
3. Cada grupo familiar va completo a un solo fold. Los grupos se reparten de
   mayor a menor, siempre al fold con menos animales, para que los 5 queden
   del mismo tamano.

Salida (se versiona en git, para que todos usen exactamente los mismos folds):

    data/folds/<escenario>.csv        id_animal, fold (1..5)
    data/folds/<escenario>_meta.json  parametros y diagnostico

Uso:

    python -m src.data.particiones                 # holstein + simulaciones
    python -m src.data.particiones --escenario sim_n500

Para leer los folds desde un modelo o el runner:

    from src.data.particiones import cargar_folds
    folds = cargar_folds("holstein", ids)   # folds[i] es el fold de ids[i]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOLDS_DIR = PROJECT_ROOT / "data" / "folds"

K_FOLDS = 5
UMBRAL_PARENTESCO = 0.10
SEMILLA = 2026
UMBRALES_DIAGNOSTICO = (0.25, 0.40, 0.50)


# ---------------------------------------------------------------- calculo

def matriz_g(X: np.ndarray) -> np.ndarray:
    """Matriz de parentesco genomico de VanRaden: G = ZZ' / (2 * sum p(1-p)).

    ``X`` es animales x SNPs codificado 0/1/2. Devuelve una matriz simetrica
    n x n; la diagonal ronda 1 y los no parientes rondan 0.
    """
    M = np.asarray(X, dtype=np.float32)
    if M.ndim != 2 or M.shape[0] < 2:
        raise ValueError(f"X debe ser una matriz animales x SNPs, llego {M.shape}")
    p = M.mean(axis=0) / 2.0
    denominador = float(2.0 * np.sum(p.astype(np.float64) * (1.0 - p)))
    if denominador <= 0:
        raise ValueError("Todos los SNP son monomorficos: no se puede calcular G")
    Z = M - 2.0 * p
    G = (Z @ Z.T).astype(np.float64) / denominador
    return (G + G.T) / 2.0


def agrupar_parientes(G: np.ndarray, umbral: float = UMBRAL_PARENTESCO) -> np.ndarray:
    """Etiqueta de grupo familiar por animal (enlace promedio sobre 1 - G).

    Se usa enlace promedio y no simple: con enlace simple una cadena de
    parentescos debiles une a casi toda la poblacion en un solo grupo.
    """
    D = 1.0 - np.asarray(G, dtype=np.float64)
    np.fill_diagonal(D, 0.0)
    D = np.clip((D + D.T) / 2.0, 0.0, None)
    arbol = linkage(squareform(D, checks=False), method="average")
    return fcluster(arbol, t=1.0 - umbral, criterion="distance")


def asignar_folds(grupos: Sequence[int], k: int = K_FOLDS,
                  semilla: int = SEMILLA) -> np.ndarray:
    """Reparte grupos completos en k folds balanceados. Devuelve folds 1..k.

    Los grupos van de mayor a menor (empates en orden aleatorio con semilla)
    al fold que tenga menos animales en ese momento.
    """
    grupos = np.asarray(grupos)
    etiquetas, tamanos = np.unique(grupos, return_counts=True)
    if len(grupos) < k:
        raise ValueError(f"Hay {len(grupos)} animales; se necesitan al menos {k}")
    rng = np.random.default_rng(semilla)
    desempate = rng.permutation(len(etiquetas))
    orden = np.lexsort((desempate, -tamanos))

    folds = np.zeros(len(grupos), dtype=int)
    carga = np.zeros(k, dtype=int)
    for i in orden:
        destino = int(np.argmin(carga))
        miembros = grupos == etiquetas[i]
        folds[miembros] = destino + 1
        carga[destino] += int(tamanos[i])
    if (carga == 0).any():
        raise RuntimeError(f"Quedo un fold vacio: tamanos {carga.tolist()}")
    return folds


def pares_cruzados(G: np.ndarray, folds: np.ndarray, umbral: float) -> int:
    """Pares de animales con G > umbral que quedan en folds distintos."""
    folds = np.asarray(folds)
    total = 0
    for f in np.unique(folds):
        dentro = folds == f
        total += int((G[np.ix_(dentro, ~dentro)] > umbral).sum())
    return total // 2


def generar_folds(X: np.ndarray, ids: Sequence[str], k: int = K_FOLDS,
                  umbral: float = UMBRAL_PARENTESCO,
                  semilla: int = SEMILLA) -> tuple[pd.DataFrame, dict]:
    """Calcula G, agrupa parientes y reparte. Devuelve (tabla, diagnostico)."""
    ids = [str(i) for i in ids]
    if len(ids) != len(X):
        raise ValueError(f"X tiene {len(X)} filas y hay {len(ids)} ids")
    if len(set(ids)) != len(ids):
        raise ValueError("Hay id_animal duplicados")

    G = matriz_g(X)
    grupos = agrupar_parientes(G, umbral)
    folds = asignar_folds(grupos, k, semilla)

    azar = np.random.default_rng(semilla).permutation(np.arange(len(ids)) % k) + 1
    _, tam_grupos = np.unique(grupos, return_counts=True)
    meta = {
        "metodo": "VanRaden + clustering jerarquico de enlace promedio sobre 1-G",
        "parentesco_minimo_agrupado": umbral,
        "k_folds": k,
        "semilla": semilla,
        "n_animales": len(ids),
        "n_snps": int(X.shape[1]),
        "n_grupos": int(len(tam_grupos)),
        "grupo_mayor": int(tam_grupos.max()),
        "tamanos_fold": [int((folds == f).sum()) for f in range(1, k + 1)],
        "pares_cruzados": {f"G>{u:.2f}": pares_cruzados(G, folds, u)
                           for u in UMBRALES_DIAGNOSTICO},
        "pares_cruzados_azar": {f"G>{u:.2f}": pares_cruzados(G, azar, u)
                                for u in UMBRALES_DIAGNOSTICO},
    }
    tabla = pd.DataFrame({"id_animal": ids, "fold": folds})
    return tabla, meta


# ---------------------------------------------------------- lectura/escritura

def ruta_folds(escenario: str, base: Path = FOLDS_DIR) -> Path:
    return Path(base) / f"{escenario}.csv"


def _cargar_datos(escenario: str) -> tuple[np.ndarray, list[str]]:
    if escenario == "holstein":
        from src.data.load_holstein import cargar
        X, _, ids = cargar(target="fpro")
    else:
        from src.data.load_simulacion import cargar
        X, _, ids = cargar(escenario, target="fenotipo")
    return X, ids


def guardar_folds(escenario: str, base: Path = FOLDS_DIR) -> dict:
    """Genera y escribe data/folds/<escenario>.csv y su _meta.json."""
    X, ids = _cargar_datos(escenario)
    tabla, meta = generar_folds(X, ids)
    meta["escenario"] = escenario
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ruta_folds(escenario, base), index=False)
    with open(base / f"{escenario}_meta.json", "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, ensure_ascii=False)
    return meta


def cargar_folds(escenario: str, ids: Sequence[str],
                 base: Path = FOLDS_DIR) -> np.ndarray:
    """Devuelve el fold (1..5) de cada animal, en el mismo orden que ``ids``.

    Falla si el archivo no cubre exactamente a los mismos animales.
    """
    ruta = ruta_folds(escenario, base)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Generalo con:\n"
            f"  python -m src.data.particiones --escenario {escenario}"
        )
    tabla = pd.read_csv(ruta, dtype={"id_animal": str})
    if list(tabla.columns) != ["id_animal", "fold"]:
        raise RuntimeError(f"{ruta.name}: columnas {list(tabla.columns)}, "
                           "se esperaba ['id_animal', 'fold']")
    if tabla["id_animal"].duplicated().any():
        raise RuntimeError(f"{ruta.name}: hay id_animal duplicados")
    validos = set(range(1, K_FOLDS + 1))
    if not set(tabla["fold"].unique()) == validos:
        raise RuntimeError(f"{ruta.name}: los folds deben ser exactamente {sorted(validos)}")

    ids = [str(i) for i in ids]
    mapa = dict(zip(tabla["id_animal"], tabla["fold"]))
    faltan = [i for i in ids if i not in mapa]
    if faltan or len(mapa) != len(ids):
        raise RuntimeError(
            f"{ruta.name} no corresponde a estos datos: {len(faltan)} ids sin fold, "
            f"{len(mapa)} en el archivo vs {len(ids)} en los datos"
        )
    return np.array([mapa[i] for i in ids], dtype=int)


def _escenarios_disponibles() -> list[str]:
    from src.data.load_simulacion import listar_escenarios
    return ["holstein", *listar_escenarios()]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--escenario", default="todos",
                        help="holstein, sim_n125, sim_n500, sim_n2000 o todos")
    args = parser.parse_args(argv)
    escenarios = _escenarios_disponibles() if args.escenario == "todos" else [args.escenario]
    for esc in escenarios:
        meta = guardar_folds(esc)
        print(f"{esc}: {meta['n_animales']} animales, {meta['n_grupos']} grupos "
              f"(mayor {meta['grupo_mayor']}), folds {meta['tamanos_fold']}")
        for clave, valor in meta["pares_cruzados"].items():
            print(f"   pares {clave} separados: {valor:>6} (azar: {meta['pares_cruzados_azar'][clave]})")


if __name__ == "__main__":
    main()
