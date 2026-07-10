import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { guest: true } },
  {
    path: '/',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'users', component: () => import('../views/UsersView.vue') },
      { path: 'online-users', redirect: { path: '/users', query: { tab: 'sessions' } } },
      { path: 'roles', component: () => import('../views/RolesView.vue') },
      { path: 'audit', component: () => import('../views/AuditView.vue') },
      { path: 'clinical-movements', component: () => import('../views/ClinicalMovementsView.vue') },
      { path: 'security', component: () => import('../views/SecurityView.vue') },
      { path: 'infrastructure', component: () => import('../views/InfrastructureView.vue') },
      { path: 'appointments', component: () => import('../views/AppointmentsView.vue') },
      { path: 'accounting', component: () => import('../views/AccountingView.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(import.meta.env.BASE_URL), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/login'
  if (to.meta.requiresAdmin && !auth.isAdmin) return '/login'
  if (to.meta.guest && auth.isAuthenticated) return '/dashboard'
})

export default router
