import axios from 'axios'

const mainApi = axios.create({ baseURL: '/api/v1' })

mainApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default mainApi
