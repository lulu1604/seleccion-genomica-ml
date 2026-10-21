"""Tests de results/snp_literatura.csv (SNP conocidos de la literatura para el SHAP)."""
import re
from pathlib import Path

import pandas as pd
import pytest

RUTA = Path(__file__).resolve().parents[1] / "results" / "snp_literatura.csv"
COLUMNAS = ["rsid", "gen", "cromosoma", "rasgo", "doi"]
RASGOS = {"mkg", "fpro", "scs"}


@pytest.fixture(scope="module")
def tabla():
    return pd.read_csv(RUTA, dtype=str, keep_default_na=False)


def test_tiene_las_columnas_del_contrato(tabla):
    assert list(tabla.columns) == COLUMNAS


def test_cubre_los_tres_rasgos_con_al_menos_un_snp(tabla):
    assert set(tabla["rasgo"]) == RASGOS


def test_hay_entre_5_y_10_snp_distintos(tabla):
    assert 5 <= tabla["rsid"].nunique() <= 10


def test_no_hay_celdas_vacias(tabla):
    assert (tabla.apply(lambda col: col.str.strip()) != "").all().all()


def test_formato_de_rsid_cromosoma_y_doi(tabla):
    assert tabla["rsid"].str.fullmatch(r"rs\d+").all()
    assert tabla["cromosoma"].str.fullmatch(r"\d{1,2}").all()
    assert tabla["cromosoma"].astype(int).between(1, 29).all()
    assert tabla["doi"].map(lambda d: re.fullmatch(r"10\.\d{4,9}/\S+", d) is not None).all()


def test_no_hay_filas_duplicadas(tabla):
    assert not tabla.duplicated(["rsid", "rasgo"]).any()


def test_un_rsid_siempre_tiene_el_mismo_gen_y_cromosoma(tabla):
    assert (tabla.groupby("rsid")[["gen", "cromosoma"]].nunique() == 1).all().all()


def test_dgat1_va_como_k232a_y_no_como_la_variante_intronica(tabla):
    dgat1 = tabla[tabla["gen"] == "DGAT1"]
    assert set(dgat1["rsid"]) == {"rs109234250"}
    assert "rs109421300" not in set(tabla["rsid"])
