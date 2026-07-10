/** Monnaie officielle SGHL — franc CFA (XAF / CFA), zone CEMAC. */
export const CURRENCY_LABEL = 'FCFA'
export const CURRENCY_SYMBOL = 'FCFA'
export const CURRENCY_FULL = 'Franc CFA (FCFA — XAF)'

export function formatMoney(amount, options = {}) {
  const { decimals = 0, empty = '—' } = options
  if (amount === null || amount === undefined || amount === '') return `${empty} ${CURRENCY_SYMBOL}`
  const n = Number(amount)
  if (Number.isNaN(n)) return `${empty} ${CURRENCY_SYMBOL}`
  const formatted = new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.round(n))
  return `${formatted} ${CURRENCY_SYMBOL}`
}

/** Alias explicite CFA */
export const formatCFA = formatMoney
