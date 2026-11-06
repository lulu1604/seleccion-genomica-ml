from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge


def entrenar_y_predecir(X_train, y_train, X_test, **params):
    """Entrena Ridge con regularizacion fija y devuelve una prediccion por fila."""
    X_train = np.asarray(X_train, dtype=np.float32)
    X_test = np.asarray(X_test, dtype=np.float32)
    y_train = np.asarray(y_train, dtype=np.float64).ravel()

    modelo = Ridge(alpha=params.get("alpha", 10.0), solver="lsqr")
    modelo.fit(X_train, y_train)
    return np.asarray(modelo.predict(X_test), dtype=np.float64).ravel()
