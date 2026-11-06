"""Trazabilidad y publicacion atomica de la MLP residual para la E6.

La tabla de seleccion usa solo los *trains* de los folds externos. Las
metricas de test externo se calculan despues por el runner comun y no
participan en seleccionar ``dropout`` ni la epoca.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from src.evaluation import validacion_cruzada as VC
from src.data.particiones import cargar_folds
from src.models.mlp import entrenar_y_predecir, validar_configuracion

DROP_OUTS = (0.0, 0.1, 0.2)
COLUMNAS_SELECCION = [
    "fold", "dropout", "best_val_mse", "best_epoch", "epochs_ran", "n_fit",
    "n_val", "input_batch_mb", "tiempo_s",
]
ESCENARIOS_E6 = (
    ("holstein", "mkg"), ("holstein", "fpro"), ("holstein", "scs"),
    ("sim_n125", "fenotipo"), ("sim_n500", "fenotipo"),
    ("sim_n2000", "fenotipo"),
)


def seleccionar_dropout_por_fold(
    X: np.ndarray,
    y: np.ndarray,
    folds: np.ndarray,
    *,
    dropouts: Iterable[float] = DROP_OUTS,
    params: dict | None = None,
    validador: Callable[..., dict] = validar_configuracion,
) -> pd.DataFrame:
    """Registra cada candidato usando solamente el train de su fold externo."""
    params = dict(params or {})
    filas = []
    for fold in range(1, VC.K_FOLDS + 1):
        train = np.asarray(folds) != fold
        for dropout in dropouts:
            inicio = time.perf_counter()
            resumen = validador(X[train], y[train], **{**params, "dropout": float(dropout)})
            filas.append({
                "fold": fold, "dropout": float(dropout),
                "best_val_mse": resumen["best_val_mse"],
                "best_epoch": resumen["best_epoch"],
                "epochs_ran": resumen["epochs_ran"], "n_fit": resumen["n_fit"],
                "n_val": resumen["n_val"], "input_batch_mb": resumen["input_batch_mb"],
                "tiempo_s": round(time.perf_counter() - inicio, 3),
            })
    return pd.DataFrame(filas, columns=COLUMNAS_SELECCION)


def ejecutar_seleccion_interna(
    escenario: str, rasgo: str, *, params: dict | None = None,
    results_dir: Path = VC.RESULTS_DIR,
) -> pd.DataFrame:
    """Ejecuta y registra la seleccion previa sin generar metricas de test."""
    X, y, _, ids = VC.cargar_escenario(escenario, rasgo)
    folds = cargar_folds(escenario, ids)
    tabla = seleccionar_dropout_por_fold(X, y, folds, params=params)
    carpeta = Path(results_dir) / "experiments"
    carpeta.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(carpeta / f"mlp_residual__{escenario}__{rasgo}__seleccion_interna.csv", index=False)
    return tabla


def evaluar_residual(
    escenario: str, rasgo: str, *, params: dict | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evalua un escenario oficial y devuelve metricas y seleccion por fold.

    La seleccion realmente usada se hace dentro de ``entrenar_y_predecir``
    para cada fold; esta funcion solo convierte esos registros en evidencia
    versionable. No expone etiquetas de test al modelo.
    """
    params = dict(params or {})
    registros: list[dict] = []

    def modelo(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, **_: object) -> np.ndarray:
        registro_fold: list[dict] = []
        pred = entrenar_y_predecir(
            X_train, y_train, X_test, dropouts=DROP_OUTS,
            registro_seleccion=registro_fold, **params,
        )
        if len(registro_fold) != 1:
            raise RuntimeError("Cada fold debe generar exactamente un registro de seleccion")
        registros.append(registro_fold[0])
        return pred

    tabla = VC.evaluar("mlp", escenario, rasgo, funcion=modelo)
    seleccion = pd.DataFrame(registros)
    if len(seleccion) != VC.K_FOLDS:
        raise RuntimeError("Faltan registros de seleccion interna")
    seleccion.insert(0, "fold", np.arange(1, VC.K_FOLDS + 1))
    seleccion.insert(0, "rasgo", rasgo)
    seleccion.insert(0, "escenario", escenario)
    return tabla, seleccion


def _validar_tabla_definitiva(tabla: pd.DataFrame) -> None:
    if list(tabla.columns) != VC.COLUMNAS or len(tabla) != VC.K_FOLDS:
        raise ValueError("El parcial definitivo no cumple el contrato de cinco folds")
    if tabla["fold"].tolist() != list(range(1, VC.K_FOLDS + 1)):
        raise ValueError("Los folds definitivos deben ser 1..5 en orden")
    if not np.isfinite(tabla[["r_pearson", "rmse", "tiempo_s"]].to_numpy()).all():
        raise ValueError("Las metricas definitivas deben ser finitas")


def ejecutar_seis_definitivos(
    *, params: dict | None = None, results_dir: Path = VC.RESULTS_DIR,
    progreso: Callable[[str, str], None] | None = None,
) -> tuple[dict[tuple[str, str], pd.DataFrame], dict[tuple[str, str], pd.DataFrame]]:
    """Corre los seis escenarios y publica todos sus CSV solo si todos pasan.

    No se escribe ningun parcial definitivo durante las corridas. Si una
    falla, los parciales actuales permanecen intactos; si todas validan, se
    escriben los seis parciales y seis tablas de seleccion al final.
    """
    resultados: dict[tuple[str, str], pd.DataFrame] = {}
    selecciones: dict[tuple[str, str], pd.DataFrame] = {}
    for escenario, rasgo in ESCENARIOS_E6:
        tabla, seleccion = evaluar_residual(escenario, rasgo, params=params)
        _validar_tabla_definitiva(tabla)
        resultados[escenario, rasgo] = tabla
        selecciones[escenario, rasgo] = seleccion
        if progreso is not None:
            progreso(escenario, rasgo)

    carpeta_experimentos = Path(results_dir) / "experiments"
    carpeta_experimentos.mkdir(parents=True, exist_ok=True)
    for (escenario, rasgo), tabla in resultados.items():
        VC.guardar_parcial(tabla, escenario, results_dir=results_dir)
        selecciones[escenario, rasgo].to_csv(
            carpeta_experimentos / f"mlp_residual__{escenario}__{rasgo}__seleccion.csv",
            index=False,
        )
    return resultados, selecciones


def main() -> None:
    """Punto de entrada reproducible para la corrida final de la E6."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="corre los seis escenarios E6")
    parser.add_argument("--results-dir", type=Path, default=VC.RESULTS_DIR)
    args = parser.parse_args()
    if not args.all:
        parser.error("usa --all para ejecutar los seis escenarios oficiales")
    resultados, _ = ejecutar_seis_definitivos(
        results_dir=args.results_dir,
        progreso=lambda escenario, rasgo: print(f"completo:{escenario}:{rasgo}", flush=True),
    )
    for (escenario, rasgo), tabla in resultados.items():
        print(
            f"{escenario},{rasgo},{tabla.r_pearson.mean():.6f},"
            f"{tabla.r_pearson.std(ddof=1):.6f},{tabla.rmse.mean():.6f},"
            f"{tabla.tiempo_s.sum():.3f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
