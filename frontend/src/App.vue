<template>
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
            <h2 class="text-xl font-bold text-white">Parolni o'zgartiring</h2>
            <p class="text-amber-400 text-sm mt-2">
              Xavfsizlik uchun dastlabki parolni o'zgartirish majburiy
            </p>
          </div>

          <!-- Form -->
          <div class="space-y-4">
            <div>
              <label class="text-surface-400 text-sm mb-1 block">Yangi parol</label>
              <input
                v-model="newPassword"
                type="password"
                class="input w-full"
                placeholder="Kamida 8 belgi"
                @keyup.enter="confirmFocus"
                ref="newPassRef"
              />
            </div>
            <div>
              <label class="text-surface-400 text-sm mb-1 block">Yangi parolni tasdiqlang</label>
              <input
                v-model="confirmPassword"
                type="password"
                class="input w-full"
                placeholder="Parolni qayta kiriting"
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
              <span v-if="changingPassword">⏳ Saqlanmoqda...</span>
              <span v-else>✅ Parolni saqlash</span>
            </button>
          </div>

          <p class="text-surface-600 text-xs text-center mt-4">
            Bu oynani yopib bo'lmaydi — parol o'zgartirilguncha
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { RouterView } from 'vue-router'
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

const authStore = useAuthStore()

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
    passwordError.value = 'Parol kamida 8 belgidan iborat bo\'lishi kerak'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'Parollar mos kelmadi'
    return
  }

  // Kuchli parol tekshiruvi
  const strong = /^(?=.*[A-Z])(?=.*[0-9]).{8,}$/
  if (!strong.test(newPassword.value)) {
    passwordError.value = 'Parolda kamida 1 ta katta harf va 1 ta raqam bo\'lishi kerak'
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
    passwordError.value = e.response?.data?.detail || 'Xato yuz berdi'
  } finally {
    changingPassword.value = false
  }
}
</script>
