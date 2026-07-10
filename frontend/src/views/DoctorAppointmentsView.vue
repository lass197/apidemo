<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import EmptyState from '../components/ui/EmptyState.vue'

const tab = ref('upcoming')
const filterStatus = ref('')
const loading = ref(true)
const error = ref('')
const appointments = ref([])
const patients = ref([])

const STATUS_LABELS = {
  PENDING: 'En attente',
  CONFIRMED: 'Confirmé',
  CANCELLED: 'Annulé',
  COMPLETED: 'Terminé',
}

const apptHeaders = [
  { key: 'patient_name', label: 'Patient' },
  { key: 'patient_email', label: 'Email' },
  { key: 'patient_phone', label: 'Téléphone' },
  { key: 'service_name', label: 'Prestation' },
  { key: 'scheduled_at_label', label: 'Date' },
  { key: 'status_label', label: 'Statut' },
]

const patientHeaders = [
  { key: 'name', label: 'Patient' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Téléphone' },
  { key: 'next_label', label: 'Prochain rendez-vous' },
]

function formatAppt(a) {
  return {
    ...a,
    scheduled_at_label: new Date(a.scheduled_at).toLocaleString('fr-FR'),
    service_name: a.service_name || 'Consultation',
    status_label: STATUS_LABELS[a.status] || a.status,
    patient_email: a.patient_email || '—',
    patient_phone: a.patient_phone || '—',
  }
}

const upcomingRows = computed(() =>
  appointments.value
    .filter((a) => ['PENDING', 'CONFIRMED'].includes(a.status))
    .filter((a) => new Date(a.scheduled_at) >= new Date())
    .map(formatAppt)
)

const allRows = computed(() => {
  let rows = appointments.value.map(formatAppt)
  if (filterStatus.value) rows = rows.filter((r) => r.status === filterStatus.value)
  return rows
})

const patientRows = computed(() =>
  patients.value.map((p) => ({
    ...p,
    email: p.email || '—',
    phone: p.phone || '—',
    next_label: p.next_appointment_at
      ? new Date(p.next_appointment_at).toLocaleString('fr-FR')
      : '—',
  }))
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [appts, pats] = await Promise.all([
      api.get('/hr/appointments/mine/'),
      api.get('/hr/appointments/mine/patients/'),
    ])
    appointments.value = appts.data
    patients.value = pats.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de charger vos rendez-vous.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Mes rendez-vous"
      subtitle="Liste de vos consultations planifiées — coordonnées patients incluses"
    />

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>

    <div class="flex flex-wrap gap-2 mb-6">
      <button
        type="button"
        class="tab-btn"
        :class="tab === 'upcoming' ? 'tab-btn-active' : 'tab-btn-inactive'"
        @click="tab = 'upcoming'"
      >À venir</button>
      <button
        type="button"
        class="tab-btn"
        :class="tab === 'all' ? 'tab-btn-active' : 'tab-btn-inactive'"
        @click="tab = 'all'"
      >Tous les rendez-vous</button>
      <button
        type="button"
        class="tab-btn"
        :class="tab === 'patients' ? 'tab-btn-active' : 'tab-btn-inactive'"
        @click="tab = 'patients'"
      >Mes patients</button>
      <button type="button" class="btn-secondary text-sm ml-auto" @click="load">Actualiser</button>
    </div>

    <LoadingState v-if="loading" />

    <template v-else-if="tab === 'upcoming'">
      <EmptyState
        v-if="!upcomingRows.length"
        title="Aucun rendez-vous à venir"
        description="Les demandes validées par le secrétariat apparaîtront ici."
      />
      <DataTable v-else :headers="apptHeaders" :rows="upcomingRows" empty-title="">
        <template #cell-status_label="{ row }">
          <StatusBadge :status="row.status" />
        </template>
        <template #cell-patient_email="{ row }">
          <a v-if="row.patient_email && row.patient_email !== '—'" :href="`mailto:${row.patient_email}`" class="text-primary text-sm hover:underline">{{ row.patient_email }}</a>
          <span v-else class="text-slate-400">—</span>
        </template>
      </DataTable>
    </template>

    <template v-else-if="tab === 'all'">
      <div class="mb-4 flex flex-wrap gap-2 items-center">
        <label class="text-sm text-slate-600">Filtrer :</label>
        <select v-model="filterStatus" class="form-select sm:w-44">
          <option value="">Tous statuts</option>
          <option v-for="(label, code) in STATUS_LABELS" :key="code" :value="code">{{ label }}</option>
        </select>
      </div>
      <EmptyState v-if="!allRows.length" title="Aucun rendez-vous" />
      <DataTable v-else :headers="apptHeaders" :rows="allRows" empty-title="">
        <template #cell-status_label="{ row }">
          <StatusBadge :status="row.status" />
        </template>
        <template #cell-patient_email="{ row }">
          <a v-if="row.patient_email && row.patient_email !== '—'" :href="`mailto:${row.patient_email}`" class="text-primary text-sm hover:underline">{{ row.patient_email }}</a>
          <span v-else class="text-slate-400">—</span>
        </template>
      </DataTable>
    </template>

    <template v-else>
      <EmptyState v-if="!patientRows.length" title="Aucun patient" description="Vos patients avec rendez-vous s'afficheront ici." />
      <DataTable v-else :headers="patientHeaders" :rows="patientRows" empty-title="">
        <template #cell-email="{ row }">
          <a v-if="row.email && row.email !== '—'" :href="`mailto:${row.email}`" class="text-primary text-sm hover:underline">{{ row.email }}</a>
          <span v-else class="text-slate-400">—</span>
        </template>
      </DataTable>
    </template>
  </div>
</template>
