# BOVIGEN — reglas para asistentes de código

Proyecto grupal de Machine Learning (ESAN 2026-2): comparar modelos de ML contra
GBLUP para predecir mérito genético a partir de SNPs. Lee `README.md` para el
contrato de archivos.

## Contrato que no se rompe

- Un modelo = `src/models/<nombre>.py` con
  `entrenar_y_predecir(X_train, y_train, X_test, **params) -> np.ndarray`.
  Parte de `src/models/_plantilla.py`. El modelo no lee archivos ni folds.
- Evaluar siempre con el runner común, nunca con un split propio:
  `python -m src.evaluation.validacion_cruzada --modelo <nombre> --escenario <esc> --rasgo <rasgo>`
- Folds: `data/folds/<escenario>.csv` (1..5, por parentesco genómico). No se
  regeneran ni se editan a mano; si hace falta cambiarlos, es una decisión del grupo.
- Resultados: cada modelo escribe su `results/parciales/...csv`. No edites
  `results/resultados.csv` a mano: se arma con `--consolidar`.
- Escenarios: `holstein` (rasgos `mkg`, `fpro`, `scs`) y `sim_n125`,
  `sim_n500`, `sim_n2000` (rasgo `fenotipo`; r se mide contra `valor_gv`).
- Desarrolla y prueba en `sim_n500` (rápido); Holstein al final.
- Semillas: `params.get("semilla", 2026)` en todo lo que tenga azar.

## Git

- Nunca trabajar en `main`. Una rama y un PR por pieza.
- Nunca `git add .` ni `git add -A`: agregar archivo por archivo.
- Nunca subir datos: nada de `data/raw`, `data/processed`, `.parquet`, `.zip`,
  `.vcf`, modelos entrenados (`.pkl`, `.pt`). Sí se suben `data/folds/` y
  `results/parciales/`.
- Nunca `--force` ni reescribir historia.
- Antes del PR: `pytest tests/ -q` en verde y un test nuevo para lo que agregaste.
- Los PR se unen con merge commit, no squash.

## Estilo

- Python, nombres y mensajes en español, como el resto de `src/`.
- Funciones pequeñas, sin dependencias nuevas sin avisar en el PR
  (las permitidas están en `requirements.txt`).
