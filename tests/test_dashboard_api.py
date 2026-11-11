"""Tests del backend del dashboard (solo lectura de CSV)."""
import io
import statistics

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from dashboard.backend.app import main
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


# ---- endpoints para el ganadero ----

SNPS = [f"SNP{j + 1}" for j in range(6)]


def _genotipos(n=3):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.integers(0, 3, size=(n, len(SNPS))), columns=SNPS)
    df.insert(0, "id_animal", [f"Anim{i + 1}" for i in range(n)])
    return df


def _csv(df):
    return df.to_csv(index=False).encode()


@pytest.fixture
def ganadero(tmp_path, monkeypatch):
    """Raíz falsa con un paquete genómico pequeño y un ejemplo de 3 animales."""
    monkeypatch.setenv("BOVIGEN_RAIZ", str(tmp_path))
    rng = np.random.default_rng(1)
    X_ref = rng.integers(0, 3, size=(50, len(SNPS))).astype(np.float32)
    paq = {"snps": np.array(SNPS), "media_snp": X_ref.mean(axis=0)}
    for r in ("fpro", "mkg", "scs"):
        coef = rng.normal(size=len(SNPS)).astype(np.float32)
        paq.update({f"coef_{r}": coef, f"media_pred_{r}": np.array(1.0),
                    f"ref_{r}": (X_ref - paq["media_snp"]) @ coef + 1.0})
    ruta = tmp_path / main.PAQUETE
    ruta.parent.mkdir(parents=True)
    np.savez(ruta, **paq)
    _escribir(tmp_path, main.EJEMPLO, _genotipos())
    return TestClient(app), tmp_path


def test_ejemplo_demo_con_cuatro_prioridades(ganadero):
    client, _ = ganadero
    datos = client.get("/api/ejemplo").json()
    assert datos["demo"] is True and datos["total"] == 3
    assert [a["id"] for a in datos["animales"]] == ["Anim1", "Anim2", "Anim3"]
    for animal in datos["animales"]:
        assert set(animal["por_prioridad"]) == {"balanceado", "grasa", "leche", "ubre"}


def test_ejemplo_archivo_se_descarga(ganadero):
    client, _ = ganadero
    resp = client.get("/api/ejemplo/archivo")
    assert resp.status_code == 200
    assert "ejemplo_adn.csv" in resp.headers["content-disposition"]


def test_evaluar_csv_valido_y_con_marcador_faltante(ganadero):
    client, _ = ganadero
    resp = client.post("/api/evaluar", files={"archivo": ("adn.csv", _csv(_genotipos(2)))})
    assert resp.status_code == 200
    assert resp.json()["demo"] is False and resp.json()["total"] == 2

    malo = _genotipos(2).drop(columns="SNP4")
    resp = client.post("/api/evaluar", files={"archivo": ("adn.csv", _csv(malo))})
    assert resp.status_code == 422
    assert "le falta 1 marcador" in resp.json()["detail"]
    assert "SNP" not in resp.json()["detail"]


def test_evaluar_archivo_vacio_o_muy_grande(ganadero, monkeypatch):
    client, _ = ganadero
    resp = client.post("/api/evaluar", files={"archivo": ("adn.csv", b"")})
    assert resp.status_code == 422
    monkeypatch.setattr(main, "MAX_BYTES", 10)
    resp = client.post("/api/evaluar", files={"archivo": ("adn.csv", _csv(_genotipos()))})
    assert resp.status_code == 413


def test_evaluar_sin_paquete_da_503(ganadero):
    client, raiz = ganadero
    (raiz / main.PAQUETE).unlink()
    main._paquete.cache_clear()
    resp = client.post("/api/evaluar", files={"archivo": ("adn.csv", _csv(_genotipos()))})
    assert resp.status_code == 503


PRED_FALSA = {"peso_kg": 490.9, "altura_cruz_cm": 122.4, "perimetro_toracico_cm": 185.2,
              "largo_oblicuo_cm": 151.0, "largo_cadera_cm": 44.3,
              "error": {"peso_kg": 83.8, "altura_cruz_cm": 7.1, "perimetro_toracico_cm": 11.3,
                        "largo_oblicuo_cm": 11.9, "largo_cadera_cm": 4.5}}
FOTOS = {"lateral": ("1_lat.jpg", b"foto"), "posterior": ("1_pos.jpg", b"foto")}


@pytest.fixture
def medidor(ganadero, monkeypatch):
    """Con un modelo de visión 'presente' y predecir() reemplazado (no carga torch)."""
    client, raiz = ganadero
    (raiz / main.MODELO_VISION).parent.mkdir(parents=True)
    (raiz / main.MODELO_VISION).write_bytes(b"falso")
    llamadas = []

    def falso(ruta_lat, ruta_pos, ruta_modelo):
        llamadas.append((ruta_lat.read_bytes(), ruta_pos.read_bytes(), ruta_modelo))
        return PRED_FALSA

    monkeypatch.setattr(main, "_predictor", lambda: falso)
    return client, raiz, llamadas, monkeypatch


def test_medir_devuelve_peso_con_rango_y_medidas(medidor):
    client, raiz, llamadas, _ = medidor
    datos = client.post("/api/medir", files=FOTOS).json()
    assert datos["peso"]["valor"] == 490.9
    assert datos["peso"]["min"] == pytest.approx(407.1)
    assert datos["peso"]["max"] == pytest.approx(574.7)
    assert [m["nombre"] for m in datos["medidas"]] == [
        "Altura a la cruz", "Perímetro del tórax", "Largo del cuerpo", "Largo de cadera"]
    assert datos["medidas"][2] == {"clave": "largo_oblicuo_cm", "nombre": "Largo del cuerpo",
                                   "valor": 151.0, "error": 11.9, "unidad": "cm"}
    assert llamadas == [(b"foto", b"foto", raiz / main.MODELO_VISION)]


def test_medir_foto_sin_vaca_da_422(medidor):
    client, _, _, monkeypatch = medidor

    def sin_vaca(*args, **kwargs):
        raise ValueError("No se encontro la vaca en la foto lateral.")

    monkeypatch.setattr(main, "_predictor", lambda: sin_vaca)
    resp = client.post("/api/medir", files=FOTOS)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "No se encontro la vaca en la foto lateral."


def test_medir_sin_modelo_da_503(ganadero):
    client, _ = ganadero
    resp = client.post("/api/medir", files=FOTOS)
    assert resp.status_code == 503
    assert resp.json()["detail"] == "El medidor por foto no está disponible"


def _metricas_cnn(raiz):
    _escribir(raiz, main.METRICAS_CNN, pd.DataFrame({
        "medida": ["altura_cruz_cm", "peso_kg"], "rmse": [7.08, 83.79],
        "mae": [5.3, 71.8], "r_pearson": [0.49, 0.40]}))


def test_medir_ejemplos_marca_dentro_del_margen(ganadero):
    client, raiz = ganadero
    _metricas_cnn(raiz)
    _escribir(raiz, main.PREDICCIONES_CNN, pd.DataFrame({
        "id_animal_img": [1, 2, 3, 4], "peso_kg_real": [545.0, 507.0, 450.0, 600.0],
        "peso_kg_pred": [481.6, 477.8, 548.8, 590.0]}))
    datos = client.get("/api/medir/ejemplos").json()
    assert datos["error_kg"] == 83.8
    assert [e["dentro"] for e in datos["ejemplos"]] == [True, True, False]
    assert datos["ejemplos"][0]["foto_lateral"] == "/api/medir/foto/1/lat"
    assert len(datos["todas"]) == 4


def test_medir_foto_solo_las_de_muestra(ganadero):
    client, raiz = ganadero
    (raiz / "data/sample/imagenes").mkdir(parents=True)
    (raiz / "data/sample/imagenes/1_lat.jpg").write_bytes(b"jpg")
    assert client.get("/api/medir/foto/1/lat").status_code == 200
    assert client.get("/api/medir/foto/9/lat").status_code == 404
    assert client.get("/api/medir/foto/1/arriba").status_code == 404


def _resumen_e6(raiz):
    filas = []
    for esc, rasgos in (("holstein", ("fpro", "mkg", "scs")), ("sim_n125", ("fenotipo",)),
                        ("sim_n500", ("fenotipo",)), ("sim_n2000", ("fenotipo",))):
        for rasgo in rasgos:
            filas.append({"escenario": esc, "rasgo": rasgo, "ruido": "base", "modelo": "ridge",
                          "r_media": {"fpro": 0.78, "mkg": 0.69, "scs": 0.31}.get(rasgo, 0.1)})
            filas.append({"escenario": esc, "rasgo": rasgo, "ruido": "base", "modelo": "gblup",
                          "r_media": {"holstein": 0.66, "sim_n125": 0.165,
                                      "sim_n500": 0.33, "sim_n2000": 0.594}[esc]})
    _escribir(raiz, main.RESUMEN_E6, pd.DataFrame(filas))


def test_confianza(ganadero):
    client, raiz = ganadero
    _resumen_e6(raiz)
    _metricas_cnn(raiz)
    datos = client.get("/api/confianza").json()
    # 10 × (0.5 + asin(r)/π): 0.78 -> 7.85 -> 8; 0.69 -> 7.42 -> 7; 0.31 -> 6.0 -> 6
    assert [a["de_cada_10"] for a in datos["aciertos"]] == [8, 7, 6]
    assert [a["rasgo"] for a in datos["aciertos"]] == ["Grasa", "Leche", "Ubre sana"]
    assert [t["nivel"] for t in datos["tamanos"]] == ["Baja", "Media", "Media", "Alta"]
    assert [t["ancho"] for t in datos["tamanos"]] == [25, 50, 90, 100]
    assert datos["tamanos"][3]["nombre"] == "5,024 Holstein"
    assert (datos["error_peso_kg"], datos["error_altura_cm"]) == (84, 7)


def test_confianza_sin_resultados_da_503(ganadero):
    client, _ = ganadero
    resp = client.get("/api/confianza")
    assert resp.status_code == 503
    assert "resumen_e6.csv" in resp.json()["detail"]
