# E6 — Implementación de GBLUP y comparación de modelos

## 1. Qué hice

Implementé el modelo **GBLUP (Genomic Best Linear Unbiased Prediction)** para predecir valores genéticos a partir de información genómica representada mediante SNPs.

La implementación utiliza la matriz de parentesco genómico de VanRaden (método 1). También desarrollé pruebas unitarias para verificar las predicciones, la fórmula matricial, la prevención de fuga de información y la compatibilidad con el evaluador común del proyecto.

Como parte de E6, participé en la comparación de cinco modelos: GBLUP, Ridge, XGBoost, MLP y Random Forest, utilizando seis escenarios de evaluación.

## 2. Datos y evaluación

Se trabajó con seis escenarios:

- **Holstein:** rasgos fpro, mkg y scs.
- **Simulaciones:** sim_n125, sim_n500 y sim_n2000.

En Holstein, el modelo se entrena y evalúa utilizando el mismo rasgo.

En las simulaciones, se entrena utilizando el fenotipo y se evalúa comparando las predicciones con el valor genético verdadero (`valor_gv`).

La evaluación utiliza cinco folds de validación cruzada. En cada iteración, cuatro folds se utilizan para entrenar y el restante para probar.

Se verificó que los cinco modelos utilizaran las mismas particiones para cada escenario, permitiendo compararlos bajo las mismas condiciones.

Las métricas utilizadas fueron:

- **Pearson (r):** mide la correlación lineal entre los valores reales y las predicciones. Un valor cercano a 1 indica una correlación positiva fuerte.
- **RMSE:** mide el error de las predicciones. Cuanto menor sea, mejor.
- **Tiempo de ejecución:** registra cuánto demora el entrenamiento y la predicción en cada fold.

Los resultados se resumen mediante el promedio y la desviación estándar de las métricas entre los cinco folds.

## 3. Método y decisiones

### Implementación de GBLUP

El modelo recibe las matrices de genotipos de entrenamiento y prueba, junto con los valores del rasgo de entrenamiento.

Los genotipos SNP están codificados como 0, 1 o 2.

La implementación realiza los siguientes pasos:

1. Calcula las frecuencias alélicas utilizando exclusivamente los animales de entrenamiento.
2. Centra los genotipos utilizando las frecuencias calculadas.
3. Construye la matriz de parentesco genómico de entrenamiento y la matriz de parentesco entre prueba y entrenamiento.
4. Incorpora una penalización basada en la heredabilidad asumida.
5. Resuelve el sistema matricial para obtener los coeficientes del modelo.
6. Genera las predicciones para los animales de prueba.

Se utiliza una heredabilidad asumida de `h2=0.3` por defecto. Este valor se mantiene fijo para todos los rasgos y no se selecciona observando los resultados del conjunto de prueba.

La implementación también valida las dimensiones de las matrices, los valores finitos, la heredabilidad y la existencia de SNPs variables.

### Comparación E6

Se compararon cinco modelos:

- GBLUP.
- Ridge.
- XGBoost.
- MLP.
- Random Forest.

La comparación comprende seis escenarios y cinco modelos, dando un total de 30 combinaciones evaluadas y 150 registros correspondientes a los cinco folds de cada combinación.

Se utilizó GBLUP como modelo de referencia para calcular la diferencia de Pearson medio de los demás modelos.

## 4. Resultados

Los modelos seleccionados según el mayor Pearson medio fueron:

| Escenario | Modelo seleccionado | Pearson medio | RMSE medio |
|---|---|---:|---:|
| Holstein fpro | Ridge | 0.777259 | 0.641775 |
| Holstein mkg | Ridge | 0.693122 | 0.748395 |
| Holstein scs | MLP | 0.630995 | 0.806648 |
| sim_n125 | MLP | 0.220673 | 0.991991 |
| sim_n500 | MLP | 0.214573 | 1.039926 |
| sim_n2000 | GBLUP | 0.407625 | 0.913510 |

### Interpretación

**Holstein fpro:** Ridge obtuvo el mayor Pearson medio, con 0.777259, superando a GBLUP (0.710348).

**Holstein mkg:** Ridge obtuvo 0.693122 y GBLUP 0.685773. La diferencia de 0.007349 es pequeña, por lo que se considera un empate práctico.

**Holstein scs:** MLP obtuvo 0.630995 y Ridge 0.629168. La diferencia de 0.001827 también representa un empate práctico.

**Simulaciones n125 y n500:** MLP obtuvo los mayores valores de Pearson medio, con 0.220673 y 0.214573, respectivamente.

**Simulación n2000:** GBLUP obtuvo el mayor Pearson medio, con 0.407625.

Un resultado importante se observa al comparar Ridge y GBLUP en sim_n2000. Aunque Ridge presenta una correlación positiva, su RMSE es considerablemente mayor: aproximadamente 1.649 frente a 0.914 de GBLUP. Esto demuestra que una correlación positiva no necesariamente implica un menor error de predicción.

En general, los resultados muestran que el modelo seleccionado depende del escenario y del rasgo evaluado. No existe un único modelo que obtenga el mayor Pearson medio en todos los casos.

## 5. Limitaciones

- La heredabilidad de GBLUP se fijó en 0.3 y no se optimizó individualmente para cada rasgo.
- Las diferencias entre los promedios de Pearson son descriptivas y no demuestran por sí solas superioridad estadística.
- En las simulaciones, los valores de correlación obtenidos son relativamente bajos, especialmente en n125 y n500.
- Pearson y RMSE miden aspectos diferentes del rendimiento. Por ello, ambas métricas deben considerarse al interpretar los resultados.
- En los datos reales no se dispone del valor genético verdadero para realizar la misma evaluación que en las simulaciones.

## 6. Archivos relacionados

**Implementación y evaluación:**

- `src/models/gblup.py`: implementación del modelo GBLUP.
- `src/evaluation/validacion_cruzada.py`: evaluador común de los modelos.
- `src/evaluation/metricas.py`: funciones para calcular Pearson y RMSE.
- `src/evaluation/comparacion.py`: generación del resumen comparativo y gráficos.

**Pruebas:**

- `tests/test_gblup.py`: cinco pruebas específicas para GBLUP.
- `tests/test_comparacion.py`: pruebas de la comparación de modelos.

**Resultados:**

- `results/parciales/`: resultados individuales de cada modelo y escenario.
- `results/resultados.csv`: consolidación de los resultados parciales, con 150 filas.
- `results/resumen_e6.csv`: resumen de las métricas de los modelos.
- `results/mejor_modelo.csv`: modelo seleccionado para cada escenario.
- `results/figures/`: gráficos generados para la comparación.

Las pruebas completas del proyecto finalizaron con **120 pruebas aprobadas**.

## 7. Reproducir

Para ejecutar la evaluación de un modelo con el evaluador común:

```bash
python -m src.evaluation.validacion_cruzada --modelo gblup --escenario holstein --rasgo fpro
```

Para consolidar los resultados parciales:

```bash
python -m src.evaluation.validacion_cruzada --consolidar
```

Para generar el resumen comparativo y los gráficos de E6:

```bash
python -m src.evaluation.comparacion
```

Para ejecutar las pruebas del proyecto:

```bash
python -m pytest -q
```

La comparación final se generó utilizando los 30 archivos parciales disponibles, correspondientes a los cinco modelos y los seis escenarios.