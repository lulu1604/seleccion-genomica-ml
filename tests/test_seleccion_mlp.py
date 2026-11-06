"""Contrato de la seleccion interna de hiperparametros de la MLP."""
import numpy as np

from src.evaluation.seleccion_mlp import COLUMNAS_SELECCION, seleccionar_dropout_por_fold


def test_seleccion_entrega_una_fila_por_fold_y_configuracion_sin_test_externo():
    X = np.arange(50 * 3, dtype=np.uint8).reshape(50, 3) % 3
    y = np.arange(50, dtype=float)
    folds = np.arange(50) % 5 + 1
    llamadas = []

    def validador(X_train, y_train, **params):
        # El ultimo SNP identifica el animal: nunca deben aparecer los diez test.
        llamadas.append((set(y_train), params["dropout"]))
        return {
            "best_val_mse": params["dropout"] + 0.1,
            "best_epoch": 3,
            "epochs_ran": 5,
            "n_fit": 34,
            "n_val": 6,
            "input_batch_mb": 0.01,
        }

    tabla = seleccionar_dropout_por_fold(
        X, y, folds, dropouts=(0.0, 0.1, 0.2), validador=validador
    )

    assert list(tabla.columns) == COLUMNAS_SELECCION
    assert len(tabla) == 15
    assert tabla.groupby("fold")["dropout"].nunique().eq(3).all()
    assert all(len(entrenados) == 40 for entrenados, _ in llamadas)
    assert set(tabla["fold"]) == {1, 2, 3, 4, 5}
