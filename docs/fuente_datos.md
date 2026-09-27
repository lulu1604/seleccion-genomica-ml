# Fuente de Datos Principal — Holstein Alemán (Zhang et al., 2015)

## 1. Referencia, Enlace y Licencia

* **Estudio:** Zhang et al. (2015), *Genome-Wide Association Studies for Quantitative Traits in Holstein Cattle*, **G3: Genes, Genomes, Genetics** (Vol. 5, Issue 11, pp. 2575–2581).
* **DOI:** [https://doi.org/10.1534/g3.115.016261](https://doi.org/10.1534/g3.115.016261)
* **Archivos suplementarios:** File S1 (genotipos) y File S2 (fenotipos / EBVs).
* **Licencia:** Datos de acceso libre para investigación académica, publicados como material suplementario de la revista *G3*.

---

## 2. Descripción del Dataset

### Genotipos (File S1 — `016261_files1.zip`)

| Propiedad | Valor |
|---|---|
| Archivo dentro del ZIP | `cattle_genotypes.txt` |
| Tamaño comprimido | 60.4 MB |
| Tamaño descomprimido | 408.2 MB |
| Separador | Tabulador (`\t`) |
| Encoding | UTF-8 / ASCII |
| Animales | **5,024** |
| SNPs | **42,551** |
| Columna ID | `Animal` (`Anim1` .. `Anim5024`) |
| Nombres de SNP | `SNP1` .. `SNP42551` (nombres internos del estudio) |
| Codificación | `0`, `1`, `2` (conteo de alelos de referencia) |
| Valores faltantes | **0** (ninguno) |
| IDs duplicados | **0** |
| Columnas SNP duplicadas | **0** |

> **IMPORTANTE:** Los nombres `SNP1`..`SNP42551` son identificadores internos del estudio.
> **No existe** un mapping completo confirmado hacia identificadores públicos de marcadores (rsIDs).
> `Table_S2.xls` contiene anotación para SNPs significativos por rasgo, pero **NO debe usarse**
> para renombrar automáticamente columnas asumiendo que `SNP1 = fila 1 de Table_S2`.

### Targets / EBVs (File S2 — `016261_files2.txt`)

| Propiedad | Valor |
|---|---|
| Separador | Tabulador (`\t`) |
| Encoding | UTF-8 / ASCII |
| Animales | **5,024** |
| Columnas | `id`, `mkg`, `fpro`, `scs` |
| Valores faltantes | **0** |
| IDs duplicados | **0** |

Los targets son **EBVs ya estandarizados por la fuente** (media ≈ 0, desviación estándar ≈ 1):

| Columna cruda | Significado biológico | Estadísticas |
|---|---|---|
| `mkg` | Producción de leche (*Milk Yield*, en kg) | min = −3.38, max = 3.32 |
| `fpro` | Porcentaje de grasa (*Fat Percentage*) | min = −3.57, max = 4.28 |
| `scs` | Células somáticas (*Somatic Cell Score*) | min = −4.46, max = 3.47 |

### Alineamiento de IDs

* File S1 y File S2 contienen exactamente los **mismos 5,024 animales**.
* Los IDs vienen en el **mismo orden** en ambos archivos.
* El script de preprocesamiento realiza alineamiento explícito por ID para garantizar correspondencia.

---

## 3. Archivos Crudos (`data/raw/holstein_2015/`)

Los archivos crudos se almacenan localmente y **NO se suben a GitHub** (bloqueados por `.gitignore`).

| Archivo | Descripción | Uso |
|---|---|---|
| `016261_files1.zip` | File S1: Matriz de genotipos (X) | **Input principal del preprocessing** |
| `016261_files2.txt` | File S2: Targets / EBVs (y) | **Input principal del preprocessing** |
| `016261_016261si.pdf` | Información suplementaria del paper | Referencia documental |
| `016261_tables1.pdf` | Tablas de resultados publicados (GBLUP/BayesB) | Comparación de baseline |
| `Table_S2.xls` | Anotación genómica de SNPs significativos | Material complementario (NO integrado a X) |
| `README_fuente_holstein.docx` | Documentación original de la fuente | Referencia |

### Checksums de archivos raw (para verificación de integridad)

| Archivo | MD5 |
|---|---|
| `016261_files1.zip` | `8c7eb6060952c9e618fd2d6213c3e0a7` |
| `016261_files2.txt` | `0634a0d23937650646264870934c4f0b` |

### Pasos de descarga

1. Acceder al paper: [https://doi.org/10.1534/g3.115.016261](https://doi.org/10.1534/g3.115.016261)
2. Descargar **File S1** (`016261_files1.zip`) y **File S2** (`016261_files2.txt`) desde la sección de material suplementario.
3. Colocar ambos archivos en `data/raw/holstein_2015/`.

---

## 4. Datos Procesados (`data/processed/holstein/`)

**NO se suben a GitHub.** Se regeneran ejecutando el script de preprocesamiento.

### Formato elegido: Parquet (Snappy, uint8)

**Alternativas evaluadas:**
| Formato | Ventajas | Desventajas | Decisión |
|---|---|---|---|
| **Parquet** | Preserva nombres de SNP, buena compresión, lectura rápida, integración nativa con pandas/pyarrow | Overhead de metadata con 42k columnas | **Elegido** |
| NPY/NPZ | I/O muy rápido | Pierde nombres de columnas, requiere archivos separados de metadata | Descartado |
| Feather | Similar a Parquet | Menor compresión para este tipo de datos | Descartado |

**Razón principal:** Parquet preserva los nombres de SNP dentro del archivo (no necesita `snp_ids.csv` separado), `pyarrow` ya está en `requirements.txt`, y el loader abstrae el formato para que el equipo no dependa de él.

### Archivos generados

| Archivo | Contenido | Tamaño |
|---|---|---|
| `X.parquet` | Matriz 5024 × 42551 (uint8, snappy) | ~59 MB |
| `y.csv` | Tabla con `id_animal`, `mkg`, `fpro`, `scs` | ~186 KB |
| `animal_ids.csv` | Llave explícita y orden de las filas de `X.parquet` | ~48 KB |
| `qc_report.json` | Reporte de control de calidad machine-readable | ~1.6 KB |
| `manifest.json` | Metadatos de reproducibilidad | ~850 B |

### Cómo regenerar los datos procesados

```bash
python src/data/preprocess_holstein.py
```

* Requiere: archivos raw en `data/raw/holstein_2015/`.
* Tiempo estimado: ~2-3 minutos.
* La matriz X ocupa ~204 MB como `uint8`; el preprocesamiento con pandas y
  PyArrow necesita margen adicional para copias temporales. Planificar al menos
  3 GB de RAM disponible para regenerarlo de forma segura.

---

## 5. Loader del Equipo

Todos los modelos deben usar el loader en lugar de leer los archivos directamente:

```python
from src.data.load_holstein import load_holstein

# Cargar X (ndarray uint8) y y (DataFrame con id_animal + 3 targets)
X, y = load_holstein()

# Cargar un target específico como array 1-D
X, y_mkg = load_holstein(target="mkg")
X, y_fpro = load_holstein(target="fpro")
X, y_scs = load_holstein(target="scs")

# Acceder a metadatos
from src.data.load_holstein import load_holstein_meta
meta = load_holstein_meta()
```

`X.parquet` contiene solamente SNPs para conservar la matriz con forma
`5024 × 42551`. La llave de cada fila se conserva en `animal_ids.csv`. Antes
de devolver datos, el loader valida forma, schema SNP, valores 0/1/2, IDs,
orden exacto `animal_ids.csv` ↔ `y.csv` y checksums de IDs/SNPs en el manifest.
Así, `X[i]` y `y[i]` corresponden al mismo animal; si el contrato se altera,
el loader falla con un error claro.

---

## 6. Datos de Muestra (`data/sample/holstein/`)

Para desarrollo y pruebas sin necesitar los 60 MB raw:

* **`X_toy.csv`**: 10 animales reales × 20 SNPs reales (`Anim1`..`Anim10`, `SNP1`..`SNP20`).
* **`y_toy.csv`**: Mismos 10 animales con targets reales (`id_animal`, `mkg`, `fpro`, `scs`).

> Estos archivos son una muestra para desarrollo, **NO para evaluación científica**.

---

## 7. Material Complementario (No integrado)

### `Table_S2.xls`
Contiene anotación genómica para SNPs que resultaron significativos en el estudio original (cromosoma, posición, gen).
**NO se integra a X** porque no existe correspondencia directa confirmada entre los índices `SNP1..SNP42551` y las filas de esta tabla.
Cualquier anotación biológica futura debe tratarse como un módulo separado.

### `016261_tables1.pdf`
Contiene resultados publicados de modelos GBLUP y BayesB del estudio original.
Sirve como **referencia de baseline** para comparar con los modelos del proyecto.
**NO se procesa como parte de X/y.**
