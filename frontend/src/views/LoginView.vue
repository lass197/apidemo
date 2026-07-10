<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AlertBanner from '../components/ui/AlertBanner.vue'
import FormField from '../components/ui/FormField.vue'
import { validators } from '../composables/useFormValidation'
import { patientLoginError } from '../composables/apiErrors'

const props = defineProps({
  portal: { type: String, default: 'staff' },
})

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref(props.portal === 'patient' ? '' : 'sec.dupont')
const password = ref(props.portal === 'patient' ? '' : 'Secretaire@2026')
const error = ref('')
const loginHint = ref(null)
const fieldErrors = ref({})
const loading = ref(false)

const isPatient = computed(() => props.portal === 'patient')

function validateLoginFields() {
  if (!isPatient.value) return true
  const idErr = validators.loginIdentifier(username.value, true)
  fieldErrors.value = idErr ? { username: idErr } : {}
  return !idErr
}

function onIdentifierBlur() {
  if (!isPatient.value) return
  const msg = validators.loginIdentifier(username.value, true)
  fieldErrors.value = msg ? { username: msg } : {}
}

async function submit() {
  error.value = ''
  loginHint.value = null
  if (isPatient.value && !validateLoginFields()) {
    error.value = 'Corrigez le champ signalé ci-dessous.'
    return
  }
  loading.value = true
  try {
    const loginId = isPatient.value ? username.value.trim().toLowerCase() : username.value
    await auth.login(loginId, password.value, props.portal)
    const redirect = route.query.redirect
    if (props.portal === 'patient') {
      router.push(typeof redirect === 'string' ? redirect : '/patient')
    } else {
      router.push(typeof redirect === 'string' ? redirect : '/dashboard')
    }
  } catch (e) {
    if (isPatient.value) {
      const { message, hint } = patientLoginError(e)
      error.value = message
      loginHint.value = hint
      if (hint === 'password' || message.toLowerCase().includes('email')) {
        fieldErrors.value = { username: message.includes('mot de passe') ? '' : message }
        if (message.includes('mot de passe')) fieldErrors.value.password = message
      }
    } else {
      error.value = e.message || e.response?.data?.detail || 'Connexion échouée'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center p-4"
    :class="isPatient ? 'bg-gradient-to-br from-slate-800 to-slate-950' : 'bg-gradient-to-br from-teal-950 via-slate-900 to-slate-950'"
  >
    <div class="w-full max-w-md">
      <div class="text-center mb-8 text-white">
        <router-link to="/" class="inline-block text-xs text-white/50 hover:text-white/80 mb-4">← Accueil SGHL</router-link>
        <div
          class="inline-flex w-16 h-16 rounded-3xl items-center justify-center text-2xl font-bold shadow-2xl mb-4"
          :class="isPatient ? 'bg-slate-600 shadow-slate-900/40' : 'bg-primary shadow-primary/40'"
        >S</div>
        <h1 class="text-3xl font-bold tracking-tight">{{ isPatient ? 'Espace patient' : 'Personnel hospitalier' }}</h1>
        <p class="mt-2 opacity-80">{{ isPatient ? 'Rendez-vous, résultats, soins' : 'Connexion staff SGHL' }}</p>
      </div>

      <form @submit.prevent="submit" class="card p-8 shadow-2xl shadow-black/20">
        <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
        <p v-if="loginHint === 'register'" class="text-sm text-slate-600 mb-4 -mt-2">
          <router-link to="/patient/register" class="text-primary font-medium hover:underline">Créer un compte patient</router-link>
        </p>
        <p v-else-if="loginHint === 'verify'" class="text-sm text-slate-600 mb-4 -mt-2">
          <router-link to="/patient/verify" class="text-primary font-medium hover:underline">Activer mon compte avec le code email</router-link>
        </p>

        <FormField
          :label="isPatient ? 'Email' : 'Identifiant'"
          :error="fieldErrors.username"
          :required="isPatient"
          :hint="isPatient ? 'L\'adresse utilisée à l\'inscription' : undefined"
          class="mb-4"
        >
          <input
            v-model="username"
            :type="isPatient ? 'email' : 'text'"
            class="form-input"
            :autocomplete="isPatient ? 'email' : 'username'"
            :placeholder="isPatient ? 'votre.email@exemple.com' : ''"
            required
            @blur="onIdentifierBlur"
          />
        </FormField>
        <FormField label="Mot de passe" :error="fieldErrors.password" required class="mb-6">
          <input v-model="password" type="password" class="form-input" autocomplete="current-password" required />
        </FormField>
        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? 'Connexion…' : 'Se connecter' }}
        </button>

        <div class="mt-6 pt-4 border-t border-slate-100 text-center text-xs text-slate-400 space-y-2">
          <p v-if="isPatient">
            Pas encore de compte ?
            <router-link to="/patient/register" class="text-primary font-medium hover:underline">Créer un compte</router-link>
            ·
            <router-link to="/patient/verify" class="text-primary font-medium hover:underline">Code reçu ?</router-link>
            · Personnel → <router-link to="/login" class="text-primary font-medium hover:underline">Staff</router-link>
          </p>
          <p v-else>
            Patient → <router-link to="/patient/login" class="text-primary font-medium hover:underline">Espace patient</router-link>
            · Admin → <a href="/admin/" class="text-primary font-medium hover:underline">Console admin</a>
          </p>
        </div>
      </form>
    </div>
  </div>
</template>
