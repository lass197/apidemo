/** Extrait le message d'erreur renvoyé par l'API Django Ninja / axios. */
export function apiErrorDetail(error, fallback = 'Une erreur est survenue.') {
  const data = error?.response?.data
  const detail = data?.detail

  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === 'string') return item
      if (item?.msg) return item.msg
      if (item?.message) return item.message
      return JSON.stringify(item)
    })
    if (parts.length) return parts.join(' ')
  }
  if (typeof data === 'string' && data.trim()) return data.slice(0, 300)
  if (data?.message) return data.message

  const code = error?.code || ''
  const msg = error?.message || ''
  if (
    msg === 'Network Error'
    || code === 'ERR_NETWORK'
    || code === 'ECONNREFUSED'
    || code === 'ERR_CONNECTION_REFUSED'
    || !error?.response
  ) {
    return 'Impossible de joindre le serveur. Lancez le backend : cd backend puis python manage.py runserver'
  }

  const status = error?.response?.status
  if (status === 429) return 'Trop de tentatives. Patientez quelques minutes.'
  if (status === 500) return 'Erreur serveur. Réessayez ou contactez le support.'

  return fallback
}

/** Associe le message API au champ formulaire (email, téléphone…). */
export function mapApiErrorToFields(detail) {
  const out = {}
  if (!detail || typeof detail !== 'string') return out
  const d = detail.toLowerCase()
  if (d.includes('email') || (d.includes('compte') && d.includes('existe'))) {
    out.email = detail
  }
  if (d.includes('téléphone') || d.includes('telephone')) {
    out.phone = detail
  }
  if (d.includes('mot de passe') && !d.includes('correspondent')) {
    out.password = detail
  }
  return out
}

/** Message connexion patient plus explicite. */
export function patientLoginError(error, fallback = 'Connexion impossible.') {
  const detail = apiErrorDetail(error, fallback)
  const d = detail.toLowerCase()
  if (d.includes('aucun compte') || d.includes('email inconnu')) {
    return { message: detail, hint: 'register' }
  }
  if (d.includes('non vérifié') || d.includes('code reçu')) {
    return { message: detail, hint: 'verify' }
  }
  if (d.includes('mot de passe incorrect')) {
    return { message: detail, hint: 'password' }
  }
  if (d.includes('identifiants invalides') && error?.response?.status === 400) {
    return { message: 'Email ou mot de passe incorrect.', hint: null }
  }
  return { message: detail, hint: null }
}
