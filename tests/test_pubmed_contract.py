"""Tests del contrato de la evidencia de PubMed (gene_evidence.csv).

Ninguna prueba llama a la red: requests.get siempre está simulado.
"""
from __future__ import annotations

import importlib

import pandas as pd
import pytest
import requests

pubmed = importlib.import_module("src.data.pubmed")

COLUMNAS = ["gen", "n_papers", "milk", "fat", "yield", "somatic_cell"]
NUMERICAS = COLUMNAS[1:]

ABSTRACTS = (
    "1. DGAT1 and Milk fat yield in dairy cattle. Milk yield increased.\n"
    "2. Somatic cell score and fat content of milk.\n"
)


class _Respuesta:
    """Respuesta de juguete con la interfaz que usa pubmed.py."""

    def __init__(self, *, json_data=None, text=""):
        self._json = json_data
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        if self._json is None:
            raise ValueError("no es JSON")
        return self._json


def _api_simulada(ids, abstracts=ABSTRACTS):
    """Devuelve un requests.get falso y la lista de URLs que recibió."""
    llamadas = []

    def fake_get(url, **kwargs):
        llamadas.append(url)
        if "esearch" in url:
            return _Respuesta(json_data={"esearchresult": {"idlist": ids}})
        return _Respuesta(text=abstracts)

    return fake_get, llamadas


def _api_caida(*args, **kwargs):
    raise requests.ConnectionError("sin red")


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    """Caché y resultados en carpetas temporales, sin pausas."""
    monkeypatch.setattr(pubmed, "RAW_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(pubmed, "RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(pubmed.time, "sleep", lambda s: None)
    return tmp_path


def _correr_main(entorno, genes):
    pubmed.main(genes)
    # keep_default_na=False: una celda vacía se lee como "" y no como NaN
    return pd.read_csv(entorno / "results" / "gene_evidence.csv",
                       keep_default_na=False)


def test_csv_tiene_las_columnas_del_contrato_en_orden(entorno, monkeypatch):
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    df = _correr_main(entorno, ["DGAT1"])

    assert list(df.columns) == COLUMNAS


def test_gen_es_la_primera_columna(entorno, monkeypatch):
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    df = _correr_main(entorno, ["DGAT1"])

    assert df.columns[0] == "gen"


def test_gen_siempre_sale_en_mayusculas(entorno, monkeypatch):
    """Protege el cruce con results/snp_annot.csv (Ensembl)."""
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    assert pubmed.process_gene("dgat1")["gen"] == "DGAT1"
    assert pubmed.process_gene("  Dgat1 ")["gen"] == "DGAT1"

    df = _correr_main(entorno, ["dgat1"])
    assert list(df["gen"]) == ["DGAT1"]


def test_gen_sin_resultados_devuelve_ceros(entorno, monkeypatch):
    fake_get, llamadas = _api_simulada([])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    fila = pubmed.process_gene("GEN_INVENTADO_QUE_NO_EXISTE")

    assert fila["gen"] == "GEN_INVENTADO_QUE_NO_EXISTE"
    assert all(fila[col] == 0 for col in NUMERICAS)
    assert len(llamadas) == 1  # sin IDs no hay nada que descargar


def test_si_la_api_falla_devuelve_ceros_y_sigue(entorno, monkeypatch, capsys):
    monkeypatch.setattr(pubmed.requests, "get", _api_caida)

    df = _correr_main(entorno, ["DGAT1", "ABCG2"])

    assert list(df["gen"]) == ["DGAT1", "ABCG2"]
    assert (df[NUMERICAS] == 0).all().all()
    salida = capsys.readouterr().out
    assert "ADVERTENCIA" in salida and "DGAT1" in salida and "sin red" in salida


def test_respuesta_que_no_es_json_devuelve_ceros(entorno, monkeypatch):
    """PubMed a veces responde una página de error en HTML."""
    monkeypatch.setattr(pubmed.requests, "get",
                        lambda url, **kw: _Respuesta(text="<html>error</html>"))

    fila = pubmed.process_gene("DGAT1")

    assert all(fila[col] == 0 for col in NUMERICAS)


def test_un_fallo_no_se_guarda_en_cache(entorno, monkeypatch):
    """Si no, un corte de red dejaría ceros pegados para siempre."""
    monkeypatch.setattr(pubmed.requests, "get", _api_caida)
    pubmed.process_gene("DGAT1")

    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    assert pubmed.process_gene("DGAT1")["n_papers"] == 2


def test_no_hay_nan_ni_celdas_vacias(entorno, monkeypatch):
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)
    pubmed.process_gene("DGAT1")
    # El segundo gen falla: la fila de ceros tampoco puede dejar huecos
    monkeypatch.setattr(pubmed.requests, "get", _api_caida)

    df = _correr_main(entorno, ["DGAT1", "ABCG2"])

    assert not df.isna().any().any()
    assert not (df.astype(str) == "").any().any()
    for col in NUMERICAS:
        assert pd.api.types.is_integer_dtype(df[col])


def test_cuenta_las_palabras_clave(entorno, monkeypatch):
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    fila = pubmed.process_gene("DGAT1")

    assert fila == {"gen": "DGAT1", "n_papers": 2, "milk": 3, "fat": 2,
                    "yield": 2, "somatic_cell": 1}


def test_segunda_llamada_usa_cache_y_no_toca_la_red(entorno, monkeypatch):
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)
    primera = pubmed.process_gene("DGAT1")

    assert (entorno / "raw" / "DGAT1.txt").exists()
    assert (entorno / "raw" / "DGAT1_ids.json").exists()

    monkeypatch.setattr(pubmed.requests, "get", _api_caida)
    segunda = pubmed.process_gene("dgat1")

    assert segunda == primera
    assert segunda["n_papers"] == 2


def test_usar_cache_false_fuerza_la_recarga(entorno, monkeypatch):
    fake_get, _ = _api_simulada(["111", "222"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)
    pubmed.process_gene("DGAT1")

    fake_get, llamadas = _api_simulada(["111", "222", "333"])
    monkeypatch.setattr(pubmed.requests, "get", fake_get)

    assert pubmed.process_gene("DGAT1", usar_cache=False)["n_papers"] == 3
    assert len(llamadas) == 2
