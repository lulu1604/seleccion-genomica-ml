"""API de solo lectura del dashboard BOVIGEN. Ver dashboard/CONTRATO_API.md."""
from fastapi import FastAPI, Query

from .datos import FUENTES, a_registros, leer, resumen

app = FastAPI(title="BOVIGEN API")


@app.get("/api/salud")
def salud():
    return {"estado": "ok", "demo": {nombre: leer(nombre)[1] for nombre in FUENTES}}


@app.get("/api/resumen")
def obtener_resumen():
    df, demo = leer("resultados")
    return {"demo": demo, "filas": a_registros(resumen(df))}


@app.get("/api/resultados")
def obtener_resultados(
    modelo: str | None = None,
    rasgo: str | None = None,
    escenario_n: int | None = None,
):
    df, demo = leer("resultados")
    if modelo is not None:
        df = df[df["modelo"] == modelo]
    if rasgo is not None:
        df = df[df["rasgo"] == rasgo]
    if escenario_n is not None:
        df = df[df["escenario_n"] == escenario_n]
    return {"demo": demo, "filas": a_registros(df)}


@app.get("/api/shap")
def obtener_shap(top: int = Query(20, ge=1, le=100)):
    df, demo = leer("shap")
    df = df.sort_values("importancia", ascending=False).head(top)
    return {"demo": demo, "filas": a_registros(df)}


@app.get("/api/vision")
def obtener_vision():
    df, demo = leer("vision")
    return {"demo": demo, "filas": a_registros(df)}
