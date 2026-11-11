// Tipos y llamadas al backend. Ver dashboard/CONTRATO_API.md.

export type Prioridad = 'balanceado' | 'grasa' | 'leche' | 'ubre'
export type Rasgo = 'grasa' | 'leche' | 'ubre sana'
export type Categoria = 'Élite' | 'Bueno' | 'Regular' | 'Bajo'
export type Accion = 'Embriones' | 'Semen sexado' | 'Semen convencional' | 'Semen de carne'

export interface Puesto {
  puntaje: number
  categoria: Categoria
  accion: Accion
  puesto: number
}

export interface Zona {
  marcador: string
  zona: string
  detalle: string
  efecto: 'sube' | 'baja'
  valor: number
}

export interface Animal {
  id: string
  tipo: string
  percentiles: Record<Rasgo, number>
  etiqueta: string
  por_prioridad: Record<Prioridad, Puesto>
  zonas: Record<Rasgo, Zona[]>
}

export interface Evaluacion {
  demo: boolean
  total: number
  animales: Animal[]
}

export interface Medida {
  clave: string
  nombre: string
  valor: number
  error: number
  unidad: string
}

export interface Medicion {
  peso: Medida & { min: number; max: number }
  medidas: Medida[]
}

export interface VacaPesada {
  id: number
  real_kg: number
  estimado_kg: number
  dentro: boolean
}

export interface EjemplosMedicion {
  ejemplos: (VacaPesada & { foto_lateral: string })[]
  todas: VacaPesada[]
  error_kg: number
}

export interface Confianza {
  animales_referencia: number
  aciertos: { rasgo: string; de_cada_10: number }[]
  tamanos: { nombre: string; nivel: 'Baja' | 'Media' | 'Alta'; ancho: number }[]
  error_peso_kg: number
  error_altura_cm: number
}

/** Error con un mensaje listo para mostrar al usuario. */
export class ErrorApi extends Error {}

const SIN_CONEXION = 'No pudimos conectar con el servidor. Revisa que esté encendido e intenta de nuevo.'

async function pedir<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(ruta, opciones)
  } catch {
    throw new ErrorApi(SIN_CONEXION)
  }
  if (resp.ok) return (await resp.json()) as T
  const cuerpo = await resp.json().catch(() => null)
  if (typeof cuerpo?.detail === 'string') throw new ErrorApi(cuerpo.detail)
  if (resp.status >= 500) throw new ErrorApi(SIN_CONEXION)
  throw new ErrorApi('Algo salió mal. Intenta de nuevo.')
}

function formulario(campos: Record<string, File>): FormData {
  const datos = new FormData()
  for (const [nombre, archivo] of Object.entries(campos)) datos.append(nombre, archivo)
  return datos
}

export const RUTA_ARCHIVO_EJEMPLO = '/api/ejemplo/archivo'

export const api = {
  ejemplo: () => pedir<Evaluacion>('/api/ejemplo'),
  evaluar: (archivo: File) =>
    pedir<Evaluacion>('/api/evaluar', { method: 'POST', body: formulario({ archivo }) }),
  medir: (lateral: File, posterior: File) =>
    pedir<Medicion>('/api/medir', { method: 'POST', body: formulario({ lateral, posterior }) }),
  ejemplosMedicion: () => pedir<EjemplosMedicion>('/api/medir/ejemplos'),
  confianza: () => pedir<Confianza>('/api/confianza'),
}
