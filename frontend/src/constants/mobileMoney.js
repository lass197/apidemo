/** Mobile Money — Congo-Brazzaville (seuls réseaux autorisés au comptoir SGHL). */
export const MOBILE_MONEY_METHODS = [
  {
    value: 'AIRTEL',
    label: 'Airtel Money',
    network: 'Airtel Congo',
    prefix: '+242 05',
    color: 'border-red-500 bg-red-50 ring-red-200',
    active: 'border-red-600 bg-red-600 text-white shadow-red-600/30',
    badge: 'bg-red-600',
    icon: '🔴',
  },
  {
    value: 'MTN',
    label: 'MTN Mobile Money',
    network: 'MTN Congo',
    prefix: '+242 06',
    color: 'border-amber-400 bg-amber-50 ring-amber-200',
    active: 'border-amber-500 bg-amber-500 text-white shadow-amber-500/30',
    badge: 'bg-amber-500',
    icon: '🟡',
  },
]

export const PAYMENT_PROCEDURE = [
  'Sélectionner la facture et vérifier le solde restant',
  'Choisir le réseau mobile (Airtel ou MTN)',
  'Saisir le montant — ne pas dépasser le solde dû',
  'Indiquer la référence transaction (N° ou téléphone payeur)',
  'Valider après confirmation du débit mobile money',
]
