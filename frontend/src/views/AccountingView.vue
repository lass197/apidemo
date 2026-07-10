<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import { formatMoney } from '../composables/currency'
import { usePermissions } from '../composables/usePermissions'

const { can } = usePermissions()

const invoices = ref([])
const journal = ref([])
const prices = ref([])
const tab = ref('overview')
const loading = ref(true)
const error = ref('')
const success = ref('')
const savingAdj = ref(false)

const adjForm = ref({
  invoice_id: '',
  account_code: '471',
  label: '',
  entry_type: 'DEBIT',
  amount: '',
  reason: '',
})

const canAdjust = computed(() => can('billing.adjust'))

const kpi = computed(() => {
  const unpaid = invoices.value.filter((i) => parseFloat(i.balance_due) > 0 && i.status !== 'CANCELLED')
  const totalDue = unpaid.reduce((s, i) => s + parseFloat(i.balance_due), 0)
  const declaredPaid = invoices.value.filter((i) => i.patient_declaration?.status === 'PAID').length
  const declaredUnpaid = invoices.value.filter((i) => i.patient_declaration?.status === 'UNPAID').length
  const adjustments = journal.value.filter((e) => e.is_adjustment).length
  return {
    total: invoices.value.length,
    unpaidCount: unpaid.length,
    totalDue,
    paid: invoices.value.filter((i) => i.status === 'PAID').length,
    declaredPaid,
    declaredUnpaid,
    adjustments,
    journalEntries: journal.value.length,
  }
})

const pendingDeclarations = computed(() =>
  invoices.value.filter(
    (i) =>
      i.patient_declaration?.status === 'PAID'
      && parseFloat(i.balance_due) > 0
      && i.status !== 'CANCELLED',
  ),
)

function patientDeclBadge(decl) {
  if (!decl) return null
  if (decl.status === 'PAID') {
    return { label: 'Payé (patient)', cls: 'bg-emerald-100 text-emerald-800', detail: `${decl.method} · ${decl.phone_number}` }
  }
  return { label: 'Impayé (patient)', cls: 'bg-amber-100 text-amber-900', detail: `${decl.method} · ${decl.phone_number}` }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const requests = [
      api.get('/billing/invoices/'),
      api.get('/billing/accounting/journal/'),
      api.get('/billing/prices/'),
    ]
    const [inv, j, p] = await Promise.all(requests)
    invoices.value = inv.data
    journal.value = j.data
    prices.value = p.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function submitAdjustment() {
  if (!canAdjust.value) return
  error.value = ''
  success.value = ''
  savingAdj.value = true
  try {
    await api.post('/billing/accounting/adjustments/', { ...adjForm.value })
    adjForm.value = {
      invoice_id: '',
      account_code: '471',
      label: '',
      entry_type: 'DEBIT',
      amount: '',
      reason: '',
    }
    success.value = 'Ajustement comptable enregistré.'
    await load()
    tab.value = 'journal'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ajustement refusé.'
  } finally {
    savingAdj.value = false
  }
}

async function downloadPdf(inv) {
  try {
    const response = await api.get(`/billing/invoices/${inv.id}/pdf/`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${inv.invoice_number}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e.response?.data?.detail || 'PDF indisponible.'
  }
}

onMounted(load)
</script>

<template>
  <div class="pb-8">
    <PageHeader
      title="Comptabilité"
      subtitle="Suivi financier, journal des écritures et ajustements — espace comptable SGHL"
    />

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
    <AlertBanner v-if="success" type="success" class="mb-4">{{ success }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div class="card card-body !py-4 border-l-4 border-l-indigo-500">
          <p class="text-2xl font-bold text-indigo-700 tabular-nums">{{ kpi.total }}</p>
          <p class="text-xs text-slate-500 mt-1">Factures enregistrées</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-red-500">
          <p class="text-xl font-bold text-red-700 tabular-nums">{{ formatMoney(kpi.totalDue) }}</p>
          <p class="text-xs text-slate-500 mt-1">Encours patient ({{ kpi.unpaidCount }})</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-amber-500">
          <p class="text-2xl font-bold text-amber-700 tabular-nums">{{ pendingDeclarations.length }}</p>
          <p class="text-xs text-slate-500 mt-1">Déclarations « payé » à rapprocher</p>
        </div>
        <div class="card card-body !py-4 border-l-4 border-l-emerald-500">
          <p class="text-2xl font-bold text-emerald-700 tabular-nums">{{ kpi.journalEntries }}</p>
          <p class="text-xs text-slate-500 mt-1">Écritures journal ({{ kpi.adjustments }} ajust.)</p>
        </div>
      </div>

      <div class="card !p-2 mb-6">
        <div class="flex flex-wrap gap-1.5 p-1">
          <button
            v-for="t in [
              { id: 'overview', label: '📊 Vue d\'ensemble' },
              { id: 'invoices', label: '🧾 Factures' },
              { id: 'declarations', label: '📱 Déclarations patient' },
              { id: 'journal', label: '📒 Journal' },
              ...(canAdjust ? [{ id: 'adjustments', label: '✏️ Ajustements' }] : []),
              { id: 'prices', label: '🏷️ Tarifs' },
            ]"
            :key="t.id"
            type="button"
            class="rounded-xl px-4 py-2.5 text-sm font-semibold transition-all"
            :class="tab === t.id ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-600 hover:bg-slate-100'"
            @click="tab = t.id"
          >
            {{ t.label }}
          </button>
        </div>
      </div>

      <!-- Vue d'ensemble -->
      <div v-show="tab === 'overview'" class="space-y-6">
        <section class="card card-body">
          <h3 class="font-semibold mb-3">Répartition des factures</h3>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div class="rounded-xl bg-emerald-50 px-4 py-3">
              <p class="text-2xl font-bold text-emerald-700">{{ kpi.paid }}</p>
              <p class="text-xs text-slate-500">Soldées</p>
            </div>
            <div class="rounded-xl bg-amber-50 px-4 py-3">
              <p class="text-2xl font-bold text-amber-700">{{ kpi.unpaidCount }}</p>
              <p class="text-xs text-slate-500">En attente</p>
            </div>
            <div class="rounded-xl bg-teal-50 px-4 py-3">
              <p class="text-2xl font-bold text-teal-700">{{ kpi.declaredPaid }}</p>
              <p class="text-xs text-slate-500">Décl. payé (patient)</p>
            </div>
            <div class="rounded-xl bg-slate-50 px-4 py-3">
              <p class="text-2xl font-bold text-slate-700">{{ kpi.declaredUnpaid }}</p>
              <p class="text-xs text-slate-500">Décl. impayé</p>
            </div>
          </div>
        </section>

        <section v-if="pendingDeclarations.length" class="card overflow-hidden border-amber-200">
          <div class="px-5 py-4 border-b bg-amber-50/80">
            <h3 class="font-bold text-amber-900">À rapprocher — patient a déclaré « payé »</h3>
            <p class="text-xs text-amber-800/80 mt-1">
              Vérifiez le Mobile Money puis demandez au secrétariat l'encaissement si le paiement est confirmé.
            </p>
          </div>
          <div class="divide-y divide-slate-100">
            <div
              v-for="i in pendingDeclarations.slice(0, 5)"
              :key="i.id"
              class="px-5 py-3 flex flex-wrap justify-between gap-2 text-sm"
            >
              <div>
                <span class="font-mono font-semibold text-indigo-800">{{ i.invoice_number }}</span>
                <span class="text-slate-600 ml-2">{{ i.patient_name }}</span>
              </div>
              <span class="font-bold text-red-700">{{ formatMoney(i.balance_due) }} restant</span>
            </div>
          </div>
        </section>
      </div>

      <!-- Factures -->
      <div v-show="tab === 'invoices'" class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="text-left p-4 font-semibold">N° facture</th>
                <th class="text-left p-4 font-semibold">Patient</th>
                <th class="text-left p-4 font-semibold">Statut</th>
                <th class="text-right p-4 font-semibold">Part patient</th>
                <th class="text-right p-4 font-semibold">Reste dû</th>
                <th class="p-4 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="i in invoices"
                :key="i.id"
                class="border-t border-slate-100 hover:bg-slate-50/50"
              >
                <td class="p-4 font-mono font-semibold text-indigo-800">{{ i.invoice_number }}</td>
                <td class="p-4 font-medium">{{ i.patient_name || '—' }}</td>
                <td class="p-4"><StatusBadge :status="i.status" /></td>
                <td class="p-4 text-right tabular-nums">{{ formatMoney(i.patient_amount) }}</td>
                <td class="p-4 text-right">
                  <span
                    class="font-bold tabular-nums"
                    :class="parseFloat(i.balance_due) > 0 ? 'text-red-700' : 'text-emerald-700'"
                  >
                    {{ formatMoney(i.balance_due) }}
                  </span>
                </td>
                <td class="p-4 text-right">
                  <button type="button" class="text-indigo-700 text-xs font-semibold hover:underline" @click="downloadPdf(i)">
                    PDF
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!invoices.length" class="p-10 text-center text-slate-500">Aucune facture.</p>
      </div>

      <!-- Déclarations patient -->
      <div v-show="tab === 'declarations'" class="card overflow-hidden">
        <div class="px-5 py-4 border-b bg-slate-50/80">
          <h3 class="font-bold">Déclarations Mobile Money (patient)</h3>
          <p class="text-xs text-slate-500 mt-1">Lecture seule — le secrétariat enregistre l'encaissement après vérification.</p>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="text-left p-4 font-semibold">Facture</th>
                <th class="text-left p-4 font-semibold">Patient</th>
                <th class="text-left p-4 font-semibold">Déclaration</th>
                <th class="text-right p-4 font-semibold">Reste dû</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="i in invoices.filter((inv) => inv.patient_declaration)"
                :key="i.id"
                class="border-t border-slate-100"
              >
                <td class="p-4 font-mono font-semibold">{{ i.invoice_number }}</td>
                <td class="p-4">{{ i.patient_name }}</td>
                <td class="p-4">
                  <span
                    v-if="patientDeclBadge(i.patient_declaration)"
                    class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                    :class="patientDeclBadge(i.patient_declaration).cls"
                  >
                    {{ patientDeclBadge(i.patient_declaration).label }}
                  </span>
                  <p class="text-[10px] text-slate-500 mt-1">{{ patientDeclBadge(i.patient_declaration)?.detail }}</p>
                </td>
                <td class="p-4 text-right font-bold" :class="parseFloat(i.balance_due) > 0 ? 'text-red-700' : 'text-emerald-700'">
                  {{ formatMoney(i.balance_due) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!invoices.some((i) => i.patient_declaration)" class="p-10 text-center text-slate-500">
          Aucune déclaration patient pour le moment.
        </p>
      </div>

      <!-- Journal -->
      <div v-show="tab === 'journal'" class="card overflow-hidden">
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
              <tr
                v-for="e in journal"
                :key="e.id"
                class="border-t"
                :class="{ 'bg-amber-50/60': e.is_adjustment }"
              >
                <td class="p-4 text-slate-600">{{ e.entry_date }}</td>
                <td class="p-4 font-mono text-xs">{{ e.account_code }}</td>
                <td class="p-4">
                  {{ e.label }}
                  <span v-if="e.is_adjustment" class="ml-2 text-[10px] font-bold uppercase text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">Ajust.</span>
                </td>
                <td class="p-4 text-right font-semibold" :class="e.entry_type === 'DEBIT' ? 'text-emerald-600' : 'text-red-600'">
                  {{ e.entry_type === 'DEBIT' ? '+' : '−' }}{{ formatMoney(e.amount) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!journal.length" class="p-8 text-center text-slate-500">Journal vide.</p>
      </div>

      <!-- Ajustements -->
      <div v-show="tab === 'adjustments' && canAdjust" class="space-y-6">
        <form
          class="card card-body grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-4xl"
          @submit.prevent="submitAdjustment"
        >
          <h3 class="sm:col-span-3 font-semibold text-slate-900">Ajustement manuel du journal</h3>
          <select v-model="adjForm.invoice_id" class="form-select" required>
            <option value="">Facture liée</option>
            <option v-for="i in invoices" :key="i.id" :value="i.id">{{ i.invoice_number }} — {{ i.patient_name }}</option>
          </select>
          <input v-model="adjForm.account_code" placeholder="Compte (ex. 471)" class="form-input" required />
          <select v-model="adjForm.entry_type" class="form-select">
            <option value="DEBIT">Débit</option>
            <option value="CREDIT">Crédit</option>
          </select>
          <input v-model="adjForm.label" placeholder="Libellé" class="form-input sm:col-span-2" required />
          <input v-model="adjForm.amount" type="number" step="1" min="0" placeholder="Montant FCFA" class="form-input" required />
          <input v-model="adjForm.reason" placeholder="Motif (obligatoire pour audit)" class="form-input sm:col-span-2" />
          <button type="submit" class="btn-primary sm:col-span-3" :disabled="savingAdj">
            {{ savingAdj ? 'Enregistrement…' : 'Enregistrer l\'ajustement' }}
          </button>
        </form>
        <p class="text-xs text-slate-500 max-w-2xl">
          Les ajustements sont immuables et tracés dans le journal. Comptes usuels : 411 (clients), 416 (assurance), 512 (banque), 706 (produits).
        </p>
      </div>

      <!-- Tarifs -->
      <div v-show="tab === 'prices'" class="card overflow-hidden">
        <div class="px-5 py-4 border-b bg-slate-50/80">
          <h3 class="font-bold">Grille tarifaire active</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="text-left p-4 font-semibold">Code</th>
                <th class="text-left p-4 font-semibold">Libellé</th>
                <th class="text-left p-4 font-semibold">Type</th>
                <th class="text-right p-4 font-semibold">Prix unitaire</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in prices" :key="p.id" class="border-t border-slate-100">
                <td class="p-4 font-mono text-xs">{{ p.code }}</td>
                <td class="p-4">{{ p.label }}</td>
                <td class="p-4 text-slate-500">{{ p.service_type }}</td>
                <td class="p-4 text-right font-semibold tabular-nums">{{ formatMoney(p.unit_price) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!prices.length" class="p-8 text-center text-slate-500">Aucun tarif actif.</p>
      </div>
    </template>
  </div>
</template>
