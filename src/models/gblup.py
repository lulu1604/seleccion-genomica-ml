"""GBLUP con la matriz de parentesco genomico de VanRaden (metodo 1).

Predice valores geneticos a partir de SNPs codificados como 0, 1 o 2.
La frecuencia alelica, la media del rasgo y el ajuste se calculan usando
SOLO los animales de entrenamiento, sin informacion del conjunto de prueba.

El parametro h2 es la heredabilidad asumida (por defecto, 0.3).
Se fija antes de evaluar y se mantiene para todos los rasgos.
No se elige mirando los resultados del conjunto de prueba.
"""

import numpy as np
from scipy.linalg import solve


def entrenar_y_predecir(X_train, y_train, X_test, h2=0.3,
                        **params) -> np.ndarray:
    """Entrena GBLUP y predice una observacion por animal de prueba.

    Args:
        X_train (np.ndarray): Genotipos de entrenamiento, animales x SNPs.
        y_train (np.ndarray): Rasgo continuo de los animales de entrenamiento.
        X_test (np.ndarray): Genotipos de prueba, animales x SNPs.
        h2 (float): Heredabilidad asumida, estrictamente entre 0 y 1.
        **params: Parametros extra del runner (no utilizados).

    Returns:
        np.ndarray: Predicciones 1-D alineadas con las filas de X_test.
    """
    if not 0 < h2 < 1:
        raise ValueError("h2 debe estar entre 0 y 1 (sin incluir extremos)")

    Xtr = np.asarray(X_train, dtype=np.float32)
    Xte = np.asarray(X_test, dtype=np.float32)
    ytr = np.asarray(y_train, dtype=np.float64).ravel()

    if (Xtr.ndim != 2 or Xte.ndim != 2 or
            Xtr.shape[1] != Xte.shape[1] or
            len(Xtr) != len(ytr) or len(Xtr) == 0):
        raise ValueError(
            "Dimensiones incompatibles entre X_train, y_train y X_test"
        )
    if not np.isfinite(ytr).all():
        raise ValueError("y_train contiene valores no finitos")
    if len(Xte) == 0:
        return np.empty(0, dtype=np.float64)

    # Frecuencia alelica calculada SOLO con el entrenamiento.
    p = Xtr.mean(axis=0) / 2.0
    denominador = float(2.0 * np.sum(p * (1.0 - p), dtype=np.float64))
    if denominador <= 0:
        raise ValueError("No hay SNPs variables en el entrenamiento")

    # SNPs centrados usando la misma media de entrenamiento.
    Ztr = Xtr - 2.0 * p
    Zte = Xte - 2.0 * p

    # Matriz de parentesco train-train y test-train (VanRaden).
    Gtr = (Ztr @ Ztr.T) / denominador
    Gte = (Zte @ Ztr.T) / denominador

    # BLUP: (G + lambda I) * alfa = y - media_train.
    penalizacion = (1.0 - h2) / h2
    Gtr = Gtr.astype(np.float64)
    Gtr.flat[::len(Gtr) + 1] += penalizacion

    media = float(ytr.mean())
    alfa = solve(Gtr, ytr - media, assume_a="pos", check_finite=False,
                 overwrite_a=True)
    return np.asarray(media + Gte @ alfa, dtype=np.float64).ravel()
