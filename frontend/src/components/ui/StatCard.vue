<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  hint: String,
  tone: { type: String, default: 'primary' },
  icon: String,
})

const tones = {
  primary: 'text-primary',
  blue: 'text-blue-600',
  green: 'text-emerald-600',
  orange: 'text-orange-600',
  red: 'text-red-600',
  violet: 'text-violet-600',
}
</script>

<template>
  <div class="stat-card">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="text-sm font-medium text-slate-500">{{ label }}</p>
        <p class="text-3xl font-bold mt-1 tracking-tight" :class="tones[tone] || tones.primary">{{ value }}</p>
        <p v-if="hint" class="text-xs text-slate-400 mt-2">{{ hint }}</p>
      </div>
      <div v-if="icon" class="w-11 h-11 rounded-2xl bg-slate-50 flex items-center justify-center text-xl shrink-0">
        {{ icon }}
      </div>
    </div>
  </div>
</template>
