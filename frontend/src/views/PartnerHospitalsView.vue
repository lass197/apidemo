<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const hospitals = ref([])
const cities = ref([])
const search = ref('')
const cityFilter = ref('')
const onlyAvailable = ref(false)
const expandedId = ref(null)

const stats = computed(() => ({
  total: hospitals.value.length,
  available: hospitals.value.filter((h) => h.can_receive).length,
  beds: hospitals.value.reduce((sum, h) => sum + h.available_beds, 0),
}))

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}

function goToTransfer(hospitalId) {
  router.push({ path: '/transfers', query: { partner: hospitalId } })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { only_available: onlyAvailable.value }
    if (search.value.trim()) params.search = search.value.trim()
    if (cityFilter.value) params.city = cityFilter.value
    const [list, cityList] = await Promise.all([
      api.get('/clinical/partner-hospitals/', { params }),
      api.get('/clinical/partner-hospitals/cities/'),
    ])
    hospitals.value = list.data
    cities.value = cityList.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de charger les établissements partenaires.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Hôpitaux partenaires"
      subtitle="Réseau d'établissements disponibles pour recevoir des patients transférés"
    />

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>

    <div v-if="!loading && hospitals.length" class="grid grid-cols-3 gap-3 mb-6">
      <div class="card card-body text-center py-4">
        <p class="text-2xl font-bold text-slate-900">{{ stats.total }}</p>
        <p class="text-xs text-slate-500">Établissements</p>
      </div>
      <div class="card card-body text-center py-4">
        <p class="text-2xl font-bold text-emerald-700">{{ stats.available }}</p>
        <p class="text-xs text-slate-500">Peuvent recevoir</p>
      </div>
      <div class="card card-body text-center py-4">
        <p class="text-2xl font-bold text-primary-700">{{ stats.beds }}</p>
        <p class="text-xs text-slate-500">Lits disponibles</p>
      </div>
    </div>

    <div class="card card-body mb-6 flex flex-wrap gap-3 items-end">
      <label class="block flex-1 min-w-[12rem]">
        <span class="form-label">Rechercher</span>
        <input
          v-model="search"
          type="search"
          class="form-input"
          placeholder="Nom, ville, spécialité…"
          @keyup.enter="load"
        />
      </label>
      <label class="block min-w-[10rem]">
        <span class="form-label">Ville</span>
        <select v-model="cityFilter" class="form-select" @change="load">
          <option value="">Toutes les villes</option>
          <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <label class="flex items-center gap-2 text-sm text-slate-600 pb-2 cursor-pointer whitespace-nowrap">
        <input v-model="onlyAvailable" type="checkbox" class="rounded border-slate-300" @change="load" />
        Uniquement avec lits libres
      </label>
      <button type="button" class="btn-secondary text-sm" @click="load">Actualiser</button>
    </div>

    <LoadingState v-if="loading" />

    <EmptyState
      v-else-if="!hospitals.length"
      title="Aucun établissement trouvé"
      description="Modifiez les filtres ou contactez l'administration pour mettre à jour le réseau partenaire."
      icon="🏥"
    />

    <p v-else class="text-xs text-slate-500 mb-3">{{ hospitals.length }} établissement(s)</p>

    <div v-if="!loading && hospitals.length" class="space-y-3">
      <article
        v-for="h in hospitals"
        :key="h.id"
        class="card overflow-hidden"
        :class="h.can_receive ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-slate-300'"
      >
        <div class="card-body">
          <div class="flex flex-wrap justify-between gap-3 items-start">
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2 mb-1">
                <h2 class="font-semibold text-slate-900">{{ h.name }}</h2>
                <StatusBadge :status="h.can_receive ? 'Disponible' : 'Complet'" />
              </div>
              <p class="text-sm text-slate-600 mb-1">{{ h.city }}</p>
              <p v-if="h.address" class="text-sm text-slate-500">{{ h.address }}</p>
              <p class="text-sm mt-2">
                <span class="font-medium text-slate-800">{{ h.available_beds }}</span>
                <span class="text-slate-500"> / {{ h.total_beds }} lits disponibles</span>
              </p>
              <p v-if="h.phone" class="text-xs text-slate-500 mt-1">{{ h.phone }}</p>
            </div>
            <div class="flex flex-wrap gap-2 shrink-0">
              <button type="button" class="btn-secondary text-xs !py-2" @click="toggleExpand(h.id)">
                {{ expandedId === h.id ? 'Masquer les détails' : 'Voir les détails' }}
              </button>
              <button
                v-if="auth.hasPerm('clinical.transfer') && h.can_receive"
                type="button"
                class="btn-primary text-xs !py-2"
                @click="goToTransfer(h.id)"
              >
                Proposer un transfert
              </button>
            </div>
          </div>

          <div v-if="expandedId === h.id" class="mt-4 pt-4 border-t border-slate-100">
            <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Spécialités</h3>
            <p v-if="h.specialties" class="text-sm text-slate-700">{{ h.specialties }}</p>
            <p v-else class="text-sm text-slate-400">Non renseignées.</p>
            <div class="mt-3 flex items-center gap-2">
              <div
                class="h-2 flex-1 max-w-xs rounded-full bg-slate-100 overflow-hidden"
                role="presentation"
              >
                <div
                  class="h-full rounded-full transition-all"
                  :class="h.can_receive ? 'bg-emerald-500' : 'bg-slate-400'"
                  :style="{ width: `${h.total_beds ? (h.available_beds / h.total_beds) * 100 : 0}%` }"
                />
              </div>
              <span class="text-xs text-slate-500">
                {{ h.total_beds ? Math.round((h.available_beds / h.total_beds) * 100) : 0 }} % de capacité libre
              </span>
            </div>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
