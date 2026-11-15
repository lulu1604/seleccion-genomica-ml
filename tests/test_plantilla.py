"""Tests de la plantilla de Excel del dashboard, con un paquete falso pequeño (sin datos reales)."""
import io

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from dashboard.backend.app import main
from dashboard.backend.app.genomica import ErrorGenotipos, evaluar
from dashboard.backend.app.plantilla import crear_ejemplo_excel, crear_plantilla, leer_excel

N_SNP = 20
SNPS = [f"SNP{j + 1}" for j in range(N_SNP)]


def _paquete():
    rng = np.random.default_rng(3)
    X_ref = rng.integers(0, 3, size=(60, N_SNP)).astype(np.float32)
    paq = {"snps": np.array(SNPS), "media_snp": X_ref.mean(axis=0)}
    for r in ("fpro", "mkg", "scs"):
        coef = rng.normal(size=N_SNP).astype(np.float32)
        paq.update({f"coef_{r}": coef, f"media_pred_{r}": np.array(1.0),
                    f"ref_{r}": (X_ref - paq["media_snp"]) @ coef + 1.0})
    return paq


def _ejemplo_csv(n=5):
    rng = np.random.default_rng(4)
    df = pd.DataFrame(rng.integers(0, 3, size=(n, N_SNP)), columns=SNPS)
    df.insert(0, "tipo", "Toro")
    df.insert(0, "id_animal", [f"Anim{i + 1}" for i in range(n)])
    return df


def _excel(animales, columnas=None, hojas=("Animales", "ADN"), quitar_marcador=None):
    """Excel a mano: animales = [(id, tipo, nombre)]; columnas = ids de la hoja ADN."""
    columnas = [a[0] for a in animales] if columnas is None else columnas
    wb = Workbook()
    wb.remove(wb.active)
    if "Animales" in hojas:
        hoja = wb.create_sheet("Animales")
        hoja.append(["id_animal", "tipo", "nombre"])
        for fila in animales:
            hoja.append(list(fila))
    if "ADN" in hojas:
        hoja = wb.create_sheet("ADN")
        hoja.append(["marcador", *columnas])
        rng = np.random.default_rng(5)
        for snp in SNPS:
            if snp != quitar_marcador:
                hoja.append([snp, *rng.integers(0, 3, size=len(columnas)).tolist()])
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


VAQUILLAS = [("V-001", "Vaquilla", "Lucerito"), ("V-002", "vaquilla", ""), ("V-003", "", "")]


# ---- formato de la plantilla ----

def test_crear_plantilla_tiene_hojas_marcadores_y_lista_de_tipos():
    libro = load_workbook(io.BytesIO(crear_plantilla(SNPS)))
    assert libro.sheetnames == ["Instrucciones", "Animales", "ADN"]

    instrucciones = [f[0] for f in libro["Instrucciones"].iter_rows(values_only=True)]
    assert instrucciones[0] == "Cómo usar esta plantilla"
    assert instrucciones[-1] == "Funciona solo con ganado Holstein."
    assert len(instrucciones) == 10

    animales = libro["Animales"]
    assert [c.value for c in animales[1]] == ["id_animal", "tipo", "nombre"]
    assert animales["A1"].font.b and animales.freeze_panes == "A2"
    assert animales.max_row == 1  # sin animales
    lista = animales.data_validations.dataValidation[0]
    assert lista.type == "list" and lista.formula1 == '"Toro,Vaca,Vaquilla"'
    assert "B2" in lista.sqref

    adn = libro["ADN"]
    assert [f[0] for f in adn.iter_rows(values_only=True)] == ["marcador", *SNPS]
    assert adn.max_column == 1 and adn.freeze_panes == "B2"


def test_ejemplo_en_excel_da_lo_mismo_que_el_csv():
    paq, csv = _paquete(), _ejemplo_csv()
    df = leer_excel(crear_ejemplo_excel(csv, SNPS), SNPS)
    assert list(df.columns[:3]) == ["id_animal", "tipo", "nombre"]
    assert list(df.columns[3:]) == SNPS
    assert evaluar(df, paq) == evaluar(csv, paq)


def test_leer_excel_normaliza_tipo_nombre_e_ids_numericos():
    animales = [*VAQUILLAS, (2042, "TORO", None)]
    df = leer_excel(_excel(animales, columnas=["V-001", "V-002", "V-003", 2042]), SNPS)
    assert df["id_animal"].tolist() == ["V-001", "V-002", "V-003", "2042"]
    assert df["tipo"].tolist() == ["Vaquilla", "Vaquilla", "", "Toro"]
    assert df["nombre"].tolist() == ["Lucerito", "", "", ""]
    resultado = evaluar(df, _paquete())
    assert resultado[0]["nombre"] == "Lucerito" and resultado[0]["tipo"] == "Vaquilla"


# ---- un test por cada mensaje de error ----

@pytest.mark.parametrize("contenido, mensaje", [
    (lambda: _excel(VAQUILLAS, hojas=("Animales",)), "La plantilla debe tener las hojas Animales y ADN."),
    (lambda: _excel(VAQUILLAS, columnas=["V-001", "V-002"]),
     "El animal V-003 está en la hoja Animales pero no tiene columna en la hoja ADN."),
    (lambda: _excel(VAQUILLAS, columnas=["V-001", "V-002", "V-003", "V-009"]),
     "La columna V-009 de la hoja ADN no está en la hoja Animales."),
    (lambda: _excel([("V-001", "Vaca", ""), ("V-002", "Buey", "")]),
     "El tipo de V-002 debe ser Toro, Vaca o Vaquilla (o dejarse vacío)."),
    (lambda: _excel([], columnas=[]), "La hoja Animales no tiene animales."),
])
def test_leer_excel_errores(contenido, mensaje):
    with pytest.raises(ErrorGenotipos) as error:
        leer_excel(contenido(), SNPS)
    assert str(error.value) == mensaje


def test_marcador_faltante_en_excel_lo_valida_leer_genotipos():
    df = leer_excel(_excel(VAQUILLAS, quitar_marcador="SNP7"), SNPS)
    with pytest.raises(ErrorGenotipos, match="le falta 1 marcador"):
        evaluar(df, _paquete())


def test_archivo_que_no_es_excel():
    with pytest.raises(ErrorGenotipos, match="No se pudo abrir el Excel"):
        leer_excel(b"PK esto no es un excel", SNPS)


# ---- API ----

@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("BOVIGEN_RAIZ", str(tmp_path))
    ruta = tmp_path / main.PAQUETE
    ruta.parent.mkdir(parents=True)
    np.savez(ruta, **_paquete())
    ejemplo = tmp_path / main.EJEMPLO
    ejemplo.parent.mkdir(parents=True)
    _ejemplo_csv().to_csv(ejemplo, index=False)
    return TestClient(main.app)


def _subir(cliente, nombre, contenido):
    return cliente.post("/api/evaluar", files={"archivo": (nombre, contenido)})


def test_api_evaluar_excel_valido(cliente):
    resp = _subir(cliente, "mis_animales.xlsx", _excel(VAQUILLAS))
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["demo"] is False and datos["total"] == 3
    assert [(a["id"], a["tipo"], a["nombre"]) for a in datos["animales"]] == [
        ("V-001", "Vaquilla", "Lucerito"), ("V-002", "Vaquilla", ""), ("V-003", "", "")]


def test_api_evaluar_excel_con_errores_da_422(cliente):
    resp = _subir(cliente, "mis_animales.xlsx", _excel(VAQUILLAS, columnas=["V-001", "V-002"]))
    assert resp.status_code == 422
    assert resp.json()["detail"] == (
        "El animal V-003 está en la hoja Animales pero no tiene columna en la hoja ADN.")


@pytest.mark.parametrize("nombre, contenido", [
    ("notas.txt", "hola, estos son mis animales\nlucerito\n".encode()),
    ("foto.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00"),
])
def test_api_evaluar_ni_csv_ni_excel_da_422(cliente, nombre, contenido):
    resp = _subir(cliente, nombre, contenido)
    assert resp.status_code == 422
    assert resp.json()["detail"] == main.NI_CSV_NI_EXCEL


@pytest.mark.parametrize("ruta, archivo", [
    ("/api/plantilla", "plantilla_bovigen.xlsx"),
    ("/api/ejemplo/excel", "ejemplo_bovigen.xlsx"),
])
def test_api_descarga_excel(cliente, ruta, archivo):
    resp = cliente.get(ruta)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == main.XLSX
    assert archivo in resp.headers["content-disposition"]
    libro = load_workbook(io.BytesIO(resp.content), read_only=True)
    assert libro.sheetnames == ["Instrucciones", "Animales", "ADN"]


def test_api_ejemplo_excel_da_los_mismos_animales_que_el_csv(cliente):
    excel = cliente.get("/api/ejemplo/excel").content
    subido = _subir(cliente, "ejemplo_bovigen.xlsx", excel).json()["animales"]
    ejemplo = cliente.get("/api/ejemplo").json()["animales"]
    assert subido == ejemplo
