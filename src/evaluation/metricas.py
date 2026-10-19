"""Metricas de evaluacion comunes a todos los modelos."""
from __future__ import annotations

import numpy as np


def r_pearson(y_real, y_pred) -> float:
    """Correlacion de Pearson entre lo real y lo predicho.

    Devuelve NaN si alguno de los dos es constante (la correlacion no existe).
    """
    a = np.asarray(y_real, dtype=np.float64)
    b = np.asarray(y_pred, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError(f"Formas distintas o no 1-D: {a.shape} vs {b.shape}")
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def rmse(y_real, y_pred) -> float:
    """Raiz del error cuadratico medio."""
    a = np.asarray(y_real, dtype=np.float64)
    b = np.asarray(y_pred, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"Formas distintas: {a.shape} vs {b.shape}")
    return float(np.sqrt(np.mean((a - b) ** 2)))
