"""Silueta de la vaca: segmentacion con rembg (U2-Net) y medidas geometricas.

La silueta aporta lo que la CNN pierde al promediar sus mapas: que tan alta,
larga y ancha aparece la vaca en la foto. Las mascaras se guardan en
data/processed/mascaras/ (no se suben al repo) para no recalcularlas.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

VISTAS = {"lat": "ruta_lateral", "pos": "ruta_posterior"}
N_GEOMETRIA = 23  # medidas por vista


@lru_cache(maxsize=1)
def segmentador_rembg(modelo: str = "u2net"):
    """Funcion foto(PIL) -> mascara booleana. La sesion se crea una sola vez
    por proceso y se reutiliza.

    La primera vez rembg descarga U2-Net (~176 MB) desde GitHub, por defecto a
    ~/.rembg/models/u2net/u2net.onnx. Para no descargarlo (p. ej. en Docker),
    copiar u2net.onnx a una carpeta y definir U2NET_HOME=<esa carpeta>."""
    from rembg import new_session, remove  # import aqui: los tests no lo necesitan
    sesion = new_session(modelo)
    return lambda img: np.asarray(remove(img, session=sesion, only_mask=True)) > 127


def limpiar(m: np.ndarray) -> np.ndarray:
    """Se queda con la mancha mas grande (descarta personas sueltas) y rellena huecos."""
    etiquetas, n = ndimage.label(m)
    if n == 0:
        raise ValueError("La mascara esta vacia: no se encontro la vaca")
    if n > 1:
        tam = ndimage.sum(m, etiquetas, range(1, n + 1))
        m = etiquetas == (np.argmax(tam) + 1)
    return ndimage.binary_fill_holes(m)


def geometria(m: np.ndarray) -> np.ndarray:
    """23 medidas de la silueta, como fraccion del tamano de la foto."""
    H, W = m.shape
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    alto, ancho = (y1 - y0 + 1) / H, (x1 - x0 + 1) / W
    caja = m[y0:y1 + 1, x0:x1 + 1]
    alto_col = caja.sum(0) / H     # alto de la silueta en cada columna
    ancho_fila = caja.sum(1) / W   # ancho de la silueta en cada fila

    def pct(p, s):
        return np.percentile(s[s > 0], p)

    def en(frac, s):  # valor del perfil a cierta fraccion de la caja
        return s[min(int(frac * len(s)), len(s) - 1)]

    f = [m.mean(), alto, ancho, ancho / alto, caja.mean(),
         ys.mean() / H, xs.mean() / W, y0 / H, y1 / H,
         pct(50, alto_col), pct(90, alto_col), pct(50, ancho_fila), pct(90, ancho_fila)]
    f += [en(t, ancho_fila) for t in (0.1, 0.25, 0.4, 0.55, 0.7)]
    f += [en(t, alto_col) for t in (0.2, 0.35, 0.5, 0.65, 0.8)]
    return np.array(f, dtype=np.float64)


def mascara(ruta_foto: Path, ruta_cache: Path, segmentar) -> np.ndarray:
    if ruta_cache.exists():
        return np.asarray(Image.open(ruta_cache)) > 127
    with Image.open(ruta_foto) as img:
        m = segmentar(img.convert("RGB"))
    ruta_cache.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((m * 255).astype(np.uint8)).save(ruta_cache)
    return m


def features_geometria(tabla, carpeta_cache, segmentar=None) -> np.ndarray:
    """(animales, 46): geometria de la vista lateral y de la posterior."""
    carpeta_cache = Path(carpeta_cache)
    filas = []
    for _, fila in tabla.iterrows():
        partes = []
        for vista, col in VISTAS.items():
            cache = carpeta_cache / f"{fila['id_animal_img']}_{vista}.png"
            if segmentar is None and not cache.exists():
                segmentar = segmentador_rembg()
            partes.append(geometria(limpiar(mascara(Path(fila[col]), cache, segmentar))))
        filas.append(np.concatenate(partes))
    return np.vstack(filas)
