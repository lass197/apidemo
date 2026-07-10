/** Icônes de secours — certains emoji récents (ex. 🫁) ne s'affichent pas sur Windows 10. */
const SERVICE_ICON_BY_CODE = {
  PNEUMO: '😷',
  CARDIO: '❤️',
  NEURO: '🧠',
  ORTHO: '🦴',
  PED: '👶',
  PEDIA: '👶',
  GYNECO: '♀️',
  LABO: '🔬',
  'MED-GEN': '🩺',
  URG: '🚑',
}

const UNSUPPORTED_ICONS = new Set(['🫁', '🫀', '🫃', '🫄'])

export function resolveServiceIcon(service) {
  const code = service?.code
  const icon = (service?.icon || '').trim()
  if (icon && !UNSUPPORTED_ICONS.has(icon)) return icon
  if (code && SERVICE_ICON_BY_CODE[code]) return SERVICE_ICON_BY_CODE[code]
  return '🏥'
}
