<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import { useAuthStore } from '../stores/auth'
import { formatMoney } from '../composables/currency'

const auth = useAuthStore()
const canOrder = computed(() => auth.hasPerm('lab.order'))
const canProcess = computed(() => auth.hasPerm('lab.enter_results'))
const canValidate = computed(() => auth.hasPerm('lab.validate_results'))
const canPublish = computed(() => auth.hasPerm('lab.publish_results'))

const tab = ref('workflow')
const loading = ref(true)
const error = ref('')
const success = ref('')

const overview = ref({ test_count: 0, orders_pending: 0, orders_urgent: 0, orders_validated_today: 0, orders_published: 0 })
const orders = ref([])
const tests = ref([])
const patients = ref([])
const statusFilter = ref('')
const searchQuery = ref('')
const testSearch = ref('')

const orderForm = ref({ patient_id: '', test_type_id: '', priority: 'NORMAL', clinical_notes: '' })
const resultForms = ref({})

const SAMPLE_LABELS = {
  blood: 'Sang',
  urine: 'Urines',
  stool: 'Selles',
  other: 'Autre',
}

const STATUS_STEPS = ['ORDERED', 'COLLECTED', 'ASSIGNED', 'RESULTS_ENTERED', 'VALIDATED', 'PUBLISHED']
const STATUS_LABELS = {
  ORDERED: 'Commandé',
  COLLECTED: 'Prélevé',
  ASSIGNED: 'Affecté',
  RESULTS_ENTERED: 'Résultats saisis',
  VALIDATED: 'Validé',
  PUBLISHED: 'Publié',
}

const actions = {
  ORDERED: { action: 'collect', perm: 'enter_results', label: 'Prélèvement' },
  COLLECTED: { action: 'assign', perm: 'enter_results', label: 'Affecter au labo' },
  ASSIGNED: { action: 'results', perm: 'enter_results', label: 'Saisir résultats' },
  RESULTS_ENTERED: { action: 'validate', perm: 'validate_results', label: 'Valider (biologiste)' },
  VALIDATED: { action: 'publish', perm: 'publish_results', label: 'Publier + PDF patient' },
}

const testHeaders = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Examen' },
  { key: 'sample_type', label: 'Échantillon' },
  { key: 'price', label: 'Tarif' },
]

const testRows = computed(() =>
  tests.value.map((t) => ({
    ...t,
    sample_type: SAMPLE_LABELS[t.sample_type] || t.sample_type,
    price: formatMoney(t.price),
  })),
)

function fmtDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function statusIndex(status) {
  return STATUS_STEPS.indexOf(status)
}

function canRunAction(order, cfg) {
  if (cfg.perm === 'enter_results') return canProcess.value
  if (cfg.perm === 'validate_results') return canValidate.value
  if (cfg.perm === 'publish_results') return canPublish.value
  return false
}

function defaultResultData(testCode) {
  const templates = {
    NFS: { hb: '', gb: '', plt: '' },
    GLY: { glycemie_g_l: '' },
    CRP: { crp_mg_l: '' },
  }
  return JSON.stringify(templates[testCode] || { valeur: '' }, null, 0)
}

function getResultForm(orderId, testCode) {
  if (!resultForms.value[orderId]) {
    resultForms.value[orderId] = {
      result_data: defaultResultData(testCode),
      interpretation: 'Dans les normes',
    }
  }
  return resultForms.value[orderId]
}

async function loadTests() {
  const { data } = await api.get('/laboratory/tests/', { params: { search: testSearch.value.trim() } })
  tests.value = data
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
    const reqs = [
      api.get('/laboratory/overview/'),
      api.get('/laboratory/orders/', { params }),
      api.get('/laboratory/tests/'),
    ]
    if (canOrder.value) {
      reqs.push(api.get('/clinical/patients/'))
    }
    const results = await Promise.all(reqs)
    overview.value = results[0].data
    orders.value = results[1].data
    tests.value = results[2].data
    patients.value = results[3]?.data || []
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function createOrder() {
  error.value = ''
  success.value = ''
  try {
    await api.post('/laboratory/orders/', orderForm.value)
    orderForm.value = { patient_id: '', test_type_id: '', priority: 'NORMAL', clinical_notes: '' }
    success.value = 'Commande labo enregistrée — workflow LIS démarré.'
    tab.value = 'workflow'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur commande.'
  }
}

async function advance(order, cfg) {
  error.value = ''
  success.value = ''
  try {
    if (cfg.action === 'results') {
      const form = getResultForm(order.id, order.test_code)
      const data = JSON.parse(form.result_data || '{}')
      await api.post(`/laboratory/orders/${order.id}/results/`, {
        result_data: data,
        interpretation: form.interpretation || 'Dans les normes',
      })
      success.value = 'Résultats enregistrés.'
    } else {
      await api.post(`/laboratory/orders/${order.id}/${cfg.action}/`)
      success.value =
        cfg.action === 'publish'
          ? 'Résultat publié — PDF disponible dans le dossier patient.'
          : 'Étape enregistrée.'
    }
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible.'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Service Laboratoire — LIS"
      subtitle="Commande → Prélèvement → Analyse → Validation biologiste → Publication PDF"
    />

    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- KPI -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        <div class="card card-body !py-4 text-center">
          <p class="text-2xl font-bold text-cyan-700">{{ overview.test_count }}</p>
          <p class="text-xs text-slate-500 mt-1">Examens au catalogue</p>
        </div>
        <div class="card card-body !py-4 text-center">
          <p class="text-2xl font-bold text-amber-600">{{ overview.orders_pending }}</p>
          <p class="text-xs text-slate-500 mt-1">En cours de traitement</p>
        </div>
        <div class="card card-body !py-4 text-center">
          <p class="text-2xl font-bold text-red-600">{{ overview.orders_urgent }}</p>
          <p class="text-xs text-slate-500 mt-1">Urgentes</p>
        </div>
        <div class="card card-body !py-4 text-center">
          <p class="text-2xl font-bold text-violet-700">{{ overview.orders_validated_today }}</p>
          <p class="text-xs text-slate-500 mt-1">Validées aujourd'hui</p>
        </div>
        <div class="card card-body !py-4 text-center col-span-2 lg:col-span-1">
          <p class="text-2xl font-bold text-emerald-700">{{ overview.orders_published }}</p>
          <p class="text-xs text-slate-500 mt-1">Publiées (PDF)</p>
        </div>
      </div>

      <div class="flex flex-wrap gap-2 mb-4">
        <button
          v-for="t in [
            { id: 'workflow', label: 'File d\'attente' },
            { id: 'order', label: 'Nouvelle commande' },
            { id: 'catalog', label: 'Catalogue examens' },
          ]"
          :key="t.id"
          type="button"
          :class="tab === t.id ? 'tab-btn-active' : 'tab-btn-inactive'"
          class="tab-btn"
          @click="tab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- Workflow -->
      <section v-show="tab === 'workflow'" class="space-y-4">
        <div class="flex flex-col sm:flex-row gap-3">
          <input
            v-model="searchQuery"
            type="search"
            class="form-input flex-1 max-w-sm"
            placeholder="Rechercher patient ou examen…"
            @keyup.enter="load"
          />
          <select v-model="statusFilter" class="form-select max-w-xs" @change="load">
            <option value="">Tous les statuts</option>
            <option v-for="s in STATUS_STEPS" :key="s" :value="s">{{ STATUS_LABELS[s] }}</option>
          </select>
          <button type="button" class="btn-primary shrink-0" @click="load">Actualiser</button>
        </div>

        <div v-if="orders.length" class="space-y-4">
          <article
            v-for="o in orders"
            :key="o.id"
            class="card card-body border-l-4"
            :class="o.priority === 'URGENT' ? 'border-l-red-500' : 'border-l-cyan-500'"
          >
            <div class="flex flex-col lg:flex-row lg:justify-between gap-4">
              <div class="flex-1">
                <div class="flex flex-wrap items-center gap-2 mb-1">
                  <p class="font-semibold text-lg">{{ o.test_name }}</p>
                  <span class="text-xs font-mono text-slate-400">{{ o.test_code }}</span>
                  <StatusBadge :status="o.status" />
                  <span
                    v-if="o.priority === 'URGENT'"
                    class="text-xs font-bold text-red-700 bg-red-50 px-2 py-0.5 rounded-full"
                  >
                    URGENT
                  </span>
                </div>
                <p class="text-sm text-slate-600">
                  <strong>{{ o.patient_name || 'Patient' }}</strong>
                  · {{ fmtDateTime(o.created_at) }}
                </p>
                <p v-if="o.clinical_notes" class="text-sm text-slate-500 mt-1 italic">{{ o.clinical_notes }}</p>

                <!-- Pipeline -->
                <div class="flex flex-wrap gap-1 mt-3">
                  <span
                    v-for="(step, idx) in STATUS_STEPS"
                    :key="step"
                    class="text-[10px] px-2 py-0.5 rounded-full"
                    :class="
                      idx <= statusIndex(o.status)
                        ? 'bg-cyan-100 text-cyan-800 font-medium'
                        : 'bg-slate-100 text-slate-400'
                    "
                  >
                    {{ STATUS_LABELS[step] }}
                  </span>
                </div>
              </div>

              <div v-if="actions[o.status] && canRunAction(o, actions[o.status])" class="lg:w-72 shrink-0 space-y-2">
                <template v-if="actions[o.status].action === 'results'">
                  <textarea
                    v-model="getResultForm(o.id, o.test_code).result_data"
                    class="form-input text-xs font-mono min-h-[60px]"
                    placeholder='{"valeur": "..."}'
                  />
                  <input
                    v-model="getResultForm(o.id, o.test_code).interpretation"
                    class="form-input text-sm"
                    placeholder="Interprétation"
                  />
                </template>
                <button
                  type="button"
                  class="btn-primary w-full text-sm"
                  @click="advance(o, actions[o.status])"
                >
                  {{ actions[o.status].label }} →
                </button>
              </div>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="Aucune commande"
          :description="canOrder ? 'Créez une commande dans l\'onglet « Nouvelle commande ».' : 'Les commandes médecin apparaîtront ici.'"
          icon="🔬"
        />
      </section>

      <!-- Commande -->
      <section v-show="tab === 'order'">
        <form
          v-if="canOrder"
          @submit.prevent="createOrder"
          class="card card-body max-w-2xl space-y-4"
        >
          <h3 class="font-semibold text-lg">Commander un examen</h3>
          <label>
            <span class="form-label">Patient</span>
            <select v-model="orderForm.patient_id" class="form-select" required>
              <option value="">Sélectionner…</option>
              <option v-for="p in patients" :key="p.id" :value="p.id">{{ p.last_name }} {{ p.first_name }}</option>
            </select>
          </label>
          <label>
            <span class="form-label">Examen</span>
            <select v-model="orderForm.test_type_id" class="form-select" required>
              <option value="">Sélectionner…</option>
              <option v-for="t in tests" :key="t.id" :value="t.id">
                {{ t.code }} — {{ t.name }} ({{ formatMoney(t.price) }})
              </option>
            </select>
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label>
              <span class="form-label">Priorité</span>
              <select v-model="orderForm.priority" class="form-select">
                <option value="NORMAL">Normal</option>
                <option value="URGENT">Urgent</option>
              </select>
            </label>
          </div>
          <label>
            <span class="form-label">Notes cliniques</span>
            <input v-model="orderForm.clinical_notes" class="form-input" placeholder="Contexte, jeûne, traitement en cours…" />
          </label>
          <button type="submit" class="btn-primary">Envoyer au laboratoire</button>
        </form>
        <EmptyState v-else title="Réservé aux médecins" description="Permission lab.order requise." icon="🩺" />
      </section>

      <!-- Catalogue -->
      <section v-show="tab === 'catalog'" class="space-y-4">
        <input
          v-model="testSearch"
          type="search"
          class="form-input max-w-md"
          placeholder="Rechercher un examen…"
          @input="loadTests"
        />
        <DataTable
          :headers="testHeaders"
          :rows="testRows"
          empty-title="Catalogue vide"
          empty-description="Exécutez seed_sghl pour charger les examens."
        />
        <p class="text-xs text-slate-500">
          Dolisie — Étage 1 · Prélèvements salle 101 · Plateau technique salle 102 · 7h–19h
        </p>
      </section>
    </template>
  </div>
</template>
