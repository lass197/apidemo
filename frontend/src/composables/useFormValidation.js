/** Règles de validation formulaires — miroir backend */

import { parseInternationalPhone } from './phoneCountries'

const PERSON_NAME_RE = /^[a-zA-ZÀ-ÿ\s'-]+$/
const EMAIL_RE = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/

export const validators = {
  personName(value, field = 'Ce champ') {
    const v = (value || '').trim()
    if (!v) return `${field} est obligatoire.`
    if (/\d/.test(v)) return `${field} : les chiffres ne sont pas autorisés.`
    if (!PERSON_NAME_RE.test(v)) return `${field} : lettres, espaces, apostrophe et tiret uniquement.`
    if (v.length < 2) return `${field} : minimum 2 caractères.`
    return ''
  },

  phone(value, required = false) {
    return validators.phoneInternational(value, required)
  },

  phoneInternational(value, required = false) {
    const v = (value || '').trim()
    if (!v) return required ? 'Téléphone obligatoire.' : ''
    if (!v.startsWith('+')) return 'Sélectionnez l\'indicatif pays et saisissez uniquement des chiffres.'
    const { country, national } = parseInternationalPhone(v)
    if (!national) return 'Numéro obligatoire (chiffres uniquement).'
    if (!/^\d+$/.test(national)) return 'Le numéro ne doit contenir que des chiffres.'
    if (national.length < country.min || national.length > country.max) {
      return `${country.name} (+${country.dial}) : ${country.min === country.max ? country.min : `${country.min} à ${country.max}`} chiffres.`
    }
    return ''
  },

  email(value, required = false) {
    const v = (value || '').trim().toLowerCase()
    if (!v) return required ? 'Email obligatoire.' : ''
    if (v.includes(' ')) return 'L\'email ne doit pas contenir d\'espaces.'
    if (!v.includes('@') || !v.includes('.')) return 'Format invalide : exemple nom@domaine.fr'
    if (!EMAIL_RE.test(v)) return 'Adresse email incorrecte. Vérifiez l\'orthographe.'
    const domain = v.split('@')[1]
    if (!domain || domain.startsWith('.') || domain.endsWith('.')) return 'Domaine email invalide (ex. @gmail.com).'
    return ''
  },

  loginIdentifier(value, isPatient = false) {
    const v = (value || '').trim()
    if (!v) return isPatient ? 'Email ou identifiant obligatoire.' : 'Identifiant obligatoire.'
    if (v.includes('@')) return validators.email(v, true)
    return validators.username(v)
  },

  dateOfBirth(value) {
    if (!value) return 'Date de naissance obligatoire.'
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return 'Date invalide.'
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    if (d > today) return 'La date ne peut pas être dans le futur.'
    const age = today.getFullYear() - d.getFullYear()
    if (age > 120) return 'Date de naissance invalide.'
    return ''
  },

  password(value, min = 10) {
    if (!value || value.length < min) return `Mot de passe : minimum ${min} caractères.`
    if (/^\d+$/.test(value)) return 'Le mot de passe ne peut pas être entièrement numérique.'
    return ''
  },

  username(value) {
    const v = (value || '').trim().toLowerCase()
    if (!v) return 'Identifiant obligatoire.'
    if (!/^[a-z0-9._-]{3,40}$/.test(v)) return 'Identifiant : 3–40 caractères (a-z, 0-9, . _ -).'
    return ''
  },

  /** Recherche patient (nom/prénom) — lettres uniquement, min. 2 caractères */
  personNameSearch(value, field = 'Nom du patient') {
    const v = (value || '').trim()
    if (!v) return `${field} est obligatoire.`
    if (/\d/.test(v)) return `${field} : les chiffres ne sont pas autorisés.`
    if (!PERSON_NAME_RE.test(v)) return `${field} : lettres, espaces, apostrophe et tiret uniquement.`
    if (v.length < 2) return `${field} : minimum 2 caractères.`
    return ''
  },

  /** Motif ou résumé clinique */
  medicalText(value, field = 'Ce champ', { required = true, minLength = 10 } = {}) {
    const v = (value || '').trim()
    if (!v) return required ? `${field} est obligatoire.` : ''
    if (v.length < minLength) return `${field} : minimum ${minLength} caractères.`
    if (/^\d+$/.test(v)) return `${field} : ne peut pas être uniquement numérique.`
    if (!/[a-zA-ZÀ-ÿ]/.test(v)) return `${field} : doit contenir des lettres.`
    return ''
  },

  requiredSelection(value, field = 'Ce champ') {
    if (!value) return `${field} : sélection obligatoire.`
    return ''
  },

  /** Filtre établissement (nom, ville) — lettres uniquement si renseigné */
  optionalLabelSearch(value, field = 'Recherche') {
    const v = (value || '').trim()
    if (!v) return ''
    if (/\d/.test(v)) return `${field} : les chiffres ne sont pas autorisés.`
    if (!PERSON_NAME_RE.test(v)) return `${field} : lettres, espaces, apostrophe et tiret uniquement.`
    return ''
  },
}

/** Bloque la saisie de chiffres dans les champs nom */
export function blockDigitsInName(event) {
  if (/\d/.test(event.key)) event.preventDefault()
}

/** Nettoie collage (paste) pour noms */
export function sanitizeNamePaste(event, setter) {
  event.preventDefault()
  const text = (event.clipboardData?.getData('text') || '').replace(/\d/g, '')
  setter(text)
}

export function validateFields(rules) {
  const errors = {}
  for (const [key, fn] of Object.entries(rules)) {
    const msg = fn()
    if (msg) errors[key] = msg
  }
  return errors
}

export function hasErrors(errors) {
  return Object.values(errors).some(Boolean)
}
