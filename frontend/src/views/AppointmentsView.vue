<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import Modal from '../components/Modal.vue'
import FormField from '../components/ui/FormField.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
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
const doctorSlots = ref([])
const loadingSlots = ref(false)
const slotCheck = ref({ available: true, message: '' })
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
  { key: 'patient_email', label: 'Email' },
  { key: 'doctor_name', label: 'Médecin' },
  { key: 'service_name', label: 'Prestation' },
  { key: 'scheduled_at_label', label: 'Date' },
  { key: 'availability_label', label: 'Dispo. médecin' },
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
    patient_email: a.patient_email || '—',
    availability_label: a.doctor_slot_available ? 'Disponible' : (a.doctor_slot_message || 'Indisponible'),
  }
}

async function loadDoctorSlots(doctorId) {
  if (!doctorId) {
    doctorSlots.value = []
    return
  }
  loadingSlots.value = true
  try {
    const { data } = await api.get(`/hr/availabilities/${doctorId}/slots/`)
    doctorSlots.value = data
  } catch {
    doctorSlots.value = []
  } finally {
    loadingSlots.value = false
  }
}

function updateSlotCheck() {
  if (!selected.value || reviewForm.value.action === 'reject') {
    slotCheck.value = { available: true, message: '' }
    return
  }
  const iso = reviewForm.value.scheduled_at
    ? new Date(reviewForm.value.scheduled_at).toISOString()
    : selected.value.scheduled_at
  const match = doctorSlots.value.find(
    (s) => new Date(s.scheduled_at).getTime() === new Date(iso).getTime(),
  )
  if (match) {
    slotCheck.value = {
      available: match.available,
      message: match.available ? 'Créneau libre dans l\'agenda du médecin' : 'Créneau déjà réservé',
    }
  } else if (selected.value.doctor_slot_available && !reviewForm.value.scheduled_at) {
    slotCheck.value = { available: true, message: selected.value.doctor_slot_message || 'Créneau disponible' }
  } else {
    slotCheck.value = {
      available: false,
      message: 'Hors agenda du médecin — choisissez un créneau ci-dessous ou refusez la demande',
    }
  }
}

function pickSlot(iso) {
  reviewForm.value.scheduled_at = toDatetimeLocal(iso)
  updateSlotCheck()
}

const canConfirmReview = computed(() => {
  if (reviewForm.value.action === 'reject') return reviewForm.value.rejection_reason.trim().length > 0
  if (reviewForm.value.action === 'postpone') return !!reviewForm.value.scheduled_at
  return slotCheck.value.available
})

const availableSlotsForReview = computed(() =>
  doctorSlots.value.filter((s) => s.available).slice(0, 16),
)

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
      api.get('/hr/appointments/pending/'),
      api.get('/hr/appointments/', { params: filterStatus.value ? { status: filterStatus.value } : {} }),
      patients.value.length ? Promise.resolve({ data: patients.value }) : api.get('/clinical/patients/', { params: { page: 1, page_size: 200 } }),
      doctors.value.length ? Promise.resolve({ data: doctors.value }) : api.get('/hr/doctors/'),
      services.value.length ? Promise.resolve({ data: services.value }) : api.get('/hr/services/manage/'),
    ])
    pending.value = p.data.map(formatRow)
    allAppts.value = a.data.map(formatRow)
    if (!patients.value.length) patients.value = pat.data
    if (!doctors.value.length) doctors.value = doc.data
    if (!services.value.length) services.value = svc.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Accès refusé (permission hr.review_appointments)'
  } finally {
    loading.value = false
  }
}

function openReview(row) {
  selected.value = row
  modalMode.value = 'review'
  reviewForm.value = {
    action: 'confirm',
    scheduled_at: toDatetimeLocal(row.scheduled_at),
    staff_notes: row.staff_notes || '',
    rejection_reason: '',
  }
  slotCheck.value = {
    available: row.doctor_slot_available !== false,
    message: row.doctor_slot_message || '',
  }
  loadDoctorSlots(row.doctor_id)
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
  editForm.value = {
    patient_id: patients.value[0]?.id || '',
    doctor_id: doctors.value[0]?.id || '',
    service_id: services.value[0]?.id || '',
    scheduled_at: '',
    reason: '',
    staff_notes: '',
    status: 'CONFIRMED',
  }
  showModal.value = true
}

async function submitReview() {
  error.value = ''
  success.value = ''
  if (!canConfirmReview.value) {
    error.value = slotCheck.value.message || 'Créneau indisponible — choisissez un autre horaire ou refusez la demande.'
    return
  }
  saving.value = true
  try {
    const payload = {
      action: reviewForm.value.action,
      staff_notes: reviewForm.value.staff_notes,
      rejection_reason: reviewForm.value.rejection_reason,
    }
    if (reviewForm.value.scheduled_at && ['confirm', 'postpone'].includes(reviewForm.value.action)) {
      payload.scheduled_at = new Date(reviewForm.value.scheduled_at).toISOString()
    }
    await api.patch(`/hr/appointments/${selected.value.id}/review/`, payload)
    showModal.value = false
    success.value = 'Rendez-vous mis à jour — le patient sera notifié par email.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible.'
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
      await api.post('/hr/appointments/', payload)
      success.value = 'Rendez-vous créé.'
    } else {
      await api.patch(`/hr/appointments/${selected.value.id}/`, payload)
      success.value = 'Rendez-vous mis à jour.'
    }
    showModal.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Enregistrement impossible.'
  } finally {
    saving.value = false
  }
}

async function cancelAppt(row) {
  if (!window.confirm(`Annuler le rendez-vous de ${row.patient_name} ?`)) return
  try {
    await api.delete(`/hr/appointments/${row.id}/`)
    success.value = 'Rendez-vous annulé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Annulation impossible.'
  }
}

function canEdit(row) {
  return row.status !== 'COMPLETED' && row.status !== 'CANCELLED'
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Rendez-vous patients" :subtitle="`${pending.length} demande(s) en attente — validez selon la disponibilité du médecin`">
      <template #actions>
        <button type="button" class="btn-primary" @click="openCreate">+ Nouveau rendez-vous</button>
      </template>
    </PageHeader>

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
    <AlertBanner v-if="success" type="success" class="mb-4">{{ success }}</AlertBanner>

    <div class="flex flex-wrap gap-2 mb-4">
      <button type="button" class="tab-btn" :class="tab === 'pending' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'pending'">
        En attente ({{ pending.length }})
      </button>
      <button type="button" class="tab-btn" :class="tab === 'all' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'all'">
        Tous les rendez-vous
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

    <DataTable
      :headers="headers"
      :rows="displayedRows"
      :loading="loading"
      empty-title="Aucune demande en attente"
      empty-description="Les nouvelles réservations patient apparaîtront ici."
    >
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
      <template #cell-availability_label="{ value, row }">
        <span
          class="text-xs font-semibold px-2 py-0.5 rounded-full"
          :class="row.doctor_slot_available ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'"
        >{{ value }}</span>
      </template>
      <template #actions="{ row }">
        <button v-if="row.status === 'PENDING'" type="button" class="text-primary text-xs font-medium hover:underline mr-2" @click="openReview(row)">Traiter</button>
        <button v-if="canEdit(row)" type="button" class="text-primary text-xs font-medium hover:underline mr-2" @click="openEdit(row)">Modifier</button>
        <button v-if="canEdit(row)" type="button" class="text-red-500 text-xs font-medium hover:underline" @click="cancelAppt(row)">Annuler</button>
      </template>
    </DataTable>

    <Modal :open="showModal" :title="modalMode === 'create' ? 'Nouveau rendez-vous' : modalMode === 'edit' ? 'Modifier le rendez-vous' : 'Gérer le rendez-vous'" @close="showModal = false">
      <p v-if="selected && modalMode === 'review'" class="text-sm text-slate-600 mb-4">
        <strong>{{ selected.patient_name }}</strong> — {{ selected.doctor_name }}
      </p>
      <div v-if="modalMode === 'review'" class="space-y-3">
        <div
          v-if="reviewForm.action === 'confirm'"
          class="rounded-xl px-3 py-2 text-sm border"
          :class="slotCheck.available ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800'"
        >
          {{ slotCheck.message || (slotCheck.available ? 'Créneau compatible avec l\'agenda du médecin' : 'Créneau incompatible') }}
        </div>
        <FormField label="Action">
          <select v-model="reviewForm.action" class="form-select" @change="updateSlotCheck">
            <option value="confirm">Confirmer (valider)</option>
            <option value="postpone">Reporter (nouvelle date)</option>
            <option value="reject">Refuser (créneau indisponible)</option>
          </select>
        </FormField>
        <FormField v-if="reviewForm.action !== 'reject'" label="Date & heure">
          <input v-model="reviewForm.scheduled_at" type="datetime-local" class="form-input" @change="updateSlotCheck" />
        </FormField>
        <div v-if="reviewForm.action !== 'reject' && availableSlotsForReview.length" class="rounded-xl bg-slate-50 border border-slate-100 p-3">
          <p class="text-xs font-semibold text-slate-600 mb-2">Créneaux libres — {{ selected?.doctor_name }}</p>
          <div v-if="loadingSlots" class="text-xs text-slate-400">Chargement de l'agenda…</div>
          <div v-else class="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
            <button
              v-for="s in availableSlotsForReview"
              :key="s.scheduled_at"
              type="button"
              class="text-xs px-2 py-1 rounded-lg border border-teal-200 bg-white text-teal-800 hover:bg-teal-50"
              @click="pickSlot(s.scheduled_at)"
            >
              {{ new Date(s.scheduled_at).toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) }}
            </button>
          </div>
        </div>
        <FormField label="Note au patient">
          <textarea v-model="reviewForm.staff_notes" class="form-input min-h-[60px]" placeholder="Instructions, rappel documents…" />
        </FormField>
        <FormField v-if="reviewForm.action === 'reject'" label="Motif de refus">
          <textarea v-model="reviewForm.rejection_reason" class="form-input min-h-[60px]" placeholder="Ex. médecin indisponible à cette heure…" required />
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
          <textarea v-model="editForm.reason" class="form-input min-h-[60px]" />
        </FormField>
        <FormField label="Notes internes" class="sm:col-span-2">
          <textarea v-model="editForm.staff_notes" class="form-input min-h-[60px]" />
        </FormField>
      </div>
      <template #footer>
        <button type="button" class="btn-secondary" @click="showModal = false">Annuler</button>
        <button v-if="modalMode === 'review'" type="button" class="btn-primary" :disabled="saving || !canConfirmReview" @click="submitReview">
          {{ saving ? 'Enregistrement…' : (reviewForm.action === 'confirm' ? 'Valider le rendez-vous' : 'Enregistrer') }}
        </button>
        <button v-else type="button" class="btn-primary" :disabled="saving" @click="submitEdit">
          {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
      </template>
    </Modal>
  </div>
</template>
