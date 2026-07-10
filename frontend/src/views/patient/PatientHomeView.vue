<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import LoadingState from '../../components/ui/LoadingState.vue'
import StatusBadge from '../../components/ui/StatusBadge.vue'
import HospitalHomeLocation from '../../components/HospitalHomeLocation.vue'
import { HOSPITAL_ADDRESS, formatCountryDisplay, resolveHospitalMap } from '../../constants/hospitalLocation'

const router = useRouter()
const loading = ref(true)
const hospital = ref(null)
const appointments = ref([])
const patient = ref(null)

const mapLinks = () => resolveHospitalMap(hospital.value)

async function load() {
  loading.value = true
  appointments.value = []

  try {
    const { data: h } = await api.get('/public/hospital/')
    hospital.value = h
  } catch {
    hospital.value = {
      name: HOSPITAL_ADDRESS.name,
      city: HOSPITAL_ADDRESS.city,
      city_nickname: HOSPITAL_ADDRESS.cityNickname,
      country: HOSPITAL_ADDRESS.country,
      country_code: HOSPITAL_ADDRESS.countryCode,
      country_display: HOSPITAL_ADDRESS.countryDisplay,
      neighborhood: HOSPITAL_ADDRESS.neighborhood,
      street: HOSPITAL_ADDRESS.street,
      street_number: HOSPITAL_ADDRESS.streetNumber,
      landmark: HOSPITAL_ADDRESS.landmark,
      address: HOSPITAL_ADDRESS.full,
    }
  }

  try {
    const { data: p } = await api.get('/clinical/patients/me/')
    patient.value = p
    const { data } = await api.get('/hr/appointments/patient/me/')
    appointments.value = data.filter((a) => ['PENDING', 'CONFIRMED'].includes(a.status)).slice(0, 3)
  } catch {
    patient.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <LoadingState v-if="loading" />

    <template v-else>
      <section class="card overflow-hidden mb-5 bg-gradient-to-br from-teal-700 to-teal-900 text-white">
        <div class="p-6">
          <div class="flex items-center gap-2 mb-2">
            <span class="relative flex h-2.5 w-2.5">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-300 opacity-80" />
              <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-yellow-300 shadow-[0_0_8px_2px_rgba(253,224,71,0.9)]" />
            </span>
            <p class="text-teal-200 text-xs font-semibold uppercase tracking-wide">
              {{ hospital?.city || HOSPITAL_ADDRESS.city }} · {{ hospital?.city_nickname || HOSPITAL_ADDRESS.cityNickname }} · {{ formatCountryDisplay(hospital) }}
            </p>
          </div>
          <h1 class="text-2xl font-bold">{{ hospital?.name || HOSPITAL_ADDRESS.name }}</h1>
          <p class="text-teal-100/90 text-sm mt-2 leading-relaxed">
            {{ hospital?.neighborhood || HOSPITAL_ADDRESS.neighborhood }} —
            {{ hospital?.street || HOSPITAL_ADDRESS.street }} {{ hospital?.street_number || HOSPITAL_ADDRESS.streetNumber }}
          </p>
          <p class="text-teal-100/80 text-xs mt-1">{{ hospital?.landmark || HOSPITAL_ADDRESS.landmark }}</p>
          <p class="text-teal-200/90 text-xs mt-3 flex items-center gap-1.5">
            <span class="inline-block w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
            La carte ci-dessous indique la localisation exacte (signal clignotant)
          </p>
          <div class="flex flex-wrap gap-2 mt-4">
            <router-link
              to="/patient/appointments"
              class="inline-flex items-center px-4 py-2 rounded-full bg-white text-teal-800 text-sm font-semibold hover:bg-teal-50 transition shadow-sm"
            >
              Prendre rendez-vous
            </router-link>
            <a
              :href="mapLinks().googleDirectionsUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white/20 text-sm font-semibold hover:bg-white/30 transition border border-white/30"
            >
              🧭 Itinéraire
            </a>
          </div>
        </div>
      </section>

      <!-- Carte Google Maps — toujours affichée -->
      <HospitalHomeLocation :hospital="hospital" />

      <div v-if="hospital?.stats" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div v-for="s in hospital.stats" :key="s.label" class="card card-body !py-3 text-center">
          <p class="text-xl font-bold text-teal-700">{{ s.value }}</p>
          <p class="text-xs text-slate-500">{{ s.label }}</p>
        </div>
      </div>

      <section class="mb-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold text-slate-800">Prochains rendez-vous</h2>
          <router-link to="/patient/appointments" class="text-xs text-teal-700 font-medium hover:underline">Tout voir</router-link>
        </div>
        <div v-if="appointments.length" class="space-y-2">
          <div v-for="a in appointments" :key="a.id" class="card card-body !py-3 flex items-center justify-between gap-3">
            <div>
              <p class="font-medium text-sm">Dr {{ a.doctor_name?.split(' ').pop() }}</p>
              <p class="text-xs text-slate-500">{{ new Date(a.scheduled_at).toLocaleString('fr-FR') }}</p>
            </div>
            <StatusBadge :status="a.status" />
          </div>
        </div>
        <div v-else class="card card-body text-center text-sm text-slate-500">
          Aucun rendez-vous à venir —
          <button type="button" class="text-teal-700 font-medium hover:underline ml-1" @click="router.push('/patient/appointments')">Réserver</button>
        </div>
      </section>

      <section>
        <h2 class="font-semibold text-slate-800 mb-3">Accès rapide</h2>
        <div class="grid grid-cols-2 gap-3">
          <router-link to="/patient/services" class="card card-body hover:shadow-md transition !py-4">
            <span class="text-2xl">📋</span>
            <p class="font-medium text-sm mt-2">Services médicaux</p>
            <p class="text-xs text-slate-500">Spécialités, horaires & labo</p>
          </router-link>
          <router-link to="/patient/records" class="card card-body hover:shadow-md transition !py-4 ring-2 ring-teal-100">
            <span class="text-2xl">📁</span>
            <p class="font-medium text-sm mt-2">Mon dossier</p>
            <p class="text-xs text-slate-500">Carte patient PDF, QR code & documents</p>
          </router-link>
        </div>
      </section>

      <AlertBanner v-if="hospital?.emergency_phones?.length" type="info" class="mt-5">
        <p class="font-medium mb-1">Urgences 24h/24 — Dolisie, République du Congo (RC)</p>
        <p class="text-sm flex flex-wrap gap-x-3 gap-y-1">
          <a
            v-for="(line, i) in hospital.emergency_phones"
            :key="i"
            :href="`tel:${line.tel}`"
            class="font-semibold hover:underline"
          >
            {{ line.display }}
          </a>
        </p>
      </AlertBanner>
    </template>
  </div>
</template>
