"""Evaluación genómica para el ganadero (la usa el dashboard).

Recibe genotipos (0/1/2 por SNP) y devuelve, por animal, qué tan bueno es en
grasa, leche y ubre sana comparado con los animales de referencia, más una
categoría y una recomendación. No entrena nada: usa el paquete que arma
`dashboard/backend/preparar_genomica.py` (Ridge entrenado con los folds 2-5).

El paquete es un .npz (solo arrays de numpy, sin pickle).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RASGOS = ["fpro", "mkg", "scs"]
NOMBRE = {"fpro": "grasa", "mkg": "leche", "scs": "ubre sana"}
# Los 3 rasgos vienen en la escala alemana de valores relativos (RZ): más alto = mejor.
# En SCS (RZS) un valor alto significa MENOS células somáticas, o sea ubre más sana
# (Zhang et al. 2015, Tabla 1: SCS con media 102.3 y DE 11.7). Por eso no se invierte.
SENTIDO = {"fpro": 1.0, "mkg": 1.0, "scs": 1.0}
# Única zona con gen identificado: el pico de grasa y leche (SNP25070-SNP25140) cae al
# inicio del cromosoma 14, igual que en la Figura S1 de Zhang et al. 2015, y tiene
# efectos opuestos en grasa y leche, la firma de DGAT1.
ZONAS_CONOCIDAS = [(25070, 25140, "Zona del cromosoma 14", "Probablemente el gen DGAT1, conocido por subir la grasa")]
PESOS = {
    "balanceado": {"fpro": 1 / 3, "mkg": 1 / 3, "scs": 1 / 3},
    "grasa": {"fpro": 0.6, "mkg": 0.2, "scs": 0.2},
    "leche": {"fpro": 0.2, "mkg": 0.6, "scs": 0.2},
    "ubre": {"fpro": 0.2, "mkg": 0.2, "scs": 0.6},
}
CATEGORIAS = [  # (puntaje mínimo, categoría, acción)
    (90, "Élite", "Embriones"),
    (50, "Bueno", "Semen sexado"),
    (25, "Regular", "Semen convencional"),
    (0, "Bajo", "Semen de carne"),
]
MAX_ANIMALES = 2000


class ErrorGenotipos(ValueError):
    """Problema con el archivo subido; el mensaje se muestra tal cual al usuario."""


def cargar_paquete(ruta: str | Path) -> dict:
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe {ruta}. Generalo con: python dashboard/backend/preparar_genomica.py")
    with np.load(ruta, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def percentil(valores: np.ndarray, referencia: np.ndarray) -> np.ndarray:
    """% de la referencia que queda por debajo o igual (0-100)."""
    ref = np.sort(np.asarray(referencia, dtype=float))
    return 100.0 * np.searchsorted(ref, np.asarray(valores, dtype=float), side="right") / len(ref)


def categoria(puntaje: float) -> tuple[str, str]:
    for minimo, nombre, accion in CATEGORIAS:
        if puntaje >= minimo:
            return nombre, accion
    return CATEGORIAS[-1][1:]


def etiqueta(p: dict) -> str:
    """p = {"fpro": percentil, "mkg": ..., "scs": ...}."""
    if all(p[r] >= 75 for r in RASGOS):
        return "bueno en las 3"
    mejor = max(RASGOS, key=lambda r: p[r])
    if p[mejor] >= 70:
        return f"destaca en {NOMBRE[mejor]}"
    if np.mean([p[r] for r in RASGOS]) >= 50:
        return "sobre el promedio"
    return "bajo el promedio"


def nombre_zona(posicion: int) -> dict:
    """posicion = número del marcador (SNP25091 -> 25091)."""
    for desde, hasta, nombre, detalle in ZONAS_CONOCIDAS:
        if desde <= posicion <= hasta:
            return {"zona": nombre, "detalle": detalle}
    return {"zona": "Otra zona del ADN", "detalle": "Sin gen conocido"}


def confianza(r: float) -> str:
    return "alto" if r >= 0.75 else "medio" if r >= 0.60 else "bajo"


def leer_genotipos(df: pd.DataFrame, snps: list[str]) -> tuple[list[str], list[str], np.ndarray]:
    """Valida el archivo y devuelve (ids, tipos, X float32 en el orden de `snps`)."""
    if "id_animal" not in df.columns:
        raise ErrorGenotipos("El archivo debe tener una columna 'id_animal'.")
    if len(df) == 0:
        raise ErrorGenotipos("El archivo no tiene animales.")
    if len(df) > MAX_ANIMALES:
        raise ErrorGenotipos(f"Máximo {MAX_ANIMALES} animales por archivo.")
    faltan = [s for s in snps if s not in df.columns]
    if faltan:
        raise ErrorGenotipos(
            f"Faltan {len(faltan)} marcadores del ADN (por ejemplo {', '.join(faltan[:3])}). "
            "Usa el mismo formato que el archivo de ejemplo.")
    valores = df[snps].to_numpy().ravel()
    X = pd.to_numeric(pd.Series(valores), errors="coerce").to_numpy(dtype=np.float32)
    X = X.reshape(len(df), len(snps))
    if np.isnan(X).any() or not np.isin(X, (0, 1, 2)).all():
        raise ErrorGenotipos("Los marcadores solo pueden valer 0, 1 o 2, sin celdas vacías.")
    ids = df["id_animal"].astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise ErrorGenotipos("Hay animales repetidos en 'id_animal'.")
    tipos = df["tipo"].fillna("").astype(str).tolist() if "tipo" in df.columns else [""] * len(ids)
    return ids, tipos, X


def _z(pred: np.ndarray, paq: dict, r: str) -> np.ndarray:
    ref = paq[f"ref_{r}"]
    return SENTIDO[r] * (pred - ref.mean()) / ref.std()


def evaluar(df: pd.DataFrame, paq: dict, n_zonas: int = 3) -> list[dict]:
    """Una entrada por animal con percentiles, categoría por prioridad y zonas del ADN."""
    snps = paq["snps"].tolist()
    ids, tipos, X = leer_genotipos(df, snps)
    Xc = X - paq["media_snp"]
    pred = {r: Xc @ paq[f"coef_{r}"] + paq[f"media_pred_{r}"] for r in RASGOS}
    pct = {r: percentil(SENTIDO[r] * pred[r], SENTIDO[r] * paq[f"ref_{r}"]) for r in RASGOS}

    puntajes = {}
    for prioridad, w in PESOS.items():
        ref_comb = sum(w[r] * _z(paq[f"ref_{r}"], paq, r) for r in RASGOS)
        comb = sum(w[r] * _z(pred[r], paq, r) for r in RASGOS)
        puntajes[prioridad] = percentil(comb, ref_comb)

    salida = []
    for i, ident in enumerate(ids):
        p = {r: float(pct[r][i]) for r in RASGOS}
        por_prioridad = {}
        for prioridad in PESOS:
            puntaje = round(float(puntajes[prioridad][i]))
            nombre, accion = categoria(puntaje)
            por_prioridad[prioridad] = {"puntaje": puntaje, "categoria": nombre, "accion": accion}
        zonas = {}
        for r in RASGOS:
            aporte = SENTIDO[r] * Xc[i] * paq[f"coef_{r}"]
            orden = np.argsort(aporte)
            elegidos = list(orden[::-1][:n_zonas]) + [orden[0]]
            zonas[NOMBRE[r]] = [{"marcador": snps[j], **nombre_zona(j + 1),
                                 "efecto": "sube" if aporte[j] >= 0 else "baja",
                                 "valor": round(float(aporte[j]), 4)} for j in elegidos]
        salida.append({
            "id": ident,
            "tipo": tipos[i],
            "percentiles": {NOMBRE[r]: round(p[r]) for r in RASGOS},
            "etiqueta": etiqueta(p),
            "por_prioridad": por_prioridad,
            "zonas": zonas,
        })
    # puesto según cada prioridad
    for prioridad in PESOS:
        orden = sorted(range(len(salida)), key=lambda k: -puntajes[prioridad][k])
        for puesto, k in enumerate(orden, start=1):
            salida[k]["por_prioridad"][prioridad]["puesto"] = puesto
    return salida
