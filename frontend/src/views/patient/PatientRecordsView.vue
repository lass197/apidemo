<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/client'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import LoadingState from '../../components/ui/LoadingState.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import StatusBadge from '../../components/ui/StatusBadge.vue'
import { formatMoney } from '../../composables/currency'
import { MOBILE_MONEY_METHODS } from '../../constants/mobileMoney'

const auth = useAuthStore()
const tab = ref('documents')
const loading = ref(true)
const error = ref('')
const invoiceSuccess = ref('')

const patient = ref(null)
const documents = ref([])
const careTasks = ref([])
const chatMessages = ref([])
const reminders = ref([])
const invoices = ref([])
const chatInput = ref('')
const doctors = ref([])
const selectedDoctorId = ref('')
const downloadingCard = ref(false)
const declaringId = ref('')
const declareForm = ref({
  phone_number: '',
  method: 'AIRTEL',
  transaction_reference: '',
})

async function loadDoctors() {
  const { data } = await api.get('/hr/doctors/')
  doctors.value = data
  if (!selectedDoctorId.value && data.length) {
    selectedDoctorId.value = data[0].id
  }
}

async function downloadIdentityCard() {
  if (!patient.value) return
  downloadingCard.value = true
  error.value = ''
  try {
    const params = selectedDoctorId.value ? { doctor_id: selectedDoctorId.value } : {}
    const response = await api.get('/clinical/patients/me/identity-pdf/', {
      params,
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `carte-patient-${patient.value.last_name}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Génération de la carte patient impossible.'
  } finally {
    downloadingCard.value = false
  }
}

async function loadInvoices() {
  try {
    const { data } = await api.get('/billing/invoices/mine/')
    invoices.value = data
  } catch {
    invoices.value = []
  }
}

async function declareInvoice(invoiceId, declaration) {
  invoiceSuccess.value = ''
  error.value = ''
  if (!declareForm.value.phone_number.trim() || declareForm.value.phone_number.trim().length < 8) {
    error.value = 'Saisissez votre numéro Mobile Money (Airtel / MTN).'
    return
  }
  declaringId.value = invoiceId
  try {
    await api.post(`/billing/invoices/mine/${invoiceId}/declare/`, {
      phone_number: declareForm.value.phone_number.trim(),
      method: declareForm.value.method,
      declaration,
      transaction_reference: declareForm.value.transaction_reference.trim(),
    })
    invoiceSuccess.value = declaration === 'PAID'
      ? 'Paiement déclaré — la facture a été mise à jour.'
      : 'Déclaration impayée enregistrée.'
    await loadInvoices()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Déclaration impossible.'
  } finally {
    declaringId.value = ''
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: p } = await api.get('/clinical/patients/me/')
    patient.value = p
    declareForm.value.phone_number = p.phone || ''
    await loadDoctors()
    const results = await Promise.allSettled([
      api.get(`/documents/?patient_id=${p.id}`),
      api.get(`/clinical/care-tasks/patient/${p.id}/`),
      api.get(`/hr/chat/${p.id}/`),
      api.get(`/hr/reminders/patient/${p.id}/`),
      api.get('/billing/invoices/mine/'),
    ])
    if (results[0].status === 'fulfilled') documents.value = results[0].value.data
    if (results[1].status === 'fulfilled') careTasks.value = results[1].value.data
    if (results[2].status === 'fulfilled') chatMessages.value = results[2].value.data
    if (results[3].status === 'fulfilled') reminders.value = results[3].value.data
    if (results[4].status === 'fulfilled') invoices.value = results[4].value.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur chargement dossier.'
  } finally {
    loading.value = false
  }
}

async function downloadDoc(doc) {
  const response = await api.get(`/documents/${doc.id}/download/`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = doc.title || 'document'
  a.click()
  URL.revokeObjectURL(url)
}

async function sendChat() {
  if (!chatInput.value.trim() || !patient.value) return
  await api.post('/hr/chat/', { patient_id: patient.value.id, content: chatInput.value.trim() })
  chatInput.value = ''
  const { data } = await api.get(`/hr/chat/${patient.value.id}/`)
  chatMessages.value = data
}

onMounted(load)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-slate-900 mb-1">Mon dossier médical</h1>
    <p class="text-slate-500 text-sm mb-4">Carte patient PDF, documents, soins et communication</p>

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
    <AlertBanner v-if="invoiceSuccess" type="success" class="mb-4">{{ invoiceSuccess }}</AlertBanner>

    <div class="flex gap-1 mb-4 overflow-x-auto pb-1">
      <button
        v-for="t in [
          { id: 'documents', label: 'Documents' },
          { id: 'invoices', label: 'Factures' },
          { id: 'care', label: 'Soins' },
          { id: 'chat', label: 'Médecin' },
          { id: 'reminders', label: 'Rappels' },
        ]"
        :key="t.id"
        type="button"
        class="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition"
        :class="tab === t.id ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-600'"
        @click="tab = t.id"
      >{{ t.label }}</button>
    </div>

    <LoadingState v-if="loading" />

    <template v-else>
      <div class="card card-body mb-4 bg-slate-50 border border-slate-200">
        <p class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">Identité dossier</p>
        <p class="font-semibold text-slate-900">{{ patient.last_name }} {{ patient.first_name }}</p>
        <p class="text-xs text-slate-500 mt-1">N° dossier : {{ patient.id }}</p>
        <p v-if="patient.email" class="text-xs text-slate-500">{{ patient.email }}</p>
      </div>

      <div v-if="tab === 'documents'">
        <div class="card card-body mb-5 bg-teal-50/80 border border-teal-100">
          <h2 class="font-semibold text-slate-900 mb-1">Carte patient (PDF + QR code)</h2>
          <p class="text-sm text-slate-600 mb-4">
            Générez votre carte depuis votre dossier : identifiants dans le PDF. En scannant le QR code,
            le personnel voit vos diagnostics CIM-10, les notes du médecin et les ordonnances.
          </p>
          <div class="flex flex-wrap gap-3 items-end">
            <div class="flex-1 min-w-[12rem]">
              <label class="block text-xs font-medium text-slate-600 mb-1">Médecin référent</label>
              <select v-model="selectedDoctorId" class="form-select w-full">
                <option v-for="d in doctors" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
            </div>
            <button
              type="button"
              class="btn-primary shrink-0"
              :disabled="!selectedDoctorId || downloadingCard"
              @click="downloadIdentityCard"
            >
              {{ downloadingCard ? 'Génération…' : 'Télécharger la carte PDF' }}
            </button>
          </div>
        </div>

        <h3 class="text-sm font-semibold text-slate-800 mb-2">Autres documents</h3>
        <EmptyState v-if="!documents.length" title="Aucun document" description="Vos résultats et factures apparaîtront ici." />
        <div v-else class="space-y-2">
          <div v-for="d in documents" :key="d.id" class="card card-body flex justify-between items-center !py-3">
            <div>
              <p class="font-medium text-sm">{{ d.title }}</p>
              <p class="text-xs text-slate-400">{{ d.document_type }} · {{ new Date(d.created_at).toLocaleDateString('fr-FR') }}</p>
            </div>
            <button type="button" class="text-teal-700 text-xs font-medium hover:underline" @click="downloadDoc(d)">Télécharger</button>
          </div>
        </div>
      </div>

      <div v-if="tab === 'invoices'">
        <p class="text-sm text-slate-600 mb-4">
          Validez vos factures depuis votre téléphone : saisissez votre numéro Airtel ou MTN, puis indiquez si vous avez payé ou non.
        </p>
        <EmptyState v-if="!invoices.length" title="Aucune facture" description="Les factures créées par le secrétariat apparaîtront ici." />
        <div v-else class="space-y-4">
          <div v-for="inv in invoices" :key="inv.id" class="card card-body">
            <div class="flex flex-wrap justify-between gap-2 mb-2">
              <p class="font-mono font-bold text-teal-800">{{ inv.invoice_number }}</p>
              <StatusBadge :status="inv.status" />
            </div>
            <p class="text-sm">Part patient : <strong>{{ formatMoney(inv.patient_amount) }}</strong></p>
            <p class="text-sm" :class="parseFloat(inv.balance_due) > 0 ? 'text-red-700' : 'text-emerald-700'">
              Reste dû : <strong>{{ formatMoney(inv.balance_due) }}</strong>
            </p>
            <p v-if="inv.patient_declaration" class="text-xs text-slate-500 mt-2">
              <template v-if="inv.patient_declaration.status === 'PAID'">
                ✓ Vous avez déclaré payé ({{ inv.patient_declaration.phone_number }})
              </template>
              <template v-else>
                ✗ Vous avez déclaré impayé ({{ inv.patient_declaration.phone_number }})
              </template>
            </p>
            <div
              v-if="parseFloat(inv.balance_due) > 0 && inv.status !== 'PAID'"
              class="mt-4 pt-4 border-t border-slate-100 space-y-3"
            >
              <label class="block">
                <span class="form-label">N° Mobile Money</span>
                <input v-model="declareForm.phone_number" type="tel" class="form-input" placeholder="06 XX XX XX XX" />
              </label>
              <label class="block">
                <span class="form-label">Réseau</span>
                <select v-model="declareForm.method" class="form-select">
                  <option v-for="m in MOBILE_MONEY_METHODS" :key="m.value" :value="m.value">{{ m.label }}</option>
                </select>
              </label>
              <label class="block">
                <span class="form-label">Réf. transaction (optionnel)</span>
                <input v-model="declareForm.transaction_reference" class="form-input" placeholder="ID reçu après paiement" />
              </label>
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="btn-primary"
                  :disabled="declaringId === inv.id"
                  @click="declareInvoice(inv.id, 'PAID')"
                >
                  {{ declaringId === inv.id ? 'Envoi…' : 'J\'ai payé — valider' }}
                </button>
                <button
                  type="button"
                  class="btn-secondary"
                  :disabled="declaringId === inv.id"
                  @click="declareInvoice(inv.id, 'UNPAID')"
                >
                  Je n'ai pas payé
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="tab === 'care'">
        <EmptyState v-if="!careTasks.length" title="Aucun soin enregistré" />
        <div v-else class="space-y-2">
          <div v-for="t in careTasks" :key="t.id" class="card card-body !py-3 text-sm">
            <div class="flex justify-between"><span class="font-medium">{{ t.task_type }}</span><StatusBadge :status="t.status" /></div>
            <p class="text-slate-500 text-xs mt-1">{{ t.notes }}</p>
          </div>
        </div>
      </div>

      <div v-if="tab === 'chat'">
        <div class="card card-body mb-3 max-h-64 overflow-y-auto space-y-2">
          <p v-if="!chatMessages.length" class="text-sm text-slate-400 text-center py-4">Envoyez un message à l'équipe médicale</p>
          <div
            v-for="m in chatMessages"
            :key="m.id"
            class="text-sm px-3 py-2 rounded-xl max-w-[85%]"
            :class="m.sender_id === auth.user?.id ? 'bg-teal-100 ml-auto' : 'bg-slate-100'"
          >{{ m.content }}</div>
        </div>
        <form @submit.prevent="sendChat" class="flex gap-2">
          <input v-model="chatInput" class="form-input flex-1" placeholder="Votre message…" />
          <button type="submit" class="btn-primary shrink-0">Envoyer</button>
        </form>
      </div>

      <div v-if="tab === 'reminders'">
        <EmptyState v-if="!reminders.length" title="Aucun rappel médicament" />
        <div v-else class="space-y-2">
          <div v-for="r in reminders" :key="r.id" class="card card-body !py-3 flex justify-between text-sm">
            <div>
              <p class="font-medium">{{ r.medicine_name }}</p>
              <p class="text-xs text-slate-500">{{ r.dosage }} — {{ r.schedule_time }}</p>
            </div>
            <span class="text-xs text-teal-600">{{ r.is_active ? 'Actif' : 'Inactif' }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
