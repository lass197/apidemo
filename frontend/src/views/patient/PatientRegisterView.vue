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
const loading = ref(false)
const error = ref('')
const fieldErrors = ref({})

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

function validateForm() {
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
  if (!validateForm()) {
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
    auth.setSession(data, 'patient')
    router.push('/patient')
  } catch (e) {
    if (e.response?.status === 502 || e.code === 'ERR_NETWORK') {
      error.value = 'Serveur indisponible (502). Attendez une minute puis réessayez.'
    } else {
      const detail = apiErrorDetail(e, 'Inscription impossible.')
      fieldErrors.value = { ...fieldErrors.value, ...mapApiErrorToFields(detail) }
      error.value = Object.keys(mapApiErrorToFields(detail)).length
        ? 'Corrigez les champs signalés ci-dessous.'
        : detail
    }
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
        <h1 class="text-2xl font-bold mt-4">Créer un compte patient</h1>
        <p class="text-sm text-white/70 mt-1">Accès immédiat à vos rendez-vous, résultats et soins</p>
      </div>

      <form @submit.prevent="submitRegister" class="card p-6 sm:p-8 shadow-2xl space-y-4">
        <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Prénom" :error="fieldErrors.first_name" required>
            <input v-model="form.first_name" class="form-input" @keydown="blockDigitsInName" @input="stripDigitsFromName('first_name')" @paste="onNamePaste('first_name', $event)" />
          </FormField>
          <FormField label="Nom" :error="fieldErrors.last_name" required>
            <input v-model="form.last_name" class="form-input" @keydown="blockDigitsInName" @input="stripDigitsFromName('last_name')" @paste="onNamePaste('last_name', $event)" />
          </FormField>
        </div>
        <FormField label="Email" :error="fieldErrors.email" required hint="Utilisé pour la connexion">
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
        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? 'Création…' : 'Créer mon compte' }}
        </button>
        <p class="text-center text-sm text-slate-500">
          Déjà inscrit ?
          <router-link to="/patient/login" class="text-primary font-medium hover:underline">Se connecter</router-link>
        </p>
      </form>
    </div>
  </div>
</template>
