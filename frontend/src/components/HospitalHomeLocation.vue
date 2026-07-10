<script setup>
import { computed, ref } from 'vue'
import { resolveHospitalMap } from '../constants/hospitalLocation'
import MapHospitalPulseMarker from './MapHospitalPulseMarker.vue'

const props = defineProps({
  hospital: { type: Object, default: null },
})

const useOsmFallback = ref(false)

const info = computed(() => ({
  name: props.hospital?.name || 'Centre Hospitalier SGHL',
  city: props.hospital?.city || 'Dolisie',
  cityNickname: props.hospital?.city_nickname || 'La Terre Jaune',
  neighborhood: props.hospital?.neighborhood || 'Quartier Gaïa',
  street: props.hospital?.street || 'Rue Mali',
  streetNumber: props.hospital?.street_number || '35',
  landmark: props.hospital?.landmark || "En face du consistoire EEC",
  address: props.hospital?.address || '35, Rue Mali — Quartier Gaïa, Dolisie',
}))

const map = computed(() => resolveHospitalMap(props.hospital))

const embedSrc = computed(() =>
  useOsmFallback.value ? map.value.openStreetMapEmbed : map.value.googleEmbedUrl,
)

const markerLabel = computed(() => `${info.value.city} (RC) · SGHL`)

function switchToOsm() {
  useOsmFallback.value = true
}
</script>

<template>
  <section class="card overflow-hidden mb-5 shadow-md border border-slate-200">
    <div class="px-5 py-4 bg-white border-b border-slate-100">
      <div class="flex items-center gap-2 mb-1">
        <span class="relative flex h-3 w-3">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span class="relative inline-flex rounded-full h-3 w-3 bg-red-600" />
        </span>
        <p class="text-xs font-bold uppercase tracking-wider text-red-600">
          Localisation exacte
        </p>
      </div>
      <h2 class="font-bold text-slate-900 text-lg leading-tight">
        {{ info.name }}
      </h2>
      <p class="text-sm text-slate-600 mt-1">
        <strong>{{ info.streetNumber }}, {{ info.street }}</strong> — {{ info.neighborhood }}, {{ info.city }}
      </p>
      <p class="text-xs text-slate-500 mt-1">{{ info.landmark }}</p>
    </div>

    <!-- Carte + marqueur lumineux -->
    <div class="relative w-full bg-slate-300" style="min-height: 300px; height: 58vw; max-height: 440px;">
      <iframe
        :key="embedSrc"
        :src="embedSrc"
        title="Google Maps — Centre Hospitalier SGHL, Dolisie"
        class="absolute inset-0 w-full h-full border-0 z-0"
        loading="eager"
        allowfullscreen
        referrerpolicy="no-referrer-when-downgrade"
        @load="useOsmFallback = false"
      />

      <!-- Marqueur pulsant — point exact de l'hôpital -->
      <div
        class="absolute top-1/2 left-1/2 z-20 -translate-x-1/2 -translate-y-[58%]"
      >
        <MapHospitalPulseMarker :label="markerLabel" />
      </div>

      <button
        v-if="!useOsmFallback"
        type="button"
        class="absolute bottom-3 right-3 z-30 text-[10px] bg-white/95 shadow-md px-2.5 py-1.5 rounded-lg text-slate-600 hover:bg-white border border-slate-200"
        @click="switchToOsm"
      >
        Carte ne s'affiche pas ?
      </button>
    </div>

    <div class="px-4 py-4 sm:px-5 bg-white border-t border-slate-100 space-y-3">
      <div class="flex flex-col sm:flex-row flex-wrap gap-2">
        <a
          :href="map.googleDirectionsUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center gap-2 text-sm font-bold text-white bg-teal-600 hover:bg-teal-700 px-5 py-3 rounded-xl transition shadow-sm flex-1 sm:flex-none min-w-[160px]"
        >
          🧭 Itinéraire GPS
        </a>
        <a
          :href="map.googleMapsUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center gap-2 text-sm font-bold text-teal-800 bg-teal-50 border-2 border-teal-200 hover:bg-teal-100 px-5 py-3 rounded-xl transition flex-1 sm:flex-none min-w-[160px]"
        >
          🗺️ Ouvrir Google Maps
        </a>
        <router-link
          to="/patient/discover"
          class="inline-flex items-center justify-center gap-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 px-5 py-3 rounded-xl transition flex-1 sm:flex-none"
        >
          Infos hôpital →
        </router-link>
      </div>
      <p class="text-[11px] text-slate-400 text-center sm:text-left">
        {{ info.address }}
      </p>
    </div>
  </section>
</template>
