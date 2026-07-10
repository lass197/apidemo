<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import FormField from '../../components/ui/FormField.vue'
import api from '../../api/client'
import { validators } from '../../composables/useFormValidation'
import { apiErrorDetail, mapApiErrorToFields } from '../../composables/apiErrors'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const success = ref('')
const fieldErrors = ref({})
const email = ref('')
const otpCode = ref('')
const password = ref('')

function validateEmailField() {
  const msg = validators.email(email.value, true)
  fieldErrors.value = msg ? { email: msg } : {}
  return !msg
}

async function resend() {
  error.value = ''
  success.value = ''
  if (!validateEmailField()) {
    error.value = 'Corrigez l\'email ci-dessous.'
    return
  }
  loading.value = true
  try {
    await api.post('/auth/register/patient/resend-otp/', { email: email.value.trim().toLowerCase() })
    success.value = 'Un nouveau code a été envoyé. Vérifiez votre boîte mail (et les spams).'
  } catch (e) {
    const detail = apiErrorDetail(e, 'Envoi impossible.')
    fieldErrors.value = { ...fieldErrors.value, ...mapApiErrorToFields(detail) }
    error.value = fieldErrors.value.email || detail
  } finally {
    loading.value = false
  }
}

async function verify() {
  error.value = ''
  success.value = ''
  if (!validateEmailField()) {
    error.value = 'Corrigez l\'email ci-dessous.'
    return
  }
  if (!/^\d{6}$/.test(otpCode.value.trim())) {
    error.value = 'Code à 6 chiffres requis.'
    return
  }
  if (!password.value || password.value.length < 10) {
    fieldErrors.value = { ...fieldErrors.value, password: 'Mot de passe : minimum 10 caractères.' }
    error.value = 'Corrigez les champs signalés.'
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/auth/register/patient/verify-otp/', {
      email: email.value.trim().toLowerCase(),
      code: otpCode.value.trim(),
      password: password.value,
    })
    auth.setSession(data, 'patient')
    router.push('/patient')
  } catch (e) {
    const detail = apiErrorDetail(e, 'Vérification impossible.')
    fieldErrors.value = { ...fieldErrors.value, ...mapApiErrorToFields(detail) }
    error.value = Object.keys(mapApiErrorToFields(detail)).length ? 'Corrigez les champs signalés.' : detail
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-950 p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-6 text-white">
        <router-link to="/patient/register" class="text-xs text-white/50 hover:text-white/80">← Inscription</router-link>
        <h1 class="text-2xl font-bold mt-4">Activer mon compte</h1>
        <p class="text-sm text-white/70 mt-1">Saisissez le code reçu par email</p>
      </div>

      <form @submit.prevent="verify" class="card p-6 sm:p-8 shadow-2xl space-y-4">
        <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>
        <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>

        <FormField label="Email" :error="fieldErrors.email" required hint="Même adresse qu'à l'inscription">
          <input
            v-model="email"
            type="email"
            class="form-input"
            autocomplete="email"
            placeholder="exemple@email.com"
            @blur="validateEmailField"
          />
        </FormField>
        <FormField label="Mot de passe (celui choisi à l'inscription)" :error="fieldErrors.password" required>
          <input v-model="password" type="password" class="form-input" autocomplete="current-password" />
        </FormField>
        <FormField label="Code à 6 chiffres" required>
          <input
            v-model="otpCode"
            class="form-input text-center text-2xl tracking-[0.5em] font-mono"
            maxlength="6"
            inputmode="numeric"
            pattern="[0-9]*"
            placeholder="000000"
            autocomplete="one-time-code"
          />
        </FormField>

        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? 'Vérification…' : 'Activer mon compte' }}
        </button>
        <button type="button" class="btn-secondary w-full text-sm" :disabled="loading" @click="resend">
          Renvoyer le code
        </button>
      </form>
    </div>
  </div>
</template>
