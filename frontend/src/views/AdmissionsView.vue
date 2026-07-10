<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import FormField from '../components/ui/FormField.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import Modal from '../components/Modal.vue'
import {
  blockDigitsInName,
  sanitizeNamePaste,
  validateFields,
  validators,
} from '../composables/useFormValidation'

const hospitalizations = ref([])
const movements = ref([])
const error = ref('')
const success = ref('')
const loading = ref(true)
const submitAttempted = ref(false)
const fieldErrors = ref({})

const form = ref({
  patient_id: '',
  bed_id: '',
  referring_doctor_id: '',
  expected_discharge_date: '',
  admission_reason: '',
})

const patientQuery = ref('')
const doctorQuery = ref('')
const bedQuery = ref('')
const dischargeQuery = ref('')

const patientResults = ref([])
const doctorResults = ref([])
const bedResults = ref([])
const dischargeResults = ref([])

const searchingPatient = ref(false)
const searchingDoctor = ref(false)
const searchingBed = ref(false)
const searchingDischarge = ref(false)

const selectedPatient = ref(null)
const selectedDoctor = ref(null)
const selectedBed = ref(null)
const selectedDischarge = ref(null)

const dischargeId = ref('')

const editModalOpen = ref(false)
const editTarget = ref(null)
const editForm = ref({ admission_date: '', reason: '' })
const cancelReason = ref('')

let patientTimer = null
let doctorTimer = null
let bedTimer = null
let dischargeTimer = null

function fmtDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function patientLabel(p) {
  return `${p.last_name} ${p.first_name}`
}

function doctorLabel(d) {
  return `Dr. ${d.last_name} ${d.first_name}`
}

function bedLabel(b) {
  return `${b.department_name} — Ch.${b.room_number} Lit ${b.label}`
}

async function searchPatients() {
  const term = patientQuery.value.trim()
  if (term.length < 2) {
    patientResults.value = []
    return
  }
  searchingPatient.value = true
  try {
    const { data } = await api.get('/clinical/patients/', { params: { search: term, page_size: 20 } })
    patientResults.value = data
  } catch {
    patientResults.value = []
  } finally {
    searchingPatient.value = false
  }
}

async function searchDoctors() {
  const term = doctorQuery.value.trim()
  if (term.length < 2) {
    doctorResults.value = []
    return
  }
  searchingDoctor.value = true
  try {
    const { data } = await api.get('/clinical/doctors/', { params: { search: term } })
    doctorResults.value = data
  } catch {
    doctorResults.value = []
  } finally {
    searchingDoctor.value = false
  }
}

async function searchBeds() {
  const term = bedQuery.value.trim()
  searchingBed.value = true
  try {
    const { data } = await api.get('/clinical/beds/available/', {
      params: term.length >= 2 ? { search: term } : {},
    })
    bedResults.value = data
  } catch {
    bedResults.value = []
  } finally {
    searchingBed.value = false
  }
}

async function searchDischargePatients() {
  const term = dischargeQuery.value.trim()
  if (term.length < 2) {
    dischargeResults.value = []
    return
  }
  searchingDischarge.value = true
  try {
    const { data } = await api.get('/clinical/hospitalizations/active/', { params: { search: term } })
    dischargeResults.value = data
  } catch {
    dischargeResults.value = []
  } finally {
    searchingDischarge.value = false
  }
}

function onPatientInput() {
  patientQuery.value = patientQuery.value.replace(/\d/g, '')
  if (selectedPatient.value && patientQuery.value.trim() !== patientLabel(selectedPatient.value)) {
    form.value.patient_id = ''
    selectedPatient.value = null
  }
  if (fieldErrors.value.patient) fieldErrors.value = { ...fieldErrors.value, patient: '' }
  clearTimeout(patientTimer)
  patientTimer = setTimeout(searchPatients, 300)
}

function onDoctorInput() {
  doctorQuery.value = doctorQuery.value.replace(/\d/g, '')
  if (selectedDoctor.value && doctorQuery.value.trim() !== doctorLabel(selectedDoctor.value)) {
    form.value.referring_doctor_id = ''
    selectedDoctor.value = null
  }
  if (fieldErrors.value.doctor) fieldErrors.value = { ...fieldErrors.value, doctor: '' }
  clearTimeout(doctorTimer)
  doctorTimer = setTimeout(searchDoctors, 300)
}

function onBedInput() {
  if (selectedBed.value && bedQuery.value.trim() !== bedLabel(selectedBed.value)) {
    form.value.bed_id = ''
    selectedBed.value = null
  }
  if (fieldErrors.value.bed) fieldErrors.value = { ...fieldErrors.value, bed: '' }
  clearTimeout(bedTimer)
  bedTimer = setTimeout(searchBeds, 300)
}

function onDischargeInput() {
  dischargeQuery.value = dischargeQuery.value.replace(/\d/g, '')
  if (selectedDischarge.value && dischargeQuery.value.trim() !== selectedDischarge.value.patient_name) {
    dischargeId.value = ''
    selectedDischarge.value = null
  }
  clearTimeout(dischargeTimer)
  dischargeTimer = setTimeout(searchDischargePatients, 300)
}

function onNamePaste(target, event) {
  sanitizeNamePaste(event, (text) => {
    if (target === 'patient') {
      patientQuery.value = text
      onPatientInput()
    } else if (target === 'doctor') {
      doctorQuery.value = text
      onDoctorInput()
    } else {
      dischargeQuery.value = text
      onDischargeInput()
    }
  })
}

function selectPatient(p) {
  selectedPatient.value = p
  form.value.patient_id = p.id
  patientQuery.value = patientLabel(p)
  patientResults.value = []
  fieldErrors.value = { ...fieldErrors.value, patient: '' }
}

function selectDoctor(d) {
  selectedDoctor.value = d
  form.value.referring_doctor_id = d.id
  doctorQuery.value = doctorLabel(d)
  doctorResults.value = []
  fieldErrors.value = { ...fieldErrors.value, doctor: '' }
}

function selectBed(b) {
  selectedBed.value = b
  form.value.bed_id = b.id
  bedQuery.value = bedLabel(b)
  bedResults.value = []
  fieldErrors.value = { ...fieldErrors.value, bed: '' }
}

function selectDischarge(h) {
  selectedDischarge.value = h
  dischargeId.value = h.id
  dischargeQuery.value = h.patient_name
  dischargeResults.value = []
}

function clearPatient() {
  selectedPatient.value = null
  form.value.patient_id = ''
  patientQuery.value = ''
  patientResults.value = []
}

function clearDoctor() {
  selectedDoctor.value = null
  form.value.referring_doctor_id = ''
  doctorQuery.value = ''
  doctorResults.value = []
}

function clearBed() {
  selectedBed.value = null
  form.value.bed_id = ''
  bedQuery.value = ''
}

function clearDischarge() {
  selectedDischarge.value = null
  dischargeId.value = ''
  dischargeQuery.value = ''
  dischargeResults.value = []
}

function validateForm() {
  fieldErrors.value = validateFields({
    patient: () => {
      if (!form.value.patient_id) {
        const err = validators.personNameSearch(patientQuery.value, 'Nom du patient')
        if (err) return err
        return 'Cliquez sur le patient dans la liste affichée ci-dessous.'
      }
      return ''
    },
    doctor: () => {
      if (!form.value.referring_doctor_id) {
        const err = validators.personNameSearch(doctorQuery.value, 'Médecin référent')
        if (err) return err
        return 'Cliquez sur le médecin dans la liste affichée ci-dessous.'
      }
      return ''
    },
    bed: () => validators.requiredSelection(form.value.bed_id, 'Lit'),
    expected_discharge_date: () =>
      !form.value.expected_discharge_date ? 'Date de sortie prévue obligatoire.' : '',
    admission_reason: () =>
      validators.medicalText(form.value.admission_reason, "Motif d'admission", { minLength: 5 }),
  })
  return !Object.values(fieldErrors.value).some(Boolean)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [h, m] = await Promise.all([
      api.get('/clinical/hospitalizations/active/'),
      api.get('/clinical/patient-movements/').catch(() => ({ data: [] })),
    ])
    hospitalizations.value = h.data
    movements.value = m.data
    await searchBeds()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function admit() {
  error.value = ''
  success.value = ''
  submitAttempted.value = true
  if (!validateForm()) return
  try {
    await api.post('/clinical/admissions/', form.value)
    form.value = { patient_id: '', bed_id: '', referring_doctor_id: '', expected_discharge_date: '', admission_reason: '' }
    clearPatient()
    clearDoctor()
    clearBed()
    submitAttempted.value = false
    fieldErrors.value = {}
    success.value = 'Patient admis — PDF remis au dossier patient.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Admission échouée.'
  }
}

async function discharge() {
  error.value = ''
  success.value = ''
  if (!dischargeId.value) {
    error.value = dischargeQuery.value.trim()
      ? 'Sélectionnez le patient hospitalisé dans la liste.'
      : 'Saisissez le nom du patient à sortir.'
    return
  }
  try {
    await api.post('/clinical/discharges/', { hospitalization_id: dischargeId.value })
    clearDischarge()
    success.value = 'Sortie enregistrée — PDF disponible pour le patient.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Sortie échouée.'
  }
}

function openEdit(h) {
  editTarget.value = h
  editForm.value = { admission_date: toLocalInput(h.admission_date), reason: '' }
  editModalOpen.value = true
}

async function saveAdmissionDate() {
  if (!editTarget.value) return
  error.value = ''
  success.value = ''
  try {
    await api.patch(`/clinical/hospitalizations/${editTarget.value.id}/admission-date/`, {
      admission_date: new Date(editForm.value.admission_date).toISOString(),
      reason: editForm.value.reason,
    })
    editModalOpen.value = false
    success.value = "Date d'admission corrigée — historique et PDF mis à jour."
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Correction échouée.'
  }
}

async function cancelAdmission(h) {
  const reason = window.prompt(
    `Annuler l'admission de ${h.patient_name} ?\nIndiquez le motif (ex. erreur de saisie) :`,
    cancelReason.value || "Erreur sur l'heure d'admission",
  )
  if (reason === null) return
  error.value = ''
  success.value = ''
  try {
    await api.delete(`/clinical/hospitalizations/${h.id}/cancel-admission/?reason=${encodeURIComponent(reason)}`)
    success.value = 'Admission annulée — lit libéré, historique conservé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Annulation échouée.'
  }
}

async function downloadPdf(movement) {
  if (!movement.document_id) return
  try {
    const response = await api.get(`/documents/${movement.document_id}/download/`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${movement.event_type_label}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Téléchargement impossible.'
  }
}

const showPatientList = computed(
  () => patientResults.value.length && !selectedPatient.value && !searchingPatient.value,
)
const showDoctorList = computed(
  () => doctorResults.value.length && !selectedDoctor.value && !searchingDoctor.value,
)
const showBedList = computed(
  () => bedResults.value.length && !selectedBed.value && !searchingBed.value && bedQuery.value.trim().length >= 1,
)
const showDischargeList = computed(
  () => dischargeResults.value.length && !selectedDischarge.value && !searchingDischarge.value,
)

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Admissions & logistique"
      subtitle="Saisissez le nom du patient, du médecin et du lit — historique PDF signé"
    />

    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <form @submit.prevent="admit" class="card card-body mb-6 space-y-5">
        <h3 class="font-semibold text-lg">Nouvelle admission</h3>

        <!-- Patient -->
        <div class="space-y-2">
          <FormField
            label="Nom du patient à admettre"
            required
            :error="submitAttempted ? fieldErrors.patient : ''"
            hint="Saisissez au moins 2 lettres, puis cliquez sur le bon patient dans la liste."
          >
            <input
              v-model="patientQuery"
              type="search"
              class="form-input"
              placeholder="Ex. Bayendat, Kouassi…"
              autocomplete="off"
              @keydown="blockDigitsInName"
              @paste="onNamePaste('patient', $event)"
              @input="onPatientInput"
            />
          </FormField>
          <p v-if="searchingPatient" class="text-xs text-slate-500">Recherche dans le registre…</p>
          <ul
            v-if="showPatientList"
            class="border border-primary-200 rounded-lg divide-y divide-slate-100 max-h-48 overflow-y-auto bg-white shadow-sm"
          >
            <li v-for="p in patientResults" :key="p.id">
              <button
                type="button"
                class="w-full text-left px-3 py-2.5 text-sm hover:bg-primary-50"
                @click="selectPatient(p)"
              >
                <span class="font-medium">{{ p.last_name }} {{ p.first_name }}</span>
                <span class="text-slate-500 text-xs block">
                  Né(e) le {{ new Date(p.date_of_birth).toLocaleDateString('fr-FR') }}
                  <span v-if="p.phone"> — {{ p.phone }}</span>
                </span>
              </button>
            </li>
          </ul>
          <div v-if="selectedPatient" class="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm flex justify-between gap-2">
            <div>
              <p class="text-xs font-semibold text-emerald-700 uppercase mb-0.5">Patient sélectionné</p>
              <p class="font-medium text-emerald-900">{{ patientLabel(selectedPatient) }}</p>
            </div>
            <button type="button" class="text-xs text-emerald-800 hover:underline shrink-0" @click="clearPatient">Changer</button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Médecin -->
          <div class="space-y-2">
            <FormField
              label="Médecin référent"
              required
              :error="submitAttempted ? fieldErrors.doctor : ''"
              hint="Nom du médecin traitant"
            >
              <input
                v-model="doctorQuery"
                type="search"
                class="form-input"
                placeholder="Ex. Martin…"
                autocomplete="off"
                @keydown="blockDigitsInName"
                @paste="onNamePaste('doctor', $event)"
                @input="onDoctorInput"
              />
            </FormField>
            <ul v-if="showDoctorList" class="border rounded-lg divide-y max-h-40 overflow-y-auto text-sm">
              <li v-for="d in doctorResults" :key="d.id">
                <button type="button" class="w-full text-left px-3 py-2 hover:bg-slate-50" @click="selectDoctor(d)">
                  Dr. {{ d.last_name }} {{ d.first_name }}
                </button>
              </li>
            </ul>
            <p v-if="selectedDoctor" class="text-xs text-emerald-700">
              ✓ {{ doctorLabel(selectedDoctor) }}
              <button type="button" class="ml-2 underline" @click="clearDoctor">Changer</button>
            </p>
          </div>

          <!-- Lit -->
          <div class="space-y-2">
            <FormField
              label="Lit disponible"
              required
              :error="submitAttempted ? fieldErrors.bed : ''"
              hint="Service, chambre ou numéro de lit"
            >
              <input
                v-model="bedQuery"
                type="search"
                class="form-input"
                placeholder="Ex. Urgences, ch. 3…"
                autocomplete="off"
                @input="onBedInput"
                @focus="searchBeds"
              />
            </FormField>
            <ul v-if="showBedList" class="border rounded-lg divide-y max-h-40 overflow-y-auto text-sm">
              <li v-for="b in bedResults" :key="b.id">
                <button type="button" class="w-full text-left px-3 py-2 hover:bg-slate-50" @click="selectBed(b)">
                  {{ bedLabel(b) }}
                </button>
              </li>
            </ul>
            <p v-if="selectedBed" class="text-xs text-emerald-700">
              ✓ {{ bedLabel(selectedBed) }}
              <button type="button" class="ml-2 underline" @click="clearBed">Changer</button>
            </p>
          </div>

          <label>
            <span class="form-label">Sortie prévue</span>
            <input v-model="form.expected_discharge_date" type="date" class="form-input" required />
            <p v-if="submitAttempted && fieldErrors.expected_discharge_date" class="text-xs text-red-600 mt-1">
              {{ fieldErrors.expected_discharge_date }}
            </p>
          </label>
        </div>

        <FormField
          label="Motif d'admission"
          required
          :error="submitAttempted ? fieldErrors.admission_reason : ''"
        >
          <input
            v-model="form.admission_reason"
            class="form-input"
            placeholder="Motif clinique ou administratif (min. 5 caractères)"
          />
        </FormField>

        <button type="submit" class="btn-primary w-full sm:w-auto">Admettre le patient</button>
      </form>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <form @submit.prevent="discharge" class="card card-body lg:col-span-1 space-y-3">
          <h3 class="font-semibold">Sortie patient</h3>
          <FormField label="Nom du patient" hint="Saisissez le nom puis sélectionnez dans la liste">
            <input
              v-model="dischargeQuery"
              type="search"
              class="form-input"
              placeholder="Ex. Bayendat…"
              autocomplete="off"
              @keydown="blockDigitsInName"
              @paste="onNamePaste('discharge', $event)"
              @input="onDischargeInput"
            />
          </FormField>
          <ul v-if="showDischargeList" class="border rounded-lg divide-y max-h-36 overflow-y-auto text-sm">
            <li v-for="h in dischargeResults" :key="h.id">
              <button type="button" class="w-full text-left px-3 py-2 hover:bg-slate-50" @click="selectDischarge(h)">
                <span class="font-medium">{{ h.patient_name }}</span>
                <span class="text-slate-500 text-xs block">{{ h.admission_reason }}</span>
              </button>
            </li>
          </ul>
          <p v-if="selectedDischarge" class="text-xs text-emerald-700">
            ✓ {{ selectedDischarge.patient_name }}
            <button type="button" class="ml-2 underline" @click="clearDischarge">Changer</button>
          </p>
          <button type="submit" class="btn-secondary w-full border-slate-700 !text-slate-700">Enregistrer sortie</button>
          <p class="text-xs text-slate-500">Un PDF signé sera ajouté au dossier patient.</p>
        </form>

        <div class="lg:col-span-2">
          <h3 class="font-semibold text-lg mb-4">Hospitalisations actives ({{ hospitalizations.length }})</h3>
          <div v-if="hospitalizations.length" class="card divide-y divide-slate-100">
            <div v-for="h in hospitalizations" :key="h.id" class="px-5 py-4 flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
              <div>
                <p class="font-semibold">{{ h.patient_name }}</p>
                <p class="text-sm text-slate-500 mt-0.5">{{ h.admission_reason }}</p>
                <p class="text-xs text-slate-400 mt-1">
                  Admis le {{ fmtDateTime(h.admission_date) }}
                  <span v-if="h.department_name"> — {{ h.department_name }}, ch. {{ h.room_number }}, lit {{ h.bed_label }}</span>
                </p>
              </div>
              <div class="flex flex-wrap items-center gap-2 shrink-0">
                <StatusBadge :status="h.status" />
                <button type="button" class="text-xs font-medium text-primary-700 hover:underline" @click="openEdit(h)">
                  Corriger l'heure
                </button>
                <button type="button" class="text-xs font-medium text-red-600 hover:underline" @click="cancelAdmission(h)">
                  Annuler
                </button>
              </div>
            </div>
          </div>
          <EmptyState v-else title="Aucune hospitalisation active" icon="🛏️" />
        </div>
      </div>

      <section v-if="movements.length" class="card card-body">
        <h3 class="font-semibold text-lg mb-1">Historique admissions / sorties / transferts</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-slate-500 border-b">
                <th class="py-2 pr-3">Date</th>
                <th class="py-2 pr-3">Patient</th>
                <th class="py-2 pr-3">Événement</th>
                <th class="py-2 pr-3">Par</th>
                <th class="py-2">PDF</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in movements" :key="m.id" class="border-b border-slate-50">
                <td class="py-2.5 pr-3 whitespace-nowrap">{{ fmtDateTime(m.event_at) }}</td>
                <td class="py-2.5 pr-3">{{ m.patient_name }}</td>
                <td class="py-2.5 pr-3">{{ m.event_type_label }}</td>
                <td class="py-2.5 pr-3 text-slate-600">{{ m.performed_by_name || '—' }}</td>
                <td class="py-2.5">
                  <button
                    v-if="m.document_id"
                    type="button"
                    class="text-primary text-xs font-medium hover:underline"
                    @click="downloadPdf(m)"
                  >
                    Télécharger
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <Modal :open="editModalOpen" title="Corriger l'heure d'admission" @close="editModalOpen = false">
      <p v-if="editTarget" class="text-sm text-slate-600 mb-4">
        Patient : <strong>{{ editTarget.patient_name }}</strong>
      </p>
      <label class="block mb-4">
        <span class="form-label">Nouvelle date et heure</span>
        <input v-model="editForm.admission_date" type="datetime-local" class="form-input" required />
      </label>
      <label class="block mb-4">
        <span class="form-label">Motif de correction (optionnel)</span>
        <input v-model="editForm.reason" class="form-input" placeholder="Ex. erreur de saisie à l'accueil" />
      </label>
      <div class="flex gap-2 justify-end">
        <button type="button" class="btn-secondary" @click="editModalOpen = false">Annuler</button>
        <button type="button" class="btn-primary" @click="saveAdmissionDate">Enregistrer</button>
      </div>
    </Modal>
  </div>
</template>
