import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

/** Navigation staff — ordre décroissant de privilège métier (après ADMIN). */
export const STAFF_NAV = [
  { to: '/dashboard', label: 'Tableau de bord', icon: '📊', permission: 'core.view_dashboard' },
  { to: '/patients', label: 'Patients', icon: '👥', permission: 'clinical.view_patient' },
  { to: '/admissions', label: 'Admissions', icon: '🛏️', permission: 'clinical.admit_patient' },
  { to: '/transfer-requests', label: 'Transferts à valider', icon: '📋', permission: 'clinical.validate_transfer' },
  { to: '/transfers', label: 'Transferts', icon: '🔄', permission: 'clinical.transfer' },
  { to: '/partner-hospitals', label: 'Hôpitaux partenaires', icon: '🏥', role: 'DOCTOR', permission: 'clinical.view_partner_hospitals' },
  { to: '/consultations', label: 'Consultations', icon: '🩺', permission: 'clinical.consult' },
  { to: '/my-appointments', label: 'Mes rendez-vous', icon: '📅', permission: 'clinical.consult' },
  { to: '/nursing', label: 'Soins infirmiers', icon: '💉', permission: 'clinical.nursing_care' },
  { to: '/laboratory', label: 'Laboratoire', icon: '🔬', permission: 'lab.order', permissionAlt: 'lab.enter_results', permissionsAny: ['lab.validate_results', 'lab.publish_results'] },
  { to: '/billing', label: 'Facturation', icon: '💰', permission: 'billing.create_invoice' },
  { to: '/accounting', label: 'Comptabilité', icon: '📊', permission: 'billing.adjust' },
  { to: '/pharmacy', label: 'Pharmacie', icon: '💊', permission: 'pharmacy.manage_stock', permissionAlt: 'pharmacy.dispense' },
  { to: '/appointments', label: 'Rendez-vous patients', icon: '📅', permission: 'hr.review_appointments' },
  { to: '/hr', label: 'RH & plannings', icon: '🗓️', permission: 'hr.manage_schedule' },
  { to: '/documents', label: 'Documents', icon: '📄', permission: 'documents.view' },
]

export function usePermissions() {
  const auth = useAuthStore()

  const can = (permission, alt, role, anyPerms = []) => {
    if (role && auth.hasRole(role)) return true
    if (anyPerms.length && anyPerms.some((p) => auth.hasPerm(p))) return true
    if (!permission) return true
    if (auth.hasPerm(permission)) return true
    if (alt && auth.hasPerm(alt)) return true
    return false
  }

  const mainNav = computed(() =>
    STAFF_NAV.filter((item) => can(item.permission, item.permissionAlt, item.role, item.permissionsAny || []))
  )

  return { can, mainNav, STAFF_NAV }
}
