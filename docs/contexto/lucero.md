# Contexto MLP — Lucero

Actualizado: 29 de octubre de 2026. Este artefacto acompaña las corridas del
MLP para la E6; no selecciona un mejor modelo ni interpreta causalmente los
resultados.

## Qué implementa

`src/models/mlp.py` implementa una regresión con una red `42551 -> 4 -> 2 -> 1`
para el contrato común `entrenar_y_predecir(X_train, y_train, X_test, **params)`.
No abre archivos ni conoce los folds. En cada fold:

1. calcula la media y desviación de cada SNP **solo con train**;
2. escala el rasgo de train, ajusta la red y predice test;
3. revierte la escala del rasgo antes de devolver las predicciones.

Esto conserva el aislamiento train/test establecido por
`src.evaluation.validacion_cruzada` y los folds versionados en `data/folds/`.

## Configuración reproducible

Las tres corridas Holstein usan exactamente: `semilla=2026`, `epochs=5`,
`batch_size=4096`, `max_batch_mb=1024`, `hidden_dim=4`,
`learning_rate=0.005` y `weight_decay=0.0001`. Se ejecutaron con cinco folds
para cada rasgo. El límite explícito de 1024 MiB conserva el lote grande usado
en estas corridas; por defecto el modelo limita su matriz de entrada a 256 MiB
para funcionar en equipos con menos memoria.

| Escenario | Rasgo | Folds | r de Pearson medio | RMSE medio |
|---|---:|---:|---:|---:|
| Holstein (n=5024) | mkg | 5 | 0.271324 | 1.271117 |
| Holstein (n=5024) | fpro | 5 | 0.235846 | 1.342416 |
| Holstein (n=5024) | scs | 5 | 0.176431 | 1.267895 |
| sim_n125 | fenotipo | 5 | 0.129761 | 1.161838 |
| sim_n500 | fenotipo | 5 | 0.118423 | 1.180697 |
| sim_n2000 | fenotipo | 5 | 0.135385 | 1.130397 |

Los cinco resultados por escenario están en `results/parciales/` y la tabla de
30 filas consolidada está en `results/resultados.csv`.

## Estado para la E6

Se completaron las 6 de 6 corridas asignadas al MLP: tres rasgos Holstein y
tres poblaciones AlphaSimR. Los CSV de simulación se validaron con el loader
oficial antes de ejecutar los folds: IDs alineados, SNPs en `{0, 1, 2}`, 10 005
marcadores y cinco folds balanceados. Los datos procesados permanecen fuera de
Git en `data/processed/`.

Para reproducir las tres corridas de simulación, con los directorios oficiales
ya disponibles en `data/processed/`, se usan:

```powershell
python -m src.evaluation.validacion_cruzada --modelo mlp --escenario sim_n125 --rasgo fenotipo --param semilla=2026 --param epochs=5 --param batch_size=4096 --param max_batch_mb=1024 --param hidden_dim=4 --param learning_rate=0.005 --param weight_decay=0.0001
python -m src.evaluation.validacion_cruzada --modelo mlp --escenario sim_n500 --rasgo fenotipo --param semilla=2026 --param epochs=5 --param batch_size=4096 --param max_batch_mb=1024 --param hidden_dim=4 --param learning_rate=0.005 --param weight_decay=0.0001
python -m src.evaluation.validacion_cruzada --modelo mlp --escenario sim_n2000 --rasgo fenotipo --param semilla=2026 --param epochs=5 --param batch_size=4096 --param max_batch_mb=1024 --param hidden_dim=4 --param learning_rate=0.005 --param weight_decay=0.0001
```

Luego se consolida con `python -m src.evaluation.validacion_cruzada --consolidar`.

## Actualización residual (29 de octubre de 2026)

La versión definitiva usa una rama lineal aditiva más una residual `4 -> 2 -> 1`,
validación interna 85/15 por fold, dropout seleccionado entre 0.0/0.1/0.2,
early stopping y refit desde cero. Configuración: semilla 2026, máximo 100
épocas, patience 15, lr 1e-3, weight decay 1e-3 y batch 4096.

| Escenario | r v1 -> residual | RMSE v1 -> residual |
|---|---:|---:|
| mkg | 0.271 -> 0.680 | 1.271 -> 0.751 |
| fpro | 0.236 -> 0.699 | 1.342 -> 0.729 |
| scs | 0.176 -> 0.631 | 1.268 -> 0.807 |
| sim_n125 | 0.130 -> 0.221 | 1.162 -> 0.992 |
| sim_n500 | 0.118 -> 0.215 | 1.181 -> 1.040 |
| sim_n2000 | 0.135 -> 0.373 | 1.130 -> 0.927 |

La residual mejora r y RMSE en los seis escenarios. Los seis baseline están
en `results/parciales/historico/`; los seis CSV superiores son los definitivos
para E6 y sus selecciones por fold están en `results/experiments/`.

Limitaciones: el tiempo reportado incluye selección interna y es mucho mayor
en Holstein; los resultados no establecen causalidad ni sustituyen la
comparación final con GBLUP/Ridge. No se seleccionó ninguna configuración con
los folds de test externos. `results/resultados.csv` se excluye de esta entrega:
Chayna debe consumir exclusivamente los seis parciales definitivos.
