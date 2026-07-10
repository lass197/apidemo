import { defineStore } from 'pinia'
import api from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('admin_user') || 'null'),
    token: localStorage.getItem('admin_access_token'),
  }),
  getters: {
    isAuthenticated: (s) => !!s.token,
    isAdmin: (s) => s.user?.roles?.includes('ADMIN'),
    permissions: (s) => s.user?.permissions || [],
    hasPerm: (s) => (codename) => s.user?.permissions?.includes(codename) ?? false,
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post('/auth/login/', { username, password })
      if (!data.user.roles.includes('ADMIN')) {
        throw new Error('Accès réservé aux administrateurs.')
      }
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('admin_access_token', data.access_token)
      localStorage.setItem('admin_refresh_token', data.refresh_token)
      localStorage.setItem('admin_user', JSON.stringify(data.user))
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('admin_access_token')
      localStorage.removeItem('admin_refresh_token')
      localStorage.removeItem('admin_user')
    },
  },
})
