<script setup>
defineProps({
  open: Boolean,
  title: String,
  wide: Boolean,
})
defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="$emit('close')" />
      <div
        class="relative bg-white rounded-2xl shadow-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        :class="wide ? 'max-w-3xl' : 'max-w-lg'"
        role="dialog"
        aria-modal="true"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100 shrink-0">
          <h2 class="text-lg font-semibold text-slate-900">{{ title }}</h2>
          <button type="button" class="text-slate-400 hover:text-slate-600 text-xl leading-none" @click="$emit('close')">×</button>
        </div>
        <div class="overflow-y-auto px-6 py-4">
          <slot />
        </div>
        <div v-if="$slots.footer" class="px-6 py-4 border-t border-slate-100 shrink-0 flex gap-2 justify-end">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
