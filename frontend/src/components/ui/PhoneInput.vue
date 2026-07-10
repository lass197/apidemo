<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import {
  PHONE_COUNTRIES,
  filterCountries,
  bestCountryMatch,
  formatE164,
  parseInternationalPhone,
} from '../../composables/phoneCountries'

const props = defineProps({
  modelValue: { type: String, default: '' },
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'blur'])

const countryCode = ref('CG')
const national = ref('')
const countrySearch = ref('')
const showList = ref(false)
const nationalInput = ref(null)

const country = computed(() => PHONE_COUNTRIES.find((c) => c.code === countryCode.value) || PHONE_COUNTRIES[0])

const filteredCountries = computed(() => filterCountries(countrySearch.value))

const searchActive = computed(() => {
  const q = countrySearch.value.trim()
  if (!q) return false
  const label = `${country.value.name} (+${country.value.dial})`
  return normalizeLabel(q) !== normalizeLabel(label)
})

function normalizeLabel(s) {
  return String(s).toLowerCase().replace(/\s+/g, ' ')
}

const previewCountry = computed(() => {
  if (!searchActive.value) return null
  return bestCountryMatch(countrySearch.value)
})

watch(
  () => props.modelValue,
  (v) => {
    const parsed = parseInternationalPhone(v)
    countryCode.value = parsed.country.code
    national.value = parsed.national
    if (!searchActive.value) {
      countrySearch.value = `${parsed.country.name} (+${parsed.country.dial})`
    }
  },
  { immediate: true }
)

function syncEmit() {
  emit('update:modelValue', formatE164(country.value, national.value))
}

async function selectCountry(c) {
  countryCode.value = c.code
  countrySearch.value = `${c.name} (+${c.dial})`
  showList.value = false
  onCountryChange()
  await nextTick()
  nationalInput.value?.focus()
}

function onCountryChange() {
  national.value = national.value.replace(/\D/g, '').slice(0, country.value.max)
  syncEmit()
}

function onSearchFocus() {
  showList.value = true
  const q = countrySearch.value.trim()
  if (q && q.includes('(+')) {
    countrySearch.value = ''
  }
}

function onSearchInput() {
  showList.value = true
  const match = previewCountry.value
  if (match && filteredCountries.value.length === 1) {
    countryCode.value = match.code
    onCountryChange()
  }
}

function onSearchKeydown(event) {
  if (event.key === 'Escape') {
    showList.value = false
    countrySearch.value = `${country.value.name} (+${country.value.dial})`
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    const pick = previewCountry.value || filteredCountries.value[0]
    if (pick) selectCountry(pick)
  }
}

function onSearchBlur() {
  setTimeout(() => {
    showList.value = false
    if (!countrySearch.value.trim()) {
      countrySearch.value = `${country.value.name} (+${country.value.dial})`
    } else {
      const match = bestCountryMatch(countrySearch.value)
      if (match) {
        countryCode.value = match.code
        countrySearch.value = `${match.name} (+${match.dial})`
        onCountryChange()
      }
    }
    emit('blur')
  }, 150)
}

function onNationalInput(event) {
  const digits = event.target.value.replace(/\D/g, '')
  national.value = digits.slice(0, country.value.max)
  syncEmit()
}

function blockNonDigitKey(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return
  const allowed = ['Backspace', 'Delete', 'Tab', 'ArrowLeft', 'ArrowRight', 'Home', 'End']
  if (allowed.includes(event.key)) return
  if (!/^\d$/.test(event.key)) event.preventDefault()
}

function onPaste(event) {
  event.preventDefault()
  const text = (event.clipboardData?.getData('text') || '').replace(/\D/g, '')
  national.value = text.slice(0, country.value.max)
  syncEmit()
}
</script>

<template>
  <div class="relative">
    <label class="form-label text-[11px] text-slate-500 mb-1 block">Pays — tapez le nom, l'indicatif s'affiche</label>
    <input
      v-model="countrySearch"
      type="search"
      class="form-input text-sm mb-1"
      placeholder="Ex. Canada, France, Congo…"
      autocomplete="off"
      @focus="onSearchFocus"
      @input="onSearchInput"
      @keydown="onSearchKeydown"
      @blur="onSearchBlur"
    />

    <p
      v-if="searchActive && previewCountry"
      class="text-xs font-medium text-teal-700 bg-teal-50 border border-teal-100 rounded-lg px-3 py-2 mb-2 flex flex-wrap items-center gap-2"
    >
      <span>{{ previewCountry.flag }}</span>
      <span>{{ previewCountry.name }}</span>
      <span class="font-mono text-teal-900">+{{ previewCountry.dial }}</span>
      <span class="text-teal-600/80">— puis saisissez le numéro ci-dessous</span>
    </p>

    <div
      v-if="showList && searchActive && filteredCountries.length"
      class="absolute z-20 left-0 right-0 max-h-52 overflow-y-auto bg-white border border-slate-200 rounded-xl shadow-lg mb-2"
    >
      <button
        v-for="c in filteredCountries.slice(0, 40)"
        :key="c.code"
        type="button"
        class="w-full text-left px-3 py-2.5 text-sm hover:bg-teal-50 flex items-center gap-2 border-b border-slate-50 last:border-0"
        @mousedown.prevent="selectCountry(c)"
      >
        <span class="text-lg">{{ c.flag }}</span>
        <span class="flex-1 truncate font-medium">{{ c.name }}</span>
        <span class="font-mono text-sm font-semibold text-teal-700 shrink-0">+{{ c.dial }}</span>
      </button>
      <p v-if="filteredCountries.length > 40" class="text-[10px] text-slate-400 px-3 py-2">
        {{ filteredCountries.length }} pays — précisez la recherche
      </p>
    </div>
    <p v-else-if="searchActive && !filteredCountries.length" class="text-xs text-amber-700 mb-2">
      Aucun pays trouvé pour « {{ countrySearch }} »
    </p>

    <div class="flex gap-2 mt-2">
      <div
        class="flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-teal-200 bg-teal-50 shrink-0 min-w-[6rem]"
        :title="country.name"
      >
        <span>{{ country.flag }}</span>
        <span class="font-mono text-sm font-bold text-teal-800">+{{ country.dial }}</span>
      </div>
      <input
        ref="nationalInput"
        :value="national"
        type="tel"
        inputmode="numeric"
        pattern="[0-9]*"
        class="form-input flex-1 font-mono tracking-wide"
        :placeholder="country.example || `Numéro (${country.min}${country.min !== country.max ? '-' + country.max : ''} chiffres)`"
        :required="required"
        :aria-invalid="!!error"
        @input="onNationalInput"
        @keydown="blockNonDigitKey"
        @paste="onPaste"
      />
    </div>
    <p class="text-[11px] text-slate-500 mt-1.5">
      Indicatif actuel : <strong class="font-mono">+{{ country.dial }}</strong> ({{ country.name }})
      — sans le 0 en tête du numéro local
    </p>
  </div>
</template>
