<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import LoadingState from '../../components/ui/LoadingState.vue'
import EmptyState from '../../components/ui/EmptyState.vue'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const doctors = ref([])
const specialties = ref([])
const specialtyFilter = ref('')
const onlyAvailable = ref(false)
const expandedId = ref(null)

const filteredCount = computed(() => doctors.value.length)

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('fr-FR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function fmtSession(session) {
  return `${session.start} – ${session.end} (${session.slot_duration_minutes} min)`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { only_available: onlyAvailable.value }
    if (specialtyFilter.value) params.specialty = specialtyFilter.value
    const [dir, specs] = await Promise.all([
      api.get('/hr/doctors/directory/', { params }),
      api.get('/hr/doctors/specialties/'),
    ])
    doctors.value = dir.data
    specialties.value = specs.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de charger les médecins.'
  } finally {
    loading.value = false
  }
}

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function bookWith(doctor) {
  router.push({ path: '/patient/appointments', query: { doctor: doctor.id } })
}

onMounted(load)
</script>

<template>
  <div>
    <h1 class="text-xl font-bold text-slate-900 mb-1">Médecins disponibles</h1>
    <p class="text-slate-500 text-sm mb-4">
      Agendas par spécialité — matinées et après-midis sur des jours différents
    </p>

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>

    <div class="card card-body mb-6 flex flex-wrap gap-3 items-end">
      <label class="block flex-1 min-w-[10rem]">
        <span class="form-label">Spécialité</span>
        <select v-model="specialtyFilter" class="form-select" @change="load">
          <option value="">Toutes les spécialités</option>
          <option v-for="s in specialties" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <label class="flex items-center gap-2 text-sm text-slate-600 pb-2 cursor-pointer">
        <input v-model="onlyAvailable" type="checkbox" class="rounded border-slate-300" @change="load" />
        Uniquement avec créneaux libres
      </label>
      <button type="button" class="btn-secondary text-sm" @click="load">Actualiser</button>
    </div>

    <LoadingState v-if="loading" />

    <EmptyState
      v-else-if="!doctors.length"
      title="Aucun médecin trouvé"
      description="Modifiez les filtres ou réessayez plus tard."
    />

    <p v-else class="text-xs text-slate-500 mb-3">{{ filteredCount }} médecin(s)</p>

    <div v-if="!loading && doctors.length" class="space-y-3">
      <article
        v-for="d in doctors"
        :key="d.id"
        class="card overflow-hidden"
        :class="d.available_slots_count ? 'border-teal-100' : 'border-slate-100 opacity-90'"
      >
        <div class="card-body">
          <div class="flex flex-wrap justify-between gap-3 items-start">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2 mb-1">
                <h2 class="font-semibold text-slate-900">Dr {{ d.name }}</h2>
                <span class="text-xs font-medium px-2 py-0.5 rounded-full bg-teal-50 text-teal-800">
                  {{ d.specialty }}
                </span>
              </div>
              <p v-if="d.department_name" class="text-xs text-slate-500 mb-1">
                Service {{ d.department_name }}
              </p>
              <p v-if="d.bio" class="text-sm text-slate-600 line-clamp-2">{{ d.bio }}</p>
              <p class="text-xs mt-2" :class="d.available_slots_count ? 'text-emerald-700' : 'text-amber-700'">
                <template v-if="d.available_slots_count">
                  {{ d.available_slots_count }} créneau(x) libre(s) sur 4 semaines
                  <span v-if="d.next_available_at"> — prochain : {{ fmtDate(d.next_available_at) }}</span>
                </template>
                <template v-else>Aucun créneau libre pour le moment</template>
              </p>
            </div>
            <div class="flex flex-wrap gap-2 shrink-0">
              <button
                type="button"
                class="btn-secondary text-xs !py-2"
                @click="toggleExpand(d.id)"
              >
                {{ expandedId === d.id ? 'Masquer l\'agenda' : 'Voir l\'agenda' }}
              </button>
              <button
                type="button"
                class="btn-primary text-xs !py-2"
                :disabled="!d.available_slots_count"
                @click="bookWith(d)"
              >
                Prendre rendez-vous
              </button>
            </div>
          </div>

          <div v-if="expandedId === d.id" class="mt-4 pt-4 border-t border-slate-100 space-y-4">
            <div>
              <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                Planning des 4 prochaines semaines
              </h3>
              <div
                v-if="d.agenda_calendar?.length"
                class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2"
              >
                <div
                  v-for="day in d.agenda_calendar.slice(0, 12)"
                  :key="day.date"
                  class="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5"
                >
                  <p class="text-sm font-semibold text-slate-800 capitalize">{{ day.weekday_label }}</p>
                  <ul class="mt-1.5 space-y-1">
                    <li
                      v-for="(session, idx) in day.sessions"
                      :key="idx"
                      class="text-xs text-slate-600 flex items-center gap-1.5"
                    >
                      <span class="text-teal-600">🕐</span>
                      {{ fmtSession(session) }}
                    </li>
                  </ul>
                </div>
              </div>
              <p v-else class="text-sm text-slate-400">Aucune plage publiée.</p>
            </div>
            <div>
              <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Prochains créneaux disponibles
              </h3>
              <div v-if="d.upcoming_slots.length" class="flex flex-wrap gap-2">
                <button
                  v-for="slot in d.upcoming_slots"
                  :key="slot.scheduled_at"
                  type="button"
                  class="text-xs font-medium px-2.5 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-100 hover:bg-emerald-100 transition"
                  @click="router.push({ path: '/patient/appointments', query: { doctor: d.id, slot: slot.scheduled_at } })"
                >
                  {{ fmtDate(slot.scheduled_at) }}
                </button>
              </div>
              <p v-else class="text-sm text-slate-400">Complet sur la période affichée.</p>
            </div>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
