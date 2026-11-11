<script setup lang="ts">
import { computed } from 'vue'
import type { Rasgo } from '../api'
import Estado from '../componentes/Estado.vue'
import Icono from '../componentes/Icono.vue'
import { buscarAnimal, cargarEjemplo, rodeo } from '../rodeo'
import { idCorto, INICIALES, mayuscula, NOMBRE_ESTABLO, PRIORIDADES, RASGOS, RECOMENDACION, SEGURIDAD } from '../textos'

const props = defineProps<{ id: string }>()

const animal = computed(() => buscarAnimal(props.id))
const puesto = computed(() => animal.value?.por_prioridad[rodeo.prioridad])
const nombrePrioridad = computed(() => PRIORIDADES.find((p) => p.valor === rodeo.prioridad)?.nombre)

const rasgos = computed(() =>
  RASGOS.map((r) => {
    const p = animal.value?.percentiles[r.clave] ?? 0
    return { ...r, p, llenas: Math.round(p / 10), seguro: SEGURIDAD[r.clave] }
  }),
)

const mejor = computed<Rasgo>(() => {
  const p = animal.value?.percentiles
  if (!p) return 'grasa'
  return RASGOS.map((r) => r.clave).reduce((m, r) => (p[r] > p[m] ? r : m))
})

const zonas = computed(() => {
  const lista = animal.value?.zonas[mejor.value] ?? []
  const maximo = Math.max(...lista.map((z) => Math.abs(z.valor)), 1e-9)
  return lista.map((z) => ({
    ...z,
    numero: z.marcador.replace(/\D/g, ''),
    ancho: Math.max(4, Math.round((100 * Math.abs(z.valor)) / maximo)),
  }))
})

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
          <h1 id="t-animal">Animal {{ idCorto(animal.id) }}</h1>
          <span class="claro">
            {{ animal.tipo ? `${animal.tipo} · ` : '' }}Holstein · puesto {{ puesto.puesto }} de {{ rodeo.animales.length }}
            <template v-if="rodeo.prioridad !== 'balanceado'"> · prioridad {{ nombrePrioridad?.toLowerCase() }}</template>
          </span>
          <div class="chips">
            <span class="chip chip-claro">{{ puesto.categoria }}</span>
            <span class="chip chip-oscuro">{{ mayuscula(animal.etiqueta) }}</span>
          </div>
        </div>
      </div>
      <div class="recomendacion">
        <span class="rotulo">Recomendación</span>
        <span class="serif texto">{{ RECOMENDACION[puesto.accion] }}</span>
        <div class="no-imprimir">
          <button type="button" class="boton boton-lavanda" @click="descargar">
            <Icono nombre="descargar" :tamano="16" />Descargar ficha
          </button>
        </div>
      </div>
    </section>

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
        <h2 id="t-porque">¿Por qué salió tan bueno en {{ mejor }}?</h2>
        <span class="sub">Las partes de su ADN que más lo empujaron hacia arriba o hacia abajo</span>
      </div>
      <div class="zonas">
        <div v-for="(z, i) in zonas" :key="i" class="zona">
          <span class="zona-texto">
            <strong>{{ z.zona }}</strong>
            <span class="sub">{{ z.detalle }}</span>
            <span class="marcador">marcador {{ z.numero }}</span>
          </span>
          <div class="pista" aria-hidden="true">
            <div class="relleno" :class="z.efecto" :style="{ width: `${z.ancho}%` }"></div>
          </div>
          <span class="efecto" :class="z.efecto">{{ z.efecto }}</span>
        </div>
      </div>
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
.marcador { font-size: 10.5px; color: var(--tierra); }
.pista { height: 14px; border-radius: 7px; background: var(--app); overflow: hidden; }
.relleno { height: 100%; border-radius: 7px; }
.relleno.sube { background: var(--oscuro); }
.relleno.baja { background: var(--tierra); }
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
