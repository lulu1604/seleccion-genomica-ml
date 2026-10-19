"""Tests del contrato de modelos y del runner de validacion cruzada."""
import math

import numpy as np
import pandas as pd
import pytest

from src.evaluation import validacion_cruzada as VC
from src.evaluation.metricas import r_pearson, rmse


def _datos(n=50, snps=20, semilla=0):
    rng = np.random.default_rng(semilla)
    X = rng.integers(0, 3, (n, snps)).astype(np.uint8)
    gv = X[:, :5].sum(axis=1).astype(float)
    fen = gv + rng.normal(0, 1, n)
    ids = [f"A{i}" for i in range(n)]
    folds = np.arange(n) % 5 + 1
    return (X, fen, gv, ids), folds


def test_metricas():
    assert r_pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert r_pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert math.isnan(r_pearson([1, 2, 3], [5, 5, 5]))
    assert rmse([0, 0], [3, 4]) == pytest.approx(math.sqrt(12.5))


def test_evaluar_devuelve_una_fila_por_fold_con_el_contrato():
    datos, folds = _datos()

    def media(X_train, y_train, X_test):
        return np.full(len(X_test), y_train.mean()) + X_test[:, 0] * 1e-3

    tabla = VC.evaluar("media", "sim_prueba", "fenotipo", funcion=media,
                       datos=datos, folds=folds)
    assert list(tabla.columns) == VC.COLUMNAS
    assert tabla["fold"].tolist() == [1, 2, 3, 4, 5]
    assert (tabla["escenario_n"] == 50).all()
    assert tabla["tiempo_s"].ge(0).all()


def test_el_modelo_nunca_ve_animales_del_test():
    datos, folds = _datos()
    X = datos[0].copy()
    X[:, -1] = np.arange(len(X))  # columna con el indice de cada animal
    vistos = []

    def espia(X_train, y_train, X_test):
        entrenados, probados = set(X_train[:, -1]), set(X_test[:, -1])
        assert not entrenados & probados
        vistos.append(probados)
        return np.zeros(len(X_test)) + X_test[:, 0]

    VC.evaluar("espia", "sim_prueba", "fenotipo", funcion=espia,
               datos=(X, *datos[1:]), folds=folds)
    assert set().union(*vistos) == set(range(len(X)))  # cada animal se predice 1 vez


def test_en_simulacion_r_se_mide_contra_valor_genetico():
    datos, folds = _datos()
    _, _, gv, _ = datos

    def oraculo(X_train, y_train, X_test):
        return X_test[:, :5].sum(axis=1).astype(float)  # devuelve gv exacto

    tabla = VC.evaluar("oraculo", "sim_prueba", "fenotipo", funcion=oraculo,
                       datos=datos, folds=folds)
    assert tabla["r_pearson"].tolist() == pytest.approx([1.0] * 5)
    assert tabla["rmse"].tolist() == pytest.approx([0.0] * 5)


@pytest.mark.parametrize("salida", ["corta", "nan"])
def test_evaluar_rechaza_predicciones_invalidas(salida):
    datos, folds = _datos()

    def roto(X_train, y_train, X_test):
        if salida == "corta":
            return np.zeros(len(X_test) - 1)
        return np.full(len(X_test), np.nan)

    with pytest.raises(ValueError):
        VC.evaluar("roto", "sim_prueba", "fenotipo", funcion=roto,
                   datos=datos, folds=folds)


def test_params_llegan_al_modelo():
    datos, folds = _datos()
    recibidos = {}

    def con_params(X_train, y_train, X_test, alpha=None):
        recibidos["alpha"] = alpha
        return X_test[:, 0].astype(float)

    VC.evaluar("p", "sim_prueba", "fenotipo", params={"alpha": 3.5},
               funcion=con_params, datos=datos, folds=folds)
    assert recibidos["alpha"] == 3.5


def test_guardar_parcial_y_consolidar(tmp_path):
    datos, folds = _datos()

    def m(X_train, y_train, X_test):
        return X_test[:, 0].astype(float)

    for nombre in ("modelo_b", "modelo_a"):
        tabla = VC.evaluar(nombre, "sim_prueba", "fenotipo", funcion=m,
                           datos=datos, folds=folds)
        ruta = VC.guardar_parcial(tabla, "sim_prueba", results_dir=tmp_path)
        assert ruta.name == f"{nombre}__sim_prueba__fenotipo__base.csv"

    total = VC.consolidar(results_dir=tmp_path)
    assert len(total) == 10
    assert total["modelo"].iloc[0] == "modelo_a"
    leido = pd.read_csv(tmp_path / "resultados.csv")
    assert list(leido.columns) == VC.COLUMNAS


def test_consolidar_sin_parciales_deja_solo_encabezado(tmp_path):
    VC.consolidar(results_dir=tmp_path)
    assert (tmp_path / "resultados.csv").read_text().strip() == ",".join(VC.COLUMNAS)


def test_modelo_inexistente_o_plantilla():
    with pytest.raises(ValueError, match="No existe"):
        VC._funcion_modelo("no_existe_este_modelo")
    with pytest.raises(ValueError, match="plantilla"):
        VC._funcion_modelo("_plantilla")


def test_rasgo_invalido():
    with pytest.raises(ValueError):
        VC.cargar_escenario("holstein", "fenotipo")
    with pytest.raises(ValueError):
        VC.cargar_escenario("sim_n500", "fpro")


def test_leer_params():
    assert VC._leer_params(["alpha=10", "lr=0.01", "kernel=rbf"]) == {
        "alpha": 10, "lr": 0.01, "kernel": "rbf"}
    with pytest.raises(ValueError):
        VC._leer_params(["sin_igual"])
