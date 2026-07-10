<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import Modal from '../components/Modal.vue'
import FormField from '../components/FormField.vue'
import {
  validators,
  blockDigitsInName,
  sanitizeNamePaste,
  validateFields,
  hasErrors,
} from '../composables/useFormValidation'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const tab = ref(route.query.tab === 'sessions' ? 'sessions' : 'accounts')
const users = ref([])
const onlineUsers = ref([])
const roles = ref([])
const loading = ref(true)
const onlineLoading = ref(false)
const showModal = ref(false)
const editing = ref(null)
const error = ref('')
const loadError = ref('')
const fieldErrors = ref({})
const search = ref('')
const filterRole = ref('')
const showInactive = ref(true)
const activeOnly = ref(false)
const lastOnlineRefresh = ref(null)

const form = ref({
  username: '', email: '', password: '', first_name: '', last_name: '', phone: '',
  is_staff: false, role_codes: [],
})

const accountHeaders = [
  { key: 'username', label: 'Identifiant' },
  { key: 'name', label: 'Nom' },
  { key: 'email', label: 'Email' },
  { key: 'roles', label: 'Rôles' },
  { key: 'connection', label: 'Connexion' },
  { key: 'mfa', label: 'MFA' },
  { key: 'status', label: 'Statut' },
]

const sessionHeaders = [
  { key: 'user', label: 'Utilisateur' },
  { key: 'roles', label: 'Rôles' },
  { key: 'activity', label: 'Activité' },
  { key: 'sessions', label: 'Sessions' },
  { key: 'ip', label: 'IP' },
]

const ROLE_META = {
  ADMIN: { icon: '🛡️', color: 'border-violet-300 bg-violet-50 text-violet-800' },
  SECRETARY: { icon: '📋', color: 'border-blue-300 bg-blue-50 text-blue-800' },
  DOCTOR: { icon: '🩺', color: 'border-teal-300 bg-teal-50 text-teal-800' },
  NURSE: { icon: '💉', color: 'border-pink-300 bg-pink-50 text-pink-800' },
  BIOLOGIST: { icon: '🔬', color: 'border-amber-300 bg-amber-50 text-amber-800' },
  PHARMACIST: { icon: '💊', color: 'border-green-300 bg-green-50 text-green-800' },
  PATIENT: { icon: '👤', color: 'border-slate-300 bg-slate-50 text-slate-700' },
}

const stats = computed(() => ({
  total: users.value.length,
  active: users.value.filter((u) => u.is_active).length,
  connected: users.value.filter((u) => u.has_active_session).length,
  online: users.value.filter((u) => u.is_online).length,
}))

const sessionRows = computed(() =>
  onlineUsers.value.map((u) => ({
    ...u,
    activity: formatActivity(u.last_seen_at),
    sessions: u.sessions.length,
    ip: u.last_login_ip || u.sessions[0]?.ip_address || '—',
  }))
)

let searchTimer
let onlineTimer

watch(tab, (value) => {
  router.replace({ query: value === 'sessions' ? { tab: 'sessions' } : {} })
  if (value === 'sessions') loadOnline()
})

watch(() => route.query.tab, (q) => {
  const next = q === 'sessions' ? 'sessions' : 'accounts'
  if (tab.value !== next) tab.value = next
})

watch([search, filterRole, showInactive], () => {
  if (tab.value !== 'accounts') return
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadAccounts, 300)
})

function formatActivity(iso) {
  if (!iso) return 'Connecté (inactif)'
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return 'En ligne'
  if (diff < 3600) return `Actif il y a ${Math.floor(diff / 60)} min`
  return new Date(iso).toLocaleString('fr-FR')
}

function isRecentlyActive(iso) {
  if (!iso) return false
  return Date.now() - new Date(iso).getTime() < 15 * 60 * 1000
}

function connectionLabel(row) {
  if (row.is_online) return 'En ligne'
  if (row.has_active_session) return 'Session active'
  return 'Hors ligne'
}

async function loadAccounts() {
  loading.value = true
  loadError.value = ''
  try {
    const params = new URLSearchParams()
    if (showInactive.value) params.set('include_inactive', 'true')
    if (filterRole.value) params.set('role', filterRole.value)
    if (search.value.trim()) params.set('search', search.value.trim())

    const { data } = await api.get(`/users/?${params}`)
    users.value = data.map((x) => ({
      ...x,
      name: `${x.first_name} ${x.last_name}`.trim() || '—',
      status: x.is_active ? 'Actif' : 'Inactif',
      mfa: x.mfa_enabled ? 'Activé' : '—',
      connection: connectionLabel(x),
    }))

    if (!roles.value.length) {
      try {
        const { data: rolesData } = await api.get('/roles/')
        roles.value = rolesData
      } catch {
        loadError.value = 'Comptes chargés, mais la liste des rôles est indisponible.'
      }
    }
  } catch (e) {
    loadError.value = e.response?.data?.detail || 'Impossible de charger les utilisateurs.'
  } finally {
    loading.value = false
  }
}

async function loadOnline() {
  onlineLoading.value = true
  try {
    const { data } = await api.get('/online-users/', { params: { active_only: activeOnly.value } })
    onlineUsers.value = data
    lastOnlineRefresh.value = new Date()
  } finally {
    onlineLoading.value = false
  }
}

async function load() {
  await loadAccounts()
  if (tab.value === 'sessions') await loadOnline()
}

function openCreate() {
  editing.value = null
  form.value = { username: '', email: '', password: '', first_name: '', last_name: '', phone: '', is_staff: false, role_codes: [] }
  error.value = ''
  fieldErrors.value = {}
  showModal.value = true
}

function openEdit(row) {
  editing.value = row
  form.value = {
    username: row.username, email: row.email, password: '',
    first_name: row.first_name, last_name: row.last_name, phone: row.phone || '',
    is_staff: row.is_staff, role_codes: [...row.roles],
  }
  error.value = ''
  fieldErrors.value = {}
  showModal.value = true
}

function onNamePaste(field, event) {
  sanitizeNamePaste(event, (text) => {
    form.value[field] = text
  })
}

function stripDigitsFromName(field) {
  form.value[field] = form.value[field].replace(/\d/g, '')
}

function validateUserForm() {
  fieldErrors.value = validateFields({
    username: () => (editing.value ? '' : validators.username(form.value.username)),
    email: () => validators.email(form.value.email, true),
    first_name: () => (form.value.first_name.trim() ? validators.personName(form.value.first_name, 'Prénom') : ''),
    last_name: () => (form.value.last_name.trim() ? validators.personName(form.value.last_name, 'Nom') : ''),
    phone: () => validators.phone(form.value.phone),
    password: () => (editing.value && !form.value.password ? '' : validators.password(form.value.password)),
  })
  return !hasErrors(fieldErrors.value)
}

function toggleRole(code) {
  const idx = form.value.role_codes.indexOf(code)
  if (idx >= 0) form.value.role_codes.splice(idx, 1)
  else form.value.role_codes.push(code)
}

async function save() {
  error.value = ''
  if (!form.value.role_codes.length) {
    error.value = 'Sélectionnez au moins un rôle.'
    return
  }
  if (!validateUserForm()) return
  try {
    if (editing.value) {
      const payload = { ...form.value }
      if (!payload.password) delete payload.password
      delete payload.username
      await api.patch(`/users/${editing.value.id}/`, payload)
    } else {
      await api.post('/users/', form.value)
    }
    showModal.value = false
    await loadAccounts()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur enregistrement'
  }
}

async function toggleActive(row) {
  if (row.id === auth.user?.id && row.is_active) {
    loadError.value = 'Vous ne pouvez pas désactiver votre propre compte.'
    return
  }
  const action = row.is_active ? 'désactiver' : 'activer'
  if (!window.confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} le compte « ${row.username} » ?`)) return
  loadError.value = ''
  try {
    await api.post(`/users/${row.id}/${row.is_active ? 'deactivate' : 'activate'}/`)
    await loadAccounts()
    if (tab.value === 'sessions') await loadOnline()
  } catch (e) {
    loadError.value = e.response?.data?.detail || `Impossible de ${action} le compte.`
  }
}

onMounted(async () => {
  await load()
  onlineTimer = setInterval(() => {
    if (tab.value === 'sessions') loadOnline()
  }, 30000)
})

onUnmounted(() => {
  clearTimeout(searchTimer)
  if (onlineTimer) clearInterval(onlineTimer)
})
</script>

<template>
  <div>
    <PageHeader
      title="Utilisateurs"
      :subtitle="`${stats.total} compte(s) — gestion RBAC, comptes et sessions actives`"
    >
      <template #actions>
        <button v-if="tab === 'accounts'" type="button" class="btn-primary" @click="openCreate">
          + Nouvel utilisateur
        </button>
      </template>
    </PageHeader>

    <div class="flex flex-wrap gap-2 mb-6">
      <button
        type="button"
        class="tab-btn"
        :class="tab === 'accounts' ? 'tab-btn-active' : 'tab-btn-inactive'"
        @click="tab = 'accounts'"
      >
        Comptes
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="tab === 'sessions' ? 'tab-btn-active' : 'tab-btn-inactive'"
        @click="tab = 'sessions'"
      >
        Sessions connectées
        <span v-if="stats.connected" class="ml-1.5 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold">
          {{ stats.connected }}
        </span>
      </button>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div class="stat-card !py-3">
        <p class="text-[10px] font-semibold text-slate-500 uppercase">Comptes</p>
        <p class="text-2xl font-bold text-admin">{{ stats.total }}</p>
      </div>
      <div class="stat-card !py-3">
        <p class="text-[10px] font-semibold text-slate-500 uppercase">Actifs</p>
        <p class="text-2xl font-bold text-slate-800">{{ stats.active }}</p>
      </div>
      <div class="stat-card !py-3">
        <p class="text-[10px] font-semibold text-slate-500 uppercase">Sessions</p>
        <p class="text-2xl font-bold text-amber-600">{{ stats.connected }}</p>
      </div>
      <div class="stat-card !py-3">
        <p class="text-[10px] font-semibold text-slate-500 uppercase">En ligne</p>
        <p class="text-2xl font-bold text-emerald-600">{{ stats.online }}</p>
      </div>
    </div>

    <p v-if="loadError" class="alert-error mb-4">{{ loadError }}</p>

    <!-- Onglet Comptes -->
    <template v-if="tab === 'accounts'">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <div class="card card-body !py-3 text-sm">
          <p class="font-semibold text-admin">🛡️ Admin</p>
          <p class="text-slate-500 text-xs mt-1">Rôle ADMIN → <code class="text-xs">/admin/</code></p>
        </div>
        <div class="card card-body !py-3 text-sm">
          <p class="font-semibold text-teal-700">🏥 Personnel</p>
          <p class="text-slate-500 text-xs mt-1">Médecin, infirmier… → portail staff</p>
        </div>
        <div class="card card-body !py-3 text-sm">
          <p class="font-semibold text-slate-700">👤 Patient</p>
          <p class="text-slate-500 text-xs mt-1">Rôle PATIENT → <code class="text-xs">/patient</code></p>
        </div>
      </div>

      <div class="card card-body mb-6 flex flex-col sm:flex-row gap-3">
        <input v-model="search" type="search" placeholder="Rechercher nom, email, identifiant…" class="form-input flex-1" />
        <select v-model="filterRole" class="form-select sm:w-44">
          <option value="">Tous les rôles</option>
          <option v-for="r in roles" :key="r.code" :value="r.code">{{ r.name }}</option>
        </select>
        <label class="flex items-center gap-2 text-sm text-slate-600 shrink-0 cursor-pointer">
          <input v-model="showInactive" type="checkbox" class="rounded" />
          Inactifs
        </label>
      </div>

      <DataTable :headers="accountHeaders" :rows="users" :loading="loading" empty-title="Aucun utilisateur trouvé">
        <template #cell-roles="{ row }">
          <span
            v-for="(code, i) in row.roles"
            :key="code"
            class="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-lg border mr-1 font-medium"
            :class="ROLE_META[code]?.color || 'border-slate-200 bg-slate-50'"
          >
            {{ ROLE_META[code]?.icon || '•' }} {{ row.role_labels?.[i] || code }}
          </span>
        </template>
        <template #cell-connection="{ row }">
          <span
            class="inline-flex items-center gap-1.5 text-xs font-medium"
            :class="row.is_online ? 'text-emerald-600' : row.has_active_session ? 'text-amber-600' : 'text-slate-400'"
          >
            <span
              class="w-2 h-2 rounded-full"
              :class="row.is_online ? 'bg-emerald-500' : row.has_active_session ? 'bg-amber-400' : 'bg-slate-300'"
            />
            {{ row.connection }}
          </span>
        </template>
        <template #cell-mfa="{ value }">
          <span :class="value === 'Activé' ? 'text-emerald-600 font-medium' : 'text-slate-400'">{{ value }}</span>
        </template>
        <template #cell-status="{ value }">
          <span :class="value === 'Actif' ? 'text-emerald-600 font-medium' : 'text-red-500'">{{ value }}</span>
        </template>
        <template #actions="{ row }">
          <button type="button" class="text-admin text-xs font-medium hover:underline mr-3" @click="openEdit(row)">
            Modifier
          </button>
          <button
            type="button"
            class="text-xs font-medium hover:underline"
            :class="row.is_active ? 'text-red-500' : 'text-emerald-600'"
            :disabled="row.id === auth.user?.id && row.is_active"
            @click="toggleActive(row)"
          >
            {{ row.is_active ? 'Désactiver' : 'Activer' }}
          </button>
        </template>
      </DataTable>
    </template>

    <!-- Onglet Sessions -->
    <template v-else>
      <div class="flex flex-wrap items-center gap-3 mb-6">
        <label class="inline-flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
          <input v-model="activeOnly" type="checkbox" class="rounded border-slate-300" @change="loadOnline" />
          Uniquement activité récente (15 min)
        </label>
        <button type="button" class="btn-secondary text-sm" @click="loadOnline">Actualiser</button>
        <span v-if="lastOnlineRefresh" class="text-xs text-slate-400">
          Dernière mise à jour : {{ lastOnlineRefresh.toLocaleTimeString('fr-FR') }}
        </span>
        <span class="ml-auto text-sm font-medium text-admin">{{ onlineUsers.length }} connecté(s)</span>
      </div>

      <DataTable
        :headers="sessionHeaders"
        :rows="sessionRows"
        :loading="onlineLoading"
        empty-title="Aucun utilisateur connecté"
      >
        <template #cell-user="{ row }">
          <div class="flex items-center gap-2">
            <span
              class="w-2 h-2 rounded-full shrink-0"
              :class="isRecentlyActive(row.last_seen_at) ? 'bg-emerald-500' : 'bg-amber-400'"
            />
            <div>
              <p class="font-medium text-slate-800">{{ row.full_name }}</p>
              <p class="text-xs text-slate-500">{{ row.username }} · {{ row.email }}</p>
            </div>
          </div>
        </template>
        <template #cell-roles="{ row }">
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(code, i) in row.roles"
              :key="code"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border text-xs font-medium"
              :class="ROLE_META[code]?.color || 'border-slate-200 bg-slate-50'"
            >
              {{ ROLE_META[code]?.icon || '•' }} {{ row.role_labels[i] || code }}
            </span>
          </div>
        </template>
        <template #cell-activity="{ row }">
          <span :class="isRecentlyActive(row.last_seen_at) ? 'text-emerald-600 font-medium' : 'text-slate-500'">
            {{ formatActivity(row.last_seen_at) }}
          </span>
        </template>
        <template #cell-sessions="{ value, row }">
          <span class="text-sm">{{ value }}</span>
          <p
            v-if="row.sessions?.length"
            class="text-[10px] text-slate-400 mt-0.5 truncate max-w-[180px]"
            :title="row.sessions[0].user_agent"
          >
            {{ row.sessions[0].user_agent || 'Navigateur inconnu' }}
          </p>
        </template>
      </DataTable>
    </template>

    <Modal :open="showModal" :title="editing ? 'Modifier utilisateur' : 'Nouvel utilisateur'" wide @close="showModal = false">
      <p v-if="error" class="alert-error mb-4">{{ error }}</p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <FormField label="Identifiant" :error="fieldErrors.username" :required="!editing">
          <input v-model="form.username" :disabled="!!editing" class="form-input" />
        </FormField>
        <FormField label="Email" :error="fieldErrors.email" required>
          <input v-model="form.email" type="email" class="form-input" />
        </FormField>
        <FormField label="Prénom" :error="fieldErrors.first_name">
          <input
            v-model="form.first_name"
            class="form-input"
            @keydown="blockDigitsInName"
            @input="stripDigitsFromName('first_name')"
            @paste="onNamePaste('first_name', $event)"
          />
        </FormField>
        <FormField label="Nom" :error="fieldErrors.last_name">
          <input
            v-model="form.last_name"
            class="form-input"
            @keydown="blockDigitsInName"
            @input="stripDigitsFromName('last_name')"
            @paste="onNamePaste('last_name', $event)"
          />
        </FormField>
        <FormField label="Téléphone" :error="fieldErrors.phone">
          <input v-model="form.phone" type="tel" class="form-input" />
        </FormField>
        <FormField :label="editing ? 'Nouveau mot de passe (opt.)' : 'Mot de passe'" :error="fieldErrors.password" :required="!editing">
          <input v-model="form.password" type="password" class="form-input" />
        </FormField>
      </div>

      <label class="flex items-center gap-2 text-sm text-slate-700 mb-6 cursor-pointer">
        <input v-model="form.is_staff" type="checkbox" class="rounded border-slate-300" />
        Accès staff Django (is_staff)
      </label>

      <p class="form-label mb-3">Rôles — détermine le portail et les permissions</p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2">
        <button
          v-for="r in roles"
          :key="r.code"
          type="button"
          class="flex items-start gap-3 p-3 rounded-xl border-2 text-left transition"
          :class="form.role_codes.includes(r.code) ? 'border-admin bg-violet-50' : 'border-slate-200 hover:border-slate-300'"
          @click="toggleRole(r.code)"
        >
          <span class="text-xl">{{ ROLE_META[r.code]?.icon || '👤' }}</span>
          <div>
            <p class="font-semibold text-sm">{{ r.name }}</p>
            <p class="text-xs text-slate-500">{{ r.user_count }} compte(s) · {{ r.permissions.length }} perm.</p>
            <p class="text-xs text-slate-400 mt-0.5">{{ r.description }}</p>
          </div>
        </button>
      </div>

      <template #footer>
        <button type="button" class="btn-secondary" @click="showModal = false">Annuler</button>
        <button type="button" class="btn-primary" @click="save">Enregistrer</button>
      </template>
    </Modal>
  </div>
</template>
