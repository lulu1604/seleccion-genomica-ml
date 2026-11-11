<script setup lang="ts">
// Barra inferior fija (solo en el celular).
import type { Pantalla } from '../navegacion'

defineProps<{ pantalla: Pantalla }>()

const SECCIONES = [
  { pantalla: 'animales', enlace: '#/animales', nombre: 'Animales' },
  { pantalla: 'medir', enlace: '#/medir', nombre: 'Medir' },
  { pantalla: 'confiar', enlace: '#/confiar', nombre: 'Confiar' },
] as const
</script>

<template>
  <nav class="barra-movil solo-movil" aria-label="Secciones">
    <div>
      <a v-for="s in SECCIONES" :key="s.pantalla" :href="s.enlace"
         :aria-current="(s.pantalla === pantalla || (s.pantalla === 'animales' && pantalla === 'ficha')) ? 'page' : undefined">
        {{ s.nombre }}
      </a>
    </div>
  </nav>
</template>

<style scoped>
.barra-movil {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px 12px calc(14px + env(safe-area-inset-bottom));
  background: var(--app);
  z-index: 10;
}
div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  background: var(--oscuro);
  border-radius: 999px;
  padding: 6px;
  max-width: 480px;
  margin: 0 auto;
}
a {
  min-height: 48px;
  border-radius: 999px;
  color: var(--tarjeta);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 12.5px;
  text-decoration: none;
}
a[aria-current='page'] { background: var(--tarjeta); color: var(--oscuro); font-weight: 700; }
</style>
