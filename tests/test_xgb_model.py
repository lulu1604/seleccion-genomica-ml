import numpy as np

from src.models.xgb import entrenar_y_predecir


def test_xgb_entrenar_y_predecir_devuelve_vector_1d_finito():
    rng = np.random.default_rng(0)
    X = rng.integers(0, 3, size=(50, 20), dtype=np.uint8)
    y = X[:, :5].sum(axis=1).astype(float)

    X_train = X[:40]
    y_train = y[:40]
    X_test = X[40:]

    pred = entrenar_y_predecir(X_train, y_train, X_test, semilla=7)

    assert pred.shape == (10,)
    assert np.isfinite(pred).all()
    assert pred.dtype.kind in {"f", "i"}
