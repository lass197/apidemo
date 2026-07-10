<script setup>
defineProps({
  label: { type: String, default: 'Chargement en cours…' },
})
</script>

<template>
  <div class="card p-10 flex flex-col items-center justify-center gap-4" role="status" aria-live="polite">
    <div class="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
    <p class="text-sm text-slate-500">{{ label }}</p>
  </div>
</template>
