<script setup>
defineProps({
  headers: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  loading: Boolean,
  emptyTitle: { type: String, default: 'Aucune donnée' },
})
</script>

<template>
  <div class="card overflow-hidden">
    <div v-if="loading" class="p-10 text-center text-slate-500" role="status">Chargement…</div>
    <div v-else-if="!rows.length" class="p-12 text-center">
      <p class="font-semibold text-slate-700">{{ emptyTitle }}</p>
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-slate-50/80 border-b border-slate-100">
            <th v-for="h in headers" :key="h.key" scope="col" class="text-left px-5 py-3.5 font-semibold text-slate-600 whitespace-nowrap">{{ h.label }}</th>
            <th v-if="$slots.actions" scope="col" class="px-5 py-3.5 w-32 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="(row, i) in rows" :key="row.id || i" class="hover:bg-slate-50/60 transition-colors">
            <td v-for="h in headers" :key="h.key" class="px-5 py-4 align-middle">
              <slot :name="`cell-${h.key}`" :row="row" :value="row[h.key]">{{ row[h.key] }}</slot>
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
