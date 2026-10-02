"""Loader de las poblaciones simuladas con AlphaSimR.

Expone la misma interfaz que ``load_holstein.cargar``:

    X, y, ids = cargar("sim_n500", target="fenotipo")

Los archivos los genera ``src/data/simular.R``. No se versionan: viven en
``data/processed/sim_n<N>/`` y se reproducen corriendo el script.

A diferencia del dataset real, aquí se conoce el valor genetico verdadero de
cada animal (columna ``valor_gv``), porque es una simulacion. Sirve como
referencia exacta para evaluar los modelos.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

VALID_TARGETS = ("fenotipo", "valor_gv")
ID_COL = "id_animal"
PATRON_ESCENARIO = re.compile(r"^sim_n\d+$")


def listar_escenarios() -> list[str]:
    """Escenarios disponibles en disco, por ejemplo ['sim_n125', 'sim_n500']."""
    if not PROCESSED_DIR.exists():
        return []
    escenarios = [d.name for d in PROCESSED_DIR.iterdir()
                  if d.is_dir() and PATRON_ESCENARIO.match(d.name)]
    return sorted(escenarios, key=lambda nombre: int(nombre.split("_n")[1]))


def _rutas(escenario: str) -> tuple[Path, Path]:
    if not PATRON_ESCENARIO.match(escenario):
        raise ValueError(
            f"Escenario invalido: '{escenario}'. Debe tener la forma 'sim_n<N>', "
            f"por ejemplo 'sim_n500'. Disponibles: {listar_escenarios()}"
        )
    carpeta = PROCESSED_DIR / escenario
    return carpeta / "X_sim.csv", carpeta / "y_sim.csv"


def _verificar_existen(x_path: Path, y_path: Path, escenario: str) -> None:
    faltan = [str(p) for p in (x_path, y_path) if not p.exists()]
    if faltan:
        raise FileNotFoundError(
            f"No se encontraron los archivos del escenario '{escenario}': {faltan}\n"
            "Genera los datos primero:\n"
            "  Rscript src/data/simular.R\n"
            f"Escenarios disponibles ahora: {listar_escenarios()}"
        )


def _validar(X_df: pd.DataFrame, y_df: pd.DataFrame, escenario: str) -> list[str]:
    """Valida esquema, tipos, rango y alineacion. Devuelve los ids."""
    if X_df.columns[0] != ID_COL:
        raise RuntimeError(
            f"[{escenario}] La primera columna de X_sim.csv debe ser '{ID_COL}', "
            f"y es '{X_df.columns[0]}'"
        )
    if list(y_df.columns) != [ID_COL, *VALID_TARGETS]:
        raise RuntimeError(
            f"[{escenario}] Columnas inesperadas en y_sim.csv: {list(y_df.columns)}; "
            f"se esperaba {[ID_COL, *VALID_TARGETS]}"
        )
    if len(X_df) != len(y_df):
        raise RuntimeError(
            f"[{escenario}] X tiene {len(X_df)} filas y y tiene {len(y_df)}"
        )
    if len(X_df) == 0 or X_df.shape[1] < 2:
        raise RuntimeError(f"[{escenario}] X_sim.csv no tiene datos")

    genotipos = X_df.drop(columns=ID_COL)
    if genotipos.isna().to_numpy().any():
        raise RuntimeError(f"[{escenario}] X_sim.csv contiene valores faltantes")
    if not all(pd.api.types.is_numeric_dtype(genotipos[c]) for c in genotipos.columns):
        raise RuntimeError(f"[{escenario}] X_sim.csv contiene columnas no numericas")
    valores = genotipos.to_numpy()
    if valores.min() < 0 or valores.max() > 2:
        raise RuntimeError(
            f"[{escenario}] X_sim.csv tiene genotipos fuera de {{0, 1, 2}} "
            f"(min={valores.min()}, max={valores.max()})"
        )

    if y_df.isna().to_numpy().any():
        raise RuntimeError(f"[{escenario}] y_sim.csv contiene valores faltantes")
    if not all(pd.api.types.is_numeric_dtype(y_df[t]) for t in VALID_TARGETS):
        raise RuntimeError(f"[{escenario}] los targets de y_sim.csv deben ser numericos")

    ids_x = X_df[ID_COL].astype(str).tolist()
    ids_y = y_df[ID_COL].astype(str).tolist()
    if len(set(ids_x)) != len(ids_x):
        raise RuntimeError(f"[{escenario}] X_sim.csv tiene id_animal duplicados")
    if ids_x != ids_y:
        raise RuntimeError(
            f"[{escenario}] Los id_animal de X_sim.csv y y_sim.csv no coinciden "
            "en valor u orden"
        )
    return ids_x


def cargar(escenario: str, target: Optional[str] = "fenotipo",
           as_numpy: bool = True) -> tuple:
    """Devuelve (X, y, ids) validados para un escenario simulado.

    X   -> matriz numerica (animales x SNPs), sin la columna id_animal
    y   -> vector 1-D del target; si ``target`` es None, el DataFrame completo
    ids -> lista de id_animal en el mismo orden que las filas de X
    """
    if target is not None and target not in VALID_TARGETS:
        raise ValueError(
            f"Target invalido: '{target}'. Debe ser uno de {VALID_TARGETS}"
        )

    x_path, y_path = _rutas(escenario)
    _verificar_existen(x_path, y_path, escenario)

    X_df = pd.read_csv(x_path)
    y_df = pd.read_csv(y_path)
    ids = _validar(X_df, y_df, escenario)

    genotipos = X_df.drop(columns=ID_COL)
    X = genotipos.to_numpy(dtype=np.uint8) if as_numpy else genotipos
    y = y_df[target].to_numpy() if target is not None else y_df
    return X, y, ids


if __name__ == "__main__":
    disponibles = listar_escenarios()
    print(f"Escenarios disponibles: {disponibles}")
    for esc in disponibles:
        X, y, ids = cargar(esc)
        print(f"{esc}: X={X.shape} y={y.shape} ids={len(ids)} primeros={ids[:2]}")
