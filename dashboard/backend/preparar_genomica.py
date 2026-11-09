"""Arma el paquete genómico del dashboard y el archivo de ejemplo (correr UNA vez).

    python dashboard/backend/preparar_genomica.py

Necesita data/processed/holstein/ (X.parquet, y.csv) y data/folds/holstein.csv.
- Entrena Ridge (alpha=10, lsqr: la misma configuración evaluada en la E6)
  con los folds 2-5 y lo prueba en el fold 1.
- Referencia para los percentiles: las predicciones de los 1005 animales del
  fold 1 (no se usaron para entrenar).
- Guarda models/genomica/ridge_holstein.npz (no se sube; models/ está en .gitignore)
  y data/sample/genotipos_ejemplo.csv (12 animales del fold 1).
"""
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.linear_model import Ridge

RAIZ = Path(__file__).resolve().parents[2]
RASGOS = ["fpro", "mkg", "scs"]
ALPHA = 10.0
N_EJEMPLO = 12


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app.genomica import evaluar  # noqa: E402

    proc = RAIZ / "data" / "processed" / "holstein"
    X = pd.read_parquet(proc / "X.parquet")
    y = pd.read_csv(proc / "y.csv")
    folds = pd.read_csv(RAIZ / "data" / "folds" / "holstein.csv")
    ids = X.pop("id_animal").astype(str)
    if not (ids.values == y["id_animal"].astype(str).values).all():
        raise SystemExit("X e y no tienen los animales en el mismo orden")
    fold = ids.map(dict(zip(folds["id_animal"].astype(str), folds["fold"]))).to_numpy()
    tr, te = fold != 1, fold == 1
    snps = X.columns.to_numpy().astype(str)
    Xa = X.to_numpy(dtype=np.float32)
    media_snp = Xa[tr].mean(axis=0)

    paq = {"snps": snps, "media_snp": media_snp.astype(np.float32),
           "alpha": np.array(ALPHA), "n_entrenamiento": np.array(int(tr.sum())),
           "n_referencia": np.array(int(te.sum())),
           "creado": np.array(datetime.now().isoformat(timespec="seconds"))}
    for r in RASGOS:
        m = Ridge(alpha=ALPHA, solver="lsqr").fit(Xa[tr], y[r].to_numpy()[tr])
        coef = m.coef_.astype(np.float32)
        media_pred = float(m.intercept_ + media_snp.astype(np.float64) @ m.coef_)
        pred_te = (Xa[te] - media_snp) @ coef + media_pred
        r_te = pearsonr(pred_te, y[r].to_numpy()[te])[0]
        print(f"{r}: r en fold 1 = {r_te:.4f}")
        paq.update({f"coef_{r}": coef, f"media_pred_{r}": np.array(media_pred),
                    f"ref_{r}": pred_te.astype(np.float64), f"r_fold1_{r}": np.array(r_te)})

    salida = RAIZ / "models" / "genomica" / "ridge_holstein.npz"
    salida.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(salida, **paq)
    print(f"Guardado: {salida.relative_to(RAIZ)} ({salida.stat().st_size / 1e6:.1f} MB)")

    # ejemplo: 12 animales del fold 1 repartidos de mejor a peor (puntaje balanceado)
    ref = pd.DataFrame(Xa[te].astype(np.int8), columns=snps)
    ref.insert(0, "id_animal", ids[te].to_numpy())
    puntaje = np.array([a["por_prioridad"]["balanceado"]["puntaje"] for a in evaluar(ref, paq)])
    objetivos = np.linspace(97, 4, N_EJEMPLO)
    elegidos = []
    for o in objetivos:
        orden = np.argsort(np.abs(puntaje - o))
        elegidos.append(next(k for k in orden if k not in elegidos))
    ejemplo = ref.iloc[elegidos].copy()
    ejemplo.insert(1, "tipo", "Toro")
    destino = RAIZ / "data" / "sample" / "genotipos_ejemplo.csv"
    ejemplo.to_csv(destino, index=False)
    print(f"Ejemplo: {destino.relative_to(RAIZ)} ({len(ejemplo)} animales, "
          f"{destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
