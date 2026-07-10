<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'

const movements = ref([])
const loading = ref(true)
const error = ref('')
const eventFilter = ref('')

const headers = [
  { key: 'event_at', label: 'Date' },
  { key: 'patient_name', label: 'Patient' },
  { key: 'event_type_label', label: 'Événement' },
  { key: 'performed_by_name', label: 'Effectué par' },
]

const eventOptions = [
  { value: '', label: 'Tous les événements' },
  { value: 'ADMISSION', label: 'Admission' },
  { value: 'ADMISSION_CORRECTION', label: 'Correction admission' },
  { value: 'ADMISSION_CANCEL', label: 'Annulation admission' },
  { value: 'DISCHARGE', label: 'Sortie' },
  { value: 'INTERNAL_TRANSFER', label: 'Transfert interne' },
  { value: 'INTER_TRANSFER', label: 'Transfert inter-établissement' },
]

function fmtDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ limit: '200' })
    if (eventFilter.value) params.set('event_type', eventFilter.value)
    const { data } = await api.get(`/patient-movements/?${params}`)
    movements.value = data.map((m) => ({
      ...m,
      event_at: fmtDateTime(m.event_at),
      performed_by_name: m.performed_by_name || '—',
    }))
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function downloadPdf(row) {
  if (!row.document_id) return
  try {
    const response = await api.get(`/documents/${row.document_id}/download/`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.event_type_label}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Téléchargement impossible.'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Mouvements patients"
      subtitle="Historique complet des admissions, sorties et transferts avec attestations PDF signées"
    />

    <p v-if="error" class="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{{ error }}</p>

    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <select v-model="eventFilter" class="form-select flex-1 max-w-xs">
        <option v-for="opt in eventOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <button type="button" class="btn-primary shrink-0" @click="load">Actualiser</button>
    </div>

    <DataTable
      :headers="headers"
      :rows="movements"
      :loading="loading"
      empty-title="Aucun mouvement"
      empty-description="Les événements cliniques apparaîtront ici dès qu'une admission, sortie ou transfert est enregistré."
    >
      <template #actions="{ row }">
        <button
          v-if="row.document_id"
          type="button"
          class="text-violet-600 text-xs font-medium hover:underline"
          @click="downloadPdf(row)"
        >
          PDF
        </button>
      </template>
    </DataTable>
  </div>
</template>
