import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

// ── Progress bar hook ────────────────────────────────────
let _progressBar = null
export function setProgressBar(bar) { _progressBar = bar }

api.interceptors.request.use(config => {
  _progressBar?.start()
  return config
}, err => {
  _progressBar?.finish()
  return Promise.reject(err)
})

api.interceptors.response.use(
  res => {
    _progressBar?.finish()
    return res
  },
  err => {
    _progressBar?.finish()
    const status = err.response?.status
    const isLoginEndpoint = err.config?.url?.includes('/auth/token')

    // Login sahifasida yoki login so'rovida redirect qilmaymiz —
    // aks holda 2FA paytida refresh loop yuz beradi
    if (status === 401 && !isLoginEndpoint && window.location.pathname !== '/login') {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }

    // Global error page redirect — faqat sahifa so'rovlari uchun
    // (fon so'rovlari, eksport, va boshqalar uchun emas)
    if (!err.config?._skipErrorRedirect) {
      if (status === 403 && !isLoginEndpoint) {
        window.location.href = '/403'
      } else if (status === 429) {
        window.location.href = '/429'
      } else if (status === 502) {
        window.location.href = '/502'
      } else if (status === 503) {
        window.location.href = '/503'
      }
    }

    return Promise.reject(err)
  }
)

export default api
