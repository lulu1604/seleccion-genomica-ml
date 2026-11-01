"""Tests del modulo de vision (usan solo las fotos de data/sample)."""
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from PIL import Image

from src.data.imagenes import enderezar_posterior
from src.vision import entrenar
from src.vision.cnn import N_SALIDAS, construir, extraer_features
from src.vision.dataset import (MEDIDAS, FotosBovinos, asignar_folds,
                                cargar_indice)
from src.vision.silueta import N_GEOMETRIA, geometria, limpiar

RAIZ = Path(__file__).resolve().parents[1]
INDICE_MUESTRA = RAIZ / "data" / "sample" / "imagenes_index_sample.csv"


def segmentar_falso(img):
    """Sustituto de rembg para los tests: pixeles mas claros que la media."""
    g = np.asarray(img.convert("L"), dtype=float)
    return g > g.mean()


def _indice_sintetico(tmp_path, n=10):
    """n animales falsos: reutiliza las 6 fotos de muestra con medidas inventadas."""
    base = pd.read_csv(INDICE_MUESTRA, dtype={"id_animal_img": str})
    rng = np.random.default_rng(0)
    filas = []
    for i in range(n):
        origen = base.iloc[i % len(base)]
        lat, pos = tmp_path / f"{i}_lat.jpg", tmp_path / f"{i}_pos.jpg"
        shutil.copy(RAIZ / origen["ruta_lateral"], lat)
        shutil.copy(RAIZ / origen["ruta_posterior"], pos)
        filas.append({
            "id_animal_img": str(i), "ruta_lateral": lat.name, "ruta_posterior": pos.name,
            "peso_kg": 450 + rng.normal(0, 40), "altura_cruz_cm": 120 + rng.normal(0, 5),
            "perimetro_toracico_cm": 185 + rng.normal(0, 8),
            "largo_oblicuo_cm": 155 + rng.normal(0, 8),
            "longitud_cadera_cm": 44 + rng.normal(0, 3),
        })
    ruta = tmp_path / "indice.csv"
    pd.DataFrame(filas).to_csv(ruta, index=False)
    return ruta


# ------------------------------------------------------------- datos

def test_cargar_indice_renombra_cadera_y_resuelve_rutas():
    tabla = cargar_indice(INDICE_MUESTRA, RAIZ)
    assert len(tabla) == 3
    assert list(tabla.columns[-5:]) == MEDIDAS      # el orden de las 5 salidas
    assert "longitud_cadera_cm" not in tabla.columns
    assert tabla["ruta_lateral"].map(Path.exists).all()


def test_cargar_indice_falla_si_faltan_fotos(tmp_path):
    ruta = _indice_sintetico(tmp_path, n=5)
    (tmp_path / "0_lat.jpg").unlink()
    with pytest.raises(FileNotFoundError):
        cargar_indice(ruta, tmp_path)


def test_folds_por_animal_balanceados_y_reproducibles():
    ids = [str(i) for i in range(72)]
    f1, f2 = asignar_folds(ids), asignar_folds(ids)
    assert (f1 == f2).all()                          # misma semilla -> mismos folds
    assert set(f1) == {1, 2, 3, 4, 5}
    assert sorted(np.bincount(f1)[1:]) == [14, 14, 14, 15, 15]
    assert len(f1) == len(ids)                       # un fold por animal (no por foto)


def test_enderezar_posterior_gira_solo_las_horizontales():
    horizontal = Image.new("RGB", (40, 30))
    horizontal.putpixel((0, 0), (255, 0, 0))         # esquina superior izquierda
    derecha = enderezar_posterior(horizontal)
    assert derecha.size == (30, 40)
    assert derecha.getpixel((29, 0)) == (255, 0, 0)  # giro horario: pasa arriba a la derecha
    vertical = Image.new("RGB", (30, 40))
    assert enderezar_posterior(vertical) is vertical


def test_item_del_dataset_tiene_las_formas_esperadas():
    tabla = cargar_indice(INDICE_MUESTRA, RAIZ)
    y = tabla[MEDIDAS].to_numpy(dtype=np.float32)
    ds = FotosBovinos(tabla, y.mean(axis=0), y.std(axis=0))
    lat, pos, medidas = ds[0]
    assert lat.shape == pos.shape == (3, 224, 224)
    assert medidas.shape == (N_SALIDAS,)
    assert len(ds) == 3


# ------------------------------------------------------------- silueta

def test_geometria_de_un_rectangulo():
    m = np.zeros((100, 200), dtype=bool)
    m[20:70, 50:150] = True                          # 50 de alto, 100 de ancho
    g = geometria(m)
    assert g.shape == (N_GEOMETRIA,)
    assert g[0] == pytest.approx(0.25)               # area
    assert g[1] == pytest.approx(0.5)                # alto / alto de la foto
    assert g[2] == pytest.approx(0.5)                # ancho / ancho de la foto
    assert g[4] == pytest.approx(1.0)                # llena toda su caja


def test_limpiar_descarta_manchas_chicas_y_rellena_huecos():
    m = np.zeros((50, 50), dtype=bool)
    m[10:40, 10:30] = True
    m[20:25, 15:20] = False                          # hueco
    m[2:5, 45:48] = True                             # "persona" suelta
    limpia = limpiar(m)
    assert limpia[22, 17] and not limpia[3, 46]
    with pytest.raises(ValueError):
        limpiar(np.zeros((5, 5), dtype=bool))


# ------------------------------------------------------------- redes

def test_red_devuelve_5_salidas_y_congela_el_backbone():
    red = construir(preentrenada=False, congelar_backbone=True)
    lat = torch.zeros(2, 3, 224, 224)
    assert red(lat, lat).shape == (2, N_SALIDAS)
    entrenables = [n for n, p in red.named_parameters() if p.requires_grad]
    assert entrenables and all(n.startswith("cabeza") for n in entrenables)


def test_extraer_features_une_las_dos_vistas():
    x = torch.zeros(3, 3, 224, 224)
    F = extraer_features(x, x, preentrenada=False)
    assert F.shape == (3, 2 * 1280)
    assert np.isfinite(F).all()


# ------------------------------------------------------------- entrenamiento

def test_ensamble_entrega_una_fila_por_medida(tmp_path):
    ruta = _indice_sintetico(tmp_path)
    promedio, detalle, pred = entrenar.correr(ruta, tmp_path, n_folds=5, preentrenada=False,
                                              verbose=False, segmentar=segmentar_falso)
    assert list(promedio.columns) == entrenar.COLUMNAS_SALIDA
    assert promedio["medida"].tolist() == MEDIDAS
    assert np.isfinite(promedio[["rmse", "mae"]].to_numpy()).all()
    assert sorted(detalle["fold"].unique()) == [1, 2, 3, 4, 5]
    assert len(list((tmp_path / "data/processed/mascaras").glob("*.png"))) == 20
    # cada animal aparece una sola vez, con la prediccion de su fold de test
    assert pred["id_animal_img"].tolist() == [str(i) for i in range(10)]
    assert sorted(pred["fold"].unique()) == [1, 2, 3, 4, 5]
    assert [f"{m}_pred" for m in MEDIDAS] == [c for c in pred.columns if c.endswith("_pred")]


def test_ensamble_no_mira_las_medidas_del_test(tmp_path):
    """Cambiar las medidas de los animales de test no debe cambiar su prediccion."""
    tabla = cargar_indice(_indice_sintetico(tmp_path, n=15), tmp_path)
    folds = asignar_folds(tabla["id_animal_img"])
    features = entrenar.features_ensamble(tabla, tmp_path / "m", segmentar_falso, preentrenada=False)
    _, pred1, _ = entrenar.ensamble_fold(tabla, folds, 1, features)
    alterada = tabla.copy()
    alterada.loc[folds == 1, MEDIDAS] *= 10
    _, pred2, _ = entrenar.ensamble_fold(alterada, folds, 1, features)
    np.testing.assert_allclose(pred1, pred2)


def test_cnn_base_sigue_funcionando(tmp_path):
    ruta = _indice_sintetico(tmp_path)
    promedio, _, pred = entrenar.correr(ruta, tmp_path, metodo="cnn", solo_fold=2, epocas=1,
                                        lote=4, preentrenada=False, verbose=False)
    assert promedio["medida"].tolist() == MEDIDAS
    assert len(pred) == 2 and (pred["fold"] == 2).all()   # 10 animales / 5 folds


def test_cli_escribe_los_dos_csv(tmp_path):
    ruta = _indice_sintetico(tmp_path)
    tabla = cargar_indice(ruta, tmp_path)
    entrenar.features_ensamble(tabla, tmp_path / "masc", segmentar_falso, preentrenada=False)
    salida = tmp_path / "vision" / "metricas_cnn.csv"
    entrenar.main(["--indice", str(ruta), "--raiz", str(tmp_path), "--mascaras", "masc",
                   "--sin-preentrenar", "--salida", str(salida)])
    assert list(pd.read_csv(salida).columns) == ["medida", "rmse", "mae", "r_pearson"]
    detalle = pd.read_csv(tmp_path / "vision" / "metricas_cnn_folds.csv")
    assert sorted(detalle["fold"].unique()) == [1, 2, 3, 4, 5]
    assert "rmse_base" in detalle.columns
    pred = pd.read_csv(tmp_path / "vision" / "predicciones_cnn.csv")
    assert len(pred) == 10 and "peso_kg_real" in pred.columns
