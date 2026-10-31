import numpy as np

from src.models.random_forest import entrenar_y_predecir


def test_random_forest_entrenar_y_predecir_devuelve_vector_finito():
    rng = np.random.default_rng(0)
    X = rng.integers(0, 3, size=(50, 20), dtype=np.uint8)
    y = X[:, :5].sum(axis=1).astype(float)

    pred = entrenar_y_predecir(
        X[:40], y[:40], X[40:], semilla=7, n_estimators=20
    )

    assert pred.shape == (10,)
    assert np.isfinite(pred).all()
