"""Tests del backend del dashboard (solo lectura de CSV)."""
import statistics

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from dashboard.backend.app.datos import FUENTES
from dashboard.backend.app.main import app

COLUMNAS = ["modelo", "rasgo", "escenario_n", "ruido", "fold", "r_pearson", "rmse", "tiempo_s"]

R_GBLUP = [0.70, 0.72, 0.74]
R_RIDGE = [0.60, 0.65, 0.61]


def _escribir(raiz, relativa, df):
    ruta = raiz / relativa
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)


def _resultados_reales():
    filas = []
    for modelo, rs in (("gblup", R_GBLUP), ("ridge", R_RIDGE)):
        for fold, r in enumerate(rs, start=1):
            filas.append({"modelo": modelo, "rasgo": "fpro", "escenario_n": 5024,
                          "ruido": "base", "fold": fold, "r_pearson": r,
                          "rmse": 0.8, "tiempo_s": 1.0})
    return pd.DataFrame(filas, columns=COLUMNAS)


def _demos(raiz):
    _escribir(raiz, FUENTES["resultados"][1], _resultados_reales())
    _escribir(raiz, FUENTES["shap"][1], pd.DataFrame({
        "snp": ["a", "b", "c", "d"], "rsid": ["rs1", "", "", ""],
        "gen": ["DGAT1", "", "", ""], "importancia": [0.01, 0.05, 0.03, 0.02],
        "n_papers": [3, 0, 0, 0]}))
    _escribir(raiz, FUENTES["vision"][1], pd.DataFrame({
        "medida": ["peso_kg"], "rmse": [38.0], "mae": [29.5], "r_pearson": [0.86]}))


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("BOVIGEN_RAIZ", str(tmp_path))
    _demos(tmp_path)
    return TestClient(app), tmp_path


def test_resultados_solo_encabezado_usa_demo(cliente):
    client, raiz = cliente
    _escribir(raiz, FUENTES["resultados"][0], pd.DataFrame(columns=COLUMNAS))
    assert client.get("/api/resumen").json()["demo"] is True


def test_resumen_con_resultados_reales(cliente):
    client, raiz = cliente
    _escribir(raiz, FUENTES["resultados"][0], _resultados_reales())
    datos = client.get("/api/resumen").json()
    assert datos["demo"] is False
    filas = {f["modelo"]: f for f in datos["filas"]}
    assert set(filas) == {"gblup", "ridge"}
    for modelo, rs in (("gblup", R_GBLUP), ("ridge", R_RIDGE)):
        assert filas[modelo]["r_medio"] == pytest.approx(round(sum(rs) / 3, 4))
        assert filas[modelo]["r_desv"] == pytest.approx(round(statistics.stdev(rs), 4))
        assert filas[modelo]["n_folds"] == 3


def test_filtros_de_resultados(cliente):
    client, raiz = cliente
    _escribir(raiz, FUENTES["resultados"][0], _resultados_reales())
    filas = client.get("/api/resultados", params={
        "modelo": "ridge", "rasgo": "fpro", "escenario_n": 5024}).json()["filas"]
    assert len(filas) == 3
    assert {f["modelo"] for f in filas} == {"ridge"}
    assert client.get("/api/resultados", params={"rasgo": "scs"}).json()["filas"] == []


def test_shap_top_ordenado(cliente):
    client, _ = cliente
    filas = client.get("/api/shap", params={"top": 3}).json()["filas"]
    assert [f["importancia"] for f in filas] == [0.05, 0.03, 0.02]
    assert client.get("/api/shap", params={"top": 0}).status_code == 422


def test_nan_sale_como_null(cliente):
    client, raiz = cliente
    df = _resultados_reales()
    df.loc[0, "r_pearson"] = float("nan")
    _escribir(raiz, FUENTES["resultados"][0], df)
    filas = client.get("/api/resultados", params={"modelo": "gblup"}).json()["filas"]
    assert filas[0]["r_pearson"] is None


def test_salud_informa_demo_por_fuente(cliente):
    client, raiz = cliente
    _escribir(raiz, FUENTES["resultados"][0], _resultados_reales())
    datos = client.get("/api/salud").json()
    assert datos == {"estado": "ok",
                     "demo": {"resultados": False, "shap": True, "vision": True}}
