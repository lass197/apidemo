<script setup>
import { onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import AlertBanner from '../components/ui/AlertBanner.vue'
import StatusBadge from '../components/ui/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const documents = ref([])
const patients = ref([])
const patientId = ref('')
const loading = ref(true)
const uploadForm = ref({ patient_id: '', title: '', document_type: 'OTHER' })
const fileInput = ref(null)
const error = ref('')

const headers = [
  { key: 'title', label: 'Titre' },
  { key: 'document_type', label: 'Type' },
  { key: 'file_size', label: 'Taille' },
  { key: 'created_at', label: 'Créé le' },
]

async function load() {
  loading.value = true
  const params = patientId.value ? `?patient_id=${patientId.value}` : ''
  const [d, p] = await Promise.all([
    api.get(`/documents/${params}`),
    api.get('/clinical/patients/'),
  ])
  documents.value = d.data.map((doc) => ({
    ...doc,
    file_size: `${(doc.file_size / 1024).toFixed(1)} Ko`,
    created_at: new Date(doc.created_at).toLocaleDateString('fr-FR'),
  }))
  patients.value = p.data
  loading.value = false
}

async function upload() {
  error.value = ''
  const file = fileInput.value?.files?.[0]
  if (!file || !uploadForm.value.patient_id) {
    error.value = 'Patient et fichier requis.'
    return
  }
  const fd = new FormData()
  fd.append('patient_id', uploadForm.value.patient_id)
  fd.append('title', uploadForm.value.title || file.name)
  fd.append('document_type', uploadForm.value.document_type)
  fd.append('file', file)
  try {
    await api.post('/documents/upload/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    uploadForm.value = { patient_id: '', title: '', document_type: 'OTHER' }
    if (fileInput.value) fileInput.value.value = ''
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Upload échoué'
  }
}

async function download(doc) {
  const response = await api.get(`/documents/${doc.id}/download/`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `${doc.title}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Documents médicaux" subtitle="Upload sécurisé chiffré — PDF, imagerie" />

    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <form
      v-if="auth.hasPerm('documents.upload')"
      @submit.prevent="upload"
      class="card card-body mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3"
    >
      <select v-model="uploadForm.patient_id" class="form-select" required>
        <option value="">Patient</option>
        <option v-for="p in patients" :key="p.id" :value="p.id">{{ p.last_name }} {{ p.first_name }}</option>
      </select>
      <input v-model="uploadForm.title" placeholder="Titre (optionnel)" class="form-input" />
      <select v-model="uploadForm.document_type" class="form-select">
        <option value="IMAGING">Imagerie</option>
        <option value="CONSULTATION">Consultation</option>
        <option value="OTHER">Autre</option>
      </select>
      <input ref="fileInput" type="file" accept=".pdf,image/*" class="form-input text-sm" required />
      <button type="submit" class="btn-primary">Uploader</button>
    </form>

    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <select v-model="patientId" class="form-select flex-1">
        <option value="">Tous les patients</option>
        <option v-for="p in patients" :key="p.id" :value="p.id">{{ p.last_name }} {{ p.first_name }}</option>
      </select>
      <button type="button" @click="load" class="btn-primary shrink-0">Filtrer</button>
    </div>

    <DataTable
      :headers="headers"
      :rows="documents"
      :loading="loading"
      empty-title="Aucun document"
      empty-description="Uploadez un fichier PDF ou une image pour un patient."
    >
      <template #cell-document_type="{ value }">
        <StatusBadge :status="value" />
      </template>
      <template #actions="{ row }">
        <button type="button" @click="download(row)" class="text-primary text-xs font-medium hover:underline">
          Télécharger
        </button>
      </template>
    </DataTable>
  </div>
</template>
