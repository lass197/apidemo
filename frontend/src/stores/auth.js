import { defineStore } from 'pinia'
import api from '../api/client'

const STAFF_ROLES = ['SECRETARY', 'ACCOUNTANT', 'DOCTOR', 'NURSE', 'BIOLOGIST', 'PHARMACIST']

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    token: localStorage.getItem('access_token'),
    portal: localStorage.getItem('portal') || null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.token && !!s.user,
    roles: (s) => s.user?.roles || [],
    permissions: (s) => s.user?.permissions || [],
    isStaff: (s) => s.user?.roles?.some((r) => STAFF_ROLES.includes(r)) ?? false,
    isPatient: (s) => s.user?.roles?.includes('PATIENT') ?? false,
    isAdmin: (s) => s.user?.roles?.includes('ADMIN') ?? false,
    hasRole: (s) => (role) => s.user?.roles?.includes(role),
    hasPerm: (s) => (codename) => s.user?.permissions?.includes(codename) ?? false,
  },
  actions: {
    async login(username, password, portal = 'staff', mfaCode = null) {
      const payload = { username, password }
      if (mfaCode) payload.mfa_code = mfaCode
      const { data } = await api.post('/auth/login/', payload)

      if (portal === 'staff') {
        if (data.user.roles.includes('ADMIN') && !data.user.roles.some((r) => STAFF_ROLES.includes(r))) {
          throw new Error('Compte administrateur : utilisez /admin/')
        }
        if (!data.user.roles.some((r) => STAFF_ROLES.includes(r))) {
          if (data.user.roles.includes('PATIENT')) {
            throw new Error('Compte patient : utilisez l\'espace patient (/patient/login)')
          }
          throw new Error('Accès staff non autorisé pour ce compte.')
        }
      } else if (portal === 'patient') {
        if (!data.user.roles.includes('PATIENT')) {
          if (data.user.roles.includes('ADMIN')) {
            throw new Error('Compte admin : utilisez /admin/')
          }
          throw new Error('Espace réservé aux patients.')
        }
      }

      this.token = data.access_token
      this.user = data.user
      this.portal = portal
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      localStorage.setItem('portal', portal)
    },
    async restoreSession() {
      if (!this.token) return false
      try {
        const { data } = await api.get('/users/me/')
        this.user = data
        localStorage.setItem('user', JSON.stringify(data))
        return true
      } catch {
        this.logout()
        return false
      }
    },
    logout() {
      this.token = null
      this.user = null
      this.portal = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      localStorage.removeItem('portal')
    },
    setSession(data, portal) {
      this.token = data.access_token
      this.user = data.user
      this.portal = portal
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      localStorage.setItem('portal', portal)
    },
  },
})
