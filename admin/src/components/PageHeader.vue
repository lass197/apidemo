<script setup>
defineProps({
  title: String,
  subtitle: String,
})
</script>

<template>
  <header class="mb-8">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
      <div>
        <p class="text-xs font-semibold uppercase tracking-widest text-admin mb-1">Administration</p>
        <h1 class="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">{{ title }}</h1>
        <p v-if="subtitle" class="text-slate-500 mt-1.5 max-w-2xl">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2 shrink-0">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
