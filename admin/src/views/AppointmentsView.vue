<script setup>
import { computed, onMounted, ref } from 'vue'
import mainApi from '../api/mainClient'
import PageHeader from '../components/PageHeader.vue'
import Modal from '../components/Modal.vue'
import FormField from '../components/FormField.vue'
import DataTable from '../components/DataTable.vue'

const tab = ref('pending')
const filterStatus = ref('')
const pending = ref([])
const allAppts = ref([])
const patients = ref([])
const doctors = ref([])
const services = ref([])
const loading = ref(true)
const error = ref('')
const success = ref('')
const showModal = ref(false)
const modalMode = ref('review')
const selected = ref(null)
const saving = ref(false)

const reviewForm = ref({ action: 'confirm', scheduled_at: '', staff_notes: '', rejection_reason: '' })
const editForm = ref({
  patient_id: '', doctor_id: '', service_id: '', scheduled_at: '', reason: '', staff_notes: '', status: 'CONFIRMED',
})

const STATUS_LABELS = {
  PENDING: 'En attente',
  CONFIRMED: 'Confirmé',
  CANCELLED: 'Annulé',
  COMPLETED: 'Terminé',
}

const headers = [
  { key: 'patient_name', label: 'Patient' },
  { key: 'doctor_name', label: 'Médecin' },
  { key: 'service_name', label: 'Prestation' },
  { key: 'scheduled_at_label', label: 'Date' },
  { key: 'status_label', label: 'Statut' },
]

const displayedRows = computed(() => {
  let rows = tab.value === 'pending' ? pending.value : allAppts.value
  if (filterStatus.value) rows = rows.filter((r) => r.status === filterStatus.value)
  return rows
})

function formatRow(a) {
  return {
    ...a,
    scheduled_at_label: new Date(a.scheduled_at).toLocaleString('fr-FR'),
    service_name: a.service_name || '—',
    status_label: STATUS_LABELS[a.status] || a.status,
  }
}

function toDatetimeLocal(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [p, a, pat, doc, svc] = await Promise.all([
      mainApi.get('/hr/appointments/pending/'),
      mainApi.get('/hr/appointments/', { params: filterStatus.value ? { status: filterStatus.value } : {} }),
      patients.value.length ? Promise.resolve({ data: patients.value }) : mainApi.get('/clinical/patients/', { params: { page_size: 200 } }),
      doctors.value.length ? Promise.resolve({ data: doctors.value }) : mainApi.get('/hr/doctors/'),
      services.value.length ? Promise.resolve({ data: services.value }) : mainApi.get('/hr/services/manage/'),
    ])
    pending.value = p.data.map(formatRow)
    allAppts.value = a.data.map(formatRow)
    if (!patients.value.length) patients.value = pat.data
    if (!doctors.value.length) doctors.value = doc.data
    if (!services.value.length) services.value = svc.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur chargement des rendez-vous'
  } finally {
    loading.value = false
  }
}

function openReview(row) {
  selected.value = row
  modalMode.value = 'review'
  reviewForm.value = { action: 'confirm', scheduled_at: toDatetimeLocal(row.scheduled_at), staff_notes: row.staff_notes || '', rejection_reason: '' }
  showModal.value = true
}

function openEdit(row) {
  selected.value = row
  modalMode.value = 'edit'
  editForm.value = {
    patient_id: row.patient_id,
    doctor_id: row.doctor_id,
    service_id: row.service_id || '',
    scheduled_at: toDatetimeLocal(row.scheduled_at),
    reason: row.reason || '',
    staff_notes: row.staff_notes || '',
    status: row.status,
  }
  showModal.value = true
}

function openCreate() {
  selected.value = null
  modalMode.value = 'create'
  const firstDoc = doctors.value[0]
  const firstPat = patients.value[0]
  editForm.value = {
    patient_id: firstPat?.id || '',
    doctor_id: firstDoc?.id || '',
    service_id: services.value[0]?.id || '',
    scheduled_at: '',
    reason: '',
    staff_notes: '',
    status: 'CONFIRMED',
  }
  showModal.value = true
}

async function submitReview() {
  saving.value = true
  error.value = ''
  try {
    const payload = { action: reviewForm.value.action, staff_notes: reviewForm.value.staff_notes, rejection_reason: reviewForm.value.rejection_reason }
    if (reviewForm.value.scheduled_at && reviewForm.value.action !== 'reject') {
      payload.scheduled_at = new Date(reviewForm.value.scheduled_at).toISOString()
    }
    await mainApi.patch(`/hr/appointments/${selected.value.id}/review/`, payload)
    showModal.value = false
    success.value = 'Rendez-vous traité — notification patient envoyée.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur'
  } finally {
    saving.value = false
  }
}

async function submitEdit() {
  saving.value = true
  error.value = ''
  try {
    const payload = {
      patient_id: editForm.value.patient_id,
      doctor_id: editForm.value.doctor_id,
      service_id: editForm.value.service_id || null,
      scheduled_at: new Date(editForm.value.scheduled_at).toISOString(),
      reason: editForm.value.reason,
      staff_notes: editForm.value.staff_notes,
      status: editForm.value.status,
    }
    if (modalMode.value === 'create') {
      await mainApi.post('/hr/appointments/', { ...payload, status: editForm.value.status })
      success.value = 'Rendez-vous créé.'
    } else {
      await mainApi.patch(`/hr/appointments/${selected.value.id}/`, payload)
      success.value = 'Rendez-vous mis à jour.'
    }
    showModal.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Enregistrement impossible'
  } finally {
    saving.value = false
  }
}

async function cancelAppt(row) {
  if (!window.confirm(`Annuler le rendez-vous de ${row.patient_name} ?`)) return
  error.value = ''
  try {
    await mainApi.delete(`/hr/appointments/${row.id}/`)
    success.value = 'Rendez-vous annulé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Annulation impossible'
  }
}

function canEdit(row) {
  return row.status !== 'COMPLETED' && row.status !== 'CANCELLED'
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader :title="'Rendez-vous patients'" :subtitle="`${pending.length} en attente · ${allAppts.length} au total`">
      <template #actions>
        <button type="button" class="btn-primary" @click="openCreate">+ Nouveau rendez-vous</button>
      </template>
    </PageHeader>

    <p v-if="error" class="alert-error mb-4">{{ error }}</p>
    <p v-if="success" class="alert-success mb-4">{{ success }}</p>

    <div class="flex flex-wrap gap-2 mb-4">
      <button type="button" class="tab-btn" :class="tab === 'pending' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'pending'">
        En attente ({{ pending.length }})
      </button>
      <button type="button" class="tab-btn" :class="tab === 'all' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'all'">
        Tous
      </button>
      <select v-if="tab === 'all'" v-model="filterStatus" class="form-select sm:w-40" @change="load">
        <option value="">Tous statuts</option>
        <option value="PENDING">En attente</option>
        <option value="CONFIRMED">Confirmé</option>
        <option value="CANCELLED">Annulé</option>
        <option value="COMPLETED">Terminé</option>
      </select>
      <button type="button" class="btn-secondary text-sm ml-auto" @click="load">Actualiser</button>
    </div>

    <DataTable :headers="headers" :rows="displayedRows" :loading="loading" empty-title="Aucun rendez-vous">
      <template #cell-status_label="{ value, row }">
        <span
          class="text-xs font-semibold px-2 py-0.5 rounded-full"
          :class="{
            'bg-amber-100 text-amber-800': row.status === 'PENDING',
            'bg-emerald-100 text-emerald-800': row.status === 'CONFIRMED',
            'bg-red-100 text-red-800': row.status === 'CANCELLED',
            'bg-slate-100 text-slate-700': row.status === 'COMPLETED',
          }"
        >{{ value }}</span>
      </template>
      <template #actions="{ row }">
        <button v-if="row.status === 'PENDING'" type="button" class="text-admin text-xs font-medium hover:underline mr-2" @click="openReview(row)">Traiter</button>
        <button v-if="canEdit(row)" type="button" class="text-admin text-xs font-medium hover:underline mr-2" @click="openEdit(row)">Modifier</button>
        <button v-if="canEdit(row)" type="button" class="text-red-500 text-xs font-medium hover:underline" @click="cancelAppt(row)">Annuler</button>
      </template>
    </DataTable>

    <Modal :open="showModal" :title="modalMode === 'create' ? 'Nouveau rendez-vous' : modalMode === 'edit' ? 'Modifier le rendez-vous' : 'Traiter le rendez-vous'" wide @close="showModal = false">
      <div v-if="modalMode === 'review'" class="space-y-3">
        <FormField label="Action">
          <select v-model="reviewForm.action" class="form-select">
            <option value="confirm">Confirmer</option>
            <option value="postpone">Reporter</option>
            <option value="reject">Refuser</option>
          </select>
        </FormField>
        <FormField v-if="reviewForm.action !== 'reject'" label="Date & heure">
          <input v-model="reviewForm.scheduled_at" type="datetime-local" class="form-input" />
        </FormField>
        <FormField label="Note au patient">
          <textarea v-model="reviewForm.staff_notes" class="form-input min-h-[60px]" />
        </FormField>
        <FormField v-if="reviewForm.action === 'reject'" label="Motif de refus">
          <textarea v-model="reviewForm.rejection_reason" class="form-input min-h-[60px]" />
        </FormField>
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="Patient" required>
          <select v-model="editForm.patient_id" class="form-select">
            <option v-for="p in patients" :key="p.id" :value="p.id">{{ p.last_name }} {{ p.first_name }}</option>
          </select>
        </FormField>
        <FormField label="Médecin" required>
          <select v-model="editForm.doctor_id" class="form-select">
            <option v-for="d in doctors" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </FormField>
        <FormField label="Prestation">
          <select v-model="editForm.service_id" class="form-select">
            <option value="">— Aucune —</option>
            <option v-for="s in services" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </FormField>
        <FormField label="Statut">
          <select v-model="editForm.status" class="form-select">
            <option value="PENDING">En attente</option>
            <option value="CONFIRMED">Confirmé</option>
            <option value="COMPLETED">Terminé</option>
          </select>
        </FormField>
        <FormField label="Date & heure" required class="sm:col-span-2">
          <input v-model="editForm.scheduled_at" type="datetime-local" class="form-input" required />
        </FormField>
        <FormField label="Motif" class="sm:col-span-2">
          <textarea v-model="editForm.reason" class="form-input" rows="2" />
        </FormField>
        <FormField label="Notes internes" class="sm:col-span-2">
          <textarea v-model="editForm.staff_notes" class="form-input" rows="2" />
        </FormField>
      </div>
      <template #footer>
        <button type="button" class="btn-secondary" @click="showModal = false">Annuler</button>
        <button
          v-if="modalMode === 'review'"
          type="button"
          class="btn-primary"
          :disabled="saving"
          @click="submitReview"
        >Valider</button>
        <button v-else type="button" class="btn-primary" :disabled="saving" @click="submitEdit">{{ saving ? '…' : 'Enregistrer' }}</button>
      </template>
    </Modal>
  </div>
</template>
