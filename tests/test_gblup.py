"""Pruebas de GBLUP: contrato, formulas y validacion cruzada comun."""

import numpy as np
import pytest

from src.evaluation.validacion_cruzada import evaluar
from src.models.gblup import entrenar_y_predecir


def test_predicciones_1d_y_finitas():
    """Predice un valor por animal de prueba y respeta su orden."""
    Xtr = np.array([[0, 0, 1], [1, 0, 2], [2, 1, 0],
                    [1, 2, 1], [0, 1, 2]], dtype=np.uint8)
    ytr = np.array([1.0, 2.0, 4.0, 3.0, 1.5])
    Xte = np.array([[2, 0, 1], [0, 2, 1]], dtype=np.uint8)

    pred = entrenar_y_predecir(Xtr, ytr, Xte)
    pred_invertido = entrenar_y_predecir(Xtr, ytr, Xte[::-1])

    assert pred.shape == (2,)
    assert np.isfinite(pred).all()
    np.testing.assert_allclose(pred, pred_invertido[::-1])


def test_formula_gblup_con_heredabilidad():
    """Compara el modelo con la formula matricial independiente."""
    Xtr = np.array([[0, 1], [1, 2], [2, 0], [1, 1]], dtype=np.uint8)
    Xte = np.array([[2, 1], [0, 0]], dtype=np.uint8)
    ytr = np.array([-1.0, 0.5, 2.0, 1.2])
    h2 = 0.5

    p = Xtr.mean(axis=0) / 2.0
    Ztr = Xtr - 2.0 * p
    Zte = Xte - 2.0 * p
    k = 2.0 * np.sum(p * (1.0 - p))
    Gtr = Ztr @ Ztr.T / k
    Gte = Zte @ Ztr.T / k
    mu = ytr.mean()
    esperado = mu + Gte @ np.linalg.solve(
        Gtr + (1.0 - h2) / h2 * np.eye(len(Xtr)), ytr - mu)

    np.testing.assert_allclose(
        entrenar_y_predecir(Xtr, ytr, Xte, h2=h2), esperado, atol=1e-6)


def test_cambiar_test_no_modifica_prediccion():
    """Los SNPs del test nunca cambian las frecuencias de training."""
    Xtr = np.array([[0, 1, 0], [2, 2, 1], [0, 0, 2],
                    [1, 1, 1]], dtype=np.uint8)
    ytr = np.array([0.3, -1.5, 1.9, 0.1])
    punto = np.array([[0, 1, 2]], dtype=np.uint8)
    otros = np.array([[2, 2, 2], [1, 0, 0]], dtype=np.uint8)

    solo = entrenar_y_predecir(Xtr, ytr, punto)[0]
    con_otros = entrenar_y_predecir(
        Xtr, ytr, np.vstack([punto, otros]))[0]
    assert solo == pytest.approx(con_otros)


def test_h2_y_matriz_sin_variacion_rechazadas():
    """Rechaza una heredabilidad imposible o SNPs monomorficos."""
    Xtr = np.array([[0, 1], [2, 1], [1, 0]], dtype=np.uint8)
    ytr = np.array([2.0, 3.0, 4.0])
    for h2 in (0, 1, -0.1, 1.5):
        with pytest.raises(ValueError, match="h2"):
            entrenar_y_predecir(Xtr, ytr, Xtr[:1], h2=h2)

    with pytest.raises(ValueError, match="SNPs variables"):
        entrenar_y_predecir(np.zeros((3, 2)), ytr, np.zeros((1, 2)))


def test_compatible_con_evaluador_de_cinco_folds():
    """El runner puede llamar el modelo sin archivos de datos externos."""
    rng = np.random.default_rng(2026)
    X = rng.integers(0, 3, (30, 12), dtype=np.uint8)
    y = X[:, :4].sum(axis=1).astype(float) + rng.normal(0, 0.2, 30)
    ids = [f"A{i}" for i in range(30)]
    folds = np.arange(30) % 5 + 1

    tabla = evaluar("gblup", "sim_prueba", "fenotipo",
                    datos=(X, y, y, ids), folds=folds)
    assert tabla["fold"].tolist() == [1, 2, 3, 4, 5]
    assert (tabla["modelo"] == "gblup").all()
    assert np.isfinite(tabla["r_pearson"]).all()
    assert np.isfinite(tabla["rmse"]).all()
