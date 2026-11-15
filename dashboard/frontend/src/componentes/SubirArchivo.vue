<script setup lang="ts">
// Botón "Subir archivo": elige la plantilla de Excel (o un CSV) y la manda a evaluar.
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
    <input type="file" accept=".xlsx,.csv" :disabled="rodeo.analizando" @change="elegido" />
  </label>
</template>
