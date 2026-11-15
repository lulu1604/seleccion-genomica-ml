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
| `POST /api/evaluar` | Multipart con `archivo` (CSV). Igual que `/api/ejemplo` pero `"demo": false`. 422 si el archivo no es válido, 413 si pesa más de 60 MB |
| `POST /api/medir` | Multipart con `lateral` y `posterior` (fotos). `{"peso": {clave, nombre, valor, error, unidad, min, max}, "medidas": [{clave, nombre, valor, error, unidad}]}`. 422 si no encuentra la vaca, 503 si falta el modelo |
| `GET /api/medir/ejemplos` | `{"ejemplos": [{id, real_kg, estimado_kg, dentro, foto_lateral}] (vacas 1-3), "todas": [{id, real_kg, estimado_kg, dentro}] (72), "error_kg"}` |
| `GET /api/medir/foto/{id}/{vista}` | Foto JPG de muestra; `id` 1-3 y `vista` `lat` o `pos` (si no, 404) |
| `GET /api/confianza` | `{"animales_referencia", "aciertos": [{rasgo, de_cada_10}], "tamanos": [{nombre, nivel, ancho}], "error_peso_kg", "error_altura_cm"}`. 503 si faltan los resultados |

Un `animal` es:
```
{"id": "Anim2042", "tipo": "Toro",
 "percentiles": {"grasa": 0-100, "leche": 0-100, "ubre sana": 0-100},
 "etiqueta": "bueno en las 3" | "destaca en …" | "sobre el promedio" | "bajo el promedio",
 "por_prioridad": {"balanceado" | "grasa" | "leche" | "ubre":
                   {"puntaje": 0-100, "categoria", "accion", "puesto"}},
 "zonas": {"grasa" | "leche" | "ubre sana":
           [{"marcador", "zona", "detalle", "efecto": "sube" | "baja", "valor"}]}}
```

- Medidas, en este orden: Peso (`peso_kg`), Altura a la cruz (`altura_cruz_cm`),
  Perímetro del tórax (`perimetro_toracico_cm`), Largo del cuerpo (`largo_oblicuo_cm`),
  Largo de cadera (`largo_cadera_cm`). `error` es el RMSE de la validación cruzada;
  `min`/`max` del peso = valor ± error.
- `dentro` = |estimado − real| ≤ error de peso (RMSE de `metricas_cnn.csv`).
- `de_cada_10` = `round(10 × (0.5 + asin(r) / π))` con el r medio de ridge en Holstein.
- `tamanos`: r medio de gblup por escenario (Holstein: promedio de los 3 rasgos);
  nivel Baja < 0.3, Media < 0.6, Alta ≥ 0.6; `ancho` = r / r máximo × 100.
