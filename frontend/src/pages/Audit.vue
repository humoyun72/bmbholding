<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 gap-3 flex-wrap">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-white">Audit jurnali</h1>
        <p class="text-surface-400 text-sm mt-1">Tizimda bajarilgan barcha amallar</p>
      </div>
      <button @click="loadLogs" class="btn-ghost text-sm flex items-center gap-2 whitespace-nowrap">
        <span :class="{ 'animate-spin': loading }">🔄</span> Yangilash
      </button>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-6">
      <div class="flex items-center gap-3 flex-wrap">
        <select v-model="filters.action" class="input flex-1 min-w-40" @change="resetAndLoad">
          <option value="">Barcha amallar</option>
          <option v-for="a in actions" :key="a" :value="a">{{ actionLabel(a) }}</option>
        </select>
        <select v-model="filters.user_id" class="input flex-1 min-w-40" @change="resetAndLoad">
          <option value="">Barcha foydalanuvchilar</option>
          <option v-for="u in users" :key="u.id" :value="u.id">{{ u.full_name || u.username }}</option>
        </select>
        <button @click="clearFilters" class="btn-ghost text-sm whitespace-nowrap">Filtrni tozalash</button>
      </div>
    </div>

    <!-- Desktop table -->
    <div class="card overflow-hidden hidden sm:block">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800">
              <th v-for="col in columns" :key="col"
                class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">
                {{ col }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="py-16 text-center">
                <div class="flex flex-col items-center gap-3">
                  <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
                  <span class="text-surface-500 text-sm">Yuklanmoqda...</span>
                </div>
              </td>
            </tr>
            <tr v-else-if="!logs.length">
              <td colspan="5" class="py-16 text-center text-surface-600 text-sm">
                Audit yozuvlari topilmadi
              </td>
            </tr>
            <tr v-else v-for="log in logs" :key="log.id"
              class="border-b border-surface-800/50 hover:bg-surface-800/30 transition-colors">
              <td class="px-5 py-3.5">
                <div v-if="log.user" class="flex items-center gap-2">
                  <div class="w-7 h-7 rounded-full bg-brand-600/30 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0">
                    {{ (log.user.full_name || log.user.username).charAt(0).toUpperCase() }}
                  </div>
                  <div class="min-w-0">
                    <div class="text-white text-sm font-medium truncate">{{ log.user.full_name || log.user.username }}</div>
                    <div class="text-surface-500 text-xs">{{ roleLabel(log.user.role) }}</div>
                  </div>
                </div>
                <span v-else class="text-surface-600 text-sm italic">Tizim</span>
              </td>
              <td class="px-5 py-3.5">
                <span :class="['inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium', actionBadge(log.action)]">
                  <span>{{ actionIcon(log.action) }}</span>
                  <span>{{ actionLabel(log.action) }}</span>
                </span>
              </td>
              <td class="px-5 py-3.5">
                <div v-if="log.case_id" class="text-brand-400 text-sm font-mono">
                  <router-link :to="`/cases/${log.case_id}`" class="hover:underline">#{{ log.case_id.slice(0, 8) }}</router-link>
                </div>
                <div v-else-if="log.entity_type" class="text-surface-400 text-sm">
                  {{ log.entity_type }}
                  <span v-if="log.entity_id" class="text-surface-600 font-mono ml-1 text-xs">#{{ log.entity_id.slice(0, 8) }}</span>
                </div>
                <span v-else class="text-surface-700 text-xs">—</span>
              </td>
              <td class="px-5 py-3.5">
                <span class="text-surface-400 text-sm font-mono">{{ log.ip_address || '—' }}</span>
              </td>
              <td class="px-5 py-3.5 whitespace-nowrap">
                <div class="text-white text-sm">{{ formatDate(log.created_at) }}</div>
                <div class="text-surface-500 text-xs">{{ formatTime(log.created_at) }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-between px-5 py-4 border-t border-surface-800 flex-wrap gap-3">
        <span class="text-surface-500 text-sm">Jami {{ total }} yozuv</span>
        <div class="flex items-center gap-2">
          <button @click="changePage(currentPage - 1)" :disabled="currentPage <= 1"
            class="btn-ghost text-sm disabled:opacity-30 disabled:cursor-not-allowed">← Oldingi</button>
          <span class="text-surface-400 text-sm">{{ currentPage }} / {{ totalPages }}</span>
          <button @click="changePage(currentPage + 1)" :disabled="currentPage >= totalPages"
            class="btn-ghost text-sm disabled:opacity-30 disabled:cursor-not-allowed">Keyingi →</button>
        </div>
      </div>
      <div v-else-if="!loading && logs.length" class="px-5 py-3 border-t border-surface-800">
        <span class="text-surface-500 text-sm">Jami {{ total }} yozuv</span>
      </div>
    </div>

    <!-- Mobile card list -->
    <div class="sm:hidden space-y-3">
      <div v-if="loading" class="card p-8 text-center">
        <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      </div>
      <div v-else-if="!logs.length" class="card p-8 text-center text-surface-600 text-sm">
        Audit yozuvlari topilmadi
      </div>
      <div v-else v-for="log in logs" :key="log.id" class="card p-4">
        <div class="flex items-start justify-between gap-3 mb-2">
          <div class="flex items-center gap-2">
            <div v-if="log.user" class="w-7 h-7 rounded-full bg-brand-600/30 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0">
              {{ (log.user.full_name || log.user.username).charAt(0).toUpperCase() }}
            </div>
            <div>
              <div class="text-white text-sm font-medium">{{ log.user ? (log.user.full_name || log.user.username) : 'Tizim' }}</div>
              <div class="text-surface-500 text-xs">{{ log.ip_address || '—' }}</div>
            </div>
          </div>
          <div class="text-right flex-shrink-0">
            <div class="text-surface-400 text-xs">{{ formatDate(log.created_at) }}</div>
            <div class="text-surface-600 text-xs">{{ formatTime(log.created_at) }}</div>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <span :class="['inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', actionBadge(log.action)]">
            {{ actionIcon(log.action) }} {{ actionLabel(log.action) }}
          </span>
          <router-link v-if="log.case_id" :to="`/cases/${log.case_id}`"
            class="text-brand-400 text-xs font-mono hover:underline">
            #{{ log.case_id.slice(0, 8) }}
          </router-link>
        </div>
      </div>
      <div v-if="totalPages > 1" class="flex items-center justify-center gap-3 py-2">
        <button @click="changePage(currentPage - 1)" :disabled="currentPage <= 1"
          class="btn-ghost text-sm disabled:opacity-30">← Oldingi</button>
        <span class="text-surface-400 text-sm">{{ currentPage }} / {{ totalPages }}</span>
        <button @click="changePage(currentPage + 1)" :disabled="currentPage >= totalPages"
          class="btn-ghost text-sm disabled:opacity-30">Keyingi →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/utils/api'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const perPage = 50
const actions = ref([])
const users = ref([])

const filters = ref({ action: '', user_id: '' })

const columns = ['Foydalanuvchi', 'Amal', 'Murojaat / Ob\'ekt', 'IP manzil', 'Vaqt']

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage)))
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const ACTION_META = {
  login:               { label: 'Kirish',        icon: '🔑', badge: 'bg-green-500/20 text-green-400' },
  logout:              { label: 'Chiqish',        icon: '🚪', badge: 'bg-surface-700 text-surface-400' },
  case_view:           { label: 'Ko\'rish',       icon: '👁',  badge: 'bg-blue-500/20 text-blue-400' },
  case_update:         { label: 'Yangilash',      icon: '✏️',  badge: 'bg-yellow-500/20 text-yellow-400' },
  case_assign:         { label: 'Tayinlash',      icon: '👤',  badge: 'bg-purple-500/20 text-purple-400' },
  case_comment:        { label: 'Izoh',           icon: '💬',  badge: 'bg-cyan-500/20 text-cyan-400' },
  case_export:         { label: 'Eksport',        icon: '📤',  badge: 'bg-orange-500/20 text-orange-400' },
  attachment_download: { label: 'Yuklash',        icon: '📎',  badge: 'bg-orange-500/20 text-orange-400' },
  user_create:         { label: 'Foydalanuvchi',  icon: '➕',  badge: 'bg-brand-500/20 text-brand-400' },
  user_update:         { label: 'Foydalanuvchi tahrirlash', icon: '🔧', badge: 'bg-brand-500/20 text-brand-400' },
  survey_create:       { label: 'So\'rovnoma',    icon: '📊',  badge: 'bg-pink-500/20 text-pink-400' },
}

function actionLabel(a) { return ACTION_META[a]?.label || a }
function actionIcon(a)  { return ACTION_META[a]?.icon  || '📌' }
function actionBadge(a) { return ACTION_META[a]?.badge || 'bg-surface-700 text-surface-400' }

const ROLE_LABELS = { admin: 'Admin', investigator: 'Tergovchi', viewer: 'Kuzatuvchi' }
function roleLabel(r) { return ROLE_LABELS[r] || r }

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('uz-UZ', { year: 'numeric', month: '2-digit', day: '2-digit' })
}
function formatTime(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function loadLogs() {
  loading.value = true
  try {
    const params = { page: currentPage.value, per_page: perPage }
    if (filters.value.action)  params.action  = filters.value.action
    if (filters.value.user_id) params.user_id = filters.value.user_id
    const { data } = await api.get('/v1/audit', { params })
    logs.value  = data.items
    total.value = data.total
  } catch (e) {
    console.error('Audit log yuklanmadi:', e)
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  try {
    const [actRes, usrRes] = await Promise.all([
      api.get('/v1/audit/actions'),
      api.get('/v1/auth/users'),
    ])
    actions.value = actRes.data
    users.value   = usrRes.data
  } catch (e) {
    console.error('Meta yuklanmadi:', e)
  }
}

function resetAndLoad() {
  currentPage.value = 1
  loadLogs()
}

function clearFilters() {
  filters.value = { action: '', user_id: '' }
  resetAndLoad()
}

function changePage(p) {
  if (p < 1 || p > totalPages.value) return
  currentPage.value = p
  loadLogs()
}

onMounted(() => {
  loadMeta()
  loadLogs()
})
</script>
