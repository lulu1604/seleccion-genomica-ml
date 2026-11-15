"""Lectura de los CSV del dashboard (solo lectura, sin BD).

Si el archivo real no existe o solo tiene encabezado, se usa el de prueba
de data/sample/ y se marca como demo.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

# nombre -> (ruta real, ruta demo), relativas a la raíz
FUENTES = {
    "resultados": ("results/resultados.csv", "data/sample/resultados_demo.csv"),
    "shap": ("results/shap_top_snp.csv", "data/sample/shap_demo.csv"),
    "vision": ("results/vision/metricas_cnn.csv", "data/sample/vision_demo.csv"),
}

CLAVES_RESUMEN = ["modelo", "rasgo", "escenario_n", "ruido"]


def raiz() -> Path:
    """Raíz de los datos: BOVIGEN_RAIZ si existe, si no la raíz del repo."""
    if "BOVIGEN_RAIZ" in os.environ:
        return Path(os.environ["BOVIGEN_RAIZ"])
    return Path(__file__).resolve().parents[3]


def _leer_si_tiene_filas(ruta: Path) -> pd.DataFrame | None:
    if not ruta.is_file():
        return None
    df = pd.read_csv(ruta)
    return df if len(df) > 0 else None


def leer(nombre: str) -> tuple[pd.DataFrame, bool]:
    """Devuelve (df, es_demo) para una de las fuentes de FUENTES."""
    real, demo = FUENTES[nombre]
    df = _leer_si_tiene_filas(raiz() / real)
    if df is not None:
        return df, False
    ruta_demo = raiz() / demo
    if not ruta_demo.is_file():
        raise FileNotFoundError(
            f"No hay datos para '{nombre}': falta {real} y también el demo {demo}. "
            "Corre: python dashboard/backend/crear_demo.py"
        )
    return pd.read_csv(ruta_demo), True


def a_registros(df: pd.DataFrame) -> list[dict]:
    """Lista de dicts lista para JSON, con NaN convertido a None."""
    limpio = df.astype(object).replace({np.nan: None})
    return limpio.to_dict(orient="records")


def resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Media, desviación muestral y n de folds por modelo y escenario."""
    agrupado = df.groupby(CLAVES_RESUMEN, as_index=False).agg(
        r_medio=("r_pearson", "mean"),
        r_desv=("r_pearson", lambda s: s.std(ddof=1)),
        rmse_medio=("rmse", "mean"),
        n_folds=("fold", "count"),
    )
    return agrupado.round(4)
