<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'

const hospitalizations = ref([])
const tasks = ref([])
const selectedHosp = ref('')
const vitals = ref([])
const vitalForm = ref({
  temperature: null, heart_rate: null, blood_pressure_systolic: null,
  blood_pressure_diastolic: null, oxygen_saturation: null, notes: '',
})

const taskHeaders = [
  { key: 'description', label: 'Soin' },
  { key: 'scheduled_at', label: 'Prévu' },
  { key: 'status', label: 'Statut' },
]

const chartPoints = computed(() => {
  const sorted = [...vitals.value].reverse().slice(-10)
  if (!sorted.length) return ''
  const maxHr = Math.max(...sorted.map((v) => v.heart_rate || 0), 100)
  return sorted
    .map((v, i) => {
      const x = 20 + i * 30
      const y = 80 - ((v.heart_rate || 0) / maxHr) * 60
      return `${x},${y}`
    })
    .join(' ')
})

async function load() {
  const [h, t] = await Promise.all([
    api.get('/clinical/hospitalizations/active/'),
    api.get('/clinical/care-tasks/overdue/'),
  ])
  hospitalizations.value = h.data
  tasks.value = t.data.map((x) => ({
    ...x,
    scheduled_at: new Date(x.scheduled_at).toLocaleString('fr-FR'),
  }))
}

async function loadVitals() {
  if (!selectedHosp.value) return
  const { data } = await api.get(`/clinical/vital-signs/${selectedHosp.value}/`)
  vitals.value = data
}

async function recordVitals() {
  await api.post('/clinical/vital-signs/', { hospitalization_id: selectedHosp.value, ...vitalForm.value })
  vitalForm.value = { temperature: null, heart_rate: null, blood_pressure_systolic: null, blood_pressure_diastolic: null, oxygen_saturation: null, notes: '' }
  await loadVitals()
}

async function completeTask(task) {
  await api.post(`/clinical/care-tasks/${task.id}/complete/`)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Soins infirmiers" subtitle="Constantes vitales, tendances, alertes doses omises" />

    <AlertBanner v-if="tasks.some(t => t.status === 'MISSED')" type="warning" title="Alertes — doses omises">
      <p v-for="t in tasks.filter(x => x.status === 'MISSED')" :key="t.id" class="text-sm">{{ t.description }}</p>
    </AlertBanner>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <div class="card card-body">
        <h3 class="font-semibold mb-4">Constantes vitales</h3>
        <select v-model="selectedHosp" @change="loadVitals" class="form-select mb-4">
          <option value="">Sélectionner hospitalisation</option>
          <option v-for="h in hospitalizations" :key="h.id" :value="h.id">{{ h.patient_name }}</option>
        </select>
        <div class="grid grid-cols-2 gap-3 mb-4">
          <input v-model.number="vitalForm.temperature" type="number" step="0.1" placeholder="Temp °C" class="form-input" />
          <input v-model.number="vitalForm.heart_rate" type="number" placeholder="FC bpm" class="form-input" />
          <input v-model.number="vitalForm.blood_pressure_systolic" type="number" placeholder="TA sys" class="form-input" />
          <input v-model.number="vitalForm.blood_pressure_diastolic" type="number" placeholder="TA dia" class="form-input" />
          <input v-model.number="vitalForm.oxygen_saturation" type="number" placeholder="SpO2 %" class="form-input col-span-2" />
        </div>
        <button type="button" @click="recordVitals" :disabled="!selectedHosp" class="btn-primary w-full">Enregistrer</button>

        <div v-if="vitals.length" class="mt-4">
          <p class="text-sm font-medium text-slate-600 mb-2">Tendance fréquence cardiaque</p>
          <svg viewBox="0 0 320 100" class="w-full h-24 bg-slate-50 rounded-lg">
            <polyline v-if="chartPoints" fill="none" stroke="#0d9488" stroke-width="2" :points="chartPoints" />
          </svg>
          <div class="mt-2 space-y-1">
            <div v-for="v in vitals.slice(0, 5)" :key="v.id" class="text-sm bg-slate-50 rounded-lg px-3 py-2 flex justify-between">
              <span>{{ new Date(v.recorded_at).toLocaleString('fr-FR') }}</span>
              <span>{{ v.temperature }}°C · FC {{ v.heart_rate }} · SpO2 {{ v.oxygen_saturation }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 class="font-semibold mb-3">Plan de soins / tâches</h3>
        <DataTable :headers="taskHeaders" :rows="tasks">
          <template #cell-status="{ value }">
            <StatusBadge :status="value" />
          </template>
          <template #actions="{ row }">
            <button v-if="row.status === 'PENDING'" type="button" @click="completeTask(row)" class="btn-primary !py-1 !px-2 text-xs">Effectué</button>
          </template>
        </DataTable>
      </div>
    </div>
  </div>
</template>
