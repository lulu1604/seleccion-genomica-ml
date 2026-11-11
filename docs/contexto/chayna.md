# E6 — Comparación de modelos

## Metodología

Se compararon cinco modelos (GBLUP, Ridge, XGBoost, MLP y Random Forest) en seis escenarios, utilizando cinco folds de validación cruzada.

Se verificó que todos los modelos utilizaron las mismas cinco particiones (folds), permitiendo realizar una comparación bajo las mismas condiciones.

La evaluación considera el promedio y la desviación estándar de Pearson r y RMSE. También se calculó la diferencia de Pearson medio respecto a GBLUP, utilizado como referencia.

## Resultados principales

Según el Pearson medio:

- **Ridge:** mayor valor en Holstein fpro y mkg.
- **MLP:** mayor valor en Holstein scs y simulaciones n125 y n500.
- **GBLUP:** mayor valor en simulación n2000.

Los modelos seleccionados por escenario se encuentran en `results/mejor_modelo.csv`.

## Interpretación de Ridge y GBLUP

Ridge y GBLUP son métodos de predicción relacionados, aunque utilizan enfoques y penalizaciones diferentes.

En Holstein mkg, Ridge obtiene un Pearson de 0.693122 frente a 0.685773 de GBLUP, una diferencia de apenas 0.007349. Por ello, se considera un empate práctico.

En Holstein fpro, Ridge obtiene 0.777259 frente a 0.710348 de GBLUP, mostrando una diferencia mayor de 0.066911.

En Holstein scs, MLP obtiene 0.630995 y Ridge 0.629168. La diferencia de 0.001827 indica también un empate práctico entre ambos modelos.

En la simulación n2000, aunque Ridge presenta una correlación positiva, su RMSE es considerablemente mayor: 1.649 frente a 0.914 de GBLUP. Esto indica que Ridge presenta un mayor error en sus predicciones, por lo que una correlación positiva no implica necesariamente una buena precisión predictiva.

## Limitaciones

Las comparaciones son descriptivas. Las diferencias de Pearson medio no demuestran por sí solas superioridad estadística.

En GBLUP se utilizó una heredabilidad fija de 0.3, sin optimizarla por rasgo, lo que puede influir en sus resultados.