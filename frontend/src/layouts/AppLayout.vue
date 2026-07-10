<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePermissions } from '../composables/usePermissions'

const auth = useAuthStore()
const router = useRouter()
const { mainNav } = usePermissions()
const sidebarOpen = ref(false)

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex min-h-screen bg-gradient-to-br from-slate-100 via-slate-50 to-teal-50/30">
    <!-- Mobile overlay -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-slate-900/50 z-40 lg:hidden"
      @click="sidebarOpen = false"
    />

    <aside
      class="fixed lg:static inset-y-0 left-0 z-50 w-72 bg-hospital-900 text-white flex flex-col shrink-0 transform transition-transform duration-200 lg:translate-x-0"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="p-6 border-b border-teal-800/60">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-primary flex items-center justify-center font-bold text-lg shadow-lg shadow-primary/30">
            S
          </div>
          <div>
            <p class="text-[10px] text-teal-300 uppercase tracking-[0.2em] font-semibold">Personnel</p>
            <h1 class="text-lg font-bold leading-tight">SGHL Hospital</h1>
          </div>
        </div>
      </div>

      <nav class="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Navigation principale">
        <router-link
          v-for="item in mainNav"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          active-class="nav-link-active"
          @click="sidebarOpen = false"
        >
          <span class="text-lg w-6 text-center" aria-hidden="true">{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </nav>

      <div class="p-4 border-t border-teal-800/60">
        <div class="rounded-2xl bg-teal-950/40 p-4">
          <p class="text-sm font-medium">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</p>
          <p class="text-xs text-teal-300 mt-0.5">{{ auth.roles.join(' · ') }}</p>
          <button
            type="button"
            @click="logout"
            class="mt-3 w-full btn-ghost !text-red-300 hover:!bg-red-950/40 !justify-start !px-2"
          >
            Déconnexion
          </button>
        </div>
      </div>
    </aside>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="lg:hidden sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-slate-200 px-4 py-3 flex items-center gap-3">
        <button
          type="button"
          class="btn-secondary !p-2.5"
          aria-label="Ouvrir le menu"
          @click="sidebarOpen = true"
        >
          ☰
        </button>
        <span class="font-semibold text-slate-800">SGHL</span>
      </header>

      <main class="flex-1 p-4 sm:p-6 lg:p-8 overflow-auto">
        <div class="page-shell">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>
