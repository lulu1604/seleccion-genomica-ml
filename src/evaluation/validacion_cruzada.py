"""Runner comun de validacion cruzada: mismos datos, mismos folds, misma metrica.

Cada modelo vive en ``src/models/<nombre>.py`` y expone
``entrenar_y_predecir(X_train, y_train, X_test, **params)``
(ver ``src/models/_plantilla.py``). Este runner:

1. carga el escenario (holstein o una simulacion) y sus folds de data/folds/,
2. en cada fold k: entrena con los otros 4 y predice el fold k,
3. calcula r de Pearson, RMSE y tiempo,
4. guarda results/parciales/<modelo>__<escenario>__<rasgo>__<ruido>.csv.

Cada modelo escribe su propio archivo parcial, asi nadie edita el mismo CSV.
``--consolidar`` junta todos los parciales en results/resultados.csv.

En las simulaciones se entrena con el fenotipo y r/RMSE se calculan contra el
valor genetico verdadero (valor_gv), que en datos reales no se conoce.

Uso:

    python -m src.evaluation.validacion_cruzada --modelo ridge --escenario sim_n500 --rasgo fenotipo
    python -m src.evaluation.validacion_cruzada --modelo ridge --escenario holstein --rasgo fpro --param alpha=10
    python -m src.evaluation.validacion_cruzada --consolidar
"""
from __future__ import annotations

import argparse
import importlib
import time
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np
import pandas as pd

from src.data.particiones import FOLDS_DIR, K_FOLDS, cargar_folds
from src.evaluation.metricas import r_pearson, rmse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
COLUMNAS = ["modelo", "rasgo", "escenario_n", "ruido", "fold",
            "r_pearson", "rmse", "tiempo_s"]
RASGOS_HOLSTEIN = ("mkg", "fpro", "scs")
RASGOS_SIM = ("fenotipo",)

Datos = tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]


def cargar_escenario(escenario: str, rasgo: str) -> Datos:
    """Devuelve (X, y_entrenar, y_evaluar, ids) del escenario."""
    if escenario == "holstein":
        if rasgo not in RASGOS_HOLSTEIN:
            raise ValueError(f"Rasgo '{rasgo}' no existe en holstein: {RASGOS_HOLSTEIN}")
        from src.data.load_holstein import cargar
        X, y, ids = cargar(target=rasgo)
        return X, y, y, ids
    if rasgo not in RASGOS_SIM:
        raise ValueError(f"En simulaciones se entrena con {RASGOS_SIM}, llego '{rasgo}'")
    from src.data.load_simulacion import cargar
    X, tabla, ids = cargar(escenario, target=None)
    return X, tabla["fenotipo"].to_numpy(), tabla["valor_gv"].to_numpy(), ids


def _funcion_modelo(modelo: str) -> Callable[..., np.ndarray]:
    if modelo.startswith("_"):
        raise ValueError(f"'{modelo}' es una plantilla, no un modelo")
    try:
        modulo = importlib.import_module(f"src.models.{modelo}")
    except ModuleNotFoundError as exc:
        raise ValueError(f"No existe src/models/{modelo}.py") from exc
    if not hasattr(modulo, "entrenar_y_predecir"):
        raise ValueError(f"src/models/{modelo}.py no define entrenar_y_predecir()")
    return modulo.entrenar_y_predecir


def evaluar(modelo: str, escenario: str, rasgo: str, ruido: str = "base",
            params: Optional[dict] = None,
            funcion: Optional[Callable[..., np.ndarray]] = None,
            datos: Optional[Datos] = None,
            folds: Optional[np.ndarray] = None,
            folds_dir: Path = FOLDS_DIR) -> pd.DataFrame:
    """Corre los 5 folds y devuelve una fila por fold con las columnas del contrato.

    ``funcion``, ``datos`` y ``folds`` existen para los tests; en uso normal
    se dejan en None y se leen de src/models, data/processed y data/folds.
    """
    params = dict(params or {})
    fn = funcion or _funcion_modelo(modelo)
    X, y_train_all, y_eval_all, ids = datos or cargar_escenario(escenario, rasgo)
    if folds is None:
        folds = cargar_folds(escenario, ids, base=folds_dir)
    folds = np.asarray(folds)
    if len(folds) != len(X):
        raise ValueError(f"Hay {len(folds)} folds para {len(X)} animales")

    filas = []
    for k in range(1, K_FOLDS + 1):
        test = folds == k
        inicio = time.perf_counter()
        pred = np.asarray(fn(X[~test], y_train_all[~test], X[test], **params),
                          dtype=np.float64).ravel()
        segundos = time.perf_counter() - inicio
        if pred.shape != (int(test.sum()),):
            raise ValueError(f"[{modelo}] fold {k}: devolvio {pred.shape} predicciones, "
                             f"se esperaban {int(test.sum())}")
        if not np.isfinite(pred).all():
            raise ValueError(f"[{modelo}] fold {k}: hay NaN o infinitos en las predicciones")
        filas.append({
            "modelo": modelo,
            "rasgo": rasgo,
            "escenario_n": len(ids),
            "ruido": ruido,
            "fold": k,
            "r_pearson": round(r_pearson(y_eval_all[test], pred), 6),
            "rmse": round(rmse(y_eval_all[test], pred), 6),
            "tiempo_s": round(segundos, 3),
        })
    return pd.DataFrame(filas, columns=COLUMNAS)


def guardar_parcial(tabla: pd.DataFrame, escenario: str,
                    results_dir: Path = RESULTS_DIR) -> Path:
    """Escribe results/parciales/<modelo>__<escenario>__<rasgo>__<ruido>.csv."""
    if list(tabla.columns) != COLUMNAS:
        raise ValueError(f"Columnas {list(tabla.columns)}; el contrato es {COLUMNAS}")
    fila = tabla.iloc[0]
    carpeta = Path(results_dir) / "parciales"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{fila['modelo']}__{escenario}__{fila['rasgo']}__{fila['ruido']}.csv"
    tabla.to_csv(ruta, index=False)
    return ruta


def consolidar(results_dir: Path = RESULTS_DIR) -> pd.DataFrame:
    """Junta results/parciales/*.csv en results/resultados.csv."""
    results_dir = Path(results_dir)
    partes = [pd.read_csv(p) for p in sorted((results_dir / "parciales").glob("*.csv"))]
    for parte in partes:
        if list(parte.columns) != COLUMNAS:
            raise ValueError(f"Un parcial no cumple el contrato: {list(parte.columns)}")
    tabla = (pd.concat(partes, ignore_index=True) if partes
             else pd.DataFrame(columns=COLUMNAS))
    tabla = tabla.sort_values(["modelo", "rasgo", "escenario_n", "ruido", "fold"],
                              ignore_index=True)
    tabla.to_csv(results_dir / "resultados.csv", index=False)
    return tabla


def _leer_params(pares: Sequence[str]) -> dict:
    params = {}
    for par in pares:
        clave, _, valor = par.partition("=")
        if not clave or not _:
            raise ValueError(f"Parametro mal escrito: '{par}' (usa clave=valor)")
        for tipo in (int, float):
            try:
                params[clave] = tipo(valor)
                break
            except ValueError:
                continue
        else:
            params[clave] = valor
    return params


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Validacion cruzada comun de BOVIGEN")
    parser.add_argument("--modelo", help="nombre del archivo en src/models/, sin .py")
    parser.add_argument("--escenario", help="holstein, sim_n125, sim_n500 o sim_n2000")
    parser.add_argument("--rasgo", help="holstein: mkg/fpro/scs · simulaciones: fenotipo")
    parser.add_argument("--ruido", default="base")
    parser.add_argument("--param", action="append", default=[], help="clave=valor (repetible)")
    parser.add_argument("--consolidar", action="store_true",
                        help="junta los parciales en results/resultados.csv")
    args = parser.parse_args(argv)

    if args.modelo:
        if not (args.escenario and args.rasgo):
            parser.error("--modelo necesita --escenario y --rasgo")
        tabla = evaluar(args.modelo, args.escenario, args.rasgo, args.ruido,
                        _leer_params(args.param))
        ruta = guardar_parcial(tabla, args.escenario)
        print(tabla.to_string(index=False))
        print(f"\nr medio: {tabla['r_pearson'].mean():.3f}  ->  {ruta.relative_to(PROJECT_ROOT)}")
    if args.consolidar:
        total = consolidar()
        print(f"results/resultados.csv: {len(total)} filas")
    if not (args.modelo or args.consolidar):
        parser.print_help()


if __name__ == "__main__":
    main()
