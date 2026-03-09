<template>
  <div class="min-h-screen bg-surface-950 flex items-center justify-center p-4 relative overflow-hidden">
    <!-- Background decoration -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-96 h-96 bg-brand-800/10 rounded-full blur-3xl"></div>
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-900/5 rounded-full blur-3xl"></div>
    </div>

    <div class="w-full max-w-md relative animate-fade-in">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-brand-600 rounded-2xl mb-4 shadow-glow">
          <svg class="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">{{ t('login.title') }}</h1>
        <p class="text-surface-400 text-sm mt-1">{{ t('login.subtitle') }}</p>
      </div>

      <!-- Login card -->
      <div class="card p-8 shadow-2xl">
        <h2 class="text-lg font-semibold text-white mb-6">{{ t('login.heading') }}</h2>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('login.username') }}</label>
            <input v-model="form.username" type="text" class="input" placeholder="admin"
              autocomplete="username" required />
          </div>

          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('login.password') }}</label>
            <div class="relative">
              <input v-model="form.password" :type="showPassword ? 'text' : 'password'"
                class="input pr-10" placeholder="••••••••" autocomplete="current-password" required />
              <button type="button" @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-white transition-colors">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path v-if="showPassword" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 2FA code (shown after first attempt if needed) -->
          <div v-if="requires2FA">
            <label class="block text-sm font-medium text-surface-300 mb-2">
              🔐 {{ t('login.totp_label') }}
            </label>
            <input
              v-model="form.totpCode"
              ref="totpInput"
              type="text"
              class="input font-mono tracking-widest text-center text-lg"
              placeholder="000 000"
              maxlength="6"
              inputmode="numeric"
              autocomplete="one-time-code"
              @input="onTotpInput"
            />
            <p class="text-surface-500 text-xs mt-1.5 text-center">
              {{ t('login.totp_hint') }}
            </p>
          </div>

          <!-- Error -->
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
            {{ loading ? t('login.loading') : t('login.login_btn') }}
          </button>
          <div class="text-center mt-3">
            <router-link to="/forgot-password"
              class="text-brand-400 hover:text-brand-300 text-sm transition-colors">
              {{ t('login.forgot_password') }}
            </router-link>
          </div>
        </form>
      </div>

      <p class="text-center text-surface-600 text-xs mt-6">
        {{ t('login.copyright', { year: new Date().getFullYear() }) }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()

const form = reactive({ username: '', password: '', totpCode: '' })
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const requires2FA = ref(false)
const totpInput = ref(null)

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.username, form.password, requires2FA.value ? form.totpCode : null)
    router.push('/dashboard')
  } catch (err) {
    const detail = err.response?.data?.detail || ''
    const has2FAHeader = err.response?.headers?.['x-2fa-required'] === 'true'
    const is2FAError = has2FAHeader || detail.toLowerCase().includes('2fa')

    if (is2FAError) {
      requires2FA.value = true
      form.totpCode = ''
      error.value = t('login.error_2fa')
      // 2FA input ga focus
      await nextTick()
      totpInput.value?.focus()
    } else if (err.response?.status === 401) {
      requires2FA.value = false
      error.value = t('login.error_invalid')
    } else {
      error.value = detail || t('login.error_generic')
    }
  } finally {
    loading.value = false
  }
}

// 6 ta raqam kiritilganda avtomatik submit
function onTotpInput() {
  const digits = form.totpCode.replace(/\D/g, '').slice(0, 6)
  form.totpCode = digits
  if (digits.length === 6 && !loading.value) {
    handleLogin()
  }
}
</script>
