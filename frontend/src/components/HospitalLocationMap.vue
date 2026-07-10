<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  googleEmbedUrl: { type: String, default: '' },
  openstreetmapEmbedUrl: { type: String, default: '' },
  embedUrl: { type: String, default: '' },
  openstreetmapUrl: { type: String, default: '' },
  googleMapsUrl: { type: String, default: '' },
  googleMapsDirectionsUrl: { type: String, default: '' },
  directionsHint: { type: String, default: '' },
  latitude: { type: Number, default: null },
  longitude: { type: Number, default: null },
  compact: { type: Boolean, default: false },
})

const mapTab = ref('google')

const googleSrc = computed(
  () => props.googleEmbedUrl || props.embedUrl || '',
)
const osmSrc = computed(() => props.openstreetmapEmbedUrl || '')

const activeSrc = computed(() => (mapTab.value === 'google' ? googleSrc.value : osmSrc.value))

const hasGoogle = computed(() => Boolean(googleSrc.value))
const hasOsm = computed(() => Boolean(osmSrc.value))
</script>

<template>
  <section class="card overflow-hidden">
    <div class="px-5 py-4 border-b border-slate-100 bg-slate-50/80 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="font-semibold text-slate-800">
          {{ compact ? 'Nous situer' : 'Carte — Google Maps' }}
        </h2>
        <p v-if="directionsHint" class="text-xs text-slate-500 mt-1">{{ directionsHint }}</p>
      </div>
      <div v-if="hasGoogle && hasOsm && !compact" class="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
        <button
          type="button"
          class="px-3 py-1.5 font-medium transition"
          :class="mapTab === 'google' ? 'bg-teal-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'"
          @click="mapTab = 'google'"
        >
          Google Maps
        </button>
        <button
          type="button"
          class="px-3 py-1.5 font-medium transition border-l border-slate-200"
          :class="mapTab === 'osm' ? 'bg-teal-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'"
          @click="mapTab = 'osm'"
        >
          Plan
        </button>
      </div>
    </div>

    <div
      class="relative bg-slate-100"
      :class="compact ? 'aspect-[16/9]' : 'aspect-[16/10] sm:aspect-[2/1]'"
    >
      <iframe
        v-if="activeSrc"
        :src="activeSrc"
        title="Carte — Centre Hospitalier SGHL, Dolisie"
        class="absolute inset-0 w-full h-full border-0"
        loading="lazy"
        allowfullscreen
        referrerpolicy="no-referrer-when-downgrade"
      />
      <div v-else class="absolute inset-0 flex items-center justify-center text-sm text-slate-500">
        Carte indisponible
      </div>
    </div>

    <div class="px-5 py-3 flex flex-wrap gap-3 border-t border-slate-100 bg-white">
      <a
        v-if="googleMapsDirectionsUrl"
        :href="googleMapsDirectionsUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1.5 text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 px-3 py-1.5 rounded-lg transition"
      >
        <span aria-hidden="true">🧭</span>
        Itinéraire
      </a>
      <a
        v-if="googleMapsUrl"
        :href="googleMapsUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1.5 text-sm font-medium text-teal-700 hover:text-teal-900 hover:underline"
      >
        <span aria-hidden="true">🗺️</span>
        Ouvrir dans Google Maps
      </a>
      <a
        v-if="openstreetmapUrl"
        :href="openstreetmapUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 hover:underline"
      >
        <span aria-hidden="true">📍</span>
        OpenStreetMap
      </a>
    </div>
  </section>
</template>
