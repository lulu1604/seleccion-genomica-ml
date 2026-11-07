
"""Pruebas para el resumen de comparacion E6."""

import pandas as pd

from src.evaluation.comparacion import resumir


def test_diferencia_vs_gblup():
    """Comprueba medias, folds y diferencia contra GBLUP."""
    filas = []

    for fold in range(1, 6):
        for modelo, r, error in [
            ("gblup", 0.6, 0.9),
            ("ridge", 0.7, 0.8),
        ]:
            filas.append({
                "modelo": modelo,
                "rasgo": "fpro",
                "escenario_n": 5024,
                "ruido": "base",
                "fold": fold,
                "r_pearson": r,
                "rmse": error,
                "tiempo_s": 1.0,
            })

    resumen = resumir(pd.DataFrame(filas))
    resumen = resumen.set_index("modelo")

    assert resumen.loc["ridge", "n_folds"] == 5
    assert abs(resumen.loc["ridge", "r_media"] - 0.7) < 1e-9
    assert abs(
        resumen.loc["ridge", "diferencia_vs_gblup"] - 0.1
    ) < 1e-9
    assert abs(
        resumen.loc["gblup", "diferencia_vs_gblup"]
    ) < 1e-9
