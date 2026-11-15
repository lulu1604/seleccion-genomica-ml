<script setup lang="ts">
// Íconos de línea de la maqueta (24×24, trazo actual).
defineProps<{
  nombre: 'animales' | 'camara' | 'escudo' | 'subir' | 'info' | 'alerta' | 'flecha' | 'volver' | 'descargar'
  tamano?: number
}>()
</script>

<template>
  <svg aria-hidden="true" :width="tamano ?? 18" :height="tamano ?? 18" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <template v-if="nombre === 'animales'">
      <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
    </template>
    <template v-else-if="nombre === 'camara'">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </template>
    <template v-else-if="nombre === 'escudo'">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><polyline points="9 12 11 14 15 10" />
    </template>
    <template v-else-if="nombre === 'subir'">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </template>
    <template v-else-if="nombre === 'descargar'">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </template>
    <template v-else-if="nombre === 'info' || nombre === 'alerta'">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </template>
    <template v-else-if="nombre === 'flecha'">
      <line x1="7" y1="17" x2="17" y2="7" /><polyline points="7 7 17 7 17 17" />
    </template>
    <template v-else-if="nombre === 'volver'">
      <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
    </template>
  </svg>
</template>
