<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import LoadingState from '../../components/ui/LoadingState.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { formatCountryDisplay, HOSPITAL_ADDRESS, normalizeServiceLocationHint } from '../../constants/hospitalLocation'
import { resolveServiceIcon } from '../../constants/serviceIcons'

const router = useRouter()
const loading = ref(true)
const services = ref([])
const hospital = ref(null)

const countryLabel = computed(() => formatCountryDisplay(hospital.value))

onMounted(async () => {
  try {
    const [svc, hosp] = await Promise.all([
      api.get('/public/hospital/services/'),
      api.get('/public/hospital/'),
    ])
    services.value = svc.data
    hospital.value = hosp.data
  } catch {
    services.value = []
    hospital.value = {
      name: HOSPITAL_ADDRESS.name,
      city: HOSPITAL_ADDRESS.city,
      country_code: HOSPITAL_ADDRESS.countryCode,
      country_display: HOSPITAL_ADDRESS.countryDisplay,
      address: HOSPITAL_ADDRESS.full,
      street_number: HOSPITAL_ADDRESS.streetNumber,
      street: HOSPITAL_ADDRESS.street,
      neighborhood: HOSPITAL_ADDRESS.neighborhood,
    }
  } finally {
    loading.value = false
  }
})

function book(service) {
  router.push({ path: '/patient/appointments', query: { service: service.id || service.code } })
}

function formatLocation(service) {
  const hint = normalizeServiceLocationHint(service.location_hint)
  if (/dolisie|\(RC\)|république du congo/i.test(hint)) return hint
  const city = hospital.value?.city || HOSPITAL_ADDRESS.city
  const code = hospital.value?.country_code || HOSPITAL_ADDRESS.countryCode
  return hint ? `${hint} · ${city} (${code})` : `${city} — ${countryLabel.value}`
}
</script>

<template>
  <div>
    <header class="mb-6">
      <h1 class="text-xl font-bold text-slate-900 mb-1">Services médicaux</h1>
      <p class="text-slate-500 text-sm">
        Où se faire consulter — {{ hospital?.name || HOSPITAL_ADDRESS.name }}
      </p>
    </header>

    <section class="card card-body mb-6 bg-teal-50/80 border border-teal-100">
      <p class="text-xs font-bold uppercase tracking-wider text-teal-800 mb-1">
        Établissement · {{ countryLabel }}
      </p>
      <p class="text-sm font-semibold text-slate-800">
        {{ hospital?.street_number || HOSPITAL_ADDRESS.streetNumber }},
        {{ hospital?.street || HOSPITAL_ADDRESS.street }} —
        {{ hospital?.neighborhood || HOSPITAL_ADDRESS.neighborhood }}
      </p>
      <p class="text-sm text-slate-600 mt-0.5">
        {{ hospital?.city || HOSPITAL_ADDRESS.city }}
        ({{ hospital?.city_nickname || HOSPITAL_ADDRESS.cityNickname }})
      </p>
      <p class="text-xs text-slate-500 mt-2 leading-relaxed">
        Chaque fiche indique le <strong>service</strong>, sa <strong>description</strong>,
        le <strong>lieu exact dans l'hôpital</strong> et les <strong>horaires</strong>.
        Tous les services sont à Dolisie, {{ countryLabel }}.
      </p>
    </section>

    <LoadingState v-if="loading" />

    <div
      v-else-if="services.length"
      class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5"
    >
      <article
        v-for="s in services"
        :key="s.id || s.code"
        class="card card-body flex flex-col hover:shadow-lg transition-shadow duration-200"
      >
        <div class="flex items-start gap-3 mb-3">
          <span class="text-3xl shrink-0 leading-none" aria-hidden="true">{{ resolveServiceIcon(s) }}</span>
          <div class="min-w-0">
            <h2 class="font-bold text-slate-800 text-lg leading-snug">{{ s.name }}</h2>
            <span class="inline-block mt-1 text-[10px] font-semibold uppercase tracking-wide text-teal-700 bg-teal-50 px-2 py-0.5 rounded-full">
              Dolisie (RC)
            </span>
          </div>
        </div>

        <p class="text-sm text-slate-600 leading-relaxed flex-1">
          {{ s.description }}
        </p>

        <div class="mt-4 pt-4 border-t border-slate-100 space-y-2">
          <p class="flex items-start gap-2 text-sm text-slate-600">
            <span class="shrink-0" aria-hidden="true">📍</span>
            <span>{{ formatLocation(s) }}</span>
          </p>
          <p v-if="s.opening_hours" class="flex items-start gap-2 text-sm font-medium text-teal-700">
            <span class="shrink-0" aria-hidden="true">🕐</span>
            <span>{{ s.opening_hours }}</span>
          </p>
          <p v-if="s.price_hint" class="text-xs text-slate-400">
            Tarif indicatif : {{ s.price_hint }}
            <span v-if="s.duration_minutes"> · {{ s.duration_minutes }} min</span>
          </p>
        </div>

        <button
          v-if="s.is_bookable_online !== false"
          type="button"
          class="btn-primary w-full !py-2.5 text-sm mt-4"
          @click="book(s)"
        >
          Prendre rendez-vous
        </button>
        <p v-else class="text-xs text-slate-500 mt-4 text-center italic">
          Présentez-vous directement — pas de réservation en ligne
        </p>
      </article>
    </div>

    <EmptyState
      v-else
      title="Aucun service disponible"
      description="Les prestations seront bientôt affichées ici."
      icon="🏥"
    />
  </div>
</template>
