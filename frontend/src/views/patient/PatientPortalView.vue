<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/client'
import AlertBanner from '../../components/ui/AlertBanner.vue'
import StatusBadge from '../../components/ui/StatusBadge.vue'
import LoadingState from '../../components/ui/LoadingState.vue'
import EmptyState from '../../components/ui/EmptyState.vue'

const auth = useAuthStore()
const router = useRouter()
const tab = ref('rdv')
const loading = ref(true)
const error = ref('')
const success = ref('')

const patient = ref(null)
const appointments = ref([])
const doctors = ref([])
const slots = ref([])
const documents = ref([])
const careTasks = ref([])
const chatMessages = ref([])
const reminders = ref([])

const doctorId = ref(null)
const selectedSlot = ref(null)
const reason = ref('')
const chatInput = ref('')

const tabs = [
  { id: 'rdv', label: 'Rendez-vous', icon: '📅' },
  { id: 'results', label: 'Résultats', icon: '📄' },
  { id: 'care', label: 'Soins', icon: '💊' },
  { id: 'chat', label: 'Médecin', icon: '💬' },
  { id: 'reminders', label: 'Rappels', icon: '⏰' },
]

const patientId = computed(() => patient.value?.id)

async function loadProfile() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/clinical/patients/me/')
    patient.value = data
    await Promise.all([loadAppointments(), loadDoctors(), loadDocuments(), loadCareTasks(), loadReminders()])
  } catch (e) {
    error.value = e.response?.data?.detail || 'Profil patient non lié à ce compte.'
  } finally {
    loading.value = false
  }
}

async function loadAppointments() {
  if (!patientId.value) return
  const { data } = await api.get('/hr/appointments/patient/me/')
  appointments.value = data
}

async function loadDoctors() {
  const { data } = await api.get('/hr/doctors/')
  doctors.value = data
  doctorId.value ??= data[0]?.id
  if (doctorId.value) await loadSlots()
}

async function loadSlots() {
  if (!doctorId.value) return
  const { data } = await api.get(`/hr/availabilities/${doctorId.value}/slots/`)
  slots.value = data.filter((s) => s.available)
  selectedSlot.value = slots.value[0]?.scheduled_at ?? null
}

async function loadDocuments() {
  if (!patientId.value) return
  const { data } = await api.get(`/documents/?patient_id=${patientId.value}`)
  documents.value = data
}

async function loadCareTasks() {
  if (!patientId.value) return
  const { data } = await api.get(`/clinical/care-tasks/patient/${patientId.value}/`)
  careTasks.value = data
}

async function loadChat() {
  if (!patientId.value) return
  const { data } = await api.get(`/hr/chat/${patientId.value}/`)
  chatMessages.value = data
}

async function loadReminders() {
  if (!patientId.value) return
  const { data } = await api.get(`/hr/reminders/patient/${patientId.value}/`)
  reminders.value = data
}

async function bookRdv() {
  error.value = ''
  success.value = ''
  try {
    await api.post('/hr/appointments/', {
      patient_id: patientId.value,
      doctor_id: doctorId.value,
      scheduled_at: selectedSlot.value,
      reason: reason.value,
    })
    success.value = 'Rendez-vous confirmé.'
    reason.value = ''
    await loadAppointments()
    await loadSlots()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Créneau indisponible.'
  }
}

async function sendChat() {
  if (!chatInput.value.trim()) return
  await api.post('/hr/chat/', { patient_id: patientId.value, content: chatInput.value.trim() })
  chatInput.value = ''
  await loadChat()
}

async function downloadDoc(doc) {
  const response = await api.get(`/documents/${doc.id}/download/`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `${doc.title}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

function fmt(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function logout() {
  auth.logout()
  router.push('/')
}

onMounted(async () => {
  if (tab.value === 'chat') await loadChat()
  await loadProfile()
})

async function onTabChange(id) {
  tab.value = id
  if (id === 'chat') await loadChat()
}
</script>

<template>
  <div>
    <AlertBanner v-if="success" type="success">{{ success }}</AlertBanner>
    <AlertBanner v-if="error" type="error">{{ error }}</AlertBanner>

    <LoadingState v-if="loading" label="Chargement de votre dossier…" />

    <template v-else-if="patient">
      <!-- Onglets -->
      <div class="flex gap-1 overflow-x-auto pb-1 mb-6 -mx-1 px-1">
        <button
          v-for="t in tabs"
          :key="t.id"
          type="button"
          class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition shrink-0"
          :class="tab === t.id ? 'bg-primary text-white shadow-sm' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'"
          @click="onTabChange(t.id)"
        >
          <span>{{ t.icon }}</span>
          {{ t.label }}
        </button>
      </div>

      <!-- RDV -->
      <div v-if="tab === 'rdv'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="card card-body">
          <h3 class="font-semibold text-lg mb-4">Prendre rendez-vous</h3>
          <label class="block mb-3">
            <span class="form-label">Médecin</span>
            <select v-model="doctorId" class="form-select" @change="loadSlots">
              <option v-for="d in doctors" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </label>
          <label v-if="slots.length" class="block mb-3">
            <span class="form-label">Créneau disponible</span>
            <select v-model="selectedSlot" class="form-select">
              <option v-for="s in slots" :key="s.scheduled_at" :value="s.scheduled_at">{{ fmt(s.scheduled_at) }}</option>
            </select>
          </label>
          <p v-else class="text-sm text-slate-500 mb-3">Aucun créneau disponible pour ce médecin.</p>
          <label class="block mb-4">
            <span class="form-label">Motif</span>
            <input v-model="reason" class="form-input" placeholder="Consultation de suivi…" />
          </label>
          <button type="button" class="btn-primary w-full" :disabled="!selectedSlot" @click="bookRdv">Confirmer</button>
        </div>
        <div>
          <h3 class="font-semibold mb-3">Mes rendez-vous</h3>
          <div v-if="appointments.length" class="space-y-2">
            <div v-for="a in appointments" :key="a.id" class="card card-body !py-3 flex justify-between items-center gap-3">
              <div>
                <p class="font-medium">{{ a.doctor_name }}</p>
                <p class="text-sm text-slate-500">{{ fmt(a.scheduled_at) }}</p>
              </div>
              <StatusBadge :status="a.status" />
            </div>
          </div>
          <EmptyState v-else title="Aucun rendez-vous" icon="📅" />
        </div>
      </div>

      <!-- Résultats -->
      <div v-else-if="tab === 'results'">
        <div v-if="documents.length" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div v-for="d in documents" :key="d.id" class="card card-body !py-4 flex items-center gap-4 cursor-pointer hover:shadow-md transition" @click="downloadDoc(d)">
            <span class="text-3xl">📄</span>
            <div class="flex-1 min-w-0">
              <p class="font-medium truncate">{{ d.title }}</p>
              <p class="text-xs text-slate-500">{{ d.document_type }} · {{ new Date(d.created_at).toLocaleDateString('fr-FR') }}</p>
            </div>
            <span class="text-primary text-sm font-medium shrink-0">Télécharger</span>
          </div>
        </div>
        <EmptyState v-else title="Aucun document" description="Vos résultats d'examens apparaîtront ici après publication." icon="📄" />
      </div>

      <!-- Plan de soins -->
      <div v-else-if="tab === 'care'">
        <div v-if="careTasks.length" class="space-y-2">
          <div v-for="t in careTasks" :key="t.id" class="card card-body !py-3 flex justify-between items-center gap-3">
            <div>
              <p class="font-medium">{{ t.description }}</p>
              <p class="text-xs text-slate-500">{{ t.plan_title }} · {{ fmt(t.scheduled_at) }}</p>
            </div>
            <StatusBadge :status="t.status" />
          </div>
        </div>
        <EmptyState v-else title="Aucun soin planifié" description="Visible uniquement si vous êtes hospitalisé(e)." icon="💊" />
      </div>

      <!-- Chat -->
      <div v-else-if="tab === 'chat'" class="card overflow-hidden flex flex-col" style="height: 420px">
        <div class="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50">
          <div v-for="m in chatMessages" :key="m.id" class="bg-white rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm max-w-[85%] shadow-sm border border-slate-100">
            {{ m.content }}
          </div>
          <p v-if="!chatMessages.length" class="text-center text-slate-400 text-sm py-8">Aucun message — écrivez à votre médecin.</p>
        </div>
        <div class="p-3 border-t bg-white flex gap-2">
          <input v-model="chatInput" class="form-input flex-1" placeholder="Votre message…" @keydown.enter="sendChat" />
          <button type="button" class="btn-primary shrink-0" @click="sendChat">Envoyer</button>
        </div>
      </div>

      <!-- Rappels -->
      <div v-else-if="tab === 'reminders'">
        <div v-if="reminders.length" class="space-y-2">
          <div v-for="r in reminders" :key="r.id" class="card card-body !py-3 flex items-center gap-4">
            <span class="text-2xl">⏰</span>
            <div>
              <p class="font-medium">{{ r.medicine_name }}</p>
              <p class="text-sm text-slate-500">{{ r.dosage }} — {{ r.schedule_time }}</p>
            </div>
          </div>
        </div>
        <EmptyState v-else title="Aucun rappel médicament" icon="⏰" />
      </div>
    </template>

    <EmptyState v-else title="Profil patient introuvable" description="Contactez l'accueil pour lier votre compte à un dossier patient." icon="⚠️">
      <template #action>
        <button type="button" class="btn-secondary mt-4" @click="logout">Retour à l'accueil</button>
      </template>
    </EmptyState>
  </div>
</template>
