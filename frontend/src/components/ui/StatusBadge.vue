<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

const cls = computed(() => {
  const s = props.status.toUpperCase()
  if (['CONFIRMED', 'DONE', 'VALIDATED', 'PAID', 'COMPLETED', 'AVAILABLE'].includes(s)) return 'badge-success'
  if (['PENDING', 'DRAFT', 'IN_PROGRESS', 'PROCESSING'].includes(s)) return 'badge-warning'
  if (['MISSED', 'CANCELLED', 'FAILED', 'OVERDUE', 'EXPIRED'].includes(s)) return 'badge-danger'
  return 'badge-neutral'
})
</script>

<template>
  <span :class="cls">{{ status }}</span>
</template>
