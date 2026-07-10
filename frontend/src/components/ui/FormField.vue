<script setup>
defineProps({
  label: String,
  error: String,
  hint: String,
  required: Boolean,
})
</script>

<template>
  <label class="block">
    <span v-if="label" class="form-label">
      {{ label }}
      <span v-if="required" class="text-red-500" aria-hidden="true"> *</span>
    </span>
    <slot />
    <p v-if="error" class="text-xs text-red-600 mt-1.5 font-medium" role="alert">{{ error }}</p>
    <p v-else-if="hint" class="text-xs text-slate-400 mt-1">{{ hint }}</p>
  </label>
</template>
