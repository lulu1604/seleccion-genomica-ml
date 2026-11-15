<script setup lang="ts">
// Menú lateral (solo en computadora).
import type { Pantalla } from '../navegacion'
import { FECHA_HOY, NOMBRE_ESTABLO } from '../textos'
import Icono from './Icono.vue'

defineProps<{ pantalla: Pantalla }>()

const SECCIONES = [
  { pantalla: 'animales', enlace: '#/animales', nombre: 'Mis animales', icono: 'animales' },
  { pantalla: 'medir', enlace: '#/medir', nombre: 'Medir por foto', icono: 'camara' },
  { pantalla: 'confiar', enlace: '#/confiar', nombre: '¿Por qué confiar?', icono: 'escudo' },
] as const
</script>

<template>
  <aside class="lateral solo-escritorio">
    <div class="logo" aria-hidden="true">B</div>
    <div class="saludo">
      <p>Hola,<br />{{ NOMBRE_ESTABLO }}</p>
      <span class="sub">Actualizado: {{ FECHA_HOY }}</span>
    </div>
    <nav aria-label="Secciones">
      <a v-for="s in SECCIONES" :key="s.pantalla" :href="s.enlace"
         :aria-current="(s.pantalla === pantalla || (s.pantalla === 'animales' && pantalla === 'ficha')) ? 'page' : undefined">
        <Icono :nombre="s.icono" />{{ s.nombre }}
      </a>
    </nav>
    <div class="relleno"></div>
    <slot />
  </aside>
</template>

<style scoped>
.lateral {
  flex: 0 0 240px;
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 22px 20px;
}
.logo {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--oscuro);
  color: var(--tarjeta);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 24px;
}
.saludo { display: flex; flex-direction: column; gap: 6px; }
.saludo p { margin: 0; font-family: var(--serif); font-size: 30px; line-height: 1.1; }
.saludo .sub { font-size: 12px; }
nav { display: flex; flex-direction: column; gap: 6px; }
nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  color: var(--texto-medio);
  font-weight: 600;
  text-decoration: none;
}
nav a:hover { background: var(--pastilla); }
nav a[aria-current='page'] { background: var(--lavanda-suave); color: var(--texto); font-weight: 700; }
.relleno { flex: 1; }
</style>
