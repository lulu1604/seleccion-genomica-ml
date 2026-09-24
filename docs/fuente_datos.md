# Fuente de Datos Principal — Holstein Alemán (Zhang et al., 2015)

## 1. Referencia del Estudio, Enlace y Licencia
* **Estudio:** Zhang et al. (2015), *Genome-Wide Association Studies for Quantitative Traits in Holstein Cattle*, **G3: Genes, Genomes, Genetics** (Vol. 5, Issue 11, pp. 2575–2581).
* **Enlace oficial:** [https://doi.org/10.1534/g3.115.016261](https://doi.org/10.1534/g3.115.016261)
* **Archivos suplementarios:** File S1 (Genotipos $X$) y File S2 (Fenotipos / EBVs $y$).
* **Licencia / Uso:** Datos de libre acceso académico para investigación proporcionados en el portal suplementario de la revista *G3*.

---

## 2. Pasos de Descarga y Almacenamiento Local
1. Ingresar al enlace del paper suplementario de *G3*: `https://doi.org/10.1534/g3.115.016261`.
2. Descargar los archivos suplementarios **File S1** (`016261_files1.zip`) y **File S2** (`016261_files2.txt`).
3. Guardar los archivos descargados en la carpeta local `data/raw/holstein_2015/`.

---

## 3. Especificaciones de los Archivos Crudos (`data/raw/holstein_2015/`)
Los archivos crudos se almacenan en `data/raw/holstein_2015/` y **no se suben a GitHub** (bloqueados mediante `.gitignore`).

| Archivo | Formato / Separador | Número de Filas / Animales | Número de Columnas | Codificación / Contenido |
|---|---|---|---|---|
| `016261_files1.zip` | Comprimido (ZIP) | **5,024 animales** | **42,551 SNPs** | Genotipos ($X$) codificados como `0`, `1` y `2` (alelos de riesgo/referencia). |
| `016261_files2.txt` | Texto plano (`\t` tabulador) | **5,024 animales** (+1 fila de cabecera) | 4 columnas (`id`, `mkg`, `fpro`, `scs`) | Fenotipos ($y$ / GEBV). Contiene valores continuos por rasgo. |
| `016261_016261si.pdf` | PDF | N/A | N/A | Información y métodos suplementarios del estudio. |
| `016261_tables1.pdf` | PDF | N/A | N/A | Tablas de resultados de referencia (modelos GBLUP y BayesB). |
| `Table_S2.xls` | Excel (XLS) | N/A | N/A | Anotación genómica complementaria de SNPs significativos. |
| `README_fuente_holstein.docx` | Documento (DOCX) | N/A | N/A | Documentación descriptiva original suministrada con la fuente. |

---

## 4. Correspondencia de Nombres de Fenotipos (File S2 → Proyecto)

Para estandarizar el código y contrato de datos del proyecto, los nombres de columnas de fenotipos en `016261_files2.txt` se mapean de la siguiente manera:

| Columna Cruda (File S2) | Nombre Estandarizado en Proyecto | Significado Biológico |
|---|---|---|
| `id` | `id_animal` | Identificador único del animal (`Anim1` .. `Anim5024`). |
| `mkg` | `leche` | Producción de leche (*Milk Yield*, en kg). |
| `fpro` | `grasa` | Porcentaje de grasa (*Fat Percentage*, en %). |
| `scs` | `celulas_somaticas` | Puntuación de células somáticas (*Somatic Cell Score*). |

* **Mapeo explícito obligatorio:**
  * `leche` = `mkg`
  * `grasa` = `fpro`
  * `celulas_somaticas` = `scs`

---

## 5. Datos de Muestra / Toy Data (`data/sample/`)
Para permitir que el equipo pruebe los modelos sin manejar los 63 MB crudos, se incluyen dos datasets sintéticos en `data/sample/`:

* **`data/sample/X_toy.csv`**:
  * 10 animales (`A0001` .. `A0010`).
  * 20 SNPs (`snp_00001` .. `snp_00020`).
  * Codificación SNP: valores enteros `0`, `1` y `2`.
* **`data/sample/y_toy.csv`**:
  * Mismos 10 animales (`A0001` .. `A0010`).
  * Columnas: `id_animal,leche,grasa,celulas_somaticas`.
