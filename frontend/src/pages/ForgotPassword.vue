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
              d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">{{ t('forgot_password_page.title') }}</h1>
        <p class="text-surface-400 text-sm mt-1">{{ t('forgot_password_page.subtitle') }}</p>
      </div>

      <div class="card p-8 shadow-2xl">
        <div v-if="success" class="text-center space-y-4">
          <div class="w-16 h-16 bg-green-500/15 rounded-2xl flex items-center justify-center text-4xl mx-auto">✅</div>
          <p class="text-surface-200 text-sm">{{ t('forgot_password_page.success') }}</p>
          <router-link to="/login" class="btn-primary w-full justify-center block text-center py-2.5">
            {{ t('forgot_password_page.back_login') }}
          </router-link>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">
              {{ t('forgot_password_page.email_label') }}
            </label>
            <input v-model="email" type="email" class="input w-full"
              :placeholder="t('forgot_password_page.email_placeholder')"
              autocomplete="email" required />
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
            {{ loading ? t('forgot_password_page.loading') : t('forgot_password_page.submit_btn') }}
          </button>

          <div class="text-center">
            <router-link to="/login" class="text-surface-400 hover:text-surface-200 text-sm transition-colors">
              ← {{ t('forgot_password_page.back_login') }}
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '@/utils/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const email = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    await api.post('/v1/auth/forgot-password', { email: email.value })
    success.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || t('forgot_password_page.error')
  } finally {
    loading.value = false
  }
}
</script>
