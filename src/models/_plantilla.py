"""PLANTILLA: copia este archivo como src/models/<nombre>.py para agregar un modelo.

Contrato (lo unico que el runner necesita de tu modelo):

    def entrenar_y_predecir(X_train, y_train, X_test, **params) -> np.ndarray

- X_train, X_test: matrices numpy uint8 (animales x SNPs, valores 0/1/2).
- y_train: vector numpy 1-D con el rasgo de los animales de train.
- Devuelve un vector 1-D con una prediccion por fila de X_test, en el mismo
  orden. Sin NaN.
- No leas archivos ni folds aqui: el runner ya te pasa el train y el test.
  Asi es imposible que se cuele un animal del test en el entrenamiento.
- Si tu modelo tiene azar (RF, XGBoost, redes), fija la semilla con
  ``params.get("semilla", 2026)``.

Probarlo (rapido, en una simulacion chica):

    python -m src.evaluation.validacion_cruzada --modelo <nombre> --escenario sim_n500 --rasgo fenotipo

Este archivo empieza con "_" para que nadie lo corra por error.
"""
from __future__ import annotations

import numpy as np


def entrenar_y_predecir(X_train: np.ndarray, y_train: np.ndarray,
                        X_test: np.ndarray, **params) -> np.ndarray:
    raise NotImplementedError("Copia esta plantilla y escribe tu modelo aqui")
