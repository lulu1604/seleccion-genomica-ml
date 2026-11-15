<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api, ErrorApi, type EjemplosMedicion, type Medicion } from '../api'
import Estado from '../componentes/Estado.vue'
import Icono from '../componentes/Icono.vue'
import { INICIALES, kg, NOMBRE_ESTABLO } from '../textos'

type Vista = 'lateral' | 'posterior'

const fotos = reactive<Record<Vista, { archivo: File | null; vista: string }>>({
  lateral: { archivo: null, vista: '' },
  posterior: { archivo: null, vista: '' },
})
const midiendo = ref(false)
const error = ref('')
const resultado = ref<Medicion | null>(null)

const ejemplos = ref<EjemplosMedicion | null>(null)
const cargandoEjemplos = ref(false)
const errorEjemplos = ref('')
const verTodas = ref(false)

const listo = computed(() => fotos.lateral.archivo && fotos.posterior.archivo && !midiendo.value)

function elegir(vista: Vista, evento: Event) {
  const archivo = (evento.target as HTMLInputElement).files?.[0]
  if (!archivo) return
  if (fotos[vista].vista) URL.revokeObjectURL(fotos[vista].vista)
  fotos[vista] = { archivo, vista: URL.createObjectURL(archivo) }
  error.value = ''
}

async function calcular() {
  if (!fotos.lateral.archivo || !fotos.posterior.archivo) return
  midiendo.value = true
  error.value = ''
  try {
    resultado.value = await api.medir(fotos.lateral.archivo, fotos.posterior.archivo)
  } catch (e) {
    error.value = e instanceof ErrorApi ? e.message : 'Algo salió mal. Intenta de nuevo.'
  } finally {
    midiendo.value = false
  }
}

async function cargarEjemplos() {
  cargandoEjemplos.value = true
  errorEjemplos.value = ''
  try {
    ejemplos.value = await api.ejemplosMedicion()
  } catch (e) {
    errorEjemplos.value = e instanceof ErrorApi ? e.message : 'Algo salió mal. Intenta de nuevo.'
  } finally {
    cargandoEjemplos.value = false
  }
}

onMounted(cargarEjemplos)
onUnmounted(() => {
  for (const f of Object.values(fotos)) if (f.vista) URL.revokeObjectURL(f.vista)
})

const veredicto = (dentro: boolean) => (dentro ? 'dentro del margen' : 'fuera del margen')
</script>

<template>
  <div class="barra-superior">
    <h1>¿Cuánto mide y pesa tu vaca?</h1>
    <span class="avatar" :aria-label="`Cuenta: ${NOMBRE_ESTABLO}`">{{ INICIALES }}</span>
  </div>

  <div class="panel">
    <div class="rejilla-2">
      <section class="tarjeta" aria-labelledby="t-fotos">
        <h2 id="t-fotos"><span class="solo-escritorio">Sube dos fotos</span><span class="solo-movil">Toma dos fotos</span></h2>
        <div class="cajas">
          <label class="caja" :class="{ elegida: fotos.lateral.vista }">
            <img v-if="fotos.lateral.vista" :src="fotos.lateral.vista" alt="Foto de costado elegida" />
            <svg v-else class="solo-escritorio" aria-hidden="true" width="64" height="38" viewBox="0 0 64 38" fill="#8C8378">
              <rect x="12" y="8" width="38" height="16" rx="7" /><rect x="44" y="3" width="14" height="10" rx="4" />
              <rect x="15" y="22" width="4" height="12" /><rect x="22" y="22" width="4" height="12" />
              <rect x="38" y="22" width="4" height="12" /><rect x="44" y="22" width="4" height="12" />
            </svg>
            <Icono v-if="!fotos.lateral.vista" nombre="camara" :tamano="28" class="solo-movil" />
            <strong>De costado</strong>
            <span class="sub solo-escritorio">{{ fotos.lateral.vista ? 'toca para cambiarla' : 'la vaca entera' }}</span>
            <input type="file" accept="image/*" capture="environment" @change="elegir('lateral', $event)" />
          </label>
          <label class="caja" :class="{ elegida: fotos.posterior.vista }">
            <img v-if="fotos.posterior.vista" :src="fotos.posterior.vista" alt="Foto desde atrás elegida" />
            <svg v-else class="solo-escritorio" aria-hidden="true" width="40" height="38" viewBox="0 0 40 38" fill="#8C8378">
              <rect x="9" y="2" width="22" height="22" rx="8" /><rect x="11" y="22" width="5" height="13" />
              <rect x="24" y="22" width="5" height="13" />
            </svg>
            <Icono v-if="!fotos.posterior.vista" nombre="camara" :tamano="28" class="solo-movil" />
            <strong>Desde atrás</strong>
            <span class="sub solo-escritorio">{{ fotos.posterior.vista ? 'toca para cambiarla' : 'centrada' }}</span>
            <input type="file" accept="image/*" capture="environment" @change="elegir('posterior', $event)" />
          </label>
        </div>
        <ul class="consejos solo-escritorio">
          <li>✓ Animal completo, sin cortar patas ni cabeza</li>
          <li>✓ Buena luz</li>
          <li>✗ En diagonal o de frente</li>
        </ul>
        <span class="consejos solo-movil">Animal completo, buena luz, de costado (no en diagonal).</span>
        <button type="button" class="boton boton-oscuro calcular" :disabled="!listo" @click="calcular">Calcular</button>
        <div v-if="midiendo" class="aviso" role="status">
          <span class="girando" aria-hidden="true"></span>Midiendo… la primera vez puede tardar hasta 1 minuto
        </div>
        <div v-if="error" class="aviso aviso-error" role="alert"><Icono nombre="alerta" />{{ error }}</div>
      </section>

      <section class="tarjeta tarjeta-oscura resultado" aria-labelledby="t-res" aria-live="polite">
        <template v-if="resultado">
          <h2 id="t-res" class="rotulo">Peso estimado</h2>
          <span class="serif peso">{{ kg(resultado.peso.valor) }}</span>
          <span>Puede estar entre <strong>{{ Math.round(resultado.peso.min) }} y {{ kg(resultado.peso.max) }}</strong></span>
          <div class="medidas">
            <div v-for="m in resultado.medidas" :key="m.clave" class="medida">
              <span class="claro">{{ m.nombre }}</span>
              <strong>{{ Math.round(m.valor) }} {{ m.unidad }}</strong>
              <span class="error">± {{ Math.round(m.error) }} {{ m.unidad }}</span>
            </div>
          </div>
          <span class="claro solo-movil">Es una estimación: para vender o dosificar, usa la balanza.</span>
        </template>
        <template v-else>
          <h2 id="t-res" class="rotulo">Tu resultado</h2>
          <span class="serif vacio">Aquí verás cuánto pesa y mide tu vaca.</span>
          <span class="claro">Sube las dos fotos y toca Calcular.</span>
        </template>
      </section>
    </div>

    <section class="tarjeta" aria-labelledby="t-estudio">
      <div class="titulo-ejemplos">
        <h2 id="t-estudio">Así le fue con vacas que ya pesamos</h2>
        <span class="sub">Estimado sin haber visto su peso</span>
      </div>
      <Estado :cargando="cargandoEjemplos" :error="errorEjemplos" @reintentar="cargarEjemplos" />
      <template v-if="ejemplos">
        <div class="rejilla-3">
          <div v-for="e in ejemplos.ejemplos" :key="e.id" class="vaca">
            <img :src="e.foto_lateral" :alt="`Foto de costado de la vaca ${e.id}`" loading="lazy" />
            <div class="vaca-titulo">
              <strong>Vaca {{ e.id }}</strong>
              <span class="chip" :class="e.dentro ? 'cat-bueno' : 'fuera'">{{ veredicto(e.dentro) }}</span>
            </div>
            <div class="pesos">
              <span>Real<br /><strong>{{ kg(e.real_kg) }}</strong></span>
              <span>Estimado<br /><strong>{{ kg(e.estimado_kg) }}</strong></span>
            </div>
          </div>
        </div>
        <button type="button" class="boton boton-borde ver-todas" :aria-expanded="verTodas" @click="verTodas = !verTodas">
          {{ verTodas ? 'Ocultar la lista' : `Ver las ${ejemplos.todas.length} vacas` }}
        </button>
        <div v-if="verTodas" class="desliza">
          <table>
            <thead>
              <tr><th scope="col">Vaca</th><th scope="col">Peso real</th><th scope="col">Estimado</th>
                <th scope="col">Diferencia</th><th scope="col"></th></tr>
            </thead>
            <tbody>
              <tr v-for="v in ejemplos.todas" :key="v.id">
                <td>{{ v.id }}</td>
                <td>{{ kg(v.real_kg) }}</td>
                <td>{{ kg(v.estimado_kg) }}</td>
                <td>{{ kg(Math.abs(v.estimado_kg - v.real_kg)) }}</td>
                <td><span class="chip" :class="v.dentro ? 'cat-bueno' : 'fuera'">{{ veredicto(v.dentro) }}</span></td>
              </tr>
            </tbody>
          </table>
          <span class="sub">Margen: ± {{ kg(ejemplos.error_kg) }}.</span>
        </div>
      </template>
    </section>

    <section class="tarjeta antes" aria-labelledby="t-saber">
      <h2 id="t-saber">Antes de usarlo</h2>
      <span>Lo probamos con fotos de {{ ejemplos?.todas.length ?? 72 }} vacas. Acierta mejor la altura que el peso.
        Con otras razas o fotos tomadas a otra distancia, el error puede ser mayor. Para más precisión,
        toma siempre las fotos a la misma distancia.</span>
    </section>
  </div>
</template>

<style scoped>
.cajas { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.caja {
  position: relative; min-height: 130px; border: 2px dashed var(--tierra); border-radius: 16px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  text-align: center; padding: 10px; cursor: pointer; overflow: hidden;
}
.caja:hover { border-color: var(--texto-suave); }
.caja:focus-within { outline: 2px solid var(--oscuro); outline-offset: 2px; }
.caja.elegida { border-style: solid; border-color: var(--oscuro); }
.caja img { width: 100%; height: 86px; object-fit: cover; border-radius: 10px; }
.caja input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.caja strong { font-size: 13px; }
.caja .sub { font-size: 11.5px; }
.consejos { margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 12.5px; color: var(--texto-medio); }
.calcular { min-height: 46px; }

.resultado { gap: 12px; }
.rotulo { font-family: var(--sans); font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--sobre-oscuro); }
.peso { font-size: 58px; line-height: 1; }
.vacio { font-size: 26px; line-height: 1.2; }
.claro { font-size: 13px; color: var(--sobre-oscuro); }
.medidas { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 4px; }
.medida { background: var(--oscuro-2); border-radius: 12px; padding: 10px 12px; display: flex; flex-direction: column; }
.medida .claro { font-size: 11.5px; }
.medida strong { font-size: 17px; }
.medida .error { font-size: 11px; color: #BFB6A9; }

.titulo-ejemplos { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px; }
.vaca { background: var(--app); border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.vaca img { width: 100%; height: 120px; object-fit: cover; border-radius: 12px; background: var(--pastilla); }
.vaca-titulo { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.fuera { background: transparent; color: var(--texto-medio); }
.pesos { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; font-size: 12px; color: var(--texto-suave); }
.pesos strong { font-size: 18px; color: var(--texto); }
.ver-todas { align-self: flex-start; }
.desliza { overflow-x: auto; display: flex; flex-direction: column; gap: 8px; }
table { width: 100%; border-collapse: collapse; min-width: 480px; font-size: 13px; }
th { text-align: left; color: var(--texto-suave); font-size: 11.5px; font-weight: 600; padding: 6px 8px; }
td { padding: 6px 8px; border-top: 1px solid var(--linea); }

.antes { flex-direction: row; flex-wrap: wrap; gap: 8px 28px; align-items: baseline; padding: 18px 20px; }
.antes h2 { font-size: 20px; }
.antes span { flex: 1 1 420px; font-size: 13px; color: var(--texto-medio); }

@media (max-width: 768px) {
  .caja { min-height: 120px; }
  .peso { font-size: 50px; }
  .medida { padding: 8px 10px; }
  .medida strong { font-size: 16px; }
}
</style>
