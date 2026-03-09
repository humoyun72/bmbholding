<template>
  <div class="min-h-screen bg-surface-950 flex items-center justify-center p-4 relative overflow-hidden">
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-96 h-96 bg-brand-800/10 rounded-full blur-3xl"></div>
    </div>

    <div class="w-full max-w-md relative animate-fade-in">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-brand-600 rounded-2xl mb-4 shadow-glow">
          <svg class="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">{{ t('reset_password_page.title') }}</h1>
      </div>

      <div class="card p-8 shadow-2xl">
        <div v-if="!token" class="text-center space-y-4">
          <div class="w-16 h-16 bg-red-500/15 rounded-2xl flex items-center justify-center text-4xl mx-auto">⚠️</div>
          <p class="text-red-400 text-sm">{{ t('reset_password_page.error_invalid_token') }}</p>
          <router-link to="/login" class="btn-primary w-full justify-center block text-center py-2.5">
            {{ t('reset_password_page.back_login') }}
          </router-link>
        </div>

        <div v-else-if="success" class="text-center space-y-4">
          <div class="w-16 h-16 bg-green-500/15 rounded-2xl flex items-center justify-center text-4xl mx-auto">✅</div>
          <p class="text-surface-200 text-sm">{{ t('reset_password_page.success') }}</p>
          <router-link to="/login" class="btn-primary w-full justify-center block text-center py-2.5">
            {{ t('reset_password_page.back_login') }}
          </router-link>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">
              {{ t('reset_password_page.new_password_label') }}
            </label>
            <input v-model="newPassword" type="password" class="input w-full"
              :placeholder="t('reset_password_page.new_password_placeholder')"
              autocomplete="new-password" required />
          </div>

          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">
              {{ t('reset_password_page.confirm_password_label') }}
            </label>
            <input v-model="confirmPassword" type="password" class="input w-full"
              :placeholder="t('reset_password_page.confirm_password_placeholder')"
              autocomplete="new-password" required />
          </div>

          <div v-if="error" class="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
            <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ error }}
          </div>

          <button type="submit" class="btn-primary w-full justify-center py-3" :disabled="loading">
            <svg v-if="loading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            {{ loading ? t('reset_password_page.loading') : t('reset_password_page.submit_btn') }}
          </button>

          <div class="text-center">
            <router-link to="/login" class="text-surface-400 hover:text-surface-200 text-sm transition-colors">
              ← {{ t('reset_password_page.back_login') }}
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/utils/api'
import { useI18n } from '@/composables/useI18n'

const route = useRoute()
const { t } = useI18n()
const token = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

onMounted(() => {
  token.value = route.query.token || ''
})

async function handleSubmit() {
  error.value = ''
  if (newPassword.value.length < 8) {
    error.value = t('reset_password_page.error_min')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = t('reset_password_page.error_mismatch')
    return
  }
  loading.value = true
  try {
    await api.post('/v1/auth/reset-password', {
      token: token.value,
      new_password: newPassword.value,
    })
    success.value = true
  } catch (e) {
    const detail = e.response?.data?.detail || ''
    if (detail.toLowerCase().includes('yaroqsiz') || detail.toLowerCase().includes('invalid') || detail.toLowerCase().includes('token')) {
      error.value = t('reset_password_page.error_invalid_token')
    } else {
      error.value = detail || t('reset_password_page.error_generic')
    }
  } finally {
    loading.value = false
  }
}
</script>
