# Fuente de datos: poblaciones simuladas con AlphaSimR

Proyecto: **Selección Genómica de Precisión en Ganado Vacuno** · Machine Learning ESAN 2026-2
Script: `src/data/simular.R` · Responsable: Ana

---

## Para qué sirve esta fuente

El dataset real (Holstein alemán) tiene un solo tamaño de población y una sola heredabilidad: lo que viene, viene. La simulación permite **fabricar poblaciones a medida** y así responder la pregunta central del proyecto:

> ¿A partir de cuántos animales de referencia los modelos de Machine Learning superan a GBLUP?

Además entrega algo que ningún dato real puede dar: el **valor genético verdadero** de cada animal (`valor_gv`). En la vida real ese valor nunca se observa, solo se estima. Aquí se conoce, y sirve como vara exacta para medir qué tan bien predice cada modelo.

Los tamaños 125, 500 y 2 000 son los mismos que usa Zhang et al. (2015), para que los resultados sean comparables con los publicados en la Tabla S1 de ese paper.

---

## Herramienta

| | |
|---|---|
| Paquete | AlphaSimR 2.1.0 (CRAN) |
| Lenguaje | R 4.6.1 |
| Instalación | `install.packages("AlphaSimR")` |
| Simulador interno | MaCS, con los parámetros demográficos del ganado bovino (`species = "CATTLE"`) |

AlphaSimR no genera números al azar: simula la **historia evolutiva** de la especie, con cromosomas, recombinación y parentesco entre los animales. Eso es lo que hace que la matriz G de GBLUP tenga sentido; una simulación con números aleatorios sueltos dejaría a GBLUP sin nada que aprovechar.

---

## Parámetros usados

| Parámetro | Valor | Por qué |
|---|---|---|
| `ESCENARIOS` | 125, 500, 2000 | Mismos tamaños que el paper de referencia |
| `N_SNPS` | 10 000 | Suficiente para comparar modelos sin que la corrida sea eterna |
| `N_QTL` | 1 000 | Genes que realmente afectan al rasgo (arquitectura poligénica) |
| `H2` | 0.30 | Heredabilidad típica de producción de leche |
| `N_CROM` | 29 | Cromosomas autosómicos del ganado bovino |
| `SEMILLA` | 22200285 | Fija, para que la corrida sea reproducible |

---

## Resultados de la corrida

| Escenario | Animales | SNPs | h² pedida | h² realizada | Tiempo | Peso de `X_sim.csv` |
|---|---|---|---|---|---|---|
| `sim_n125` | 125 | 10 005 | 0.30 | **0.283** | 2.5 min | 2.6 MB |
| `sim_n500` | 500 | 10 005 | 0.30 | **0.289** | 18.3 min | 9.7 MB |
| `sim_n2000` | 2 000 | 10 005 | 0.30 | **0.304** | 65.1 min | 39 MB |

Tiempo total de la corrida: aproximadamente 1 hora y 26 minutos.

### Dos observaciones sobre estos números

**1. La h² se acerca a 0.30 conforme crece la población.**

```
n = 125   →  0.283      más lejos del valor real
n = 500   →  0.289
n = 2000  →  0.304      prácticamente clavado
```

Con pocos animales, el azar del muestreo pesa más y el valor observado se aleja del parámetro que se pidió. Es el mismo fenómeno que el proyecto estudia en la precisión de los modelos, visible ya en los datos de entrada.

**2. Los SNPs son 10 005 y no 10 000.**

El script reparte los marcadores entre 29 cromosomas: 10 000 ÷ 29 = 344.8, que redondea a 345 por cromosoma, y 345 × 29 = 10 005. Los cinco de más no afectan ningún resultado.

---

## Archivos que genera

No se suben al repositorio: `data/processed/` está en el `.gitignore`. Se reproducen corriendo el script.

```
data/processed/sim_n125/
├── X_sim.csv    125 filas × 10 006 columnas
└── y_sim.csv    125 filas × 3 columnas

data/processed/sim_n500/    idem con 500 animales
data/processed/sim_n2000/   idem con 2 000 animales
```

### Formato de `X_sim.csv`

```
id_animal,snp_00001,snp_00002,...,snp_10005
SIM125_00001,0,2,1,...,1
SIM125_00002,1,2,0,...,2
```

### Formato de `y_sim.csv`

```
id_animal,fenotipo,valor_gv
SIM125_00001,0.728869148267883,-0.0627710466335955
SIM125_00002,0.908649869079447,-0.201382794391394
```

| Columna | Qué es |
|---|---|
| `id_animal` | Identificador con prefijo `SIM<n>_`, para no confundirlo con los animales reales |
| `fenotipo` | Lo observado: genética + ambiente. Es lo que un modelo vería en la vida real |
| `valor_gv` | El valor genético **verdadero**. Solo existe en simulación, sirve como referencia de evaluación |

---

## Cómo reproducirlo

```bash
Rscript src/data/simular.R
```

Con la semilla fija, el resultado es idéntico corrida tras corrida.

Para probar rápido antes de lanzar todo, editar la primera línea de parámetros:

```r
ESCENARIOS <- c(125)
```

---

## Limitaciones

- El rasgo simulado es **puramente aditivo** (`addTraitA`). No hay dominancia ni epistasis. Si más adelante se quiere probar que el ML captura interacciones entre genes, habría que simular un rasgo con epistasis.
- Son animales sin estructura de rebaño ni efectos ambientales de manejo: solo genética más ruido.
- El escenario de 2 000 animales demora más de una hora en una laptop. Conviene correrlo una sola vez y conservar los archivos.
