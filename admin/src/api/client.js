import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1/admin' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_access_token')
      const base = import.meta.env.BASE_URL
      window.location.href = base.endsWith('/') ? `${base}login` : `${base}/login`
    }
    return Promise.reject(error)
  }
)

export default api
