<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(() => {
  if (auth.isAuthenticated) {
    if (auth.isPatient) router.replace('/patient')
    else if (auth.isStaff) router.replace('/dashboard')
  }
})

const portals = [
  {
    title: 'Personnel hospitalier',
    desc: 'Médecins, infirmiers, secrétaires, biologistes, pharmaciens',
    icon: '🏥',
    color: 'from-teal-600 to-teal-800',
    to: '/login',
    accounts: 'sec.dupont · dr.martin · inf.bernard',
  },
  {
    title: 'Espace patient',
    desc: 'Découvrez l\'hôpital, réservez en ligne, suivez votre dossier — vérification email OTP',
    icon: '👤',
    color: 'from-slate-600 to-slate-800',
    to: '/patient/register',
    accounts: 'Connexion démo : alice.moreau@email.local',
  },
  {
    title: 'Administration',
    desc: 'Utilisateurs, RBAC, audit, infrastructure, comptabilité',
    icon: '🛡️',
    color: 'from-violet-600 to-violet-900',
    to: '/admin/',
    external: true,
    accounts: 'admin / Admin@SGHL2026',
  },
]
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-teal-50/30 to-slate-100">
    <header class="max-w-5xl mx-auto px-6 pt-12 pb-8 text-center">
      <div class="inline-flex w-20 h-20 rounded-3xl bg-primary items-center justify-center text-3xl font-bold text-white shadow-xl shadow-primary/30 mb-6">
        S
      </div>
      <h1 class="text-4xl font-bold text-slate-900 tracking-tight">SGHL</h1>
      <p class="text-lg text-slate-600 mt-3 max-w-xl mx-auto">
        Système de Gestion Hospitalière et Laboratoire — choisissez votre espace de connexion
      </p>
    </header>

    <main class="max-w-5xl mx-auto px-6 pb-16">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <component
          :is="p.external ? 'a' : 'router-link'"
          v-for="p in portals"
          :key="p.title"
          :href="p.external ? p.to : undefined"
          :to="p.external ? undefined : p.to"
          class="card overflow-hidden hover:shadow-xl transition-all duration-200 hover:-translate-y-1 group"
        >
          <div class="h-2 bg-gradient-to-r" :class="p.color" />
          <div class="p-6">
            <span class="text-4xl">{{ p.icon }}</span>
            <h2 class="text-xl font-bold mt-4 group-hover:text-primary transition">{{ p.title }}</h2>
            <p class="text-sm text-slate-500 mt-2">{{ p.desc }}</p>
            <p class="text-xs text-slate-400 mt-4 font-mono bg-slate-50 rounded-lg px-3 py-2">{{ p.accounts }}</p>
            <span class="inline-block mt-4 text-sm font-medium text-primary">Accéder →</span>
          </div>
        </component>
      </div>

      <div class="mt-12 card card-body text-center text-sm text-slate-500">
        <p><strong class="text-slate-700">Application mobile</strong> — Patient &amp; médecin (Flutter) dans <code class="text-xs bg-slate-100 px-1 rounded">mobile/</code> — Chrome ou téléphone</p>
        <p class="mt-2">API documentée sur <code class="text-xs bg-slate-100 px-1 rounded">/api/v1/docs</code></p>
      </div>
    </main>
  </div>
</template>
