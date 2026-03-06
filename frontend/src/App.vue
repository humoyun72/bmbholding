<template>
  <TopProgressBar ref="progressBarRef" />

  <RouterView v-slot="{ Component }">
    <Transition name="page" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>

  <!-- ── Majburiy parol o'zgartirish modal ──────────────────────────── -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showForcePasswordModal"
        class="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <div class="bg-surface-900 border border-amber-500/30 rounded-2xl shadow-2xl w-full max-w-md p-8">
          <!-- Header -->
          <div class="text-center mb-6">
            <div class="text-4xl mb-3">🔐</div>
            <h2 class="text-xl font-bold text-white">{{ t('force_password.title') }}</h2>
            <p class="text-amber-400 text-sm mt-2">
              {{ t('force_password.desc') }}
            </p>
          </div>

          <!-- Form -->
          <div class="space-y-4">
            <div>
              <label class="text-surface-400 text-sm mb-1 block">{{ t('force_password.new_password') }}</label>
              <input
                v-model="newPassword"
                type="password"
                class="input w-full"
                :placeholder="t('force_password.placeholder_new')"
                @keyup.enter="confirmFocus"
                ref="newPassRef"
              />
            </div>
            <div>
              <label class="text-surface-400 text-sm mb-1 block">{{ t('force_password.confirm_password') }}</label>
              <input
                v-model="confirmPassword"
                type="password"
                class="input w-full"
                :placeholder="t('force_password.placeholder_confirm')"
                @keyup.enter="submitPasswordChange"
                ref="confirmRef"
              />
            </div>

            <div v-if="passwordError" class="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {{ passwordError }}
            </div>

            <button
              @click="submitPasswordChange"
              :disabled="changingPassword"
              class="btn-primary w-full py-3 mt-2 disabled:opacity-50">
              <span v-if="changingPassword">⏳ {{ t('force_password.saving') }}</span>
              <span v-else>✅ {{ t('force_password.save') }}</span>
            </button>
          </div>

          <p class="text-surface-600 text-xs text-center mt-4">
            {{ t('force_password.hint') }}
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { RouterView } from 'vue-router'
import { computed, ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api, { setProgressBar } from '@/utils/api'
import TopProgressBar from '@/components/TopProgressBar.vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const authStore = useAuthStore()
const progressBarRef = ref(null)

onMounted(() => {
  if (progressBarRef.value) setProgressBar(progressBarRef.value)
})

const showForcePasswordModal = computed(
  () => authStore.isAuthenticated && authStore.user?.forcePasswordChange === true
)

const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const changingPassword = ref(false)
const confirmRef = ref(null)

function confirmFocus() {
  confirmRef.value?.focus()
}

async function submitPasswordChange() {
  passwordError.value = ''

  if (newPassword.value.length < 8) {
    passwordError.value = t('force_password.error_min_length')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('force_password.error_mismatch')
    return
  }

  // Kuchli parol tekshiruvi
  const strong = /^(?=.*[A-Z])(?=.*[0-9]).{8,}$/
  if (!strong.test(newPassword.value)) {
    passwordError.value = t('force_password.error_weak')
    return
  }

  changingPassword.value = true
  try {
    await api.post('/v1/auth/change-password', { new_password: newPassword.value })
    // Store ni yangilash
    if (authStore.user) {
      authStore.user.forcePasswordChange = false
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e) {
    passwordError.value = e.response?.data?.detail || t('force_password.error_generic')
  } finally {
    changingPassword.value = false
  }
}
</script>
