/** Règles de validation formulaires — miroir backend */

const PERSON_NAME_RE = /^[a-zA-ZÀ-ÿ\s'-]+$/

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
    const v = (value || '').trim()
    if (!v) return required ? 'Téléphone obligatoire.' : ''
    const digits = v.replace(/\D/g, '')
    if (digits.length < 8 || digits.length > 15) return 'Téléphone invalide (8 à 15 chiffres).'
    if (!/^[+0-9\s().-]+$/.test(v)) return 'Caractères téléphone invalides.'
    return ''
  },

  email(value, required = false) {
    const v = (value || '').trim()
    if (!v) return required ? 'Email obligatoire.' : ''
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return 'Format email invalide.'
    return ''
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

  password(value, min = 8) {
    if (!value || value.length < min) return `Mot de passe : minimum ${min} caractères.`
    return ''
  },

  username(value) {
    const v = (value || '').trim().toLowerCase()
    if (!v) return 'Identifiant obligatoire.'
    if (!/^[a-z0-9._-]{3,40}$/.test(v)) return 'Identifiant : 3–40 caractères (a-z, 0-9, . _ -).'
    return ''
  },
}

export function blockDigitsInName(event) {
  if (/\d/.test(event.key)) event.preventDefault()
}

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
