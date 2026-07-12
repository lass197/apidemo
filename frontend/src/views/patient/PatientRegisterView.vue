<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import FormField from '../../components/ui/FormField.vue'
import PhoneInput from '../../components/ui/PhoneInput.vue'
import api from '../../api/client'
import {
  validators,
  blockDigitsInName,
  sanitizeNamePaste,
  validateFields,
  hasErrors,
} from '../../composables/useFormValidation'
import { apiErrorDetail, mapApiErrorToFields } from '../../composables/apiErrors'

const auth = useAuthStore()
const router = useRouter()
const step = ref(1)
const loading = ref(false)
const error = ref('')
const fieldErrors = ref({})
const pendingEmail = ref('')
const otpDevCode = ref('')
const otpSent = ref(false)

const form = ref({
  email: '',
  password: '',
  passwordConfirm: '',
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: 'F',
  phone: '',
  username: '',
  otpCode: '',
})

function onNamePaste(field, event) {
  sanitizeNamePaste(event, (text) => { form.value[field] = text })
}

function stripDigitsFromName(field) {
  form.value[field] = form.value[field].replace(/\d/g, '')
}

function validateEmailField() {
  const msg = validators.email(form.value.email, true)
  if (msg) fieldErrors.value = { ...fieldErrors.value, email: msg }
  else {
    const { email, ...rest } = fieldErrors.value
    fieldErrors.value = rest
  }
  return !msg
}

function validatePhoneField() {
  const msg = validators.phoneInternational(form.value.phone, true)
  if (msg) fieldErrors.value = { ...fieldErrors.value, phone: msg }
  else {
    const { phone, ...rest } = fieldErrors.value
    fieldErrors.value = rest
  }
  return !msg
}

function validateStep1() {
  fieldErrors.value = validateFields({
    first_name: () => validators.personName(form.value.first_name, 'Prénom'),
    last_name: () => validators.personName(form.value.last_name, 'Nom'),
    email: () => validators.email(form.value.email, true),
    date_of_birth: () => validators.dateOfBirth(form.value.date_of_birth),
    phone: () => validators.phoneInternational(form.value.phone, true),
    password: () => validators.password(form.value.password),
    passwordConfirm: () =>
      form.value.password !== form.value.passwordConfirm ? 'Les mots de passe ne correspondent pas.' : '',
    username: () => (form.value.username.trim() ? validators.username(form.value.username) : ''),
  })
  return !hasErrors(fieldErrors.value)
}

async function submitRegister() {
  error.value = ''
  if (!validateStep1()) {
    error.value = 'Corrigez les champs signalés ci-dessous.'
    return
  }
  loading.value = true
  try {
    const payload = {
      email: form.value.email.trim().toLowerCase(),
      password: form.value.password,
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim(),
      date_of_birth: form.value.date_of_birth,
      gender: form.value.gender,
      phone: form.value.phone.trim(),
    }
    if (form.value.username.trim()) payload.username = form.value.username.trim().toLowerCase()

    const { data } = await api.post('/auth/register/patient/', payload)
    pendingEmail.value = data.email
    otpSent.value = !!data.otp_sent
    otpDevCode.value = data.otp_dev_code || ''
    if (otpDevCode.value) form.value.otpCode = otpDevCode.value
    step.value = 2
  } catch (e) {
    const detail = apiErrorDetail(e, 'Inscription impossible.')
    if (e.response?.status === 502 || e.code === 'ERR_NETWORK') {
      error.value = 'Serveur indisponible (502). Attendez une minute (démarrage Render) puis réessayez.'
    } else {
      fieldErrors.value = { ...fieldErrors.value, ...mapApiErrorToFields(detail) }
      error.value = Object.keys(mapApiErrorToFields(detail)).length ? 'Corrigez les champs signalés ci-dessous.' : detail
    }
  } finally {
    loading.value = false
  }
}

async function verifyOtp() {
  error.value = ''
  if (!/^\d{6}$/.test(form.value.otpCode.trim())) {
    error.value = 'Saisissez le code à 6 chiffres reçu par email.'
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/auth/register/patient/verify-otp/', {
      email: pendingEmail.value,
      code: form.value.otpCode.trim(),
      password: form.value.password,
    })
    auth.setSession(data, 'patient')
    router.push('/patient')
  } catch (e) {
    const detail = apiErrorDetail(e, 'Code invalide.')
    if (detail.toLowerCase().includes('email')) {
      fieldErrors.value = { ...fieldErrors.value, email: detail }
    }
    error.value = detail
  } finally {
    loading.value = false
  }
}

async function resendOtp() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await api.post('/auth/register/patient/resend-otp/', { email: pendingEmail.value })
    otpSent.value = !!data.otp_sent
    otpDevCode.value = data.otp_dev_code || ''
    if (otpDevCode.value) form.value.otpCode = otpDevCode.value
    error.value = ''
    alert(data.detail || (otpDevCode.value ? `Nouveau code : ${otpDevCode.value}` : 'Un nouveau code a été envoyé.'))
  } catch (e) {
    error.value = apiErrorDetail(e, 'Renvoi impossible.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-950 p-4">
    <div class="w-full max-w-lg">
      <div class="text-center mb-6 text-white">
        <router-link to="/" class="text-xs text-white/50 hover:text-white/80">← Accueil SGHL</router-link>
        <h1 class="text-2xl font-bold mt-4">{{ step === 1 ? 'Créer un compte patient' : 'Vérification email' }}</h1>
        <p class="text-sm text-white/70 mt-1">
          {{ step === 1 ? 'Email unique — accès rendez-vous, résultats et plan de soins' : `Code envoyé à ${pendingEmail}` }}
        </p>
      </div>

      <form v-if="step === 1" @submit.prevent="submitRegister" class="card p-6 sm:p-8 shadow-2xl space-y-4">
        <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Prénom" :error="fieldErrors.first_name" required>
            <input v-model="form.first_name" class="form-input" @keydown="blockDigitsInName" @input="stripDigitsFromName('first_name')" @paste="onNamePaste('first_name', $event)" />
          </FormField>
          <FormField label="Nom" :error="fieldErrors.last_name" required>
            <input v-model="form.last_name" class="form-input" @keydown="blockDigitsInName" @input="stripDigitsFromName('last_name')" @paste="onNamePaste('last_name', $event)" />
          </FormField>
        </div>
        <FormField label="Email" :error="fieldErrors.email" required hint="Utilisé pour la connexion et le code de vérification">
          <input
            v-model="form.email"
            type="email"
            class="form-input"
            autocomplete="email"
            placeholder="exemple@email.com"
            @blur="validateEmailField"
          />
        </FormField>
        <FormField label="Identifiant" :error="fieldErrors.username" hint="Optionnel — sinon généré depuis l'email">
          <input v-model="form.username" class="form-input" placeholder="lettres et chiffres uniquement" />
        </FormField>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Date de naissance" :error="fieldErrors.date_of_birth" required>
            <input v-model="form.date_of_birth" type="date" class="form-input" />
          </FormField>
          <FormField label="Genre" required>
            <select v-model="form.gender" class="form-select">
              <option value="F">Féminin</option>
              <option value="M">Masculin</option>
              <option value="O">Autre</option>
            </select>
          </FormField>
        </div>
        <FormField label="Téléphone mobile" :error="fieldErrors.phone" required>
          <PhoneInput v-model="form.phone" :error="fieldErrors.phone" required @blur="validatePhoneField" />
        </FormField>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Mot de passe" :error="fieldErrors.password" hint="Minimum 10 caractères" required>
            <input v-model="form.password" type="password" class="form-input" autocomplete="new-password" />
          </FormField>
          <FormField label="Confirmer" :error="fieldErrors.passwordConfirm" required>
            <input v-model="form.passwordConfirm" type="password" class="form-input" autocomplete="new-password" />
          </FormField>
        </div>
        <button type="submit" :disabled="loading" class="btn-primary w-full">{{ loading ? 'Création…' : 'Continuer' }}</button>
        <p class="text-center text-sm text-slate-500">
          Déjà inscrit ?
          <router-link to="/patient/login" class="text-primary font-medium hover:underline">Se connecter</router-link>
          ·
          <router-link to="/patient/verify" class="text-primary font-medium hover:underline">Code déjà reçu ?</router-link>
        </p>
      </form>

      <form v-else @submit.prevent="verifyOtp" class="card p-6 sm:p-8 shadow-2xl space-y-4">
        <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>
        <AlertBanner v-if="otpDevCode" type="success">
          Mode démo : aucun email SMTP configuré. Votre code est
          <strong class="font-mono text-lg tracking-widest">{{ otpDevCode }}</strong>
        </AlertBanner>
        <div class="text-center py-2">
          <span class="text-4xl">📧</span>
          <p class="text-sm text-slate-600 mt-3">
            <template v-if="otpSent">
              Entrez le code à <strong>6 chiffres</strong> reçu par email pour activer votre compte.
            </template>
            <template v-else>
              Entrez le code à <strong>6 chiffres</strong> affiché ci-dessus pour activer votre compte.
            </template>
          </p>
        </div>
        <FormField label="Code de vérification" required>
          <input
            v-model="form.otpCode"
            class="form-input text-center text-2xl tracking-[0.5em] font-mono"
            maxlength="6"
            inputmode="numeric"
            pattern="[0-9]*"
            placeholder="000000"
            autocomplete="one-time-code"
          />
        </FormField>
        <button type="submit" :disabled="loading" class="btn-primary w-full">{{ loading ? 'Vérification…' : 'Activer mon compte' }}</button>
        <button type="button" class="btn-secondary w-full text-sm" :disabled="loading" @click="resendOtp">Renvoyer le code</button>
        <button type="button" class="text-sm text-slate-500 hover:text-slate-700 w-full" @click="step = 1">← Modifier mes informations</button>
      </form>
    </div>
  </div>
</template>
