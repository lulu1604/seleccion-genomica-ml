"""Crea los CSV de prueba del dashboard en data/sample/.

Son datos INVENTADOS, solo para construir el dashboard antes de tener
resultados reales. Tienen las mismas columnas que los archivos reales.

    python dashboard/backend/crear_demo.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "data" / "sample"

# r de referencia por modelo y escenario (inventados, parecidos a lo esperado)
BASE = {
    ("fpro", 5024): {"gblup": 0.71, "ridge": 0.70, "xgb": 0.62, "mlp": 0.66},
    ("fenotipo", 500): {"gblup": 0.20, "ridge": 0.20, "xgb": 0.15, "mlp": 0.17},
}


def resultados(rng):
    filas = []
    for (rasgo, n), modelos in BASE.items():
        for modelo, r in modelos.items():
            for fold in range(1, 6):
                filas.append({
                    "modelo": modelo, "rasgo": rasgo, "escenario_n": n,
                    "ruido": "base", "fold": fold,
                    "r_pearson": round(r + rng.normal(0, 0.03), 4),
                    "rmse": round(0.75 + (0.72 - r) * 0.5 + rng.normal(0, 0.02), 4),
                    "tiempo_s": round(float(rng.uniform(1, 60)), 2),
                })
    return pd.DataFrame(filas)


def shap():
    filas = [{"snp": "SNP_demo_1", "rsid": "rs109421300", "gen": "DGAT1",
              "importancia": 0.050, "n_papers": 367}]
    for i in range(2, 21):
        filas.append({"snp": f"SNP_demo_{i}", "rsid": "", "gen": "",
                      "importancia": round(0.05 / i, 4), "n_papers": 0})
    return pd.DataFrame(filas)


def vision():
    return pd.DataFrame({
        "medida": ["largo_oblicuo_cm", "altura_cruz_cm", "perimetro_toracico_cm",
                   "largo_cadera_cm", "peso_kg"],
        "rmse": [8.1, 4.2, 9.5, 3.9, 38.0],
        "mae": [6.3, 3.3, 7.4, 3.0, 29.5],
        "r_pearson": [0.78, 0.81, 0.83, 0.70, 0.86],
    })


if __name__ == "__main__":
    rng = np.random.default_rng(2026)
    SALIDA.mkdir(parents=True, exist_ok=True)
    resultados(rng).to_csv(SALIDA / "resultados_demo.csv", index=False)
    shap().to_csv(SALIDA / "shap_demo.csv", index=False)
    vision().to_csv(SALIDA / "vision_demo.csv", index=False)
    print("Listo: resultados_demo.csv, shap_demo.csv y vision_demo.csv en data/sample/")
