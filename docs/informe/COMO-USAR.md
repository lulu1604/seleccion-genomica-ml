# Informe — cómo trabajarlo

**Un solo archivo: `informe.tex`.** Se copia entero y se pega en Overleaf.
No necesita ningún archivo externo: el diagrama de etapas está dibujado con
TikZ dentro del propio `.tex` y la bibliografía está escrita adentro.

Compilado y verificado: **8 páginas, sin errores, sin referencias rotas,
sin tablas que se salgan del margen.**

---

## Overleaf

1. **New Project → Blank Project**
2. Borrar todo lo que trae `main.tex` por defecto
3. Pegar el contenido completo de `informe.tex`
4. Menu → **Compiler: pdfLaTeX**
5. Recompile

No hay que subir imágenes ni el `.bib`. Todo está adentro.

## VS Code

Extensión **LaTeX Workshop** + MiKTeX (Windows) o TeX Live. Abrir
`docs/informe/informe.tex` y guardar: compila solo. Desde terminal:

```bash
cd docs/informe
latexmk -pdf informe.tex
```

---

## Qué secciones tiene y por qué

El profesor pidió exactamente esto, y el informe tiene exactamente esto:

| Sección | Qué pidió |
|---|---|
| I · Introducción | Introducción |
| II · Estado del Arte | Mínimo 4 antecedentes, cada uno con título/autores/año, problema, BD, técnicas, metodología y resultados. **Aquí hay 5** |
| III · Metodología propuesta | Gráfico de etapas + descripción de cada etapa. **El gráfico son las 8 cajas E1–E8** |
| IV · Experimentos | Mostrar la BD que se va a emplear |
| Referencias | 8 entradas con DOI |

> El informe anterior del curso se usó **solo como referencia de formato**.
> Tenía secciones que aquí no van (justificación, objetivos, limitaciones,
> conclusiones) porque ese era un informe final y este es el primer avance.

---

## Reparto para editar

Como es un solo archivo, **no se edita en paralelo**: dos personas
guardando a la vez se pisan. Dos formas de trabajar:

**Opción A — Overleaf compartido (recomendada).** Overleaf sincroniza en
vivo, como Google Docs. Ana crea el proyecto y comparte el enlace de
edición con los cinco. Ahí sí se puede trabajar a la vez.

**Opción B — Por turnos.** Uno edita, guarda, avisa, y recién entonces
entra el siguiente.

| Sección | Responsable |
|---|---|
| Resumen, Introducción | Ana |
| Estado del Arte + Referencias | Chayna |
| Metodología (etapas E1–E8) | Ana coordina; cada uno revisa su etapa |
| Experimentos | Lucero (Holstein) + Ana (simulación) |

---

## Cómo encontrar lo que falta

Busca con **Ctrl+F**: `>>> PENDIENTE`

Hay tres, y cada uno dice de quién es:

| Quién | Qué falta |
|---|---|
| Ivan | Su código de alumno, en el bloque de autores |
| Chayna | El tamaño exacto del conjunto de VanRaden (2008) |
| Ana | El enlace de Drive al dataset, en la sección de Experimentos |

En el PDF sale en **rojo entre corchetes**, así que en la reunión se ve solo.

---

## El diagrama de etapas

Está dibujado con TikZ, en el bloque que empieza con
`\begin{tikzpicture}`. Si hay que mover una caja, se cambia su coordenada
`(x, y)` y las flechas la siguen solas. El `\resizebox` de afuera ajusta
todo al ancho de la página, así que no hay que recalcular nada si se agrega
una etapa.

Cada caja lleva debajo, en cursiva, el **artefacto** que esa etapa entrega.
Eso es lo que hace que el gráfico no sea decorativo: se puede señalar
cualquier caja y preguntar "¿ya existe ese archivo?".

---

## Cosas que rompen el PDF

| Error | Por qué | Cómo se arregla |
|---|---|---|
| `Undefined control sequence` | Un `\` de más o un comando mal escrito | Mira el número de línea del error |
| `Missing $ inserted` | Usaste `_`, `^`, `%`, `&` o `#` en texto normal | Escápalos: `\_`, `\%`, `\&`, `\#` |
| `Citation undefined` | Citaste una clave que no está en `thebibliography` | Revisa que la clave coincida exacto |
| Referencias en `[?]` | Compilaste una sola vez | Compila 2 veces, o usa `latexmk` |
| Tabla que se sale del margen | Las columnas suman más que el ancho | Baja los `p{Xcm}` o pasa a `table*` |

---

## Convenciones

- Decimales con **coma**: `0{,}85`, no `0.85`. Las llaves evitan un espacio raro
- Miles con espacio fino: `5\,024`
- Nombres de archivos, funciones y paquetes en `\texttt{}`
- Términos en otro idioma en `\textit{}`
- **Toda cifra viene de una corrida real o de una fuente citada.** Si no la
  puedes rastrear, no va
