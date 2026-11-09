# Contexto visión (medidas corporales desde foto) — Joe

Actualizado: 7 de noviembre de 2026. Módulo independiente del genómico: no usa
SNPs, ni `src/models/`, ni los folds de `data/folds/`.

## 1. Qué hice

Un modelo que estima 5 medidas corporales de una vaca (largo oblicuo, altura a
la cruz, perímetro torácico, largo de cadera y peso) a partir de su foto
lateral y su foto posterior. La versión final promedia dos regresiones Ridge:
una sobre features congeladas de una CNN (MobileNetV2) y otra sobre la
geometría de la silueta de la vaca, segmentada con U²-Net.

## 2. Datos y evaluación

- Fuente: *Cattle side view and back view dataset* (Bai, 2024), Mendeley Data,
  DOI [10.17632/h2s22wr5py.2](https://doi.org/10.17632/h2s22wr5py.2). 72 bovinos
  Horqin (Mongolia Interior, China), con 1 foto lateral y 1 posterior cada uno
  y sus medidas reales. Detalle en `docs/fuente_imagenes.md`.
- Ningún animal fotografiado tiene genotipo y ningún toro Holstein tiene foto:
  las poblaciones no se cruzan.
- Validación cruzada de 5 folds **por animal** (`asignar_folds`, semilla 2026):
  las dos fotos de un animal caen siempre en el mismo fold. Quedan folds de 15,
  15, 14, 14 y 14 animales.
- Métricas por medida, en cm y kg: RMSE, MAE y r de Pearson, promediadas
  sobre los 5 folds. Referencia: `rmse_base`, el error de predecir siempre la
  media del train. Un modelo que no baja de ahí no aporta información de la foto.

## 3. Método y decisiones

1. **Fotos posteriores enderezadas.** 70 de las 72 fotos posteriores vienen
   guardadas en horizontal (4032×3024), con la vaca girada 90° y sin etiqueta
   EXIF de orientación. Las dos correctas (50 y 64) son las únicas verticales.
   `src/data/imagenes.py` aplica la regla "posterior horizontal → girar 90°
   horario" antes de redimensionar a 224×224.
2. **CNN como extractor, no entrenada.** MobileNetV2 preentrenada en ImageNet
   [1], congelada. Por foto se promedia su mapa final (1280 valores) y el de la
   foto en espejo, porque la vaca puede mirar a cualquier lado. Lateral +
   posterior = 2560 features por animal.
3. **Silueta.** U²-Net [2], vía la librería `rembg`, separa la vaca del fondo.
   Se conserva la mancha más grande, lo que descarta personas sueltas, y se
   miden 23 valores por vista: área, alto, ancho, perfiles de alto y ancho a
   varias alturas. En total, 46 features. Las máscaras se guardan en
   `data/processed/mascaras/`, que no se versiona.
4. **Dos Ridge promediados.** Cada bloque se estandariza y se ajusta con
   `RidgeCV` (30 valores de alpha entre 0.1 y 10⁶, uno por medida, elegido por
   leave-one-out **solo dentro del train**). La predicción final es el promedio
   de los dos modelos.

¿Por qué no entrenar la red? Con 57 animales de train, la CNN base
(ResNet18 [3] congelada más una capa lineal entrenada 30 épocas) casi memoriza
el train: la pérdida baja de ~1.4 a entre 0.11 y 0.21 según el fold, y aun
así en test queda peor que la media. La
penalización de Ridge es la misma idea que usa GBLUP con los SNPs.

Variantes probadas y descartadas, siempre contra la media: Ridge o PLS sobre
ResNet18 (capas 3 y 4), grillas espaciales 2×2 a 4×4, CNN sobre la vaca
recortada y selección de modelo por medida con validación interna. Esta última
resultó ruidosa con tan pocos animales. Para no quedarnos con un método que
ganara por suerte en un solo reparto, el promedio de los dos Ridge se eligió
por su desempeño en 11 particiones distintas, no solo en los folds oficiales.
Un test (`test_ensamble_no_mira_las_medidas_del_test`) comprueba que cambiar
las medidas del test no cambia sus predicciones.

## 4. Resultados

5 folds por animal, 72 animales. Valores: promedio ± desviación entre folds.
"vs media" es la mejora en RMSE frente a predecir la media del train
(positivo = mejor).

| Medida | RMSE final | RMSE media | vs media | r final | r CNN base | vs media (CNN base) |
|---|---:|---:|---:|---:|---:|---:|
| Largo oblicuo (cm) | 11.90 ± 2.53 | 11.67 | −2.0 % | 0.28 ± 0.34 | 0.15 | −11.9 % |
| Altura a la cruz (cm) | 7.08 ± 1.92 | 7.70 | **+8.1 %** | 0.49 ± 0.17 | 0.45 | +0.3 % |
| Perímetro torácico (cm) | 11.26 ± 1.12 | 11.38 | **+1.1 %** | 0.32 ± 0.23 | 0.18 | −17.9 % |
| Largo de cadera (cm) | 4.49 ± 1.02 | 4.58 | **+2.0 %** | 0.25 ± 0.32 | 0.05 | −14.3 % |
| Peso (kg) | 83.79 ± 9.09 | 86.76 | **+3.4 %** | 0.40 ± 0.21 | 0.16 | −19.0 % |

- El método final le gana a la media en 4 de 5 medidas y mejora la r en las 5
  frente a la CNN base. La CNN base pierde contra la media en 4 de 5.
- Figura: `results/figures/vision_real_vs_pred.png`, con las medidas reales
  vs. predichas de cada animal cuando estuvo en test.
- Tablas: `results/vision/metricas_cnn.csv` (la que lee el dashboard),
  `metricas_cnn_folds.csv` (por fold, con `rmse_base`) y
  `predicciones_cnn.csv` (real y predicho por animal). La CNN base queda en
  `results/vision/historico/`.

## 5. Problemas y limitaciones

- **La mejora es modesta.** El método más fuerte gana un 8 % en altura y entre
  1 y 3 % en las demás; el largo oblicuo no le gana a la media.
- **No hay referencia de escala.** La cámara no estuvo siempre a la misma
  distancia, así que los píxeles no se traducen directamente a cm o kg.
  Además, las fotos 4:3 se aplastan a 224×224. Ese es el techo principal.
- **Predicciones conservadoras.** Ridge acerca las predicciones a la media, por
  lo que subestima a los animales extremos. Por ejemplo, el animal 4 pesa
  604 kg y el modelo predice 481 kg.
- **Pocos animales.** Con 14 o 15 por fold, la r de cada fold varía mucho (ver
  las desviaciones de la tabla). La r calculada con los 72 animales juntos en
  la figura es más baja que el promedio por fold, porque cada fold tiene su
  propia media de train.
- Los animales son Horqin, no Holstein: el resultado no se traslada
  directamente a la población genómica del proyecto.
- Dependencia nueva: `rembg[cpu]`, que descarga U²-Net (~176 MB) desde GitHub
  la primera vez.

## 6. Archivos

- Código: `src/data/imagenes.py` (endereza las posteriores),
  `src/vision/dataset.py`, `src/vision/cnn.py`, `src/vision/silueta.py`,
  `src/vision/entrenar.py`.
- Tests: `tests/test_vision.py` (13 tests) y `tests/test_predecir.py` (5 tests).
- Dashboard: `src/vision/predecir.py` y el modo `--final` de `src/vision/entrenar.py`.
- Salidas: `results/vision/` y `results/figures/vision_real_vs_pred.png`.
- Reproducir, con el dataset original descomprimido:

```bash
python src/data/imagenes.py --tabla "<dataset>/measurements.xlsx" --lateral "<dataset>/side view" --posterior "<dataset>/back view"
python -m src.vision.entrenar                       # método final (ensamble)
python -m src.vision.entrenar --metodo cnn --salida results/vision/historico/metricas_cnn_base.csv
```

## Uso en el dashboard

- **Modelo final.** `python -m src.vision.entrenar --final` ajusta los mismos
  dos Ridge con los **72 animales** (sin folds) y los guarda en
  `models/vision/ensamble.joblib` (~0.2 MB, no se sube al repo). El error que
  se reporta sigue siendo el de la validación cruzada, que el paquete copia de
  `results/vision/metricas_cnn.csv`.
- **`predecir()`** (`src/vision/predecir.py`) recibe la foto lateral y la
  posterior de una vaca nueva y repite los pasos del entrenamiento: foto a
  224×224, features de MobileNetV2, silueta con U²-Net, los dos Ridge y su
  promedio. Devuelve las 5 medidas y su error esperado, por ejemplo
  ±84 kg en peso. Si no encuentra la vaca en una foto, avisa con un error claro.
  Desde la terminal:
  `python -m src.vision.predecir --lateral <foto> --posterior <foto>`.
- **Por qué no se endereza la foto nueva.** La regla "posterior horizontal →
  girar 90°" corrige un defecto de este dataset. Una foto nueva tomada en
  horizontal puede estar bien, así que por defecto no se gira. Sí se corrige la
  rotación que guardan los celulares en el EXIF. `--enderezar` solo se usa con
  fotos originales del dataset de Mongolia.
- **Advertencia.** El modelo se entrenó con 72 vacas Horqin, fotografiadas con
  un encuadre parecido. Con fotos de otras razas, a otra distancia de la cámara
  o con otro encuadre, el error puede ser mayor que el de la validación
  (±84 kg en peso, ±7 cm en altura).

## 7. Para la PPT

Tres ideas clave:

1. Con 72 animales, **usar la CNN como extractor y regularizar** (Ridge)
   funciona mejor que entrenarla: pasa de perder contra la media en 4 de 5
   medidas a ganarle en 4 de 5.
2. **Revisar los datos importa:** 70 fotos posteriores venían giradas en el
   propio dataset y se enderezaron antes de modelar.
3. La foto sola tiene un **techo**: sin referencia de escala, la mejor medida
   (altura) mejora un 8 % sobre la media. Para pasar a producción haría falta
   una distancia de cámara fija o un objeto de tamaño conocido en la foto.

Figura recomendada: `results/figures/vision_real_vs_pred.png`.

## Referencias

[1] M. Sandler, A. Howard, M. Zhu, A. Zhmoginov y L.-C. Chen, "MobileNetV2:
Inverted Residuals and Linear Bottlenecks", *CVPR*, 2018. DOI
[10.1109/CVPR.2018.00474](https://doi.org/10.1109/CVPR.2018.00474).

[2] X. Qin, Z. Zhang, C. Huang, M. Dehghan, O. R. Zaiane y M. Jagersand,
"U²-Net: Going deeper with nested U-structure for salient object detection",
*Pattern Recognition*, 2020. DOI
[10.1016/j.patcog.2020.107404](https://doi.org/10.1016/j.patcog.2020.107404).

[3] K. He, X. Zhang, S. Ren y J. Sun, "Deep Residual Learning for Image
Recognition", *CVPR*, 2016. DOI
[10.1109/CVPR.2016.90](https://doi.org/10.1109/CVPR.2016.90).
