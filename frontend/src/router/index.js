import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

function permMeta(permission, permissionAlt, role, permissionsAny = []) {
  return { permission, permissionAlt, role, permissionsAny }
}

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { public: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
    props: { portal: 'staff' },
  },
  {
    path: '/patient/register',
    name: 'patient-register',
    component: () => import('../views/patient/PatientRegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/patient/verify',
    name: 'patient-verify',
    component: () => import('../views/patient/PatientVerifyView.vue'),
    meta: { guest: true },
  },
  {
    path: '/patient/login',
    name: 'patient-login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
    props: { portal: 'patient' },
  },
  {
    path: '/patient/qr',
    name: 'patient-qr-scan',
    component: () => import('../views/patient/PatientQrScanView.vue'),
    meta: { public: true },
  },
  {
    path: '/patient',
    component: () => import('../layouts/PatientLayout.vue'),
    meta: { requiresAuth: true, requiresPatient: true },
    children: [
      { path: '', name: 'patient-home', component: () => import('../views/patient/PatientHomeView.vue') },
      { path: 'discover', name: 'patient-discover', component: () => import('../views/patient/PatientDiscoverView.vue') },
      { path: 'services', name: 'patient-services', component: () => import('../views/patient/PatientServicesView.vue') },
      { path: 'doctors', name: 'patient-doctors', component: () => import('../views/patient/PatientDoctorsView.vue') },
      { path: 'appointments', name: 'patient-appointments', component: () => import('../views/patient/PatientAppointmentsView.vue') },
      { path: 'records', name: 'patient-records', component: () => import('../views/patient/PatientRecordsView.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/AppLayout.vue'),
    meta: { requiresAuth: true, requiresStaff: true },
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('../views/DashboardView.vue'),
        meta: permMeta('core.view_dashboard'),
      },
      {
        path: 'patients',
        name: 'patients',
        component: () => import('../views/PatientsView.vue'),
        meta: permMeta('clinical.view_patient'),
      },
      {
        path: 'admissions',
        name: 'admissions',
        component: () => import('../views/AdmissionsView.vue'),
        meta: permMeta('clinical.admit_patient'),
      },
      {
        path: 'transfer-requests',
        name: 'transfer-requests',
        component: () => import('../views/TransferRequestsView.vue'),
        meta: permMeta('clinical.validate_transfer'),
      },
      {
        path: 'transfers',
        name: 'transfers',
        component: () => import('../views/TransfersView.vue'),
        meta: permMeta('clinical.transfer'),
      },
      {
        path: 'partner-hospitals',
        name: 'partner-hospitals',
        component: () => import('../views/PartnerHospitalsView.vue'),
        meta: permMeta('clinical.view_partner_hospitals', null, 'DOCTOR'),
      },
      {
        path: 'consultations',
        name: 'consultations',
        component: () => import('../views/ConsultationsView.vue'),
        meta: permMeta('clinical.consult'),
      },
      {
        path: 'my-appointments',
        name: 'my-appointments',
        component: () => import('../views/DoctorAppointmentsView.vue'),
        meta: permMeta('clinical.consult'),
      },
      {
        path: 'nursing',
        name: 'nursing',
        component: () => import('../views/NursingView.vue'),
        meta: permMeta('clinical.nursing_care'),
      },
      {
        path: 'laboratory',
        name: 'laboratory',
        component: () => import('../views/LaboratoryView.vue'),
        meta: permMeta('lab.order', 'lab.enter_results', null, ['lab.validate_results', 'lab.publish_results']),
      },
      {
        path: 'billing',
        name: 'billing',
        component: () => import('../views/BillingView.vue'),
        meta: permMeta('billing.create_invoice'),
      },
      {
        path: 'accounting',
        name: 'accounting',
        component: () => import('../views/AccountingView.vue'),
        meta: permMeta('billing.adjust'),
      },
      {
        path: 'pharmacy',
        name: 'pharmacy',
        component: () => import('../views/PharmacyView.vue'),
        meta: permMeta('pharmacy.manage_stock', 'pharmacy.dispense'),
      },
      {
        path: 'appointments',
        name: 'appointments',
        component: () => import('../views/AppointmentsView.vue'),
        meta: permMeta('hr.review_appointments'),
      },
      {
        path: 'hr',
        name: 'hr',
        component: () => import('../views/HrView.vue'),
        meta: permMeta('hr.manage_schedule'),
      },
      {
        path: 'documents',
        name: 'documents',
        component: () => import('../views/DocumentsView.vue'),
        meta: permMeta('documents.view'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function allowedByPerm(auth, meta) {
  if (meta.role && auth.hasRole(meta.role)) return true
  if (meta.permissionsAny?.some((p) => auth.hasPerm(p))) return true
  if (!meta.permission) return true
  if (auth.hasPerm(meta.permission)) return true
  if (meta.permissionAlt && auth.hasPerm(meta.permissionAlt)) return true
  return false
}

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.public) return true

  if (to.meta.guest && auth.isAuthenticated) {
    if (auth.isPatient) return { name: 'patient-home' }
    return { name: 'dashboard' }
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    const loginRoute = to.meta.requiresPatient ? 'patient-login' : 'login'
    return { name: loginRoute, query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresStaff && auth.isAuthenticated && !auth.isStaff) {
    if (auth.isPatient) return { name: 'patient-home' }
    return { name: 'home' }
  }

  if (to.meta.requiresPatient && auth.isAuthenticated && !auth.isPatient) {
    if (auth.isStaff) return { name: 'dashboard' }
    return { name: 'home' }
  }

  if ((to.meta.permission || to.meta.role || to.meta.permissionsAny?.length) && !allowedByPerm(auth, to.meta)) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
