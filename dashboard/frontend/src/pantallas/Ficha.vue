<script setup lang="ts">
import { computed } from 'vue'
import type { Rasgo } from '../api'
import ChipTipo from '../componentes/ChipTipo.vue'
import Estado from '../componentes/Estado.vue'
import Icono from '../componentes/Icono.vue'
import { buscarAnimal, cargarEjemplo, rodeo } from '../rodeo'
import {
  etiquetaDe, idCorto, INICIALES, mayuscula, nombreAnimal, NOMBRE_ESTABLO, NOTA_TORO, PRIORIDADES, RASGOS,
  rasgoEnFrase, recomendacion, SEGURIDAD, sexoDe,
} from '../textos'

const props = defineProps<{ id: string }>()

const animal = computed(() => buscarAnimal(props.id))
const puesto = computed(() => animal.value?.por_prioridad[rodeo.prioridad])
const nombrePrioridad = computed(() => PRIORIDADES.find((p) => p.valor === rodeo.prioridad)?.nombre)
const sexo = computed(() => (animal.value ? sexoDe(animal.value) : 'neutro'))
const hembra = computed(() => sexo.value === 'hembra')
const consejo = computed(() => (animal.value && puesto.value ? recomendacion(puesto.value.categoria, animal.value) : null))

const rasgos = computed(() =>
  RASGOS.map((r) => {
    const p = animal.value?.percentiles[r.clave] ?? 0
    return { ...r, queMide: r.queMide[sexo.value], p, llenas: Math.round(p / 10), seguro: SEGURIDAD[r.clave] }
  }),
)

const mejor = computed<Rasgo>(() => {
  const p = animal.value?.percentiles
  if (!p) return 'grasa'
  return RASGOS.map((r) => r.clave).reduce((m, r) => (p[r] > p[m] ? r : m))
})

// barras divergentes: escala común a todas las filas del rasgo (incluido "Resto de su ADN");
// la más larga ocupa media pista (50 %), hacia la derecha si sube y hacia la izquierda si baja
const zonas = computed(() => {
  const lista = animal.value?.zonas[mejor.value] ?? []
  const maximo = Math.max(...lista.map((z) => Math.abs(z.valor)), 1e-9)
  return lista.map((z) => ({ ...z, ancho: Math.max(1, (50 * Math.abs(z.valor)) / maximo) }))
})
const totalSube = computed(() => zonas.value.reduce((suma, z) => suma + z.valor, 0) >= 0)

function descargar() {
  window.print()
}
</script>

<template>
  <div class="barra-superior">
    <a href="#/animales" class="boton boton-pastilla no-imprimir"><Icono nombre="volver" :tamano="16" />Volver a mis animales</a>
    <span class="avatar no-imprimir" :aria-label="`Cuenta: ${NOMBRE_ESTABLO}`">{{ INICIALES }}</span>
  </div>

  <Estado v-if="!rodeo.animales.length" :cargando="rodeo.cargando" :error="rodeo.error"
          texto-cargando="Buscando el animal…" @reintentar="cargarEjemplo" />

  <div v-else-if="!animal || !puesto" class="estado" role="alert">
    <strong>No encontramos el animal {{ idCorto(id) }}.</strong>
    <span class="sub">Puede que ya no esté en el archivo que estás viendo.</span>
    <a href="#/animales" class="boton boton-oscuro">Ver mis animales</a>
  </div>

  <div v-else class="panel">
    <section class="tarjeta tarjeta-oscura portada" aria-labelledby="t-animal">
      <div class="quien">
        <span class="puesto serif">{{ puesto.puesto }}</span>
        <div class="datos">
          <span class="tipo"><ChipTipo :tipo="animal.tipo" /></span>
          <h1 id="t-animal">{{ nombreAnimal(animal) }}</h1>
          <span class="claro">
            Holstein · puesto {{ puesto.puesto }} de {{ rodeo.animales.length }}
            <template v-if="rodeo.prioridad !== 'balanceado'"> · prioridad {{ nombrePrioridad?.toLowerCase() }}</template>
          </span>
          <div class="chips">
            <span class="chip chip-claro">{{ puesto.categoria }}</span>
            <span class="chip chip-oscuro">{{ mayuscula(etiquetaDe(animal)) }}</span>
          </div>
        </div>
      </div>
      <div class="recomendacion">
        <span class="rotulo">Recomendación · {{ consejo?.accion }}</span>
        <span class="serif texto">{{ consejo?.texto }}</span>
        <div class="no-imprimir">
          <button type="button" class="boton boton-lavanda" @click="descargar">
            <Icono nombre="descargar" :tamano="16" />Descargar ficha
          </button>
        </div>
      </div>
    </section>

    <div v-if="sexo === 'toro'" class="aviso" role="note">
      <Icono nombre="info" />
      <span>{{ NOTA_TORO }}</span>
    </div>

    <div class="rejilla-3">
      <section v-for="r in rasgos" :key="r.clave" class="tarjeta rasgo">
        <div class="rasgo-titulo">
          <h2>{{ r.nombre }}</h2>
          <span class="sub">{{ r.queMide }}</span>
        </div>
        <span>Mejor que <strong class="serif numero">{{ r.p }}</strong> de cada 100</span>
        <div class="barras" aria-hidden="true">
          <span v-for="i in 10" :key="i" :class="{ llena: i <= r.llenas }"></span>
        </div>
        <span class="seguro">Qué tan seguro: <strong>{{ r.seguro }}</strong></span>
      </section>
    </div>

    <section class="tarjeta" aria-labelledby="t-porque">
      <div class="encabezado">
        <h2 id="t-porque">¿Por qué salió tan {{ hembra ? 'buena' : 'bueno' }} en {{ rasgoEnFrase(mejor, sexo) }}?</h2>
        <span class="sub">Cada barra es una parte de su ADN que empujó su nota hacia arriba o hacia abajo. Todas juntas dan su resultado.</span>
      </div>
      <div class="zonas">
        <div v-for="(z, i) in zonas" :key="i" class="zona" :class="{ resto: z.resto }">
          <span class="zona-texto">
            <span class="zona-nombre">
              <strong>{{ z.zona }}</strong>
              <span v-if="z.gen" class="chip chip-gen">{{ z.gen }}</span>
            </span>
            <span class="sub">{{ z.detalle }}</span>
          </span>
          <div class="pista" aria-hidden="true">
            <div class="relleno" :class="z.efecto" :style="{ width: `${z.ancho}%` }"></div>
          </div>
          <span class="efecto" :class="z.efecto">{{ z.efecto }}</span>
        </div>
      </div>
      <p class="total">Total: <strong>{{ totalSube ? 'sube' : 'baja' }} su nota</strong></p>
    </section>
  </div>
</template>

<style scoped>
.portada { flex-direction: row; flex-wrap: wrap; gap: 18px 32px; align-items: center; justify-content: space-between; padding: 22px; }
.quien { display: flex; align-items: center; gap: 16px; }
.puesto {
  flex: none; width: 64px; height: 64px; border-radius: 50%; background: var(--tarjeta); color: var(--oscuro);
  display: flex; align-items: center; justify-content: center; font-size: 28px;
}
.datos { display: flex; flex-direction: column; gap: 4px; }
.tipo:empty { display: none; }
.tipo { margin-bottom: 2px; }
.datos h1 { font-size: 32px; line-height: 1.1; }
.claro { font-size: 13px; color: var(--sobre-oscuro); }
.datos .chips { margin-top: 4px; }
.chip-claro { background: var(--tarjeta); color: var(--oscuro); }
.chip-oscuro { background: var(--chip-oscuro); color: var(--tarjeta); }
.recomendacion { flex: 0 1 380px; display: flex; flex-direction: column; gap: 10px; }
.rotulo { font-size: 12px; color: var(--sobre-oscuro); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; }
.recomendacion .texto { font-size: 22px; line-height: 1.2; }

.rasgo { padding: 18px; gap: 12px; }
.rasgo-titulo { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.numero { font-size: 34px; }
.barras { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 4px; }
.barras span { height: 12px; border-radius: 6px; background: var(--linea); }
.barras span.llena { background: var(--oscuro); }
.seguro { font-size: 12.5px; color: var(--texto-medio); padding-top: 8px; border-top: 1px solid var(--linea); }

.zonas { display: flex; flex-direction: column; gap: 12px; }
.zona { display: grid; grid-template-columns: minmax(0, 1fr) minmax(80px, 240px) 56px; gap: 12px; align-items: center; }
.zona-texto { display: flex; flex-direction: column; min-width: 0; }
.zona-texto .sub { font-size: 12px; }
.zona-nombre { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; }
.chip-gen { font-size: 10.5px; padding: 2px 8px; background: var(--lavanda-suave); color: var(--oscuro); }
.zona.resto { padding-top: 12px; border-top: 1px dashed var(--tierra); }

/* barra divergente: línea central; sube hacia la derecha (oscuro), baja hacia la izquierda (tierra) */
.pista { position: relative; height: 14px; border-radius: 7px; background: var(--app); }
.pista::before {
  content: ''; position: absolute; left: 50%; top: -3px; bottom: -3px; width: 2px;
  margin-left: -1px; background: var(--borde-oscuro); border-radius: 1px;
}
.relleno { position: absolute; top: 0; bottom: 0; }
.relleno.sube { left: 50%; background: var(--oscuro); border-radius: 0 7px 7px 0; }
.relleno.baja { right: 50%; background: var(--tierra); border-radius: 7px 0 0 7px; }
.total { margin: 4px 0 0; padding-top: 10px; border-top: 1px solid var(--linea); font-size: 13.5px; }
.efecto { font-weight: 700; text-align: right; }
.efecto.baja { color: var(--texto-suave); }

@media (max-width: 768px) {
  .datos h1 { font-size: 26px; }
  .zona { grid-template-columns: minmax(0, 1fr) 44px; }
  .pista { grid-column: 1 / -1; grid-row: 2; }
}
@media print {
  .portada { background: #fff; color: var(--texto); border: 1px solid var(--linea); }
  .claro, .rotulo { color: var(--texto-suave); }
}
</style>
