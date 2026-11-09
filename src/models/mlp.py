"""MLP residual aditiva para prediccion genomica con seleccion interna.

Cada llamada recibe solo el ``train`` de un fold externo. La seleccion de
regularizacion usa un 15 % interno y nunca consulta los animales de test.
Despues se reinicializa la red y se ajusta sobre todo el train externo por la
epoca seleccionada.
"""
from __future__ import annotations

import copy
import random
from typing import Any

import numpy as np
import torch
from torch import nn


class _MLP(nn.Module):
    """Componente aditivo lineal mas correccion no lineal compacta."""

    def __init__(self, n_features: int, hidden_dim: int, dropout: float = 0.0) -> None:
        super().__init__()
        second_hidden = max(1, hidden_dim // 2)
        self.aditiva = nn.Linear(n_features, 1)
        self.residual = nn.Sequential(
            nn.Linear(n_features, hidden_dim), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, second_hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(second_hidden, 1),
        )
        # Inicio neutro: tras desnormalizar predice la media de train. Evita
        # que 10k+ coeficientes aleatorios descalibren los primeros epochs.
        nn.init.zeros_(self.aditiva.weight)
        nn.init.zeros_(self.aditiva.bias)
        nn.init.zeros_(self.residual[-1].weight)
        nn.init.zeros_(self.residual[-1].bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (self.aditiva(x) + self.residual(x)).squeeze(-1)


def _validar_entradas(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Normaliza tipos y verifica el contrato sin copiar matrices completas."""
    X_train = np.asarray(X_train)
    y_train = np.asarray(y_train, dtype=np.float32).reshape(-1)
    X_test = None if X_test is None else np.asarray(X_test)
    if X_train.ndim != 2 or (X_test is not None and X_test.ndim != 2):
        raise ValueError("X_train y X_test deben ser matrices 2-D")
    if X_test is not None and X_train.shape[1] != X_test.shape[1]:
        raise ValueError("X_train y X_test deben tener el mismo numero de SNPs")
    if len(X_train) != len(y_train):
        raise ValueError("X_train e y_train deben tener el mismo numero de animales")
    if len(X_train) < 2:
        raise ValueError("X_train necesita al menos dos animales")
    if not np.isfinite(X_train).all() or (X_test is not None and not np.isfinite(X_test).all()):
        raise ValueError("Los genotipos deben ser finitos")
    if not np.isfinite(y_train).all():
        raise ValueError("y_train debe ser finito")
    return X_train, y_train, X_test


def _batch_size_efectivo(solicitado: int, n_features: int, max_batch_mb: float) -> int:
    """Limita la matriz float32 de entrada de cada lote, no la RAM total."""
    bytes_por_fila = n_features * np.dtype(np.float32).itemsize
    max_filas = max(1, int(max_batch_mb * 1024**2 // bytes_por_fila))
    return min(solicitado, max_filas)


def _partir_fit_validacion(
    n_muestras: int, *, fraccion_validacion: float, semilla: int
) -> tuple[np.ndarray, np.ndarray]:
    """Construye una particion interna disjunta y reproducible."""
    if n_muestras < 3:
        raise ValueError("Se requieren al menos tres animales para validacion interna")
    if not 0 < fraccion_validacion < 0.5:
        raise ValueError("fraccion_validacion debe estar entre 0 y 0.5")
    n_validacion = max(1, int(np.ceil(n_muestras * fraccion_validacion)))
    n_validacion = min(n_validacion, n_muestras - 1)
    orden = np.random.default_rng(semilla).permutation(n_muestras)
    return orden[n_validacion:], orden[:n_validacion]


def _escalar_snp(lote: np.ndarray, media: np.ndarray, desvio: np.ndarray) -> np.ndarray:
    escalado = lote.astype(np.float32, copy=True)
    np.subtract(escalado, media, out=escalado)
    np.divide(escalado, desvio, out=escalado)
    return escalado


def _estadisticas_fit(
    X_fit: np.ndarray, y_fit: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.float32, np.float32]:
    media = X_fit.mean(axis=0, dtype=np.float64).astype(np.float32)
    desvio = X_fit.std(axis=0, dtype=np.float64).astype(np.float32)
    desvio[desvio == 0] = 1.0
    media_y = np.float32(y_fit.mean())
    desvio_y = np.float32(y_fit.std())
    if desvio_y == 0:
        desvio_y = np.float32(1.0)
    return media, desvio, media_y, desvio_y


def _sembrar(semilla: int) -> None:
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)


def _parametros(params: dict[str, object]) -> dict[str, Any]:
    valores: dict[str, Any] = {
        "semilla": 2026, "epochs": 100, "patience": 15, "min_delta": 1e-4,
        "fraccion_validacion": 0.15, "batch_size": 4096, "max_batch_mb": 1024.0,
        "hidden_dim": 4, "dropout": 0.1, "learning_rate": 1e-3,
        "weight_decay": 1e-3,
    }
    valores.update(params)
    for clave in ("semilla", "epochs", "patience", "batch_size", "hidden_dim"):
        valores[clave] = int(valores[clave])
    for clave in ("min_delta", "fraccion_validacion", "max_batch_mb", "dropout", "learning_rate", "weight_decay"):
        valores[clave] = float(valores[clave])
    if valores["epochs"] < 1 or valores["patience"] < 1 or valores["batch_size"] < 1 or valores["hidden_dim"] < 1:
        raise ValueError("epochs, patience, batch_size y hidden_dim deben ser positivos")
    if not 0 <= valores["dropout"] < 1 or valores["learning_rate"] <= 0 or valores["weight_decay"] < 0:
        raise ValueError("dropout invalido, learning_rate positivo y weight_decay no negativo")
    if valores["max_batch_mb"] <= 0 or valores["min_delta"] < 0:
        raise ValueError("max_batch_mb debe ser positivo y min_delta no negativo")
    return valores


def _entrenar_epoca(
    modelo: _MLP, optimizador: torch.optim.Optimizer, X_fit: np.ndarray, y_fit: np.ndarray,
    estadisticas: tuple[np.ndarray, np.ndarray, np.float32, np.float32], batch_size: int,
    generador: torch.Generator,
) -> None:
    media, desvio, media_y, desvio_y = estadisticas
    perdida = nn.MSELoss()
    modelo.train()
    orden = torch.randperm(len(X_fit), generator=generador).numpy()
    for inicio in range(0, len(orden), batch_size):
        indices = orden[inicio : inicio + batch_size]
        x = torch.from_numpy(_escalar_snp(X_fit[indices], media, desvio))
        y = torch.from_numpy((y_fit[indices] - media_y) / desvio_y)
        optimizador.zero_grad()
        valor = perdida(modelo(x), y)
        valor.backward()
        optimizador.step()


def _mse_validacion(
    modelo: _MLP, X_val: np.ndarray, y_val: np.ndarray,
    estadisticas: tuple[np.ndarray, np.ndarray, np.float32, np.float32], batch_size: int,
) -> float:
    media, desvio, media_y, desvio_y = estadisticas
    predicciones: list[np.ndarray] = []
    modelo.eval()
    with torch.no_grad():
        for inicio in range(0, len(X_val), batch_size):
            x = torch.from_numpy(_escalar_snp(X_val[inicio : inicio + batch_size], media, desvio))
            predicciones.append(modelo(x).numpy())
    pred = np.concatenate(predicciones) * desvio_y + media_y
    return float(np.mean((pred - y_val) ** 2))


def _ajustar_desde_particion(
    X_fit: np.ndarray, y_fit: np.ndarray, X_val: np.ndarray, y_val: np.ndarray,
    configuracion: dict[str, Any], estadisticas: tuple[np.ndarray, np.ndarray, np.float32, np.float32],
) -> dict[str, Any]:
    """Ajusta un candidato sobre una particion y estadisticas ya fijadas."""
    lote = _batch_size_efectivo(configuracion["batch_size"], X_fit.shape[1], configuracion["max_batch_mb"])
    _sembrar(configuracion["semilla"])
    modelo = _MLP(X_fit.shape[1], configuracion["hidden_dim"], configuracion["dropout"])
    optimizador = torch.optim.AdamW(modelo.parameters(), lr=configuracion["learning_rate"], weight_decay=configuracion["weight_decay"])
    generador = torch.Generator(device="cpu").manual_seed(configuracion["semilla"])
    mejor_mse, mejor_epoca, espera, mejor_estado = float("inf"), 0, 0, None
    for epoca in range(1, configuracion["epochs"] + 1):
        _entrenar_epoca(modelo, optimizador, X_fit, y_fit, estadisticas, lote, generador)
        mse = _mse_validacion(modelo, X_val, y_val, estadisticas, lote)
        if mse < mejor_mse - configuracion["min_delta"]:
            mejor_mse, mejor_epoca, espera = mse, epoca, 0
            mejor_estado = copy.deepcopy(modelo.state_dict())
        else:
            espera += 1
            if espera >= configuracion["patience"]:
                break
    if mejor_estado is None:
        raise RuntimeError("La validacion interna no produjo un estado seleccionable")
    return {
        "dropout": configuracion["dropout"], "best_val_mse": mejor_mse,
        "best_epoch": mejor_epoca, "epochs_ran": epoca, "n_fit": len(X_fit),
        "n_val": len(X_val), "input_batch_mb": lote * X_fit.shape[1] * 4 / 1024**2,
    }


def _ajustar_con_validacion(
    X_train: np.ndarray, y_train: np.ndarray, configuracion: dict[str, Any]
) -> dict[str, Any]:
    """Selecciona epoca en fit/validacion interna, sin tocar test externo."""
    indices_fit, indices_val = _partir_fit_validacion(
        len(X_train), fraccion_validacion=configuracion["fraccion_validacion"], semilla=configuracion["semilla"]
    )
    X_fit, y_fit = X_train[indices_fit], y_train[indices_fit]
    X_val, y_val = X_train[indices_val], y_train[indices_val]
    return _ajustar_desde_particion(
        X_fit, y_fit, X_val, y_val, configuracion, _estadisticas_fit(X_fit, y_fit)
    )


def validar_configuracion(X_train: np.ndarray, y_train: np.ndarray, **params: object) -> dict[str, Any]:
    """Evalua una configuracion exclusivamente dentro del train externo."""
    X_train, y_train, _ = _validar_entradas(X_train, y_train)
    return _ajustar_con_validacion(X_train, y_train, _parametros(dict(params)))


def _refit_y_predecir(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray,
    configuracion: dict[str, Any], epochs: int,
) -> np.ndarray:
    """Reinicializa la red y la entrena con todo train por la epoca seleccionada."""
    estadisticas = _estadisticas_fit(X_train, y_train)
    lote = _batch_size_efectivo(configuracion["batch_size"], X_train.shape[1], configuracion["max_batch_mb"])
    _sembrar(configuracion["semilla"] + 10_000)
    modelo = _MLP(X_train.shape[1], configuracion["hidden_dim"], configuracion["dropout"])
    optimizador = torch.optim.AdamW(modelo.parameters(), lr=configuracion["learning_rate"], weight_decay=configuracion["weight_decay"])
    generador = torch.Generator(device="cpu").manual_seed(configuracion["semilla"] + 10_000)
    for _ in range(epochs):
        _entrenar_epoca(modelo, optimizador, X_train, y_train, estadisticas, lote, generador)
    media, desvio, media_y, desvio_y = estadisticas
    predicciones: list[np.ndarray] = []
    modelo.eval()
    with torch.no_grad():
        for inicio in range(0, len(X_test), lote):
            x = torch.from_numpy(_escalar_snp(X_test[inicio : inicio + lote], media, desvio))
            predicciones.append(modelo(x).numpy())
    pred = np.concatenate(predicciones) if predicciones else np.empty(0, dtype=np.float32)
    return (pred * desvio_y + media_y).astype(np.float64, copy=False)


def entrenar_y_predecir(
    X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, **params: object
) -> np.ndarray:
    """Selecciona dropout internamente, reinicializa y predice el test externo.

    ``registro_seleccion`` es una lista opcional que recibe el resumen del
    dropout elegido; permite al runner guardar trazabilidad por fold.
    """
    registro = params.pop("registro_seleccion", None)
    candidatos = tuple(float(d) for d in params.pop("dropouts", (params.get("dropout", 0.1),)))
    if not candidatos:
        raise ValueError("dropouts debe contener al menos un candidato")
    X_train, y_train, X_test = _validar_entradas(X_train, y_train, X_test)
    assert X_test is not None
    base = _parametros(dict(params))
    indices_fit, indices_val = _partir_fit_validacion(
        len(X_train), fraccion_validacion=base["fraccion_validacion"], semilla=base["semilla"]
    )
    X_fit, y_fit = X_train[indices_fit], y_train[indices_fit]
    X_val, y_val = X_train[indices_val], y_train[indices_val]
    estadisticas = _estadisticas_fit(X_fit, y_fit)
    resumentes: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for dropout in candidatos:
        configuracion = _parametros({**base, "dropout": dropout})
        resumen = _ajustar_desde_particion(
            X_fit, y_fit, X_val, y_val, configuracion, estadisticas
        )
        resumentes.append((resumen, configuracion))
    resumen, configuracion = min(resumentes, key=lambda par: (par[0]["best_val_mse"], par[0]["dropout"]))
    pred = _refit_y_predecir(X_train, y_train, X_test, configuracion, resumen["best_epoch"])
    if registro is not None:
        if not isinstance(registro, list):
            raise TypeError("registro_seleccion debe ser una lista")
        registro.append({**resumen, "configuracion": configuracion.copy()})
    return pred
