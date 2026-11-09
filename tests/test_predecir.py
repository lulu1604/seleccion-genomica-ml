"""Tests de predecir() para el dashboard.

No usan models/ (no esta en el repo) ni descargan U2-Net: entrenan un mini
modelo con las 3 fotos de data/sample y un segmentador falso.
"""
from pathlib import Path

import joblib
import numpy as np
import pytest
from PIL import Image

from src.vision import entrenar, predecir
from src.vision.dataset import MEDIDAS, cargar_indice

RAIZ = Path(__file__).resolve().parents[1]
MUESTRA = RAIZ / "data" / "sample" / "imagenes"
INDICE_MUESTRA = RAIZ / "data" / "sample" / "imagenes_index_sample.csv"


def segmentar_falso(img):
    """Sustituto de rembg: pixeles mas claros que la media."""
    g = np.asarray(img.convert("L"), dtype=float)
    return g > g.mean()


def segmentar_vacio(img):
    return np.zeros((img.height, img.width), dtype=bool)


@pytest.fixture
def ruta_modelo(tmp_path):
    """Mini modelo con los 3 animales de muestra, guardado en tmp_path."""
    metricas = tmp_path / "metricas_cnn.csv"
    metricas.write_text("medida,rmse,mae,r_pearson\n"
                        + "".join(f"{m},1.5,1.0,0.3\n" for m in MEDIDAS))
    tabla = cargar_indice(INDICE_MUESTRA, RAIZ)
    paquete = entrenar.entrenar_final(tabla, tmp_path / "masc", metricas,
                                      segmentar=segmentar_falso, preentrenada=False)
    return entrenar.guardar_modelo(paquete, tmp_path / "models" / "ensamble.joblib")


def test_entrenar_final_guarda_el_paquete(ruta_modelo):
    paquete = joblib.load(ruta_modelo)
    assert set(paquete["modelos"]) == {"cnn", "geometria"}
    assert paquete["medidas"] == MEDIDAS
    assert paquete["n_animales"] == 3
    assert len(paquete["media"]) == len(paquete["desv"]) == 5


def test_predecir_devuelve_5_medidas_finitas(ruta_modelo):
    r = predecir.predecir(MUESTRA / "1_lat.jpg", MUESTRA / "1_pos.jpg", ruta_modelo,
                          segmentar=segmentar_falso)
    assert all(np.isfinite(r[m]) for m in MEDIDAS)
    assert r["error"] == {m: 1.5 for m in MEDIDAS}


def test_predecir_sin_vaca_da_error_claro(ruta_modelo):
    with pytest.raises(ValueError, match="No se encontro la vaca en la foto lateral"):
        predecir.predecir(MUESTRA / "1_lat.jpg", MUESTRA / "1_pos.jpg", ruta_modelo,
                          segmentar=segmentar_vacio)


def test_enderezar_solo_si_se_pide(tmp_path):
    foto = Image.new("RGB", (400, 300), "white")
    foto.paste((255, 0, 0), (0, 0, 100, 100))      # bloque rojo arriba a la izquierda
    ruta = tmp_path / "horizontal.jpg"
    foto.save(ruta)
    rojo = lambda img, x, y: img.getpixel((x, y))[0] > 200 and img.getpixel((x, y))[1] < 80
    igual = predecir.preparar_foto(ruta, posterior=True, enderezar=False)
    girada = predecir.preparar_foto(ruta, posterior=True, enderezar=True)
    assert igual.size == girada.size == (224, 224)
    assert rojo(igual, 10, 10) and not rojo(igual, 213, 10)
    assert rojo(girada, 213, 10) and not rojo(girada, 10, 10)   # giro horario


def test_predecir_sin_modelo_avisa_como_entrenarlo(tmp_path):
    with pytest.raises(FileNotFoundError, match="--final"):
        predecir.predecir(MUESTRA / "1_lat.jpg", MUESTRA / "1_pos.jpg",
                          tmp_path / "no_existe.joblib", segmentar=segmentar_falso)
