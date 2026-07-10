<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import Modal from '../components/Modal.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import FormField from '../components/ui/FormField.vue'
import {
  validators,
  blockDigitsInName,
  sanitizeNamePaste,
  validateFields,
  hasErrors,
} from '../composables/useFormValidation'

const patients = ref([])
const error = ref('')
const success = ref('')
const loading = ref(true)
const showForm = ref(false)
const showEdit = ref(false)
const editing = ref(null)
const fieldErrors = ref({})

const emptyForm = () => ({
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: 'F',
  phone: '',
  email: '',
})

const form = ref(emptyForm())

const headers = [
  { key: 'name', label: 'Nom complet' },
  { key: 'date_of_birth', label: 'Naissance' },
  { key: 'gender_display', label: 'Genre' },
  { key: 'phone', label: 'Téléphone' },
  { key: 'email', label: 'Email' },
]

const genderLabel = { M: 'Masculin', F: 'Féminin', O: 'Autre' }

function validatePatientForm() {
  fieldErrors.value = validateFields({
    first_name: () => validators.personName(form.value.first_name, 'Prénom'),
    last_name: () => validators.personName(form.value.last_name, 'Nom'),
    date_of_birth: () => validators.dateOfBirth(form.value.date_of_birth),
    phone: () => validators.phone(form.value.phone),
    email: () => validators.email(form.value.email),
  })
  return !hasErrors(fieldErrors.value)
}

function onNamePaste(field, event) {
  sanitizeNamePaste(event, (text) => {
    form.value[field] = text
  })
}

function stripDigitsFromName(field) {
  form.value[field] = form.value[field].replace(/\d/g, '')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/clinical/patients/')
    patients.value = data.map((p) => ({
      ...p,
      name: `${p.last_name} ${p.first_name}`,
      gender_display: genderLabel[p.gender] || p.gender,
    }))
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = emptyForm()
  fieldErrors.value = {}
  error.value = ''
  success.value = ''
  showForm.value = true
  showEdit.value = false
}

function cancelCreate() {
  showForm.value = false
  form.value = emptyForm()
  fieldErrors.value = {}
}

function openEdit(row) {
  editing.value = row
  form.value = {
    first_name: row.first_name,
    last_name: row.last_name,
    date_of_birth: row.date_of_birth,
    gender: row.gender,
    phone: row.phone || '',
    email: row.email || '',
  }
  fieldErrors.value = {}
  error.value = ''
  showEdit.value = true
}

async function create() {
  error.value = ''
  success.value = ''
  if (!validatePatientForm()) return
  try {
    await api.post('/clinical/patients/', form.value)
    showForm.value = false
    form.value = emptyForm()
    success.value = 'Patient enregistré avec succès.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Création échouée.'
  }
}

async function saveEdit() {
  error.value = ''
  success.value = ''
  if (!validatePatientForm() || !editing.value) return
  try {
    const payload = { ...form.value }
    if (!payload.email) payload.email = ''
    await api.patch(`/clinical/patients/${editing.value.id}/`, payload)
    showEdit.value = false
    editing.value = null
    success.value = 'Dossier patient mis à jour.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Modification échouée.'
  }
}

async function archive(row) {
  const name = `${row.last_name || ''} ${row.first_name || ''}`.trim() || row.name
  if (!window.confirm(`Archiver le dossier de ${name} ?`)) return
  error.value = ''
  success.value = ''
  try {
    await api.delete(`/clinical/patients/${row.id}/`)
    success.value = 'Dossier patient archivé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Archivage impossible.'
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Patients" subtitle="Dossiers administratifs — création, modification et archivage">
      <template #actions>
        <button type="button" class="btn-primary" @click="openCreate">
          + Nouveau patient
        </button>
      </template>
    </PageHeader>

    <AlertBanner v-if="error" type="error" class="mb-4">{{ error }}</AlertBanner>
    <AlertBanner v-if="success" type="success" class="mb-4">{{ success }}</AlertBanner>

    <form v-if="showForm" @submit.prevent="create" class="card card-body mb-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
      <FormField label="Prénom" :error="fieldErrors.first_name" required>
        <input
          v-model="form.first_name"
          class="form-input"
          :class="{ 'ring-red-300 border-red-300': fieldErrors.first_name }"
          autocomplete="given-name"
          @keydown="blockDigitsInName"
          @input="stripDigitsFromName('first_name')"
          @paste="onNamePaste('first_name', $event)"
        />
      </FormField>
      <FormField label="Nom" :error="fieldErrors.last_name" required>
        <input
          v-model="form.last_name"
          class="form-input"
          :class="{ 'ring-red-300 border-red-300': fieldErrors.last_name }"
          autocomplete="family-name"
          @keydown="blockDigitsInName"
          @input="stripDigitsFromName('last_name')"
          @paste="onNamePaste('last_name', $event)"
        />
      </FormField>
      <FormField label="Date de naissance" :error="fieldErrors.date_of_birth" required>
        <input v-model="form.date_of_birth" type="date" class="form-input" :class="{ 'ring-red-300 border-red-300': fieldErrors.date_of_birth }" />
      </FormField>
      <FormField label="Genre" required>
        <select v-model="form.gender" class="form-select">
          <option value="F">Féminin</option>
          <option value="M">Masculin</option>
          <option value="O">Autre</option>
        </select>
      </FormField>
      <FormField label="Email" :error="fieldErrors.email" hint="Optionnel — unique si renseigné" class="sm:col-span-2">
        <input v-model="form.email" type="email" class="form-input" :class="{ 'ring-red-300 border-red-300': fieldErrors.email }" placeholder="Pour inscription patient ultérieure" />
      </FormField>
      <FormField label="Téléphone" :error="fieldErrors.phone" class="sm:col-span-2">
        <input v-model="form.phone" type="tel" class="form-input" :class="{ 'ring-red-300 border-red-300': fieldErrors.phone }" placeholder="+33 6 12 34 56 78" />
      </FormField>
      <div class="sm:col-span-2 flex gap-2">
        <button type="submit" class="btn-primary">Enregistrer le patient</button>
        <button type="button" class="btn-secondary" @click="cancelCreate">Annuler</button>
      </div>
    </form>

    <DataTable
      :headers="headers"
      :rows="patients"
      :loading="loading"
      empty-title="Aucun patient enregistré"
      empty-description="Créez un premier dossier patient pour commencer."
    >
      <template #actions="{ row }">
        <button type="button" class="text-primary text-xs font-medium hover:underline mr-3" @click="openEdit(row)">Modifier</button>
        <button type="button" class="text-red-500 text-xs font-medium hover:underline" @click="archive(row)">Archiver</button>
      </template>
    </DataTable>

    <Modal :open="showEdit" title="Modifier le patient" @close="showEdit = false">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="Prénom" :error="fieldErrors.first_name" required>
          <input
            v-model="form.first_name"
            class="form-input"
            @keydown="blockDigitsInName"
            @input="stripDigitsFromName('first_name')"
            @paste="onNamePaste('first_name', $event)"
          />
        </FormField>
        <FormField label="Nom" :error="fieldErrors.last_name" required>
          <input
            v-model="form.last_name"
            class="form-input"
            @keydown="blockDigitsInName"
            @input="stripDigitsFromName('last_name')"
            @paste="onNamePaste('last_name', $event)"
          />
        </FormField>
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
        <FormField label="Email" :error="fieldErrors.email" class="sm:col-span-2">
          <input v-model="form.email" type="email" class="form-input" />
        </FormField>
        <FormField label="Téléphone" :error="fieldErrors.phone" class="sm:col-span-2">
          <input v-model="form.phone" type="tel" class="form-input" />
        </FormField>
      </div>
      <template #footer>
        <button type="button" class="btn-secondary" @click="showEdit = false">Annuler</button>
        <button type="button" class="btn-primary" @click="saveEdit">Enregistrer</button>
      </template>
    </Modal>
  </div>
</template>
