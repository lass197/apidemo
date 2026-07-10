import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

const PUBLIC_AUTH_PATHS = ['/auth/login', '/auth/register', '/auth/refresh']

function isPublicAuthRequest(url = '') {
  return PUBLIC_AUTH_PATHS.some((p) => url.includes(p))
}

api.interceptors.request.use((config) => {
  if (!isPublicAuthRequest(config.url)) {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401 && !isPublicAuthRequest(error.config?.url)) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      const onPatient = window.location.pathname.startsWith('/patient')
      window.location.href = onPatient ? '/patient/login' : '/login'
    }
    return Promise.reject(error)
  }
)

export default api
