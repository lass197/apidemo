<script setup>
import { ref } from 'vue'
import api from '../api/mainClient'
import PageHeader from '../components/PageHeader.vue'

const step = ref('idle')
const qrUri = ref('')
const confirmCode = ref('')
const message = ref('')
const error = ref('')

async function setupMfa() {
  error.value = ''
  message.value = ''
  try {
    const { data } = await api.post('/auth/mfa/setup/')
    qrUri.value = data.provisioning_uri
    step.value = 'confirm'
    message.value = 'Scannez le QR code avec Google Authenticator ou entrez le secret manuellement.'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur configuration MFA'
  }
}

async function confirmMfa() {
  error.value = ''
  try {
    await api.post('/auth/mfa/confirm/', { code: confirmCode.value })
    message.value = 'MFA activé avec succès sur votre compte administrateur.'
    step.value = 'done'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Code invalide'
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="MFA & sécurité"
      subtitle="Authentification à deux facteurs (TOTP) pour les comptes administrateurs"
    />

    <p v-if="error" class="alert-error mb-4">{{ error }}</p>
    <p v-if="message" class="alert-success mb-4">{{ message }}</p>

    <div class="card card-body max-w-xl">
      <h3 class="font-semibold text-lg mb-2">Configuration TOTP</h3>
      <p class="text-sm text-slate-600 mb-6">
        Activez le MFA pour renforcer la sécurité de la console d'administration.
        Compatible avec Google Authenticator, Authy et applications TOTP standard.
      </p>

      <button v-if="step === 'idle'" type="button" class="btn-primary" @click="setupMfa">
        Démarrer la configuration MFA
      </button>

      <div v-if="step === 'confirm'" class="space-y-4">
        <p class="text-xs font-mono break-all bg-slate-50 p-3 rounded-xl border">{{ qrUri }}</p>
        <label class="block">
          <span class="form-label">Code à 6 chiffres</span>
          <input v-model="confirmCode" class="form-input" maxlength="6" inputmode="numeric" placeholder="000000" />
        </label>
        <button type="button" class="btn-primary" @click="confirmMfa">Confirmer et activer</button>
      </div>

      <p v-if="step === 'done'" class="text-emerald-700 font-medium">✓ MFA opérationnel</p>
    </div>
  </div>
</template>
