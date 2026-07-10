<script setup>
defineProps({
  title: { type: String, default: 'Aucune donnée' },
  description: String,
  icon: { type: String, default: '📭' },
})
</script>

<template>
  <div class="card p-12 text-center">
    <div class="text-4xl mb-3" aria-hidden="true">{{ icon }}</div>
    <p class="font-semibold text-slate-700">{{ title }}</p>
    <p v-if="description" class="text-sm text-slate-500 mt-2 max-w-md mx-auto">{{ description }}</p>
    <div v-if="$slots.action" class="mt-6">
      <slot name="action" />
    </div>
  </div>
</template>
