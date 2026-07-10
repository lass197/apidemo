<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'

const matrix = ref(null)
const loading = ref(true)
const search = ref('')
const selectedModule = ref('all')
const selectedRole = ref(null)

const ROLE_COLORS = {
  ADMIN: 'bg-violet-100 text-violet-800 border-violet-200',
  SECRETARY: 'bg-blue-100 text-blue-800 border-blue-200',
  ACCOUNTANT: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  DOCTOR: 'bg-teal-100 text-teal-800 border-teal-200',
  NURSE: 'bg-pink-100 text-pink-800 border-pink-200',
  BIOLOGIST: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  PHARMACIST: 'bg-amber-100 text-amber-800 border-amber-200',
  PATIENT: 'bg-slate-100 text-slate-700 border-slate-200',
}

const MODULE_LABELS = {
  core: 'Système',
  clinical: 'Clinique',
  laboratory: 'Laboratoire',
  billing: 'Facturation',
  pharmacy: 'Pharmacie',
  hr: 'RH',
  documents: 'Documents',
}

onMounted(async () => {
  try {
    const { data } = await api.get('/rbac/matrix/')
    matrix.value = data
    if (data.roles.length) selectedRole.value = data.roles[0].code
  } finally {
    loading.value = false
  }
})

const filteredPermissions = computed(() => {
  if (!matrix.value) return []
  let perms = matrix.value.permissions
  if (selectedModule.value !== 'all') {
    perms = perms.filter((p) => p.module === selectedModule.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    perms = perms.filter(
      (p) => p.codename.toLowerCase().includes(q) || p.name.toLowerCase().includes(q)
    )
  }
  return perms
})

const selectedRoleData = computed(() =>
  matrix.value?.roles.find((r) => r.code === selectedRole.value)
)

function hasPerm(roleCode, permCode) {
  return matrix.value?.matrix?.[roleCode]?.[permCode] ?? false
}

function countPermsForRole(roleCode) {
  if (!matrix.value) return 0
  return Object.values(matrix.value.matrix[roleCode] || {}).filter(Boolean).length
}
</script>

<template>
  <div>
    <PageHeader
      title="Rôles & permissions"
      subtitle="Matrice RBAC — qui peut faire quoi dans SGHL"
    />

    <div v-if="loading" class="card p-12 text-center text-slate-500">Chargement de la matrice…</div>

    <template v-else-if="matrix">
      <!-- Cartes rôles -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3 mb-8">
        <button
          v-for="role in matrix.roles"
          :key="role.code"
          type="button"
          class="card card-body !p-4 text-left transition ring-2 ring-transparent hover:ring-admin/30"
          :class="{ '!ring-admin': selectedRole === role.code }"
          @click="selectedRole = role.code"
        >
          <span class="text-xs font-bold px-2 py-0.5 rounded-full border" :class="ROLE_COLORS[role.code]">
            {{ role.code }}
          </span>
          <p class="font-semibold mt-2 text-sm">{{ role.name }}</p>
          <p class="text-xs text-slate-500 mt-1">{{ role.user_count }} utilisateur(s)</p>
          <p class="text-xs text-admin font-medium mt-1">{{ countPermsForRole(role.code) }} / {{ matrix.permissions.length }} perm.</p>
        </button>
      </div>

      <!-- Détail rôle sélectionné -->
      <div v-if="selectedRoleData" class="card card-body mb-8 border-admin/20 bg-violet-50/30">
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <h3 class="text-xl font-bold">{{ selectedRoleData.name }}</h3>
            <p class="text-sm text-slate-600 mt-1">{{ selectedRoleData.description }}</p>
            <p class="text-xs font-mono text-slate-400 mt-2">{{ selectedRoleData.code }}</p>
          </div>
          <div class="text-right shrink-0">
            <p class="text-3xl font-bold text-admin">{{ selectedRoleData.user_count }}</p>
            <p class="text-xs text-slate-500">comptes actifs</p>
          </div>
        </div>
      </div>

      <!-- Filtres matrice -->
      <div class="flex flex-col sm:flex-row gap-3 mb-4">
        <input v-model="search" type="search" placeholder="Rechercher une permission…" class="form-input flex-1" />
        <select v-model="selectedModule" class="form-select sm:w-48">
          <option value="all">Tous les modules</option>
          <option v-for="m in matrix.modules" :key="m" :value="m">{{ MODULE_LABELS[m] || m }}</option>
        </select>
      </div>

      <!-- Matrice tableau -->
      <div class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-slate-50 border-b">
                <th class="text-left px-4 py-3 font-semibold text-slate-600 sticky left-0 bg-slate-50 min-w-[220px]">
                  Permission
                </th>
                <th
                  v-for="role in matrix.roles"
                  :key="role.code"
                  class="px-3 py-3 text-center font-semibold text-xs min-w-[72px]"
                  :class="{ 'bg-violet-50': selectedRole === role.code }"
                >
                  <span class="block truncate" :title="role.name">{{ role.code }}</span>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <template v-for="mod in matrix.modules" :key="mod">
                <tr v-if="selectedModule === 'all'" class="bg-slate-100/60">
                  <td :colspan="matrix.roles.length + 1" class="px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                    {{ MODULE_LABELS[mod] || mod }}
                  </td>
                </tr>
                <tr
                  v-for="perm in filteredPermissions.filter((p) => p.module === mod)"
                  :key="perm.codename"
                  class="hover:bg-slate-50/50"
                >
                  <td class="px-4 py-2.5 sticky left-0 bg-white">
                    <p class="font-mono text-xs text-admin">{{ perm.codename }}</p>
                    <p class="text-xs text-slate-500">{{ perm.name }}</p>
                  </td>
                  <td
                    v-for="role in matrix.roles"
                    :key="role.code"
                    class="text-center px-3 py-2.5"
                    :class="{ 'bg-violet-50/50': selectedRole === role.code }"
                  >
                    <span
                      v-if="hasPerm(role.code, perm.codename)"
                      class="inline-flex w-6 h-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold"
                      title="Autorisé"
                    >✓</span>
                    <span v-else class="inline-block w-6 h-6 rounded-full bg-slate-100" title="Refusé" />
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <p class="text-xs text-slate-400 mt-4">
        La matrice RBAC est définie dans le code (`core/services/rbac.py`) et synchronisée au seed.
        Les modifications runtime ne sont pas encore supportées — contactez un développeur pour ajouter des permissions.
      </p>
    </template>
  </div>
</template>
