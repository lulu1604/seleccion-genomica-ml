"""Entrena la CNN de medidas corporales con validacion cruzada por animal.

    python -m src.vision.entrenar --folds 5 --salida results/vision/metricas_cnn.csv

Primera entrega (CNN base, un solo fold para ver que entrena y su RMSE):

    python -m src.vision.entrenar --solo-fold 1

Escribe results/vision/metricas_cnn.csv (lo lee el dashboard) con una fila por
medida y el promedio de los folds, en cm y kg:

    medida,rmse,mae,r_pearson

Y, al lado, <salida>_folds.csv con el detalle por fold (y el RMSE de predecir
siempre la media del train, para saber si la red aporta algo).

La CNN NO usa el runner de src/models/ (ese es solo para SNPs).
"""
from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader

from src.evaluation.metricas import r_pearson, rmse
from src.vision.cnn import construir
from src.vision.dataset import MEDIDAS, FotosBovinos, asignar_folds, cargar_indice

COLUMNAS_SALIDA = ["medida", "rmse", "mae", "r_pearson"]
COLUMNAS_FOLDS = ["fold", "medida", "rmse", "mae", "r_pearson", "rmse_base"]


def fijar_semilla(semilla: int) -> None:
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)


def _predecir(modelo, dataset, media, desv, dispositivo) -> np.ndarray:
    """Predice un dataset y devuelve las medidas en sus unidades (cm y kg)."""
    modelo.eval()
    salidas = []
    with torch.no_grad():
        for lat, pos, _ in DataLoader(dataset, batch_size=16, shuffle=False):
            salidas.append(modelo(lat.to(dispositivo), pos.to(dispositivo)).cpu().numpy())
    return np.concatenate(salidas) * desv + media


def entrenar_fold(tabla: pd.DataFrame, folds: np.ndarray, fold: int, *,
                  epocas: int, lr: float, lote: int, semilla: int,
                  preentrenada: bool, congelar: bool, dispositivo, verbose: bool = True):
    """Entrena con los animales de los otros folds y predice los del `fold`.

    Devuelve (y_real, y_pred, y_base), cada uno de forma (animales_test, 5).
    """
    fijar_semilla(semilla)
    train, test = tabla[folds != fold], tabla[folds == fold]

    # La normalizacion se calcula SOLO con el train: el test no puede influir.
    y_train = train[MEDIDAS].to_numpy(dtype=np.float32)
    media, desv = y_train.mean(axis=0), y_train.std(axis=0)
    desv[desv == 0] = 1.0

    ds_train = FotosBovinos(train, media, desv)
    ds_test = FotosBovinos(test, media, desv)
    # Un lote de 1 foto rompe BatchNorm si el backbone no esta congelado.
    cargador = DataLoader(ds_train, batch_size=lote, shuffle=True,
                          drop_last=len(ds_train) % lote == 1,
                          generator=torch.Generator().manual_seed(semilla))

    modelo = construir(preentrenada=preentrenada, congelar_backbone=congelar).to(dispositivo)
    parametros = [p for p in modelo.parameters() if p.requires_grad]
    optimizador = torch.optim.Adam(parametros, lr=lr)
    perdida = nn.MSELoss()

    for epoca in range(1, epocas + 1):
        modelo.train()
        total = 0.0
        for lat, pos, y in cargador:
            lat, pos, y = lat.to(dispositivo), pos.to(dispositivo), y.to(dispositivo)
            optimizador.zero_grad()
            error = perdida(modelo(lat, pos), y)
            error.backward()
            optimizador.step()
            total += error.item() * len(y)
        if verbose and (epoca == 1 or epoca % 10 == 0 or epoca == epocas):
            print(f"  fold {fold} epoca {epoca:3d}/{epocas}  perdida train {total / len(ds_train):.4f}")

    y_real = test[MEDIDAS].to_numpy(dtype=np.float64)
    y_pred = _predecir(modelo, ds_test, media, desv, dispositivo)
    y_base = np.tile(y_train.mean(axis=0), (len(test), 1))
    return y_real, y_pred, y_base


def metricas_fold(fold: int, y_real, y_pred, y_base) -> pd.DataFrame:
    """Una fila por medida, en las unidades originales (cm y kg)."""
    filas = []
    for j, medida in enumerate(MEDIDAS):
        filas.append({
            "fold": fold,
            "medida": medida,
            "rmse": rmse(y_real[:, j], y_pred[:, j]),
            "mae": float(np.mean(np.abs(y_real[:, j] - y_pred[:, j]))),
            "r_pearson": r_pearson(y_real[:, j], y_pred[:, j]),
            "rmse_base": rmse(y_real[:, j], y_base[:, j]),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_FOLDS)


def promediar(por_fold: pd.DataFrame) -> pd.DataFrame:
    """Promedio de los folds por medida (r_pearson ignora los NaN)."""
    prom = por_fold.groupby("medida", sort=False)[["rmse", "mae", "r_pearson"]].mean().reset_index()
    return prom.set_index("medida").loc[MEDIDAS].reset_index()[COLUMNAS_SALIDA]


def correr(indice, raiz=".", n_folds=5, solo_fold=None, epocas=30, lr=1e-3, lote=8,
           semilla=2026, preentrenada=True, congelar=True, verbose=True):
    """Corre la validacion cruzada y devuelve (promedio_por_medida, detalle_por_fold)."""
    tabla = cargar_indice(indice, raiz)
    folds = asignar_folds(tabla["id_animal_img"], n_folds, semilla)
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if verbose:
        print(f"{len(tabla)} animales, {n_folds} folds por animal, dispositivo: {dispositivo}")

    a_correr = [solo_fold] if solo_fold else list(range(1, n_folds + 1))
    detalle = []
    for fold in a_correr:
        t0 = time.perf_counter()
        y_real, y_pred, y_base = entrenar_fold(
            tabla, folds, fold, epocas=epocas, lr=lr, lote=lote, semilla=semilla,
            preentrenada=preentrenada, congelar=congelar, dispositivo=dispositivo,
            verbose=verbose)
        m = metricas_fold(fold, y_real, y_pred, y_base)
        detalle.append(m)
        if verbose:
            print(f"fold {fold} ({int((folds == fold).sum())} animales, "
                  f"{time.perf_counter() - t0:.0f} s):")
            print(m[["medida", "rmse", "rmse_base", "mae", "r_pearson"]]
                  .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    detalle = pd.concat(detalle, ignore_index=True)
    return promediar(detalle), detalle


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--indice", default="results/imagenes_index.csv")
    p.add_argument("--raiz", default=".", help="Carpeta contra la que se resuelven las rutas del indice")
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--solo-fold", type=int, default=None, help="Correr solo este fold (1..folds)")
    p.add_argument("--epocas", type=int, default=30)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--lote", type=int, default=8)
    p.add_argument("--semilla", type=int, default=2026)
    p.add_argument("--descongelar", action="store_true",
                   help="Entrenar tambien la ResNet18 (por defecto solo la capa final)")
    p.add_argument("--sin-preentrenar", action="store_true",
                   help="Pesos aleatorios en vez de los de ImageNet (solo para pruebas)")
    p.add_argument("--salida", default="results/vision/metricas_cnn.csv")
    a = p.parse_args(argv)

    if a.solo_fold is not None and not 1 <= a.solo_fold <= a.folds:
        p.error(f"--solo-fold debe estar entre 1 y {a.folds}")

    promedio, detalle = correr(
        a.indice, a.raiz, a.folds, a.solo_fold, a.epocas, a.lr, a.lote, a.semilla,
        preentrenada=not a.sin_preentrenar, congelar=not a.descongelar)

    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    promedio.round(4).to_csv(salida, index=False)
    ruta_folds = salida.with_name(salida.stem + "_folds.csv")
    detalle.round(4).to_csv(ruta_folds, index=False)
    print(f"\nPromedio de {detalle['fold'].nunique()} fold(s):")
    print(promedio.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nGuardado: {salida} y {ruta_folds}")


if __name__ == "__main__":
    main()
