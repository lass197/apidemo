<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import Modal from '../components/Modal.vue'
import FormField from '../components/FormField.vue'

const auth = useAuthStore()
const canManageBuilding = computed(() => auth.hasPerm('core.manage_users'))
const canDeleteBuilding = computed(() => auth.hasPerm('core.delete_building'))
const tab = ref('buildings')
const showInactive = ref(true)
const buildings = ref([])
const departments = ref([])
const rooms = ref([])
const beds = ref([])
const loading = ref(true)
const error = ref('')
const success = ref('')
const showModal = ref(false)
const modalType = ref('building')
const buildingModalMode = ref('edit')
const editing = ref(null)

const buildingForm = ref({ name: '', code: '', address: '', is_active: true })
const deptForm = ref({ building_id: '', name: '', code: '', is_active: true })
const roomForm = ref({ department_id: '', number: '', floor: 0, is_active: true })
const bedForm = ref({ room_id: '', label: '', status: 'AVAILABLE', is_active: true })

const selectedBuildingId = ref('')
const selectedDeptId = ref('')

const BED_STATUS = {
  AVAILABLE: 'Disponible',
  OCCUPIED: 'Occupé',
  MAINTENANCE: 'Maintenance',
}

function activeLabel(isActive) {
  return isActive !== false ? 'Actif' : 'Inactif'
}

const buildingHeaders = [
  { key: 'name', label: 'Nom' },
  { key: 'code', label: 'Code' },
  { key: 'beds', label: 'Lits' },
  { key: 'departments_count', label: 'Services' },
  { key: 'status', label: 'Statut' },
]

const deptHeaders = [
  { key: 'building_code', label: 'Bâtiment' },
  { key: 'name', label: 'Service' },
  { key: 'code', label: 'Code' },
  { key: 'rooms_count', label: 'Chambres' },
  { key: 'status', label: 'Statut' },
]

const roomHeaders = [
  { key: 'building_code', label: 'Bâtiment' },
  { key: 'department_name', label: 'Service' },
  { key: 'number', label: 'N° chambre' },
  { key: 'floor', label: 'Étage' },
  { key: 'beds_count', label: 'Lits' },
  { key: 'status', label: 'Statut' },
]

const bedHeaders = [
  { key: 'building_code', label: 'Bâtiment' },
  { key: 'department_name', label: 'Service' },
  { key: 'room_number', label: 'Chambre' },
  { key: 'label', label: 'Lit' },
  { key: 'status_label', label: 'Occupation' },
  { key: 'status', label: 'Enregistrement' },
]

const buildingRows = computed(() =>
  buildings.value
    .filter((b) => showInactive.value || b.is_active !== false)
    .map((b) => ({
      ...b,
      beds: `${b.beds_available}/${b.beds_total}`,
      status: activeLabel(b.is_active),
    }))
)

const deptRows = computed(() =>
  filteredDepts.value
    .filter((d) => showInactive.value || d.is_active !== false)
    .map((d) => ({ ...d, status: activeLabel(d.is_active) }))
)

const roomRows = computed(() =>
  filteredRooms.value
    .filter((r) => showInactive.value || r.is_active !== false)
    .map((r) => ({ ...r, status: activeLabel(r.is_active) }))
)

const bedRows = computed(() =>
  filteredBeds.value
    .filter((b) => showInactive.value || b.is_active !== false)
    .map((b) => ({
      ...b,
      occupation: b.status,
      occupation_label: BED_STATUS[b.status] || b.status,
      status: activeLabel(b.is_active),
    }))
)

const filteredDepts = computed(() => {
  let rows = departments.value
  if (selectedBuildingId.value) {
    rows = rows.filter((d) => d.building_id === selectedBuildingId.value)
  }
  return rows
})

const filteredRooms = computed(() => {
  let rows = rooms.value
  if (selectedBuildingId.value) {
    const deptIds = departments.value
      .filter((d) => d.building_id === selectedBuildingId.value)
      .map((d) => d.id)
    rows = rows.filter((r) => deptIds.includes(r.department_id))
  }
  if (selectedDeptId.value) rows = rows.filter((r) => r.department_id === selectedDeptId.value)
  return rows
})

const filteredBeds = computed(() => {
  if (!selectedDeptId.value && !selectedBuildingId.value) return beds.value
  const roomIds = new Set(filteredRooms.value.map((r) => r.id))
  return beds.value.filter((b) => roomIds.has(b.room_id))
})

const inactiveParams = computed(() => ({ include_inactive: showInactive.value }))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = inactiveParams.value
    const [b, d, r, bd] = await Promise.all([
      api.get('/infrastructure/buildings/', { params }),
      api.get('/infrastructure/departments/', { params }),
      api.get('/infrastructure/rooms/', { params }),
      api.get('/infrastructure/beds/', { params }),
    ])
    buildings.value = b.data
    departments.value = d.data
    rooms.value = r.data
    beds.value = bd.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur chargement infrastructure'
  } finally {
    loading.value = false
  }
}

function openBuildingCreate() {
  editing.value = null
  modalType.value = 'building'
  buildingModalMode.value = 'create'
  buildingForm.value = { name: '', code: '', address: '', is_active: true }
  showModal.value = true
}

function openBuildingEdit(row) {
  editing.value = row
  modalType.value = 'building'
  buildingModalMode.value = 'edit'
  buildingForm.value = {
    name: row.name,
    code: row.code,
    address: row.address || '',
    is_active: row.is_active !== false,
  }
  showModal.value = true
}

function openBuildingRename(row) {
  editing.value = row
  modalType.value = 'building'
  buildingModalMode.value = 'rename'
  buildingForm.value = {
    name: row.name,
    code: row.code,
    address: row.address || '',
    is_active: row.is_active !== false,
  }
  showModal.value = true
}

function openDeptCreate() {
  editing.value = null
  modalType.value = 'department'
  deptForm.value = {
    building_id: selectedBuildingId.value || buildings.value.find((b) => b.is_active !== false)?.id || '',
    name: '',
    code: '',
    is_active: true,
  }
  showModal.value = true
}

function openDeptEdit(row) {
  editing.value = row
  modalType.value = 'department'
  deptForm.value = {
    building_id: row.building_id,
    name: row.name,
    code: row.code,
    is_active: row.is_active !== false,
  }
  showModal.value = true
}

function openRoomCreate() {
  editing.value = null
  modalType.value = 'room'
  roomForm.value = {
    department_id: selectedDeptId.value || filteredDepts.value.find((d) => d.is_active !== false)?.id || '',
    number: '',
    floor: 0,
    is_active: true,
  }
  showModal.value = true
}

function openRoomEdit(row) {
  editing.value = row
  modalType.value = 'room'
  roomForm.value = {
    department_id: row.department_id,
    number: row.number,
    floor: row.floor,
    is_active: row.is_active !== false,
  }
  showModal.value = true
}

function openBedCreate() {
  editing.value = null
  modalType.value = 'bed'
  bedForm.value = {
    room_id: filteredRooms.value.find((r) => r.is_active !== false)?.id || '',
    label: '',
    status: 'AVAILABLE',
    is_active: true,
  }
  showModal.value = true
}

function openBedEdit(row) {
  editing.value = row
  modalType.value = 'bed'
  bedForm.value = {
    room_id: row.room_id,
    label: row.label,
    status: row.status,
    is_active: row.is_active !== false,
  }
  showModal.value = true
}

async function saveModal() {
  error.value = ''
  try {
    if (modalType.value === 'building') {
      if (editing.value) {
        let payload
        if (buildingModalMode.value === 'rename') {
          payload = { name: buildingForm.value.name }
        } else if (buildingModalMode.value === 'edit') {
          payload = {
            ...buildingForm.value,
            code: buildingForm.value.code.trim().toUpperCase(),
          }
        } else {
          payload = {
            ...buildingForm.value,
            code: buildingForm.value.code.trim().toUpperCase(),
          }
        }
        await api.patch(`/infrastructure/buildings/${editing.value.id}/`, payload)
        success.value =
          buildingModalMode.value === 'rename' ? 'Bâtiment renommé.' : 'Bâtiment mis à jour.'
      } else {
        const { is_active, ...createPayload } = buildingForm.value
        await api.post('/infrastructure/buildings/', {
          ...createPayload,
          code: createPayload.code.trim().toUpperCase(),
        })
        success.value = 'Bâtiment créé.'
      }
    } else if (modalType.value === 'department') {
      const payload = { ...deptForm.value, code: deptForm.value.code.toUpperCase() }
      if (editing.value) {
        await api.patch(`/infrastructure/departments/${editing.value.id}/`, {
          name: payload.name,
          code: payload.code,
          is_active: payload.is_active,
        })
        success.value = 'Service mis à jour.'
      } else {
        await api.post('/infrastructure/departments/', payload)
        success.value = 'Service créé.'
      }
    } else if (modalType.value === 'room') {
      if (editing.value) {
        await api.patch(`/infrastructure/rooms/${editing.value.id}/`, {
          number: roomForm.value.number,
          floor: roomForm.value.floor,
          is_active: roomForm.value.is_active,
        })
        success.value = 'Chambre mise à jour.'
      } else {
        await api.post('/infrastructure/rooms/', roomForm.value)
        success.value = 'Chambre créée.'
      }
    } else if (modalType.value === 'bed') {
      if (editing.value) {
        await api.patch(`/infrastructure/beds/${editing.value.id}/`, {
          label: bedForm.value.label,
          status: bedForm.value.status,
          is_active: bedForm.value.is_active,
        })
        success.value = 'Lit mis à jour.'
      } else {
        await api.post('/infrastructure/beds/', bedForm.value)
        success.value = 'Lit créé.'
      }
    }
    showModal.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Enregistrement impossible'
  }
}

async function toggleBuildingActive(row) {
  const next = row.is_active === false
  if (!next && !window.confirm(`Désactiver le bâtiment « ${row.name} » ?`)) return
  error.value = ''
  try {
    await api.patch(`/infrastructure/buildings/${row.id}/`, { is_active: next })
    success.value = next ? 'Bâtiment activé.' : 'Bâtiment désactivé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible'
  }
}

async function toggleDeptActive(row) {
  const next = row.is_active === false
  if (!next && !window.confirm(`Désactiver le service « ${row.name} » ?`)) return
  try {
    await api.patch(`/infrastructure/departments/${row.id}/`, { is_active: next })
    success.value = next ? 'Service activé.' : 'Service désactivé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible'
  }
}

async function toggleRoomActive(row) {
  const next = row.is_active === false
  if (!next && !window.confirm(`Désactiver la chambre « ${row.number} » ?`)) return
  try {
    await api.patch(`/infrastructure/rooms/${row.id}/`, { is_active: next })
    success.value = next ? 'Chambre activée.' : 'Chambre désactivée.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible'
  }
}

async function toggleBedActive(row) {
  const next = row.is_active === false
  if (!next && !window.confirm(`Désactiver le lit « ${row.label} » ?`)) return
  try {
    await api.patch(`/infrastructure/beds/${row.id}/`, { is_active: next })
    success.value = next ? 'Lit activé.' : 'Lit désactivé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible'
  }
}

async function setBedStatusQuick(row, status) {
  try {
    await api.patch(`/infrastructure/beds/${row.id}/`, { status })
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Mise à jour impossible'
  }
}

async function deactivateBuilding(row) {
  if (!window.confirm(`Supprimer (désactiver) le bâtiment « ${row.name} » ?`)) return
  try {
    await api.delete(`/infrastructure/buildings/${row.id}/`)
    success.value = 'Bâtiment supprimé.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Action impossible'
  }
}

const modalTitle = computed(() => {
  if (modalType.value === 'building') {
    if (buildingModalMode.value === 'rename') return 'Renommer le bâtiment'
    if (buildingModalMode.value === 'create') return 'Nouveau bâtiment'
    return 'Modifier le bâtiment'
  }
  const labels = { department: 'service', room: 'chambre', bed: 'lit' }
  const action = editing.value ? 'Modifier' : 'Nouveau'
  return `${action} ${labels[modalType.value]}`
})

const actionBtn =
  'px-2 py-1 rounded-md text-xs font-medium transition'

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Infrastructure"
      subtitle="Bâtiments, services, chambres et lits — statut actif/inactif"
    />

    <p v-if="error" class="alert-error mb-4">{{ error }}</p>
    <p v-if="success" class="alert-success mb-4">{{ success }}</p>

    <div class="card card-body mb-6 flex flex-wrap gap-3 items-end">
      <div>
        <label class="form-label">Filtrer par bâtiment</label>
        <select v-model="selectedBuildingId" class="form-select sm:w-48">
          <option value="">Tous</option>
          <option v-for="b in buildings.filter((x) => x.is_active !== false)" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>
      </div>
      <div>
        <label class="form-label">Filtrer par service</label>
        <select v-model="selectedDeptId" class="form-select sm:w-48">
          <option value="">Tous</option>
          <option v-for="d in filteredDepts.filter((x) => x.is_active !== false)" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>
      <label class="flex items-center gap-2 text-sm text-slate-600 cursor-pointer pb-1">
        <input v-model="showInactive" type="checkbox" class="rounded border-slate-300" @change="load" />
        Afficher les éléments inactifs
      </label>
      <button type="button" class="btn-secondary text-sm ml-auto" @click="load">Actualiser</button>
    </div>

    <div class="flex flex-wrap gap-2 mb-6">
      <button type="button" class="tab-btn" :class="tab === 'buildings' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'buildings'">Bâtiments</button>
      <button type="button" class="tab-btn" :class="tab === 'departments' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'departments'">Services</button>
      <button type="button" class="tab-btn" :class="tab === 'rooms' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'rooms'">Chambres</button>
      <button type="button" class="tab-btn" :class="tab === 'beds' ? 'tab-btn-active' : 'tab-btn-inactive'" @click="tab = 'beds'">Lits</button>
    </div>

    <template v-if="tab === 'buildings'">
      <div class="flex justify-end mb-4">
        <button v-if="canManageBuilding" type="button" class="btn-primary" @click="openBuildingCreate">+ Bâtiment</button>
      </div>
      <DataTable :headers="buildingHeaders" :rows="buildingRows" :loading="loading" empty-title="Aucun bâtiment">
        <template #cell-status="{ row }">
          <span
            class="text-xs font-semibold px-2 py-0.5 rounded-full"
            :class="row.is_active !== false ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'"
          >{{ row.status }}</span>
        </template>
        <template #actions="{ row }">
          <div v-if="canManageBuilding" class="flex flex-wrap gap-1 justify-end">
            <button type="button" :class="actionBtn + ' bg-slate-100 text-slate-700 hover:bg-slate-200'" @click="openBuildingRename(row)">Renommer</button>
            <button type="button" :class="actionBtn + ' bg-admin/10 text-admin hover:bg-admin/20'" @click="openBuildingEdit(row)">Modifier</button>
            <button
              type="button"
              :class="actionBtn + (row.is_active !== false ? ' bg-amber-50 text-amber-800 hover:bg-amber-100' : ' bg-emerald-50 text-emerald-800 hover:bg-emerald-100')"
              @click="toggleBuildingActive(row)"
            >{{ row.is_active !== false ? 'Désactiver' : 'Activer' }}</button>
            <button
              v-if="canDeleteBuilding && row.is_active !== false"
              type="button"
              :class="actionBtn + ' bg-red-50 text-red-600 hover:bg-red-100'"
              @click="deactivateBuilding(row)"
            >Supprimer</button>
          </div>
        </template>
      </DataTable>
    </template>

    <template v-else-if="tab === 'departments'">
      <div class="flex justify-end mb-4">
        <button v-if="canManageBuilding" type="button" class="btn-primary" @click="openDeptCreate">+ Service</button>
      </div>
      <DataTable :headers="deptHeaders" :rows="deptRows" :loading="loading" empty-title="Aucun service">
        <template #cell-status="{ row }">
          <span
            class="text-xs font-semibold px-2 py-0.5 rounded-full"
            :class="row.is_active !== false ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'"
          >{{ row.status }}</span>
        </template>
        <template #actions="{ row }">
          <div v-if="canManageBuilding" class="flex flex-wrap gap-1 justify-end">
            <button type="button" :class="actionBtn + ' bg-admin/10 text-admin hover:bg-admin/20'" @click="openDeptEdit(row)">Modifier</button>
            <button
              type="button"
              :class="actionBtn + (row.is_active !== false ? ' bg-amber-50 text-amber-800' : ' bg-emerald-50 text-emerald-800')"
              @click="toggleDeptActive(row)"
            >{{ row.is_active !== false ? 'Désactiver' : 'Activer' }}</button>
          </div>
        </template>
      </DataTable>
    </template>

    <template v-else-if="tab === 'rooms'">
      <div class="flex justify-end mb-4">
        <button v-if="canManageBuilding" type="button" class="btn-primary" @click="openRoomCreate">+ Chambre</button>
      </div>
      <DataTable :headers="roomHeaders" :rows="roomRows" :loading="loading" empty-title="Aucune chambre">
        <template #cell-status="{ row }">
          <span
            class="text-xs font-semibold px-2 py-0.5 rounded-full"
            :class="row.is_active !== false ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'"
          >{{ row.status }}</span>
        </template>
        <template #actions="{ row }">
          <div v-if="canManageBuilding" class="flex flex-wrap gap-1 justify-end">
            <button type="button" :class="actionBtn + ' bg-admin/10 text-admin hover:bg-admin/20'" @click="openRoomEdit(row)">Modifier n°</button>
            <button
              type="button"
              :class="actionBtn + (row.is_active !== false ? ' bg-amber-50 text-amber-800' : ' bg-emerald-50 text-emerald-800')"
              @click="toggleRoomActive(row)"
            >{{ row.is_active !== false ? 'Désactiver' : 'Activer' }}</button>
          </div>
        </template>
      </DataTable>
    </template>

    <template v-else>
      <div class="flex justify-end mb-4">
        <button v-if="canManageBuilding" type="button" class="btn-primary" @click="openBedCreate">+ Lit</button>
      </div>
      <DataTable :headers="bedHeaders" :rows="bedRows" :loading="loading" empty-title="Aucun lit">
        <template #cell-status_label="{ row }">
          <span
            class="text-xs font-semibold px-2 py-0.5 rounded-full"
            :class="{
              'bg-emerald-100 text-emerald-800': row.occupation === 'AVAILABLE',
              'bg-red-100 text-red-800': row.occupation === 'OCCUPIED',
              'bg-amber-100 text-amber-800': row.occupation === 'MAINTENANCE',
            }"
          >{{ row.occupation_label }}</span>
        </template>
        <template #cell-status="{ row }">
          <span
            class="text-xs font-semibold px-2 py-0.5 rounded-full"
            :class="row.is_active !== false ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'"
          >{{ row.status }}</span>
        </template>
        <template #actions="{ row }">
          <div v-if="canManageBuilding" class="flex flex-wrap gap-1 items-center justify-end">
            <button type="button" :class="actionBtn + ' bg-admin/10 text-admin hover:bg-admin/20'" @click="openBedEdit(row)">Modifier</button>
            <select class="form-input !py-1 text-xs w-28" :value="row.occupation" @change="setBedStatusQuick(row, $event.target.value)">
              <option value="AVAILABLE">Disponible</option>
              <option value="OCCUPIED">Occupé</option>
              <option value="MAINTENANCE">Maintenance</option>
            </select>
            <button
              type="button"
              :class="actionBtn + (row.is_active !== false ? ' bg-amber-50 text-amber-800' : ' bg-emerald-50 text-emerald-800')"
              @click="toggleBedActive(row)"
            >{{ row.is_active !== false ? 'Désactiver' : 'Activer' }}</button>
          </div>
        </template>
      </DataTable>
    </template>

    <Modal :open="showModal" :title="modalTitle" @close="showModal = false">
      <div v-if="modalType === 'building'" class="space-y-3">
        <FormField label="Nom" required>
          <input v-model="buildingForm.name" class="form-input" required autofocus />
        </FormField>
        <template v-if="buildingModalMode !== 'rename'">
          <FormField label="Code" required hint="Identifiant court unique (ex. A, MAIN) — modifiable">
            <input
              v-model="buildingForm.code"
              class="form-input font-mono uppercase"
              maxlength="20"
              required
            />
          </FormField>
          <FormField label="Adresse"><input v-model="buildingForm.address" class="form-input" /></FormField>
        </template>
        <p v-else class="text-xs text-slate-500">
          Code : <span class="font-mono font-medium">{{ buildingForm.code }}</span>
        </p>
        <label v-if="buildingModalMode === 'edit'" class="flex items-center gap-2 text-sm cursor-pointer">
          <input v-model="buildingForm.is_active" type="checkbox" class="rounded border-slate-300" />
          Bâtiment actif (visible pour admissions et filtres)
        </label>
      </div>
      <div v-else-if="modalType === 'department'" class="space-y-3">
        <FormField label="Bâtiment" required>
          <select v-model="deptForm.building_id" class="form-select" :disabled="!!editing">
            <option v-for="b in buildings.filter((x) => x.is_active !== false)" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </FormField>
        <FormField label="Nom du service" required><input v-model="deptForm.name" class="form-input" required /></FormField>
        <FormField label="Code" required><input v-model="deptForm.code" class="form-input" required /></FormField>
        <label v-if="editing" class="flex items-center gap-2 text-sm cursor-pointer">
          <input v-model="deptForm.is_active" type="checkbox" class="rounded border-slate-300" />
          Service actif
        </label>
      </div>
      <div v-else-if="modalType === 'room'" class="space-y-3">
        <FormField label="Service" required>
          <select v-model="roomForm.department_id" class="form-select" :disabled="!!editing">
            <option v-for="d in departments.filter((x) => x.is_active !== false)" :key="d.id" :value="d.id">{{ d.building_code }} — {{ d.name }}</option>
          </select>
        </FormField>
        <FormField label="N° chambre" required><input v-model="roomForm.number" class="form-input" required /></FormField>
        <FormField label="Étage"><input v-model.number="roomForm.floor" type="number" min="0" class="form-input" /></FormField>
        <label v-if="editing" class="flex items-center gap-2 text-sm cursor-pointer">
          <input v-model="roomForm.is_active" type="checkbox" class="rounded border-slate-300" />
          Chambre active
        </label>
      </div>
      <div v-else class="space-y-3">
        <FormField label="Chambre" required>
          <select v-model="bedForm.room_id" class="form-select" :disabled="!!editing">
            <option v-for="r in rooms.filter((x) => x.is_active !== false)" :key="r.id" :value="r.id">
              {{ r.building_code }} / {{ r.department_name }} — Ch. {{ r.number }}
            </option>
          </select>
        </FormField>
        <FormField label="N° / libellé lit" required><input v-model="bedForm.label" class="form-input" required placeholder="A, B, 1…" /></FormField>
        <FormField label="Occupation">
          <select v-model="bedForm.status" class="form-select">
            <option value="AVAILABLE">Disponible</option>
            <option value="OCCUPIED">Occupé</option>
            <option value="MAINTENANCE">Maintenance</option>
          </select>
        </FormField>
        <label v-if="editing" class="flex items-center gap-2 text-sm cursor-pointer">
          <input v-model="bedForm.is_active" type="checkbox" class="rounded border-slate-300" />
          Lit enregistré (actif)
        </label>
      </div>
      <template #footer>
        <button type="button" class="btn-secondary" @click="showModal = false">Annuler</button>
        <button type="button" class="btn-primary" @click="saveModal">Enregistrer</button>
      </template>
    </Modal>
  </div>
</template>
