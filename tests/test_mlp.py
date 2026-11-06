"""Contrato del MLP para el runner comun de validacion cruzada."""
import numpy as np
import torch

from src.models.mlp import (
    _MLP,
    _batch_size_efectivo,
    _partir_fit_validacion,
    entrenar_y_predecir,
    validar_configuracion,
)


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


def test_split_interno_es_determinista_disjunto_y_del_quince_por_ciento():
    fit_a, val_a = _partir_fit_validacion(20, fraccion_validacion=0.15, semilla=91)
    fit_b, val_b = _partir_fit_validacion(20, fraccion_validacion=0.15, semilla=91)

    assert len(val_a) == 3
    assert len(fit_a) == 17
    assert not set(fit_a) & set(val_a)
    np.testing.assert_array_equal(fit_a, fit_b)
    np.testing.assert_array_equal(val_a, val_b)


def test_mlp_residual_configura_dropout_en_las_dos_capas_ocultas():
    modelo = _MLP(n_features=12, hidden_dim=8, dropout=0.1)
    capas_dropout = [capa for capa in modelo.residual if isinstance(capa, torch.nn.Dropout)]

    assert len(capas_dropout) == 2
    assert [capa.p for capa in capas_dropout] == [0.1, 0.1]
    assert modelo.aditiva.in_features == 12
    assert torch.count_nonzero(modelo.aditiva.weight) == 0
    assert torch.count_nonzero(modelo.aditiva.bias) == 0
    assert torch.count_nonzero(modelo.residual[-1].weight) == 0


def test_validacion_interna_reporta_mejor_epoca_sin_consumir_test_externo():
    X_train, y_train, _ = _datos()

    resumen = validar_configuracion(
        X_train,
        y_train,
        semilla=2026,
        epochs=8,
        patience=2,
        batch_size=10,
        hidden_dim=8,
        dropout=0.1,
        learning_rate=0.01,
        weight_decay=1e-3,
    )

    assert resumen["n_fit"] == 25
    assert resumen["n_val"] == 5
    assert 1 <= resumen["best_epoch"] <= 8
    assert np.isfinite(resumen["best_val_mse"])
