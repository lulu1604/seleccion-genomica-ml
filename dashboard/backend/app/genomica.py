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
# Respaldo sin mapa: el pico de grasa y leche (SNP25070-SNP25140) cae al inicio del
# cromosoma 14, igual que en la Figura S1 de Zhang et al. 2015, y tiene efectos opuestos
# en grasa y leche, la firma de DGAT1.
ZONAS_CONOCIDAS = [(25070, 25140, "Zona del cromosoma 14", "Probablemente el gen DGAT1, conocido por subir la grasa")]

# Con mapa (paq["cromosoma"], paq["mb"], de results/mapa_snp.csv): genes de la leche
# conocidos cerca de los picos del Ridge. Posiciones aproximadas en Mb (UMD3.1).
# "Probablemente" = pico a <~1 Mb del gen; "posiblemente" = gen candidato por verificar.
GENES = [
    {"cromosoma": 14, "desde": 0.0, "hasta": 3.5, "gen": "DGAT1", "detalle": {
        "fpro": "Probablemente el gen DGAT1, que arma la grasa de la leche",
        "mkg": "Probablemente el gen DGAT1: sube la grasa, pero baja un poco los litros",
        "scs": "Probablemente el gen DGAT1, que casi no influye en la ubre"}},
    {"cromosoma": 5, "desde": 91.5, "hasta": 95.5, "gen": "MGST1", "detalle": {
        "_": "Probablemente el gen MGST1, ligado a la grasa de la leche"}},
    {"cromosoma": 20, "desde": 30.5, "hasta": 34.0, "gen": "GHR", "detalle": {
        "_": "Probablemente el gen GHR (hormona del crecimiento), ligado a la leche y la grasa"}},
    {"cromosoma": 6, "desde": 86.0, "hasta": 90.0, "gen": "caseínas", "detalle": {
        "_": "Cerca de los genes de las caseínas, las proteínas de la leche"}},
    {"cromosoma": 27, "desde": 35.5, "hasta": 37.5, "gen": "AGPAT6", "detalle": {
        "_": "Posiblemente el gen AGPAT6, ligado a la grasa de la leche"}},
    {"cromosoma": 19, "desde": 50.5, "hasta": 53.0, "gen": "FASN", "detalle": {
        "_": "Posiblemente el gen FASN, que fabrica grasas de la leche"}},
]
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


def _zonas_ficha(aporte: np.ndarray, snps: list[str], n_zonas: int = 3,
                 rasgo: str = "fpro", paq: dict | None = None) -> list[dict]:
    """Las n_zonas que más suben, la que más baja y una fila final "Resto de su ADN".

    Una zona conocida cuenta como UNA sola fila: su valor es la suma de los aportes
    de todos sus marcadores, y "marcador" es el de mayor aporte absoluto dentro de ella.
    Con mapa, las zonas conocidas son las ventanas de GENES y cada fila dice su
    cromosoma; sin mapa, se usa ZONAS_CONOCIDAS (por número de marcador).
    La fila "resto" suma todo lo que no se muestra, así la cuenta cuadra:
    suma de las filas = suma de todos los aportes.
    """
    hay_mapa = paq is not None and "cromosoma" in paq and "mb" in paq
    filas = []
    dentro = np.zeros(len(aporte), dtype=bool)
    if hay_mapa:
        cromo, mb = paq["cromosoma"], paq["mb"]
        for g in GENES:
            sel = np.flatnonzero((cromo == g["cromosoma"]) & (mb >= g["desde"]) & (mb <= g["hasta"]))
            if len(sel) == 0:
                continue
            dentro[sel] = True
            j = int(sel[np.argmax(np.abs(aporte[sel]))])
            detalle = g["detalle"].get(rasgo, g["detalle"].get("_"))
            filas.append((float(aporte[sel].sum()), j,
                          {"zona": f"Zona del cromosoma {g['cromosoma']}", "detalle": detalle,
                           "gen": g["gen"], "cromosoma": int(g["cromosoma"])}))
    else:
        for desde, hasta, nombre, detalle in ZONAS_CONOCIDAS:
            tramo = slice(desde - 1, min(hasta, len(aporte)))
            if tramo.start >= len(aporte):
                continue
            dentro[tramo] = True
            j = tramo.start + int(np.argmax(np.abs(aporte[tramo])))
            filas.append((float(aporte[tramo].sum()), j,
                          {"zona": nombre, "detalle": detalle, "gen": "DGAT1", "cromosoma": 14}))
    for j in np.flatnonzero(~dentro):
        filas.append((float(aporte[j]), int(j), None))
    filas.sort(key=lambda f: f[0])
    suben = filas[::-1][:n_zonas]
    baja = [f for f in filas[:1] if f not in suben]
    elegidas = suben + baja

    def describir(j: int, info: dict | None) -> dict:
        if info is not None:
            return info
        if hay_mapa:
            return {"zona": f"Zona del cromosoma {int(paq['cromosoma'][j])}",
                    "detalle": "Sin gen identificado", "gen": "", "cromosoma": int(paq["cromosoma"][j])}
        return {**nombre_zona(j + 1), "gen": "", "cromosoma": 0}

    salida = [{"marcador": snps[j], **describir(j, info),
               "efecto": "sube" if v >= 0 else "baja", "valor": round(v, 4), "resto": False}
              for v, j, info in elegidas]
    resto = float(aporte.sum()) - sum(v for v, _, _ in elegidas)
    salida.append({"marcador": "", "zona": "Resto de su ADN",
                   "detalle": "Miles de zonas pequeñas sumadas", "gen": "", "cromosoma": 0,
                   "efecto": "sube" if resto >= 0 else "baja", "valor": round(resto, 4), "resto": True})
    return salida


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
        cuantos = (f"le falta {len(faltan)} marcador" if len(faltan) == 1
                   else f"le faltan {len(faltan):,} marcadores".replace(",", "."))
        raise ErrorGenotipos(
            f"Al archivo {cuantos} del ADN de los {len(snps):,} que necesitamos. ".replace(",", ".")
            + "Pide al laboratorio el archivo completo o usa el mismo formato que el archivo de ejemplo.")
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
    nombres = df["nombre"].fillna("").astype(str).tolist() if "nombre" in df.columns else [""] * len(ids)
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
            zonas[NOMBRE[r]] = _zonas_ficha(aporte, snps, n_zonas, rasgo=r, paq=paq)
        salida.append({
            "id": ident,
            "tipo": tipos[i],
            "nombre": nombres[i],
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
