<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import FormField from '../components/ui/FormField.vue'
import PhoneInput from '../components/ui/PhoneInput.vue'
import { useAuthStore } from '../stores/auth'
import {
  validators,
  blockDigitsInName,
  sanitizeNamePaste,
  validateFields,
  hasErrors,
} from '../composables/useFormValidation'

const auth = useAuthStore()
const tab = ref('queue')
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const success = ref('')

const overview = ref({ medicine_count: 0, stock_units: 0, alert_count: 0, lot_count: 0, expiring_soon: 0 })
const medicines = ref([])
const alerts = ref([])
const stock = ref([])
const movements = ref([])
const prescriptions = ref([])

const searchQuery = ref('')
const stockSearch = ref('')
const catalogFilter = ref('all')

const lotForm = ref({ medicine_id: '', lot_number: '', expiry_date: '', quantity: 10, location: '' })
const dispenseForm = ref({ medicine_id: '', quantity: 1 })

const patientForm = ref({
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: 'F',
  phone: '',
  email: '',
})
const patientFieldErrors = ref({})
const patientSaving = ref(false)

const canManageStock = computed(() => auth.hasPerm('pharmacy.manage_stock'))
const canDispense = computed(() => auth.hasPerm('pharmacy.dispense'))
const canRegisterPatient = computed(() => canDispense.value || auth.hasPerm('clinical.admit_patient'))

const tabs = computed(() => [
  { id: 'queue', label: 'File du jour', icon: '📋', count: prescriptions.value.length || null },
  { id: 'patient', label: 'Nouveau patient', icon: '👤', hidden: !canRegisterPatient.value },
  { id: 'catalog', label: 'Catalogue', icon: '💊', count: overview.value.medicine_count || null },
  { id: 'stock', label: 'Lots & péremption', icon: '📦', count: overview.value.lot_count || null },
  { id: 'reception', label: 'Réception', icon: '📥', hidden: !canManageStock.value },
  { id: 'dispense', label: 'Dispensation', icon: '📤', hidden: !canDispense.value },
  { id: 'movements', label: 'Traçabilité', icon: '🕐' },
].filter((t) => !t.hidden))

const kpiCards = computed(() => [
  {
    key: 'products',
    label: 'Produits référencés',
    value: overview.value.medicine_count,
    icon: '💊',
    accent: 'from-violet-500 to-violet-600',
    text: 'text-violet-700',
    bg: 'bg-violet-50',
  },
  {
    key: 'units',
    label: 'Unités disponibles',
    value: overview.value.stock_units.toLocaleString('fr-FR'),
    icon: '✅',
    accent: 'from-emerald-500 to-emerald-600',
    text: 'text-emerald-700',
    bg: 'bg-emerald-50',
  },
  {
    key: 'alerts',
    label: 'Alertes rupture',
    value: overview.value.alert_count,
    icon: '⚠️',
    accent: 'from-amber-500 to-orange-500',
    text: overview.value.alert_count ? 'text-amber-700' : 'text-slate-700',
    bg: overview.value.alert_count ? 'bg-amber-50' : 'bg-slate-50',
    pulse: overview.value.alert_count > 0,
  },
  {
    key: 'lots',
    label: 'Lots actifs',
    value: overview.value.lot_count,
    icon: '📦',
    accent: 'from-indigo-500 to-indigo-600',
    text: 'text-indigo-700',
    bg: 'bg-indigo-50',
  },
  {
    key: 'expiry',
    label: 'Péremption < 90 j',
    value: overview.value.expiring_soon,
    icon: '⏳',
    accent: 'from-rose-500 to-red-600',
    text: overview.value.expiring_soon ? 'text-red-700' : 'text-slate-700',
    bg: overview.value.expiring_soon ? 'bg-red-50' : 'bg-slate-50',
    pulse: overview.value.expiring_soon > 0,
  },
])

const catalogHeaders = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Produit' },
  { key: 'form', label: 'Forme' },
  { key: 'stock_total', label: 'Stock' },
  { key: 'unit_price', label: 'Prix unit.' },
]

const stockHeaders = [
  { key: 'medicine_name', label: 'Produit' },
  { key: 'lot_number', label: 'Lot' },
  { key: 'quantity', label: 'Qté' },
  { key: 'expiry_date', label: 'Péremption' },
  { key: 'location', label: 'Emplacement' },
]

const FORM_ICONS = {
  comprimé: '💊',
  gélule: '💊',
  injection: '💉',
  perfusion: '💧',
  aérosol: '💨',
  poudre: '🧪',
  flacon: '🧴',
  ampoule: '💉',
  poche: '💧',
}

const filteredCatalog = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let list = medicines.value
  if (catalogFilter.value === 'low') {
    list = list.filter((m) => m.stock_status === 'LOW' || m.stock_status === 'OUT')
  } else if (catalogFilter.value === 'ok') {
    list = list.filter((m) => m.stock_status === 'OK')
  }
  if (!q) return list
  return list.filter(
    (m) => m.name.toLowerCase().includes(q) || m.code.toLowerCase().includes(q) || m.form.toLowerCase().includes(q),
  )
})

const catalogRows = computed(() =>
  filteredCatalog.value.map((m) => ({
    ...m,
    unit_price: `${Number(m.unit_price).toLocaleString('fr-FR')} FCFA`,
  })),
)

const filteredStockRows = computed(() => {
  const q = stockSearch.value.trim().toLowerCase()
  if (!q) return stock.value
  return stock.value.filter(
    (l) => l.medicine_name.toLowerCase().includes(q) || l.lot_number.toLowerCase().includes(q),
  )
})

const stockRows = computed(() =>
  filteredStockRows.value.map((l) => ({
    ...l,
    expiry_date: fmtDate(l.expiry_date),
    days_to_expiry: l.days_to_expiry,
  })),
)

const expiringLots = computed(() =>
  [...stock.value]
    .filter((l) => l.days_to_expiry <= 90)
    .sort((a, b) => a.days_to_expiry - b.days_to_expiry)
    .slice(0, 6),
)

const movementRows = computed(() =>
  movements.value.map((m) => ({
    ...m,
    created_at: fmtDateTime(m.created_at),
    quantity: `${m.movement_type === 'IN' ? '+' : '−'}${m.quantity}`,
    movement_type: m.movement_type,
  })),
)

const selectedMedicine = computed(() =>
  medicines.value.find((m) => m.id === dispenseForm.value.medicine_id),
)

function formIcon(form) {
  const key = (form || '').toLowerCase()
  return FORM_ICONS[key] || '💊'
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

function fmtDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function stockBadge(status) {
  if (status === 'OUT') return { label: 'Rupture', cls: 'bg-red-100 text-red-800 ring-red-200' }
  if (status === 'LOW') return { label: 'Stock bas', cls: 'bg-amber-100 text-amber-800 ring-amber-200' }
  return { label: 'Disponible', cls: 'bg-emerald-100 text-emerald-800 ring-emerald-200' }
}

function expiryBadge(days) {
  if (days <= 30) return { label: 'Urgent', cls: 'bg-red-100 text-red-800', bar: 'bg-red-500', pct: Math.max(5, (days / 30) * 100) }
  if (days <= 90) return { label: 'À surveiller', cls: 'bg-amber-100 text-amber-800', bar: 'bg-amber-500', pct: (days / 90) * 100 }
  return { label: 'OK', cls: 'bg-slate-100 text-slate-600', bar: 'bg-emerald-500', pct: 100 }
}

async function loadMedicines() {
  const { data } = await api.get('/pharmacy/medicines/', { params: { search: searchQuery.value.trim() } })
  medicines.value = data
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const reqs = [
      api.get('/pharmacy/overview/'),
      api.get('/pharmacy/medicines/'),
      api.get('/pharmacy/stock/alerts/'),
      api.get('/pharmacy/stock/'),
      api.get('/pharmacy/stock/movements/'),
    ]
    if (canDispense.value) {
      reqs.push(api.get('/clinical/prescriptions/validated/'))
    }
    const results = await Promise.all(reqs)
    overview.value = results[0].data
    medicines.value = results[1].data
    alerts.value = results[2].data
    stock.value = results[3].data
    movements.value = results[4].data
    prescriptions.value = results[5]?.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function addLot() {
  error.value = ''
  success.value = ''
  submitting.value = true
  try {
    await api.post('/pharmacy/stock/lots/', lotForm.value)
    lotForm.value = { medicine_id: '', lot_number: '', expiry_date: '', quantity: 10, location: '' }
    success.value = 'Lot enregistré — stock mis à jour.'
    tab.value = 'stock'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur réception.'
  } finally {
    submitting.value = false
  }
}

async function dispense(fromRow = null) {
  error.value = ''
  success.value = ''
  const medicineId = fromRow?.id || dispenseForm.value.medicine_id
  const quantity = fromRow ? 1 : dispenseForm.value.quantity
  if (!medicineId) {
    error.value = 'Sélectionnez un médicament.'
    return
  }
  submitting.value = true
  try {
    await api.post(`/pharmacy/dispense/${medicineId}/?quantity=${quantity}`)
    success.value = `${quantity} unité(s) dispensée(s) — mouvement tracé.`
    dispenseForm.value = { medicine_id: '', quantity: 1 }
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Stock insuffisant.'
  } finally {
    submitting.value = false
  }
}

function pickForDispense(m) {
  dispenseForm.value.medicine_id = m.id
  tab.value = 'dispense'
}

function pickForReception(m) {
  lotForm.value.medicine_id = m.id
  tab.value = 'reception'
}

function goToAlerts() {
  catalogFilter.value = 'low'
  tab.value = 'catalog'
}

function goToExpiring() {
  tab.value = 'stock'
}

function emptyPatientForm() {
  return {
    first_name: '',
    last_name: '',
    date_of_birth: '',
    gender: 'F',
    phone: '',
    email: '',
  }
}

function onPatientNamePaste(field, event) {
  sanitizeNamePaste(event, (text) => {
    patientForm.value[field] = text
  })
}

function stripPatientNameDigits(field) {
  patientForm.value[field] = patientForm.value[field].replace(/\d/g, '')
}

function validatePatientForm() {
  patientFieldErrors.value = validateFields({
    first_name: () => validators.personName(patientForm.value.first_name, 'Prénom'),
    last_name: () => validators.personName(patientForm.value.last_name, 'Nom'),
    date_of_birth: () => validators.dateOfBirth(patientForm.value.date_of_birth),
    phone: () => validators.phoneInternational(patientForm.value.phone, true),
    email: () => validators.email(patientForm.value.email, true),
  })
  return !hasErrors(patientFieldErrors.value)
}

async function registerPatient() {
  error.value = ''
  success.value = ''
  if (!validatePatientForm()) {
    error.value = 'Vérifiez les champs obligatoires — email et téléphone sont requis au comptoir.'
    tab.value = 'patient'
    return
  }
  patientSaving.value = true
  try {
    const { data } = await api.post('/clinical/patients/', {
      ...patientForm.value,
      email: patientForm.value.email.trim().toLowerCase(),
      phone: patientForm.value.phone.trim(),
    })
    success.value = `Patient ${data.last_name} ${data.first_name} enregistré — contact : ${data.email || '—'} / ${data.phone || '—'}`
    patientForm.value = emptyPatientForm()
    patientFieldErrors.value = {}
    tab.value = 'queue'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Enregistrement patient impossible.'
  } finally {
    patientSaving.value = false
  }
}

function contactStatus(p) {
  const hasEmail = !!(p.patient_email || '').trim()
  const hasPhone = !!(p.patient_phone || '').trim()
  if (hasEmail && hasPhone) return 'complete'
  if (hasEmail || hasPhone) return 'partial'
  return 'missing'
}

let searchTimer = null
watch(searchQuery, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadMedicines, 300)
})

onMounted(load)
</script>

<template>
  <div class="pharmacy-space pb-8">
    <PageHeader title="Pharmacie hospitalière" subtitle="Gestion des stocks, dispensation FIFO et traçabilité réglementaire">
      <template #actions>
        <button type="button" class="btn-secondary text-sm" :disabled="loading" @click="load">
          {{ loading ? 'Actualisation…' : '↻ Actualiser' }}
        </button>
      </template>
    </PageHeader>

    <!-- Bandeau établissement -->
    <section
      class="relative overflow-hidden rounded-2xl mb-6 bg-gradient-to-br from-violet-700 via-violet-800 to-indigo-900 text-white shadow-lg shadow-violet-900/20"
    >
      <div class="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-white/5 blur-2xl" aria-hidden="true" />
      <div class="absolute -left-4 bottom-0 h-32 w-32 rounded-full bg-violet-400/10 blur-xl" aria-hidden="true" />
      <div class="relative px-6 py-5 sm:px-8 sm:py-6 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <p class="text-violet-200 text-xs font-bold uppercase tracking-widest mb-1">SGHL · Dolisie (RC)</p>
          <h2 class="text-xl sm:text-2xl font-bold tracking-tight">Officine centrale — Centre Hospitalier</h2>
          <p class="text-violet-100/90 text-sm mt-2 max-w-xl leading-relaxed">
            Réception par lots, contrôle des péremptions, dispensation sur ordonnance validée.
            Sortie automatique FIFO (lot le plus proche de l'expiration).
          </p>
        </div>
        <div class="flex flex-wrap gap-2 shrink-0">
          <span class="inline-flex items-center gap-2 rounded-xl bg-white/10 backdrop-blur px-4 py-2 text-sm font-medium ring-1 ring-white/20">
            <span class="text-lg" aria-hidden="true">💊</span>
            {{ overview.medicine_count }} produits
          </span>
          <span class="inline-flex items-center gap-2 rounded-xl bg-white/10 backdrop-blur px-4 py-2 text-sm font-medium ring-1 ring-white/20">
            <span class="text-lg" aria-hidden="true">📦</span>
            {{ overview.stock_units.toLocaleString('fr-FR') }} unités
          </span>
        </div>
      </div>
    </section>

    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- KPI -->
      <div class="grid grid-cols-2 xl:grid-cols-5 gap-3 sm:gap-4 mb-6">
        <button
          v-for="card in kpiCards"
          :key="card.key"
          type="button"
          class="card card-body !p-0 overflow-hidden text-left transition-all hover:shadow-md hover:-translate-y-0.5"
          :class="card.key === 'alerts' && card.pulse ? 'ring-2 ring-amber-300/60' : ''"
          @click="card.key === 'alerts' ? goToAlerts() : card.key === 'expiry' ? goToExpiring() : null"
        >
          <div class="flex h-full">
            <div class="w-1.5 shrink-0 bg-gradient-to-b" :class="card.accent" />
            <div class="flex-1 p-4 sm:p-5">
              <div class="flex items-start justify-between gap-2">
                <span
                  class="flex h-10 w-10 items-center justify-center rounded-xl text-lg"
                  :class="card.bg"
                  aria-hidden="true"
                >
                  {{ card.icon }}
                </span>
                <span
                  v-if="card.pulse"
                  class="relative flex h-2.5 w-2.5 mt-1"
                  aria-hidden="true"
                >
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                  <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
                </span>
              </div>
              <p class="text-2xl sm:text-3xl font-bold mt-3 tabular-nums" :class="card.text">
                {{ card.value }}
              </p>
              <p class="text-xs text-slate-500 mt-1 font-medium">{{ card.label }}</p>
            </div>
          </div>
        </button>
      </div>

      <!-- Alertes rapides -->
      <div v-if="alerts.length || expiringLots.length" class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div
          v-if="alerts.length"
          class="rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50/50 p-5"
        >
          <div class="flex items-center gap-2 mb-3">
            <span class="text-xl" aria-hidden="true">⚠️</span>
            <h3 class="font-bold text-amber-900">Réapprovisionnement requis</h3>
            <span class="ml-auto text-xs font-bold bg-amber-200 text-amber-900 px-2.5 py-0.5 rounded-full">
              {{ alerts.length }}
            </span>
          </div>
          <ul class="space-y-2">
            <li
              v-for="a in alerts.slice(0, 5)"
              :key="a.id"
              class="flex items-center justify-between gap-3 rounded-xl bg-white/80 px-3 py-2 text-sm border border-amber-100"
            >
              <span class="font-medium text-slate-800 truncate">{{ a.name }}</span>
              <span class="shrink-0 text-xs font-semibold text-amber-800">{{ a.stock_total }} restant(s)</span>
            </li>
          </ul>
          <button type="button" class="mt-3 text-xs font-semibold text-amber-800 hover:underline" @click="goToAlerts">
            Voir tout le catalogue →
          </button>
        </div>

        <div
          v-if="expiringLots.length"
          class="rounded-2xl border border-red-200 bg-gradient-to-r from-red-50 to-rose-50/50 p-5"
        >
          <div class="flex items-center gap-2 mb-3">
            <span class="text-xl" aria-hidden="true">⏳</span>
            <h3 class="font-bold text-red-900">Lots proches de la péremption</h3>
          </div>
          <ul class="space-y-2">
            <li
              v-for="lot in expiringLots"
              :key="lot.id"
              class="rounded-xl bg-white/80 px-3 py-2.5 text-sm border border-red-100"
            >
              <div class="flex justify-between gap-2 mb-1.5">
                <span class="font-medium text-slate-800 truncate">{{ lot.medicine_name }}</span>
                <span class="shrink-0 text-xs font-mono text-slate-500">{{ lot.lot_number }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="flex-1 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="expiryBadge(lot.days_to_expiry).bar"
                    :style="{ width: `${Math.min(100, expiryBadge(lot.days_to_expiry).pct)}%` }"
                  />
                </div>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" :class="expiryBadge(lot.days_to_expiry).cls">
                  J-{{ lot.days_to_expiry }}
                </span>
              </div>
            </li>
          </ul>
          <button type="button" class="mt-3 text-xs font-semibold text-red-800 hover:underline" @click="goToExpiring">
            Gérer les lots →
          </button>
        </div>
      </div>

      <!-- Navigation -->
      <div class="card !p-2 mb-6 sticky top-0 z-10 shadow-sm border border-slate-200/80 bg-white/95 backdrop-blur-sm">
        <div class="flex flex-wrap gap-1.5 p-1">
          <button
            v-for="t in tabs"
            :key="t.id"
            type="button"
            class="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all"
            :class="
              tab === t.id
                ? 'bg-violet-600 text-white shadow-md shadow-violet-600/25'
                : 'text-slate-600 hover:bg-slate-100'
            "
            @click="tab = t.id"
          >
            <span aria-hidden="true">{{ t.icon }}</span>
            {{ t.label }}
            <span
              v-if="t.count"
              class="text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center"
              :class="tab === t.id ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'"
            >
              {{ t.count }}
            </span>
          </button>
        </div>
      </div>

      <!-- Nouveau patient -->
      <section v-show="tab === 'patient'" class="max-w-3xl">
        <form class="space-y-6" @submit.prevent="registerPatient">
          <div class="card card-body border-slate-200">
            <h3 class="font-bold text-lg text-slate-900 flex items-center gap-2 mb-1">
              <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-base" aria-hidden="true">🪪</span>
              Identité du patient
            </h3>
            <p class="text-sm text-slate-500 mb-5">Informations civiles pour créer le dossier administratif au comptoir.</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label="Prénom" :error="patientFieldErrors.first_name" required>
                <input
                  v-model="patientForm.first_name"
                  class="form-input"
                  :class="{ 'ring-red-300 border-red-300': patientFieldErrors.first_name }"
                  autocomplete="given-name"
                  placeholder="Ex. Alice"
                  @keydown="blockDigitsInName"
                  @input="stripPatientNameDigits('first_name')"
                  @paste="onPatientNamePaste('first_name', $event)"
                />
              </FormField>
              <FormField label="Nom" :error="patientFieldErrors.last_name" required>
                <input
                  v-model="patientForm.last_name"
                  class="form-input"
                  :class="{ 'ring-red-300 border-red-300': patientFieldErrors.last_name }"
                  autocomplete="family-name"
                  placeholder="Ex. Moreau"
                  @keydown="blockDigitsInName"
                  @input="stripPatientNameDigits('last_name')"
                  @paste="onPatientNamePaste('last_name', $event)"
                />
              </FormField>
              <FormField label="Date de naissance" :error="patientFieldErrors.date_of_birth" required>
                <input
                  v-model="patientForm.date_of_birth"
                  type="date"
                  class="form-input"
                  :class="{ 'ring-red-300 border-red-300': patientFieldErrors.date_of_birth }"
                />
              </FormField>
              <FormField label="Genre" required>
                <select v-model="patientForm.gender" class="form-select">
                  <option value="F">Féminin</option>
                  <option value="M">Masculin</option>
                  <option value="O">Autre</option>
                </select>
              </FormField>
            </div>
          </div>

          <!-- Coordonnées mises en avant -->
          <div class="rounded-2xl border-2 border-violet-300 bg-gradient-to-br from-violet-50 via-white to-indigo-50 shadow-sm overflow-hidden">
            <div class="px-5 sm:px-6 py-4 bg-violet-600/10 border-b border-violet-200">
              <div class="flex items-start gap-3">
                <span class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-violet-600 text-white text-xl shadow-md shadow-violet-600/30" aria-hidden="true">
                  📇
                </span>
                <div>
                  <p class="text-[10px] font-bold uppercase tracking-widest text-violet-700">Obligatoire au comptoir</p>
                  <h3 class="font-bold text-lg text-violet-950 mt-0.5">Coordonnées de contact</h3>
                  <p class="text-sm text-violet-900/80 mt-1 leading-relaxed">
                    L'<strong>email</strong> et le <strong>numéro de téléphone</strong> permettent d'envoyer les notifications
                    de retrait, les rappels d'ordonnance et les confirmations de dispensation.
                  </p>
                </div>
              </div>
            </div>

            <div class="p-5 sm:p-6 space-y-5">
              <FormField
                label="Adresse email"
                :error="patientFieldErrors.email"
                required
                hint="Utilisée pour les alertes patient et la création de compte en ligne ultérieure"
              >
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-lg pointer-events-none" aria-hidden="true">📧</span>
                  <input
                    v-model="patientForm.email"
                    type="email"
                    class="form-input pl-11 text-base font-medium"
                    :class="{ 'ring-2 ring-red-300 border-red-400': patientFieldErrors.email, 'ring-2 ring-violet-200 border-violet-300': !patientFieldErrors.email }"
                    autocomplete="email"
                    placeholder="patient@exemple.com"
                  />
                </div>
              </FormField>

              <FormField
                label="Téléphone mobile"
                :error="patientFieldErrors.phone"
                required
                hint="Format international — République du Congo (+242) par défaut"
              >
                <div
                  class="rounded-xl ring-2 p-1 bg-white"
                  :class="patientFieldErrors.phone ? 'ring-red-300' : 'ring-violet-200'"
                >
                  <PhoneInput
                    v-model="patientForm.phone"
                    :error="patientFieldErrors.phone"
                    required
                  />
                </div>
              </FormField>

              <div class="flex flex-wrap gap-2 pt-1">
                <span class="inline-flex items-center gap-1.5 text-xs font-medium text-violet-800 bg-violet-100 px-3 py-1.5 rounded-full">
                  <span aria-hidden="true">✉️</span> Confirmation par email
                </span>
                <span class="inline-flex items-center gap-1.5 text-xs font-medium text-violet-800 bg-violet-100 px-3 py-1.5 rounded-full">
                  <span aria-hidden="true">📲</span> SMS / appel de retrait
                </span>
                <span class="inline-flex items-center gap-1.5 text-xs font-medium text-violet-800 bg-violet-100 px-3 py-1.5 rounded-full">
                  <span aria-hidden="true">💊</span> Suivi pharmacie
                </span>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap gap-3">
            <button type="submit" class="btn-primary px-8" :disabled="patientSaving">
              {{ patientSaving ? 'Enregistrement…' : '✓ Enregistrer le patient' }}
            </button>
            <button
              type="button"
              class="btn-secondary"
              @click="patientForm = emptyPatientForm(); patientFieldErrors = {}"
            >
              Effacer le formulaire
            </button>
          </div>
        </form>
      </section>

      <!-- File du jour -->
      <section v-show="tab === 'queue'" class="space-y-4">
        <div v-if="prescriptions.length" class="space-y-3">
          <article
            v-for="p in prescriptions"
            :key="p.id"
            class="card card-body border-l-4 border-l-violet-500 hover:shadow-md transition-shadow"
          >
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-2 mb-2">
                  <span class="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100 text-violet-700 font-bold text-sm">
                    {{ (p.patient_name || '?').charAt(0) }}
                  </span>
                  <div class="min-w-0 flex-1">
                    <p class="font-bold text-slate-900 text-lg">{{ p.patient_name }}</p>
                    <p v-if="p.validated_at" class="text-xs text-slate-500">
                      Ordonnance validée · {{ fmtDateTime(p.validated_at) }}
                    </p>
                  </div>
                  <span class="text-[10px] font-bold uppercase tracking-wide bg-violet-100 text-violet-800 px-2.5 py-1 rounded-full shrink-0">
                    À préparer
                  </span>
                </div>

                <!-- Coordonnées patient -->
                <div
                  class="rounded-xl border p-4 mb-3"
                  :class="{
                    'border-emerald-200 bg-emerald-50/70': contactStatus(p) === 'complete',
                    'border-amber-200 bg-amber-50/70': contactStatus(p) === 'partial',
                    'border-red-200 bg-red-50/70': contactStatus(p) === 'missing',
                  }"
                >
                  <p class="text-[10px] font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5"
                    :class="contactStatus(p) === 'missing' ? 'text-red-800' : contactStatus(p) === 'partial' ? 'text-amber-800' : 'text-emerald-800'"
                  >
                    <span aria-hidden="true">📇</span>
                    Coordonnées patient
                    <span v-if="contactStatus(p) === 'missing'" class="normal-case font-semibold">— à compléter</span>
                  </p>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div class="flex items-start gap-2.5 min-w-0">
                      <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm text-base" aria-hidden="true">📧</span>
                      <div class="min-w-0">
                        <p class="text-[10px] font-semibold uppercase text-slate-500">Email</p>
                        <p v-if="p.patient_email" class="text-sm font-semibold text-slate-800 truncate">{{ p.patient_email }}</p>
                        <p v-else class="text-sm font-medium text-red-600">Non renseigné</p>
                      </div>
                    </div>
                    <div class="flex items-start gap-2.5 min-w-0">
                      <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm text-base" aria-hidden="true">📱</span>
                      <div class="min-w-0">
                        <p class="text-[10px] font-semibold uppercase text-slate-500">Téléphone</p>
                        <p v-if="p.patient_phone" class="text-sm font-semibold text-slate-800">{{ p.patient_phone }}</p>
                        <p v-else class="text-sm font-medium text-red-600">Non renseigné</p>
                      </div>
                    </div>
                  </div>
                </div>
                <ul class="mt-3 space-y-2">
                  <li
                    v-for="(item, i) in p.items"
                    :key="i"
                    class="flex items-center gap-3 rounded-xl bg-slate-50 border border-slate-100 px-4 py-2.5 text-sm"
                  >
                    <span class="text-lg shrink-0" aria-hidden="true">💊</span>
                    <div>
                      <p class="font-semibold text-slate-800">{{ item.medicine_name }}</p>
                      <p v-if="item.dosage" class="text-xs text-slate-500">{{ item.dosage }}</p>
                    </div>
                  </li>
                </ul>
              </div>
              <div v-if="canDispense" class="lg:w-48 shrink-0 flex flex-col gap-2">
                <p class="text-xs text-slate-500 leading-relaxed">
                  Dispensez chaque ligne depuis l'onglet Dispensation ou le catalogue.
                </p>
                <button type="button" class="btn-primary w-full text-sm" @click="tab = 'dispense'">
                  Ouvrir dispensation →
                </button>
              </div>
            </div>
          </article>
        </div>

        <EmptyState
          v-else
          title="Aucune ordonnance en attente"
          description="Les prescriptions validées par les médecins apparaîtront ici pour préparation."
          icon="📋"
        />

        <div v-if="movements.length" class="card card-body mt-6">
          <h3 class="font-bold text-slate-800 mb-4 flex items-center gap-2">
            <span aria-hidden="true">🕐</span> Derniers mouvements
          </h3>
          <div class="space-y-2">
            <div
              v-for="m in movements.slice(0, 5)"
              :key="m.id"
              class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm"
              :class="m.movement_type === 'IN' ? 'bg-emerald-50/80' : 'bg-red-50/60'"
            >
              <span
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-bold text-xs"
                :class="m.movement_type === 'IN' ? 'bg-emerald-200 text-emerald-800' : 'bg-red-200 text-red-800'"
              >
                {{ m.movement_type === 'IN' ? '↓' : '↑' }}
              </span>
              <div class="flex-1 min-w-0">
                <p class="font-medium text-slate-800 truncate">{{ m.medicine_name }}</p>
                <p class="text-xs text-slate-500">{{ m.reason }} · {{ fmtDateTime(m.created_at) }}</p>
              </div>
              <span
                class="font-bold tabular-nums shrink-0"
                :class="m.movement_type === 'IN' ? 'text-emerald-700' : 'text-red-700'"
              >
                {{ m.movement_type === 'IN' ? '+' : '−' }}{{ m.quantity }}
              </span>
            </div>
          </div>
          <button type="button" class="mt-4 text-sm font-semibold text-violet-700 hover:underline" @click="tab = 'movements'">
            Historique complet →
          </button>
        </div>
      </section>

      <!-- Catalogue -->
      <section v-show="tab === 'catalog'" class="space-y-4">
        <div class="card card-body">
          <div class="flex flex-col lg:flex-row gap-3 lg:items-center">
            <div class="relative flex-1 max-w-lg">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">🔍</span>
              <input
                v-model="searchQuery"
                type="search"
                class="form-input pl-10 w-full"
                placeholder="Rechercher produit, code DCI ou forme…"
              />
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="f in [
                  { id: 'all', label: 'Tous' },
                  { id: 'ok', label: 'Disponibles' },
                  { id: 'low', label: 'Alertes' },
                ]"
                :key="f.id"
                type="button"
                class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors"
                :class="catalogFilter === f.id ? 'bg-violet-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
                @click="catalogFilter = f.id"
              >
                {{ f.label }}
              </button>
            </div>
          </div>
        </div>

        <DataTable
          :headers="catalogHeaders"
          :rows="catalogRows"
          empty-title="Aucun produit"
          empty-description="Lancez seed_sghl pour charger le catalogue hospitalier."
        >
          <template #cell-code="{ row }">
            <span class="font-mono text-xs font-semibold text-violet-700 bg-violet-50 px-2 py-1 rounded-md">
              {{ row.code }}
            </span>
          </template>
          <template #cell-name="{ row }">
            <div class="flex items-center gap-3">
              <span
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-lg ring-1 ring-violet-100"
                aria-hidden="true"
              >
                {{ formIcon(row.form) }}
              </span>
              <div>
                <p class="font-semibold text-slate-900">{{ row.name }}</p>
                <p class="text-xs text-slate-400">{{ row.unit }}</p>
              </div>
            </div>
          </template>
          <template #cell-form="{ row }">
            <span class="text-sm text-slate-600 capitalize">{{ row.form }}</span>
          </template>
          <template #cell-stock_total="{ row }">
            <span class="inline-flex items-center gap-2">
              <span class="font-bold tabular-nums text-lg">{{ row.stock_total }}</span>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ring-1" :class="stockBadge(row.stock_status).cls">
                {{ stockBadge(row.stock_status).label }}
              </span>
            </span>
          </template>
          <template #cell-unit_price="{ row }">
            <span class="font-medium text-slate-700 tabular-nums">{{ row.unit_price }}</span>
          </template>
          <template #actions="{ row }">
            <div class="flex flex-wrap gap-1 justify-end">
              <button
                v-if="canDispense && row.stock_total > 0"
                type="button"
                class="rounded-lg bg-violet-600 text-white text-xs font-semibold px-3 py-1.5 hover:bg-violet-700 transition-colors"
                @click="pickForDispense(row)"
              >
                Dispenser
              </button>
              <button
                v-if="canManageStock"
                type="button"
                class="rounded-lg bg-slate-100 text-slate-700 text-xs font-semibold px-3 py-1.5 hover:bg-slate-200 transition-colors"
                @click="pickForReception(row)"
              >
                + Lot
              </button>
            </div>
          </template>
        </DataTable>
      </section>

      <!-- Stock -->
      <section v-show="tab === 'stock'" class="space-y-4">
        <div class="card card-body">
          <input
            v-model="stockSearch"
            type="search"
            class="form-input max-w-md"
            placeholder="Filtrer par produit ou numéro de lot…"
          />
        </div>

        <div v-if="filteredStockRows.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-4">
          <article
            v-for="lot in filteredStockRows.slice(0, 6)"
            :key="lot.id"
            class="card card-body border-t-4"
            :class="lot.days_to_expiry <= 30 ? 'border-t-red-500' : lot.days_to_expiry <= 90 ? 'border-t-amber-500' : 'border-t-emerald-500'"
          >
            <p class="font-bold text-slate-900 truncate">{{ lot.medicine_name }}</p>
            <p class="text-xs font-mono text-violet-600 mt-0.5">{{ lot.lot_number }}</p>
            <div class="mt-3 flex justify-between text-sm">
              <span class="text-slate-500">Quantité</span>
              <span class="font-bold">{{ lot.quantity }}</span>
            </div>
            <div class="mt-1 flex justify-between text-sm">
              <span class="text-slate-500">Emplacement</span>
              <span class="font-medium">{{ lot.location || '—' }}</span>
            </div>
            <div class="mt-3 pt-3 border-t border-slate-100">
              <div class="flex justify-between items-center text-xs mb-1.5">
                <span class="text-slate-500">Péremption {{ fmtDate(lot.expiry_date) }}</span>
                <span class="font-bold px-2 py-0.5 rounded-full" :class="expiryBadge(lot.days_to_expiry).cls">
                  J-{{ lot.days_to_expiry }}
                </span>
              </div>
              <div class="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  class="h-full rounded-full"
                  :class="expiryBadge(lot.days_to_expiry).bar"
                  :style="{ width: `${Math.min(100, expiryBadge(lot.days_to_expiry).pct)}%` }"
                />
              </div>
            </div>
          </article>
        </div>

        <DataTable
          :headers="stockHeaders"
          :rows="stockRows"
          empty-title="Stock vide"
          empty-description="Enregistrez une réception pour alimenter les lots."
        >
          <template #cell-expiry_date="{ row }">
            <span>{{ row.expiry_date }}</span>
            <span
              class="inline-block text-[10px] font-bold mt-0.5 px-2 py-0.5 rounded-full"
              :class="expiryBadge(row.days_to_expiry).cls"
            >
              {{ expiryBadge(row.days_to_expiry).label }} · J-{{ row.days_to_expiry }}
            </span>
          </template>
        </DataTable>
      </section>

      <!-- Réception -->
      <section v-show="tab === 'reception'">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <form
            v-if="canManageStock"
            class="lg:col-span-2 card card-body space-y-5 border-violet-100"
            @submit.prevent="addLot"
          >
            <div>
              <h3 class="font-bold text-xl text-slate-900 flex items-center gap-2">
                <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-lg" aria-hidden="true">📥</span>
                Réception de stock
              </h3>
              <p class="text-sm text-slate-500 mt-1">Enregistrez un nouveau lot ou complétez un lot existant.</p>
            </div>
            <label class="block">
              <span class="form-label">Produit</span>
              <select v-model="lotForm.medicine_id" class="form-select" required>
                <option value="">Sélectionner un produit…</option>
                <option v-for="m in medicines" :key="m.id" :value="m.id">
                  {{ m.code }} — {{ m.name }} ({{ m.stock_total }} en stock)
                </option>
              </select>
            </label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label class="block">
                <span class="form-label">N° de lot</span>
                <input v-model="lotForm.lot_number" class="form-input" required placeholder="LOT-2026-001" />
              </label>
              <label class="block">
                <span class="form-label">Date de péremption</span>
                <input v-model="lotForm.expiry_date" type="date" class="form-input" required />
              </label>
              <label class="block">
                <span class="form-label">Quantité reçue</span>
                <input v-model.number="lotForm.quantity" type="number" min="1" class="form-input" />
              </label>
              <label class="block">
                <span class="form-label">Emplacement rayonnage</span>
                <input v-model="lotForm.location" class="form-input" placeholder="Ex. A1, D1-S (stupéfiants)" />
              </label>
            </div>
            <button type="submit" class="btn-primary w-full sm:w-auto" :disabled="submitting">
              {{ submitting ? 'Enregistrement…' : '✓ Valider la réception' }}
            </button>
          </form>

          <aside v-if="canManageStock" class="card card-body bg-gradient-to-br from-violet-50 to-indigo-50 border-violet-100 h-fit">
            <h4 class="font-bold text-violet-900 mb-3">Bonnes pratiques</h4>
            <ul class="space-y-3 text-sm text-violet-900/80">
              <li class="flex gap-2"><span aria-hidden="true">✓</span> Vérifier l'étiquetage et la date de péremption à la réception.</li>
              <li class="flex gap-2"><span aria-hidden="true">✓</span> Stupéfiants : emplacement sécurisé (D1-S, D2-U).</li>
              <li class="flex gap-2"><span aria-hidden="true">✓</span> Un lot identique est fusionné automatiquement.</li>
            </ul>
          </aside>

          <EmptyState v-else class="lg:col-span-3" title="Accès réservé" description="Permission gestion de stock requise." icon="🔒" />
        </div>
      </section>

      <!-- Dispensation -->
      <section v-show="tab === 'dispense'">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <form
            v-if="canDispense"
            class="lg:col-span-2 card card-body space-y-5 border-emerald-100"
            @submit.prevent="dispense()"
          >
            <div>
              <h3 class="font-bold text-xl text-slate-900 flex items-center gap-2">
                <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-lg" aria-hidden="true">📤</span>
                Dispensation
              </h3>
              <p class="text-sm text-slate-500 mt-1">
                Sortie FIFO — le lot dont la péremption est la plus proche est utilisé en priorité.
              </p>
            </div>
            <label class="block">
              <span class="form-label">Produit à dispenser</span>
              <select v-model="dispenseForm.medicine_id" class="form-select" required>
                <option value="">Sélectionner…</option>
                <option v-for="m in medicines.filter((x) => x.stock_total > 0)" :key="m.id" :value="m.id">
                  {{ formIcon(m.form) }} {{ m.name }} — {{ m.stock_total }} disponible(s)
                </option>
              </select>
            </label>
            <div
              v-if="selectedMedicine"
              class="rounded-xl bg-slate-50 border border-slate-100 p-4 flex items-center gap-4"
            >
              <span class="text-3xl" aria-hidden="true">{{ formIcon(selectedMedicine.form) }}</span>
              <div>
                <p class="font-bold text-slate-900">{{ selectedMedicine.name }}</p>
                <p class="text-sm text-slate-500">
                  {{ selectedMedicine.code }} · Stock actuel :
                  <strong class="text-emerald-700">{{ selectedMedicine.stock_total }}</strong>
                </p>
              </div>
            </div>
            <label class="block max-w-xs">
              <span class="form-label">Quantité</span>
              <input v-model.number="dispenseForm.quantity" type="number" min="1" class="form-input text-lg font-bold" />
            </label>
            <button type="submit" class="btn-primary w-full sm:w-auto bg-emerald-600 hover:bg-emerald-700" :disabled="submitting">
              {{ submitting ? 'Dispensation…' : '✓ Confirmer la sortie' }}
            </button>
          </form>

          <aside v-if="canDispense" class="card card-body bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-100 h-fit">
            <h4 class="font-bold text-emerald-900 mb-3">Rappel réglementaire</h4>
            <ul class="space-y-3 text-sm text-emerald-900/80">
              <li class="flex gap-2"><span aria-hidden="true">📋</span> Vérifier l'ordonnance validée avant toute sortie.</li>
              <li class="flex gap-2"><span aria-hidden="true">🔒</span> Chaque mouvement est tracé et horodaté.</li>
              <li class="flex gap-2"><span aria-hidden="true">⏳</span> Lots expirés exclus automatiquement.</li>
            </ul>
          </aside>

          <EmptyState v-else class="lg:col-span-3" title="Accès réservé" description="Permission dispensation requise." icon="🔒" />
        </div>
      </section>

      <!-- Mouvements -->
      <section v-show="tab === 'movements'" class="space-y-4">
        <div v-if="movementRows.length" class="relative pl-6 border-l-2 border-slate-200 space-y-4 ml-2">
          <article
            v-for="m in movementRows"
            :key="m.id"
            class="relative card card-body !py-4"
          >
            <span
              class="absolute -left-[1.6rem] top-5 flex h-8 w-8 items-center justify-center rounded-full ring-4 ring-white text-xs font-bold"
              :class="m.movement_type === 'IN' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'"
              aria-hidden="true"
            >
              {{ m.movement_type === 'IN' ? '↓' : '↑' }}
            </span>
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <p class="font-bold text-slate-900">{{ m.medicine_name }}</p>
                <p class="text-sm text-slate-500">
                  Lot {{ m.lot_number }} · {{ m.reason }}
                </p>
              </div>
              <div class="flex items-center gap-3 shrink-0">
                <span
                  class="text-lg font-bold tabular-nums"
                  :class="m.movement_type === 'IN' ? 'text-emerald-600' : 'text-red-600'"
                >
                  {{ m.quantity }}
                </span>
                <time class="text-xs text-slate-400">{{ m.created_at }}</time>
              </div>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="Aucun mouvement enregistré"
          description="Les entrées (réception) et sorties (dispensation) apparaîtront ici."
          icon="🕐"
        />
      </section>
    </template>
  </div>
</template>
