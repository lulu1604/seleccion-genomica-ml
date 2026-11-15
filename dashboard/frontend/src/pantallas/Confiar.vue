<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, ErrorApi, type Confianza } from '../api'
import Estado from '../componentes/Estado.vue'
import { INICIALES, NOMBRE_ESTABLO } from '../textos'

const datos = ref<Confianza | null>(null)
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    datos.value = await api.confianza()
  } catch (e) {
    error.value = e instanceof ErrorApi ? e.message : 'Algo salió mal. Intenta de nuevo.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

const COLOR_NIVEL = { Baja: 'var(--tierra)', Media: 'var(--lavanda)', Alta: 'var(--oscuro)' }
const miles = (n: number) => n.toLocaleString('en-US')
</script>

<template>
  <div class="barra-superior">
    <h1>¿Qué tan seguido acierta?</h1>
    <span class="avatar" :aria-label="`Cuenta: ${NOMBRE_ESTABLO}`">{{ INICIALES }}</span>
  </div>

  <Estado :cargando="cargando" :error="error" @reintentar="cargar" />

  <div v-if="datos" class="panel">
    <section class="tarjeta tarjeta-oscura portada">
      <span class="serif cifra">{{ miles(datos.animales_referencia) }}</span>
      <span class="texto">animales Holstein con resultados ya conocidos. Le escondimos la respuesta a una parte,
        le pedimos que la adivinara y comparamos. Probamos 5 métodos y usamos el que mejor acertó.</span>
    </section>

    <section class="tarjeta" aria-labelledby="t-pares">
      <div class="encabezado">
        <h2 id="t-pares">Si comparas dos animales, ¿elige bien cuál es mejor?</h2>
        <span class="sub">De cada 10 comparaciones, cuántas acierta</span>
      </div>
      <div class="rejilla-3">
        <div v-for="a in datos.aciertos" :key="a.rasgo" class="acierto">
          <strong>{{ a.rasgo }}</strong>
          <span><strong class="serif numero">{{ a.de_cada_10 }}</strong> de cada 10</span>
          <div class="puntos" aria-hidden="true">
            <span v-for="i in 10" :key="i" :class="{ lleno: i <= a.de_cada_10 }"></span>
          </div>
        </div>
      </div>
    </section>

    <div class="rejilla-2">
      <section class="tarjeta" aria-labelledby="t-ref">
        <div class="encabezado">
          <h2 id="t-ref">Más animales de referencia, más acierta</h2>
          <span class="sub">Probado en rodeos simulados y en los {{ miles(datos.animales_referencia) }} Holstein</span>
        </div>
        <div v-for="t in datos.tamanos" :key="t.nombre" class="tamano">
          <span>{{ t.nombre }}</span>
          <div class="pista" aria-hidden="true">
            <div :style="{ width: `${t.ancho}%`, background: COLOR_NIVEL[t.nivel] }"></div>
          </div>
          <strong>{{ t.nivel }}</strong>
        </div>
        <span class="nota">Por eso el sistema se apoya en miles de animales Holstein de referencia.</span>
      </section>

      <section class="tarjeta" aria-labelledby="t-saber">
        <h2 id="t-saber">Lo que debes saber</h2>
        <ul>
          <li>Funciona con ganado <strong>Holstein</strong>. En mestizas o razas de carne no está probado.</li>
          <li>La genética es una parte: la comida, el clima y el manejo también cuentan.</li>
          <li>La medida por foto es aproximada: el peso puede variar unos <strong>{{ datos.error_peso_kg }} kg</strong>
            y la altura unos <strong>{{ datos.error_altura_cm }} cm</strong>.</li>
          <li>Acierta más en grasa que en salud de la ubre.</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.portada { flex-direction: row; flex-wrap: wrap; gap: 14px 32px; align-items: center; padding: 22px; }
.cifra { font-size: 52px; line-height: 1; }
.texto { flex: 1 1 380px; font-size: 15px; }
.acierto { background: var(--app); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.acierto > strong { font-size: 15px; }
.numero { font-size: 36px; }
.puntos { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 4px; }
.puntos span { aspect-ratio: 1; border-radius: 50%; background: var(--tierra-suave); }
.puntos span.lleno { background: var(--oscuro); }
.tamano { display: grid; grid-template-columns: 110px minmax(0, 1fr) 56px; gap: 10px; align-items: center; font-size: 13px; }
.pista { height: 16px; border-radius: 8px; background: var(--app); overflow: hidden; }
.pista div { height: 100%; border-radius: 8px; }
.nota { font-size: 12.5px; color: var(--texto-medio); }
ul { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 8px; font-size: 13.5px; }

@media (max-width: 768px) {
  .cifra { font-size: 44px; }
  .tamano { grid-template-columns: 96px minmax(0, 1fr) 48px; }
}
</style>
