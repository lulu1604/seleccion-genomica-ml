"""Tests del contrato de las poblaciones simuladas (AlphaSimR)."""
from __future__ import annotations

import importlib

import pandas as pd
import pytest

loader = importlib.import_module("src.data.load_simulacion")


def _escribir_escenario(processed_dir, *, ids_x, ids_y=None, genotipos=None,
                        escenario="sim_n2"):
    """Crea un escenario de juguete en disco."""
    ids_y = ids_y if ids_y is not None else ids_x
    genotipos = genotipos if genotipos is not None else {"snp_00001": [0, 2],
                                                        "snp_00002": [1, 0]}
    carpeta = processed_dir / escenario
    carpeta.mkdir(parents=True)

    pd.DataFrame({"id_animal": ids_x, **genotipos}).to_csv(
        carpeta / "X_sim.csv", index=False)
    pd.DataFrame({
        "id_animal": ids_y,
        "fenotipo": [0.5, -0.5],
        "valor_gv": [0.2, -0.2],
    }).to_csv(carpeta / "y_sim.csv", index=False)
    return carpeta


@pytest.fixture
def processed_dir(monkeypatch, tmp_path):
    directorio = tmp_path / "processed"
    directorio.mkdir()
    monkeypatch.setattr(loader, "PROCESSED_DIR", directorio)
    return directorio


def test_cargar_devuelve_ids_alineados_con_las_filas(processed_dir):
    """El contrato central: X[i], y[i] e ids[i] son el mismo animal."""
    _escribir_escenario(processed_dir, ids_x=["SIM2_00001", "SIM2_00002"])

    X, y, ids = loader.cargar("sim_n2", target="fenotipo")

    assert X.shape == (2, 2)
    assert list(ids) == ["SIM2_00001", "SIM2_00002"]
    assert len(y) == len(ids) == X.shape[0]
    assert list(X[0]) == [0, 1]
    assert y[0] == 0.5


def test_cargar_rechaza_ids_desalineados(processed_dir):
    """Si y viene en otro orden, debe fallar en vez de entrenar mal."""
    _escribir_escenario(
        processed_dir,
        ids_x=["SIM2_00001", "SIM2_00002"],
        ids_y=["SIM2_00002", "SIM2_00001"],
    )

    with pytest.raises(RuntimeError, match="no coinciden"):
        loader.cargar("sim_n2")


def test_cargar_rechaza_genotipos_fuera_de_rango(processed_dir):
    """Un valor distinto de 0/1/2 no debe pasar."""
    _escribir_escenario(
        processed_dir,
        ids_x=["SIM2_00001", "SIM2_00002"],
        genotipos={"snp_00001": [0, 5], "snp_00002": [1, 0]},
    )

    with pytest.raises(RuntimeError, match="fuera de"):
        loader.cargar("sim_n2")


def test_cargar_rechaza_target_invalido(processed_dir):
    _escribir_escenario(processed_dir, ids_x=["SIM2_00001", "SIM2_00002"])

    with pytest.raises(ValueError, match="Target invalido"):
        loader.cargar("sim_n2", target="mkg")


def test_cargar_avisa_si_falta_el_escenario(processed_dir):
    """El error debe decir qué comando corregir la situación."""
    with pytest.raises(FileNotFoundError, match="simular.R"):
        loader.cargar("sim_n999")


def test_listar_escenarios_ordena_por_tamano(processed_dir):
    for escenario in ("sim_n500", "sim_n125", "sim_n2000"):
        (processed_dir / escenario).mkdir()

    assert loader.listar_escenarios() == ["sim_n125", "sim_n500", "sim_n2000"]
