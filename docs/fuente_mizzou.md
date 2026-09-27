# Fuente de Datos Complementaria — Mizzou Hair Shedding (Durbin et al., 2021 / 2024)

## 1. Referencia del Estudio, Enlaces y Licencia

* **Estudio:** Durbin et al. (2024), *Genomic loci involved in sensing environmental cues and metabolism affect seasonal coat shedding in Bos taurus and Bos indicus cattle*, **G3: Genes|Genomes|Genetics**, Volume 14, Issue 2, February 2024.
* **DOI del Paper:** [https://doi.org/10.1093/g3journal/jkad279](https://doi.org/10.1093/g3journal/jkad279)
* **Preprint:** [https://doi.org/10.1101/2022.12.14.520472](https://doi.org/10.1101/2022.12.14.520472)
* **Repositorio Dryad (DOI):** [https://doi.org/10.5061/dryad.ngf1vhhz4](https://doi.org/10.5061/dryad.ngf1vhhz4)
* **Repositorio de Código Público:** [https://github.com/harlydurbin/mizzou_hairshed_public](https://github.com/harlydurbin/mizzou_hairshed_public)
* **Licencia:** CC0 1.0 Universal (Dominio Público).
* **Carácter en el proyecto:** **Fuente secundaria/complementaria**. No sustituye ni se combina con la fuente principal de Holstein 2015.

---

## 2. Archivos Locales y Artefactos Reportados por la Fuente

Los archivos crudos se ubican en la carpeta local `data/raw/mizzou/` y **no se suben a GitHub** (protegidos por `.gitignore`).

| Archivo | Formato | Tamaño / checksum | Evidencia | Estado local |
|---|---|---|---|---|
| `Durbin_etal_2021_MizzouHairShedding_pheno_metadata.csv` | CSV | 2,944,572 bytes; SHA-256 `4a60…8e03c` | Verificado localmente | **Disponible** |
| `Durbin_README.md` | Markdown | 5,618 bytes; SHA-256 `f2ed…5fee` | Verificado localmente | **Disponible** |
| `Durbin_etal_2021_MizzouHairShedding_genotypes.vcf.gz` | VCF (BGZF) | ~3.18 GB; checksum reportado `14dce…e03c` | Reportado por Dryad, no recalculado | **No descargado** |
| `Durbin_etal_2021_MizzouHairShedding_genotypes.vcf.gz.tbi` | Tabix index | ~2.21 MB; checksum reportado `ac266…e43221` | Reportado por Dryad, no recalculado | **No descargado** |

---

## 3. Datos Genómicos VCF — Reportados por la Fuente, No Verificados Localmente

El VCF y su índice Tabix no están presentes en `data/raw/mizzou/`; por tanto,
no se inspeccionaron su header, assembly, cromosomas ni la semántica de la
columna `ID`.

El README local de la fuente reporta **846,153 marcadores SNP imputados** para
**10,393 bovinos**. Estos conteos son información reportada por la fuente, no
una verificación del archivo local. Cuando el VCF exista, se deberá inspeccionar
directamente `#CHROM`, `POS`, `ID`, `REF`, `ALT`, `FORMAT`, las muestras y la
referencia genómica antes de afirmar IDs rs, cromosomas o assembly.

La descarga, si un alcance futuro la requiere, se hace manualmente desde
[Dryad](https://doi.org/10.5061/dryad.ngf1vhhz4) hacia `data/raw/mizzou/`.

---

## 4. Inspección del Dataset Fenotípico / Metadatos

### Cifras Verificadas y Discrepancia Documental
* **Número real de observaciones:** **36,899 filas de datos** (excluyendo la cabecera).
* **Confirmación de la discrepancia (36,900 vs 36,899):**
  El archivo físico `Durbin_etal_2021_MizzouHairShedding_pheno_metadata.csv` contiene exactamente **36,900 líneas en texto** (1 línea de encabezados + 36,899 registros de fenotipos). El README cita "36,900 observations" por conteo bruto de líneas, pero el abstract oficial del paper y los metadatos de Dryad confirman inequívocamente: *"36,899 repeated phenotypes from 13,364 cattle"*.
* **Número de animales únicos:** **13,364 bovinos** (identificados por la columna `id`).
* **Repetición de observaciones por animal (modelo de registros repetidos):**
  * Rango de observaciones por animal: **1 a 28 registros**.
  * Mediana: **2 observaciones**.
  * Media: **2.76 observaciones**.
  * 4,069 animales tienen 1 observación; 4,127 tienen 2; 2,394 tienen 3; 1,534 tienen 4; y 1,240 tienen 5 o más observaciones a lo largo de los años.
* **Periodo temporal cubierto:** Del **2012-03-27** al **2020-06-25**.

### Variables y Faltantes (12 Columnas)

| Columna | Tipo | Valores Faltantes | % Faltantes | Descripción y Distribución |
|---|---|---|---|---|
| `id` | Texto / ID | **0** | 0.00% | Identificador anónimo del animal (13,364 únicos). |
| **`hair_score`** | **Flotante / Entero** | **0** | **0.00%** | **Target principal:** Puntuación de muda de pelo (1: muda completa ~100%, 5: sin muda ~0%). Media: 2.62, Desv: 1.33, Mediana: 2.0. Conteo: Score 1 (8,988), 2 (10,589), 3 (7,482), 4 (5,144), 5 (4,682) y 14 casos decimales (1.5, 2.5, 3.5). |
| `sex` | Categórico | 4 | 0.01% | Sexo del animal: Hembras `F` (36,395), Machos `M` (500). |
| `coat_color` | Categórico | 2,061 | 5.59% | Color del pelaje reportado (`BLACK`, `RED`, `BRINDLE`, etc.). |
| `age_class` | Numérico | 1,059 | 2.87% | Clase de edad en años al momento de la evaluación (1 a 21). |
| `age_group` | Categórico | 1,059 | 2.87% | Grupo de edad codificado (1: 1 año, 2: 2-3 años, 3: 4-9 años, 4: 10+ años). |
| `calving_season` | Categórico | 1,712 | 4.64% | Estación de parto: `FALL` (20,390), `SPRING` (14,797). |
| `toxic_fescue` | Categórico | 544 | 1.47% | Indicador de pastoreo en festuca tóxica: `YES` (29,445), `NO` (6,910). |
| `score_group` | Entero | 0 | 0.00% | Grupo de puntuación asignado mediante ventana deslizante de 5 días. |
| `date_score_recorded` | Fecha (`YYYY-MM-DD`) | 454 | 1.23% | Fecha de recolección del puntaje de muda. |
| `mean_apparent_high` | Flotante | 454 | 1.23% | Temperatura aparente ("sensación térmica") promedio de los 30 días previos. |
| `mean_day_length` | Flotante | 454 | 1.23% | Duración media del día (horas de luz) en los 30 días previos. |

---

## 5. Datos de Muestra / Toy Data (`data/sample/mizzou/`)

Para desarrollo y pruebas locales de pipelines tabulares se proporciona:

* **`data/sample/mizzou/pheno_toy.csv`**:
  * Contiene las **primeras 200 filas reales** del dataset fenotípico.
  * Preserva exactamente las 12 columnas originales y sus tipos.
  * Se sube al repositorio para pruebas rápidas y prototipado sin descargar el CSV completo.

---

## 6. Reglas de Aislamiento
* **Completamente independiente de Holstein 2015:** Mizzou corresponde a poblaciones multirraza de carne de EE.UU. (Angus, Hereford, etc.), mientras que Holstein corresponde a toros lecheros alemanes de Zhang et al. (2015).
* Los identificadores de animales, marcadores y fenotipos **NO se deben mezclar**.
