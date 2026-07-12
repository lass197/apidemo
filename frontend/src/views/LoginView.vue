<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AlertBanner from '../components/ui/AlertBanner.vue'
import FormField from '../components/ui/FormField.vue'
import { validators } from '../composables/useFormValidation'
import { patientLoginError } from '../composables/apiErrors'
import api from '../api/client'

const props = defineProps({
  portal: { type: String, default: 'staff' },
})

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref(props.portal === 'patient' ? '' : 'sec.dupont')
const password = ref(props.portal === 'patient' ? '' : 'Secretaire@2026')
const loginOtp = ref('')
const challengeId = ref('')
const otpDevCode = ref('')
const step = ref(1)
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
  if (isPatient.value && step.value === 1 && !validateLoginFields()) {
    error.value = 'Corrigez le champ signalé ci-dessous.'
    return
  }
  if (isPatient.value && step.value === 2 && !/^\d{6}$/.test(loginOtp.value.trim())) {
    error.value = 'Saisissez le code à 6 chiffres affiché ci-dessus.'
    return
  }

  loading.value = true
  try {
    if (isPatient.value) {
      const loginId = username.value.trim().toLowerCase()
      const payload = { username: loginId, password: password.value }
      if (step.value === 2) {
        payload.login_otp = loginOtp.value.trim()
        payload.challenge_id = challengeId.value
      }
      const { data } = await api.post('/auth/login/', payload)

      if (data.requires_otp) {
        challengeId.value = data.challenge_id
        otpDevCode.value = data.otp_dev_code || ''
        loginOtp.value = data.otp_dev_code || ''
        step.value = 2
        return
      }

      if (!data.user?.roles?.includes('PATIENT')) {
        throw new Error('Espace réservé aux patients.')
      }
      auth.setSession(data, 'patient')
      const redirect = route.query.redirect
      router.push(typeof redirect === 'string' ? redirect : '/patient')
    } else {
      await auth.login(username.value, password.value, 'staff')
      const redirect = route.query.redirect
      router.push(typeof redirect === 'string' ? redirect : '/dashboard')
    }
  } catch (e) {
    if (isPatient.value) {
      if (e.response?.status === 502 || e.code === 'ERR_NETWORK') {
        error.value = 'Serveur indisponible. Attendez une minute puis réessayez.'
      } else {
        const { message, hint } = patientLoginError(e)
        error.value = message
        loginHint.value = hint
      }
    } else {
      error.value = e.message || e.response?.data?.detail || 'Connexion échouée'
    }
  } finally {
    loading.value = false
  }
}

function backToCredentials() {
  step.value = 1
  loginOtp.value = ''
  challengeId.value = ''
  otpDevCode.value = ''
  error.value = ''
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
        <h1 class="text-3xl font-bold tracking-tight">
          {{ isPatient ? (step === 2 ? 'Confirmation' : 'Espace patient') : 'Personnel hospitalier' }}
        </h1>
        <p class="mt-2 opacity-80">
          {{ isPatient
            ? (step === 2 ? 'Validez le code affiché pour entrer' : 'Rendez-vous, résultats, soins')
            : 'Connexion staff SGHL' }}
        </p>
      </div>

      <form @submit.prevent="submit" class="card p-8 shadow-2xl shadow-black/20">
        <AlertBanner v-if="otpDevCode && isPatient && step === 2" type="success" class="mb-4" title="Code de connexion">
          <p class="text-center font-mono text-3xl tracking-[0.35em] font-bold mt-1">{{ otpDevCode }}</p>
          <p class="text-xs mt-2 opacity-80">Ce code n’est pas envoyé par email — saisissez-le ci-dessous.</p>
        </AlertBanner>

        <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
        <p v-if="loginHint === 'register'" class="text-sm text-slate-600 mb-4 -mt-2">
          <router-link to="/patient/register" class="text-primary font-medium hover:underline">Créer un compte patient</router-link>
        </p>

        <template v-if="!isPatient || step === 1">
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
        </template>

        <template v-else>
          <FormField label="Code à 6 chiffres" required class="mb-6">
            <input
              v-model="loginOtp"
              class="form-input text-center text-2xl tracking-[0.5em] font-mono"
              maxlength="6"
              inputmode="numeric"
              pattern="[0-9]*"
              placeholder="000000"
              autocomplete="one-time-code"
              required
            />
          </FormField>
        </template>

        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? 'Patientez…' : (isPatient && step === 2 ? 'Confirmer la connexion' : 'Se connecter') }}
        </button>
        <button
          v-if="isPatient && step === 2"
          type="button"
          class="btn-secondary w-full text-sm mt-3"
          @click="backToCredentials"
        >
          ← Modifier email / mot de passe
        </button>

        <div class="mt-6 pt-4 border-t border-slate-100 text-center text-xs text-slate-400 space-y-2">
          <p v-if="isPatient">
            Pas encore de compte ?
            <router-link to="/patient/register" class="text-primary font-medium hover:underline">Créer un compte</router-link>
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
