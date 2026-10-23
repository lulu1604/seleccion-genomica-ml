"""Tests de la CNN de medidas corporales (usan solo las fotos de data/sample)."""
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from src.vision import entrenar
from src.vision.cnn import N_SALIDAS, construir
from src.vision.dataset import (MEDIDAS, FotosBovinos, asignar_folds,
                                cargar_indice)

RAIZ = Path(__file__).resolve().parents[1]
INDICE_MUESTRA = RAIZ / "data" / "sample" / "imagenes_index_sample.csv"


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


def test_item_del_dataset_tiene_las_formas_esperadas():
    tabla = cargar_indice(INDICE_MUESTRA, RAIZ)
    y = tabla[MEDIDAS].to_numpy(dtype=np.float32)
    ds = FotosBovinos(tabla, y.mean(axis=0), y.std(axis=0))
    lat, pos, medidas = ds[0]
    assert lat.shape == pos.shape == (3, 224, 224)
    assert medidas.shape == (N_SALIDAS,)
    assert len(ds) == 3


def test_red_devuelve_5_salidas_y_congela_el_backbone():
    red = construir(preentrenada=False, congelar_backbone=True)
    lat = torch.zeros(2, 3, 224, 224)
    assert red(lat, lat).shape == (2, N_SALIDAS)
    entrenables = [n for n, p in red.named_parameters() if p.requires_grad]
    assert entrenables and all(n.startswith("cabeza") for n in entrenables)


def test_correr_entrega_una_fila_por_medida(tmp_path):
    ruta = _indice_sintetico(tmp_path)
    promedio, detalle = entrenar.correr(ruta, tmp_path, n_folds=5, epocas=1, lote=4,
                                        preentrenada=False, verbose=False)
    assert list(promedio.columns) == entrenar.COLUMNAS_SALIDA
    assert promedio["medida"].tolist() == MEDIDAS
    assert np.isfinite(promedio[["rmse", "mae"]].to_numpy()).all()
    assert sorted(detalle["fold"].unique()) == [1, 2, 3, 4, 5]


def test_cli_solo_fold_escribe_los_dos_csv(tmp_path):
    ruta = _indice_sintetico(tmp_path)
    salida = tmp_path / "vision" / "metricas_cnn.csv"
    entrenar.main(["--indice", str(ruta), "--raiz", str(tmp_path), "--solo-fold", "1",
                   "--epocas", "1", "--lote", "4", "--sin-preentrenar",
                   "--salida", str(salida)])
    assert list(pd.read_csv(salida).columns) == ["medida", "rmse", "mae", "r_pearson"]
    detalle = pd.read_csv(tmp_path / "vision" / "metricas_cnn_folds.csv")
    assert detalle["fold"].unique().tolist() == [1]
