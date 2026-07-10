<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'

const transfers = ref([])
const loading = ref(true)
const error = ref('')
const success = ref('')
const rejectId = ref('')
const rejectReason = ref('')

const pending = computed(() => transfers.value.filter((t) => t.status === 'PENDING'))
const processed = computed(() => transfers.value.filter((t) => t.status !== 'PENDING'))

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/clinical/inter-hospital-transfers/')
    transfers.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de charger les demandes.'
  } finally {
    loading.value = false
  }
}

async function validateTransfer(id) {
  error.value = ''
  success.value = ''
  try {
    await api.post(`/clinical/inter-hospital-transfers/${id}/validate/`)
    success.value = 'Transfert validé. Le patient est enregistré comme transféré et le lit est libéré.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Validation échouée.'
  }
}

function openReject(id) {
  rejectId.value = id
  rejectReason.value = ''
}

function cancelReject() {
  rejectId.value = ''
  rejectReason.value = ''
}

async function confirmReject() {
  error.value = ''
  success.value = ''
  try {
    await api.post(`/clinical/inter-hospital-transfers/${rejectId.value}/reject/`, {
      rejection_reason: rejectReason.value,
    })
    success.value = 'Demande de transfert refusée. Le médecin pourra en soumettre une nouvelle.'
    cancelReject()
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Refus échoué.'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Demandes de transfert"
      subtitle="Validation secrétariat — demandes soumises par les médecins"
    />

    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <p v-if="pending.length" class="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-6">
        {{ pending.length }} demande(s) en attente de votre validation
      </p>

      <section class="mb-8">
        <h3 class="font-semibold text-lg mb-4">À valider</h3>
        <EmptyState
          v-if="!pending.length"
          title="Aucune demande en attente"
          description="Les nouvelles demandes des médecins apparaîtront ici."
          icon="✅"
        />
        <div v-else class="space-y-4">
          <article
            v-for="t in pending"
            :key="t.id"
            class="card overflow-hidden border-l-4 border-l-amber-400"
          >
            <div class="card-body space-y-4">
              <div class="flex flex-wrap justify-between gap-3 items-start">
                <div>
                  <div class="flex flex-wrap items-center gap-2 mb-1">
                    <h4 class="font-semibold text-lg">{{ t.patient_name }}</h4>
                    <StatusBadge :status="t.status_label" />
                  </div>
                  <p class="text-sm text-slate-500">
                    Demandé par {{ t.requested_by_name }} le {{ fmtDate(t.created_at) }}
                  </p>
                </div>
                <div class="flex flex-wrap gap-2 shrink-0">
                  <button type="button" class="btn-primary text-sm" @click="validateTransfer(t.id)">
                    Valider le transfert
                  </button>
                  <button type="button" class="btn-secondary text-sm" @click="openReject(t.id)">
                    Refuser
                  </button>
                </div>
              </div>

              <div class="grid sm:grid-cols-2 gap-4 text-sm">
                <div class="p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <h5 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Patient</h5>
                  <p><span class="text-slate-500">Motif d'admission :</span> {{ t.admission_reason }}</p>
                  <p class="mt-1">
                    <span class="text-slate-500">Lit actuel :</span>
                    {{ t.department_name || '—' }}, ch. {{ t.room_number || '—' }}, lit {{ t.bed_label || '—' }}
                  </p>
                  <p class="mt-1 text-slate-500">Admis le {{ fmtDate(t.admission_date) }}</p>
                </div>
                <div class="p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <h5 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Destination</h5>
                  <p class="font-medium">{{ t.partner_hospital_name }}</p>
                  <p>{{ t.partner_hospital_city }}</p>
                  <p v-if="t.partner_hospital_address" class="text-slate-600">{{ t.partner_hospital_address }}</p>
                  <p v-if="t.partner_hospital_phone" class="mt-1">{{ t.partner_hospital_phone }}</p>
                  <p v-if="t.partner_hospital_specialties" class="mt-1 text-slate-600">{{ t.partner_hospital_specialties }}</p>
                </div>
              </div>

              <div class="text-sm space-y-2">
                <div>
                  <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Motif médical</p>
                  <p class="text-slate-800 whitespace-pre-wrap">{{ t.reason }}</p>
                </div>
                <div v-if="t.clinical_summary">
                  <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Résumé clinique</p>
                  <p class="text-slate-700 whitespace-pre-wrap">{{ t.clinical_summary }}</p>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section v-if="processed.length">
        <h3 class="font-semibold text-lg mb-4">Historique</h3>
        <div class="overflow-x-auto card">
          <table class="data-table w-full">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Destination</th>
                <th>Médecin</th>
                <th>Statut</th>
                <th>Traité par</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in processed" :key="t.id">
                <td>{{ t.patient_name }}</td>
                <td>{{ t.partner_hospital_name }}</td>
                <td>{{ t.requested_by_name }}</td>
                <td><StatusBadge :status="t.status_label" /></td>
                <td>{{ t.validated_by_name || '—' }}</td>
                <td>{{ fmtDate(t.validated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <div
      v-if="rejectId"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="cancelReject"
    >
      <form class="card card-body max-w-md w-full" @submit.prevent="confirmReject">
        <h3 class="font-semibold text-lg mb-2">Refuser la demande</h3>
        <p class="text-sm text-slate-600 mb-4">Indiquez éventuellement un motif pour le médecin.</p>
        <label class="block mb-4">
          <span class="form-label">Motif du refus (optionnel)</span>
          <textarea v-model="rejectReason" class="form-input min-h-[80px]" placeholder="Capacité saturée, dossier incomplet…" />
        </label>
        <div class="flex gap-2 justify-end">
          <button type="button" class="btn-secondary" @click="cancelReject">Annuler</button>
          <button type="submit" class="btn-primary !bg-red-600 hover:!bg-red-700">Confirmer le refus</button>
        </div>
      </form>
    </div>
  </div>
</template>
