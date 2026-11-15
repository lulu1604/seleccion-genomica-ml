// Estado compartido entre "Mis animales" y la ficha: el rodeo que se está mostrando.
import { computed, reactive } from 'vue'
import { api, ErrorApi, type Animal, type Prioridad } from './api'

export const rodeo = reactive({
  animales: [] as Animal[],
  demo: true,
  cargando: false, // primera carga (ejemplo)
  analizando: false, // evaluando un archivo subido
  error: '', // no se pudo cargar nada
  aviso: '', // el archivo subido tuvo un problema (se mantiene lo que ya estaba)
  prioridad: 'balanceado' as Prioridad,
})

/** Animales ordenados por su puesto en la prioridad elegida (no vuelve a llamar a la API). */
export const ordenados = computed(() =>
  [...rodeo.animales].sort(
    (a, b) => a.por_prioridad[rodeo.prioridad].puesto - b.por_prioridad[rodeo.prioridad].puesto,
  ),
)

function mensaje(e: unknown): string {
  return e instanceof ErrorApi ? e.message : 'Algo salió mal. Intenta de nuevo.'
}

export async function cargarEjemplo(): Promise<void> {
  rodeo.cargando = true
  rodeo.error = ''
  try {
    const datos = await api.ejemplo()
    rodeo.animales = datos.animales
    rodeo.demo = true
  } catch (e) {
    rodeo.error = mensaje(e)
  } finally {
    rodeo.cargando = false
  }
}

export async function subirArchivo(archivo: File): Promise<void> {
  rodeo.analizando = true
  rodeo.aviso = ''
  try {
    const datos = await api.evaluar(archivo)
    rodeo.animales = datos.animales
    rodeo.demo = false
    rodeo.error = ''
  } catch (e) {
    rodeo.aviso = mensaje(e)
  } finally {
    rodeo.analizando = false
  }
}

export function buscarAnimal(id: string): Animal | undefined {
  return rodeo.animales.find((a) => a.id === id)
}
