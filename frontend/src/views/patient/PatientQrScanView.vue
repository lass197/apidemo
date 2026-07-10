<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import LoadingState from '../../components/ui/LoadingState.vue'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import HospitalIcon from '../../components/icons/HospitalIcon.vue'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref(null)

const apiBase = import.meta.env.VITE_API_BASE || '/api/v1'

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

const clinical = computed(() => data.value?.clinical_summary || {})
const consultations = computed(() => clinical.value.consultations || [])
const diagnoses = computed(() => clinical.value.primary_diagnoses || [])

onMounted(async () => {
  const { p, d, t, at } = route.query
  if (!p || !t || !at) {
    error.value = 'QR code incomplet. Régénérez la carte patient depuis votre dossier.'
    loading.value = false
    return
  }
  try {
    const { data: res } = await axios.get(`${apiBase}/public/patient-qr/`, {
      params: { p, d: d || undefined, t, at },
    })
    data.value = res
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de lire ce QR code.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-100 to-teal-50/40">
    <header class="bg-teal-800 text-white px-4 py-5 shadow-md">
      <div class="max-w-2xl mx-auto flex items-center gap-3">
        <HospitalIcon size="md" variant="light" />
        <div>
          <p class="text-teal-200 text-xs font-semibold uppercase tracking-wide">SGHL · Dolisie (RC)</p>
          <h1 class="text-lg font-bold">Dossier patient — scan QR</h1>
        </div>
      </div>
    </header>

    <main class="max-w-2xl mx-auto px-4 py-6">
      <LoadingState v-if="loading" />
      <AlertBanner v-else-if="error" type="error">{{ error }}</AlertBanner>

      <template v-else-if="data">
        <section class="card card-body mb-4">
          <p class="text-xs font-bold uppercase text-slate-500 mb-2">Patient</p>
          <h2 class="text-xl font-bold text-slate-900">{{ data.patient.full_name }}</h2>
          <dl class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div><dt class="text-slate-500">N° dossier</dt><dd class="font-medium break-all">{{ data.patient.id }}</dd></div>
            <div><dt class="text-slate-500">Naissance</dt><dd class="font-medium">{{ data.patient.date_of_birth }}</dd></div>
            <div><dt class="text-slate-500">Sexe</dt><dd class="font-medium">{{ data.patient.gender_label }}</dd></div>
            <div><dt class="text-slate-500">Téléphone</dt><dd class="font-medium">{{ data.patient.phone || '—' }}</dd></div>
            <div class="sm:col-span-2"><dt class="text-slate-500">Email</dt><dd class="font-medium">{{ data.patient.email || '—' }}</dd></div>
          </dl>
        </section>

        <section v-if="data.doctor" class="card card-body mb-4 bg-teal-50/60 border-teal-100">
          <p class="text-xs font-bold uppercase text-teal-800 mb-2">Médecin référent</p>
          <p class="font-semibold text-slate-900">{{ data.doctor.full_name }}</p>
          <p class="text-sm text-slate-600">{{ data.doctor.specialty }}</p>
          <p v-if="data.doctor.department_name" class="text-xs text-slate-500 mt-1">{{ data.doctor.department_name }}</p>
        </section>

        <section v-if="clinical.hospitalization" class="card card-body mb-4">
          <p class="text-xs font-bold uppercase text-slate-500 mb-2">Hospitalisation</p>
          <p class="text-sm"><span class="text-slate-500">Statut :</span> <strong>{{ clinical.hospitalization.status }}</strong></p>
          <p class="text-sm mt-1"><span class="text-slate-500">Motif :</span> {{ clinical.hospitalization.admission_reason || '—' }}</p>
          <p class="text-sm mt-1"><span class="text-slate-500">Service :</span> {{ clinical.hospitalization.department || '—' }}</p>
        </section>

        <section v-if="diagnoses.length" class="card card-body mb-4 border-amber-100 bg-amber-50/50">
          <p class="text-xs font-bold uppercase text-amber-900 mb-2">Diagnostics (CIM-10)</p>
          <ul class="space-y-2">
            <li v-for="d in diagnoses" :key="d.code" class="text-sm">
              <span class="font-mono font-semibold text-amber-900">{{ d.code }}</span>
              — {{ d.label }}
            </li>
          </ul>
        </section>

        <section v-if="consultations.length" class="space-y-4 mb-4">
          <h3 class="font-semibold text-slate-800">Consultations & détails médecin</h3>
          <article
            v-for="c in consultations"
            :key="c.id"
            class="card card-body border-l-4 border-teal-500"
          >
            <div class="flex flex-wrap justify-between gap-2 mb-2">
              <p class="font-medium text-slate-900">{{ c.doctor_name }}</p>
              <p class="text-xs text-slate-500">{{ fmtDate(c.date) }}</p>
            </div>
            <p class="text-xs text-teal-700 mb-2">{{ c.doctor_specialty }}</p>
            <div v-if="c.diagnoses?.length" class="mb-3">
              <p class="text-xs font-semibold text-slate-500 mb-1">Diagnostic</p>
              <p v-for="d in c.diagnoses" :key="d.code" class="text-sm">{{ d.code }} — {{ d.label }}</p>
            </div>
            <div v-if="c.symptoms" class="mb-2">
              <p class="text-xs font-semibold text-slate-500">Symptômes</p>
              <p class="text-sm text-slate-800 whitespace-pre-wrap">{{ c.symptoms }}</p>
            </div>
            <div v-if="c.clinical_notes" class="mb-2">
              <p class="text-xs font-semibold text-slate-500">Notes du médecin</p>
              <p class="text-sm text-slate-800 whitespace-pre-wrap">{{ c.clinical_notes }}</p>
            </div>
            <div v-if="c.prescriptions?.length" class="mt-3 pt-3 border-t border-slate-100">
              <p class="text-xs font-semibold text-slate-500 mb-2">Ordonnances validées</p>
              <div v-for="rx in c.prescriptions" :key="rx.id" class="text-sm mb-2">
                <ul class="list-disc list-inside text-slate-700">
                  <li v-for="(item, idx) in rx.items" :key="idx">
                    {{ item.medicine_name }} — {{ item.dosage }}, {{ item.frequency }} ({{ item.duration_days }} j)
                  </li>
                </ul>
                <p v-if="rx.instructions" class="text-xs text-slate-500 mt-1">{{ rx.instructions }}</p>
              </div>
            </div>
          </article>
        </section>

        <section v-else-if="!diagnoses.length && !clinical.hospitalization" class="card card-body text-center text-slate-500 text-sm">
          Aucune consultation enregistrée pour ce médecin. Les diagnostics apparaîtront après une consultation à l'hôpital.
        </section>

        <section v-if="clinical.recent_appointments?.length" class="card card-body mb-4">
          <p class="text-xs font-bold uppercase text-slate-500 mb-2">Rendez-vous récents</p>
          <ul class="space-y-2 text-sm">
            <li v-for="(a, i) in clinical.recent_appointments" :key="i" class="border-b border-slate-100 pb-2 last:border-0">
              <p class="font-medium">{{ fmtDate(a.date) }} — {{ a.doctor_name }}</p>
              <p v-if="a.reason" class="text-slate-600">Motif : {{ a.reason }}</p>
              <p v-if="a.staff_notes" class="text-slate-500 text-xs">Note : {{ a.staff_notes }}</p>
            </li>
          </ul>
        </section>

        <p class="text-center text-xs text-slate-400 mt-6">
          Document vérifié SGHL · émis le {{ data.issued_at }}
        </p>
      </template>
    </main>
  </div>
</template>
