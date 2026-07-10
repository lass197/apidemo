<script setup>
defineProps({
  type: { type: String, default: 'error' },
  title: String,
})
</script>

<template>
  <div
    class="alert mb-4"
    :class="{
      'alert-error': type === 'error',
      'alert-warning': type === 'warning',
      'alert-success': type === 'success',
      'alert-info': type === 'info',
    }"
    role="alert"
  >
    <p v-if="title" class="font-semibold mb-1">{{ title }}</p>
    <slot />
  </div>
</template>
