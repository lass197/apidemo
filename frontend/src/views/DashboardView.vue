<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/ui/StatCard.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import LoadingState from '../components/ui/LoadingState.vue'
import { formatMoney } from '../composables/currency'

const kpis = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get('/dashboard/kpis/')
    kpis.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Impossible de charger les indicateurs.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader
      title="Tableau de bord"
      subtitle="Vue d'ensemble de l'activité hospitalière en temps réel"
    />

    <LoadingState v-if="loading" />

    <AlertBanner v-else-if="error" type="error" title="Erreur de chargement">
      {{ error }}
      <p class="mt-2 opacity-80">Vérifiez que le backend tourne sur le port 8000.</p>
    </AlertBanner>

    <div v-else-if="kpis" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 lg:gap-5">
      <StatCard
        label="Taux d'occupation"
        :value="`${kpis.occupancy_rate}%`"
        :hint="`${kpis.occupied_beds} / ${kpis.total_beds} lits occupés`"
        tone="primary"
        icon="🛏️"
      />
      <StatCard
        label="Hospitalisations actives"
        :value="kpis.active_hospitalizations"
        hint="Patients actuellement hospitalisés"
        tone="blue"
        icon="🏥"
      />
      <StatCard
        label="Recettes du jour"
        :value="formatMoney(kpis.revenue_today)"
        hint="Encaissements enregistrés aujourd'hui (FCFA)"
        tone="green"
        icon="💰"
      />
      <StatCard
        label="Examens labo en attente"
        :value="kpis.pending_lab_exams"
        hint="Résultats à valider ou traiter"
        tone="orange"
        icon="🔬"
      />
    </div>
  </div>
</template>
