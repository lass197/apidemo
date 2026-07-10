<script setup>
import { onMounted, ref } from 'vue'
import mainApi from '../api/mainClient'
import PageHeader from '../components/PageHeader.vue'
import { formatMoney } from '../composables/currency'

const invoices = ref([])
const journal = ref([])
const error = ref('')
const success = ref('')
const adjForm = ref({
  invoice_id: '',
  account_code: '471',
  label: '',
  entry_type: 'DEBIT',
  amount: '',
  reason: '',
})

async function load() {
  const [inv, j] = await Promise.all([
    mainApi.get('/billing/invoices/'),
    mainApi.get('/billing/accounting/journal/'),
  ])
  invoices.value = inv.data
  journal.value = j.data
}

async function submitAdjustment() {
  error.value = ''
  success.value = ''
  try {
    await mainApi.post('/billing/accounting/adjustments/', {
      ...adjForm.value,
      amount: adjForm.value.amount,
    })
    adjForm.value = { invoice_id: '', account_code: '471', label: '', entry_type: 'DEBIT', amount: '', reason: '' }
    success.value = 'Ajustement enregistré.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ajustement refusé (billing.adjust)'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Comptabilité" subtitle="Ajustements manuels — permission billing.adjust (ADMIN)" />

    <p v-if="error" class="alert-error mb-4">{{ error }}</p>
    <p v-if="success" class="alert-success mb-4">{{ success }}</p>

    <form @submit.prevent="submitAdjustment" class="card card-body mb-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-3xl">
      <select v-model="adjForm.invoice_id" class="form-select" required>
        <option value="">Facture</option>
        <option v-for="i in invoices" :key="i.id" :value="i.id">{{ i.invoice_number }}</option>
      </select>
      <input v-model="adjForm.account_code" placeholder="Compte" class="form-input" required />
      <select v-model="adjForm.entry_type" class="form-select">
        <option value="DEBIT">Débit</option>
        <option value="CREIT">Crédit</option>
      </select>
      <input v-model="adjForm.label" placeholder="Libellé" class="form-input sm:col-span-2" required />
      <input v-model="adjForm.amount" type="number" step="1" min="0" placeholder="Montant FCFA" class="form-input" required />
      <input v-model="adjForm.reason" placeholder="Motif" class="form-input sm:col-span-2" />
      <button type="submit" class="btn-primary sm:col-span-3">Enregistrer ajustement</button>
    </form>

    <h3 class="font-semibold text-lg mb-4">Journal comptable</h3>
    <div v-if="journal.length" class="card divide-y divide-slate-100">
      <div
        v-for="e in journal"
        :key="e.id"
        class="px-5 py-3 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 text-sm"
        :class="{ 'bg-amber-50/80': e.is_adjustment }"
      >
        <div>
          <span class="font-medium">{{ e.label }}</span>
          <span class="text-slate-400 ml-2 font-mono text-xs">{{ e.account_code }}</span>
        </div>
        <span class="font-semibold" :class="e.entry_type === 'DEBIT' ? 'text-emerald-600' : 'text-red-600'">
          {{ e.entry_type === 'DEBIT' ? '+' : '−' }}{{ formatMoney(e.amount) }}
        </span>
      </div>
    </div>
    <div v-else class="card p-12 text-center text-slate-500">Journal vide</div>
  </div>
</template>
