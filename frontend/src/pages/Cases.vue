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
      <div class="flex items-center gap-3 flex-wrap">
        <div class="flex items-center gap-2 flex-1 min-w-48">
          <label class="text-surface-500 text-xs whitespace-nowrap">Dan:</label>
          <input type="date" v-model="filters.from_date" @change="onFilterChange" class="input flex-1 text-sm" />
        </div>
        <div class="flex items-center gap-2 flex-1 min-w-48">
          <label class="text-surface-500 text-xs whitespace-nowrap">Gacha:</label>
          <input type="date" v-model="filters.to_date" @change="onFilterChange" class="input flex-1 text-sm" />
        </div>
        <button @click="resetFilters" class="btn-ghost text-sm whitespace-nowrap">Filtrni tozalash</button>

        <!-- Export dropdown -->
        <div class="relative" ref="exportMenuRef">
          <button @click="exportOpen = !exportOpen" :disabled="exporting"
            class="btn-ghost text-sm whitespace-nowrap flex items-center gap-2 disabled:opacity-50">
            <svg v-if="exporting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span v-else>📥</span> Eksport
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

    <!-- Bulk actions bar -->
    <Transition name="slide-down">
      <div v-if="selectedIds.size > 0"
        class="card p-3 mb-4 flex items-center gap-3 flex-wrap bg-brand-500/5 border-brand-500/20">
        <span class="text-brand-300 text-sm font-medium">{{ selectedIds.size }} ta tanlandi</span>
        <button @click="bulkAssign" class="btn-ghost text-sm flex items-center gap-1.5">
          👤 Tayinlash
        </button>
        <button @click="bulkExport" class="btn-ghost text-sm flex items-center gap-1.5">
          📊 Excel eksport
        </button>
        <button @click="selectedIds.clear()" class="btn-ghost text-sm text-surface-500">
          ✕ Bekor qilish
        </button>
      </div>
    </Transition>

    <!-- Desktop table -->
    <div class="card overflow-hidden hidden sm:block">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800">
              <th class="px-3 py-4 w-10">
                <input type="checkbox" :checked="allSelected" @change="toggleAll"
                  class="accent-brand-500 w-4 h-4 rounded cursor-pointer" />
              </th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Murojaat ID</th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Kategoriya</th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Ustuvorlik</th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Holat</th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Muddat</th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Sana</th>
              <th class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">Amallar</th>
            </tr>
          </thead>
          <tbody>
            <!-- Skeleton loading -->
            <template v-if="loading">
              <tr v-for="i in 8" :key="'sk'+i" class="border-b border-surface-800/50">
                <td class="px-3 py-4 w-10"><div class="w-4 h-4 bg-surface-800 rounded animate-pulse"></div></td>
                <td class="px-5 py-4">
                  <div class="space-y-1.5">
                    <div class="h-4 w-20 bg-surface-800 rounded animate-pulse"></div>
                    <div class="h-2.5 w-32 bg-surface-800/60 rounded animate-pulse"></div>
                  </div>
                </td>
                <td class="px-5 py-4"><div class="h-4 w-20 bg-surface-800 rounded animate-pulse"></div></td>
                <td class="px-5 py-4"><div class="h-5 w-14 bg-surface-800 rounded-full animate-pulse"></div></td>
                <td class="px-5 py-4"><div class="h-5 w-24 bg-surface-800 rounded-full animate-pulse"></div></td>
                <td class="px-5 py-4"><div class="h-3.5 w-12 bg-surface-800 rounded animate-pulse"></div></td>
                <td class="px-5 py-4"><div class="h-3.5 w-28 bg-surface-800 rounded animate-pulse"></div></td>
                <td class="px-5 py-4"><div class="h-6 w-14 bg-surface-800 rounded-lg animate-pulse"></div></td>
              </tr>
            </template>
            <!-- Error state -->
            <tr v-else-if="loadError">
              <td colspan="8">
                <ErrorState :message="loadError" :retry="loadCases" />
              </td>
            </tr>
            <!-- Empty state -->
            <tr v-else-if="!cases.length">
              <td colspan="8">
                <EmptyState
                  :icon="hasFilters ? '🔍' : '📭'"
                  :title="hasFilters ? 'Natija topilmadi' : 'Murojaatlar yo\'q'"
                  :description="hasFilters ? 'Ushbu filtrlar bo\'yicha hech qanday murojaat topilmadi' : 'Yangi murojaat hali kelmagan'"
                  :action="hasFilters ? 'Filterni tozalash' : ''"
                  :action-fn="hasFilters ? resetFilters : null" />
              </td>
            </tr>
            <template v-for="c in cases" :key="c.id">
              <tr class="border-b border-surface-800/50 hover:bg-surface-800/30 transition-colors group relative"
                :class="{ 'opacity-50 pointer-events-none': rowLoading === c.external_id }">
                <!-- Loading overlay -->
                <td v-if="rowLoading === c.external_id" colspan="8"
                  class="absolute inset-0 bg-surface-900/40 z-10 flex items-center justify-center">
                  <div class="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
                </td>

                <!-- Checkbox -->
                <td class="px-3 py-4 w-10" @click.stop>
                  <input type="checkbox" :checked="selectedIds.has(c.external_id)"
                    @change="toggleSelect(c.external_id)"
                    class="accent-brand-500 w-4 h-4 rounded cursor-pointer" />
                </td>

                <!-- ID + deadline dot + description tooltip -->
                <td class="px-5 py-4 cursor-pointer" @click="goToCase(c.external_id)">
                  <div class="flex items-center gap-2">
                    <span v-if="deadlineIcon(c)" :title="c.due_at ? `Deadline: ${formatDate(c.due_at)}` : ''"
                      class="flex-shrink-0 text-xs leading-none">{{ deadlineIcon(c) }}</span>
                    <span class="font-mono text-brand-400 text-sm group-hover:text-brand-300 transition-colors">
                      {{ c.external_id }}
                    </span>
                  </div>
                  <div v-if="c.title" class="text-surface-600 text-xs mt-0.5 truncate max-w-[180px]"
                    :title="c.title">
                    {{ c.title?.length > 50 ? c.title.slice(0, 50) + '...' : c.title }}
                  </div>
                </td>

                <td class="px-5 py-4 cursor-pointer" @click="goToCase(c.external_id)">
                  <CategoryBadge :category="c.category" />
                </td>
                <td class="px-5 py-4 cursor-pointer" @click="goToCase(c.external_id)">
                  <PriorityBadge :priority="c.priority" />
                </td>
                <td class="px-5 py-4 cursor-pointer" @click="goToCase(c.external_id)">
                  <StatusBadge :status="c.status" />
                </td>
                <td class="px-5 py-4 cursor-pointer" @click="goToCase(c.external_id)">
                  <span v-if="c.due_at" class="text-surface-400 text-xs"
                    :title="`Deadline: ${formatDate(c.due_at)}`">
                    {{ formatShortDate(c.due_at) }}
                  </span>
                  <span v-else class="text-surface-600 text-xs">—</span>
                </td>
                <td class="px-5 py-4 text-surface-400 text-sm cursor-pointer" @click="goToCase(c.external_id)">
                  {{ formatDate(c.created_at) }}
                </td>

                <!-- Actions -->
                <td class="px-5 py-4" @click.stop>
                  <div class="flex items-center gap-1">
                    <CaseRowActions
                      :caseItem="c"
                      @view="goToCase(c.external_id)"
                      @action="handleRowAction($event, c)" />
                  </div>
                </td>
              </tr>
            </template>
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
      <!-- Mobile skeleton -->
      <template v-if="loading">
        <div v-for="i in 5" :key="'msk'+i" class="card p-4 space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-4 h-4 bg-surface-800 rounded animate-pulse"></div>
              <div class="h-4 w-20 bg-surface-800 rounded animate-pulse"></div>
            </div>
            <div class="h-5 w-24 bg-surface-800 rounded-full animate-pulse"></div>
          </div>
          <div class="h-3 w-3/4 bg-surface-800/60 rounded animate-pulse"></div>
          <div class="flex gap-2">
            <div class="h-4 w-20 bg-surface-800 rounded animate-pulse"></div>
            <div class="h-5 w-14 bg-surface-800 rounded-full animate-pulse"></div>
          </div>
          <div class="flex justify-between">
            <div class="h-3 w-28 bg-surface-800/60 rounded animate-pulse"></div>
            <div class="h-3 w-16 bg-surface-800/60 rounded animate-pulse"></div>
          </div>
        </div>
      </template>
      <!-- Mobile error -->
      <ErrorState v-else-if="loadError" :message="loadError" :retry="loadCases" />
      <!-- Mobile empty -->
      <EmptyState v-else-if="!cases.length"
        :icon="hasFilters ? '🔍' : '📭'"
        :title="hasFilters ? 'Natija topilmadi' : 'Murojaatlar yo\'q'"
        :description="hasFilters ? 'Ushbu filtrlar bo\'yicha hech qanday murojaat topilmadi' : 'Yangi murojaat hali kelmagan'"
        :action="hasFilters ? 'Filterni tozalash' : ''"
        :action-fn="hasFilters ? resetFilters : null" />
      <div v-for="c in cases" :key="'m'+c.id"
        class="card p-4 transition-colors relative"
        :class="{ 'opacity-50': rowLoading === c.external_id }">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <input type="checkbox" :checked="selectedIds.has(c.external_id)"
              @change.stop="toggleSelect(c.external_id)"
              class="accent-brand-500 w-4 h-4 rounded cursor-pointer" />
            <span v-if="deadlineIcon(c)" class="text-xs" :title="c.due_at ? `Deadline: ${formatDate(c.due_at)}` : ''">{{ deadlineIcon(c) }}</span>
            <span class="font-mono text-brand-400 text-sm font-semibold cursor-pointer" @click="goToCase(c.external_id)">{{ c.external_id }}</span>
          </div>
          <div class="flex items-center gap-1">
            <StatusBadge :status="c.status" />
            <CaseRowActions :caseItem="c" @view="goToCase(c.external_id)" @action="handleRowAction($event, c)" />
          </div>
        </div>
        <div v-if="c.title" class="text-surface-600 text-xs mb-2 truncate" :title="c.title">
          {{ c.title?.length > 50 ? c.title.slice(0, 50) + '...' : c.title }}
        </div>
        <div class="flex items-center gap-2 flex-wrap mb-2">
          <CategoryBadge :category="c.category" />
          <PriorityBadge :priority="c.priority" />
        </div>
        <div class="flex items-center justify-between mt-2">
          <span class="text-surface-500 text-xs">{{ formatDate(c.created_at) }}</span>
          <span v-if="c.due_at" class="text-surface-500 text-xs">⏰ {{ formatShortDate(c.due_at) }}</span>
        </div>
      </div>
      <div v-if="pagination.pages > 1" class="flex items-center justify-center gap-3 py-2">
        <button @click="changePage(pagination.page - 1)" :disabled="pagination.page <= 1"
          class="btn-ghost text-sm disabled:opacity-30 px-3 py-1.5">← Oldingi</button>
        <span class="text-surface-400 text-sm">{{ pagination.page }} / {{ pagination.pages }}</span>
        <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= pagination.pages"
          class="btn-ghost text-sm disabled:opacity-30 px-3 py-1.5">Keyingi →</button>
      </div>
    </div>

    <!-- ═══ Toast ═══ -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show"
          :class="toast.ok !== false ? 'bg-green-900/90 border-green-700 text-green-200' : 'bg-red-900/90 border-red-700 text-red-200'"
          class="fixed bottom-6 right-6 z-[99999] flex items-center gap-3 border px-4 py-3 rounded-xl shadow-xl backdrop-blur-sm">
          <span>{{ toast.ok !== false ? '✅' : '❌' }}</span>
          <span class="text-sm font-medium">{{ toast.msg }}</span>
        </div>
      </Transition>
    </Teleport>

    <!-- ═══ Status Modal ═══ -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="statusModal.open" class="fixed inset-0 z-[99997] flex items-center justify-center p-4"
          @click.self="statusModal.open = false">
          <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="statusModal.open = false"></div>
          <div class="relative bg-surface-800 border border-surface-700 rounded-2xl shadow-2xl w-full max-w-md p-6 z-10">
            <h3 class="text-lg font-semibold text-white mb-1">{{ statusModal.title }}</h3>
            <p class="text-surface-400 text-sm mb-5">
              <span class="font-mono text-brand-400">{{ statusModal.caseId }}</span> — {{ statusModal.subtitle }}
            </p>

            <div class="mb-5">
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                Izoh {{ statusModal.reasonRequired ? '(majburiy)' : '(ixtiyoriy)' }}
              </label>
              <textarea v-model="statusModal.reason" rows="3"
                class="input w-full resize-none" placeholder="Sabab yoki izoh yozing..." />
            </div>

            <div class="flex justify-end gap-3">
              <button @click="statusModal.open = false" class="btn-ghost">Bekor</button>
              <button @click="confirmStatusChange"
                :disabled="statusModal.reasonRequired && !statusModal.reason.trim()"
                :class="statusModal.danger ? 'bg-red-600 hover:bg-red-700 disabled:bg-red-800' : 'btn-primary'"
                class="px-5 py-2 rounded-xl text-white text-sm font-medium transition-colors disabled:opacity-50">
                {{ statusModal.confirmLabel }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ═══ Assign Modal ═══ -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="assignModal.open" class="fixed inset-0 z-[99997] flex items-center justify-center p-4"
          @click.self="assignModal.open = false">
          <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="assignModal.open = false"></div>
          <div class="relative bg-surface-800 border border-surface-700 rounded-2xl shadow-2xl w-full max-w-md p-6 z-10">
            <h3 class="text-lg font-semibold text-white mb-1">👤 Tayinlash</h3>
            <p class="text-surface-400 text-sm mb-5">
              <template v-if="assignModal.caseIds.length === 1">
                <span class="font-mono text-brand-400">{{ assignModal.caseIds[0] }}</span> ni ijrochiga tayinlash
              </template>
              <template v-else>
                {{ assignModal.caseIds.length }} ta murojaatni ijrochiga tayinlash
              </template>
            </p>

            <div v-if="usersLoading" class="flex items-center justify-center py-6">
              <div class="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else class="space-y-2 max-h-60 overflow-y-auto mb-5">
              <label v-for="u in users" :key="u.id"
                class="flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all"
                :class="assignModal.userId === u.id
                  ? 'border-brand-500 bg-brand-500/10'
                  : 'border-surface-700 hover:border-surface-600'">
                <input type="radio" :value="u.id" v-model="assignModal.userId"
                  class="accent-brand-500" />
                <div>
                  <div class="text-sm text-white">{{ u.full_name || u.username }}</div>
                  <div class="text-xs text-surface-500">{{ u.role }} · {{ u.email || '' }}</div>
                </div>
              </label>
              <div v-if="!users.length" class="text-surface-500 text-sm text-center py-4">
                Terguvchi topilmadi
              </div>
            </div>

            <div class="flex justify-end gap-3">
              <button @click="assignModal.open = false" class="btn-ghost">Bekor</button>
              <button @click="confirmAssign" :disabled="!assignModal.userId"
                class="btn-primary disabled:opacity-50">
                Tayinlash
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { format } from 'date-fns'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'
import CaseRowActions from '@/components/CaseRowActions.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const loadError = ref('')
const cases = ref([])
const pagination = reactive({ page: 1, pages: 1, total: 0, per_page: 20 })
const exporting = ref(false)
const exportOpen = ref(false)
const exportMenuRef = ref(null)
const toast = reactive({ show: false, ok: true, msg: '' })
const rowLoading = ref(null)
let loadAbortCtrl = null

const hasFilters = computed(() =>
  !!(filters.status || filters.category || filters.priority || filters.from_date || filters.to_date)
)

// ── Selection ───────────────────────────────────────────
const selectedIds = reactive(new Set())

const allSelected = computed(() => {
  if (!cases.value.length) return false
  return cases.value.every(c => selectedIds.has(c.external_id))
})

function toggleAll() {
  if (allSelected.value) {
    cases.value.forEach(c => selectedIds.delete(c.external_id))
  } else {
    cases.value.forEach(c => selectedIds.add(c.external_id))
  }
}

function toggleSelect(id) {
  if (selectedIds.has(id)) selectedIds.delete(id)
  else selectedIds.add(id)
}

// ── Filters ─────────────────────────────────────────────
const filters = reactive({
  status: '', category: '', priority: '',
  from_date: '', to_date: '',
})

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

// ── Data loading ────────────────────────────────────────
async function loadCases() {
  if (loadAbortCtrl) loadAbortCtrl.abort()
  loadAbortCtrl = new AbortController()
  loading.value = true
  loadError.value = ''
  try {
    const params = buildParams({ page: pagination.page, per_page: pagination.per_page })
    const { data } = await api.get('/v1/cases', { params, signal: loadAbortCtrl.signal })
    cases.value = data.items
    Object.assign(pagination, { page: data.page, pages: data.pages, total: data.total })
  } catch (e) {
    if (e.name !== 'CanceledError' && e.code !== 'ERR_CANCELED') {
      console.error('Cases yuklanmadi:', e)
      loadError.value = e.response?.data?.detail || "Ma'lumotlarni yuklashda xatolik yuz berdi"
    }
  } finally {
    loading.value = false
  }
}

function onFilterChange() { pagination.page = 1; loadCases() }
function changePage(p)    { pagination.page = p; loadCases() }

function resetFilters() {
  Object.assign(filters, { status: '', category: '', priority: '', from_date: '', to_date: '' })
  pagination.page = 1
  loadCases()
}

function goToCase(id) { router.push(`/cases/${id}`) }

// ── Helpers ─────────────────────────────────────────────
function deadlineIcon(c) {
  if (!c.due_at) return ''
  const now = new Date()
  const due = new Date(c.due_at)
  if (due < now) return '🔴'
  const hoursLeft = (due - now) / (1000 * 60 * 60)
  if (hoursLeft <= 24) return '🟡'
  return ''
}

function formatShortDate(d) {
  if (!d) return ''
  return format(new Date(d), 'dd.MM')
}

function formatDate(d) {
  return d ? format(new Date(d), 'dd.MM.yyyy HH:mm') : '—'
}

function showToast(msg, ok = true) {
  toast.msg = msg
  toast.ok = ok
  toast.show = true
  setTimeout(() => { toast.show = false }, 3500)
}

// ── Row actions ─────────────────────────────────────────
const statusModal = reactive({
  open: false, title: '', subtitle: '', caseId: '', newStatus: '',
  reasonRequired: false, reason: '',
  confirmLabel: 'Tasdiqlash', danger: false,
})

const assignModal = reactive({
  open: false, caseIds: [], userId: null,
})

const users = ref([])
const usersLoading = ref(false)

async function loadUsers() {
  if (users.value.length) return
  usersLoading.value = true
  try {
    const { data } = await api.get('/v1/users')
    users.value = data.filter(u => u.role === 'admin' || u.role === 'investigator')
  } catch (e) {
    console.error('Users yuklanmadi:', e)
  } finally {
    usersLoading.value = false
  }
}

function handleRowAction(action, c) {
  switch (action) {
    case 'start':
      openStatusModal(c, 'in_progress', '▶️ Boshlash', "Murojaatni ko'rib chiqishni boshlaysizmi?", false)
      break
    case 'complete':
      openStatusModal(c, 'completed', '✅ Yakunlash', 'Murojaatni yakunlaysizmi?', false)
      break
    case 'reject':
      openStatusModal(c, 'rejected', '❌ Rad etish', 'Murojaatni rad etasizmi?', true, true)
      break
    case 'assign':
      assignModal.caseIds = [c.external_id]
      assignModal.userId = null
      assignModal.open = true
      loadUsers()
      break
    case 'pdf':
      exportSinglePdf(c.external_id)
      break
  }
}

function openStatusModal(c, newStatus, title, subtitle, reasonRequired = false, danger = false) {
  statusModal.caseId = c.external_id
  statusModal.newStatus = newStatus
  statusModal.title = title
  statusModal.subtitle = subtitle
  statusModal.reasonRequired = reasonRequired
  statusModal.reason = ''
  statusModal.confirmLabel = title.replace(/[^\p{L}\s]/gu, '').trim()
  statusModal.danger = danger
  statusModal.open = true
}

async function confirmStatusChange() {
  const caseId = statusModal.caseId
  const newStatus = statusModal.newStatus
  const reason = statusModal.reason.trim()
  statusModal.open = false
  rowLoading.value = caseId

  try {
    await api.post(`/v1/cases/${caseId}/status`, {
      status: newStatus,
      reason: reason || null,
    })
    const item = cases.value.find(c => c.external_id === caseId)
    if (item) item.status = newStatus
    showToast('✅ Holat o\'zgartirildi')
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || 'Xatolik'), false)
  } finally {
    rowLoading.value = null
  }
}

async function confirmAssign() {
  const userId = assignModal.userId
  const caseIds = [...assignModal.caseIds]
  assignModal.open = false

  for (const caseId of caseIds) {
    rowLoading.value = caseId
    try {
      await api.post(`/v1/cases/${caseId}/assign`, { user_id: userId })
      const item = cases.value.find(c => c.external_id === caseId)
      if (item) item.assigned_to = userId
    } catch (e) {
      showToast(`❌ ${caseId}: ` + (e.response?.data?.detail || 'Xatolik'), false)
    }
  }
  rowLoading.value = null
  showToast(`✅ ${caseIds.length > 1 ? caseIds.length + ' ta murojaat' : 'Murojaat'} tayinlandi`)
  selectedIds.clear()
}

// ── Bulk ────────────────────────────────────────────────
function bulkAssign() {
  assignModal.caseIds = [...selectedIds]
  assignModal.userId = null
  assignModal.open = true
  loadUsers()
}

async function bulkExport() {
  exporting.value = true
  try {
    const params = buildParams({ format: 'xlsx', ids: [...selectedIds].join(',') })
    const resp = await api.get('/v1/cases/export', { params, responseType: 'blob' })
    const today = new Date().toISOString().slice(0, 10)
    const filename = `integrity_selected_${today}.xlsx`
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
    showToast(`✅ ${selectedIds.size} ta murojaat eksport qilindi`)
  } catch (e) {
    showToast('❌ Eksport muvaffaqiyatsiz: ' + (e.response?.data?.detail || e.message), false)
  } finally {
    exporting.value = false
  }
}

async function exportSinglePdf(caseId) {
  rowLoading.value = caseId
  try {
    const resp = await api.get(`/v1/cases/${caseId}/export`, { params: { format: 'pdf' }, responseType: 'blob' })
    const filename = `case_${caseId}.pdf`
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
    showToast(`✅ PDF yuklandi: ${filename}`)
  } catch (e) {
    showToast('❌ PDF eksport xatosi: ' + (e.response?.data?.detail || e.message), false)
  } finally {
    rowLoading.value = null
  }
}

// ── Export ───────────────────────────────────────────────
async function doExport(fmt) {
  exportOpen.value = false
  exporting.value = true
  try {
    const params = buildParams({ format: fmt })
    const resp = await api.get('/v1/cases/export', { params, responseType: 'blob' })
    const today = new Date().toISOString().slice(0, 10)
    const ext = fmt === 'pdf' ? 'pdf' : 'xlsx'
    const filename = `integrity_report_${today}.${ext}`
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
    showToast(`✅ Fayl yuklab olindi: ${filename}`)
  } catch (e) {
    showToast('❌ Eksport muvaffaqiyatsiz: ' + (e.response?.data?.detail || e.message), false)
  } finally {
    exporting.value = false
  }
}

// ── Lifecycle ───────────────────────────────────────────
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

// ── Inline badge components ─────────────────────────────
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

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }

.slide-down-enter-active, .slide-down-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
