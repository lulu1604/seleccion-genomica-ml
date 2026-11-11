# Entrega MLP residual para E6 — Lucero

Este documento da contexto para integrar los resultados de la MLP en la E6.
La versión recomendada es la MLP residual de `src/models/mlp.py`; no hace falta
reentrenarla para usar los resultados ya versionados.

## Qué se entregó

- Modelo residual aditivo: salida lineal de los SNPs + corrección no lineal
  `4 -> 2 -> 1` con ReLU.
- Selección interna de `dropout` entre `0.0`, `0.1` y `0.2` por cada fold.
- Validación interna 85/15 dentro del train externo, early stopping y refit
  desde cero usando todo el train externo.
- Seis resultados definitivos de cinco folds cada uno y sus tablas de
  selección por fold.
- Seis resultados baseline preservados en `results/parciales/historico/`.

## Protocolo que evita leakage

Para cada fold externo, el test queda aislado. El modelo divide únicamente el
train externo en fit (85 %) y validación (15 %), estima medias/desvíos solo en
fit, elige dropout y época por MSE de validación, y luego reinicializa el
modelo para entrenar sobre todo el train externo. Las métricas de test se usan
solo para el reporte final.

Configuración usada: semilla 2026, hasta 100 épocas, `patience=15`,
`learning_rate=1e-3`, `weight_decay=1e-3`, `batch_size=4096` y límite de
1024 MiB para la matriz de entrada del lote. Ese límite no equivale al uso
total de RAM del proceso.

## Resultados que debe usar Chayna

Los seis CSV definitivos están en `results/parciales/`. Todos cumplen el
contrato E6: columnas `modelo, rasgo, escenario_n, ruido, fold, r_pearson,
rmse, tiempo_s`, con folds del 1 al 5.

| Escenario | r de Pearson medio ± DE | RMSE medio | Tiempo total |
|---|---:|---:|---:|
| Holstein mkg | 0.680 ± 0.029 | 0.751 | 821.083 s |
| Holstein fpro | 0.699 ± 0.019 | 0.729 | 755.090 s |
| Holstein scs | 0.631 ± 0.040 | 0.807 | 727.482 s |
| sim_n125 | 0.221 ± 0.082 | 0.992 | 1.705 s |
| sim_n500 | 0.215 ± 0.123 | 1.040 | 5.289 s |
| sim_n2000 | 0.373 ± 0.065 | 0.927 | 14.125 s |

Frente a la MLP v1, la residual mejora tanto `r` como RMSE en los seis
escenarios. La contrapartida es el tiempo de Holstein, pues incluye selección
interna de hiperparámetros por fold.

## Archivos clave

| Ruta | Uso |
|---|---|
| `src/models/mlp.py` | Arquitectura, entrenamiento, early stopping y predicción. |
| `src/evaluation/seleccion_mlp.py` | Runner reproducible y registro de selección interna. |
| `results/parciales/mlp__*.csv` | Entradas definitivas para E6. |
| `results/experiments/mlp_residual__*__seleccion.csv` | Dropout, época y configuración elegida por fold. |
| `results/parciales/historico/mlp_v1__*.csv` | Baseline histórico; no usar como resultado final. |
| `tests/test_mlp.py`, `tests/test_seleccion_mlp.py` | Contratos de reproducibilidad, aislamiento y selección. |

`results/resultados.csv` se excluyó intencionalmente del repositorio. Para la
E6 deben consumirse los parciales anteriores, no un consolidado compartido.

## Reproducir si fuera necesario

Con los datasets procesados y folds oficiales disponibles localmente:

```powershell
python -m src.evaluation.seleccion_mlp --all
python -m pytest -v -p no:cacheprovider
```

La primera orden reentrena los seis escenarios, por lo que no debe ejecutarse
si solo se necesitan los resultados entregados.

## Limitaciones

- Las mejoras describen estos folds oficiales; no establecen causalidad ni
  sustituyen la comparación global de modelos de la E6.
- Los tiempos de Holstein incluyen la selección interna y no son comparables
  directamente con una corrida de MLP sin validación interna.
- La decisión final del mejor modelo corresponde a la E6, que comparará MLP
  con GBLUP, Ridge y los demás modelos bajo el mismo contrato.
