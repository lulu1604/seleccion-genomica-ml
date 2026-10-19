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
