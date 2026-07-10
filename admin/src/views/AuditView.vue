<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'

const tab = ref('audit')
const auditLogs = ref([])
const loginLogs = ref([])
const loading = ref(true)

const auditHeaders = [
  { key: 'timestamp', label: 'Date' },
  { key: 'username', label: 'Utilisateur' },
  { key: 'action_type', label: 'Action' },
  { key: 'resource_type', label: 'Ressource' },
  { key: 'ip_address', label: 'IP' },
]
const loginHeaders = [
  { key: 'created_at', label: 'Date' },
  { key: 'username_attempt', label: 'Identifiant' },
  { key: 'status', label: 'Statut' },
  { key: 'ip_address', label: 'IP' },
  { key: 'failure_reason', label: 'Détail' },
]

onMounted(async () => {
  const [a, l] = await Promise.all([api.get('/audit/'), api.get('/login-logs/')])
  auditLogs.value = a.data.map((x) => ({ ...x, timestamp: new Date(x.timestamp).toLocaleString('fr-FR') }))
  loginLogs.value = l.data.map((x) => ({ ...x, created_at: new Date(x.created_at).toLocaleString('fr-FR') }))
  loading.value = false
})
</script>

<template>
  <div>
    <PageHeader title="Audit & sécurité" subtitle="Livre-journal immuable et historique des connexions" />

    <div class="flex flex-wrap gap-2 mb-6">
      <button type="button" @click="tab = 'audit'" :class="tab === 'audit' ? 'tab-btn-active' : 'tab-btn-inactive'" class="tab-btn">
        Audit trail
      </button>
      <button type="button" @click="tab = 'login'" :class="tab === 'login' ? 'tab-btn-active' : 'tab-btn-inactive'" class="tab-btn">
        Connexions
      </button>
    </div>

    <DataTable v-if="tab === 'audit'" :headers="auditHeaders" :rows="auditLogs" :loading="loading" empty-title="Aucune entrée d'audit" />
    <DataTable v-else :headers="loginHeaders" :rows="loginLogs" :loading="loading" empty-title="Aucun log de connexion">
      <template #cell-status="{ value }">
        <span :class="value === 'SUCCESS' ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'">{{ value }}</span>
      </template>
    </DataTable>
  </div>
</template>
