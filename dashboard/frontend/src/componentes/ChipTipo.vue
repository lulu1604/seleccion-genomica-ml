<script setup lang="ts">
// Chip grande con el tipo del animal (Toro, Vaca, Vaquilla). Sin tipo indicado no muestra nada.
import { computed } from 'vue'
import { TIPOS, tipoDe } from '../textos'

const props = defineProps<{ tipo: string }>()
const nombre = computed(() => {
  const t = tipoDe({ tipo: props.tipo })
  return t ? TIPOS[t].nombre : ''
})
</script>

<template>
  <span v-if="nombre" class="chip chip-tipo">{{ nombre }}</span>
</template>
