"""API de solo lectura del dashboard BOVIGEN. Ver dashboard/CONTRATO_API.md."""
import io
import math
import tempfile
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from .datos import FUENTES, a_registros, leer, raiz, resumen
from .genomica import ErrorGenotipos, cargar_paquete, evaluar

app = FastAPI(title="BOVIGEN API")

PAQUETE = "models/genomica/ridge_holstein.npz"
EJEMPLO = "data/sample/genotipos_ejemplo.csv"
MODELO_VISION = "models/vision/ensamble.joblib"
RESUMEN_E6 = "results/resumen_e6.csv"
METRICAS_CNN = "results/vision/metricas_cnn.csv"
PREDICCIONES_CNN = "results/vision/predicciones_cnn.csv"
MAX_BYTES = 60 * 1024 * 1024
N_HOLSTEIN = 5024  # animales del escenario holstein (escenario_n en results/parciales)

# claves de src/vision/predecir.py -> nombre para personas, en el orden de la pantalla
MEDIDAS = [
    ("peso_kg", "Peso", "kg"),
    ("altura_cruz_cm", "Altura a la cruz", "cm"),
    ("perimetro_toracico_cm", "Perímetro del tórax", "cm"),
    ("largo_oblicuo_cm", "Largo del cuerpo", "cm"),
    ("largo_cadera_cm", "Largo de cadera", "cm"),
]
RASGOS_CONFIANZA = [("fpro", "Grasa"), ("mkg", "Leche"), ("scs", "Ubre sana")]
TAMANOS = [("sim_n125", "125 animales"), ("sim_n500", "500 animales"),
           ("sim_n2000", "2,000 animales"), ("holstein", f"{N_HOLSTEIN:,} Holstein")]


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


# ---- para el ganadero: evaluación genómica ----

@lru_cache(maxsize=4)
def _paquete(ruta: str) -> dict:
    return cargar_paquete(ruta)


def _evaluar(df: pd.DataFrame, demo: bool) -> dict:
    try:
        paq = _paquete(str(raiz() / PAQUETE))
    except FileNotFoundError:
        raise HTTPException(503, "La evaluación genética no está disponible")
    try:
        animales = evaluar(df, paq)
    except ErrorGenotipos as e:
        raise HTTPException(422, str(e))
    return {"demo": demo, "total": len(animales), "animales": animales}


def _ruta_ejemplo() -> Path:
    ruta = raiz() / EJEMPLO
    if not ruta.is_file():
        raise HTTPException(404, "No hay archivo de ejemplo")
    return ruta


@lru_cache(maxsize=2)
def _ejemplo_evaluado(ruta: str, _version: int) -> dict:
    """El ejemplo no cambia: se evalúa una vez (`_version` = mtime, por si se regenera)."""
    return _evaluar(pd.read_csv(ruta), demo=True)


@app.get("/api/ejemplo")
def ejemplo():
    ruta = _ruta_ejemplo()
    return _ejemplo_evaluado(str(ruta), ruta.stat().st_mtime_ns)


@app.get("/api/ejemplo/archivo")
def ejemplo_archivo():
    return FileResponse(_ruta_ejemplo(), media_type="text/csv", filename="ejemplo_adn.csv")


def _leer_subida(archivo: UploadFile) -> bytes:
    contenido = archivo.file.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, f"El archivo pesa más de {MAX_BYTES // (1024 * 1024)} MB.")
    return contenido


@app.post("/api/evaluar")
def evaluar_archivo(archivo: UploadFile = File(...)):
    contenido = _leer_subida(archivo)
    try:
        df = pd.read_csv(io.BytesIO(contenido))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        raise HTTPException(422, "No se pudo leer el archivo. Debe ser un CSV como el de ejemplo.")
    return _evaluar(df, demo=False)


# ---- para el ganadero: medición por foto ----

def _predictor():
    """Importa predecir() recién al usarla: así el arranque y los tests no cargan torch."""
    from src.vision.predecir import predecir
    return predecir


def _medida(clave: str, nombre: str, unidad: str, pred: dict) -> dict:
    return {"clave": clave, "nombre": nombre, "valor": pred[clave],
            "error": pred["error"][clave], "unidad": unidad}


@app.post("/api/medir")
def medir(lateral: UploadFile = File(...), posterior: UploadFile = File(...)):
    ruta_modelo = raiz() / MODELO_VISION
    no_disponible = HTTPException(503, "El medidor por foto no está disponible")
    if not ruta_modelo.is_file():
        raise no_disponible
    with tempfile.TemporaryDirectory() as carpeta:
        rutas = []
        for nombre, foto in (("lateral", lateral), ("posterior", posterior)):
            ruta = Path(carpeta) / f"{nombre}{Path(foto.filename or '').suffix or '.jpg'}"
            ruta.write_bytes(_leer_subida(foto))
            rutas.append(ruta)
        try:
            pred = _predictor()(rutas[0], rutas[1], ruta_modelo=ruta_modelo)
        except ImportError:
            raise no_disponible
        except ValueError as e:
            raise HTTPException(422, str(e))
    peso = _medida(*MEDIDAS[0], pred)
    peso.update(min=round(peso["valor"] - peso["error"], 1), max=round(peso["valor"] + peso["error"], 1))
    return {"peso": peso, "medidas": [_medida(*m, pred) for m in MEDIDAS[1:]]}


def _leer_resultado(relativa: str) -> pd.DataFrame:
    ruta = raiz() / relativa
    if not ruta.is_file():
        raise HTTPException(503, f"Faltan los resultados ({relativa}). Corre primero la evaluación.")
    return pd.read_csv(ruta)


def _error_peso() -> float:
    metricas = _leer_resultado(METRICAS_CNN).set_index("medida")
    return float(metricas.loc["peso_kg", "rmse"])


@app.get("/api/medir/ejemplos")
def medir_ejemplos():
    error = _error_peso()
    df = _leer_resultado(PREDICCIONES_CNN)
    todas = [{"id": int(f.id_animal_img), "real_kg": float(f.peso_kg_real),
              "estimado_kg": float(f.peso_kg_pred),
              "dentro": bool(abs(f.peso_kg_pred - f.peso_kg_real) <= error)}
             for f in df.itertuples()]
    ejemplos = [dict(v, foto_lateral=f"/api/medir/foto/{v['id']}/lat")
                for v in todas if v["id"] in (1, 2, 3)]
    return {"ejemplos": ejemplos, "todas": todas, "error_kg": round(error, 1)}


@app.get("/api/medir/foto/{id_animal}/{vista}")
def medir_foto(id_animal: int, vista: str):
    ruta = raiz() / "data" / "sample" / "imagenes" / f"{id_animal}_{vista}.jpg"
    if id_animal not in (1, 2, 3) or vista not in ("lat", "pos") or not ruta.is_file():
        raise HTTPException(404, "No existe esa foto")
    return FileResponse(ruta, media_type="image/jpeg")


# ---- para el ganadero: ¿por qué confiar? ----

def de_cada_10(r: float) -> int:
    """De cada 10 pares de animales, cuántos ordena bien (r -> prob. de concordancia)."""
    return round(10 * (0.5 + math.asin(r) / math.pi))


def _nivel(r: float) -> str:
    return "Baja" if r < 0.3 else "Media" if r < 0.6 else "Alta"


@app.get("/api/confianza")
def confianza():
    e6 = _leer_resultado(RESUMEN_E6)
    metricas = _leer_resultado(METRICAS_CNN).set_index("medida")
    e6 = e6[e6["ruido"] == "base"]
    ridge = e6[(e6["modelo"] == "ridge") & (e6["escenario"] == "holstein")].set_index("rasgo")["r_media"]
    aciertos = [{"rasgo": nombre, "de_cada_10": de_cada_10(ridge[rasgo])}
                for rasgo, nombre in RASGOS_CONFIANZA]
    # en holstein, promedio de los 3 rasgos
    r_tamano = e6[e6["modelo"] == "gblup"].groupby("escenario")["r_media"].mean()
    r_max = max(r_tamano[esc] for esc, _ in TAMANOS)
    tamanos = [{"nombre": nombre, "nivel": _nivel(r_tamano[esc]),
                "ancho": round(100 * r_tamano[esc] / r_max)} for esc, nombre in TAMANOS]
    return {"animales_referencia": N_HOLSTEIN, "aciertos": aciertos, "tamanos": tamanos,
            "error_peso_kg": round(float(metricas.loc["peso_kg", "rmse"])),
            "error_altura_cm": round(float(metricas.loc["altura_cruz_cm", "rmse"]))}
