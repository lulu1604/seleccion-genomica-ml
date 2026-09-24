# Fuente de Datos Complementaria — Mizzou Hair Shedding (Durbin et al., 2021)

## 1. Referencia del Estudio y Contexto
* **Estudio:** Durbin et al. (2021), *Genomic loci involved in sensing environmental cues and metabolism affect seasonal coat shedding in Bos taurus and Bos indicus cattle*.
* **Soporte:** USDA National Institute of Food and Agriculture (AFRI Grant no. 2016-68004-24827).
* **Repositorio público:** [harlydurbin/mizzou_hairshed_public](https://github.com/harlydurbin/mizzou_hairshed_public)
* **Carácter en el proyecto:** **Fuente secundaria/complementaria**. No sustituye ni se combina con la fuente principal de Holstein 2015.

---

## 2. Archivos Locales

### Datos Crudos (`data/raw/durbin_hairshedding/`)
*(Bloqueados en Git por `.gitignore`)*

* **`Durbin_etal_2021_MizzouHairShedding_pheno_metadata.csv`**: Archivo con 36,900 observaciones de fenotipo y metadatos ambientales.
* **`Durbin_README.md`**: Copia original del README del repositorio oficial de la data.

### Datos de Muestra (`data/sample/durbin_sample.csv`)
*(Subido al repositorio para pruebas)*

* **`data/sample/durbin_sample.csv`**: Primeras 10 filas reales extraídas del dataset original para probar flujos de datos sin descargar el archivo completo.

---

## 3. Estructura de Columnas y Variables

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | String | Identificador anónimo del bovino. |
| `sex` | String | Sexo del animal (`M` o `F`). |
| `coat_color` | String | Color del pelaje reportado por el criador (ej. `BLACK`, `RED`, `BRINDLE`, `WHITE`). |
| `age_class` | Entero (1-21) | Clase de edad ajustada en años al momento del fenotipado. |
| `age_group` | Entero (1-4) | Agrupación de edad (1: 1 año, 2: 2-3 años, 3: 4-9 años, 4: 10+ años). |
| `calving_season` | String | Estación de parición (`SPRING`, `FALL`, o `NA` para machos). |
| `toxic_fescue` | Booleano | Indica si el animal pastó festuca tóxica en primavera (`TRUE` / `FALSE`). |
| `score_group` | Entero | Grupo de puntuación según ventana móvil de 5 días. |
| `date_score_recorded` | Fecha (`YYYY-MM-DD`) | Fecha en que se registró el fenotipo. |
| `mean_apparent_high` | Flotante | Sensación térmica promedio de los 30 días previos al registro. |
| `mean_day_length` | Flotante | Horas de luz solar promedio de los 30 días previos. |
| **`hair_score`** | **Entero (1-5)** | **Target principal:** Puntuación de muda de pelo (1: muda completa ~100%, 5: sin muda ~0%). |

---

## 4. Datos Genómicos Suplementarios (VCF — No descargados localmente)

Esta fuente dispone de datos genómicos imputados almacenados externamente:

* **Archivo VCF:** `Durbin_etal_2021_MizzouHairShedding_genotypes.vcf.gz` (~3.18 GB)
* **Índice Tabix:** `Durbin_etal_2021_MizzouHairShedding_genotypes.vcf.gz.tbi`
* **Contenido:** 846,153 marcadores SNP imputados para 10,393 bovinos.

### Instrucciones de Descarga (En caso de uso futuro):
1. Acceder al repositorio oficial: [github.com/harlydurbin/mizzou_hairshed_public](https://github.com/harlydurbin/mizzou_hairshed_public) o enlace de archivo en Dryad.
2. Descargar los archivos `.vcf.gz` y `.vcf.gz.tbi` dentro de `data/raw/durbin_hairshedding/`.
3. **Atención:** Los archivos `.vcf.gz` están automáticamente excluidos del control de versiones mediante `.gitignore`.

---

## 5. Reglas de Aislamiento e Integración
* **No Mezclar:** Los IDs, SNPs y el target (`hair_score`) de este dataset corresponden a una población y experimento distintos a Holstein 2015.
* **Uso Independiente:** Si se desarrollan modelos para esta fuente, deben ejecutarse en un flujo independiente (ej. en un notebook o módulo separado).
