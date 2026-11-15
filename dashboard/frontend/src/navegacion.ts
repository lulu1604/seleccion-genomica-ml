// Navegación con el hash de la URL (#/animales, #/ficha/<id>, #/medir, #/confiar),
// así el botón Atrás del celular funciona sin router.
import { ref } from 'vue'

export type Pantalla = 'animales' | 'ficha' | 'medir' | 'confiar'

export interface Ruta {
  pantalla: Pantalla
  id?: string
}

function leerHash(): Ruta {
  const [, pantalla, id] = location.hash.replace(/^#/, '').split('/')
  if (pantalla === 'ficha' && id) return { pantalla, id: decodeURIComponent(id) }
  if (pantalla === 'medir' || pantalla === 'confiar') return { pantalla }
  return { pantalla: 'animales' }
}

export const ruta = ref<Ruta>(leerHash())

window.addEventListener('hashchange', () => {
  ruta.value = leerHash()
  window.scrollTo(0, 0)
})

export function enlaceFicha(id: string): string {
  return `#/ficha/${encodeURIComponent(id)}`
}
