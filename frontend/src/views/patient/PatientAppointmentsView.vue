<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/client'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import StatusBadge from '../../components/ui/StatusBadge.vue'
import LoadingState from '../../components/ui/LoadingState.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { normalizeServiceLocationHint } from '../../constants/hospitalLocation'
import { resolveServiceIcon } from '../../constants/serviceIcons'

const route = useRoute()
const loading = ref(true)
const booking = ref(false)
const error = ref('')
const success = ref('')

const patient = ref(null)
const appointments = ref([])
const doctors = ref([])
const services = ref([])
const slots = ref([])

const doctorId = ref(null)
const serviceId = ref(null)
const selectedSlot = ref(null)
const reason = ref('')

const selectedDoctor = computed(() => doctors.value.find((d) => d.id === doctorId.value))
const selectedService = computed(() => services.value.find((s) => s.id === serviceId.value))

const statusHelp = {
  PENDING: 'En attente de validation par le secrétariat',
  CONFIRMED: 'Confirmé — présentez-vous 10 min avant',
  CANCELLED: 'Annulé',
  COMPLETED: 'Terminé',
}

const upcoming = computed(() =>
  appointments.value.filter((a) => ['PENDING', 'CONFIRMED'].includes(a.status)),
)
const past = computed(() =>
  appointments.value.filter((a) => ['CANCELLED', 'COMPLETED'].includes(a.status)),
)

const slotsByDay = computed(() => {
  const groups = new Map()
  for (const s of slots.value) {
    const d = new Date(s.scheduled_at)
    const key = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(s)
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items }))
})

function fmtSlot(iso) {
  return new Date(iso).toLocaleString('fr-FR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: p } = await api.get('/clinical/patients/me/')
    patient.value = p
    const [appts, dir, svcs] = await Promise.all([
      api.get('/hr/appointments/patient/me/'),
      api.get('/hr/doctors/directory/'),
      api.get('/hr/services/'),
    ])
    appointments.value = appts.data
    doctors.value = dir.data
    services.value = svcs.data

    const queryDoctor = route.query.doctor
    if (queryDoctor && dir.data.some((d) => d.id === queryDoctor)) {
      doctorId.value = queryDoctor
    } else {
      doctorId.value ??= dir.data.find((d) => d.available_slots_count)?.id ?? dir.data[0]?.id
    }

    if (route.query.service) {
      const match = svcs.data.find((s) => s.id === route.query.service || s.code === route.query.service)
      if (match) serviceId.value = match.id
    }
    if (doctorId.value) await loadSlots()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

async function loadSlots() {
  if (!doctorId.value) return
  const { data } = await api.get(`/hr/availabilities/${doctorId.value}/slots/`)
  slots.value = data.filter((s) => s.available)
  const querySlot = route.query.slot
  if (querySlot && slots.value.some((s) => s.scheduled_at === querySlot)) {
    selectedSlot.value = querySlot
  } else {
    selectedSlot.value = slots.value[0]?.scheduled_at ?? null
  }
}

watch(doctorId, loadSlots)

async function submitBooking() {
  error.value = ''
  success.value = ''
  if (!selectedSlot.value) {
    error.value = 'Choisissez un créneau disponible.'
    return
  }
  booking.value = true
  try {
    await api.post('/hr/appointments/', {
      patient_id: patient.value.id,
      doctor_id: doctorId.value,
      scheduled_at: selectedSlot.value,
      reason: reason.value,
      service_id: serviceId.value || undefined,
    })
    success.value = 'Demande envoyée ! Vous recevrez un email dès validation par le secrétariat.'
    reason.value = ''
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Réservation impossible.'
  } finally {
    booking.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-slate-900 mb-1">Mes rendez-vous</h1>
    <p class="text-slate-500 text-sm mb-4">
      Choisissez un médecin, consultez son agenda et réservez — confirmation par le secrétariat
    </p>

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
    <AlertBanner v-if="success" type="success" class="mb-4">{{ success }}</AlertBanner>

    <LoadingState v-if="loading" />

    <template v-else>
      <section class="card card-body mb-6">
        <div class="flex flex-wrap justify-between items-center gap-2 mb-4">
          <h2 class="font-semibold">Nouvelle demande</h2>
          <router-link to="/patient/doctors" class="text-sm text-teal-700 font-medium hover:underline">
            Voir tous les médecins →
          </router-link>
        </div>
        <div class="space-y-3">
          <label class="block">
            <span class="form-label">Médecin</span>
            <select v-model="doctorId" class="form-select">
              <option v-for="d in doctors" :key="d.id" :value="d.id">
                Dr {{ d.name }} — {{ d.specialty }}
                ({{ d.available_slots_count }} créneau{{ d.available_slots_count > 1 ? 'x' : '' }})
              </option>
            </select>
          </label>
          <div
            v-if="selectedDoctor"
            class="text-sm bg-teal-50 border border-teal-100 rounded-xl px-4 py-3 space-y-2"
          >
            <p class="font-medium text-teal-900">{{ selectedDoctor.specialty }}</p>
            <p v-if="selectedDoctor.department_name" class="text-xs text-teal-700">
              {{ selectedDoctor.department_name }}
            </p>
            <div v-if="selectedDoctor.agenda_calendar?.length" class="pt-2 border-t border-teal-100/80">
              <p class="text-xs font-semibold text-teal-800 mb-1.5">Jours de consultation</p>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="day in selectedDoctor.agenda_calendar.slice(0, 6)"
                  :key="day.date"
                  class="text-[10px] px-2 py-0.5 rounded-full bg-white/70 text-teal-900 capitalize"
                >
                  {{ day.weekday }}
                </span>
              </div>
            </div>
            <p v-if="selectedDoctor.next_available_at" class="text-xs text-slate-600">
              Prochain créneau : {{ fmtSlot(selectedDoctor.next_available_at) }}
            </p>
          </div>
          <label class="block">
            <span class="form-label">Prestation (optionnel)</span>
            <select v-model="serviceId" class="form-select">
              <option :value="null">— Choisir —</option>
              <option v-for="s in services" :key="s.id" :value="s.id">{{ resolveServiceIcon(s) }} {{ s.name }}</option>
            </select>
          </label>
          <div
            v-if="selectedService"
            class="text-sm bg-slate-50 border border-slate-100 rounded-xl px-4 py-3"
          >
            <p class="text-slate-600 leading-relaxed">{{ selectedService.description }}</p>
            <p v-if="selectedService.location_hint" class="text-xs text-slate-500 mt-2">📍 {{ normalizeServiceLocationHint(selectedService.location_hint) }}</p>
            <p v-if="selectedService.opening_hours" class="text-xs font-medium text-teal-700 mt-1">🕐 {{ selectedService.opening_hours }}</p>
          </div>
          <label class="block">
            <span class="form-label">Créneau disponible</span>
            <select v-model="selectedSlot" class="form-select">
              <optgroup v-for="group in slotsByDay" :key="group.label" :label="group.label">
                <option v-for="s in group.items" :key="s.scheduled_at" :value="s.scheduled_at">
                  {{ fmtSlot(s.scheduled_at) }}
                </option>
              </optgroup>
            </select>
            <p v-if="!slots.length" class="text-xs text-amber-600 mt-1">
              Aucun créneau pour ce médecin —
              <router-link to="/patient/doctors" class="underline">voir les autres médecins</router-link>
            </p>
          </label>
          <label class="block">
            <span class="form-label">Motif</span>
            <textarea v-model="reason" class="form-input min-h-[80px]" placeholder="Décrivez brièvement la raison de votre visite" />
          </label>
          <button type="button" class="btn-primary w-full" :disabled="booking || !slots.length" @click="submitBooking">
            {{ booking ? 'Envoi…' : 'Demander un rendez-vous' }}
          </button>
        </div>
      </section>

      <section class="mb-6">
        <h2 class="font-semibold mb-3">À venir</h2>
        <EmptyState v-if="!upcoming.length" title="Aucun rendez-vous à venir" description="Utilisez le formulaire ci-dessus pour réserver." />
        <div v-else class="space-y-2">
          <div v-for="a in upcoming" :key="a.id" class="card card-body">
            <div class="flex justify-between items-start gap-2">
              <div>
                <p class="font-medium">{{ a.service_name || 'Consultation' }}</p>
                <p class="text-sm text-slate-600">Dr {{ a.doctor_name }}</p>
                <p class="text-xs text-slate-400 mt-1">{{ fmtSlot(a.scheduled_at) }}</p>
                <p class="text-xs text-slate-500 mt-2">{{ statusHelp[a.status] }}</p>
                <p v-if="a.staff_notes" class="text-xs text-teal-700 mt-1">Note : {{ a.staff_notes }}</p>
              </div>
              <StatusBadge :status="a.status" />
            </div>
          </div>
        </div>
      </section>

      <section v-if="past.length">
        <h2 class="font-semibold mb-3 text-slate-500">Historique</h2>
        <div class="space-y-2 opacity-75">
          <div v-for="a in past" :key="a.id" class="card card-body !py-3 text-sm">
            <div class="flex justify-between">
              <span>{{ new Date(a.scheduled_at).toLocaleDateString('fr-FR') }} — Dr {{ a.doctor_name?.split(' ').pop() }}</span>
              <StatusBadge :status="a.status" />
            </div>
            <p v-if="a.rejection_reason" class="text-xs text-red-600 mt-1">{{ a.rejection_reason }}</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
