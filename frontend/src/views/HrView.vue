<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import LoadingState from '../components/ui/LoadingState.vue'

const shifts = ref([])
const appointments = ref([])
const doctors = ref([])
const patients = ref([])
const tab = ref('shifts')
const loading = ref(true)
const error = ref('')
const success = ref('')
const shiftForm = ref({ staff_id: '', department_code: 'CARDIO', start_at: '', end_at: '', notes: '' })
const apptForm = ref({ patient_id: '', doctor_id: '', scheduled_at: '', reason: '' })

async function load() {
  loading.value = true
  try {
    const [s, d, p] = await Promise.all([
      api.get('/hr/shifts/'),
      api.get('/hr/doctors/'),
      api.get('/clinical/patients/'),
    ])
    shifts.value = s.data
    doctors.value = d.data
    patients.value = p.data
    if (patients.value.length) {
      const pid = patients.value[0].id
      const ap = await api.get(`/hr/appointments/patient/${pid}/`)
      appointments.value = ap.data
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement'
  } finally {
    loading.value = false
  }
}

async function createShift() {
  error.value = ''
  success.value = ''
  try {
    await api.post('/hr/shifts/', shiftForm.value)
    shiftForm.value = { staff_id: '', department_code: 'CARDIO', start_at: '', end_at: '', notes: '' }
    success.value = 'Garde planifiée.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur planification'
  }
}

async function bookAppt() {
  error.value = ''
  success.value = ''
  try {
    await api.post('/hr/appointments/', apptForm.value)
    apptForm.value = { patient_id: '', doctor_id: '', scheduled_at: '', reason: '' }
    success.value = 'Rendez-vous réservé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Réservation échouée'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="RH & rendez-vous" subtitle="Plannings de garde et calendrier des rendez-vous" />

    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <div class="flex flex-wrap gap-2 mb-6">
      <button type="button" @click="tab = 'shifts'" :class="tab === 'shifts' ? 'tab-btn-active' : 'tab-btn-inactive'" class="tab-btn">
        Gardes
      </button>
      <button type="button" @click="tab = 'rdv'" :class="tab === 'rdv' ? 'tab-btn-active' : 'tab-btn-inactive'" class="tab-btn">
        Rendez-vous
      </button>
    </div>

    <LoadingState v-if="loading" />

    <template v-else>
      <div v-if="tab === 'shifts'">
        <form @submit.prevent="createShift" class="card card-body mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <input v-model="shiftForm.staff_id" placeholder="ID personnel (UUID)" class="form-input font-mono text-sm" required />
          <input v-model="shiftForm.department_code" placeholder="Service" class="form-input" />
          <input v-model="shiftForm.start_at" type="datetime-local" class="form-input" required />
          <input v-model="shiftForm.end_at" type="datetime-local" class="form-input" required />
          <button type="submit" class="btn-primary">Planifier garde</button>
        </form>

        <div v-if="shifts.length" class="space-y-3">
          <div v-for="s in shifts" :key="s.id" class="card card-body !py-4">
            <div class="flex justify-between items-start gap-4">
              <div>
                <p class="font-semibold">{{ s.staff_name }}</p>
                <p class="text-sm text-slate-500">{{ s.department_code }}</p>
              </div>
              <span class="badge-primary">{{ s.department_code }}</span>
            </div>
            <p class="text-sm text-slate-600 mt-2">
              {{ new Date(s.start_at).toLocaleString('fr-FR') }}
              → {{ new Date(s.end_at).toLocaleString('fr-FR') }}
            </p>
          </div>
        </div>
        <EmptyState v-else title="Aucune garde planifiée" icon="📅" />
      </div>

      <div v-else>
        <form @submit.prevent="bookAppt" class="card card-body mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <select v-model="apptForm.patient_id" class="form-select" required>
            <option value="">Patient</option>
            <option v-for="p in patients" :key="p.id" :value="p.id">{{ p.last_name }} {{ p.first_name }}</option>
          </select>
          <select v-model="apptForm.doctor_id" class="form-select" required>
            <option value="">Médecin</option>
            <option v-for="d in doctors" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
          <input v-model="apptForm.scheduled_at" type="datetime-local" class="form-input" required />
          <button type="submit" class="btn-primary">Réserver un rendez-vous</button>
        </form>

        <div v-if="appointments.length" class="space-y-2">
          <div v-for="a in appointments" :key="a.id" class="card card-body !py-3 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
            <span class="font-medium">{{ a.patient_name }} → Dr {{ a.doctor_name }}</span>
            <div class="flex items-center gap-3">
              <span class="text-sm text-slate-500">{{ new Date(a.scheduled_at).toLocaleString('fr-FR') }}</span>
              <StatusBadge :status="a.status" />
            </div>
          </div>
        </div>
        <EmptyState v-else title="Aucun rendez-vous" icon="🗓️" />
      </div>
    </template>
  </div>
</template>
