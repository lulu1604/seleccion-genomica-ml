"""Mide una vaca nueva desde sus dos fotos (lo usa el dashboard).

    python -m src.vision.predecir --lateral foto_costado.jpg --posterior foto_atras.jpg

Antes hay que entrenar y guardar el modelo final (una sola vez):

    python -m src.vision.entrenar --final

Hace con la foto nueva los mismos pasos que con las fotos de entrenamiento:
foto a 224x224 -> features de MobileNetV2 + geometria de la silueta -> los dos
Ridge -> promedio -> cm y kg. Devuelve tambien el error esperado de cada
medida: el RMSE de la validacion cruzada (results/vision/metricas_cnn.csv).
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from src.data.imagenes import TAMANO_SALIDA, enderezar_posterior
from src.vision.cnn import extraer_features
from src.vision.dataset import _foto_a_tensor
from src.vision.silueta import geometria, limpiar, segmentador_rembg

RUTA_MODELO = "models/vision/ensamble.joblib"
COMO_TOMARLA = {"lateral": "de costado", "posterior": "desde atras"}


@lru_cache(maxsize=4)
def cargar_modelo(ruta: str) -> dict:
    """Lee el .joblib una sola vez por proceso."""
    import joblib

    if not Path(ruta).exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Entrenalo con: python -m src.vision.entrenar --final")
    return joblib.load(ruta)


def preparar_foto(ruta, posterior: bool = False, enderezar: bool = False) -> Image.Image:
    """Abre la foto igual que src/data/imagenes.py: RGB y 224x224.

    `exif_transpose` aplica la rotacion que guardan los celulares. La regla de
    `enderezar_posterior` ("horizontal -> girar") es propia del dataset de
    Mongolia: una foto nueva tomada en horizontal puede estar bien, asi que
    solo se aplica si se pide (`enderezar=True`, para fotos de ese dataset).
    """
    with Image.open(ruta) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
    if posterior and enderezar:
        img = enderezar_posterior(img)
    return img.resize(TAMANO_SALIDA)


def _silueta(img: Image.Image, vista: str, segmentar) -> np.ndarray:
    m = segmentar(img)
    if not np.any(m):
        raise ValueError(f"No se encontro la vaca en la foto {vista}. Usa una foto "
                         f"con el animal entero y {COMO_TOMARLA[vista]}.")
    return geometria(limpiar(m))


def predecir(ruta_lateral, ruta_posterior, ruta_modelo=RUTA_MODELO,
             enderezar: bool = False, segmentar=None) -> dict:
    """Estima las 5 medidas de una vaca a partir de sus dos fotos.

    Devuelve {medida: valor, ..., "error": {medida: rmse}} en cm y kg.
    `segmentar` solo se cambia en los tests; por defecto se usa U2-Net (rembg).
    """
    paquete = cargar_modelo(str(ruta_modelo))
    segmentar = segmentar or segmentador_rembg()
    lateral = preparar_foto(ruta_lateral)
    posterior = preparar_foto(ruta_posterior, posterior=True, enderezar=enderezar)

    X = {
        "cnn": extraer_features(_foto_a_tensor(lateral)[None], _foto_a_tensor(posterior)[None],
                                preentrenada=paquete["preentrenada"]),
        "geometria": np.concatenate([_silueta(lateral, "lateral", segmentar),
                                     _silueta(posterior, "posterior", segmentar)])[None],
    }
    y_norm = np.mean([modelo.predict(X[k]) for k, modelo in paquete["modelos"].items()], axis=0)
    y = y_norm[0] * paquete["desv"] + paquete["media"]
    resultado = {m: round(float(v), 1) for m, v in zip(paquete["medidas"], y)}
    resultado["error"] = dict(paquete["error"])
    return resultado


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lateral", required=True, help="Foto de costado")
    p.add_argument("--posterior", required=True, help="Foto desde atras")
    p.add_argument("--modelo", default=RUTA_MODELO)
    p.add_argument("--enderezar", action="store_true",
                   help="Girar la posterior si viene horizontal (solo fotos del dataset original)")
    a = p.parse_args(argv)
    print(json.dumps(predecir(a.lateral, a.posterior, a.modelo, a.enderezar),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
