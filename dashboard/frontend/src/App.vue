<script setup lang="ts">
import { onMounted } from 'vue'
import BarraMovil from './componentes/BarraMovil.vue'
import Icono from './componentes/Icono.vue'
import Lateral from './componentes/Lateral.vue'
import SubirArchivo from './componentes/SubirArchivo.vue'
import { ruta } from './navegacion'
import Confiar from './pantallas/Confiar.vue'
import Ficha from './pantallas/Ficha.vue'
import MedirFoto from './pantallas/MedirFoto.vue'
import MisAnimales from './pantallas/MisAnimales.vue'
import { cargarEjemplo, rodeo } from './rodeo'

// el rodeo se carga al abrir (también si se entra directo a una ficha)
onMounted(() => {
  if (!rodeo.animales.length) cargarEjemplo()
})
</script>

<template>
  <div class="marco">
    <div class="app">
      <Lateral :pantalla="ruta.pantalla">
        <div v-if="ruta.pantalla === 'animales'" class="pie-oscuro">
          <Icono nombre="subir" :tamano="26" />
          <span class="serif titulo">Evalúa animales nuevos</span>
          <span class="texto">Sube el archivo con su ADN y te decimos cuáles usar.</span>
          <SubirArchivo class="boton-claro" />
        </div>
        <div v-else-if="ruta.pantalla === 'medir'" class="pie-oscuro">
          <span class="serif titulo">Es una estimación</span>
          <span class="texto">Sirve para darte una idea. Para vender o dosificar medicamentos, usa la balanza.</span>
        </div>
      </Lateral>
      <main class="contenido">
        <MisAnimales v-if="ruta.pantalla === 'animales'" />
        <Ficha v-else-if="ruta.pantalla === 'ficha'" :id="ruta.id ?? ''" />
        <MedirFoto v-else-if="ruta.pantalla === 'medir'" />
        <Confiar v-else />
      </main>
    </div>
  </div>
  <BarraMovil :pantalla="ruta.pantalla" />
</template>

<style scoped>
.pie-oscuro {
  background: var(--oscuro);
  color: var(--tarjeta);
  border-radius: 18px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.titulo { font-size: 20px; line-height: 1.15; }
.texto { font-size: 12.5px; color: var(--sobre-oscuro); }
.boton-claro { border: 1px solid var(--borde-oscuro); color: var(--tarjeta); }
</style>
