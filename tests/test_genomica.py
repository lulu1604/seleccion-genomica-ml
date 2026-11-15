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
            zonas = [z for z in animal["zonas"][nombre] if not z["resto"]]  # "Resto": test aparte
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
            filas = animal["zonas"][nombre]
            valores = [z["valor"] for z in filas if not z["resto"]]
            np.testing.assert_allclose(valores, esperado, atol=1e-4)
            # y con la fila "Resto de su ADN" la cuenta cuadra con la predicción
            total = sum(z["valor"] for z in filas) + float(paq[f"media_pred_{r}"])
            assert total == pytest.approx(float(pred[i]), abs=1e-3)


def test_nombre_zona():
    assert nombre_zona(25091)["zona"] == "Zona del cromosoma 14"
    assert "DGAT1" in nombre_zona(25091)["detalle"]
    assert nombre_zona(100) == {"zona": "Otra zona del ADN", "detalle": "Sin gen conocido"}


def test_cada_zona_trae_sus_campos(paq):
    animal = evaluar(_df(np.ones((1, N_SNP))), paq)[0]
    for zonas in animal["zonas"].values():
        for z in zonas:
            assert set(z) == {"marcador", "zona", "detalle", "efecto", "valor", "gen", "cromosoma", "resto"}


# ---- con mapa de marcadores (cromosoma y Mb en el paquete) ----

# 20 marcadores: cromosoma 1 (SNP1-7), 2 (SNP8-14) y 3 (SNP15-20); Mb = 0, 1, 2… dentro de cada uno
CROMOSOMA = np.array([1] * 7 + [2] * 7 + [3] * 6, dtype=np.int8)
MB = np.array(list(range(7)) * 2 + list(range(6)), dtype=np.float32)
GEN_PRUEBA = {"cromosoma": 1, "desde": 1.0, "hasta": 3.0, "gen": "PRUEBA", "detalle": {
    "fpro": "Gen de prueba en la grasa", "mkg": "Gen de prueba en la leche", "_": "Gen de prueba"}}
EN_GEN = [1, 2, 3]  # SNP2-SNP4: cromosoma 1, Mb 1 a 3


@pytest.fixture
def paq_mapa(paq):
    return {**paq, "cromosoma": CROMOSOMA, "mb": MB}


def _animales_varios(paq):
    filas = [_extremo(paq, "fpro", sube=True), _extremo(paq, "mkg", sube=False)]
    return _df(filas + list(np.random.default_rng(7).integers(0, 3, size=(4, N_SNP))))


@pytest.mark.parametrize("con_mapa", [True, False])
def test_resto_de_su_adn_es_la_ultima_fila_y_la_cuenta_cuadra(paq, paq_mapa, con_mapa):
    paquete = paq_mapa if con_mapa else paq
    df = _animales_varios(paq)
    Xc = df[SNPS].to_numpy(dtype=np.float32) - paq["media_snp"]
    for i, animal in enumerate(evaluar(df, paquete)):
        for r, nombre in (("fpro", "grasa"), ("mkg", "leche"), ("scs", "ubre sana")):
            filas = animal["zonas"][nombre]
            assert [z["resto"] for z in filas].count(True) == 1
            ultima = filas[-1]
            assert ultima["resto"] and ultima["zona"] == "Resto de su ADN"
            assert ultima["detalle"] == "Miles de zonas pequeñas sumadas"
            assert ultima["efecto"] == ("sube" if ultima["valor"] >= 0 else "baja")
            aporte = Xc[i] * paq[f"coef_{r}"]
            assert sum(z["valor"] for z in filas) == pytest.approx(float(aporte.sum()), abs=1e-3)


def test_ventana_de_gen_es_una_fila_con_detalle_segun_el_rasgo(paq_mapa, monkeypatch):
    monkeypatch.setattr(genomica, "GENES", [GEN_PRUEBA])
    # los marcadores del gen suman mucho entre los tres, cada uno por separado poco
    aporte = np.full(N_SNP, 0.01, dtype=np.float32)
    aporte[EN_GEN] = [0.5, 0.4, 0.45]
    aporte[10] = -0.2
    for rasgo, detalle in (("fpro", "Gen de prueba en la grasa"), ("mkg", "Gen de prueba en la leche"),
                           ("scs", "Gen de prueba")):
        filas = genomica._zonas_ficha(aporte, SNPS, 3, rasgo=rasgo, paq=paq_mapa)
        del_gen = [z for z in filas if z["gen"] == "PRUEBA"]
        assert len(del_gen) == 1
        z = del_gen[0]
        assert filas[0] is z  # la suma del gen es la que más sube
        assert z["valor"] == pytest.approx(1.35, abs=1e-4)
        assert z["zona"] == "Zona del cromosoma 1" and z["cromosoma"] == 1
        assert z["detalle"] == detalle
        assert z["marcador"] == "SNP2"  # el de mayor aporte dentro del gen
        assert all(SNPS.index(f["marcador"]) not in EN_GEN for f in filas if f is not z and not f["resto"])


def test_ventana_de_gen_en_la_ficha_completa(paq, paq_mapa, monkeypatch):
    monkeypatch.setattr(genomica, "GENES", [GEN_PRUEBA])
    df = _animales_varios(paq)
    Xc = df[SNPS].to_numpy(dtype=np.float32) - paq["media_snp"]
    vista = 0
    for i, animal in enumerate(evaluar(df, paq_mapa)):
        aporte = Xc[i] * paq["coef_fpro"]
        del_gen = [z for z in animal["zonas"]["grasa"] if z["gen"] == "PRUEBA"]
        assert len(del_gen) <= 1
        for z in del_gen:
            vista += 1
            assert z["valor"] == pytest.approx(aporte[EN_GEN].sum(), abs=1e-4)
    assert vista > 0


def test_zonas_sin_gen_dicen_su_cromosoma(paq_mapa, monkeypatch):
    monkeypatch.setattr(genomica, "GENES", [])
    animal = evaluar(_animales_varios(paq_mapa), paq_mapa)[0]
    for filas in animal["zonas"].values():
        for z in filas[:-1]:
            j = SNPS.index(z["marcador"])
            assert z["zona"] == f"Zona del cromosoma {CROMOSOMA[j]}"
            assert z["cromosoma"] == CROMOSOMA[j]
            assert z["detalle"] == "Sin gen identificado" and z["gen"] == "" and not z["resto"]


def test_sin_mapa_usa_el_respaldo_por_numero_de_marcador(paq):
    animal = evaluar(_animales_varios(paq), paq)[0]
    for filas in animal["zonas"].values():
        for z in filas[:-1]:
            assert z["zona"] == "Otra zona del ADN" and z["detalle"] == "Sin gen conocido"
            assert z["cromosoma"] == 0 and z["gen"] == ""


@pytest.mark.parametrize("aporte", [
    [0.3, 0.2, 0.1],          # todas suben: la que "más baja" ya está entre las que suben
    [0.3, -0.1, 0.2, 0.05],
])
def test_ninguna_fila_se_repite(aporte, monkeypatch):
    monkeypatch.setattr(genomica, "GENES", [])
    n = len(aporte)
    paq = {"cromosoma": CROMOSOMA[:n], "mb": MB[:n]}
    filas = genomica._zonas_ficha(np.array(aporte, dtype=np.float32), SNPS[:n], 3, paq=paq)
    marcadores = [z["marcador"] for z in filas if not z["resto"]]
    assert len(marcadores) == len(set(marcadores))
    assert sum(z["valor"] for z in filas) == pytest.approx(sum(aporte), abs=1e-4)


def test_ejemplo_desempata_por_numero_de_animal():
    puntaje = np.array([50, 97, 97, 4, 4])
    ids = ["Anim30", "Anim20", "Anim7", "Anim900", "Anim12"]
    # entre los empatados gana el número más bajo (7 antes que 20, no orden de texto)
    assert elegir_ejemplo(puntaje, ids, [97, 97, 4]) == [2, 1, 4]
    # y no depende del orden en que vengan los animales
    al_reves = elegir_ejemplo(puntaje[::-1], ids[::-1], [97, 97, 4])
    assert [ids[::-1][k] for k in al_reves] == ["Anim7", "Anim20", "Anim12"]
