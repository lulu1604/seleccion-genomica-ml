"""Tests de los folds por parentesco (src/data/particiones.py)."""
import json

import numpy as np
import pandas as pd
import pytest

from src.data import particiones as P


def _poblacion_con_familias(n_familias=10, hijos=6, n_snps=3000, semilla=0):
    """Genotipos 0/1/2 de familias de hermanos completos (G ~ 0.5 entre ellos)."""
    rng = np.random.default_rng(semilla)
    frec = rng.uniform(0.1, 0.9, n_snps)
    filas, familia = [], []
    for f in range(n_familias):
        padre = rng.random((2, n_snps)) < frec   # dos cromosomas por SNP
        madre = rng.random((2, n_snps)) < frec
        for _ in range(hijos):
            de_padre = padre[rng.integers(0, 2, n_snps), np.arange(n_snps)]
            de_madre = madre[rng.integers(0, 2, n_snps), np.arange(n_snps)]
            filas.append(de_padre.astype(np.uint8) + de_madre.astype(np.uint8))
            familia.append(f)
    ids = [f"A{i:03d}" for i in range(len(filas))]
    return np.vstack(filas), np.array(familia), ids


def test_matriz_g_simetrica_y_diagonal_cerca_de_uno():
    X, familia, _ = _poblacion_con_familias()
    G = P.matriz_g(X)
    assert G.shape == (len(X), len(X))
    assert np.allclose(G, G.T)
    assert abs(np.diag(G).mean() - 1.0) < 0.1
    hermanos = G[0, 1:6].mean()           # mismos padres
    extranos = G[0, familia != 0].mean()  # otras familias
    assert hermanos > 0.35 and abs(extranos) < 0.15


def test_ninguna_familia_queda_partida_y_folds_balanceados():
    X, familia, ids = _poblacion_con_familias()
    tabla, meta = P.generar_folds(X, ids)
    folds = tabla["fold"].to_numpy()
    for f in np.unique(familia):
        assert len(np.unique(folds[familia == f])) == 1, f"familia {f} partida"
    assert sorted(np.unique(folds)) == [1, 2, 3, 4, 5]
    assert meta["tamanos_fold"] == [12, 12, 12, 12, 12]
    assert meta["pares_cruzados"]["G>0.25"] == 0
    assert meta["pares_cruzados_azar"]["G>0.25"] > 0


def test_asignar_folds_es_reproducible_y_respeta_grupos():
    grupos = np.array([1] * 7 + [2] * 5 + [3] * 3 + list(range(4, 14)))
    a = P.asignar_folds(grupos, k=5, semilla=1)
    b = P.asignar_folds(grupos, k=5, semilla=1)
    assert np.array_equal(a, b)
    for g in np.unique(grupos):
        assert len(np.unique(a[grupos == g])) == 1
    tamanos = np.bincount(a)[1:]
    assert tamanos.max() - tamanos.min() <= 7   # nunca mas que el grupo mayor


def test_asignar_folds_rechaza_menos_animales_que_folds():
    with pytest.raises(ValueError):
        P.asignar_folds([1, 2, 3], k=5)


def test_pares_cruzados_cuenta_cada_par_una_vez():
    G = np.array([[1.0, 0.5, 0.0], [0.5, 1.0, 0.0], [0.0, 0.0, 1.0]])
    assert P.pares_cruzados(G, np.array([1, 2, 2]), 0.25) == 1
    assert P.pares_cruzados(G, np.array([1, 1, 2]), 0.25) == 0


def _escribir(tmp_path, filas):
    pd.DataFrame(filas, columns=["id_animal", "fold"]).to_csv(
        tmp_path / "prueba.csv", index=False)


def test_cargar_folds_devuelve_el_orden_de_ids(tmp_path):
    _escribir(tmp_path, [("a", 1), ("b", 2), ("c", 3), ("d", 4), ("e", 5)])
    folds = P.cargar_folds("prueba", ["e", "a", "c", "b", "d"], base=tmp_path)
    assert folds.tolist() == [5, 1, 3, 2, 4]


def test_cargar_folds_falla_si_no_cubre_los_mismos_animales(tmp_path):
    _escribir(tmp_path, [("a", 1), ("b", 2), ("c", 3), ("d", 4), ("e", 5)])
    with pytest.raises(RuntimeError):
        P.cargar_folds("prueba", ["a", "b", "c", "d", "X"], base=tmp_path)
    with pytest.raises(RuntimeError):
        P.cargar_folds("prueba", ["a", "b", "c", "d"], base=tmp_path)


def test_cargar_folds_falla_con_folds_fuera_de_1_a_5(tmp_path):
    _escribir(tmp_path, [("a", 0), ("b", 1), ("c", 2), ("d", 3), ("e", 4)])
    with pytest.raises(RuntimeError):
        P.cargar_folds("prueba", list("abcde"), base=tmp_path)


def test_cargar_folds_avisa_como_generarlos(tmp_path):
    with pytest.raises(FileNotFoundError, match="python -m src.data.particiones"):
        P.cargar_folds("no_existe", ["a"], base=tmp_path)


@pytest.mark.parametrize("escenario", ["holstein", "sim_n125", "sim_n500", "sim_n2000"])
def test_folds_versionados_son_validos(escenario):
    """Los archivos de data/folds/ cubren 1..5 y estan balanceados."""
    ruta = P.ruta_folds(escenario)
    if not ruta.exists():
        pytest.skip(f"{ruta} no existe")
    tabla = pd.read_csv(ruta, dtype={"id_animal": str})
    meta = json.loads((P.FOLDS_DIR / f"{escenario}_meta.json").read_text(encoding="utf-8"))
    assert list(tabla.columns) == ["id_animal", "fold"]
    assert not tabla["id_animal"].duplicated().any()
    tamanos = tabla["fold"].value_counts().sort_index()
    assert tamanos.index.tolist() == [1, 2, 3, 4, 5]
    assert tamanos.max() - tamanos.min() <= meta["grupo_mayor"]
    assert len(tabla) == meta["n_animales"]
