// Textos y reglas de presentación (lenguaje del ganadero, sin términos técnicos).
import type { Accion, Categoria, Prioridad, Rasgo } from './api'

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

export const RASGOS: { clave: Rasgo; nombre: string; queMide: string; corto: string }[] = [
  { clave: 'grasa', nombre: 'Grasa', queMide: '% de grasa en la leche', corto: 'Grasa' },
  { clave: 'leche', nombre: 'Leche', queMide: 'litros por lactancia', corto: 'Leche' },
  { clave: 'ubre sana', nombre: 'Ubre sana', queMide: 'menos mastitis', corto: 'Ubre' },
]

// "Qué tan seguro": según qué tan bien acertó cada rasgo en la comparación
// (≥0.75 alto, ≥0.60 medio; regla de PLAN-DASHBOARD.md).
export const SEGURIDAD: Record<Rasgo, string> = { grasa: 'alto', leche: 'medio', 'ubre sana': 'medio' }

export const RECOMENDACION: Record<Accion, string> = {
  Embriones: 'Sácale más crías: es buen candidato para embriones.',
  'Semen sexado': 'Úsalo para tener más hembras de reemplazo.',
  'Semen convencional': 'Úsalo con semen convencional, sin gastar de más.',
  'Semen de carne': 'Mejor destina sus crías a carne.',
}

/** Orden y clase de color de cada grupo (de mejor a peor). */
export const GRUPOS: { categoria: Categoria; accion: Accion; clase: string }[] = [
  { categoria: 'Élite', accion: 'Embriones', clase: 'cat-elite' },
  { categoria: 'Bueno', accion: 'Semen sexado', clase: 'cat-bueno' },
  { categoria: 'Regular', accion: 'Semen convencional', clase: 'cat-regular' },
  { categoria: 'Bajo', accion: 'Semen de carne', clase: 'cat-bajo' },
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
