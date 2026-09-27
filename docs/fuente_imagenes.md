# Fuente de datos — Imágenes de ganado (vista lateral / posterior)

**Módulo:** Joe — Cattle Side/Back View (imágenes)
**Rama:** `f1-imagenes`
**Proyecto:** Selección Genómica de Precisión en Ganado Vacuno · Machine Learning ESAN 2026-2

> ⚠️ Este dataset **no comparte animales** con el dataset genómico (Holstein alemán,
> 5,024 toros). Los 72 bovinos de este módulo no tienen genotipos y los toros
> alemanes no tienen fotos. Es un **módulo aparte**: de la foto estimamos peso
> y medidas corporales, no hay conexión con el ADN.

---

## 1. Fuente original

- **Nombre del dataset:** Cattle side view and back view dataset
- **Autora:** Lili Bai (2024)
- **Repositorio:** Mendeley Data
- **DOI:** `10.17632/h2s22wr5py.2`
- **URL:** https://data.mendeley.com/datasets/h2s22wr5py/2
- **Paper asociado:** "Image dataset for cattle biometric detection and analysis" (Data in Brief / ScienceDirect)
- **Origen de los datos:** ganado Horqin (raza amarilla), recolectado en pueblos del este de la región autónoma de Mongolia Interior, China
- **Peso del ZIP descargado:** 2.46 GB (2,461,778,220 bytes)
- **Licencia:** Mendeley Data — CC BY 4.0 (verificar el texto exacto en la página del dataset al momento de citar en el informe final)

## 2. Descripción del dataset (confirmado sobre los archivos reales)

| Pregunta | Respuesta |
|---|---|
| ¿Cuántos animales hay? | 72 bovinos |
| ¿Cuántas fotos hay por animal? | 2 (una vista lateral + una vista posterior) → 144 fotos en total |
| ¿Todos tienen lateral y posterior? | **Sí, confirmado.** Los 72 animales tienen ambas fotos; 0 incompletos al correr el script |
| Resolución original de las fotos | Variable, del orden de 4032×3024 px (JPEG/PNG de alta resolución, pesos entre ~11 MB y ~23 MB por archivo) |
| Formato de archivo original | `.png` para 143 fotos; **excepción:** el animal `50` en la carpeta `back view/` viene como `50.jpg` en vez de `.png` |
| Estructura de carpetas | `Cattle side and back view images/side view/{id}.png` y `Cattle side and back view images/back view/{id}.png`, con `id` de 1 a 72. El nombre de archivo es solo el número, sin sufijo de vista (la vista la define la carpeta, no el nombre) |
| Formato de la tabla de medidas | `measurements.xlsx` (14 KB, 72 filas, sin celdas vacías) |
| Columnas de la tabla de medidas | `Num`, `Oblique body length (cm)`, `Withers height(cm)`, `Heart girth(cm)`, `Hip length (cm)`, `Body weight (kg)` |
| Unidades | Medidas corporales en centímetros (cm), peso en kilogramos (kg) |
| ¿Cómo se relaciona cada foto con su fila? | La columna `Num` de la tabla coincide exactamente con el nombre de archivo (`Num=1` → `side view/1.png` y `back view/1.png`) |
| Peso total del dataset descargado | 2.46 GB comprimido (ZIP); las 144 fotos originales sin comprimir |
| Licencia de uso | CC BY 4.0 (Mendeley Data) |

## 3. Pasos de descarga (para que cualquiera pueda repetirlo)

1. Entrar a https://data.mendeley.com/datasets/h2s22wr5py/2
2. Descargar el archivo completo (botón "Download all")
3. Descomprimir el ZIP; queda una carpeta `Cattle side and back view images/` con dos subcarpetas (`side view/`, `back view/`) y el archivo `measurements.xlsx`
4. Colocar todo dentro de `data/raw/imagenes/` (esta carpeta está bloqueada por `.gitignore`, no se sube al repo)
5. Correr `src/data/imagenes.py` (ver sección siguiente) para generar el índice y las muestras

## 4. Procesamiento

Script: `src/data/imagenes.py`

```bash
python src/data/imagenes.py \
    --tabla "data/raw/imagenes/Cattle side and back view images/measurements.xlsx" \
    --lateral "data/raw/imagenes/Cattle side and back view images/side view" \
    --posterior "data/raw/imagenes/Cattle side and back view images/back view" \
    --salida results/imagenes_index.csv \
    --procesadas data/processed/imagenes \
    --muestra data/sample/imagenes \
    --n-muestra 3
```

El script:
- Lee `measurements.xlsx` y renombra las columnas a snake_case en español
- Busca, para cada `Num`, su foto en `side view/{Num}.png|.jpg` y `back view/{Num}.png|.jpg`
- Redimensiona cada foto emparejada a 224×224 (guardadas como `.jpg`, calidad 90)
- Reporta en consola cuántos animales quedaron completos y cuántos se perdieron (y por qué)
- Guarda el índice final en `results/imagenes_index.csv`
- Copia animales de ejemplo ya redimensionados a `data/sample/imagenes/` (estos sí se suben al repo)

**Resultado real de la corrida:** 72/72 animales completos, 0 incompletos.

## 5. Formato de salida

```
results/imagenes_index.csv
id_animal_img,ruta_lateral,ruta_posterior,peso_kg,altura_cruz_cm,perimetro_toracico_cm,largo_oblicuo_cm,longitud_cadera_cm
1,data/processed/imagenes/1_lat.jpg,data/processed/imagenes/1_pos.jpg,545,124,190,161,47
2,data/processed/imagenes/2_lat.jpg,data/processed/imagenes/2_pos.jpg,507,120,183,152,43
```

> Nota: el formato final incluye dos columnas adicionales respecto a la plantilla original del F1 (`largo_oblicuo_cm` y `longitud_cadera_cm`), porque la tabla real trae 4 medidas corporales en vez de 2. Se mantienen todas para no perder información.

## 6. Estado

- [x] Dataset descargado y descomprimido (2.46 GB)
- [x] Tabla de medidas inspeccionada: 72 filas, 6 columnas, sin nulos
- [x] Script `src/data/imagenes.py` ajustado a la estructura real (carpetas por vista, excepción del archivo `.jpg`)
- [x] 144 fotos redimensionadas a 224×224 (72 laterales + 72 posteriores)
- [x] `results/imagenes_index.csv` generado — 72/72 animales completos
- [x] `data/sample/imagenes/` con 3 animales de ejemplo (6 fotos, ~108 KB) listo para subir al repo
- [x] Confirmado explícitamente: este dataset no comparte animales con el dataset genómico
