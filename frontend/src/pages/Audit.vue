<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 gap-3 flex-wrap">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-white">Audit jurnali</h1>
        <p class="text-surface-400 text-sm mt-1">Tizimda bajarilgan barcha amallar</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="exportExcel" :disabled="exporting" class="btn-ghost text-sm flex items-center gap-2 whitespace-nowrap">
          <span :class="{ 'animate-spin': exporting }">📥</span> Excel
        </button>
        <button @click="loadLogs" class="btn-ghost text-sm flex items-center gap-2 whitespace-nowrap">
          <span :class="{ 'animate-spin': loading }">🔄</span> Yangilash
        </button>
      </div>
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
        <input
          v-model="filters.from_date"
          type="date"
          class="input flex-1 min-w-40"
          placeholder="Boshlanish sanasi"
          @change="resetAndLoad"
        />
        <input
          v-model="filters.to_date"
          type="date"
          class="input flex-1 min-w-40"
          placeholder="Tugash sanasi"
          @change="resetAndLoad"
        />
        <button @click="clearFilters" class="btn-ghost text-sm whitespace-nowrap">Filtrni tozalash</button>
      </div>
    </div>

    <!-- Desktop table -->
    <div ref="tableRef" class="card overflow-hidden hidden sm:block">
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
            <!-- Skeleton loading -->
            <template v-if="loading">
              <tr v-for="i in 5" :key="'sk-' + i" class="border-b border-surface-800/50">
                <td class="px-5 py-3.5">
                  <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-full bg-surface-700 animate-pulse"></div>
                    <div class="space-y-1.5">
                      <div class="h-3.5 w-24 bg-surface-700 rounded animate-pulse"></div>
                      <div class="h-2.5 w-16 bg-surface-800 rounded animate-pulse"></div>
                    </div>
                  </div>
                </td>
                <td class="px-5 py-3.5"><div class="h-6 w-20 bg-surface-700 rounded-full animate-pulse"></div></td>
                <td class="px-5 py-3.5"><div class="h-3.5 w-20 bg-surface-700 rounded animate-pulse"></div></td>
                <td class="px-5 py-3.5"><div class="h-3.5 w-24 bg-surface-700 rounded animate-pulse"></div></td>
                <td class="px-5 py-3.5">
                  <div class="space-y-1.5">
                    <div class="h-3.5 w-20 bg-surface-700 rounded animate-pulse"></div>
                    <div class="h-2.5 w-16 bg-surface-800 rounded animate-pulse"></div>
                  </div>
                </td>
              </tr>
            </template>

            <!-- Empty state -->
            <tr v-else-if="!logs.length">
              <td colspan="5">
                <EmptyState
                  :icon="hasAuditFilters ? '🔍' : '📋'"
                  :title="hasAuditFilters ? 'Natija topilmadi' : 'Hech qanday yozuv topilmadi'"
                  :description="hasAuditFilters ? 'Ushbu filtrlar bo\'yicha yozuv topilmadi' : 'Audit jurnali hali bo\'sh'"
                  :action="hasAuditFilters ? 'Filterni tozalash' : ''"
                  :action-fn="hasAuditFilters ? resetFilters : null" />
              </td>
            </tr>

            <!-- Data rows -->
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
      <Pagination
        v-if="!loading && pagination.pages > 0"
        v-model="pagination"
        @change="onPageChange"
      />
    </div>

    <!-- Mobile card list -->
    <div class="sm:hidden space-y-3">
      <!-- Skeleton loading -->
      <template v-if="loading">
        <div v-for="i in 5" :key="'msk-' + i" class="card p-4">
          <div class="flex items-start justify-between gap-3 mb-2">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-full bg-surface-700 animate-pulse"></div>
              <div class="space-y-1.5">
                <div class="h-3.5 w-24 bg-surface-700 rounded animate-pulse"></div>
                <div class="h-2.5 w-16 bg-surface-800 rounded animate-pulse"></div>
              </div>
            </div>
            <div class="space-y-1.5 text-right">
              <div class="h-2.5 w-16 bg-surface-700 rounded animate-pulse ml-auto"></div>
              <div class="h-2.5 w-12 bg-surface-800 rounded animate-pulse ml-auto"></div>
            </div>
          </div>
          <div class="h-5 w-24 bg-surface-700 rounded-full animate-pulse"></div>
        </div>
      </template>

      <EmptyState v-else-if="!logs.length"
        :icon="hasAuditFilters ? '🔍' : '📋'"
        :title="hasAuditFilters ? 'Natija topilmadi' : 'Hech qanday yozuv topilmadi'"
        :description="hasAuditFilters ? 'Ushbu filtrlar bo\'yicha yozuv topilmadi' : ''"
        :action="hasAuditFilters ? 'Filterni tozalash' : ''"
        :action-fn="hasAuditFilters ? resetFilters : null" />
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

      <!-- Mobile Pagination -->
      <Pagination
        v-if="!loading && pagination.pages > 0"
        v-model="pagination"
        @change="onPageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'
import Pagination from '@/components/Pagination.vue'
import EmptyState from '@/components/EmptyState.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const exporting = ref(false)
const logs = ref([])
const actions = ref([])
const users = ref([])
const tableRef = ref(null)

const pagination = reactive({
  page: 1,
  per_page: 50,
  total: 0,
  pages: 0,
})

const filters = reactive({
  action: '',
  user_id: '',
  from_date: '',
  to_date: '',
})

const hasAuditFilters = computed(() =>
  !!(filters.action || filters.user_id || filters.from_date || filters.to_date)
)

function resetFilters() {
  filters.action = ''; filters.user_id = ''; filters.from_date = ''; filters.to_date = ''
  pagination.page = 1; loadLogs()
}

const columns = ['Foydalanuvchi', 'Amal', 'Murojaat / Ob\'ekt', 'IP manzil', 'Vaqt']

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

// ── URL Sync ──────────────────────────────────────────────────────────

function readFromURL() {
  const q = route.query
  if (q.page)      pagination.page     = Number(q.page)
  if (q.per_page)  pagination.per_page = Number(q.per_page)
  if (q.action)    filters.action      = String(q.action)
  if (q.user_id)   filters.user_id     = String(q.user_id)
  if (q.from_date) filters.from_date   = String(q.from_date)
  if (q.to_date)   filters.to_date     = String(q.to_date)
}

function syncToURL() {
  const query = {}
  if (pagination.page > 1)          query.page      = String(pagination.page)
  if (pagination.per_page !== 50)   query.per_page   = String(pagination.per_page)
  if (filters.action)               query.action     = filters.action
  if (filters.user_id)              query.user_id    = filters.user_id
  if (filters.from_date)            query.from_date  = filters.from_date
  if (filters.to_date)              query.to_date    = filters.to_date

  router.replace({ query }).catch(() => {})
}

// ── API calls ─────────────────────────────────────────────────────────

function buildParams() {
  const params = { page: pagination.page, per_page: pagination.per_page }
  if (filters.action)    params.action    = filters.action
  if (filters.user_id)   params.user_id   = filters.user_id
  if (filters.from_date) params.from_date = filters.from_date
  if (filters.to_date)   params.to_date   = filters.to_date
  return params
}

async function loadLogs() {
  loading.value = true
  try {
    const { data } = await api.get('/v1/audit', { params: buildParams() })
    logs.value         = data.items
    pagination.total   = data.total
    pagination.pages   = data.pages
    syncToURL()
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
  pagination.page = 1
  loadLogs()
}

function clearFilters() {
  filters.action    = ''
  filters.user_id   = ''
  filters.from_date = ''
  filters.to_date   = ''
  resetAndLoad()
}

function onPageChange() {
  loadLogs()
  // Jadval tepasiga scroll
  if (tableRef.value) {
    tableRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

async function exportExcel() {
  exporting.value = true
  try {
    const params = { ...buildParams(), format: 'xlsx' }
    delete params.page
    delete params.per_page
    const response = await api.get('/v1/audit/export', {
      params,
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const disposition = response.headers['content-disposition']
    const filename = disposition
      ? disposition.split('filename=')[1]?.replace(/"/g, '')
      : 'audit_log.xlsx'
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Eksport xatolik:', e)
  } finally {
    exporting.value = false
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────

onMounted(() => {
  readFromURL()
  loadMeta()
  loadLogs()
})
</script>
