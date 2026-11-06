# E6 — Comparación de modelos

## Metodología
Se compararon cinco modelos (GBLUP, Ridge, XGBoost, MLP y Random Forest) en seis escenarios, utilizando cinco folds de validación cruzada.

La evaluación considera el promedio y la desviación estándar de Pearson r y RMSE. También se calculó la diferencia de Pearson medio respecto a GBLUP, utilizado como referencia.

## Resultados principales
Según el Pearson medio:

- **Ridge:** mayor valor en Holstein fpro y mkg.
- **MLP:** mayor valor en Holstein scs y simulaciones n125 y n500.
- **GBLUP:** mayor valor en simulación n2000.

Los modelos seleccionados por escenario se encuentran en `results/mejor_modelo.csv`.

## Interpretación de Ridge y GBLUP
Ridge y GBLUP están estrechamente relacionados: ambos utilizan regularización en modelos lineales, aunque pueden trabajar con representaciones y penalizaciones diferentes.

Por tanto, la ventaja observada de Ridge no debe atribuirse simplemente a que sea un modelo de Machine Learning, sino que puede depender de la regularización y configuración utilizadas.

## Limitaciones
Las comparaciones son descriptivas. Las diferencias de Pearson medio no demuestran por sí solas superioridad estadística. También debe verificarse que todos los modelos se hayan evaluado con las mismas particiones.

En GBLUP se utilizó una heredabilidad fija de 0.3, sin optimizarla por rasgo, lo que puede influir en sus resultados.