# Fase 1 — Extracción de datos

Proyecto: **Selección Genómica de Precisión en Ganado Vacuno** · Machine Learning ESAN 2026-2
Repo: `lulu1604/seleccion-genomica-ml`

---

## 0. Regla general: limpieza y llaves

Cada uno entrega su fuente **limpia y con su llave bien definida**. No todas las fuentes se juntan entre sí: solo se unen las que comparten una llave.

```
Holstein (SNPs) ──snp_id──► Ensembl (gen) ──nombre_gen──► PubMed (evidencia)
        se encadenan

Holstein  ⟷  AlphaSimR    NO se unen: son animales distintos.
                          Son datasets ALTERNATIVOS con el MISMO formato.

Imágenes (72 bovinos)     No se une con nada: módulo aparte.
```

| Fuente | Llave de salida | Con quién se cruza |
|---|---|---|
| Holstein | `id_animal`, `snp_id` | Con Ensembl por `snp_id` |
| AlphaSimR | `id_animal`, `snp_id` | Con nadie: corre por separado, mismo formato |
| Ensembl | `snp_id` → `gen` | Recibe de Holstein, entrega a PubMed |
| PubMed | `gen` | Recibe de Ensembl |
| Imágenes | `id_animal_img` | Con nadie |

**Lo que aplica a todos:**

- Nada de datos crudos al repo. El `.gitignore` bloquea `data/raw/` y `data/processed/`.
- Sí se suben los archivos de muestra chiquitos (`data/sample/`).
- Sin tildes, espacios ni mayúsculas en los nombres de columnas.
- Los identificadores siempre como texto, nunca como número (un ID que empieza en 0 pierde el 0 si es número).
- Faltantes siempre como celda vacía, nunca como 0, "NA" o "-".
- Cada script arriba lleva un comentario: qué hace, cómo se corre y qué archivo genera.
- Cada uno trabaja en su rama y abre un Pull Request que revisa otro integrante.

---

## 🔵 Lucero — Holstein alemán

**Fuente:** Zhang et al. (2015), *G3* — archivos suplementarios File S1 y File S2.
**Tipo:** estructurada · sin API · **es la data principal del proyecto**
**Rama:** `f1-holstein`

### Pasos

1. Descargar File S1 y File S2 del paper y guardarlos en `data/raw/`.
2. Anotar del archivo crudo: número de filas, número de columnas, separador, si tiene cabecera y cómo vienen codificados los SNPs.
3. Verificar que las tres columnas de fenotipo estén: producción de leche, % de grasa y células somáticas.
4. Crear los datos de juguete en `data/sample/` con 10 animales inventados y 20 SNPs, respetando la estructura real. **Estos sí se suben** y son lo que desbloquea a todo el grupo.
5. Escribir `docs/fuente_datos.md`: enlace, licencia, pasos de descarga y todo lo anotado en el punto 2.

### Formato de salida

```
data/sample/X_toy.csv
id_animal,snp_00001,snp_00002,...
A0001,0,2,...

data/sample/y_toy.csv
id_animal,leche,grasa,celulas_somaticas
A0001,320.5,-0.12,2.94
```

### Terminado cuando

- [ ] Los archivos crudos abren sin error
- [ ] `data/sample/` está en el repo y cualquiera lo puede leer con pandas
- [ ] `docs/fuente_datos.md` permite que otra persona repita la descarga sola

> ⚠️ Si el enlace del paper está caído, avisar al grupo **el mismo día**. Plan B: la simulación de Ana pasa a ser la fuente principal.

---

## 🟢 Ana — AlphaSimR (simulación)

**Fuente:** paquete AlphaSimR de R.
**Tipo:** estructurada · sin API · sostiene el aporte del proyecto
**Rama:** `f1-simulacion`

### Pasos

1. Instalar R y el paquete AlphaSimR.
2. Escribir `src/data/simular.R` con tres parámetros: `n_animales`, `n_snps` y `h2`.
3. Exportar con **exactamente las mismas columnas** que los datos de juguete de Lucero (mismos nombres, mismo orden, mismo separador).
4. Correrlo con n = 100, 500 y 2 000, guardando en `data/processed/sim_n100/`, `sim_n500/` y `sim_n2000/`.
5. Documentar en `docs/simulacion.md` qué parámetros se usaron en cada corrida, para que los resultados se puedan reproducir.

### Formato de salida

Igual al de Lucero, con `id_animal` con prefijo distinto para no confundir animales simulados con reales:

```
SIM_n500_0001,0,1,...
```

### Terminado cuando

- [ ] El script corre de principio a fin con los tres tamaños
- [ ] Las columnas son idénticas a las de `data/sample/`
- [ ] Está documentado qué valor de `h2` se usó en cada corrida

---

## 🟠 Ivan — Ensembl REST API

**Fuente:** API REST de Ensembl, especie *Bos taurus*.
**Tipo:** semiestructurada (JSON) · con API · traduce SNPs a genes
**Rama:** `f1-ensembl`

### Pasos

1. Leer la documentación de la API REST de Ensembl y probar una consulta suelta antes de programar.
2. Escribir `src/data/ensembl.py`: recibe un identificador de SNP y devuelve cromosoma, posición y gen más cercano.
3. Aplanar el JSON a una fila por SNP.
4. Guardar en disco lo ya consultado (una carpeta de caché) para no repetir llamadas, y respetar el límite de consultas por segundo que indica la documentación.
5. Probar con 5 SNPs y dejar el resultado en `results/snp_annot.csv`.

### Formato de salida

```
results/snp_annot.csv
snp_id,cromosoma,posicion,gen
rs109421300,14,1802265,DGAT1
```

### Terminado cuando

- [ ] Corre con una lista de SNPs y devuelve la tabla completa
- [ ] Si un SNP no existe en la base, escribe la fila con el gen vacío en vez de romperse
- [ ] La segunda vez que se corre usa la caché y no vuelve a llamar a la API

> La columna `snp_id` tiene que escribirse **igual** que en el dataset de Lucero. Si no, el cruce falla.

---

## 🟣 Chayna — PubMed / NCBI E-utilities

**Fuente:** abstracts de PubMed vía la API E-utilities del NCBI.
**Tipo:** **no estructurada** (texto libre) · con API · valida el sentido biológico
**Rama:** `f1-pubmed`

### Pasos

1. Leer la documentación de E-utilities y probar una búsqueda suelta en el navegador.
2. Escribir `src/data/pubmed.py`: recibe el nombre de un gen y descarga los abstracts de los papers que lo mencionan.
3. Limpiar el texto: pasar a minúsculas y quitar signos.
4. Contar menciones de las palabras clave: `milk`, `fat`, `yield`, `somatic cell`.
5. Guardar los abstracts crudos en `data/raw/pubmed/` y la tabla resumida en `results/gene_evidence.csv`.
6. Probar con el gen **DGAT1**, conocido por su efecto en la grasa de la leche: sirve de prueba de que el script funciona.

### Formato de salida

```
results/gene_evidence.csv
gen,n_papers,milk,fat,yield,somatic_cell
DGAT1,47,120,98,45,3
```

### Terminado cuando

- [ ] Corre con una lista de genes y devuelve la tabla
- [ ] Un gen sin resultados aparece con ceros, no rompe el script
- [ ] La columna `gen` coincide exactamente con la que entrega Ivan

---

## 🔴 Joe — Cattle Side/Back View (imágenes)

**Fuente:** Mendeley Data — 72 bovinos con fotos lateral y posterior + tabla de medidas corporales.
**Tipo:** **no estructurada** (imágenes) + etiquetas estructuradas · módulo aparte
**Rama:** `f1-imagenes`

### Pasos

1. Descargar el dataset a `data/raw/imagenes/` (no se sube al repo).
2. Documentar en `docs/fuente_imagenes.md`: cuántas fotos hay por animal, si todos tienen lateral y posterior, resolución, formato, qué columnas trae la tabla de medidas, en qué unidades, cómo se relaciona cada foto con su fila, peso total y licencia.
3. Escribir `src/data/imagenes.py`: leer la tabla, emparejar cada foto con su fila, redimensionar a 224×224 y reportar cuántos animales quedaron emparejados y cuántos se perdieron.
4. Subir 2 o 3 fotos de ejemplo ya redimensionadas a `data/sample/imagenes/`.

### Formato de salida

```
results/imagenes_index.csv
id_animal_img,ruta_lateral,ruta_posterior,peso_kg,altura_cruz_cm,perimetro_toracico_cm
B001,imagenes/B001_lat.jpg,imagenes/B001_pos.jpg,412.0,128.5,176.0
```

### Terminado cuando

- [ ] `docs/fuente_imagenes.md` responde todas las preguntas del punto 2
- [ ] El script reporta cuántos animales quedaron completos
- [ ] Está escrito explícitamente que **este dataset no comparte animales con el genómico**

> ⚠️ Los 72 bovinos no tienen genotipos y los 5 024 toros alemanes no tienen fotos. No se pueden unir en un mismo modelo. Por eso va como **módulo aparte**: "de la foto estimamos peso y medidas corporales". No hay que inventarle una conexión con el ADN, porque el jurado lo detecta.

---

## Cómo se presenta el proyecto con las dos ramas

| Rama | Data | Pregunta que responde |
|---|---|---|
| Genómica (Lucero, Ana, Ivan, Chayna) | SNPs, EBVs, simulación, genes, literatura | ¿Qué modelo predice mejor el mérito genético y por qué? |
| Visión (Joe) | Fotos + medidas corporales | ¿Se puede caracterizar físicamente al animal sin balanza? |

Las dos se muestran juntas en el dashboard, cada una con su población y su alcance declarado.

---

## Calendario

| Hito | Fecha |
|---|---|
| Lucero sube `data/sample/` (desbloquea a todos) | ____ |
| Entrega de los 5 scripts + Pull Request | ____ |
| Demo de 5 minutos por integrante | ____ |
