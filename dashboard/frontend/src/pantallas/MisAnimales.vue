<script setup lang="ts">
import { computed, ref } from 'vue'
import { RUTA_ARCHIVO_EJEMPLO, type Animal } from '../api'
import Estado from '../componentes/Estado.vue'
import Icono from '../componentes/Icono.vue'
import SubirArchivo from '../componentes/SubirArchivo.vue'
import { enlaceFicha } from '../navegacion'
import { cargarEjemplo, ordenados, rodeo } from '../rodeo'
import {
  claseCategoria, cuantos, FECHA_HOY, GRUPOS, idCorto, INICIALES, nivelPunto, NOMBRE_ESTABLO, PRIORIDADES, RASGOS,
} from '../textos'

const MAX_VISTAZO = 12 // columnas de "Tu rodeo de un vistazo"
const MAX_CHIPS = 24 // animales por grupo en "Qué hacer con cada animal"
const EN_MOVIL = 5 // tarjetas visibles en el celular antes de "Ver todos"

const vista = ref<'resumen' | 'ranking'>('resumen')
const verTodosMovil = ref(false)

const textoPrioridad = computed(() => PRIORIDADES.find((p) => p.valor === rodeo.prioridad)?.texto)
const puesto = (a: Animal) => a.por_prioridad[rodeo.prioridad]
const subtitulo = (a: Animal) => (a.tipo ? `${a.tipo} · ${a.etiqueta}` : a.etiqueta)

const top = computed(() => ordenados.value.slice(0, 3))
const vistazo = computed(() => ordenados.value.slice(0, MAX_VISTAZO))
// las etiquetas de las columnas van en horizontal si caben (hasta 4 caracteres)
const etiquetasHorizontales = computed(() => vistazo.value.every((a) => idCorto(a.id).length <= 4))
const enMovil = computed(() => (verTodosMovil.value ? ordenados.value : ordenados.value.slice(0, EN_MOVIL)))

const grupos = computed(() =>
  GRUPOS.map((g) => {
    const animales = ordenados.value.filter((a) => puesto(a).categoria === g.categoria)
    return { ...g, animales: animales.slice(0, MAX_CHIPS), resto: Math.max(0, animales.length - MAX_CHIPS), total: animales.length }
  }),
)

const textoAviso = computed(() =>
  rodeo.demo
    ? `Mostrando ${rodeo.animales.length} animales de ejemplo. Sube tu archivo para ver los tuyos.`
    : `Mostrando ${cuantos(rodeo.animales.length, 'animal', 'animales')} de tu archivo.`,
)
</script>

<template>
  <header class="saludo-movil solo-movil">
    <div>
      <p>Hola,<br />{{ NOMBRE_ESTABLO }}</p>
      <span class="sub">Actualizado: {{ FECHA_HOY }}</span>
    </div>
    <span class="avatar" :aria-label="`Cuenta: ${NOMBRE_ESTABLO}`">{{ INICIALES }}</span>
  </header>

  <div class="barra-superior solo-escritorio">
    <div class="pestanas" role="group" aria-label="Vista">
      <button type="button" :aria-pressed="vista === 'resumen'" @click="vista = 'resumen'">Resumen</button>
      <button type="button" :aria-pressed="vista === 'ranking'" @click="vista = 'ranking'">Ranking completo</button>
    </div>
    <span class="avatar" :aria-label="`Cuenta: ${NOMBRE_ESTABLO}`">{{ INICIALES }}</span>
  </div>

  <Estado v-if="!rodeo.animales.length" :cargando="rodeo.cargando" :error="rodeo.error"
          texto-cargando="Buscando tus animales…" @reintentar="cargarEjemplo" />

  <div v-else class="panel">
    <div v-if="rodeo.analizando" class="aviso" role="status">
      <span class="girando" aria-hidden="true"></span>Analizando el ADN de tus animales…
    </div>
    <div v-if="rodeo.aviso" class="aviso aviso-error" role="alert">
      <Icono nombre="alerta" />
      <span>{{ rodeo.aviso }}</span>
      <a :href="RUTA_ARCHIVO_EJEMPLO" download>Ver el formato del archivo de ejemplo</a>
    </div>
    <div class="aviso" role="status">
      <Icono nombre="info" />
      <span>{{ textoAviso }}</span>
      <a :href="RUTA_ARCHIVO_EJEMPLO" download>Descargar archivo de ejemplo</a>
    </div>

    <section class="tarjeta mejores" aria-labelledby="t-mejores">
      <div class="cabecera">
        <h1 id="t-mejores">Tus mejores animales</h1>
        <div class="controles">
          <label class="prioridad">Prioridad
            <select v-model="rodeo.prioridad">
              <option v-for="p in PRIORIDADES" :key="p.valor" :value="p.valor">{{ p.nombre }}</option>
            </select>
          </label>
          <SubirArchivo class="boton-lavanda solo-escritorio" />
        </div>
        <SubirArchivo class="boton-lavanda solo-movil subir-movil" texto="Subir" />
      </div>
      <span class="sub">{{ textoPrioridad }}</span>

      <div class="rejilla-3 solo-escritorio">
        <a v-for="(a, i) in top" :key="a.id" :href="enlaceFicha(a.id)" class="animal" :class="{ oscuro: i === 0 }">
          <span class="fila-arriba">
            <span class="puesto">{{ puesto(a).puesto }}</span>
            <span class="ir"><Icono nombre="flecha" :tamano="16" /></span>
          </span>
          <span class="nombre">
            <strong>Animal {{ idCorto(a.id) }}</strong>
            <span class="detalle">{{ subtitulo(a) }}</span>
          </span>
          <span class="chips">
            <span class="chip chip-tarjeta">{{ puesto(a).categoria }}</span>
            <span class="chip chip-tarjeta">{{ puesto(a).accion }}</span>
          </span>
        </a>
      </div>

      <div class="lista-movil solo-movil">
        <a v-for="(a, i) in enMovil" :key="a.id" :href="enlaceFicha(a.id)" class="animal" :class="{ oscuro: i === 0 }">
          <span class="fila-arriba">
            <span class="puesto">{{ puesto(a).puesto }}</span>
            <span class="nombre">
              <strong>Animal {{ idCorto(a.id) }}</strong>
              <span class="detalle">{{ subtitulo(a) }}</span>
            </span>
            <Icono nombre="flecha" />
          </span>
          <span class="chips">
            <span class="chip chip-tarjeta">{{ puesto(a).categoria }}</span>
            <span class="chip chip-tarjeta">{{ puesto(a).accion }}</span>
          </span>
        </a>
        <button v-if="ordenados.length > EN_MOVIL" type="button" class="boton boton-borde"
                @click="verTodosMovil = !verTodosMovil">
          {{ verTodosMovil ? 'Ver menos' : `Ver los ${ordenados.length} animales` }}
        </button>
      </div>
    </section>

    <div v-if="vista === 'resumen'" class="rejilla-2 solo-escritorio">
      <section class="tarjeta" aria-labelledby="t-rodeo">
        <div class="encabezado">
          <h2 id="t-rodeo">Tu rodeo de un vistazo</h2>
          <span class="sub">Cada círculo: qué tan bueno es ese animal en ese rasgo</span>
        </div>
        <div class="vistazo-arriba">
          <span class="total serif">{{ rodeo.animales.length }}<span> animales</span></span>
          <div class="leyenda">
            <span><i class="punto punto-top"></i>Top 10 %</span>
            <span><i class="punto punto-sobre"></i>Sobre el promedio</span>
            <span><i class="punto punto-bajo"></i>Bajo el promedio</span>
            <span><i class="punto punto-ultimo"></i>Último 25 %</span>
          </div>
        </div>
        <div class="desliza">
          <div class="matriz" :style="{ gridTemplateColumns: `68px repeat(${vistazo.length}, minmax(24px, 1fr))` }">
            <template v-for="r in RASGOS" :key="r.clave">
              <span class="rasgo">{{ r.nombre }}</span>
              <span v-for="a in vistazo" :key="a.id" class="punto" :class="nivelPunto(a.percentiles[r.clave])"
                    :title="`Animal ${idCorto(a.id)}: mejor que ${a.percentiles[r.clave]} de cada 100 en ${r.nombre.toLowerCase()}`"></span>
            </template>
            <span></span>
            <a v-for="a in vistazo" :key="a.id" :href="enlaceFicha(a.id)" class="columna" :class="{ horizontal: etiquetasHorizontales }">{{ idCorto(a.id) }}</a>
          </div>
        </div>
        <span v-if="rodeo.animales.length > MAX_VISTAZO" class="sub">
          Se muestran los {{ MAX_VISTAZO }} primeros según tu prioridad.
        </span>
      </section>

      <section class="tarjeta" aria-labelledby="t-hacer">
        <div class="encabezado">
          <h2 id="t-hacer">Qué hacer con cada animal</h2>
          <span class="sub">Según cómo salió cada uno</span>
        </div>
        <div class="grupos">
          <div v-for="g in grupos" :key="g.categoria" class="grupo">
            <span class="grupo-nombre">
              <strong>{{ g.accion }}</strong>
              <span class="sub">{{ g.categoria }} · {{ cuantos(g.total, 'animal', 'animales') }}</span>
            </span>
            <div class="chips">
              <a v-for="a in g.animales" :key="a.id" :href="enlaceFicha(a.id)" class="chip chip-id" :class="g.clase">{{ idCorto(a.id) }}</a>
              <span v-if="g.resto" class="sub">y {{ g.resto }} más</span>
              <span v-if="!g.total" class="sub">Ninguno</span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section v-else class="tarjeta solo-escritorio" aria-labelledby="t-rank">
      <h2 id="t-rank">Ranking completo</h2>
      <div class="desliza">
        <table>
          <thead>
            <tr><th scope="col">#</th><th scope="col">Animal</th><th scope="col">Grupo</th>
              <th scope="col">Grasa</th><th scope="col">Leche</th><th scope="col">Ubre</th><th scope="col">Qué hacer</th></tr>
          </thead>
          <tbody>
            <tr v-for="a in ordenados" :key="a.id">
              <td class="sub">{{ puesto(a).puesto }}</td>
              <td><a :href="enlaceFicha(a.id)"><strong>Animal {{ idCorto(a.id) }}</strong></a><br /><span class="sub">{{ a.etiqueta }}</span></td>
              <td><span class="chip" :class="claseCategoria(puesto(a).categoria)">{{ puesto(a).categoria }}</span></td>
              <td v-for="r in RASGOS" :key="r.clave">{{ a.percentiles[r.clave] }}</td>
              <td>{{ puesto(a).accion }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <span class="sub">Grasa, Leche y Ubre: de cada 100 animales Holstein, a cuántos supera.</span>
    </section>

    <section class="tarjeta solo-movil" aria-labelledby="m-rodeo">
      <h2 id="m-rodeo">Qué hacer con tu rodeo</h2>
      <div v-for="g in grupos" :key="g.categoria" class="grupo-movil">
        <span class="grupo-nombre"><strong>{{ g.accion }}</strong><span class="sub">{{ g.categoria }}</span></span>
        <span class="chip cuenta" :class="g.clase">{{ g.total }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.pestanas { display: flex; gap: 4px; background: var(--pastilla); border-radius: 999px; padding: 4px; }
.pestanas button {
  min-height: 44px; padding: 0 18px; border: none; border-radius: 999px;
  background: transparent; color: var(--texto-medio); font-weight: 700; font-size: 13px; cursor: pointer;
}
.pestanas button[aria-pressed='true'] { background: var(--oscuro); color: var(--tarjeta); }

.cabecera { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.controles { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.prioridad {
  display: flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 6px 0 14px;
  border-radius: 999px; background: var(--app); font-size: 13px; font-weight: 600; color: var(--texto-medio);
}
.prioridad select {
  min-height: 34px; border: none; border-radius: 999px; background: var(--tarjeta);
  padding: 0 10px; font-weight: 700; color: var(--texto); cursor: pointer;
}

/* tarjeta de un animal */
.animal {
  background: var(--app); color: var(--texto); border-radius: 18px; padding: 16px;
  display: flex; flex-direction: column; gap: 12px; min-height: 150px; text-decoration: none;
}
.animal:hover { color: var(--texto); box-shadow: 0 0 0 2px var(--tierra); }
.animal.oscuro { background: var(--oscuro); color: var(--tarjeta); }
.animal.oscuro:hover { color: var(--tarjeta); }
.fila-arriba { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.puesto {
  flex: none; width: 46px; height: 46px; border-radius: 50%; background: var(--oscuro); color: var(--tarjeta);
  display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-size: 20px;
}
.oscuro .puesto { background: var(--tarjeta); color: var(--oscuro); }
.ir {
  width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--tierra);
  display: flex; align-items: center; justify-content: center;
}
.oscuro .ir { border-color: var(--chip-gris); }
.nombre { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.nombre strong { font-size: 17px; }
.detalle { font-size: 13px; color: var(--texto-suave); }
.oscuro .detalle { color: var(--sobre-oscuro); }
.chip-tarjeta { background: var(--chip-gris); color: var(--tarjeta); }
.oscuro .chip-tarjeta { background: var(--chip-oscuro); }

/* vistazo */
.vistazo-arriba { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; }
.total { font-size: 40px; line-height: 1; }
.total span { font-family: var(--sans); font-size: 13px; color: var(--texto-suave); }
.leyenda { display: grid; grid-template-columns: repeat(2, auto); gap: 4px 14px; font-size: 11.5px; color: var(--texto-medio); }
.leyenda span { display: flex; align-items: center; gap: 6px; }
.leyenda .punto { width: 10px; height: 10px; }
.desliza { overflow-x: auto; }
.matriz { display: grid; gap: 6px 4px; align-items: center; }
.rasgo { font-size: 12.5px; font-weight: 600; color: var(--texto-medio); }
.punto { width: 20px; height: 20px; border-radius: 50%; justify-self: center; display: inline-block; }
.punto-top { background: var(--oscuro); }
.punto-sobre { background: var(--lavanda); }
.punto-bajo { background: var(--tierra); }
.punto-ultimo { background: #E6DFD4; border: 1px solid var(--tierra); }
.columna {
  font-size: 10px; color: var(--texto-suave); text-decoration: none; justify-self: center;
  writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap;
}
.columna.horizontal { writing-mode: horizontal-tb; transform: none; }

/* grupos */
.grupos { display: flex; flex-direction: column; gap: 10px; }
.grupo {
  display: grid; grid-template-columns: 130px minmax(0, 1fr); gap: 10px; align-items: center;
  padding-bottom: 10px; border-bottom: 1px dashed var(--tierra-suave);
}
.grupo-nombre { display: flex; flex-direction: column; font-size: 13px; }
.grupo-nombre .sub { font-size: 11.5px; }
.chip-id { padding: 6px 12px; }

/* ranking */
table { width: 100%; border-collapse: collapse; min-width: 620px; font-size: 13.5px; }
th { text-align: left; color: var(--texto-suave); font-size: 11.5px; font-weight: 600; padding: 8px; }
td { padding: 8px; border-top: 1px solid var(--linea); }
td a { text-decoration: none; }

/* celular */
.saludo-movil { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 10px 4px 4px; }
.saludo-movil p { margin: 0; font-family: var(--serif); font-size: 26px; line-height: 1.1; }
.saludo-movil .sub { font-size: 12px; }
.lista-movil { display: flex; flex-direction: column; gap: 12px; }
.grupo-movil {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
  padding-bottom: 8px; border-bottom: 1px dashed var(--tierra-suave);
}
.cuenta { min-width: 34px; text-align: center; font-size: 13px; }

@media (max-width: 768px) {
  .mejores { background: transparent; padding: 0; }
  .mejores h1 { font-size: 22px; }
  .controles { order: 3; flex-basis: 100%; }
  .prioridad { flex: 1; justify-content: space-between; background: var(--tarjeta); }
  .prioridad select { background: var(--app); }
  .subir-movil { min-height: 40px; padding: 0 14px; font-size: 12.5px; }
  .animal { background: var(--tarjeta); padding: 14px; gap: 10px; min-height: 0; }
  .lista-movil .fila-arriba { align-items: center; }
  .lista-movil .puesto { width: 40px; height: 40px; font-size: 18px; }
  .lista-movil .nombre { flex: 1; }
  .lista-movil .nombre strong { font-size: 16px; }
}
</style>
