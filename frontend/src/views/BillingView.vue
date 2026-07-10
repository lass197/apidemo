<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import Modal from '../components/Modal.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import { formatMoney, CURRENCY_FULL } from '../composables/currency'
import { MOBILE_MONEY_METHODS, PAYMENT_PROCEDURE } from '../constants/mobileMoney'

const invoices = ref([])
const hospitalizations = ref([])
const journal = ref([])
const tab = ref('billing')
const loading = ref(true)
const paying = ref(false)
const error = ref('')
const success = ref('')
const payInstantError = ref('')

const payForm = ref({ invoice_id: '', amount: '', method: 'AIRTEL', reference: '' })
const hospForm = ref({ hospitalization_id: '' })
const insuranceInfo = ref(null)
const admissionSearch = ref('')
const loadingAdmissions = ref(false)
const creatingInvoice = ref(false)

const showEdit = ref(false)
const editingInvoice = ref(null)
const editLines = ref([])
const editReason = ref('')
const savingEdit = ref(false)

const SERVICE_TYPES = [
  { value: 'ACT', label: 'Acte médical' },
  { value: 'NIGHT', label: 'Nuitée' },
  { value: 'EXAM', label: 'Examen' },
  { value: 'MEDICINE', label: 'Médicament' },
  { value: 'CONSUMABLE', label: 'Consommable' },
]

const selectedInvoice = computed(() =>
  invoices.value.find((i) => i.id === payForm.value.invoice_id) || null,
)

const selectedBalance = computed(() => {
  if (!selectedInvoice.value) return null
  return Math.round(parseFloat(selectedInvoice.value.balance_due) || 0)
})

const payAmountNum = computed(() => Math.round(parseFloat(payForm.value.amount) || 0))

const payableInvoices = computed(() =>
  invoices.value.filter(
    (i) => i.status !== 'PAID' && i.status !== 'CANCELLED' && Math.round(parseFloat(i.balance_due) || 0) > 0,
  ),
)

const payAmountExceedsBalance = computed(() => {
  if (!selectedInvoice.value || !payForm.value.amount) return false
  return payAmountNum.value > selectedBalance.value
})

const payAmountInvalid = computed(() => payForm.value.amount && payAmountNum.value <= 0)

const canSubmitPayment = computed(() => {
  if (!payForm.value.invoice_id || !payForm.value.amount || !payForm.value.reference.trim()) return false
  if (payAmountExceedsBalance.value || payAmountInvalid.value) return false
  if (selectedInvoice.value && ['PAID', 'CANCELLED'].includes(selectedInvoice.value.status)) return false
  return true
})

const billingKpi = computed(() => {
  const unpaid = invoices.value.filter((i) => parseFloat(i.balance_due) > 0 && i.status !== 'CANCELLED')
  const totalDue = unpaid.reduce((s, i) => s + parseFloat(i.balance_due), 0)
  return {
    total: invoices.value.length,
    unpaidCount: unpaid.length,
    totalDue,
    partial: invoices.value.filter((i) => i.status === 'PARTIAL').length,
    paid: invoices.value.filter((i) => i.status === 'PAID').length,
    admitted: hospitalizations.value.length,
  }
})

const selectedHospitalization = computed(() =>
  hospitalizations.value.find((h) => h.id === hospForm.value.hospitalization_id) || null,
)

const filteredHospitalizations = computed(() => {
  const q = admissionSearch.value.trim().toLowerCase()
  if (!q) return hospitalizations.value
  return hospitalizations.value.filter(
    (h) =>
      h.patient_name?.toLowerCase().includes(q)
      || h.department_name?.toLowerCase().includes(q)
      || h.admission_reason?.toLowerCase().includes(q)
      || h.room_number?.toLowerCase().includes(q)
      || h.bed_label?.toLowerCase().includes(q),
  )
})

const editSubtotal = computed(() =>
  editLines.value.reduce((sum, l) => sum + lineTotal(l), 0).toFixed(2),
)

function isEditable(status) {
  return ['DRAFT', 'ISSUED', 'PARTIAL'].includes(status)
}

function lineTotal(line) {
  const qty = parseFloat(line.quantity) || 0
  const price = parseFloat(line.unit_price) || 0
  return Math.round(qty * price * 100) / 100
}

function apiErrorMessage(e, fallback = 'Erreur.') {
  const d = e.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg || x).join(' ')
  if (d && typeof d === 'object') return JSON.stringify(d)
  return fallback
}

function updateInstantPayError() {
  if (!payForm.value.invoice_id) {
    payInstantError.value = ''
    return
  }
  if (selectedInvoice.value && ['PAID', 'CANCELLED'].includes(selectedInvoice.value.status)) {
    payInstantError.value = 'Cette facture est déjà soldée ou annulée — aucun paiement possible.'
    return
  }
  if (payAmountInvalid.value) {
    payInstantError.value = 'Le montant doit être strictement positif.'
    return
  }
  if (payAmountExceedsBalance.value) {
    payInstantError.value = `Solde insuffisant : reste à payer ${formatMoney(selectedBalance.value)} — vous avez saisi ${formatMoney(payAmountNum.value)}.`
    return
  }
  if (selectedBalance.value === 0 && payForm.value.invoice_id) {
    payInstantError.value = 'Cette facture est déjà soldée (0 FCFA restant).'
    return
  }
  payInstantError.value = ''
}

watch(
  () => [payForm.value.invoice_id, payForm.value.amount, selectedBalance.value],
  updateInstantPayError,
  { immediate: true },
)

function fillFullBalance() {
  if (selectedBalance.value != null && selectedBalance.value > 0) {
    payForm.value.amount = String(Math.round(selectedBalance.value))
    updateInstantPayError()
  }
}

function onInvoiceSelect() {
  payForm.value.amount = ''
  payInstantError.value = ''
  updateInstantPayError()
}

function fmtAdmissionDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

function invoiceForHospitalization(hospId) {
  return invoices.value.find((i) => i.hospitalization_id === hospId && i.status !== 'CANCELLED')
}

async function loadHospitalizations() {
  loadingAdmissions.value = true
  try {
    const { data } = await api.get('/clinical/hospitalizations/active/', {
      params: { search: admissionSearch.value.trim(), page_size: 200 },
    })
    hospitalizations.value = data
  } catch (e) {
    error.value = apiErrorMessage(e, 'Impossible de charger les patients admis.')
  } finally {
    loadingAdmissions.value = false
  }
}

function selectHospitalization(h) {
  hospForm.value.hospitalization_id = h.id
  loadInsurance()
}

let admissionSearchTimer = null
watch(admissionSearch, () => {
  clearTimeout(admissionSearchTimer)
  admissionSearchTimer = setTimeout(loadHospitalizations, 350)
})

async function load() {
  loading.value = true
  try {
    const [inv, j] = await Promise.all([
      api.get('/billing/invoices/'),
      api.get('/billing/accounting/journal/'),
    ])
    invoices.value = inv.data
    journal.value = j.data
    await loadHospitalizations()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function loadInsurance() {
  insuranceInfo.value = null
  const hosp = hospitalizations.value.find((h) => h.id === hospForm.value.hospitalization_id)
  if (!hosp?.patient_id) return
  try {
    const { data } = await api.get(`/billing/insurance/patient/${hosp.patient_id}/`)
    insuranceInfo.value = data
  } catch {
    insuranceInfo.value = null
  }
}

async function createInvoice() {
  error.value = ''
  success.value = ''
  if (!hospForm.value.hospitalization_id) {
    error.value = 'Sélectionnez un patient admis dans la liste.'
    return
  }
  creatingInvoice.value = true
  try {
    const { data } = await api.post(
      `/billing/invoices/from-hospitalization/${hospForm.value.hospitalization_id}/`,
    )
    hospForm.value.hospitalization_id = ''
    insuranceInfo.value = null
    success.value = `Facture ${data.invoice_number} créée pour ${data.patient_name} — ${formatMoney(data.patient_amount)}. Le patient peut valider le paiement depuis son téléphone (onglet Factures).`
    await load()
    payForm.value.invoice_id = data.id
    onInvoiceSelect()
  } catch (e) {
    error.value = apiErrorMessage(e, 'Erreur création facture.')
  } finally {
    creatingInvoice.value = false
  }
}

async function pay() {
  updateInstantPayError()
  if (!canSubmitPayment.value) {
    error.value = payInstantError.value || 'Complétez la procédure de paiement (facture, montant, réseau, référence).'
    return
  }
  error.value = ''
  success.value = ''
  paying.value = true
  try {
    const amount = payAmountNum.value
    await api.post(`/billing/invoices/${payForm.value.invoice_id}/payments/`, {
      amount: String(amount),
      method: payForm.value.method,
      reference: payForm.value.reference.trim(),
    })
    const methodLabel = MOBILE_MONEY_METHODS.find((m) => m.value === payForm.value.method)?.label || payForm.value.method
    payForm.value = { invoice_id: '', amount: '', method: 'AIRTEL', reference: '' }
    payInstantError.value = ''
    success.value = `Paiement ${methodLabel} enregistré avec succès.`
    await load()
  } catch (e) {
    const msg = apiErrorMessage(e, 'Erreur paiement.')
    error.value = msg
    payInstantError.value = msg
  } finally {
    paying.value = false
  }
}

async function openEdit(inv) {
  error.value = ''
  success.value = ''
  editingInvoice.value = inv
  editReason.value = ''
  try {
    const { data } = await api.get(`/billing/invoices/${inv.id}/lines/`)
    editLines.value = data.map((l) => ({
      description: l.description,
      service_type: l.service_type,
      quantity: l.quantity,
      unit_price: l.unit_price,
    }))
    showEdit.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de charger les lignes.'
  }
}

function addLine() {
  editLines.value.push({ description: '', service_type: 'ACT', quantity: '1', unit_price: '0' })
}

function removeLine(index) {
  if (editLines.value.length <= 1) return
  editLines.value.splice(index, 1)
}

async function saveEdit() {
  error.value = ''
  success.value = ''
  for (const line of editLines.value) {
    if (!line.description.trim() || line.description.trim().length < 2) {
      error.value = 'Chaque ligne doit avoir une description (min. 2 caractères).'
      return
    }
    if (parseFloat(line.quantity) <= 0) {
      error.value = 'Les quantités doivent être positives.'
      return
    }
  }
  savingEdit.value = true
  try {
    await api.patch(`/billing/invoices/${editingInvoice.value.id}/`, {
      lines: editLines.value.map((l) => ({
        description: l.description.trim(),
        service_type: l.service_type,
        quantity: l.quantity,
        unit_price: l.unit_price,
      })),
      reason: editReason.value.trim(),
    })
    showEdit.value = false
    editingInvoice.value = null
    success.value = 'Facture corrigée avec succès.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Correction impossible.'
  } finally {
    savingEdit.value = false
  }
}

async function downloadPdf(inv) {
  const response = await api.get(`/billing/invoices/${inv.id}/pdf/`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `${inv.invoice_number}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

function selectInvoiceForPay(inv) {
  payForm.value.invoice_id = inv.id
  tab.value = 'billing'
  onInvoiceSelect()
}

function patientDeclBadge(decl) {
  if (!decl) return null
  if (decl.status === 'PAID') {
    return { label: 'Payé (patient)', cls: 'bg-emerald-100 text-emerald-800', detail: `${decl.method} · ${decl.phone_number}` }
  }
  return { label: 'Impayé (patient)', cls: 'bg-amber-100 text-amber-900', detail: `${decl.method} · ${decl.phone_number}` }
}

onMounted(load)
</script>

<template>
  <div class="billing-space pb-8">
    <PageHeader
      title="Facturation & encaissements"
      subtitle="Espace secrétaire — factures, tiers-payant, mobile money Airtel / MTN (Congo-Brazzaville)"
    >
      <template #actions>
        <button type="button" class="btn-secondary text-sm" :disabled="loading" @click="load">
          {{ loading ? 'Actualisation…' : '↻ Actualiser' }}
        </button>
      </template>
    </PageHeader>

    <section class="rounded-2xl mb-6 bg-gradient-to-br from-teal-700 via-teal-800 to-emerald-900 text-white shadow-lg overflow-hidden">
      <div class="px-6 py-5 sm:px-8 sm:py-6">
        <p class="text-teal-200 text-xs font-bold uppercase tracking-widest mb-1">SGHL · Secrétariat · Dolisie (RC)</p>
        <h2 class="text-xl sm:text-2xl font-bold">Caisse hospitalière — Mobile Money uniquement</h2>
        <p class="text-teal-100/90 text-sm mt-2 max-w-2xl leading-relaxed">
          Tous les montants sont en <strong>{{ CURRENCY_FULL }}</strong>.
          Paiements via <strong>Airtel Money</strong> ou <strong>MTN Mobile Money</strong> uniquement.
        </p>
      </div>
    </section>

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
    <AlertBanner v-if="success" type="success" class="mb-4">{{ success }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- KPI -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        <div class="card card-body !py-4 border-l-4 border-l-indigo-500">
          <p class="text-2xl font-bold text-indigo-700 tabular-nums">{{ billingKpi.admitted }}</p>
          <p class="text-xs text-slate-500 mt-1">Patients admis</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-teal-500">
          <p class="text-2xl font-bold text-teal-700 tabular-nums">{{ billingKpi.total }}</p>
          <p class="text-xs text-slate-500 mt-1">Factures totales</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-amber-500">
          <p class="text-2xl font-bold text-amber-700 tabular-nums">{{ billingKpi.unpaidCount }}</p>
          <p class="text-xs text-slate-500 mt-1">En attente de paiement</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-red-500 col-span-2 lg:col-span-1">
          <p class="text-xl sm:text-2xl font-bold text-red-700 tabular-nums">{{ formatMoney(billingKpi.totalDue) }}</p>
          <p class="text-xs text-slate-500 mt-1">Solde global dû</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-emerald-500">
          <p class="text-2xl font-bold text-emerald-700 tabular-nums">{{ billingKpi.paid }}</p>
          <p class="text-xs text-slate-500 mt-1">Factures soldées</p>
        </div>
      </div>

      <div class="card !p-2 mb-6">
        <div class="flex flex-wrap gap-1.5 p-1">
          <button
            type="button"
            class="rounded-xl px-4 py-2.5 text-sm font-semibold transition-all"
            :class="tab === 'billing' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-600 hover:bg-slate-100'"
            @click="tab = 'billing'"
          >
            💳 Encaissement
          </button>
          <button
            type="button"
            class="rounded-xl px-4 py-2.5 text-sm font-semibold transition-all"
            :class="tab === 'journal' ? 'bg-teal-600 text-white shadow-md' : 'text-slate-600 hover:bg-slate-100'"
            @click="tab = 'journal'"
          >
            📒 Journal comptable
          </button>
        </div>
      </div>

      <div v-show="tab === 'billing'" class="space-y-6">
        <!-- Étape 1 — Patients admis -->
        <section class="card overflow-hidden border-teal-100">
          <div class="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-teal-50 to-white">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 class="font-bold text-slate-900 flex items-center gap-2">
                  <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-100 text-base" aria-hidden="true">📄</span>
                  Étape 1 — Choisir un patient admis et créer la facture
                </h3>
                <p class="text-xs text-slate-500 mt-1">
                  {{ hospitalizations.length }} patient(s) hospitalisé(s) actuellement — sélectionnez une ligne puis validez.
                </p>
              </div>
              <div class="relative w-full sm:max-w-xs">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">🔍</span>
                <input
                  v-model="admissionSearch"
                  type="search"
                  class="form-input pl-10 w-full"
                  placeholder="Rechercher patient, service, chambre…"
                />
              </div>
            </div>
          </div>

          <div v-if="loadingAdmissions" class="p-8">
            <LoadingState />
          </div>

          <div v-else-if="filteredHospitalizations.length" class="overflow-x-auto max-h-[420px] overflow-y-auto">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 text-xs uppercase text-slate-500 sticky top-0 z-10">
                <tr>
                  <th class="text-left p-3 font-semibold w-8"></th>
                  <th class="text-left p-3 font-semibold">Patient</th>
                  <th class="text-left p-3 font-semibold">Service / Lit</th>
                  <th class="text-left p-3 font-semibold">Admission</th>
                  <th class="text-left p-3 font-semibold">Motif</th>
                  <th class="text-left p-3 font-semibold">Facture</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="h in filteredHospitalizations"
                  :key="h.id"
                  class="border-t border-slate-100 cursor-pointer transition-colors"
                  :class="
                    hospForm.hospitalization_id === h.id
                      ? 'bg-teal-50 ring-2 ring-inset ring-teal-400'
                      : 'hover:bg-slate-50'
                  "
                  @click="selectHospitalization(h)"
                >
                  <td class="p-3 text-center">
                    <span
                      class="inline-flex h-5 w-5 items-center justify-center rounded-full border-2"
                      :class="hospForm.hospitalization_id === h.id ? 'border-teal-600 bg-teal-600 text-white text-[10px]' : 'border-slate-300'"
                    >
                      {{ hospForm.hospitalization_id === h.id ? '✓' : '' }}
                    </span>
                  </td>
                  <td class="p-3">
                    <p class="font-bold text-slate-900">{{ h.patient_name }}</p>
                  </td>
                  <td class="p-3 text-slate-600">
                    <p class="font-medium">{{ h.department_name || '—' }}</p>
                    <p class="text-xs text-slate-400">
                      Ch. {{ h.room_number || '—' }} · Lit {{ h.bed_label || '—' }}
                    </p>
                  </td>
                  <td class="p-3 text-slate-600 whitespace-nowrap">{{ fmtAdmissionDate(h.admission_date) }}</td>
                  <td class="p-3 text-slate-500 text-xs max-w-[200px] truncate" :title="h.admission_reason">
                    {{ h.admission_reason || '—' }}
                  </td>
                  <td class="p-3">
                    <span
                      v-if="invoiceForHospitalization(h.id)"
                      class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-amber-100 text-amber-800"
                    >
                      {{ invoiceForHospitalization(h.id).invoice_number }}
                    </span>
                    <span v-else class="text-[10px] font-semibold text-slate-400">Aucune</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-else class="p-10 text-center text-slate-500">
            Aucun patient admis pour le moment.
            <span v-if="admissionSearch.trim()"> Essayez une autre recherche.</span>
          </p>

          <!-- Patient sélectionné + création -->
          <div class="border-t border-slate-100 bg-slate-50/80 px-5 py-4">
            <div v-if="selectedHospitalization" class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div class="min-w-0">
                <p class="text-[10px] font-bold uppercase tracking-wider text-teal-700 mb-1">Patient sélectionné</p>
                <p class="font-bold text-lg text-slate-900">{{ selectedHospitalization.patient_name }}</p>
                <p class="text-sm text-slate-600 mt-0.5">
                  {{ selectedHospitalization.department_name }} —
                  Ch. {{ selectedHospitalization.room_number }} · Lit {{ selectedHospitalization.bed_label }}
                </p>
                <p class="text-xs text-slate-500 mt-1">
                  Admis le {{ fmtAdmissionDate(selectedHospitalization.admission_date) }}
                </p>
                <div
                  v-if="insuranceInfo?.has_insurance"
                  class="inline-block mt-2 rounded-lg bg-emerald-100 border border-emerald-200 px-3 py-1 text-xs font-semibold text-emerald-800"
                >
                  Tiers-payant : {{ insuranceInfo.provider_name }} ({{ insuranceInfo.coverage_rate }} %)
                </div>
                <p
                  v-if="invoiceForHospitalization(selectedHospitalization.id)"
                  class="text-xs text-amber-700 mt-2 font-medium"
                >
                  ⚠ Une facture existe déjà ({{ invoiceForHospitalization(selectedHospitalization.id).invoice_number }}) —
                  une nouvelle facture sera créée pour cette hospitalisation.
                </p>
              </div>
              <button
                type="button"
                class="btn-primary shrink-0 px-8 py-3"
                :disabled="creatingInvoice"
                @click="createInvoice"
              >
                {{ creatingInvoice ? 'Création…' : '✓ Créer la facture' }}
              </button>
            </div>
            <p v-else class="text-sm text-slate-500 text-center py-2">
              Cliquez sur un patient dans la liste ci-dessus pour préparer la facture.
            </p>
          </div>
        </section>

        <!-- Étape 2 — Paiement -->
        <form class="card card-body border-teal-100" @submit.prevent="pay">
            <h3 class="font-bold text-slate-900 flex items-center gap-2 mb-1">
              <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-100 text-base" aria-hidden="true">📲</span>
              Étape 2 — Encaissement Mobile Money
            </h3>
            <p class="text-xs text-slate-500 mb-4">Airtel ou MTN uniquement — Congo-Brazzaville (+242).</p>

            <!-- Procédure -->
            <ol class="mb-5 space-y-1.5 rounded-xl bg-slate-50 border border-slate-100 p-4">
              <li
                v-for="(step, idx) in PAYMENT_PROCEDURE"
                :key="idx"
                class="flex gap-2 text-xs text-slate-600"
              >
                <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-600 text-white text-[10px] font-bold">{{ idx + 1 }}</span>
                {{ step }}
              </li>
            </ol>

            <!-- Alerte solde immédiate -->
            <div
              v-if="payInstantError"
              class="mb-4 rounded-xl border-2 border-red-300 bg-red-50 px-4 py-3 flex items-start gap-3"
              role="alert"
            >
              <span class="text-xl shrink-0" aria-hidden="true">⛔</span>
              <div>
                <p class="text-sm font-bold text-red-800">Paiement refusé</p>
                <p class="text-sm text-red-700 mt-0.5">{{ payInstantError }}</p>
              </div>
            </div>

            <div
              v-else-if="selectedInvoice && payForm.amount && !payAmountExceedsBalance"
              class="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
            >
              ✓ Montant valide — reste après paiement :
              <strong>{{ formatMoney(Math.max(0, selectedBalance - payAmountNum)) }}</strong>
            </div>

            <label class="block mb-4">
              <span class="form-label">Facture</span>
              <select v-model="payForm.invoice_id" class="form-select" required @change="onInvoiceSelect">
                <option value="">Sélectionner une facture…</option>
                <option v-for="i in payableInvoices" :key="i.id" :value="i.id">
                  {{ i.invoice_number }} — {{ i.patient_name || 'Patient' }} (reste {{ formatMoney(i.balance_due) }})
                </option>
              </select>
              <p v-if="!payableInvoices.length" class="text-xs text-amber-700 mt-1">
                Aucune facture avec solde dû — créez d'abord une facture (étape 1).
              </p>
            </label>

            <!-- Solde facture sélectionnée -->
            <div
              v-if="selectedInvoice"
              class="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-xl bg-teal-50/80 border border-teal-100 p-3 text-center"
            >
              <div>
                <p class="text-[10px] uppercase text-slate-500 font-semibold">Patient</p>
                <p class="text-sm font-bold text-slate-800 truncate">{{ selectedInvoice.patient_name || '—' }}</p>
              </div>
              <div>
                <p class="text-[10px] uppercase text-slate-500 font-semibold">Part patient</p>
                <p class="text-sm font-bold tabular-nums">{{ formatMoney(selectedInvoice.patient_amount) }}</p>
              </div>
              <div>
                <p class="text-[10px] uppercase text-slate-500 font-semibold">Déjà payé</p>
                <p class="text-sm font-bold tabular-nums text-emerald-700">{{ formatMoney(selectedInvoice.paid_amount) }}</p>
              </div>
              <div>
                <p class="text-[10px] uppercase text-red-600 font-bold">Reste dû</p>
                <p class="text-lg font-bold tabular-nums text-red-700">{{ formatMoney(selectedInvoice.balance_due) }}</p>
              </div>
            </div>

            <!-- Réseaux Airtel / MTN -->
            <p class="form-label mb-2">Réseau mobile money <span class="text-red-500">*</span></p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <button
                v-for="m in MOBILE_MONEY_METHODS"
                :key="m.value"
                type="button"
                class="rounded-xl border-2 p-4 text-left transition-all ring-2 ring-transparent"
                :class="payForm.method === m.value ? m.active : m.color"
                @click="payForm.method = m.value"
              >
                <div class="flex items-center gap-3">
                  <span class="text-2xl" aria-hidden="true">{{ m.icon }}</span>
                  <div>
                    <p class="font-bold">{{ m.label }}</p>
                    <p class="text-xs opacity-80">{{ m.network }} · {{ m.prefix }}</p>
                  </div>
                  <span
                    v-if="payForm.method === m.value"
                    class="ml-auto text-xs font-bold px-2 py-0.5 rounded-full bg-white/25"
                  >
                    ✓
                  </span>
                </div>
              </button>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <label class="block">
                <span class="form-label">Montant ({{ CURRENCY_FULL }}) <span class="text-red-500">*</span></span>
                <input
                  v-model="payForm.amount"
                  type="number"
                  step="1"
                  min="1"
                  class="form-input text-lg font-bold tabular-nums"
                  :class="{ 'ring-2 ring-red-400 border-red-400': payAmountExceedsBalance || payAmountInvalid }"
                  placeholder="0"
                  required
                  @input="updateInstantPayError"
                />
                <button
                  v-if="selectedBalance > 0"
                  type="button"
                  class="mt-1.5 text-xs font-semibold text-teal-700 hover:underline"
                  @click="fillFullBalance"
                >
                  Solder le reste dû ({{ formatMoney(selectedBalance) }})
                </button>
              </label>
              <label class="block">
                <span class="form-label">Réf. transaction / N° payeur <span class="text-red-500">*</span></span>
                <input
                  v-model="payForm.reference"
                  class="form-input"
                  placeholder="Ex. TXN-20260315 ou 06 659 25 64"
                  required
                  minlength="4"
                />
                <p class="text-[10px] text-slate-400 mt-1">ID reçu après débit Airtel / MTN</p>
              </label>
            </div>

            <button
              type="submit"
              class="btn-primary w-full sm:w-auto px-8"
              :disabled="paying || !canSubmitPayment"
              :class="{ 'opacity-50 cursor-not-allowed': !canSubmitPayment }"
            >
              {{ paying ? 'Enregistrement…' : '✓ Valider le paiement mobile money' }}
            </button>
          </form>

        <!-- Registre des factures -->
        <div class="card overflow-hidden">
          <div class="px-5 py-4 border-b border-slate-100 bg-slate-50/80 flex flex-wrap items-center justify-between gap-2">
            <h3 class="font-bold text-slate-900">Registre des factures</h3>
            <span class="text-xs font-semibold text-slate-500">{{ invoices.length }} facture(s)</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th class="text-left p-4 font-semibold">N° facture</th>
                  <th class="text-left p-4 font-semibold">Patient</th>
                  <th class="text-left p-4 font-semibold">Statut</th>
                  <th class="text-left p-4 font-semibold">Déclaration patient</th>
                  <th class="text-right p-4 font-semibold">Part patient</th>
                  <th class="text-right p-4 font-semibold">Assurance</th>
                  <th class="text-right p-4 font-semibold">Reste dû</th>
                  <th class="p-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="i in invoices"
                  :key="i.id"
                  class="border-t border-slate-100 hover:bg-slate-50/50 transition-colors"
                >
                  <td class="p-4 font-mono font-semibold text-teal-800">{{ i.invoice_number }}</td>
                  <td class="p-4 font-medium text-slate-800">{{ i.patient_name || '—' }}</td>
                  <td class="p-4"><StatusBadge :status="i.status" /></td>
                  <td class="p-4">
                    <template v-if="patientDeclBadge(i.patient_declaration)">
                      <span
                        class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                        :class="patientDeclBadge(i.patient_declaration).cls"
                      >
                        {{ patientDeclBadge(i.patient_declaration).label }}
                      </span>
                      <p class="text-[10px] text-slate-500 mt-1">{{ patientDeclBadge(i.patient_declaration).detail }}</p>
                    </template>
                    <span v-else class="text-xs text-slate-400">En attente</span>
                  </td>
                  <td class="p-4 text-right tabular-nums">{{ formatMoney(i.patient_amount) }}</td>
                  <td class="p-4 text-right tabular-nums text-emerald-600">{{ formatMoney(i.insurance_amount) }}</td>
                  <td class="p-4 text-right">
                    <span
                      class="font-bold tabular-nums"
                      :class="parseFloat(i.balance_due) > 0 ? 'text-red-700' : 'text-emerald-700'"
                    >
                      {{ formatMoney(i.balance_due) }}
                    </span>
                  </td>
                  <td class="p-4 text-right whitespace-nowrap space-x-2">
                    <button
                      v-if="parseFloat(i.balance_due) > 0 && i.status !== 'CANCELLED'"
                      type="button"
                      class="text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 px-2.5 py-1 rounded-lg"
                      @click="selectInvoiceForPay(i)"
                    >
                      Encaisser
                    </button>
                    <button
                      v-if="isEditable(i.status)"
                      type="button"
                      class="text-primary text-xs font-medium hover:underline"
                      @click="openEdit(i)"
                    >
                      Modifier
                    </button>
                    <button type="button" class="text-slate-600 text-xs font-medium hover:underline" @click="downloadPdf(i)">
                      PDF
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!invoices.length" class="p-10 text-center text-slate-500">
            Registre vide — aucune facture enregistrée. Créez une facture à l'étape 1.
          </p>
        </div>
      </div>

      <!-- Journal -->
      <div v-show="tab === 'journal'" class="card overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-100 bg-slate-50/80">
          <h3 class="font-bold text-slate-900">Journal comptable</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="text-left p-4 font-semibold">Date</th>
                <th class="text-left p-4 font-semibold">Compte</th>
                <th class="text-left p-4 font-semibold">Libellé</th>
                <th class="text-right p-4 font-semibold">Montant</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in journal" :key="e.id" class="border-t" :class="{ 'bg-amber-50/60': e.is_adjustment }">
                <td class="p-4">{{ new Date(e.entry_date).toLocaleDateString('fr-FR') }}</td>
                <td class="p-4 font-mono text-teal-700">{{ e.account_code }}</td>
                <td class="p-4">{{ e.label }}</td>
                <td class="p-4 text-right tabular-nums font-medium">
                  {{ e.entry_type === 'DEBIT' ? '+' : '−' }}{{ formatMoney(e.amount) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!journal.length" class="p-8 text-center text-slate-500">Journal vide.</p>
      </div>
    </template>

    <Modal :open="showEdit" :title="`Corriger ${editingInvoice?.invoice_number || 'facture'}`" wide @close="showEdit = false">
      <p class="text-sm text-slate-500 mb-4">
        Modifiez les lignes en cas d'erreur. Les montants et le journal comptable seront recalculés automatiquement.
      </p>
      <div class="overflow-x-auto mb-4">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b text-left text-slate-500">
              <th class="pb-2 pr-2 font-medium">Description</th>
              <th class="pb-2 pr-2 font-medium w-32">Type</th>
              <th class="pb-2 pr-2 font-medium w-20">Qté</th>
              <th class="pb-2 pr-2 font-medium w-28">P.U. FCFA</th>
              <th class="pb-2 pr-2 font-medium w-24 text-right">Total</th>
              <th class="pb-2 w-8"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(line, idx) in editLines" :key="idx" class="border-b border-slate-100">
              <td class="py-2 pr-2"><input v-model="line.description" class="form-input text-sm" placeholder="Libellé" /></td>
              <td class="py-2 pr-2">
                <select v-model="line.service_type" class="form-select text-sm">
                  <option v-for="t in SERVICE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
              </td>
              <td class="py-2 pr-2"><input v-model="line.quantity" type="number" min="0.01" step="0.01" class="form-input text-sm" /></td>
              <td class="py-2 pr-2"><input v-model="line.unit_price" type="number" min="0" step="0.01" class="form-input text-sm" /></td>
              <td class="py-2 pr-2 text-right font-medium">{{ formatMoney(lineTotal(line)) }}</td>
              <td class="py-2">
                <button type="button" class="text-red-500 text-xs hover:underline disabled:opacity-30" :disabled="editLines.length <= 1" @click="removeLine(idx)">×</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <button type="button" class="text-sm text-primary font-medium hover:underline mb-4" @click="addLine">+ Ajouter une ligne</button>
      <label class="block mb-2">
        <span class="form-label">Motif de correction (optionnel)</span>
        <input v-model="editReason" class="form-input" placeholder="Ex. erreur de nuitées…" />
      </label>
      <p class="text-sm font-semibold text-slate-700 mt-4">Sous-total recalculé : {{ formatMoney(editSubtotal) }}</p>
      <template #footer>
        <button type="button" class="btn-secondary" @click="showEdit = false">Annuler</button>
        <button type="button" class="btn-primary" :disabled="savingEdit" @click="saveEdit">
          {{ savingEdit ? 'Enregistrement…' : 'Enregistrer la correction' }}
        </button>
      </template>
    </Modal>
  </div>
</template>
