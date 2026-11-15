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

## Dashboard

Dashboard para el ganadero: dice qué hacer con cada animal según su ADN y estima
el peso y las medidas de una vaca a partir de dos fotos. Backend FastAPI, frontend
Vue 3, todo con Docker.

### Requisitos

- Docker Desktop.
- Los 2 modelos en `models/` (no se suben a git). Se generan o se descargan del
  **Drive del grupo: carpeta DATA_PROYECTO+/MODELOS**.

| Archivo | Tamaño | Cómo se genera |
|---|---|---|
| `models/genomica/ridge_holstein.npz` | 0.7 MB | `python dashboard/backend/preparar_genomica.py` (necesita `data/processed/holstein` y `data/folds`) |
| `models/vision/ensamble.joblib` | 0.2 MB | `python -m src.vision.entrenar --final` (necesita las 72 fotos; guardado con scikit-learn 1.9.1) |

### Levantar

```bash
docker compose up --build
```

Luego abre <http://localhost:8080>. El primer build tarda unos 4 min (descarga
torch y los pesos de U²-Net y MobileNetV2). Al arrancar, el backend precarga los
modelos; la primera medición por foto tarda unos 10 s y las siguientes, 2-3 s.
Para apagarlo: `docker compose down`.

### Desarrollo (sin Docker)

```bash
# backend, desde la raíz del repo (con el entorno de "Instalación")
uvicorn dashboard.backend.app.main:app --host 127.0.0.1 --port 8000
# frontend, en otra terminal
cd dashboard/frontend
npm install
npm run dev
```

Abre <http://localhost:5173> (Vite manda `/api` al backend en `127.0.0.1:8000`).
El contrato de la API está en [`dashboard/CONTRATO_API.md`](dashboard/CONTRATO_API.md).

### Pantallas

- **Mis animales**: ranking del rodeo según la prioridad elegida (balanceado, grasa, leche o ubre sana) y qué hacer con cada animal; acepta un CSV de ADN propio.
- **Ficha**: un animal en detalle: qué tan bueno es en cada rasgo, qué tan seguro es el resultado, la recomendación y las zonas del ADN que más pesaron.
- **Medir por foto**: con una foto de costado y una desde atrás estima el peso, la altura, el perímetro del tórax y dos largos, con su margen de error.
- **¿Por qué confiar?**: de cada 10 pares de animales, en cuántos elige bien al mejor; cómo mejora con más animales de referencia, y sus límites.

### Advertencias

- La evaluación genética solo está probada en ganado **Holstein**.
- La medición por foto es **aproximada** (peso ±84 kg) y se entrenó con solo
  **72 vacas Horqin**: con otras razas o fotos tomadas de otra forma el error puede ser mayor.

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
dashboard/         F6 dashboard para el ganadero (FastAPI + Vue 3, Docker)
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
