// Textos y reglas de presentación (lenguaje del ganadero, sin términos técnicos).
import type { Categoria, Prioridad, Rasgo } from './api'

export const NOMBRE_ESTABLO = 'Establo Santa Rosa'

/** "Establo Santa Rosa" -> "SR". */
export const INICIALES = NOMBRE_ESTABLO.split(' ').slice(-2).map((p) => p[0]).join('')

export const FECHA_HOY = new Date().toLocaleDateString('es', {
  day: 'numeric', month: 'short', year: 'numeric',
}).replace('.', '')

export const PRIORIDADES: { valor: Prioridad; nombre: string; texto: string }[] = [
  { valor: 'balanceado', nombre: 'Balanceado', texto: 'Ordenados para que grasa, leche y salud de la ubre pesen lo mismo.' },
  { valor: 'grasa', nombre: 'Más grasa', texto: 'Primero los que dan leche con más grasa: mejor precio para queso y mantequilla.' },
  { valor: 'leche', nombre: 'Más leche', texto: 'Primero los que dan más litros.' },
  { valor: 'ubre', nombre: 'Ubre sana', texto: 'Primero los de ubre más sana: menos mastitis y menos gasto en veterinario.' },
]

// ---- tipo de animal ----

/** Tipo ya normalizado: el backend manda Toro, Vaca, Vaquilla o vacío ('' = sin indicar). */
export type Tipo = 'toro' | 'vaca' | 'vaquilla' | ''
/** Para los textos: un toro hereda a sus hijas; vaca y vaquilla son hembras; sin indicar, neutro. */
export type Sexo = 'toro' | 'hembra' | 'neutro'

export function tipoDe(animal: { tipo: string }): Tipo {
  const t = animal.tipo.normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase()
  return t === 'toro' || t === 'vaca' || t === 'vaquilla' ? t : ''
}

export function sexoDe(animal: { tipo: string }): Sexo {
  const t = tipoDe(animal)
  return t === 'toro' ? 'toro' : t ? 'hembra' : 'neutro'
}

export const TIPOS: Record<Exclude<Tipo, ''>, { nombre: string; letra: string }> = {
  toro: { nombre: 'Toro', letra: 'T' },
  vaca: { nombre: 'Vaca', letra: 'V' },
  vaquilla: { nombre: 'Vaquilla', letra: 'Vq' },
}

export const NOTA_TORO = 'Un toro no da leche: estos valores son lo que hereda a sus hijas.'

// ---- rasgos ----

export const RASGOS: { clave: Rasgo; nombre: string; corto: string; queMide: Record<Sexo, string> }[] = [
  {
    clave: 'grasa', nombre: 'Grasa', corto: 'Grasa',
    queMide: {
      toro: '% de grasa en la leche de sus hijas',
      hembra: '% de grasa en su leche y la de sus hijas',
      neutro: '% de grasa en la leche',
    },
  },
  {
    clave: 'leche', nombre: 'Leche', corto: 'Leche',
    queMide: {
      toro: 'litros por lactancia de sus hijas',
      hembra: 'litros por lactancia (ella y sus hijas)',
      neutro: 'litros por lactancia',
    },
  },
  {
    clave: 'ubre sana', nombre: 'Ubre sana', corto: 'Ubre',
    queMide: {
      toro: 'menos mastitis en sus hijas',
      hembra: 'menos mastitis (ella y sus hijas)',
      neutro: 'menos mastitis',
    },
  },
]

/** El rasgo dentro de una frase: en un toro, la ubre sana es la de sus hijas. */
export function rasgoEnFrase(rasgo: Rasgo, sexo: Sexo): string {
  return rasgo === 'ubre sana' && sexo === 'toro' ? 'ubre sana de sus hijas' : rasgo
}

/** Etiqueta del backend con la concordancia del tipo ("buena en las 3", "ubre sana de sus hijas"). */
export function etiquetaDe(animal: { tipo: string; etiqueta: string }): string {
  const sexo = sexoDe(animal)
  let texto = animal.etiqueta
  if (sexo === 'hembra') texto = texto.replace(/^bueno /, 'buena ')
  if (sexo === 'toro') texto = texto.replace(/ubre sana$/, rasgoEnFrase('ubre sana', sexo))
  return texto
}

// "Qué tan seguro": según qué tan bien acertó cada rasgo en la comparación
// (≥0.75 alto, ≥0.60 medio; regla de PLAN-DASHBOARD.md).
export const SEGURIDAD: Record<Rasgo, string> = { grasa: 'alto', leche: 'medio', 'ubre sana': 'medio' }

// ---- recomendación según categoría y tipo (la categoría la calcula el backend) ----

export interface Recomendacion { accion: string; texto: string }

export const RECOMENDACIONES: Record<Categoria, Record<Sexo, Recomendacion>> = {
  Élite: {
    hembra: { accion: 'Embriones', texto: 'Sácale más crías: es buena candidata para embriones.' },
    toro: { accion: 'Padre principal', texto: 'Úsalo mucho: insemina con él a tus mejores vacas.' },
    neutro: { accion: 'Embriones', texto: 'Sácale más crías: este animal es buen candidato para embriones.' },
  },
  Bueno: {
    hembra: { accion: 'Semen sexado', texto: 'Insemínala con semen sexado para tener hijas de reemplazo.' },
    toro: { accion: 'Padre de hijas', texto: 'Usa su semen sexado para tener hijas.' },
    neutro: { accion: 'Semen sexado', texto: 'Insemina a este animal con semen sexado para tener hijas de reemplazo.' },
  },
  Regular: {
    hembra: { accion: 'Semen convencional', texto: 'Insemínala con semen normal, sin gastar de más.' },
    toro: { accion: 'Uso limitado', texto: 'Úsalo poco, solo como respaldo.' },
    neutro: { accion: 'Semen convencional', texto: 'Insemina a este animal con semen normal, sin gastar de más.' },
  },
  Bajo: {
    hembra: { accion: 'Semen de carne', texto: 'Insemínala con un toro de carne: sus crías irán a carne.' },
    toro: { accion: 'No usar', texto: 'No lo uses como reproductor.' },
    neutro: { accion: 'Semen de carne', texto: 'Insemina a este animal con un toro de carne: sus crías irán a carne.' },
  },
}

export function recomendacion(categoria: Categoria, animal: { tipo: string }): Recomendacion {
  return RECOMENDACIONES[categoria][sexoDe(animal)]
}

/** Orden y clase de color de cada grupo (de mejor a peor). */
export const GRUPOS: { categoria: Categoria; clase: string }[] = [
  { categoria: 'Élite', clase: 'cat-elite' },
  { categoria: 'Bueno', clase: 'cat-bueno' },
  { categoria: 'Regular', clase: 'cat-regular' },
  { categoria: 'Bajo', clase: 'cat-bajo' },
]

export function claseCategoria(categoria: Categoria): string {
  return GRUPOS.find((g) => g.categoria === categoria)?.clase ?? 'cat-bajo'
}

/** Color del círculo en "Tu rodeo de un vistazo" según "mejor que X de cada 100". */
export function nivelPunto(p: number): string {
  return p >= 90 ? 'punto-top' : p >= 50 ? 'punto-sobre' : p >= 25 ? 'punto-bajo' : 'punto-ultimo'
}

export function cuantos(n: number, singular: string, plural: string): string {
  return `${n} ${n === 1 ? singular : plural}`
}

/** Id para mostrar: sin el prefijo "Anim" (Anim2042 → 2042). La URL y la API usan el id completo. */
export function idCorto(id: string): string {
  return id.replace(/^Anim(?=\S)/, '')
}

/** Cómo se nombra un animal en pantalla: "Lucerito · V-001" si tiene nombre, si no "Animal 2042". */
export function nombreAnimal(animal: { id: string; nombre?: string }): string {
  const nombre = animal.nombre?.trim()
  return nombre ? `${nombre} · ${idCorto(animal.id)}` : `Animal ${idCorto(animal.id)}`
}

export const AYUDA_PLANTILLA =
  'Llena la hoja Animales y pega en la hoja ADN los resultados que te mandó el laboratorio.'

export function mayuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

export function kg(valor: number): string {
  return `${Math.round(valor).toLocaleString('es')} kg`
}
