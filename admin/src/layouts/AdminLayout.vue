<script setup>
import { ref } from 'vue'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const sidebarOpen = ref(false)

const NAV = [
  { to: '/dashboard', label: 'Tableau de bord', icon: '📊', permission: 'core.manage_users' },
  { to: '/users', label: 'Utilisateurs', icon: '👤', permission: 'core.manage_users' },
  { to: '/roles', label: 'Rôles & permissions', icon: '🔐', permission: 'core.manage_users' },
  { to: '/audit', label: 'Audit & sécurité', icon: '📋', permission: 'core.view_audit' },
  { to: '/clinical-movements', label: 'Mouvements patients', icon: '🏥', permission: 'core.view_audit' },
  { to: '/security', label: 'MFA & sécurité', icon: '🛡️', permission: 'core.manage_users' },
  { to: '/infrastructure', label: 'Infrastructure', icon: '🏥', permission: 'core.manage_users' },
  { to: '/appointments', label: 'Rendez-vous patients', icon: '📅', permission: 'hr.review_appointments' },
  { to: '/accounting', label: 'Comptabilité', icon: '📒', permission: 'billing.adjust' },
]

const nav = computed(() => NAV.filter((item) => auth.hasPerm(item.permission)))

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex min-h-screen bg-gradient-to-br from-slate-100 via-slate-50 to-violet-50/30">
    <div v-if="sidebarOpen" class="fixed inset-0 bg-slate-900/50 z-40 lg:hidden" @click="sidebarOpen = false" />

    <aside
      class="fixed lg:static inset-y-0 left-0 z-50 w-72 bg-slate-900 text-white flex flex-col shrink-0 transform transition-transform duration-200 lg:translate-x-0"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="p-6 border-b border-slate-700">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-admin flex items-center justify-center font-bold text-lg">A</div>
          <div>
            <p class="text-[10px] text-violet-300 uppercase tracking-[0.2em] font-semibold">Console</p>
            <h1 class="text-lg font-bold">SGHL Admin</h1>
          </div>
        </div>
      </div>

      <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          active-class="nav-link-active"
          @click="sidebarOpen = false"
        >
          <span class="text-lg w-6 text-center">{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </nav>

      <div class="p-4 border-t border-slate-700">
        <div class="rounded-2xl bg-slate-800/60 p-4">
          <p class="text-sm font-medium">{{ auth.user?.username }}</p>
          <p class="text-xs text-violet-300 mt-0.5">Administrateur</p>
          <button type="button" @click="logout" class="mt-3 text-sm text-red-400 hover:text-red-300">Déconnexion</button>
        </div>
      </div>
    </aside>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="lg:hidden sticky top-0 z-30 bg-white/90 backdrop-blur border-b px-4 py-3 flex items-center gap-3">
        <button type="button" class="btn-secondary !p-2.5" @click="sidebarOpen = true">☰</button>
        <span class="font-semibold">SGHL Admin</span>
      </header>
      <main class="flex-1 p-4 sm:p-6 lg:p-8 overflow-auto">
        <div class="page-shell">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>
