import axios from 'axios'
import { useAuthStore } from '@/store/auth'
import router from '@/router'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach JWT token
http.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  if (authStore.user?.customer_id) {
    config.headers['X-Customer-Id'] = authStore.user.customer_id
  }
  return config
})

// Response interceptor — handle 401, refresh token
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      // Attempt token refresh
      try {
        const res = await axios.post('/api/v1/auth/refresh', {
          refresh_token: authStore.refreshToken,
        })
        authStore.token = res.data.access_token
        authStore.refreshToken = res.data.refresh_token
        localStorage.setItem('geoai_access_token', res.data.access_token)
        localStorage.setItem('geoai_refresh_token', res.data.refresh_token)
        // Retry original request
        error.config.headers.Authorization = `Bearer ${res.data.access_token}`
        return http(error.config)
      } catch {
        authStore.clearAuth()
        router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }
    return Promise.reject(error)
  }
)

export default http
