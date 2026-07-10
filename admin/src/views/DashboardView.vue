<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'

const stats = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/stats/')
    stats.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader title="Administration SGHL" subtitle="Console système — gestion, audit et infrastructure" />

    <div v-if="loading" class="card p-10 text-center text-slate-500">Chargement…</div>

    <template v-else-if="stats">
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <div class="stat-card">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Utilisateurs</p>
          <p class="text-3xl font-bold text-admin mt-1">{{ stats.users_active }}/{{ stats.users_total }}</p>
        </div>
        <div class="stat-card">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Connectés</p>
          <p class="text-3xl font-bold text-emerald-600 mt-1">{{ stats.users_online }}</p>
        </div>
        <div class="stat-card">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Audit aujourd'hui</p>
          <p class="text-3xl font-bold text-blue-600 mt-1">{{ stats.audit_today }}</p>
        </div>
        <div class="stat-card">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Échecs login</p>
          <p class="text-3xl font-bold text-red-600 mt-1">{{ stats.failed_logins_today }}</p>
        </div>
        <div class="stat-card">
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Occupation</p>
          <p class="text-3xl font-bold text-teal-600 mt-1">{{ stats.kpis.occupancy_rate }}%</p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <router-link to="/users" class="card card-body hover:shadow-md hover:border-admin/30 transition group">
          <h3 class="font-semibold group-hover:text-admin transition">Utilisateurs</h3>
          <p class="text-sm text-slate-500 mt-1">CRUD comptes et RBAC</p>
        </router-link>
        <router-link to="/users?tab=sessions" class="card card-body hover:shadow-md hover:border-admin/30 transition group">
          <h3 class="font-semibold group-hover:text-admin transition">Sessions connectées</h3>
          <p class="text-sm text-slate-500 mt-1">Utilisateurs en ligne et rôles</p>
        </router-link>
        <router-link to="/audit" class="card card-body hover:shadow-md hover:border-admin/30 transition group">
          <h3 class="font-semibold group-hover:text-admin transition">Audit trail</h3>
          <p class="text-sm text-slate-500 mt-1">Journal immuable des actions</p>
        </router-link>
        <router-link to="/security" class="card card-body hover:shadow-md hover:border-admin/30 transition group">
          <h3 class="font-semibold group-hover:text-admin transition">MFA & sécurité</h3>
          <p class="text-sm text-slate-500 mt-1">Authentification à deux facteurs</p>
        </router-link>
        <router-link to="/infrastructure" class="card card-body hover:shadow-md hover:border-admin/30 transition group">
          <h3 class="font-semibold group-hover:text-admin transition">Infrastructure</h3>
          <p class="text-sm text-slate-500 mt-1">Bâtiments, services, lits</p>
        </router-link>
        <router-link to="/accounting" class="card card-body hover:shadow-md hover:border-admin/30 transition group">
          <h3 class="font-semibold group-hover:text-admin transition">Comptabilité</h3>
          <p class="text-sm text-slate-500 mt-1">Ajustements comptables</p>
        </router-link>
      </div>
    </template>
  </div>
</template>
