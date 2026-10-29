"""Contrato del MLP para el runner comun de validacion cruzada."""
import numpy as np

from src.models.mlp import _batch_size_efectivo, entrenar_y_predecir


def _datos(semilla=7):
    rng = np.random.default_rng(semilla)
    X_train = rng.integers(0, 3, size=(30, 12), dtype=np.uint8)
    X_test = rng.integers(0, 3, size=(8, 12), dtype=np.uint8)
    # Senal sencilla pero no perfecta, para ejercitar una regresion real.
    y_train = X_train[:, :4].sum(axis=1).astype(float) + rng.normal(0, 0.1, 30)
    return X_train, y_train, X_test


def test_mlp_predice_un_valor_finito_por_animal_sin_mutar_entradas():
    X_train, y_train, X_test = _datos()
    X_train_original, X_test_original = X_train.copy(), X_test.copy()

    pred = entrenar_y_predecir(
        X_train, y_train, X_test,
        semilla=123, epochs=8, batch_size=10, hidden_dim=8, learning_rate=0.02,
    )

    assert pred.shape == (len(X_test),)
    assert np.isfinite(pred).all()
    np.testing.assert_array_equal(X_train, X_train_original)
    np.testing.assert_array_equal(X_test, X_test_original)


def test_mlp_es_reproducible_con_la_misma_semilla():
    X_train, y_train, X_test = _datos()
    params = {
        "semilla": 2026,
        "epochs": 8,
        "batch_size": 10,
        "hidden_dim": 8,
        "learning_rate": 0.02,
    }

    primera = entrenar_y_predecir(X_train, y_train, X_test, **params)
    segunda = entrenar_y_predecir(X_train, y_train, X_test, **params)

    np.testing.assert_allclose(primera, segunda, rtol=0, atol=1e-7)


def test_mlp_limita_el_lote_por_memoria_de_forma_determinista():
    assert _batch_size_efectivo(4096, n_features=42_551, max_batch_mb=128) == 788
    assert _batch_size_efectivo(128, n_features=42_551, max_batch_mb=128) == 128
