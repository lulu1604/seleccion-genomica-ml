# Selección Genómica de Precisión en Ganado Vacuno

Proyecto del curso **Machine Learning — ESAN 2026-2**.
Comparamos modelos de Machine Learning contra el método estándar **GBLUP** para predecir el mérito genético (GEBV) de un animal a partir de su perfil de SNPs, evaluando en qué escenarios (poblaciones pequeñas o ruidosas) mejora la precisión.

## Instalación

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / Mac / WSL
source .venv/bin/activate

pip install -r requirements.txt
```

## Datos

Los datos raw y procesados **NO se suben al repo** (el `.gitignore` los bloquea).
Las instrucciones de descarga y el contrato de Holstein están en
[`docs/fuente_datos.md`](docs/fuente_datos.md).

## Contrato de archivos

Todos los scripts leen y escriben en estos formatos:

| Archivo | Contenido |
|---|---|
| `data/processed/holstein/X.parquet` | Filas = animales. Primera columna `id_animal` (texto), luego `SNP1`..`SNP42551` codificados 0/1/2 |
| `data/processed/holstein/y.csv` | `id_animal` + fenotipos; mismo orden que `X.parquet` |
| `data/processed/holstein/animal_ids.csv`, `manifest.json` | Respaldo de integridad (orden de ids y checksums), no la llave principal |
| `data/folds/<escenario>.csv` | `id_animal, fold` (1..5) — **todos usan los mismos folds**. Se versionan en git. Los genera `python -m src.data.particiones` (folds por parentesco genómico G) |
| `results/parciales/<modelo>__<escenario>__<rasgo>__<ruido>.csv` | Resultado de un modelo; cada uno escribe el suyo |
| `results/resultados.csv` | `modelo, rasgo, escenario_n, ruido, fold, r_pearson, rmse, tiempo_s` — se arma juntando los parciales |

## Uso

```python
from src.data.load_holstein import cargar
X, y, ids = cargar(target="fpro")   # X sin id_animal; ids[i] es el animal de la fila X[i]
```

### Agregar un modelo

1. Copia `src/models/_plantilla.py` como `src/models/<nombre>.py` y escribe
   `entrenar_y_predecir(X_train, y_train, X_test, **params)`.
2. Pruébalo rápido en una simulación chica:

```bash
python -m src.evaluation.validacion_cruzada --modelo <nombre> --escenario sim_n500 --rasgo fenotipo
```

3. Córrelo en Holstein (`--escenario holstein --rasgo mkg|fpro|scs`) y en las demás simulaciones.
4. Junta todo: `python -m src.evaluation.validacion_cruzada --consolidar`

El runner usa siempre los folds de `data/folds/`, así el modelo nunca ve animales del test.
En las simulaciones se entrena con `fenotipo` y r se mide contra el valor genético verdadero (`valor_gv`).

Tests: `pytest tests/ -q`

## Estructura

```
data/raw/          F1 datos crudos (ignorado)
data/processed/    F2 X, y (ignorado)
data/folds/        F2 folds por parentesco (versionado)
notebooks/         exploración
src/data/          F1-F2 descarga y QC
src/models/        F3-F4 GBLUP y modelos ML
src/evaluation/    F5 métricas, CV, SHAP
results/           F5 resultados.csv y figuras
dashboard/         F6 app Streamlit
docs/              F0 glosario, F7 informe
```

## Roles

| Rol | Responsable | Carpeta |
|---|---|---|
| R1 Datos | | `src/data` |
| R2 Baseline GBLUP | | `src/models/gblup.py` |
| R3 ML clásico | | `src/models` |
| R4 Deep Learning | | `src/models` |
| R5 SHAP + Dashboard + Informe | | `src/evaluation`, `dashboard`, `docs` |

## Flujo de trabajo en Git

1. Nadie trabaja directo en `main`.
2. Cada uno crea su rama: `git checkout -b r2-gblup`
3. Sube sus cambios agregando **archivo por archivo** (nunca `git add .`, para no subir datos por error):
   `git add src/models/gblup.py tests/test_gblup.py` → `git commit -m "qué hice"` → `git push -u origin r2-gblup`
4. Abre un **Pull Request** en GitHub para que otro integrante lo revise antes de unir a `main`.
5. Antes de pedir revisión: `pytest tests/ -q` en verde. Se une con *merge commit* (no *squash*).
