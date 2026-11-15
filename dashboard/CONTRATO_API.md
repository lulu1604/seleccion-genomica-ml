# Contrato del dashboard

El backend solo LEE archivos. Si el archivo real no existe o solo tiene
encabezado, usa el de prueba y responde `"demo": true`.

| Datos | Archivo real | Archivo de prueba |
|---|---|---|
| Resultados | `results/resultados.csv` | `data/sample/resultados_demo.csv` |
| SHAP | `results/shap_top_snp.csv` | `data/sample/shap_demo.csv` |
| Visión | `results/vision/metricas_cnn.csv` | `data/sample/vision_demo.csv` |

Columnas:
- resultados: `modelo, rasgo, escenario_n, ruido, fold, r_pearson, rmse, tiempo_s`
- shap: `snp, rsid, gen, importancia, n_papers`
- vision: `medida, rmse, mae, r_pearson`

## Endpoints

| Método y ruta | Devuelve |
|---|---|
| `GET /api/salud` | `{"estado": "ok", "demo": {"resultados": bool, "shap": bool, "vision": bool}}` |
| `GET /api/resumen` | `{"demo": bool, "filas": [{modelo, rasgo, escenario_n, ruido, r_medio, r_desv, rmse_medio, n_folds}]}` |
| `GET /api/resultados?modelo=&rasgo=&escenario_n=` | `{"demo": bool, "filas": [filas por fold con las columnas de resultados.csv]}` |
| `GET /api/shap?top=20` | `{"demo": bool, "filas": [{snp, rsid, gen, importancia, n_papers}]}` ordenado por importancia descendente |
| `GET /api/vision` | `{"demo": bool, "filas": [{medida, rmse, mae, r_pearson}]}` |

Los NaN se devuelven como `null`. `r_desv` es la desviación estándar muestral
entre folds (`null` si hay un solo fold).

## Endpoints para el ganadero

Los usa el frontend. Los errores responden `{"detail": "mensaje para mostrar tal cual"}`.

| Archivo | Para qué |
|---|---|
| `models/genomica/ridge_holstein.npz` | Paquete genómico (lo arma `dashboard/backend/preparar_genomica.py`; no se sube) |
| `data/sample/genotipos_ejemplo.csv` | 12 animales de ejemplo: `id_animal, tipo, SNP1..SNP42551` (0/1/2) |
| `models/vision/ensamble.joblib` | Modelo de visión de `src/vision/predecir.py` (no se sube) |
| `results/resumen_e6.csv`, `results/vision/metricas_cnn.csv`, `results/vision/predicciones_cnn.csv` | Datos de "¿Por qué confiar?" y de los ejemplos de medición |

| Método y ruta | Devuelve |
|---|---|
| `GET /api/ejemplo` | `{"demo": true, "total": 12, "animales": [animal]}` con el archivo de ejemplo |
| `GET /api/ejemplo/archivo` | El CSV de ejemplo como descarga (`ejemplo_adn.csv`) |
| `GET /api/plantilla` | Plantilla de Excel vacía (`plantilla_bovigen.xlsx`), ver abajo. 503 si falta el paquete genómico |
| `GET /api/ejemplo/excel` | La plantilla llena con los 12 animales de ejemplo (`ejemplo_bovigen.xlsx`) |
| `POST /api/evaluar` | Multipart con `archivo`: la plantilla `.xlsx` o un CSV (se reconoce por el contenido: un `.xlsx` empieza con `PK`). Igual que `/api/ejemplo` pero `"demo": false`. 422 si el archivo no es válido (si no es ni CSV ni Excel: "Sube la plantilla de Excel (.xlsx) o un CSV como el de ejemplo."), 413 si pesa más de 60 MB |
| `POST /api/medir` | Multipart con `lateral` y `posterior` (fotos). `{"peso": {clave, nombre, valor, error, unidad, min, max}, "medidas": [{clave, nombre, valor, error, unidad}]}`. 422 si no encuentra la vaca, 503 si falta el modelo |
| `GET /api/medir/ejemplos` | `{"ejemplos": [{id, real_kg, estimado_kg, dentro, foto_lateral}] (vacas 1-3), "todas": [{id, real_kg, estimado_kg, dentro}] (72), "error_kg"}` |
| `GET /api/medir/foto/{id}/{vista}` | Foto JPG de muestra; `id` 1-3 y `vista` `lat` o `pos` (si no, 404) |
| `GET /api/confianza` | `{"animales_referencia", "aciertos": [{rasgo, de_cada_10}], "tamanos": [{nombre, nivel, ancho}], "error_peso_kg", "error_altura_cm"}`. 503 si faltan los resultados |

Un `animal` es:
```
{"id": "Anim2042", "tipo": "Toro", "nombre": "",
 "percentiles": {"grasa": 0-100, "leche": 0-100, "ubre sana": 0-100},
 "etiqueta": "bueno en las 3" | "destaca en …" | "sobre el promedio" | "bajo el promedio",
 "por_prioridad": {"balanceado" | "grasa" | "leche" | "ubre":
                   {"puntaje": 0-100, "categoria", "accion", "puesto"}},
 "zonas": {"grasa" | "leche" | "ubre sana":
           [{"marcador", "zona", "detalle", "gen", "cromosoma", "resto": false,
             "efecto": "sube" | "baja", "valor"}, …,
            {"marcador": "", "zona": "Resto de su ADN", "detalle": "Miles de zonas pequeñas sumadas",
             "gen": "", "cromosoma": 0, "resto": true, "efecto", "valor"}]}}
```

Zonas de la ficha (por rasgo): las 3 que más suben, la que más baja (si no está ya entre
las que suben) y al final la fila `resto`, con la suma de todo lo que no se muestra. Así
la suma de `valor` de todas las filas = aporte total del ADN a ese rasgo.

- `zona`: "Zona del cromosoma N" (con mapa de marcadores en el paquete; sin mapa,
  "Otra zona del ADN" o la zona conocida del cromosoma 14).
- `gen`: gen conocido de la zona (`DGAT1`, `MGST1`, `GHR`, `caseínas`, `AGPAT6`, `FASN`) o
  `""`. Los marcadores de un gen conocido van juntos en UNA fila, con `detalle` propio de
  cada rasgo (p. ej. DGAT1 en leche: "sube la grasa, pero baja un poco los litros").
  Sin gen: `detalle` = "Sin gen identificado".
- `cromosoma`: 1-29, o 0 si no se sabe (sin mapa) y en la fila `resto`.
- `resto`: `true` solo en la última fila.
- `marcador`: el de mayor aporte de la fila (vacío en `resto`); el frontend no lo muestra.
- El mapa sale de `results/mapa_snp.csv` (`snp, cromosoma, mb_aprox`), que arma
  `dashboard/backend/estimar_mapa.py` y lee `preparar_genomica.py`.

- Medidas, en este orden: Peso (`peso_kg`), Altura a la cruz (`altura_cruz_cm`),
  Perímetro del tórax (`perimetro_toracico_cm`), Largo del cuerpo (`largo_oblicuo_cm`),
  Largo de cadera (`largo_cadera_cm`). `error` es el RMSE de la validación cruzada;
  `min`/`max` del peso = valor ± error.
- `dentro` = |estimado − real| ≤ error de peso (RMSE de `metricas_cnn.csv`).
- `de_cada_10` = `round(10 × (0.5 + asin(r) / π))` con el r medio de ridge en Holstein.
- `tamanos`: r medio de gblup por escenario (Holstein: promedio de los 3 rasgos);
  nivel Baja < 0.3, Media < 0.6, Alta ≥ 0.6; `ancho` = r / r máximo × 100.
- `tipo` y `nombre` vienen del archivo (vacíos si no están).

### Plantilla de Excel

Excel aguanta 16,384 columnas y el ADN tiene 42,551 marcadores, así que los marcadores van en filas:

| Hoja | Contenido |
|---|---|
| `Instrucciones` | Cómo llenarla, sin términos técnicos |
| `Animales` | `id_animal`, `tipo` (lista: `Toro`, `Vaca`, `Vaquilla`, o vacío), `nombre` (opcional) |
| `ADN` | Columna A `marcador` (`SNP1`..`SNP42551`, en el orden del paquete); desde la B, una columna por animal con su `id_animal` en la fila 1 y valores 0/1/2 |

Errores propios del Excel (422): falta la hoja Animales o ADN, un animal sin columna en ADN, una
columna de ADN que no está en Animales, un `tipo` no válido, o Animales vacía. Marcadores faltantes,
valores distintos de 0/1/2 e ids repetidos se validan igual que en el CSV.
