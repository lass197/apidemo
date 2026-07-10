<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import HospitalIcon from '../components/icons/HospitalIcon.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const sidebarOpen = ref(false)

const nav = [
  { to: '/patient', label: 'Accueil', icon: '🏠', exact: true },
  { to: '/patient/discover', label: "L'hôpital", icon: '🏥' },
  { to: '/patient/services', label: 'Services', icon: '📋' },
  { to: '/patient/doctors', label: 'Médecins', icon: '👨‍⚕️' },
  { to: '/patient/appointments', label: 'Rendez-vous', icon: '📅' },
  { to: '/patient/records', label: 'Mon dossier', icon: '📁' },
]

const pageTitle = computed(() => {
  const item = nav.find((n) => (n.exact ? route.path === n.to : route.path.startsWith(n.to)))
  return item?.label || 'Espace patient'
})

function isActive(item) {
  return item.exact ? route.path === item.to : route.path.startsWith(item.to)
}

function logout() {
  auth.logout()
  router.push('/')
}

function closeSidebar() {
  sidebarOpen.value = false
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-teal-50/30 flex">
    <!-- Overlay mobile -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-slate-900/40 z-40 lg:hidden"
      @click="closeSidebar"
    />

    <!-- Navigation verticale -->
    <aside
      class="fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col shrink-0 transform transition-transform duration-200 lg:translate-x-0"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="p-5 border-b border-slate-100">
        <div class="flex items-center gap-3">
          <HospitalIcon size="md" variant="solid" />
          <div class="min-w-0">
            <p class="text-[10px] text-teal-700 font-bold uppercase tracking-wider">SGHL · Dolisie (RC)</p>
            <p class="font-semibold text-slate-800 truncate text-sm">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</p>
          </div>
        </div>
      </div>

      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors"
          :class="isActive(item)
            ? 'bg-teal-50 text-teal-800 border border-teal-100'
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'"
          @click="closeSidebar"
        >
          <span class="text-lg w-6 text-center shrink-0">{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </nav>

      <div class="p-3 border-t border-slate-100">
        <button
          type="button"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-500 hover:bg-slate-50 hover:text-slate-800 transition-colors"
          @click="logout"
        >
          <span class="text-lg w-6 text-center">🚪</span>
          Déconnexion
        </button>
      </div>
    </aside>

    <!-- Contenu principal -->
    <div class="flex-1 flex flex-col min-w-0 min-h-screen">
      <header class="bg-white/90 backdrop-blur border-b border-slate-200 sticky top-0 z-30 lg:hidden">
        <div class="px-4 py-3 flex items-center justify-between gap-3">
          <button
            type="button"
            class="p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            aria-label="Menu"
            @click="sidebarOpen = true"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <p class="font-semibold text-slate-800 text-sm truncate">{{ pageTitle }}</p>
          <div class="w-10" />
        </div>
      </header>

      <header class="hidden lg:flex bg-white/60 border-b border-slate-100 px-8 py-4 items-center justify-between">
        <h1 class="text-lg font-semibold text-slate-800">{{ pageTitle }}</h1>
        <p class="text-sm text-slate-500">{{ auth.user?.email }}</p>
      </header>

      <main class="flex-1 w-full max-w-5xl px-4 sm:px-6 lg:px-8 py-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
