<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <div class="flex items-center justify-between mb-6 gap-3 flex-wrap">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-white">Foydalanuvchilar</h1>
        <p class="text-surface-400 text-sm mt-1">Admin panel foydalanuvchilarini boshqarish</p>
      </div>
      <button @click="showCreate = true" class="btn-primary whitespace-nowrap">+ Foydalanuvchi qo'shish</button>
    </div>

    <!-- Desktop table -->
    <div class="card overflow-hidden hidden sm:block">
      <table class="w-full">
        <thead>
          <tr class="border-b border-surface-800">
            <th v-for="c in ['Foydalanuvchi', 'Email', 'Rol', '2FA', 'Oxirgi kirish', 'Holat']" :key="c"
              class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">{{ c }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="text-center py-16">
              <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            </td>
          </tr>
          <tr v-for="u in users" :key="u.id" class="border-b border-surface-800/50 hover:bg-surface-800/20 transition-colors">
            <td class="px-5 py-4">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center text-white text-xs font-bold">
                  {{ (u.full_name || u.username)[0].toUpperCase() }}
                </div>
                <div>
                  <div class="text-white text-sm font-medium">{{ u.full_name || u.username }}</div>
                  <div class="text-surface-500 text-xs">@{{ u.username }}</div>
                </div>
              </div>
            </td>
            <td class="px-5 py-4 text-surface-300 text-sm">{{ u.email }}</td>
            <td class="px-5 py-4"><span :class="roleClass(u.role)" class="badge">{{ roleLabel(u.role) }}</span></td>
            <td class="px-5 py-4">
              <span :class="u.totp_enabled ? 'text-green-400' : 'text-surface-600'" class="text-sm">
                {{ u.totp_enabled ? '✓ Yoqilgan' : '✗ Yoqilmagan' }}
              </span>
            </td>
            <td class="px-5 py-4 text-surface-400 text-sm">{{ u.last_login ? formatDate(u.last_login) : 'Hech qachon' }}</td>
            <td class="px-5 py-4">
              <span :class="u.is_active ? 'text-green-400' : 'text-red-400'" class="text-sm">
                {{ u.is_active ? '● Faol' : '○ Nofaol' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile card list -->
    <div class="sm:hidden space-y-3">
      <div v-if="loading" class="card p-8 text-center">
        <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      </div>
      <div v-for="u in users" :key="u.id" class="card p-4">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            {{ (u.full_name || u.username)[0].toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-white text-sm font-medium truncate">{{ u.full_name || u.username }}</div>
            <div class="text-surface-500 text-xs">{{ u.email }}</div>
          </div>
          <span :class="u.is_active ? 'text-green-400' : 'text-red-400'" class="text-xs flex-shrink-0">
            {{ u.is_active ? '● Faol' : '○ Nofaol' }}
          </span>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <span :class="roleClass(u.role)" class="badge">{{ roleLabel(u.role) }}</span>
          <span :class="u.totp_enabled ? 'text-green-400' : 'text-surface-600'" class="text-xs">
            {{ u.totp_enabled ? '🔐 2FA yoqilgan' : '2FA yoqilmagan' }}
          </span>
          <span class="text-surface-500 text-xs ml-auto">{{ u.last_login ? formatDate(u.last_login) : 'Hech qachon' }}</span>
        </div>
      </div>
    </div>

    <!-- Create user modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-md animate-slide-up">
        <div class="p-6 border-b border-surface-800 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-white">Yangi foydalanuvchi</h2>
          <button @click="showCreate = false" class="text-surface-400 hover:text-white">✕</button>
        </div>
        <form @submit.prevent="createUser" class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">Foydalanuvchi nomi *</label>
            <input v-model="newUser.username" class="input" placeholder="john.doe" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">To'liq ism</label>
            <input v-model="newUser.full_name" class="input" placeholder="John Doe" />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">Email *</label>
            <input v-model="newUser.email" class="input" type="email" placeholder="john@company.uz" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">Parol *</label>
            <input v-model="newUser.password" class="input" type="password" placeholder="Kuchli parol" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">Rol *</label>
            <select v-model="newUser.role" class="input">
              <option value="viewer">👁 Viewer (faqat ko'rish)</option>
              <option value="investigator">🔍 Investigator (ko'rish + amal)</option>
              <option value="admin">👑 Admin (to'liq huquq)</option>
            </select>
          </div>
          <div class="flex gap-3 pt-2">
            <button type="button" @click="showCreate = false" class="btn-ghost flex-1">Bekor qilish</button>
            <button type="submit" :disabled="saving" class="btn-primary flex-1 justify-center">
              {{ saving ? 'Saqlanmoqda...' : 'Yaratish' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { format } from 'date-fns'
import api from '@/utils/api'

const loading = ref(true)
const saving = ref(false)
const showCreate = ref(false)
const users = ref([])
const newUser = reactive({ username: '', email: '', full_name: '', password: '', role: 'viewer' })

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/v1/auth/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

async function createUser() {
  saving.value = true
  try {
    await api.post('/v1/auth/users', newUser)
    showCreate.value = false
    Object.assign(newUser, { username: '', email: '', full_name: '', password: '', role: 'viewer' })
    await loadUsers()
  } finally {
    saving.value = false
  }
}

function roleClass(r) {
  return r === 'admin' ? 'bg-brand-500/15 text-brand-400 border border-brand-500/20'
    : r === 'investigator' ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
    : 'bg-surface-700/50 text-surface-400'
}
function roleLabel(r) {
  return r === 'admin' ? '👑 Admin' : r === 'investigator' ? '🔍 Investigator' : '👁 Viewer'
}
function formatDate(d) { return d ? format(new Date(d), 'dd.MM.yyyy HH:mm') : '—' }

onMounted(loadUsers)
</script>
