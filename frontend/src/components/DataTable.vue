<script setup>
import LoadingState from './ui/LoadingState.vue'
import EmptyState from './ui/EmptyState.vue'

defineProps({
  headers: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  loading: Boolean,
  emptyTitle: { type: String, default: 'Aucune donnée' },
  emptyDescription: String,
})
</script>

<template>
  <LoadingState v-if="loading" />
  <EmptyState
    v-else-if="!rows.length"
    :title="emptyTitle"
    :description="emptyDescription"
  />
  <div v-else class="card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-slate-50/80 border-b border-slate-100">
            <th
              v-for="h in headers"
              :key="h.key"
              scope="col"
              class="text-left px-5 py-3.5 font-semibold text-slate-600 whitespace-nowrap"
            >
              {{ h.label }}
            </th>
            <th v-if="$slots.actions" scope="col" class="px-5 py-3.5 w-32 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="(row, i) in rows" :key="row.id || i" class="hover:bg-slate-50/60 transition-colors">
            <td v-for="h in headers" :key="h.key" class="px-5 py-4 align-middle">
              <slot :name="`cell-${h.key}`" :row="row" :value="row[h.key]">
                {{ row[h.key] }}
              </slot>
            </td>
            <td v-if="$slots.actions" class="px-5 py-4 text-right">
              <slot name="actions" :row="row" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
