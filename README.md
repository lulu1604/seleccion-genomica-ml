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
| `data/processed/holstein/X.parquet` | Filas = animales, columnas = SNPs codificados 0/1/2 |
| `data/processed/holstein/animal_ids.csv` | Llave explícita del orden de filas de `X.parquet` |
| `data/processed/holstein/y.csv` | `id_animal` + fenotipos; mismo orden que `animal_ids.csv` |
| `data/processed/folds.csv` | `id_animal, fold` (1..5) — **todos usan los mismos folds** |
| `results/resultados.csv` | `modelo, rasgo, escenario_n, ruido, fold, r_pearson, rmse, tiempo_s` |

## Estructura

```
data/raw/          F1 datos crudos (ignorado)
data/processed/    F2 X, y, folds (ignorado)
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
3. Sube sus cambios: `git add .` → `git commit -m "qué hice"` → `git push -u origin r2-gblup`
4. Abre un **Pull Request** en GitHub para que otro integrante lo revise antes de unir a `main`.
