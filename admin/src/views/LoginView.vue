<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('admin')
const password = ref('Admin@SGHL2026')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e) {
    error.value = e.message || e.response?.data?.detail || 'Connexion échouée'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-violet-950 to-slate-900 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8 text-white">
        <div class="inline-flex w-16 h-16 rounded-3xl bg-admin items-center justify-center text-2xl font-bold shadow-2xl shadow-violet-500/30 mb-4">
          A
        </div>
        <p class="text-xs text-violet-300 uppercase tracking-[0.2em] font-semibold">SGHL Administration</p>
        <h1 class="text-3xl font-bold tracking-tight mt-2">Console admin</h1>
      </div>

      <form @submit.prevent="submit" class="card p-8 shadow-2xl shadow-black/20">
        <p v-if="error" class="alert-error mb-4">{{ error }}</p>
        <label class="block mb-4">
          <span class="form-label">Identifiant</span>
          <input v-model="username" class="form-input" autocomplete="username" required />
        </label>
        <label class="block mb-6">
          <span class="form-label">Mot de passe</span>
          <input v-model="password" type="password" class="form-input" autocomplete="current-password" required />
        </label>
        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? 'Connexion…' : 'Accéder à l\'admin' }}
        </button>
        <p class="text-xs text-slate-400 mt-6 text-center space-y-1">
          <span class="block">API : /api/v1/admin/</span>
          <a href="/" class="text-admin hover:underline">← Portail staff & patient</a>
        </p>
      </form>
    </div>
  </div>
</template>
