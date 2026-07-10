import countriesData from '../data/phoneCountries.json'

/** Tous les pays (indicatifs internationaux), République du Congo (RC) +242 en tête. */
export const PHONE_COUNTRIES = countriesData

const BY_DIAL_LENGTH = [...PHONE_COUNTRIES].sort((a, b) => b.dial.length - a.dial.length)

export function findCountryByCode(code) {
  return PHONE_COUNTRIES.find((c) => c.code === code) || PHONE_COUNTRIES[0]
}

export function findCountryByDial(dial) {
  return PHONE_COUNTRIES.find((c) => c.dial === dial) || PHONE_COUNTRIES[0]
}

/** Parse +242061234567 → { country, national } */
export function parseInternationalPhone(value) {
  const digits = String(value || '').replace(/\D/g, '')
  if (!digits) return { country: PHONE_COUNTRIES[0], national: '' }
  for (const c of BY_DIAL_LENGTH) {
    if (digits.startsWith(c.dial)) {
      return { country: c, national: digits.slice(c.dial.length) }
    }
  }
  return { country: PHONE_COUNTRIES[0], national: digits }
}

export function formatE164(country, nationalDigits) {
  const n = String(nationalDigits || '').replace(/\D/g, '')
  if (!n) return ''
  return `+${country.dial}${n}`
}

/** Noms français / variantes pour la recherche (ex. « canada » → Canada +1). */
const SEARCH_ALIASES = {
  CA: ['canada', 'canadien', 'canadienne'],
  US: ['usa', 'etats-unis', 'états-unis', 'amerique', 'amérique'],
  FR: ['france', 'francais', 'français', 'francaise', 'française'],
  BE: ['belgique', 'belge'],
  CH: ['suisse', 'helvetique', 'helvétique'],
  CG: ['congo brazzaville', 'brazzaville', 'congo'],
  CD: ['congo kinshasa', 'kinshasa', 'rdc', 'republique democratique'],
  CI: ['cote divoire', "côte d'ivoire", 'ivoirien', 'abidjan'],
  CM: ['cameroun', 'camerounais'],
  SN: ['senegal', 'sénégal', 'dakar'],
  MA: ['maroc', 'marocain'],
  TN: ['tunisie', 'tunisien'],
  DZ: ['algerie', 'algérie', 'algerien'],
  GB: ['royaume-uni', 'angleterre', 'grande-bretagne', 'uk'],
  DE: ['allemagne', 'allemand'],
  ES: ['espagne', 'espagnol'],
  IT: ['italie', 'italien'],
  PT: ['portugal', 'portugais'],
  CN: ['chine', 'chinois'],
  IN: ['inde', 'indien'],
  BR: ['bresil', 'brésil', 'bresilien'],
  MX: ['mexique', 'mexicain'],
  RU: ['russie', 'russe'],
  JP: ['japon', 'japonais'],
  KR: ['coree', 'corée', 'coreen'],
  AE: ['emirats', 'émirats', 'dubai', 'dubaï'],
  SA: ['arabie saoudite', 'saoudite'],
  TR: ['turquie', 'turc'],
  NL: ['pays-bas', 'hollande', 'neerlandais'],
  LU: ['luxembourg'],
  MC: ['monaco'],
  HT: ['haiti', 'haïti'],
  MG: ['madagascar', 'malgache'],
  MU: ['maurice', 'mauricien'],
  GA: ['gabon', 'gabonais'],
  GN: ['guinee', 'guinée'],
  ML: ['mali', 'malien'],
  BF: ['burkina'],
  NE: ['niger', 'nigerien'],
  TG: ['togo', 'togolais'],
  BJ: ['benin', 'bénin', 'beninois'],
}

function normalizeSearchText(text) {
  return String(text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/['']/g, ' ')
}

function countrySearchBlob(c) {
  const parts = [
    c.name,
    c.code,
    c.dial,
    `+${c.dial}`,
    ...(SEARCH_ALIASES[c.code] || []),
  ]
  return normalizeSearchText(parts.join(' '))
}

export function filterCountries(query) {
  const raw = (query || '').trim()
  if (!raw) return PHONE_COUNTRIES
  const q = normalizeSearchText(raw)
  const dialOnly = raw.replace(/\D/g, '')
  const words = q.split(/\s+/).filter(Boolean)

  return PHONE_COUNTRIES.filter((c) => {
    const hay = countrySearchBlob(c)
    if (dialOnly && (c.dial.startsWith(dialOnly) || dialOnly.startsWith(c.dial))) return true
    if (raw.includes('+') && hay.includes(normalizeSearchText(raw.replace(/\s/g, '')))) return true
    return words.every((w) => hay.includes(w))
  })
}

/** Meilleure correspondance pour saisie partielle (ex. « cana » → Canada). */
export function bestCountryMatch(query) {
  const list = filterCountries(query)
  if (!list.length) return null
  const q = normalizeSearchText(query)
  const exact = list.find((c) => {
    const hay = countrySearchBlob(c)
    return hay.split(' ').some((w) => w === q || w.startsWith(q))
  })
  return exact || list[0]
}
