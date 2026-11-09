"""Entrena el modelo de medidas corporales con validacion cruzada por animal.

    python -m src.vision.entrenar --folds 5 --salida results/vision/metricas_cnn.csv

Metodos (`--metodo`):

- `ensamble` (por defecto): promedio de dos regresiones Ridge. Una usa las
  features congeladas de MobileNetV2 (lo que la foto "parece"); la otra, la
  geometria de la silueta segmentada con U2-Net (que tan alta, larga y ancha
  se ve la vaca). Con 72 animales esto generaliza mejor que entrenar la red.
- `cnn`: la CNN base de la primera entrega (ResNet18 congelada + capa lineal
  entrenada con descenso de gradiente). Sobreajusta; se deja para comparar.

Primera prueba rapida de un solo fold: `--solo-fold 1`.

Modelo para el dashboard (sin folds, con los 72 animales; lo usa
src/vision/predecir.py):

    python -m src.vision.entrenar --final --salida-modelo models/vision/ensamble.joblib

Escribe results/vision/metricas_cnn.csv (lo lee el dashboard) con una fila por
medida y el promedio de los folds, en cm y kg:

    medida,rmse,mae,r_pearson

Y, al lado, <salida>_folds.csv con el detalle por fold y `rmse_base`: el error
de predecir siempre la media del train. Si rmse no es menor que rmse_base, el
modelo no aporta.

Tambien escribe predicciones_cnn.csv: por animal, cada medida real y predicha
cuando ese animal estaba en el test (sirve para mostrar ejemplos en el dashboard).

Este modulo NO usa el runner de src/models/ (ese es solo para SNPs).
"""
from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader

from src.evaluation.metricas import r_pearson, rmse
from src.vision.cnn import construir, extraer_features
from src.vision.dataset import (MEDIDAS, FotosBovinos, _foto_a_tensor,
                                asignar_folds, cargar_indice)
from src.vision.silueta import features_geometria

COLUMNAS_SALIDA = ["medida", "rmse", "mae", "r_pearson"]
COLUMNAS_FOLDS = ["fold", "medida", "rmse", "mae", "r_pearson", "rmse_base"]
METODOS = ("ensamble", "cnn")
ALPHAS = np.logspace(-1, 6, 30)  # penalizaciones que prueba RidgeCV dentro del train


def fijar_semilla(semilla: int) -> None:
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)


# ---------------------------------------------------------------- ensamble

def ridge() -> object:
    """Estandariza las features y ajusta Ridge; el alpha de cada medida se elige
    con validacion interna (leave-one-out) usando SOLO el train del fold."""
    return make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS, alpha_per_target=True))


def features_ensamble(tabla, carpeta_mascaras, segmentar=None, preentrenada=True):
    """Calcula una vez, para todos los animales, los dos bloques de features.

    Ninguno se ajusta a las medidas (la CNN esta congelada y la geometria es
    una regla fija), asi que calcularlos antes de separar folds no filtra nada.
    """
    lateral = torch.stack([_foto_a_tensor(r) for r in tabla["ruta_lateral"]])
    posterior = torch.stack([_foto_a_tensor(r) for r in tabla["ruta_posterior"]])
    return {
        "cnn": extraer_features(lateral, posterior, preentrenada=preentrenada),
        "geometria": features_geometria(tabla, carpeta_mascaras, segmentar),
    }


def ensamble_fold(tabla, folds, fold, features):
    """Ajusta un Ridge por bloque con el train y promedia sus predicciones."""
    tr, te = folds != fold, folds == fold
    y = tabla[MEDIDAS].to_numpy(dtype=np.float64)
    media, desv = y[tr].mean(axis=0), y[tr].std(axis=0)
    desv[desv == 0] = 1.0
    y_norm = (y[tr] - media) / desv
    preds = [ridge().fit(X[tr], y_norm).predict(X[te]) for X in features.values()]
    y_pred = np.mean(preds, axis=0) * desv + media
    return y[te], y_pred, np.tile(media, (te.sum(), 1))


# ----------------------------------------------------- modelo final (dashboard)

def entrenar_final(tabla, carpeta_mascaras, ruta_metricas, segmentar=None,
                   preentrenada=True) -> dict:
    """Ajusta los dos Ridge con TODOS los animales, para predecir vacas nuevas.

    Es el mismo ensamble que se evalua con 5 folds, pero sin dejar animales
    fuera. Su error esperado es el de la validacion cruzada: se copia de
    `ruta_metricas` (results/vision/metricas_cnn.csv) dentro del paquete.
    """
    import sklearn
    from datetime import datetime

    features = features_ensamble(tabla, carpeta_mascaras, segmentar, preentrenada)
    y = tabla[MEDIDAS].to_numpy(dtype=np.float64)
    media, desv = y.mean(axis=0), y.std(axis=0)
    desv[desv == 0] = 1.0
    y_norm = (y - media) / desv
    metricas = pd.read_csv(ruta_metricas).set_index("medida")
    return {
        "modelos": {k: ridge().fit(X, y_norm) for k, X in features.items()},
        "media": media,
        "desv": desv,
        "medidas": list(MEDIDAS),
        "error": {m: round(float(metricas.loc[m, "rmse"]), 1) for m in MEDIDAS},
        "n_animales": len(tabla),
        "preentrenada": preentrenada,
        "sklearn": sklearn.__version__,
        "creado": datetime.now().isoformat(timespec="seconds"),
    }


def guardar_modelo(paquete: dict, ruta) -> Path:
    import joblib

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(paquete, ruta)
    return ruta


# --------------------------------------------------------------- CNN base

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
    """CNN base: entrena con los otros folds y predice los animales del `fold`.

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


# ---------------------------------------------------------------- comun

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


def tabla_predicciones(test: pd.DataFrame, fold: int, y_real, y_pred) -> pd.DataFrame:
    """Una fila por animal de test: medida real y predicha, en cm y kg."""
    filas = pd.DataFrame({"id_animal_img": test["id_animal_img"].to_numpy(), "fold": fold})
    for j, medida in enumerate(MEDIDAS):
        filas[f"{medida}_real"] = y_real[:, j]
        filas[f"{medida}_pred"] = y_pred[:, j]
    return filas


def promediar(por_fold: pd.DataFrame) -> pd.DataFrame:
    """Promedio de los folds por medida (r_pearson ignora los NaN)."""
    prom = por_fold.groupby("medida", sort=False)[["rmse", "mae", "r_pearson"]].mean().reset_index()
    return prom.set_index("medida").loc[MEDIDAS].reset_index()[COLUMNAS_SALIDA]


def correr(indice, raiz=".", n_folds=5, solo_fold=None, epocas=30, lr=1e-3, lote=8,
           semilla=2026, preentrenada=True, congelar=True, verbose=True,
           metodo="ensamble", carpeta_mascaras="data/processed/mascaras", segmentar=None):
    """Corre la validacion cruzada.

    Devuelve (promedio_por_medida, detalle_por_fold, predicciones). En
    `predicciones` cada animal aparece una vez, con lo que el modelo predijo
    cuando ese animal estaba en el TEST (nunca lo vio al entrenar).
    """
    if metodo not in METODOS:
        raise ValueError(f"metodo debe ser uno de {METODOS}")
    tabla = cargar_indice(indice, raiz)
    folds = asignar_folds(tabla["id_animal_img"], n_folds, semilla)
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if verbose:
        print(f"{len(tabla)} animales, {n_folds} folds por animal, metodo: {metodo}")

    features = None
    if metodo == "ensamble":
        if verbose:
            print("Calculando features (MobileNetV2 + silueta). La primera vez segmenta "
                  "las 144 fotos y tarda unos minutos; luego usa las mascaras guardadas.")
        features = features_ensamble(tabla, Path(raiz) / carpeta_mascaras, segmentar, preentrenada)

    a_correr = [solo_fold] if solo_fold else list(range(1, n_folds + 1))
    detalle, predicciones = [], []
    for fold in a_correr:
        t0 = time.perf_counter()
        if metodo == "ensamble":
            y_real, y_pred, y_base = ensamble_fold(tabla, folds, fold, features)
        else:
            y_real, y_pred, y_base = entrenar_fold(
                tabla, folds, fold, epocas=epocas, lr=lr, lote=lote, semilla=semilla,
                preentrenada=preentrenada, congelar=congelar, dispositivo=dispositivo,
                verbose=verbose)
        m = metricas_fold(fold, y_real, y_pred, y_base)
        detalle.append(m)
        predicciones.append(tabla_predicciones(tabla[folds == fold], fold, y_real, y_pred))
        if verbose:
            print(f"fold {fold} ({int((folds == fold).sum())} animales, "
                  f"{time.perf_counter() - t0:.0f} s):")
            print(m[["medida", "rmse", "rmse_base", "mae", "r_pearson"]]
                  .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    detalle = pd.concat(detalle, ignore_index=True)
    predicciones = pd.concat(predicciones, ignore_index=True)
    orden = predicciones["id_animal_img"].astype(int).argsort()
    return promediar(detalle), detalle, predicciones.iloc[orden].reset_index(drop=True)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--indice", default="results/imagenes_index.csv")
    p.add_argument("--raiz", default=".", help="Carpeta contra la que se resuelven las rutas del indice")
    p.add_argument("--metodo", choices=METODOS, default="ensamble")
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--solo-fold", type=int, default=None, help="Correr solo este fold (1..folds)")
    p.add_argument("--mascaras", default="data/processed/mascaras",
                   help="Carpeta (relativa a --raiz) donde se guardan las siluetas")
    p.add_argument("--epocas", type=int, default=30, help="Solo --metodo cnn")
    p.add_argument("--lr", type=float, default=1e-3, help="Solo --metodo cnn")
    p.add_argument("--lote", type=int, default=8, help="Solo --metodo cnn")
    p.add_argument("--semilla", type=int, default=2026)
    p.add_argument("--descongelar", action="store_true",
                   help="Solo --metodo cnn: entrenar tambien la ResNet18")
    p.add_argument("--sin-preentrenar", action="store_true",
                   help="Pesos aleatorios en vez de los de ImageNet (solo para pruebas)")
    p.add_argument("--salida", default="results/vision/metricas_cnn.csv",
                   help="CSV de metricas que se escribe (con --final: el que se lee para el error)")
    p.add_argument("--final", action="store_true",
                   help="Entrenar el ensamble con los 72 animales y guardarlo para el dashboard")
    p.add_argument("--salida-modelo", default="models/vision/ensamble.joblib")
    a = p.parse_args(argv)

    if a.final:
        tabla = cargar_indice(a.indice, a.raiz)
        print(f"Entrenando el modelo final con {len(tabla)} animales "
              "(la primera vez segmenta las fotos y tarda unos minutos)...")
        paquete = entrenar_final(tabla, Path(a.raiz) / a.mascaras, a.salida,
                                 preentrenada=not a.sin_preentrenar)
        ruta = guardar_modelo(paquete, a.salida_modelo)
        print(f"Guardado: {ruta} ({ruta.stat().st_size / 1e6:.1f} MB)")
        print(f"Error esperado (RMSE de la validacion cruzada): {paquete['error']}")
        return

    if a.solo_fold is not None and not 1 <= a.solo_fold <= a.folds:
        p.error(f"--solo-fold debe estar entre 1 y {a.folds}")

    promedio, detalle, predicciones = correr(
        a.indice, a.raiz, a.folds, a.solo_fold, a.epocas, a.lr, a.lote, a.semilla,
        preentrenada=not a.sin_preentrenar, congelar=not a.descongelar,
        metodo=a.metodo, carpeta_mascaras=a.mascaras)

    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    promedio.round(4).to_csv(salida, index=False)
    ruta_folds = salida.with_name(salida.stem + "_folds.csv")
    detalle.round(4).to_csv(ruta_folds, index=False)
    ruta_pred = salida.with_name(salida.stem.replace("metricas", "predicciones") + ".csv")
    predicciones.round(2).to_csv(ruta_pred, index=False)

    base = detalle.groupby("medida", sort=False)["rmse_base"].mean()
    resumen = promedio.set_index("medida")
    resumen["rmse_base"] = base
    resumen["mejora_%"] = 100 * (1 - resumen["rmse"] / resumen["rmse_base"])
    print(f"\nPromedio de {detalle['fold'].nunique()} fold(s) "
          f"(mejora_% > 0 = mejor que predecir la media):")
    print(resumen.reset_index().to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nGuardado: {salida}, {ruta_folds} y {ruta_pred}")


if __name__ == "__main__":
    main()
