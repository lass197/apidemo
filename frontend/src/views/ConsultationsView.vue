<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'

const prescriptions = ref([])
const lastPrescriptionId = ref('')
const hospitalizations = ref([])
const icd10 = ref([])
const selectedHosp = ref('')
const form = ref({ symptoms: '', clinical_notes: '', icd10_code_ids: [] })
const prescForm = ref({ consultation_id: '', instructions: '', items: [{ medicine_name: '', dosage: '', frequency: '' }] })
const message = ref('')
const error = ref('')

async function load() {
  const [h, icd] = await Promise.all([
    api.get('/clinical/hospitalizations/active/'),
    api.get('/clinical/icd10/'),
  ])
  hospitalizations.value = h.data
  icd10.value = icd.data
}

async function createConsultation() {
  error.value = ''
  try {
    const { data } = await api.post('/clinical/consultations/', {
      hospitalization_id: selectedHosp.value,
      ...form.value,
    })
    prescForm.value.consultation_id = data.id
    message.value = 'Consultation enregistrée.'
    form.value = { symptoms: '', clinical_notes: '', icd10_code_ids: [] }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur consultation'
  }
}

async function createPrescription() {
  error.value = ''
  try {
    const { data } = await api.post('/clinical/prescriptions/', prescForm.value)
    lastPrescriptionId.value = data.id
    message.value = 'Prescription créée (brouillon).'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur prescription'
  }
}

async function validatePrescription() {
  if (!lastPrescriptionId.value) {
    error.value = 'Créez d\'abord une ordonnance.'
    return
  }
  error.value = ''
  try {
    const { data } = await api.post(`/clinical/prescriptions/${lastPrescriptionId.value}/validate/`)
    message.value = data.stock_alerts?.length
      ? `Validée. Alertes stock : ${data.stock_alerts.join(', ')}`
      : 'Prescription validée et verrouillée.'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Validation échouée'
  }
}

function addPrescLine() {
  prescForm.value.items.push({ medicine_name: '', dosage: '', frequency: '' })
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Consultations médicales" subtitle="Diagnostic CIM-10, prescriptions électroniques" />

    <AlertBanner v-if="message" type="success">{{ message }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="card card-body">
        <h3 class="font-semibold text-lg mb-4">Nouvelle consultation</h3>
        <label class="block mb-3">
          <span class="form-label">Hospitalisation active</span>
          <select v-model="selectedHosp" class="form-select" required>
            <option value="">Sélectionner…</option>
            <option v-for="h in hospitalizations" :key="h.id" :value="h.id">{{ h.patient_name }} — {{ h.admission_reason }}</option>
          </select>
        </label>
        <label class="block mb-3">
          <span class="form-label">Symptômes</span>
          <textarea v-model="form.symptoms" class="form-input h-20 resize-none" required />
        </label>
        <label class="block mb-3">
          <span class="form-label">Notes cliniques</span>
          <textarea v-model="form.clinical_notes" class="form-input h-16 resize-none" />
        </label>
        <div class="mb-4">
          <span class="form-label">Codes CIM-10</span>
          <div class="max-h-36 overflow-y-auto border border-slate-200 rounded-xl p-3 space-y-2 bg-slate-50/50">
            <label v-for="c in icd10" :key="c.id" class="flex items-start gap-2 text-sm cursor-pointer hover:bg-white rounded-lg p-1">
              <input type="checkbox" :value="c.id" v-model="form.icd10_code_ids" class="mt-0.5" />
              <span><strong class="text-primary">{{ c.code }}</strong> — {{ c.description }}</span>
            </label>
          </div>
        </div>
        <button type="button" @click="createConsultation" :disabled="!selectedHosp" class="btn-primary w-full">
          Enregistrer consultation
        </button>
      </div>

      <div class="card card-body">
        <h3 class="font-semibold text-lg mb-4">Prescription électronique</h3>
        <label class="block mb-3">
          <span class="form-label">ID consultation</span>
          <input v-model="prescForm.consultation_id" class="form-input font-mono text-sm bg-slate-50" readonly placeholder="Auto après consultation" />
        </label>
        <div class="space-y-2 mb-3">
          <div v-for="(item, i) in prescForm.items" :key="i" class="grid grid-cols-3 gap-2">
            <input v-model="item.medicine_name" placeholder="Médicament" class="form-input !py-2 text-sm" />
            <input v-model="item.dosage" placeholder="Dosage" class="form-input !py-2 text-sm" />
            <input v-model="item.frequency" placeholder="Fréquence" class="form-input !py-2 text-sm" />
          </div>
        </div>
        <button type="button" @click="addPrescLine" class="btn-secondary w-full mb-3 text-xs">+ Ligne médicament</button>
        <label class="block mb-4">
          <span class="form-label">Instructions</span>
          <textarea v-model="prescForm.instructions" class="form-input h-16 resize-none" />
        </label>
        <button type="button" @click="createPrescription" class="btn-primary w-full mb-2">Créer ordonnance</button>
        <button type="button" @click="validatePrescription" class="btn-secondary w-full border-primary text-primary">
          Valider (verrouiller + pharmacie)
        </button>
      </div>
    </div>
  </div>
</template>
