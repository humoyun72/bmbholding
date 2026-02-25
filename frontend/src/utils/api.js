import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  res => res,
  err => {
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
