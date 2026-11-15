<script setup lang="ts">
// Botón "Subir archivo": elige un CSV y lo manda a evaluar.
import { rodeo, subirArchivo } from '../rodeo'

defineProps<{ texto?: string }>()

function elegido(evento: Event) {
  const input = evento.target as HTMLInputElement
  const archivo = input.files?.[0]
  input.value = '' // permite volver a elegir el mismo archivo
  if (archivo) subirArchivo(archivo)
}
</script>

<template>
  <label class="boton subir" :aria-disabled="rodeo.analizando">
    {{ texto ?? 'Subir archivo' }}
    <input type="file" accept=".csv,text/csv" :disabled="rodeo.analizando" @change="elegido" />
  </label>
</template>
