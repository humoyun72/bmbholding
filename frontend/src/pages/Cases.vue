<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 gap-3 flex-wrap">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-white">Murojaatlar</h1>
        <p class="text-surface-400 text-sm mt-1">Barcha kelgan murojaatlar ro'yxati</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-6 space-y-3">
      <div class="flex items-center gap-3 flex-wrap">
        <select v-model="filters.status" class="input flex-1 min-w-32" @change="onFilterChange">
          <option value="">Barcha holatlar</option>
          <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="filters.category" class="input flex-1 min-w-32" @change="onFilterChange">
          <option value="">Barcha kategoriyalar</option>
          <option v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
        <select v-model="filters.priority" class="input flex-1 min-w-32" @change="onFilterChange">
          <option value="">Barcha ustuvorliklar</option>
          <option v-for="p in priorityOptions" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
      </div>
      <!-- Date range + actions row -->
      <div class="flex items-center gap-3 flex-wrap">
        <div class="flex items-center gap-2 flex-1 min-w-48">
          <label class="text-surface-500 text-xs whitespace-nowrap">Dan:</label>
          <input type="date" v-model="filters.from_date" @change="onFilterChange"
            class="input flex-1 text-sm" />
        </div>
        <div class="flex items-center gap-2 flex-1 min-w-48">
          <label class="text-surface-500 text-xs whitespace-nowrap">Gacha:</label>
          <input type="date" v-model="filters.to_date" @change="onFilterChange"
            class="input flex-1 text-sm" />
        </div>
        <button @click="resetFilters" class="btn-ghost text-sm whitespace-nowrap">
          Filtrni tozalash
        </button>

        <!-- Export dropdown -->
        <div class="relative" ref="exportMenuRef">
          <button @click="exportOpen = !exportOpen"
            :disabled="exporting"
            class="btn-ghost text-sm whitespace-nowrap flex items-center gap-2 disabled:opacity-50">
            <svg v-if="exporting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span v-else>📥</span>
            Eksport
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
          <Transition name="dropdown">
            <div v-if="exportOpen"
              class="absolute right-0 top-full mt-1 w-48 bg-surface-800 border border-surface-700 rounded-xl shadow-xl z-50 overflow-hidden">
              <button @click="doExport('xlsx')"
                class="w-full text-left px-4 py-3 text-sm text-surface-200 hover:bg-surface-700 transition-colors flex items-center gap-2">
                <span>📊</span> Excel (.xlsx)
              </button>
              <button @click="doExport('pdf')"
                class="w-full text-left px-4 py-3 text-sm text-surface-200 hover:bg-surface-700 transition-colors flex items-center gap-2 border-t border-surface-700">
                <span>📄</span> PDF (.pdf)
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show"
          class="fixed bottom-6 right-6 z-[99999] flex items-center gap-3 bg-green-900/90 border border-green-700 text-green-200 px-4 py-3 rounded-xl shadow-xl backdrop-blur-sm">
          <span>✅</span>
          <span class="text-sm font-medium">{{ toast.msg }}</span>
        </div>
      </Transition>
    </Teleport>

    <!-- Table -->
    <!-- Desktop table -->
    <div class="card overflow-hidden hidden sm:block">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800">
              <th v-for="col in columns" :key="col.key"
                class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td :colspan="columns.length" class="text-center py-20">
                <div class="flex flex-col items-center gap-3">
                  <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
                  <span class="text-surface-500 text-sm">Yuklanmoqda...</span>
                </div>
              </td>
            </tr>
            <tr v-else-if="!cases.length">
              <td :colspan="columns.length" class="text-center py-20">
                <div class="text-surface-500 text-sm">Murojaatlar topilmadi</div>
              </td>
            </tr>
            <tr v-for="c in cases" :key="c.id"
              @click="goToCase(c.external_id)"
              class="border-b border-surface-800/50 hover:bg-surface-800/30 cursor-pointer transition-colors group">
              <td class="px-5 py-4">
                <span class="font-mono text-brand-400 text-sm group-hover:text-brand-300 transition-colors">
                  {{ c.external_id }}
                </span>
              </td>
              <td class="px-5 py-4"><CategoryBadge :category="c.category" /></td>
              <td class="px-5 py-4"><PriorityBadge :priority="c.priority" /></td>
              <td class="px-5 py-4"><StatusBadge :status="c.status" /></td>
              <td class="px-5 py-4">
                <span :title="c.due_at ? formatDate(c.due_at) : 'Deadline belgilanmagan'"
                  class="cursor-help">
                  {{ deadlineIcon(c) }}
                </span>
                <span v-if="c.due_at" class="text-surface-500 text-xs ml-1">{{ formatShortDate(c.due_at) }}</span>
              </td>
              <td class="px-5 py-4">
                <span :class="c.is_anonymous ? 'text-surface-400' : 'text-green-400'" class="text-xs">
                  {{ c.is_anonymous ? '🔒 Anonim' : '👤 Ochiq' }}
                </span>
              </td>
              <td class="px-5 py-4 text-surface-400 text-sm">{{ formatDate(c.created_at) }}</td>
              <td class="px-5 py-4">
                <span v-if="c.attachments_count" class="text-surface-400 text-xs flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                  {{ c.attachments_count }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Pagination -->
      <div v-if="pagination.pages > 1" class="flex items-center justify-between px-5 py-4 border-t border-surface-800 flex-wrap gap-3">
        <span class="text-surface-500 text-sm">Jami {{ pagination.total }} ta murojaat</span>
        <div class="flex items-center gap-2">
          <button @click="changePage(pagination.page - 1)" :disabled="pagination.page <= 1"
            class="btn-ghost text-sm disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5">← Oldingi</button>
          <span class="text-surface-400 text-sm">{{ pagination.page }} / {{ pagination.pages }}</span>
          <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= pagination.pages"
            class="btn-ghost text-sm disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5">Keyingi →</button>
        </div>
      </div>
    </div>

    <!-- Mobile card list -->
    <div class="sm:hidden space-y-3">
      <div v-if="loading" class="card p-8 text-center">
        <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      </div>
      <div v-else-if="!cases.length" class="card p-8 text-center text-surface-500 text-sm">
        Murojaatlar topilmadi
      </div>
      <div v-for="c in cases" :key="c.id"
        @click="goToCase(c.external_id)"
        class="card p-4 cursor-pointer hover:border-surface-700 transition-colors active:bg-surface-800/50">
        <div class="flex items-center justify-between mb-3">
          <span class="font-mono text-brand-400 text-sm font-semibold">{{ c.external_id }}</span>
          <StatusBadge :status="c.status" />
        </div>
        <div class="flex items-center gap-2 flex-wrap mb-2">
          <CategoryBadge :category="c.category" />
          <PriorityBadge :priority="c.priority" />
          <span :title="c.due_at ? formatDate(c.due_at) : 'Deadline belgilanmagan'" class="text-xs cursor-help">
            {{ deadlineIcon(c) }}
            <span v-if="c.due_at" class="text-surface-500 ml-0.5">{{ formatShortDate(c.due_at) }}</span>
          </span>
          <span :class="c.is_anonymous ? 'text-surface-400' : 'text-green-400'" class="text-xs">
            {{ c.is_anonymous ? '🔒 Anonim' : '👤 Ochiq' }}
          </span>
        </div>
        <div class="flex items-center justify-between mt-2">
          <span class="text-surface-500 text-xs">{{ formatDate(c.created_at) }}</span>
          <span v-if="c.attachments_count" class="text-surface-500 text-xs flex items-center gap-1">
            📎 {{ c.attachments_count }}
          </span>
        </div>
      </div>
      <!-- Mobile pagination -->
      <div v-if="pagination.pages > 1" class="flex items-center justify-center gap-3 py-2">
        <button @click="changePage(pagination.page - 1)" :disabled="pagination.page <= 1"
          class="btn-ghost text-sm disabled:opacity-30 px-3 py-1.5">← Oldingi</button>
        <span class="text-surface-400 text-sm">{{ pagination.page }} / {{ pagination.pages }}</span>
        <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= pagination.pages"
          class="btn-ghost text-sm disabled:opacity-30 px-3 py-1.5">Keyingi →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { format } from 'date-fns'
import api from '@/utils/api'

const router = useRouter()
const loading = ref(true)
const cases = ref([])
const pagination = reactive({ page: 1, pages: 1, total: 0, per_page: 20 })
const exporting = ref(false)
const exportOpen = ref(false)
const exportMenuRef = ref(null)
const toast = reactive({ show: false, msg: '' })
let loadAbortCtrl = null

const filters = reactive({
  status: '', category: '', priority: '',
  from_date: '', to_date: '',
})

const columns = [
  { key: 'id', label: 'Murojaat ID' },
  { key: 'category', label: 'Kategoriya' },
  { key: 'priority', label: 'Ustuvorlik' },
  { key: 'status', label: 'Holat' },
  { key: 'deadline', label: 'Muddat' },
  { key: 'anon', label: 'Tur' },
  { key: 'date', label: 'Sana' },
  { key: 'files', label: 'Fayllar' },
]

const statusOptions = [
  { value: 'new', label: 'Yangi' },
  { value: 'in_progress', label: "Ko'rib chiqilmoqda" },
  { value: 'needs_info', label: "Ma'lumot kerak" },
  { value: 'completed', label: 'Yakunlandi' },
  { value: 'rejected', label: 'Rad etildi' },
]
const categoryOptions = [
  { value: 'corruption', label: 'Korrupsiya' },
  { value: 'conflict_of_interest', label: "Manfaatlar to'qnashuvi" },
  { value: 'fraud', label: 'Firibgarlik' },
  { value: 'safety', label: 'Xavfsizlik' },
  { value: 'discrimination', label: 'Kamsitish' },
  { value: 'procurement', label: 'Tender' },
  { value: 'other', label: 'Boshqa' },
]
const priorityOptions = [
  { value: 'critical', label: '🔴 Kritik' },
  { value: 'high', label: '🟠 Yuqori' },
  { value: 'medium', label: "🟡 O'rta" },
  { value: 'low', label: '🟢 Past' },
]

function buildParams(extra = {}) {
  const params = { ...extra }
  if (filters.status)    params.status    = filters.status
  if (filters.category)  params.category  = filters.category
  if (filters.priority)  params.priority  = filters.priority
  if (filters.from_date) params.from_date = filters.from_date
  if (filters.to_date)   params.to_date   = filters.to_date
  return params
}

async function loadCases() {
  if (loadAbortCtrl) loadAbortCtrl.abort()
  loadAbortCtrl = new AbortController()
  loading.value = true
  try {
    const params = buildParams({ page: pagination.page, per_page: pagination.per_page })
    const { data } = await api.get('/v1/cases', { params, signal: loadAbortCtrl.signal })
    cases.value = data.items
    Object.assign(pagination, { page: data.page, pages: data.pages, total: data.total })
  } catch (e) {
    if (e.name !== 'CanceledError' && e.code !== 'ERR_CANCELED') {
      console.error('Cases yuklanmadi:', e)
    }
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  pagination.page = 1
  loadCases()
}

function changePage(p) {
  pagination.page = p
  loadCases()
}

function resetFilters() {
  Object.assign(filters, { status: '', category: '', priority: '', from_date: '', to_date: '' })
  pagination.page = 1
  loadCases()
}

function goToCase(id) {
  router.push(`/cases/${id}`)
}

function deadlineIcon(c) {
  if (!c.due_at) return '⬜'
  const now = new Date()
  const due = new Date(c.due_at)
  if (due < now) return '🔴'
  const hoursLeft = (due - now) / (1000 * 60 * 60)
  if (hoursLeft <= 24) return '🟡'
  return '⬜'
}

function formatShortDate(d) {
  if (!d) return ''
  return format(new Date(d), 'dd.MM')
}

// ── Export ────────────────────────────────────────────────────────────────────
async function doExport(fmt) {
  exportOpen.value = false
  exporting.value = true
  try {
    const params = buildParams({ format: fmt })
    const resp = await api.get('/v1/cases/export', {
      params,
      responseType: 'blob',
    })
    const today = new Date().toISOString().slice(0, 10)
    const ext = fmt === 'pdf' ? 'pdf' : 'xlsx'
    const filename = `integrity_report_${today}.${ext}`
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    showToast(`✅ Fayl yuklab olindi: ${filename}`)
  } catch (e) {
    showToast('❌ Eksport muvaffaqiyatsiz: ' + (e.response?.data?.detail || e.message))
  } finally {
    exporting.value = false
  }
}

function showToast(msg) {
  toast.msg = msg
  toast.show = true
  setTimeout(() => { toast.show = false }, 3500)
}

// Dropdown tashqariga bosilsa yopilsin
function handleClickOutside(e) {
  if (exportMenuRef.value && !exportMenuRef.value.contains(e.target)) {
    exportOpen.value = false
  }
}
onMounted(() => {
  loadCases()
  document.addEventListener('click', handleClickOutside)
})
onUnmounted(() => {
  if (loadAbortCtrl) loadAbortCtrl.abort()
  document.removeEventListener('click', handleClickOutside)
})

function formatDate(d) {
  return d ? format(new Date(d), 'dd.MM.yyyy HH:mm') : '—'
}

// Inline badge components
const StatusBadge = defineComponent({
  props: ['status'],
  setup(props) {
    const map = {
      new: { text: 'Yangi', cls: 'bg-blue-500/15 text-blue-400 border border-blue-500/20' },
      in_progress: { text: "Ko'rib chiqilmoqda", cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20' },
      needs_info: { text: "Ma'lumot kerak", cls: 'bg-orange-500/15 text-orange-400 border border-orange-500/20' },
      completed: { text: 'Yakunlandi', cls: 'bg-green-500/15 text-green-400 border border-green-500/20' },
      rejected: { text: 'Rad etildi', cls: 'bg-red-500/15 text-red-400 border border-red-500/20' },
      archived: { text: 'Arxivlandi', cls: 'bg-surface-700/50 text-surface-400' },
    }
    return () => {
      const s = map[props.status] || { text: props.status, cls: 'bg-surface-700 text-surface-400' }
      return h('span', { class: `badge ${s.cls}` }, s.text)
    }
  }
})

const CategoryBadge = defineComponent({
  props: ['category'],
  setup(props) {
    const map = {
      corruption: '🔴 Korrupsiya',
      conflict_of_interest: "⚖️ Manfaat",
      fraud: '💸 Firibgarlik',
      safety: '⚠️ Xavfsizlik',
      discrimination: '🚫 Kamsitish',
      procurement: '📋 Tender',
      other: '❓ Boshqa',
    }
    return () => h('span', { class: 'text-surface-300 text-sm' }, map[props.category] || props.category)
  }
})

const PriorityBadge = defineComponent({
  props: ['priority'],
  setup(props) {
    const map = {
      critical: { text: 'Kritik', cls: 'bg-red-500/15 text-red-400 border border-red-500/20' },
      high: { text: 'Yuqori', cls: 'bg-orange-500/15 text-orange-400 border border-orange-500/20' },
      medium: { text: "O'rta", cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20' },
      low: { text: 'Past', cls: 'bg-green-500/15 text-green-400 border border-green-500/20' },
    }
    return () => {
      const p = map[props.priority] || { text: props.priority, cls: '' }
      return h('span', { class: `badge ${p.cls}` }, p.text)
    }
  }
})
</script>

<style scoped>
.dropdown-enter-active, .dropdown-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-6px); }

.toast-enter-active, .toast-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(12px); }
</style>
