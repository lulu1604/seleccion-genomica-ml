<script setup lang="ts">
// Carga o error de una pantalla completa.
defineProps<{ cargando: boolean; error: string; textoCargando?: string }>()
defineEmits<{ reintentar: [] }>()
</script>

<template>
  <div v-if="cargando" class="estado" role="status">
    <span class="girando" aria-hidden="true"></span>
    <span>{{ textoCargando ?? 'Cargando…' }}</span>
  </div>
  <div v-else-if="error" class="estado" role="alert">
    <strong>{{ error }}</strong>
    <button type="button" class="boton boton-oscuro" @click="$emit('reintentar')">Intentar de nuevo</button>
  </div>
</template>
