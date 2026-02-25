<template>
  <div class="p-8 animate-fade-in max-w-2xl">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white">Sozlamalar</h1>
      <p class="text-surface-400 text-sm mt-1">Profil va xavfsizlik sozlamalari</p>
    </div>

    <!-- Profile card -->
    <div class="card p-6 mb-6">
      <h3 class="font-semibold text-white mb-5">Profil ma'lumotlari</h3>
      <div class="flex items-center gap-4 mb-6">
        <div class="w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl flex items-center justify-center text-2xl text-white font-bold">
          {{ initials }}
        </div>
        <div>
          <div class="text-white font-semibold text-lg">{{ auth.user?.fullName || auth.user?.username }}</div>
          <div class="text-surface-400 text-sm capitalize">{{ auth.user?.role }}</div>
        </div>
      </div>
    </div>

    <!-- 2FA card -->
    <div class="card p-6 mb-6">
      <div class="flex items-start justify-between mb-5">
        <div>
          <h3 class="font-semibold text-white">Ikki bosqichli autentifikatsiya (2FA)</h3>
          <p class="text-surface-500 text-sm mt-1">Akkauntingizni yanada xavfsiz qiling</p>
        </div>
        <span :class="auth.user?.totpEnabled ? 'bg-green-500/15 text-green-400 border border-green-500/20' : 'bg-surface-700/50 text-surface-400'"
          class="badge">
          {{ auth.user?.totpEnabled ? '● Yoqilgan' : 'Yoqilmagan' }}
        </span>
      </div>

      <template v-if="!auth.user?.totpEnabled">
        <p class="text-surface-400 text-sm mb-4">
          Google Authenticator, Authy yoki boshqa TOTP ilovasidan foydalanib 2FA yoqing.
        </p>
        <button v-if="!setupData" @click="setup2FA" :disabled="loading" class="btn-primary">
          {{ loading ? 'Yuklanmoqda...' : '2FA ni yoqish' }}
        </button>

        <div v-if="setupData" class="mt-5 space-y-5">
          <div class="bg-white p-4 rounded-2xl w-fit">
            <img :src="setupData.qr_code" alt="QR kod" class="w-48 h-48" />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">QR kodni skaner qilib bo'lgach, kodni kiriting:</label>
            <div class="flex gap-3">
              <input v-model="totpCode" class="input font-mono tracking-widest text-center w-40" placeholder="000000" maxlength="6" />
              <button @click="verify2FA" :disabled="!totpCode || verifying" class="btn-primary">
                {{ verifying ? '...' : 'Tasdiqlash' }}
              </button>
            </div>
          </div>
          <div v-if="setupError" class="text-red-400 text-sm">{{ setupError }}</div>
        </div>
      </template>

      <div v-else class="space-y-4">
        <p class="text-surface-400 text-sm">
          2FA yoqilgan. Har safar kirishda Authenticator ilovasidan kod kerak bo'ladi.
        </p>
        <div v-if="!showDisable2FA">
          <button @click="showDisable2FA = true" class="btn-danger text-sm">
            🔓 2FA ni o'chirish
          </button>
        </div>
        <div v-else class="space-y-3 p-4 bg-red-500/5 border border-red-500/20 rounded-xl">
          <p class="text-red-400 text-sm font-medium">⚠️ O'chirish uchun Authenticator kodingizni kiriting:</p>
          <div class="flex gap-3">
            <input v-model="disableTotpCode" type="text" inputmode="numeric"
              class="input font-mono tracking-widest text-center w-40"
              placeholder="000000" maxlength="6" />
            <button @click="disable2FA" :disabled="!disableTotpCode || disabling" class="btn-danger">
              {{ disabling ? '...' : 'O\'chirish' }}
            </button>
            <button @click="showDisable2FA = false; disableTotpCode = ''; disableError = ''" class="btn-ghost">
              Bekor
            </button>
          </div>
          <div v-if="disableError" class="text-red-400 text-sm">{{ disableError }}</div>
        </div>
      </div>
    </div>

    <!-- Webhook info -->
    <div class="card p-6">
      <h3 class="font-semibold text-white mb-4">Telegram Bot</h3>
      <p class="text-surface-400 text-sm mb-4">Webhook manzilini Telegram ga ulash uchun quyidagi tugmani bosing.</p>
      <button @click="setWebhook" :disabled="webhookLoading" class="btn-ghost text-sm">
        {{ webhookLoading ? '...' : '🔗 Webhook ulash' }}
      </button>
      <div v-if="webhookMsg" :class="webhookMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm mt-3">
        {{ webhookMsg.text }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

const auth = useAuthStore()
const loading = ref(false)
const verifying = ref(false)
const webhookLoading = ref(false)
const setupData = ref(null)
const totpCode = ref('')
const setupError = ref('')
const webhookMsg = ref(null)
const showDisable2FA = ref(false)
const disableTotpCode = ref('')
const disableError = ref('')
const disabling = ref(false)

const initials = computed(() => {
  const name = auth.user?.fullName || auth.user?.username || 'U'
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
})

async function setup2FA() {
  loading.value = true
  try {
    const { data } = await api.post('/v1/auth/setup-2fa')
    setupData.value = data
  } finally {
    loading.value = false
  }
}

async function verify2FA() {
  verifying.value = true
  setupError.value = ''
  try {
    await api.post('/v1/auth/verify-2fa', { code: totpCode.value })
    auth.user.totpEnabled = true
    setupData.value = null
    totpCode.value = ''
  } catch {
    setupError.value = 'Noto\'g\'ri kod. Qayta urinib ko\'ring.'
  } finally {
    verifying.value = false
  }
}

async function disable2FA() {
  disabling.value = true
  disableError.value = ''
  try {
    await api.post('/v1/auth/disable-2fa', { code: disableTotpCode.value })
    auth.user.totpEnabled = false
    showDisable2FA.value = false
    disableTotpCode.value = ''
  } catch (e) {
    disableError.value = e.response?.data?.detail === 'Invalid 2FA code'
      ? 'Noto\'g\'ri kod. Qayta urinib ko\'ring.'
      : (e.response?.data?.detail || 'Xatolik yuz berdi')
  } finally {
    disabling.value = false
  }
}

async function setWebhook() {
  webhookLoading.value = true
  webhookMsg.value = null
  try {
    await api.post('/telegram/set-webhook')
    webhookMsg.value = { ok: true, text: '✅ Webhook muvaffaqiyatli ulandi!' }
  } catch (e) {
    webhookMsg.value = { ok: false, text: '❌ Xatolik: ' + (e.response?.data?.detail || e.message) }
  } finally {
    webhookLoading.value = false
  }
}
</script>
