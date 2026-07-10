<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api/client'
import LoadingState from '../../components/ui/LoadingState.vue'
import HospitalHomeLocation from '../../components/HospitalHomeLocation.vue'
import { HOSPITAL_ADDRESS, formatCountryDisplay } from '../../constants/hospitalLocation'

const loading = ref(true)
const hospital = ref(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/public/hospital/')
    hospital.value = data
  } catch {
    hospital.value = {
      ...HOSPITAL_ADDRESS,
      name: HOSPITAL_ADDRESS.name,
      country: HOSPITAL_ADDRESS.country,
      country_code: HOSPITAL_ADDRESS.countryCode,
      country_display: HOSPITAL_ADDRESS.countryDisplay,
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <LoadingState v-if="loading" />

    <template v-else-if="hospital">
      <header class="mb-6">
        <div class="flex items-center gap-2 mb-2">
          <span class="relative flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span class="relative inline-flex rounded-full h-3 w-3 bg-red-600" />
          </span>
          <p class="text-xs font-semibold uppercase tracking-wider text-red-600">
            {{ hospital.city }} · {{ formatCountryDisplay(hospital) }}
          </p>
        </div>
        <h1 class="text-xl font-bold text-slate-900">{{ hospital.name }}</h1>
        <p class="text-slate-500 text-sm mt-1">{{ hospital.tagline }}</p>
      </header>

      <!-- Urgences en évidence -->
      <section class="card card-body mb-5 border-red-100 bg-gradient-to-br from-red-50 to-white">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="font-semibold text-red-800 flex items-center gap-2">
              <span aria-hidden="true">🚑</span> Urgences 24h/24
            </h2>
            <p class="text-sm text-red-700/80 mt-1">{{ hospital.emergency_hours }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <a
              v-for="(line, i) in hospital.emergency_phones || []"
              :key="i"
              :href="`tel:${line.tel}`"
              class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 text-white text-sm font-semibold hover:bg-red-700 transition shadow-sm"
            >
              <span aria-hidden="true">📞</span>
              {{ line.display }}
            </a>
          </div>
        </div>
      </section>

      <HospitalHomeLocation :hospital="hospital" class="mb-5" />

      <!-- Adresse -->
      <section class="card card-body mb-5">
        <h2 class="font-semibold mb-3 flex items-center gap-2">
          <span aria-hidden="true">📍</span> Adresse & accès
        </h2>
        <address class="not-italic text-sm text-slate-700 leading-relaxed space-y-0.5">
          <p v-for="(line, i) in hospital.address_lines || [hospital.address]" :key="i" class="font-medium">
            {{ line }}
          </p>
        </address>
        <p v-if="hospital.landmark" class="text-sm text-teal-800 bg-teal-50 rounded-lg px-3 py-2 mt-3">
          <strong>Repère :</strong> {{ hospital.landmark }}
        </p>
      </section>

      <section class="card card-body mb-5">
        <h2 class="font-semibold mb-2">À propos</h2>
        <p class="text-sm text-slate-600 leading-relaxed">{{ hospital.about }}</p>
        <p v-if="hospital.mission" class="text-sm text-slate-600 leading-relaxed mt-3">{{ hospital.mission }}</p>
      </section>

      <section class="card card-body mb-5">
        <h2 class="font-semibold mb-3">Contact & horaires</h2>
        <dl class="text-sm space-y-3">
          <div class="flex gap-3">
            <dt class="text-slate-400 w-28 shrink-0">Accueil</dt>
            <dd>
              <a :href="`tel:${hospital.phone_tel || hospital.phone}`" class="text-teal-700 font-medium hover:underline">
                {{ hospital.phone }}
              </a>
            </dd>
          </div>
          <div class="flex gap-3">
            <dt class="text-slate-400 w-28 shrink-0">Email</dt>
            <dd>
              <a :href="`mailto:${hospital.email}`" class="text-teal-700 hover:underline">{{ hospital.email }}</a>
            </dd>
          </div>
          <div class="flex gap-3">
            <dt class="text-slate-400 w-28 shrink-0">Horaires</dt>
            <dd>{{ hospital.opening_hours }}</dd>
          </div>
          <div class="flex gap-3">
            <dt class="text-slate-400 w-28 shrink-0">Ville</dt>
            <dd>{{ hospital.city }} ({{ hospital.city_nickname }}) — {{ formatCountryDisplay(hospital) }}</dd>
          </div>
        </dl>
      </section>

      <section class="mb-5">
        <h2 class="font-semibold mb-3">Points forts</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div v-for="h in hospital.highlights" :key="h.title" class="card card-body !py-4">
            <span class="text-2xl">{{ h.icon }}</span>
            <p class="font-medium text-sm mt-2">{{ h.title }}</p>
            <p class="text-xs text-slate-500 mt-1">{{ h.text }}</p>
          </div>
        </div>
      </section>

      <section class="mb-5">
        <h2 class="font-semibold mb-3">Services & départements</h2>
        <div class="card divide-y divide-slate-100">
          <div v-for="d in hospital.departments" :key="d.code" class="px-5 py-4 flex justify-between gap-3">
            <div>
              <p class="font-medium text-sm">{{ d.name }}</p>
              <p class="text-xs text-slate-500">{{ d.floor }} · {{ d.hours || hospital.opening_hours }}</p>
            </div>
            <a
              :href="`tel:${d.phone?.replace(/\s/g, '')}`"
              class="text-teal-700 text-sm font-medium shrink-0 hover:underline"
            >
              {{ d.phone }}
            </a>
          </div>
        </div>
      </section>

      <section v-if="hospital.amenities" class="mb-5">
        <h2 class="font-semibold mb-3">Confort & accès</h2>
        <div class="grid grid-cols-2 gap-3">
          <div v-for="a in hospital.amenities" :key="a.title" class="card card-body !py-3 text-center">
            <span class="text-xl">{{ a.icon }}</span>
            <p class="text-xs font-medium mt-1">{{ a.title }}</p>
            <p class="text-[10px] text-slate-500">{{ a.text }}</p>
          </div>
        </div>
      </section>

      <section v-if="hospital.faq">
        <h2 class="font-semibold mb-3">Questions fréquentes</h2>
        <div class="space-y-2">
          <details v-for="(f, i) in hospital.faq" :key="i" class="card card-body group">
            <summary class="font-medium text-sm cursor-pointer list-none flex justify-between items-center">
              {{ f.q }}
              <span class="text-slate-400 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <p class="text-sm text-slate-600 mt-3 leading-relaxed">{{ f.a }}</p>
          </details>
        </div>
      </section>
    </template>
  </div>
</template>
