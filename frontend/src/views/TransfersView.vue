<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import FormField from '../components/ui/FormField.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import {
  validators,
  blockDigitsInName,
  sanitizeNamePaste,
  validateFields,
  hasErrors,
} from '../composables/useFormValidation'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const tab = ref('inter')
const hospitalizations = ref([])
const beds = ref([])
const partnerHospitals = ref([])
const interTransfers = ref([])
const error = ref('')
const success = ref('')
const loading = ref(true)
const transferForm = ref({ hospitalization_id: '', to_bed_id: '', reason: '' })
const interForm = ref({
  hospitalization_id: '',
  partner_hospital_id: '',
  reason: '',
  clinical_summary: '',
  urgency: 'NORMAL',
  contact_phone: '',
})

const interPatientQuery = ref('')
const internalPatientQuery = ref('')
const interPatientResults = ref([])
const internalPatientResults = ref([])
const searchingInterPatient = ref(false)
const searchingInternalPatient = ref(false)
const partnerQuery = ref('')
const bedQuery = ref('')
const interFieldErrors = ref({})
const internalFieldErrors = ref({})
const interSubmitAttempted = ref(false)
const internalSubmitAttempted = ref(false)

let interSearchTimer = null
let internalSearchTimer = null

const availablePartners = computed(() => partnerHospitals.value.filter((h) => h.can_receive))
const pendingTransfers = computed(() => interTransfers.value.filter((t) => t.status === 'PENDING'))

const selectedPartner = computed(() =>
  partnerHospitals.value.find((h) => h.id === interForm.value.partner_hospital_id),
)

const selectedInterHospitalization = computed(() => {
  if (!interForm.value.hospitalization_id) return null
  return (
    hospitalizations.value.find((h) => h.id === interForm.value.hospitalization_id)
    || interPatientResults.value.find((h) => h.hospitalization_id === interForm.value.hospitalization_id)
  )
})

const selectedInternalHospitalization = computed(() => {
  if (!transferForm.value.hospitalization_id) return null
  return (
    hospitalizations.value.find((h) => h.id === transferForm.value.hospitalization_id)
    || internalPatientResults.value.find((h) => h.hospitalization_id === transferForm.value.hospitalization_id)
  )
})

const interPatientQueryValid = computed(
  () => !validators.personNameSearch(interPatientQuery.value, 'Nom du patient'),
)

const internalPatientQueryValid = computed(
  () => !validators.personNameSearch(internalPatientQuery.value, 'Nom du patient'),
)

const interNeedsPatientPick = computed(
  () =>
    !interForm.value.hospitalization_id
    && interPatientResults.value.some((p) => p.is_hospitalized)
    && !searchingInterPatient.value,
)

const internalNeedsPatientPick = computed(
  () =>
    !transferForm.value.hospitalization_id
    && internalPatientResults.value.some((p) => p.is_hospitalized)
    && !searchingInternalPatient.value,
)

const interRegisteredOnly = computed(
  () =>
    interPatientResults.value.length > 0
    && !interPatientResults.value.some((p) => p.is_hospitalized)
    && !searchingInterPatient.value,
)

const internalRegisteredOnly = computed(
  () =>
    internalPatientResults.value.length > 0
    && !internalPatientResults.value.some((p) => p.is_hospitalized)
    && !searchingInternalPatient.value,
)

const interNoPatientResults = computed(
  () =>
    !interForm.value.hospitalization_id
    && interPatientQueryValid.value
    && !searchingInterPatient.value
    && interPatientResults.value.length === 0
    && interPatientQuery.value.trim().length >= 2,
)

const internalNoPatientResults = computed(
  () =>
    !transferForm.value.hospitalization_id
    && internalPatientQueryValid.value
    && !searchingInternalPatient.value
    && internalPatientResults.value.length === 0
    && internalPatientQuery.value.trim().length >= 2,
)

const filteredPartners = computed(() => {
  const q = partnerQuery.value.trim().toLowerCase()
  if (!q) return availablePartners.value
  return availablePartners.value.filter(
    (h) =>
      h.name.toLowerCase().includes(q)
      || h.city.toLowerCase().includes(q)
      || (h.specialties || '').toLowerCase().includes(q),
  )
})

const filteredBeds = computed(() => {
  const q = bedQuery.value.trim().toLowerCase()
  if (!q) return beds.value
  return beds.value.filter(
    (b) =>
      b.department_name.toLowerCase().includes(q)
      || b.room_number.toLowerCase().includes(q)
      || b.label.toLowerCase().includes(q),
  )
})

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

async function searchPatients(query, target) {
  const term = query.trim()
  if (term.length < 2) {
    if (target === 'inter') interPatientResults.value = []
    else internalPatientResults.value = []
    return
  }
  if (target === 'inter') searchingInterPatient.value = true
  else searchingInternalPatient.value = true
  try {
    const { data } = await api.get('/clinical/transfers/patient-search/', {
      params: { search: term },
    })
    if (target === 'inter') interPatientResults.value = data
    else internalPatientResults.value = data
  } catch {
    if (target === 'inter') interPatientResults.value = []
    else internalPatientResults.value = []
  } finally {
    if (target === 'inter') searchingInterPatient.value = false
    else searchingInternalPatient.value = false
  }
}

function onInterPatientInput() {
  interPatientQuery.value = interPatientQuery.value.replace(/\d/g, '')
  if (
    interForm.value.hospitalization_id
    && interPatientQuery.value.trim() !== (selectedInterHospitalization.value?.patient_name || '').trim()
  ) {
    interForm.value.hospitalization_id = ''
  }
  if (interFieldErrors.value.patient) {
    interFieldErrors.value = { ...interFieldErrors.value, patient: '' }
  }
  clearTimeout(interSearchTimer)
  interSearchTimer = setTimeout(() => searchPatients(interPatientQuery.value, 'inter'), 300)
}

function onInternalPatientInput() {
  internalPatientQuery.value = internalPatientQuery.value.replace(/\d/g, '')
  if (
    transferForm.value.hospitalization_id
    && internalPatientQuery.value.trim() !== (selectedInternalHospitalization.value?.patient_name || '').trim()
  ) {
    transferForm.value.hospitalization_id = ''
  }
  if (internalFieldErrors.value.patient) {
    internalFieldErrors.value = { ...internalFieldErrors.value, patient: '' }
  }
  clearTimeout(internalSearchTimer)
  internalSearchTimer = setTimeout(() => searchPatients(internalPatientQuery.value, 'internal'), 300)
}

function onNamePaste(target, event) {
  sanitizeNamePaste(event, (text) => {
    if (target === 'inter') {
      interPatientQuery.value = text
      onInterPatientInput()
    } else {
      internalPatientQuery.value = text
      onInternalPatientInput()
    }
  })
}

function onPartnerQueryPaste(event) {
  sanitizeNamePaste(event, (text) => {
    partnerQuery.value = text
  })
}
function validateInterForm() {
  interFieldErrors.value = validateFields({
    patient: () => {
      if (!interForm.value.hospitalization_id) {
        const nameErr = validators.personNameSearch(interPatientQuery.value, 'Nom du patient')
        if (nameErr) return nameErr
        return 'Cliquez sur un patient dans la liste affichée juste en dessous pour le sélectionner.'
      }
      return ''
    },
    partner_hospital_id: () =>
      validators.requiredSelection(interForm.value.partner_hospital_id, 'Établissement destinataire'),
    partnerQuery: () => validators.optionalLabelSearch(partnerQuery.value, 'Recherche établissement'),
    contact_phone: () => validators.phone(interForm.value.contact_phone),
    reason: () => validators.medicalText(interForm.value.reason, 'Motif médical du transfert'),
    clinical_summary: () =>
      validators.medicalText(interForm.value.clinical_summary, 'Résumé clinique', {
        required: false,
        minLength: 5,
      }),
  })
  return !hasErrors(interFieldErrors.value)
}

function validateInternalForm() {
  internalFieldErrors.value = validateFields({
    patient: () => {
      if (!transferForm.value.hospitalization_id) {
        const nameErr = validators.personNameSearch(internalPatientQuery.value, 'Nom du patient')
        if (nameErr) return nameErr
        return 'Cliquez sur un patient dans la liste affichée juste en dessous pour le sélectionner.'
      }
      return ''
    },
    to_bed_id: () => validators.requiredSelection(transferForm.value.to_bed_id, 'Lit de destination'),
    reason: () => validators.medicalText(transferForm.value.reason, 'Motif médical'),
  })
  return !hasErrors(internalFieldErrors.value)
}

function selectInterPatient(h) {
  if (!h.is_hospitalized || !h.hospitalization_id) return
  interForm.value.hospitalization_id = h.hospitalization_id
  interPatientQuery.value = h.patient_name
  interPatientResults.value = []
  interFieldErrors.value = { ...interFieldErrors.value, patient: '' }
}

function selectInternalPatient(h) {
  if (!h.is_hospitalized || !h.hospitalization_id) return
  transferForm.value.hospitalization_id = h.hospitalization_id
  internalPatientQuery.value = h.patient_name
  internalPatientResults.value = []
  internalFieldErrors.value = { ...internalFieldErrors.value, patient: '' }
}

function clearInterPatient() {
  interForm.value.hospitalization_id = ''
  interPatientQuery.value = ''
  interPatientResults.value = []
}

function clearInternalPatient() {
  transferForm.value.hospitalization_id = ''
  internalPatientQuery.value = ''
  internalPatientResults.value = []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [h, b, p, t] = await Promise.all([
      api.get('/clinical/hospitalizations/active/', { params: { page_size: 100 } }),
      api.get('/clinical/beds/available/'),
      api.get('/clinical/partner-hospitals/'),
      api.get('/clinical/inter-hospital-transfers/'),
    ])
    hospitalizations.value = h.data
    beds.value = b.data
    partnerHospitals.value = p.data
    interTransfers.value = t.data
    const preselect = route.query.partner
    if (preselect && availablePartners.value.some((h) => h.id === preselect)) {
      interForm.value.partner_hospital_id = String(preselect)
      tab.value = 'inter'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function transferInternal() {
  error.value = ''
  success.value = ''
  internalSubmitAttempted.value = true
  if (!validateInternalForm()) return
  try {
    await api.post('/clinical/transfers/', transferForm.value)
    transferForm.value = { hospitalization_id: '', to_bed_id: '', reason: '' }
    internalPatientQuery.value = ''
    bedQuery.value = ''
    internalFieldErrors.value = {}
    internalSubmitAttempted.value = false
    success.value = 'Transfert interne effectué avec succès.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Transfert échoué.'
  }
}

const URGENCY_LABELS = { NORMAL: 'Normale', URGENT: 'Urgente', VITAL: 'Vital (SMUR / réanimation)' }

async function requestInterTransfer() {
  error.value = ''
  success.value = ''
  interSubmitAttempted.value = true
  if (!validateInterForm()) return
  const summaryParts = []
  if (interForm.value.urgency && interForm.value.urgency !== 'NORMAL') {
    summaryParts.push(`Urgence : ${URGENCY_LABELS[interForm.value.urgency] || interForm.value.urgency}`)
  }
  if (interForm.value.contact_phone.trim()) {
    summaryParts.push(`Contact destinataire : ${interForm.value.contact_phone.trim()}`)
  }
  if (interForm.value.clinical_summary.trim()) {
    summaryParts.push(interForm.value.clinical_summary.trim())
  }
  try {
    await api.post('/clinical/inter-hospital-transfers/', {
      hospitalization_id: interForm.value.hospitalization_id,
      partner_hospital_id: interForm.value.partner_hospital_id,
      reason: interForm.value.reason,
      clinical_summary: summaryParts.join('\n\n'),
    })
    interForm.value = {
      hospitalization_id: '',
      partner_hospital_id: '',
      reason: '',
      clinical_summary: '',
      urgency: 'NORMAL',
      contact_phone: '',
    }
    interPatientQuery.value = ''
    partnerQuery.value = ''
    interFieldErrors.value = {}
    interSubmitAttempted.value = false
    success.value = 'Demande transmise au secrétariat pour validation.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Demande de transfert échouée.'
  }
}

watch(
  () => interForm.value.partner_hospital_id,
  (id) => {
    const p = partnerHospitals.value.find((h) => h.id === id)
    if (p && !interForm.value.contact_phone) {
      interForm.value.contact_phone = p.phone || ''
    }
  },
)

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Transferts patients"
      subtitle="Saisissez le nom du patient et complétez le dossier de transfert"
    />

    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <template v-if="auth.hasPerm('clinical.transfer')">
      <div class="flex gap-2 mb-6 border-b border-slate-200">
        <button
          type="button"
          class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="tab === 'inter' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          @click="tab = 'inter'"
        >
          Inter-établissements
        </button>
        <button
          type="button"
          class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="tab === 'internal' ? 'border-primary-600 text-primary-700' : 'border-transparent text-slate-500 hover:text-slate-700'"
          @click="tab = 'internal'"
        >
          Interne (lit / service)
        </button>
      </div>

      <!-- Transfert inter-établissements -->
      <div v-show="tab === 'inter'" class="space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-slate-600">
            Recherchez le patient par nom, choisissez la destination et renseignez le dossier clinique.
          </p>
          <router-link to="/partner-hospitals" class="btn-secondary text-sm">
            Voir tous les hôpitaux partenaires
          </router-link>
        </div>

        <form @submit.prevent="requestInterTransfer" class="card card-body max-w-2xl space-y-4">
          <h3 class="font-semibold text-lg">Dossier de transfert inter-établissement</h3>

          <!-- Patient -->
          <div class="space-y-2">
            <FormField
              label="Nom du patient à transférer"
              required
              :error="interSubmitAttempted ? interFieldErrors.patient : ''"
              hint="Étape 1 : saisissez le nom (lettres uniquement, min. 2 caractères). Étape 2 : cliquez sur un patient hospitalisé. Seuls les patients admis avec un lit actif peuvent être transférés."
            >
              <input
                v-model="interPatientQuery"
                type="search"
                class="form-input"
                :class="{ 'border-red-400 ring-red-100': interSubmitAttempted && interFieldErrors.patient }"
                placeholder="Ex. Martin, Kouassi…"
                autocomplete="off"
                @keydown="blockDigitsInName"
                @paste="onNamePaste('inter', $event)"
                @input="onInterPatientInput"
              />
            </FormField>
            <p v-if="searchingInterPatient" class="text-xs text-slate-500">Recherche dans le registre patients…</p>
            <p
              v-else-if="interNeedsPatientPick"
              class="text-sm text-primary-800 bg-primary-50 border border-primary-200 rounded-lg px-3 py-2.5"
              role="status"
            >
              <span class="font-medium">Étape 2 —</span>
              {{ interPatientResults.filter((p) => p.is_hospitalized).length === 1 ? 'Un patient hospitalisé : cliquez' : `${interPatientResults.filter((p) => p.is_hospitalized).length} patients hospitalisés : cliquez` }}
              sur la ligne du bon patient dans la liste ci-dessous.
            </p>
            <p
              v-else-if="interRegisteredOnly"
              class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5"
              role="status"
            >
              {{ interPatientResults.length }} patient(s) trouvé(s) dans le registre, mais <strong>aucun n'est hospitalisé</strong>.
              Demandez à la secrétaire une admission (menu Admissions) avant de transférer.
            </p>
            <p
              v-else-if="interNoPatientResults"
              class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5"
              role="status"
            >
              Aucun patient enregistré ne correspond à « {{ interPatientQuery.trim() }} ». Vérifiez l'orthographe ou créez le dossier patient d'abord.
            </p>
            <ul
              v-if="interPatientResults.length && !selectedInterHospitalization && !searchingInterPatient"
              class="border-2 rounded-lg divide-y divide-slate-100 max-h-56 overflow-y-auto bg-white shadow-sm"
              :class="interNeedsPatientPick ? 'border-primary-200' : 'border-amber-200'"
            >
              <li v-for="h in interPatientResults" :key="h.patient_id">
                <button
                  v-if="h.is_hospitalized"
                  type="button"
                  class="w-full text-left px-3 py-2.5 text-sm hover:bg-primary-50 transition-colors focus:bg-primary-50 focus:outline-none"
                  @click="selectInterPatient(h)"
                >
                  <span class="font-medium">{{ h.patient_name }}</span>
                  <span class="text-slate-500"> — {{ h.admission_reason }}</span>
                  <span v-if="h.department_name" class="block text-xs text-slate-400 mt-0.5">
                    {{ h.department_name }}, ch. {{ h.room_number }}, lit {{ h.bed_label }}
                  </span>
                  <span class="block text-xs text-emerald-700 mt-0.5">{{ h.status_label }}</span>
                </button>
                <div
                  v-else
                  class="px-3 py-2.5 text-sm bg-slate-50 text-slate-500 cursor-not-allowed"
                  title="Admission requise avant transfert"
                >
                  <span class="font-medium text-slate-600">{{ h.patient_name }}</span>
                  <span class="block text-xs text-amber-700 mt-0.5">{{ h.status_label }}</span>
                </div>
              </li>
            </ul>
            <div
              v-if="selectedInterHospitalization"
              class="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm"
            >
              <div class="flex justify-between gap-2">
                <div>
                  <p class="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">Patient sélectionné</p>
                  <p class="font-medium text-emerald-900">{{ selectedInterHospitalization.patient_name }}</p>
                  <p class="text-emerald-800">{{ selectedInterHospitalization.admission_reason }}</p>
                  <p class="text-xs text-emerald-700 mt-1">
                    <template v-if="selectedInterHospitalization.admission_date">
                      Admis le {{ fmtDate(selectedInterHospitalization.admission_date) }}
                    </template>
                    <span v-if="selectedInterHospitalization.department_name">
                      · {{ selectedInterHospitalization.department_name }}, lit {{ selectedInterHospitalization.bed_label }}
                    </span>
                  </p>
                </div>
                <button type="button" class="text-xs text-emerald-700 underline shrink-0" @click="clearInterPatient">
                  Changer
                </button>
              </div>
            </div>
          </div>

          <!-- Établissement destinataire -->
          <div>
            <FormField
              label="Rechercher un établissement partenaire"
              :error="interFieldErrors.partnerQuery"
              hint="Lettres uniquement (nom, ville, spécialité)."
            >
              <input
                v-model="partnerQuery"
                type="search"
                class="form-input"
                :class="{ 'border-red-400 ring-red-100': interFieldErrors.partnerQuery }"
                placeholder="Nom, ville ou spécialité…"
                autocomplete="off"
                @keydown="blockDigitsInName"
                @paste="onPartnerQueryPaste"
              />
            </FormField>
            <FormField
              class="mt-2"
              label="Établissement destinataire"
              required
              :error="interFieldErrors.partner_hospital_id"
            >
              <select
                v-model="interForm.partner_hospital_id"
                class="form-select"
                :class="{ 'border-red-400 ring-red-100': interFieldErrors.partner_hospital_id }"
              >
                <option value="">Sélectionner l'hôpital de destination…</option>
                <option v-for="h in filteredPartners" :key="h.id" :value="h.id">
                  {{ h.name }} ({{ h.city }}) — {{ h.available_beds }} lit(s) dispo.
                </option>
              </select>
            </FormField>
            <div
              v-if="selectedPartner"
              class="mt-2 p-3 rounded-lg bg-slate-50 text-sm text-slate-700 border border-slate-200"
            >
              <p class="font-medium">{{ selectedPartner.name }}</p>
              <p>{{ selectedPartner.address }}</p>
              <p class="mt-1">{{ selectedPartner.specialties }}</p>
              <p class="mt-1 text-emerald-700">{{ selectedPartner.available_beds }} place(s) restante(s)</p>
            </div>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <FormField label="Urgence du transfert">
              <select v-model="interForm.urgency" class="form-select">
                <option value="NORMAL">Normale</option>
                <option value="URGENT">Urgente</option>
                <option value="VITAL">Vital (SMUR / réanimation)</option>
              </select>
            </FormField>
            <FormField label="Contact établissement destinataire" :error="interFieldErrors.contact_phone">
              <input
                v-model="interForm.contact_phone"
                type="tel"
                class="form-input"
                :class="{ 'border-red-400 ring-red-100': interFieldErrors.contact_phone }"
                placeholder="+242 06 123 45 67"
              />
            </FormField>
          </div>

          <FormField
            label="Motif médical du transfert"
            required
            :error="interFieldErrors.reason"
            hint="Minimum 10 caractères, doit contenir des lettres."
          >
            <textarea
              v-model="interForm.reason"
              class="form-input min-h-[72px]"
              :class="{ 'border-red-400 ring-red-100': interFieldErrors.reason }"
              placeholder="Indication clinique détaillée (ex. besoin de réanimation…)"
            />
          </FormField>

          <FormField
            label="Résumé clinique"
            :error="interFieldErrors.clinical_summary"
            hint="Optionnel — minimum 5 caractères si renseigné."
          >
            <textarea
              v-model="interForm.clinical_summary"
              class="form-input min-h-[100px]"
              :class="{ 'border-red-400 ring-red-100': interFieldErrors.clinical_summary }"
              placeholder="État du patient, traitements, allergies, examens récents…"
            />
          </FormField>

          <button type="submit" class="btn-primary w-full" :disabled="!availablePartners.length">
            Soumettre la demande au secrétariat
          </button>
        </form>

        <section v-if="pendingTransfers.length">
          <h3 class="font-semibold text-lg mb-3">Mes demandes en attente</h3>
          <p class="text-sm text-slate-600 mb-3">
            Le secrétariat validera la demande depuis son interface « Transferts à valider ».
          </p>
          <div class="space-y-3">
            <article
              v-for="t in pendingTransfers"
              :key="t.id"
              class="card card-body"
            >
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="font-medium">{{ t.patient_name }}</p>
                  <p class="text-sm text-slate-600">
                    Vers <strong>{{ t.partner_hospital_name }}</strong> ({{ t.partner_hospital_city }})
                  </p>
                  <p class="text-sm text-slate-500 mt-1">{{ t.reason }}</p>
                  <p class="text-xs text-slate-400 mt-1">
                    Soumis le {{ new Date(t.created_at).toLocaleString('fr-FR') }}
                  </p>
                </div>
                <StatusBadge status="En attente secrétariat" />
              </div>
            </article>
          </div>
        </section>

        <section v-if="interTransfers.filter((t) => t.status !== 'PENDING').length">
          <h3 class="font-semibold text-lg mb-3">Historique récent</h3>
          <div class="overflow-x-auto">
            <table class="data-table w-full">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Destination</th>
                  <th>Statut</th>
                  <th>Validé par</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in interTransfers.filter((x) => x.status !== 'PENDING')" :key="t.id">
                  <td>{{ t.patient_name }}</td>
                  <td>{{ t.partner_hospital_name }}</td>
                  <td><StatusBadge :status="t.status_label" /></td>
                  <td>{{ t.validated_by_name || '—' }}</td>
                  <td>{{ t.validated_at ? new Date(t.validated_at).toLocaleString('fr-FR') : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- Transfert interne -->
      <form v-show="tab === 'internal'" @submit.prevent="transferInternal" class="card card-body max-w-2xl space-y-4">
        <h3 class="font-semibold text-lg">Transfert interne (changement de lit)</h3>

        <div class="space-y-2">
          <FormField
            label="Nom du patient à transférer"
            required
            :error="internalSubmitAttempted ? internalFieldErrors.patient : ''"
            hint="Étape 1 : saisissez le nom (lettres uniquement, min. 2 caractères). Étape 2 : cliquez sur un patient hospitalisé. Seuls les patients admis avec un lit actif peuvent être transférés."
          >
            <input
              v-model="internalPatientQuery"
              type="search"
              class="form-input"
              :class="{ 'border-red-400 ring-red-100': internalSubmitAttempted && internalFieldErrors.patient }"
              placeholder="Ex. Martin, Kouassi…"
              autocomplete="off"
              @keydown="blockDigitsInName"
              @paste="onNamePaste('internal', $event)"
              @input="onInternalPatientInput"
            />
          </FormField>
          <p v-if="searchingInternalPatient" class="text-xs text-slate-500">Recherche dans le registre patients…</p>
          <p
            v-else-if="internalNeedsPatientPick"
            class="text-sm text-primary-800 bg-primary-50 border border-primary-200 rounded-lg px-3 py-2.5"
            role="status"
          >
            <span class="font-medium">Étape 2 —</span>
            {{ internalPatientResults.filter((p) => p.is_hospitalized).length === 1 ? 'Un patient hospitalisé : cliquez' : `${internalPatientResults.filter((p) => p.is_hospitalized).length} patients hospitalisés : cliquez` }}
            sur la ligne du bon patient dans la liste ci-dessous.
          </p>
          <p
            v-else-if="internalRegisteredOnly"
            class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5"
            role="status"
          >
            {{ internalPatientResults.length }} patient(s) trouvé(s), mais aucun n'est hospitalisé. Admission requise (menu Admissions).
          </p>
          <p
            v-else-if="internalNoPatientResults"
            class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5"
            role="status"
          >
            Aucun patient enregistré ne correspond à « {{ internalPatientQuery.trim() }} ».
          </p>
          <ul
            v-if="internalPatientResults.length && !selectedInternalHospitalization && !searchingInternalPatient"
            class="border-2 rounded-lg divide-y divide-slate-100 max-h-56 overflow-y-auto bg-white shadow-sm"
            :class="internalNeedsPatientPick ? 'border-primary-200' : 'border-amber-200'"
          >
            <li v-for="h in internalPatientResults" :key="h.patient_id">
              <button
                v-if="h.is_hospitalized"
                type="button"
                class="w-full text-left px-3 py-2.5 text-sm hover:bg-primary-50 transition-colors focus:bg-primary-50 focus:outline-none"
                @click="selectInternalPatient(h)"
              >
                <span class="font-medium">{{ h.patient_name }}</span>
                <span class="text-slate-500"> — {{ h.admission_reason }}</span>
                <span v-if="h.department_name" class="block text-xs text-slate-400 mt-0.5">
                  {{ h.department_name }}, ch. {{ h.room_number }}, lit {{ h.bed_label }}
                </span>
                <span class="block text-xs text-emerald-700 mt-0.5">{{ h.status_label }}</span>
              </button>
              <div
                v-else
                class="px-3 py-2.5 text-sm bg-slate-50 text-slate-500 cursor-not-allowed"
              >
                <span class="font-medium text-slate-600">{{ h.patient_name }}</span>
                <span class="block text-xs text-amber-700 mt-0.5">{{ h.status_label }}</span>
              </div>
            </li>
          </ul>
          <div
            v-if="selectedInternalHospitalization"
            class="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm"
          >
            <div class="flex justify-between gap-2">
              <div>
                <p class="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">Patient sélectionné</p>
                <p class="font-medium text-emerald-900">{{ selectedInternalHospitalization.patient_name }}</p>
                <p class="text-emerald-800">{{ selectedInternalHospitalization.admission_reason }}</p>
                <p class="text-xs text-emerald-700 mt-1">
                  Lit actuel :
                  {{ selectedInternalHospitalization.department_name || '—' }},
                  ch. {{ selectedInternalHospitalization.room_number || '—' }},
                  lit {{ selectedInternalHospitalization.bed_label || '—' }}
                </p>
              </div>
              <button type="button" class="text-xs text-emerald-700 underline shrink-0" @click="clearInternalPatient">
                Changer
              </button>
            </div>
          </div>
        </div>

        <FormField label="Rechercher un lit de destination" hint="Service, chambre ou libellé de lit.">
          <input
            v-model="bedQuery"
            type="search"
            class="form-input"
            placeholder="Service, numéro de chambre ou lit…"
            autocomplete="off"
          />
        </FormField>
        <FormField label="Lit de destination" required :error="internalFieldErrors.to_bed_id">
          <select
            v-model="transferForm.to_bed_id"
            class="form-select"
            :class="{ 'border-red-400 ring-red-100': internalFieldErrors.to_bed_id }"
          >
            <option value="">Sélectionner le lit…</option>
            <option v-for="b in filteredBeds" :key="b.id" :value="b.id">
              {{ b.department_name }} — Ch.{{ b.room_number }} Lit {{ b.label }}
            </option>
          </select>
        </FormField>

        <FormField
          label="Motif médical"
          required
          :error="internalFieldErrors.reason"
          hint="Minimum 10 caractères, doit contenir des lettres."
        >
          <textarea
            v-model="transferForm.reason"
            class="form-input min-h-[72px]"
            :class="{ 'border-red-400 ring-red-100': internalFieldErrors.reason }"
            placeholder="Indication clinique du transfert interne…"
          />
        </FormField>

        <button type="submit" class="btn-primary w-full">Valider le transfert interne</button>
      </form>
    </template>

    <EmptyState
      v-else
      title="Accès restreint"
      description="La permission clinical.transfer est requise pour effectuer des transferts."
      icon="🔒"
    />
  </div>
</template>
