"""Perceptron multicapa para prediccion genomica dentro del runner comun.

El escalado de SNPs y del rasgo se ajusta solamente con el subconjunto de
entrenamiento que recibe cada fold. Este modulo no lee archivos ni conoce los
folds: esa separacion evita que animales de test influyan en el entrenamiento.
"""
from __future__ import annotations

import random

import numpy as np
import torch
from torch import nn


class _MLP(nn.Module):
    """Red compacta de regresion para matrices densas de genotipos."""

    def __init__(self, n_features: int, hidden_dim: int) -> None:
        super().__init__()
        second_hidden = max(1, hidden_dim // 2)
        self.red = nn.Sequential(
            nn.Linear(n_features, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, second_hidden),
            nn.ReLU(),
            nn.Linear(second_hidden, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.red(x).squeeze(-1)


def _validar_entradas(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Normaliza tipos y rechaza entradas que romperian el contrato."""
    X_train = np.asarray(X_train)
    X_test = np.asarray(X_test)
    y_train = np.asarray(y_train, dtype=np.float32).reshape(-1)
    if X_train.ndim != 2 or X_test.ndim != 2:
        raise ValueError("X_train y X_test deben ser matrices 2-D")
    if X_train.shape[1] != X_test.shape[1]:
        raise ValueError("X_train y X_test deben tener el mismo numero de SNPs")
    if len(X_train) != len(y_train):
        raise ValueError("X_train e y_train deben tener el mismo numero de animales")
    if not len(X_train):
        raise ValueError("X_train no puede estar vacio")
    if not np.isfinite(X_train).all() or not np.isfinite(X_test).all():
        raise ValueError("Los genotipos deben ser finitos")
    if not np.isfinite(y_train).all():
        raise ValueError("y_train debe ser finito")
    return X_train, y_train, X_test


def _batch_size_efectivo(solicitado: int, n_features: int, max_batch_mb: float) -> int:
    """Limita un lote para que su matriz float32 no supere el presupuesto dado."""
    bytes_por_fila = n_features * np.dtype(np.float32).itemsize
    max_filas = max(1, int(max_batch_mb * 1024**2 // bytes_por_fila))
    return min(solicitado, max_filas)


def _escalar_snp(lote: np.ndarray, media: np.ndarray, desvio: np.ndarray) -> np.ndarray:
    """Convierte y escala un lote en sitio para no duplicar matrices densas."""
    escalado = lote.astype(np.float32, copy=True)
    np.subtract(escalado, media, out=escalado)
    np.divide(escalado, desvio, out=escalado)
    return escalado


def entrenar_y_predecir(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    **params: object,
) -> np.ndarray:
    """Ajusta un MLP solo con train y predice ``X_test``.

    Parametros opcionales: ``semilla`` (2026), ``epochs`` (20),
    ``batch_size`` (128), ``max_batch_mb`` (256), ``hidden_dim`` (16),
    ``learning_rate`` (1e-3) y ``weight_decay`` (1e-4). Se usa CPU para que las corridas sean
    reproducibles entre equipos con el mismo entorno Python/PyTorch.
    """
    X_train, y_train, X_test = _validar_entradas(X_train, y_train, X_test)
    semilla = int(params.get("semilla", 2026))
    epochs = int(params.get("epochs", 20))
    batch_size = int(params.get("batch_size", 128))
    max_batch_mb = float(params.get("max_batch_mb", 256))
    hidden_dim = int(params.get("hidden_dim", 16))
    learning_rate = float(params.get("learning_rate", 1e-3))
    weight_decay = float(params.get("weight_decay", 1e-4))
    if epochs < 1 or batch_size < 1 or hidden_dim < 1 or max_batch_mb <= 0:
        raise ValueError("epochs, batch_size, hidden_dim y max_batch_mb deben ser positivos")
    if learning_rate <= 0 or weight_decay < 0:
        raise ValueError("learning_rate debe ser positivo y weight_decay no negativo")

    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    device = torch.device("cpu")

    # Estadisticas estrictamente de train; las columnas monomorficas quedan en 0.
    feature_mean = X_train.mean(axis=0, dtype=np.float64).astype(np.float32)
    feature_std = X_train.std(axis=0, dtype=np.float64).astype(np.float32)
    feature_std[feature_std == 0] = 1.0
    y_mean = np.float32(y_train.mean())
    y_std = np.float32(y_train.std())
    if y_std == 0:
        y_std = np.float32(1.0)
    batch_size = _batch_size_efectivo(batch_size, X_train.shape[1], max_batch_mb)

    modelo = _MLP(X_train.shape[1], hidden_dim).to(device)
    optimizador = torch.optim.AdamW(
        modelo.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    perdida = nn.MSELoss()
    generador = torch.Generator(device="cpu").manual_seed(semilla)

    modelo.train()
    for _ in range(epochs):
        orden = torch.randperm(len(X_train), generator=generador).numpy()
        for inicio in range(0, len(orden), batch_size):
            indices = orden[inicio : inicio + batch_size]
            lote_x = _escalar_snp(X_train[indices], feature_mean, feature_std)
            lote_y = (y_train[indices] - y_mean) / y_std
            x = torch.from_numpy(lote_x).to(device)
            y = torch.from_numpy(lote_y).to(device)
            optimizador.zero_grad()
            valor = perdida(modelo(x), y)
            valor.backward()
            optimizador.step()

    modelo.eval()
    predicciones = []
    with torch.no_grad():
        for inicio in range(0, len(X_test), batch_size):
            lote_x = _escalar_snp(X_test[inicio : inicio + batch_size], feature_mean, feature_std)
            predicciones.append(modelo(torch.from_numpy(lote_x).to(device)).cpu().numpy())
    pred = np.concatenate(predicciones) if predicciones else np.empty(0, dtype=np.float32)
    return (pred * y_std + y_mean).astype(np.float64, copy=False)
