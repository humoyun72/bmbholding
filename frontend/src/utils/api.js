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
    const isLoginEndpoint = err.config?.url?.includes('/auth/token')
    const is401 = err.response?.status === 401

    // Login sahifasida yoki login so'rovida redirect qilmaymiz —
    // aks holda 2FA paytida refresh loop yuz beradi
    if (is401 && !isLoginEndpoint && window.location.pathname !== '/login') {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
