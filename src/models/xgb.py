from __future__ import annotations

import numpy as np
from xgboost import XGBRegressor


def entrenar_y_predecir(X_train, y_train, X_test, **params):
    """XGBoost. Hiperparámetros elegidos: (anotar aquí y por qué).

    Se usan árboles de profundidad moderada y una tasa de aprendizaje
    conservadora para limitar el sobreajuste con muchos SNPs correlacionados.
    """
    X_train = np.asarray(X_train, dtype=np.float32)
    X_test = np.asarray(X_test, dtype=np.float32)
    y_train = np.asarray(y_train, dtype=np.float32).ravel()

    modelo = XGBRegressor(
        objective=params.get("objective", "reg:squarederror"),
        n_estimators=params.get("n_estimators", 500),
        learning_rate=params.get("learning_rate", 0.05),
        max_depth=params.get("max_depth", 4),
        subsample=params.get("subsample", 0.8),
        colsample_bytree=params.get("colsample_bytree", 0.2),
        tree_method=params.get("tree_method", "hist"),
        n_jobs=params.get("n_jobs", -1),
        random_state=params.get("semilla", 2026),
        verbosity=params.get("verbosity", 0),
    )
    modelo.fit(X_train, y_train)
    pred = modelo.predict(X_test)
    return np.asarray(pred, dtype=np.float64).ravel()
