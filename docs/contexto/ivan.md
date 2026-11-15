# Contexto modelos genómicos — Iván

Actualizado: 8 de noviembre de 2026. Este documento resume las implementaciones
y corridas de XGBoost, Ridge y Random Forest para la evaluación genómica. No
elige un ganador ni interpreta los resultados como evidencia causal.

## 1. Qué hice

- Implementé `src/models/xgb.py`, `src/models/ridge.py` y
  `src/models/random_forest.py`.
- Cada modelo cumple el contrato común
  `entrenar_y_predecir(X_train, y_train, X_test, **params)`: recibe matrices y
  rasgos ya separados por el runner, no lee archivos ni decide los folds, y
  devuelve una predicción por animal de test.
- Agregué pruebas de contrato para Ridge y Random Forest. XGBoost tiene su
  prueba correspondiente en `tests/test_xgb_model.py`.
- Ejecuté los tres modelos en los seis escenarios asignados: Holstein (`mkg`,
  `fpro`, `scs`) y las simulaciones (`sim_n125`, `sim_n500`, `sim_n2000`).

## 2. Datos y evaluación

- Holstein: 5 024 animales y 42 551 SNPs; los rasgos evaluados son los EBVs
  `mkg`, `fpro` y `scs`.
- Simulaciones AlphaSimR: 125, 500 y 2 000 animales, con 10 005 SNPs. El
  entrenamiento usa `fenotipo` y la evaluación se mide contra `valor_gv`,
  conocido por ser una simulación.
- Todas las corridas usan el runner común y los cinco folds versionados en
  `data/folds/`. Los folds externos no se usaron para ajustar hiperparámetros.
- La tabla informa el promedio y la desviación estándar muestral de Pearson
  entre folds, el RMSE promedio y el tiempo total de entrenamiento de los cinco
  folds. Los valores se calcularon desde los CSV parciales versionados.

## 3. Métodos y configuración

| Modelo | Configuración predeterminada |
|---|---|
| XGBoost | `n_estimators=500`, `learning_rate=0.05`, `max_depth=4`, `colsample_bytree=0.2`, `subsample=0.8`, `tree_method="hist"`, semilla 2026 |
| Ridge | `alpha=10.0`, solver `lsqr` |
| Random Forest | `n_estimators=200`, `max_features="sqrt"`, `min_samples_leaf=2`, semilla 2026 |

Los valores predeterminados son fijos en el código; las corridas de esta tabla
no incluyeron una búsqueda de hiperparámetros. XGBoost y Random Forest usan
todos los hilos disponibles por defecto, por lo que sus tiempos —y, para
XGBoost, sus resultados— pueden variar ligeramente entre máquinas.

## 4. Resultados

Cada fila corresponde a una combinación evaluada con cinco folds. `r` se
reporta como promedio ± desviación estándar entre folds.

| Modelo | Escenario / rasgo | r de Pearson medio ± DE | RMSE medio | Tiempo total (s) |
|---|---|---:|---:|---:|
| XGBoost | Holstein / mkg | 0.639 ± 0.042 | 0.782 | 2 196.423 |
| XGBoost | Holstein / fpro | 0.776 ± 0.020 | 0.634 | 2 157.702 |
| XGBoost | Holstein / scs | 0.527 ± 0.049 | 0.859 | 2 182.628 |
| XGBoost | sim_n125 / fenotipo | −0.073 ± 0.200 | 1.106 | 14.616 |
| XGBoost | sim_n500 / fenotipo | 0.106 ± 0.065 | 1.053 | 31.792 |
| XGBoost | sim_n2000 / fenotipo | 0.278 ± 0.063 | 0.982 | 99.598 |
| Ridge | Holstein / mkg | 0.693 ± 0.022 | 0.748 | 92.330 |
| Ridge | Holstein / fpro | 0.777 ± 0.012 | 0.642 | 86.329 |
| Ridge | Holstein / scs | 0.629 ± 0.047 | 0.823 | 81.457 |
| Ridge | sim_n125 / fenotipo | 0.136 ± 0.145 | 1.056 | 0.144 |
| Ridge | sim_n500 / fenotipo | 0.204 ± 0.107 | 1.196 | 0.573 |
| Ridge | sim_n2000 / fenotipo | 0.298 ± 0.044 | 1.649 | 2.501 |
| Random Forest | Holstein / mkg | 0.506 ± 0.054 | 0.927 | 60.979 |
| Random Forest | Holstein / fpro | 0.644 ± 0.039 | 0.851 | 62.286 |
| Random Forest | Holstein / scs | 0.356 ± 0.031 | 0.962 | 62.917 |
| Random Forest | sim_n125 / fenotipo | 0.077 ± 0.182 | 0.998 | 2.298 |
| Random Forest | sim_n500 / fenotipo | 0.092 ± 0.084 | 0.998 | 2.894 |
| Random Forest | sim_n2000 / fenotipo | 0.152 ± 0.090 | 0.988 | 8.978 |

Los resultados son descriptivos para estos folds y configuraciones. La
selección del mejor modelo debe considerar la comparación E6 completa y no
solo el mayor promedio de `r`.

## 5. Limitaciones

- Los hiperparámetros no se optimizaron mediante una búsqueda común; los
  resultados comparan las configuraciones predeterminadas documentadas arriba.
- En las simulaciones se evalúa contra el valor genético verdadero; en
  Holstein, contra EBVs. Son referencias distintas y no deben interpretarse
  como una comparación directa entre poblaciones.
- La desviación entre folds puede ser considerable en las simulaciones
  pequeñas, en especial `sim_n125`.
- El uso de varios hilos puede causar variaciones entre equipos. Los tiempos
  de entrenamiento tampoco son necesariamente comparables entre máquinas.
- Los promedios de `r` por fold no sustituyen una prueba de significancia ni
  demuestran superioridad estadística.

## 6. Archivos

| Ruta | Uso |
|---|---|
| `src/models/xgb.py` | Regresor XGBoost. |
| `src/models/ridge.py` | Regresión Ridge. |
| `src/models/random_forest.py` | Regresor Random Forest. |
| `tests/test_xgb_model.py` | Prueba del contrato de XGBoost. |
| `tests/test_ridge_model.py` | Prueba del contrato de Ridge. |
| `tests/test_random_forest_model.py` | Prueba del contrato de Random Forest. |
| `results/parciales/xgb__*__base.csv` | Resultados por fold de XGBoost. |
| `results/parciales/ridge__*__base.csv` | Resultados por fold de Ridge. |
| `results/parciales/random_forest__*__base.csv` | Resultados por fold de Random Forest. |

Los parciales tienen las columnas del contrato común y cinco filas, una por
fold. No editar `results/resultados.csv` a mano; se genera con el runner.

## 7. Reproducir

Con los datos procesados y folds oficiales ya disponibles localmente:

```powershell
python -m src.evaluation.validacion_cruzada --modelo xgb --escenario holstein --rasgo mkg
python -m src.evaluation.validacion_cruzada --modelo xgb --escenario holstein --rasgo fpro
python -m src.evaluation.validacion_cruzada --modelo xgb --escenario holstein --rasgo scs
python -m src.evaluation.validacion_cruzada --modelo xgb --escenario sim_n125 --rasgo fenotipo
python -m src.evaluation.validacion_cruzada --modelo xgb --escenario sim_n500 --rasgo fenotipo
python -m src.evaluation.validacion_cruzada --modelo xgb --escenario sim_n2000 --rasgo fenotipo
```

Para repetir las seis corridas de Ridge o Random Forest, sustituir `xgb` por
`ridge` o `random_forest`. El runner conserva los mismos folds y nombres de
archivos parciales. Para validar las pruebas de los tres modelos:

```powershell
pytest tests/test_xgb_model.py tests/test_ridge_model.py tests/test_random_forest_model.py -q
```

## 8. Para la PPT

1. Los tres modelos se evaluaron con el mismo protocolo de cinco folds y los
   mismos escenarios que el baseline.
2. Ridge fue competitivo en Holstein con tiempos menores que XGBoost; en
   simulación, sus resultados dependen del tamaño de población.
3. Las diferencias de desempeño deben presentarse junto con la variabilidad
   entre folds, las configuraciones usadas y las limitaciones de comparación.
