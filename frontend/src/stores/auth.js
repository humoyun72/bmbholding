import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/utils/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isInvestigator = computed(() =>
    ['admin', 'investigator'].includes(user.value?.role)
  )

  async function login(username, password, totpCode = null) {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    if (totpCode) formData.append('scopes', totpCode)

    const { data } = await api.post('/v1/auth/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    token.value = data.access_token
    user.value = {
      username: data.username,
      fullName: data.full_name,
      role: data.role,
      totpEnabled: data.totp_enabled,
    }

    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(user.value))
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    return data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    delete api.defaults.headers.common['Authorization']
  }

  // Restore auth header on app load
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  return { token, user, isAuthenticated, isAdmin, isInvestigator, login, logout }
})
