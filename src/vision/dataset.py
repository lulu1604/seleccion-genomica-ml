"""Dataset de fotos de bovinos para la CNN de medidas corporales.

Lee results/imagenes_index.csv (lo genera src/data/imagenes.py) y entrega, por
animal, la foto lateral, la foto posterior y las 5 medidas a predecir.

Este modulo es independiente del genomico: no usa SNPs, ni src/models/, ni los
folds de data/folds/ (esos son por parentesco genomico y estos animales no
tienen genotipo).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import Dataset

# Orden fijo de las 5 salidas de la red (y de las filas de metricas_cnn.csv).
MEDIDAS = [
    "largo_oblicuo_cm",
    "altura_cruz_cm",
    "perimetro_toracico_cm",
    "largo_cadera_cm",
    "peso_kg",
]

# El indice de imagenes.py llama "longitud_cadera_cm" a lo que el contrato del
# dashboard llama "largo_cadera_cm". Se renombra aqui, en un solo lugar.
RENOMBRE_INDICE = {"longitud_cadera_cm": "largo_cadera_cm"}

# Normalizacion de ImageNet: la ResNet18 preentrenada espera estos valores.
MEDIA_IMAGENET = np.array([0.485, 0.456, 0.406], dtype=np.float32)
DESV_IMAGENET = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def cargar_indice(ruta_indice: str | Path, raiz: str | Path = ".") -> pd.DataFrame:
    """Lee el indice y resuelve las rutas de las fotos contra `raiz`.

    Devuelve una fila por animal con: id_animal_img (texto), ruta_lateral,
    ruta_posterior (Path) y las 5 columnas de MEDIDAS.
    """
    df = pd.read_csv(ruta_indice, dtype={"id_animal_img": str})
    df = df.rename(columns=RENOMBRE_INDICE)
    faltan = [c for c in ["id_animal_img", "ruta_lateral", "ruta_posterior", *MEDIDAS]
              if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en {ruta_indice}: {faltan}")
    if df["id_animal_img"].duplicated().any():
        raise ValueError("Hay id_animal_img repetidos en el indice")
    if df[MEDIDAS].isna().any().any():
        raise ValueError("Hay medidas vacias en el indice")

    raiz = Path(raiz)
    for col in ("ruta_lateral", "ruta_posterior"):
        df[col] = [raiz / r for r in df[col]]
        inexistentes = [str(r) for r in df[col] if not r.exists()]
        if inexistentes:
            raise FileNotFoundError(
                f"No existen {len(inexistentes)} fotos de '{col}', por ejemplo "
                f"{inexistentes[0]}. Corre src/data/imagenes.py para generarlas."
            )
    return df[["id_animal_img", "ruta_lateral", "ruta_posterior", *MEDIDAS]].reset_index(drop=True)


def asignar_folds(ids, n_folds: int = 5, semilla: int = 2026) -> np.ndarray:
    """Un fold (1..n_folds) por ANIMAL: sus dos fotos caen siempre juntas.

    Se mezclan los animales con la semilla y se reparten en orden, asi los
    folds quedan balanceados (72 animales -> 15,15,14,14,14) y reproducibles.
    """
    n = len(ids)
    if n < n_folds:
        raise ValueError(f"Hay {n} animales, no alcanzan para {n_folds} folds")
    orden = np.random.default_rng(semilla).permutation(n)
    folds = np.empty(n, dtype=int)
    folds[orden] = np.arange(n) % n_folds + 1
    return folds


def _foto_a_tensor(ruta: Path) -> torch.Tensor:
    """Foto 224x224 -> tensor float (3, 224, 224) normalizado como ImageNet."""
    with Image.open(ruta) as img:
        a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    a = (a - MEDIA_IMAGENET) / DESV_IMAGENET
    return torch.from_numpy(a.transpose(2, 0, 1).copy())


class FotosBovinos(Dataset):
    """Cada item = un animal: (foto_lateral, foto_posterior, medidas_normalizadas).

    Las medidas se normalizan con la media y desviacion que se le pasen (las del
    TRAIN); asi las 5 salidas pesan parecido en la perdida aunque el peso este en
    kg (~500) y las medidas en cm (~50-190).
    """

    def __init__(self, tabla: pd.DataFrame, media: np.ndarray, desv: np.ndarray):
        self.ids = tabla["id_animal_img"].tolist()
        # 72 animales x 2 fotos de 224x224 caben de sobra en memoria.
        self.lateral = [_foto_a_tensor(r) for r in tabla["ruta_lateral"]]
        self.posterior = [_foto_a_tensor(r) for r in tabla["ruta_posterior"]]
        y = tabla[MEDIDAS].to_numpy(dtype=np.float32)
        self.y = torch.from_numpy((y - media) / desv)

    def __len__(self) -> int:
        return len(self.ids)

    def __getitem__(self, i: int):
        return self.lateral[i], self.posterior[i], self.y[i]
