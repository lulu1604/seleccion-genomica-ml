"""Tests de la evaluación genómica del dashboard, con un paquete falso (sin datos reales)."""
import numpy as np
import pandas as pd
import pytest

from dashboard.backend.app import genomica
from dashboard.backend.app.genomica import (
    PESOS, RASGOS, ErrorGenotipos, categoria, etiqueta, evaluar, leer_genotipos, nombre_zona,
    percentil,
)
from dashboard.backend.preparar_genomica import elegir_ejemplo

N_SNP = 20
N_REF = 200
# cada rasgo depende de sus propios marcadores, para poder armar animales extremos
BLOQUES = {"fpro": range(0, 7), "mkg": range(7, 14), "scs": range(14, 20)}
SNPS = [f"SNP{j + 1}" for j in range(N_SNP)]


def _paquete_falso():
    rng = np.random.default_rng(0)
    X_ref = rng.integers(0, 3, size=(N_REF, N_SNP)).astype(np.float32)
    media_snp = X_ref.mean(axis=0)
    paq = {"snps": np.array(SNPS), "media_snp": media_snp}
    for r, media_pred in zip(RASGOS, (0.5, 300.0, 3.0)):
        coef = np.zeros(N_SNP, dtype=np.float32)
        coef[list(BLOQUES[r])] = rng.choice([-1.0, 1.0], len(BLOQUES[r])) * rng.uniform(0.5, 1.5, len(BLOQUES[r]))
        paq[f"coef_{r}"] = coef
        paq[f"media_pred_{r}"] = np.array(media_pred)
        paq[f"ref_{r}"] = (X_ref - media_snp) @ coef + media_pred
    return paq


def _df(filas, ids=None):
    df = pd.DataFrame(np.asarray(filas, dtype=int), columns=SNPS)
    df.insert(0, "id_animal", ids or [f"A{i}" for i in range(len(df))])
    return df


def _prediccion(paq, df, r):
    Xc = df[SNPS].to_numpy(dtype=np.float32) - paq["media_snp"]
    return Xc @ paq[f"coef_{r}"] + paq[f"media_pred_{r}"]


def _extremo(paq, r, sube):
    """Genotipo que lleva el rasgo r al máximo (sube=True) o al mínimo, en sus marcadores."""
    g = np.ones(N_SNP, dtype=int)
    for j in BLOQUES[r]:
        positivo = paq[f"coef_{r}"][j] > 0
        g[j] = 2 if positivo == sube else 0
    return g


@pytest.fixture
def paq():
    return _paquete_falso()


def test_percentil_extremos(paq):
    ref = paq["ref_fpro"]
    assert percentil(np.array([ref.max()]), ref)[0] == 100
    assert percentil(np.array([ref.min() - 1]), ref)[0] == 0


@pytest.mark.parametrize("puntaje, esperado", [
    (90, ("Élite", "Embriones")),
    (89, ("Bueno", "Semen sexado")),
    (25, ("Regular", "Semen convencional")),
    (24, ("Bajo", "Semen de carne")),
])
def test_categoria_limites(puntaje, esperado):
    assert categoria(puntaje) == esperado


@pytest.mark.parametrize("p, esperado", [
    ({"fpro": 80, "mkg": 76, "scs": 75}, "bueno en las 3"),
    ({"fpro": 20, "mkg": 70, "scs": 30}, "destaca en leche"),
    ({"fpro": 60, "mkg": 55, "scs": 50}, "sobre el promedio"),
    ({"fpro": 40, "mkg": 45, "scs": 30}, "bajo el promedio"),
])
def test_etiqueta_casos(p, esperado):
    assert etiqueta(p) == esperado


def test_scs_alto_es_ubre_mas_sana(paq):
    # escala RZS: más alto = menos células somáticas = ubre más sana (no se invierte)
    df = _df([_extremo(paq, "scs", sube=True), _extremo(paq, "scs", sube=False)])
    scs = _prediccion(paq, df, "scs")
    assert scs[0] > scs[1]
    sana, enferma = evaluar(df, paq)
    assert sana["percentiles"]["ubre sana"] > enferma["percentiles"]["ubre sana"]


def test_prioridad_grasa_no_es_prioridad_leche(paq):
    grasa = _extremo(paq, "fpro", sube=True)
    grasa[list(BLOQUES["mkg"])] = _extremo(paq, "mkg", sube=False)[list(BLOQUES["mkg"])]
    lechera = _extremo(paq, "mkg", sube=True)
    lechera[list(BLOQUES["fpro"])] = _extremo(paq, "fpro", sube=False)[list(BLOQUES["fpro"])]
    df = _df([grasa, lechera, np.ones(N_SNP)], ids=["grasa", "lechera", "promedio"])

    animales = {a["id"]: a for a in evaluar(df, paq)}
    assert animales["grasa"]["por_prioridad"]["grasa"]["puesto"] == 1
    assert animales["grasa"]["por_prioridad"]["leche"]["puesto"] != 1
    assert all(set(a["por_prioridad"]) == set(PESOS) for a in animales.values())


def _sin_id(df):
    return df.drop(columns="id_animal")


def _sin_marcador(df):
    return df.drop(columns="SNP5")


def _con_un_3(df):
    df.loc[0, "SNP2"] = 3
    return df


def _con_celda_vacia(df):
    df["SNP3"] = df["SNP3"].astype(float)
    df.loc[1, "SNP3"] = np.nan
    return df


def _ids_repetidos(df):
    df["id_animal"] = "A0"
    return df


def _vacio(df):
    return df.iloc[0:0]


@pytest.mark.parametrize("estropear", [
    _sin_id, _sin_marcador, _con_un_3, _con_celda_vacia, _ids_repetidos, _vacio,
])
def test_leer_genotipos_rechaza_archivos_malos(estropear):
    df = _df(np.ones((3, N_SNP)))
    with pytest.raises(ErrorGenotipos):
        leer_genotipos(estropear(df), SNPS)


@pytest.mark.parametrize("quitar, texto", [
    (["SNP4"], "le falta 1 marcador del ADN de los 20"),
    (["SNP4", "SNP9", "SNP15"], "le faltan 3 marcadores del ADN de los 20"),
])
def test_mensaje_de_marcadores_faltantes_sin_nombres(quitar, texto):
    df = _df(np.ones((3, N_SNP))).drop(columns=quitar)
    with pytest.raises(ErrorGenotipos) as error:
        leer_genotipos(df, SNPS)
    assert texto in str(error.value)
    assert "SNP" not in str(error.value)


def test_ficha_agrupa_cada_zona_conocida_en_una_fila(paq, monkeypatch):
    # zona de prueba: marcadores SNP2..SNP5 (posiciones 2 a 5, dentro del bloque de grasa)
    monkeypatch.setattr(genomica, "ZONAS_CONOCIDAS", [(2, 5, "Zona de prueba", "Gen de prueba")])
    dentro = list(range(1, 5))
    filas = [_extremo(paq, "fpro", sube=True), _extremo(paq, "fpro", sube=False)]
    filas += list(np.random.default_rng(2).integers(0, 3, size=(4, N_SNP)))
    df = _df(filas)
    Xc = df[SNPS].to_numpy(dtype=np.float32) - paq["media_snp"]
    vista = 0
    for r, nombre in (("fpro", "grasa"), ("mkg", "leche"), ("scs", "ubre sana")):
        for i, animal in enumerate(evaluar(df, paq)):
            aporte = Xc[i] * paq[f"coef_{r}"]
            zonas = animal["zonas"][nombre]
            de_la_zona = [z for z in zonas if z["zona"] == "Zona de prueba"]
            assert len(de_la_zona) <= 1
            for z in de_la_zona:
                vista += 1
                assert z["valor"] == pytest.approx(aporte[dentro].sum(), abs=1e-4)
                assert z["marcador"] == SNPS[dentro[int(np.argmax(np.abs(aporte[dentro])))]]
            for z in zonas:
                if z["zona"] != "Zona de prueba":
                    j = SNPS.index(z["marcador"])
                    assert j not in dentro
                    assert z["valor"] == pytest.approx(aporte[j], abs=1e-4)
            # orden: la suma de la zona compite como una fila más
            candidatos = np.sort([aporte[dentro].sum()] + [aporte[j] for j in range(N_SNP) if j not in dentro])
            esperado = list(candidatos[::-1][:3]) + [candidatos[0]]
            np.testing.assert_allclose([z["valor"] for z in zonas], esperado, atol=1e-4)
    assert vista > 0


def test_aportes_mas_promedio_dan_la_prediccion(paq):
    df = _df(np.random.default_rng(1).integers(0, 3, size=(4, N_SNP)))
    Xc = df[SNPS].to_numpy(dtype=np.float32) - paq["media_snp"]
    animales = evaluar(df, paq)
    for r, nombre in (("fpro", "grasa"), ("mkg", "leche"), ("scs", "ubre sana")):
        pred = _prediccion(paq, df, r)
        aportes = Xc * paq[f"coef_{r}"]
        np.testing.assert_allclose(aportes.sum(axis=1) + paq[f"media_pred_{r}"], pred, rtol=1e-5)
        # las zonas que muestra la ficha son esos mismos aportes, sin invertir
        for i, animal in enumerate(animales):
            esperado = np.sort(aportes[i])
            esperado = list(esperado[::-1][:3]) + [esperado[0]]
            valores = [z["valor"] for z in animal["zonas"][nombre]]
            np.testing.assert_allclose(valores, esperado, atol=1e-4)


def test_nombre_zona():
    assert nombre_zona(25091)["zona"] == "Zona del cromosoma 14"
    assert "DGAT1" in nombre_zona(25091)["detalle"]
    assert nombre_zona(100) == {"zona": "Otra zona del ADN", "detalle": "Sin gen conocido"}


def test_cada_zona_trae_sus_campos(paq):
    animal = evaluar(_df(np.ones((1, N_SNP))), paq)[0]
    for zonas in animal["zonas"].values():
        for z in zonas:
            assert set(z) == {"marcador", "zona", "detalle", "efecto", "valor"}


def test_ejemplo_desempata_por_numero_de_animal():
    puntaje = np.array([50, 97, 97, 4, 4])
    ids = ["Anim30", "Anim20", "Anim7", "Anim900", "Anim12"]
    # entre los empatados gana el número más bajo (7 antes que 20, no orden de texto)
    assert elegir_ejemplo(puntaje, ids, [97, 97, 4]) == [2, 1, 4]
    # y no depende del orden en que vengan los animales
    al_reves = elegir_ejemplo(puntaje[::-1], ids[::-1], [97, 97, 4])
    assert [ids[::-1][k] for k in al_reves] == ["Anim7", "Anim20", "Anim12"]
