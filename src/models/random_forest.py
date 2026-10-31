from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor


def entrenar_y_predecir(X_train, y_train, X_test, **params):
    """Entrena Random Forest con semilla reproducible y devuelve predicciones."""
    X_train = np.asarray(X_train, dtype=np.float32)
    X_test = np.asarray(X_test, dtype=np.float32)
    y_train = np.asarray(y_train, dtype=np.float64).ravel()

    modelo = RandomForestRegressor(
        n_estimators=params.get("n_estimators", 200),
        max_features=params.get("max_features", "sqrt"),
        min_samples_leaf=params.get("min_samples_leaf", 2),
        n_jobs=params.get("n_jobs", -1),
        random_state=params.get("semilla", 2026),
    )
    modelo.fit(X_train, y_train)
    return np.asarray(modelo.predict(X_test), dtype=np.float64).ravel()
