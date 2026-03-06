<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <!-- Header + Period filters -->
    <div class="flex items-start justify-between gap-4 mb-6 flex-wrap">
      <div>
        <h1 class="text-2xl font-bold text-white">{{ t('dashboard.title') }}</h1>
        <p class="text-surface-400 text-sm mt-1">{{ t('dashboard.subtitle') }}</p>
      </div>

      <!-- Period tabs -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <button v-for="p in periodOptions" :key="p.value"
          @click="setPeriod(p.value)"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
            activePeriod === p.value && !customOpen
              ? 'bg-brand-600 text-white shadow-sm'
              : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
          ]">
          {{ p.label }}
        </button>
        <!-- Custom date -->
        <button @click="customOpen = !customOpen"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5',
            customOpen || (customFrom && customTo)
              ? 'bg-brand-600 text-white'
              : 'bg-surface-800 text-surface-400 hover:text-white hover:bg-surface-700'
          ]">
          📅 {{ t('dashboard.custom') }}
        </button>
      </div>
    </div>

    <!-- Custom date picker panel -->
    <Transition name="slide">
      <div v-if="customOpen" class="card p-4 mb-5 flex items-end gap-3 flex-wrap">
        <div class="flex items-center gap-2">
          <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('dashboard.from') }}</label>
          <input type="date" v-model="customFrom" class="input text-sm" :max="customTo || undefined" />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('dashboard.to') }}</label>
          <input type="date" v-model="customTo" class="input text-sm" :min="customFrom || undefined" />
        </div>
        <button @click="applyCustom"
          :disabled="!customFrom || !customTo || customFrom > customTo"
          class="btn-primary text-sm px-4 py-2 disabled:opacity-40">
          {{ t('dashboard.apply') }}
        </button>
        <button @click="clearCustom" class="btn-ghost text-sm px-3 py-2 text-surface-400">
          ✕ {{ t('dashboard.cancel_custom') }}
        </button>
      </div>
    </Transition>

    <!-- Active filter badge -->
    <div v-if="filterLabel" class="flex items-center gap-3 mb-5">
      <span class="flex items-center gap-2 bg-brand-600/15 border border-brand-600/30 text-brand-300 text-xs px-3 py-1.5 rounded-lg">
        📅 {{ filterLabel }}
      </span>
      <button @click="clearAll" class="text-surface-500 hover:text-surface-300 text-xs transition-colors">
        ✕ {{ t('dashboard.clear_filter') }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-8">
      <!-- Stats skeleton -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-5">
        <SkeletonLoader type="card" :count="4" />
      </div>
      <!-- Charts skeleton -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <SkeletonLoader type="chart" class="lg:col-span-2" />
        <div class="card p-6 space-y-3">
          <div class="h-4 w-28 bg-surface-800 rounded animate-pulse mb-4"></div>
          <div v-for="i in 7" :key="i" class="flex items-center gap-3">
            <div class="w-2.5 h-2.5 rounded-full bg-surface-800 animate-pulse"></div>
            <div class="h-3 flex-1 bg-surface-800/70 rounded animate-pulse"></div>
            <div class="h-1.5 w-20 bg-surface-800 rounded-full animate-pulse"></div>
            <div class="h-3 w-4 bg-surface-800 rounded animate-pulse"></div>
          </div>
        </div>
      </div>
      <!-- Status/Priority skeleton -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div v-for="s in 2" :key="s" class="card p-6 space-y-4">
          <div class="h-4 w-24 bg-surface-800 rounded animate-pulse"></div>
          <div v-for="i in 5" :key="i" class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-surface-800 animate-pulse"></div>
              <div class="h-3 w-24 bg-surface-800/70 rounded animate-pulse"></div>
            </div>
            <div class="flex items-center gap-3">
              <div class="h-1.5 w-24 bg-surface-800 rounded-full animate-pulse"></div>
              <div class="h-3 w-5 bg-surface-800 rounded animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <ErrorState v-else-if="loadError" :message="loadError" :retry="loadStats" />

    <template v-else>
      <!-- Overdue / Deadline warning banners -->
      <div v-if="stats?.overdue_count > 0"
        @click="router.push('/cases?status=in_progress&overdue=true')"
        class="mb-4 p-4 rounded-xl bg-red-500/15 border border-red-500/30 cursor-pointer hover:bg-red-500/20 transition-colors flex items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <span class="text-2xl">🚨</span>
          <span class="text-red-300 font-medium text-sm">
            {{ t('dashboard.overdue_count', { count: stats.overdue_count }) }}
          </span>
        </div>
        <span class="text-red-400 text-xs font-medium whitespace-nowrap">{{ t('dashboard.overdue_view') }}</span>
      </div>
      <div v-if="stats?.deadline_near_count > 0"
        @click="router.push('/cases?status=in_progress&deadline_near=true')"
        class="mb-4 p-4 rounded-xl bg-yellow-500/15 border border-yellow-500/30 cursor-pointer hover:bg-yellow-500/20 transition-colors flex items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <span class="text-2xl">⏰</span>
          <span class="text-yellow-300 font-medium text-sm">
            {{ t('dashboard.deadline_near', { count: stats.deadline_near_count }) }}
          </span>
        </div>
        <span class="text-yellow-400 text-xs font-medium whitespace-nowrap">{{ t('dashboard.overdue_view') }}</span>
      </div>

      <!-- Stats row -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8">
        <div v-for="stat in statCards" :key="stat.label"
          class="card p-5 flex items-center gap-4">
          <div :class="['w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0', stat.bg]">
            {{ stat.icon }}
          </div>
          <div class="min-w-0">
            <div class="text-2xl font-bold text-white">{{ stat.value }}</div>
            <div class="text-surface-400 text-xs mt-0.5 truncate">{{ stat.label }}</div>
          </div>
        </div>
      </div>

      <!-- Charts row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
        <!-- Trend bar chart -->
        <div class="card p-6 lg:col-span-2">
          <div class="mb-5">
            <h3 class="font-semibold text-white">{{ t('dashboard.dynamics') }}</h3>
            <p class="text-surface-500 text-xs mt-0.5">{{ trendSubtitle }}</p>
          </div>
          <div class="flex items-end justify-between gap-1.5 h-40">
            <div v-for="(item, i) in monthlyBars" :key="i"
              class="flex flex-col items-center gap-1 flex-1 min-w-0">
              <span class="text-surface-400 text-xs">{{ item.count || '' }}</span>
              <div class="w-full rounded-t-md bg-brand-600 transition-all duration-700"
                :style="{ height: item.height + 'px' }"></div>
              <span class="text-surface-500 text-xs truncate w-full text-center">{{ item.label }}</span>
            </div>
            <div v-if="!monthlyBars.length" class="w-full text-center text-surface-600 text-sm py-10">
              {{ t('dashboard.no_data') }}
            </div>
          </div>
        </div>

        <!-- Category bar list -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">{{ t('dashboard.by_category') }}</h3>
          <div class="space-y-2.5">
            <div v-for="item in categoryItems" :key="item.key" class="flex items-center gap-3">
              <div class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="{ background: item.color }"></div>
              <span class="text-surface-300 text-xs flex-1 truncate">{{ item.label }}</span>
              <div class="w-20 bg-surface-800 rounded-full h-1.5 overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700"
                  :style="{ width: getCatPercent(item.key) + '%', background: item.color }"></div>
              </div>
              <span class="text-white text-xs font-medium w-5 text-right">
                {{ stats?.by_category?.[item.key] || 0 }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Status + Priority -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">{{ t('dashboard.by_status') }}</h3>
          <div class="space-y-3">
            <div v-for="item in statusItems" :key="item.key"
              class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-2 min-w-0">
                <span :class="['w-2 h-2 rounded-full flex-shrink-0', item.dot]"></span>
                <span class="text-surface-300 text-sm truncate">{{ item.label }}</span>
              </div>
              <div class="flex items-center gap-3 flex-shrink-0">
                <div class="w-24 bg-surface-800 rounded-full h-1.5 overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-700"
                    :class="item.bar"
                    :style="{ width: getPercent(stats?.by_status?.[item.key]) + '%' }"></div>
                </div>
                <span class="text-white text-sm font-medium w-6 text-right">
                  {{ stats?.by_status?.[item.key] || 0 }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">{{ t('dashboard.by_priority') }}</h3>
          <div class="space-y-3">
            <div v-for="item in priorityItems" :key="item.key"
              class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-base flex-shrink-0">{{ item.emoji }}</span>
                <span class="text-surface-300 text-sm truncate">{{ item.label }}</span>
              </div>
              <div class="flex items-center gap-3 flex-shrink-0">
                <div class="w-24 bg-surface-800 rounded-full h-1.5 overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-700"
                    :class="item.bar"
                    :style="{ width: getPercent(stats?.by_priority?.[item.key]) + '%' }"></div>
                </div>
                <span class="text-white text-sm font-medium w-6 text-right">
                  {{ stats?.by_priority?.[item.key] || 0 }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { format, differenceInDays, parseISO } from 'date-fns'
import api from '@/utils/api'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const route  = useRoute()
const { t } = useI18n()

const loading    = ref(true)
const loadError  = ref('')
const stats      = ref(null)
const activePeriod = ref('')   // 'today' | 'week' | 'month' | 'year' | ''
const customOpen = ref(false)
const customFrom = ref('')
const customTo   = ref('')

// AbortController — eski so'rovni bekor qilish
let abortCtrl = null

const periodOptions = computed(() => [
  { value: '',      label: t('dashboard.period_all') },
  { value: 'today', label: t('dashboard.period_today') },
  { value: 'week',  label: t('dashboard.period_week') },
  { value: 'month', label: t('dashboard.period_month') },
  { value: 'year',  label: t('dashboard.period_year') },
])

const filterLabel = computed(() => {
  if (customFrom.value && customTo.value && !customOpen.value) {
    const d1 = parseISO(customFrom.value)
    const d2 = parseISO(customTo.value)
    const days = differenceInDays(d2, d1) + 1
    return `${format(d1, 'dd MMM')} — ${format(d2, 'dd MMM yyyy')} (${t('dashboard.days_count', { days })})`
  }
  if (activePeriod.value) {
    const periodLabelMap = {
      today: t('dashboard.period_label_today'),
      week:  t('dashboard.period_label_week'),
      month: t('dashboard.period_label_month'),
      year:  t('dashboard.period_label_year'),
    }
    return periodLabelMap[activePeriod.value] || ''
  }
  return ''
})

const trendSubtitle = computed(() => {
  const label = stats.value?.trend_label || 'oy'
  if (label === 'kun')   return t('dashboard.daily_dynamics')
  if (label === 'hafta') return t('dashboard.weekly_dynamics')
  return t('dashboard.monthly_dynamics')
})

// ── URL sync ──────────────────────────────────────────────────────────────────
function syncToUrl() {
  const q = {}
  if (customFrom.value && customTo.value && !customOpen.value) {
    q.from = customFrom.value
    q.to   = customTo.value
  } else if (activePeriod.value) {
    q.period = activePeriod.value
  }
  router.replace({ query: q })
}

function readFromUrl() {
  const { period, from, to } = route.query
  if (from && to) {
    customFrom.value = from
    customTo.value   = to
    customOpen.value = false
    activePeriod.value = ''
  } else if (period) {
    activePeriod.value = period
  }
}

// ── Stats yuklash ─────────────────────────────────────────────────────────────
async function loadStats() {
  // Oldingi so'rovni bekor qil
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = new AbortController()

  loading.value = true
  loadError.value = ''
  try {
    const params = {}
    if (customFrom.value && customTo.value && !customOpen.value) {
      params.from_date = customFrom.value
      params.to_date   = customTo.value
    } else if (activePeriod.value) {
      params.period = activePeriod.value
    }
    const { data } = await api.get('/v1/cases/stats', {
      params,
      signal: abortCtrl.signal,
    })
    stats.value = data
  } catch (e) {
    if (e.name !== 'CanceledError' && e.code !== 'ERR_CANCELED') {
      console.error('Stats yuklab bo\'lmadi:', e)
      loadError.value = e.response?.data?.detail || t('dashboard.load_error')
    }
  } finally {
    loading.value = false
  }
}

// ── Period tanlash ────────────────────────────────────────────────────────────
function setPeriod(val) {
  activePeriod.value = val
  customFrom.value   = ''
  customTo.value     = ''
  customOpen.value   = false
  syncToUrl()
  loadStats()
}

function applyCustom() {
  if (!customFrom.value || !customTo.value || customFrom.value > customTo.value) return
  activePeriod.value = ''
  customOpen.value   = false
  syncToUrl()
  loadStats()
}

function clearCustom() {
  customOpen.value = false
  if (!customFrom.value) return
  customFrom.value = ''
  customTo.value   = ''
  syncToUrl()
  loadStats()
}

function clearAll() {
  activePeriod.value = ''
  customFrom.value   = ''
  customTo.value     = ''
  customOpen.value   = false
  syncToUrl()
  loadStats()
}

// ── Static config ─────────────────────────────────────────────────────────────
const statusItems = computed(() => [
  { key: 'new',         label: t('status.new'),         dot: 'bg-blue-400',   bar: 'bg-blue-400'   },
  { key: 'in_progress', label: t('status.in_progress'), dot: 'bg-yellow-400', bar: 'bg-yellow-400' },
  { key: 'needs_info',  label: t('status.needs_info'),  dot: 'bg-orange-400', bar: 'bg-orange-400' },
  { key: 'completed',   label: t('status.completed'),   dot: 'bg-green-400',  bar: 'bg-green-400'  },
  { key: 'rejected',    label: t('status.rejected'),    dot: 'bg-red-400',    bar: 'bg-red-400'    },
])
const priorityItems = computed(() => [
  { key: 'critical', label: t('priority.critical'), emoji: '🔴', bar: 'bg-red-500'    },
  { key: 'high',     label: t('priority.high'),     emoji: '🟠', bar: 'bg-orange-500' },
  { key: 'medium',   label: t('priority.medium'),   emoji: '🟡', bar: 'bg-yellow-500' },
  { key: 'low',      label: t('priority.low'),      emoji: '🟢', bar: 'bg-green-500'  },
])
const categoryItems = computed(() => [
  { key: 'corruption',           label: t('category_short.corruption'),           color: '#ef4444' },
  { key: 'conflict_of_interest', label: t('category_short.conflict_of_interest'), color: '#f97316' },
  { key: 'fraud',                label: t('category_short.fraud'),                color: '#eab308' },
  { key: 'safety',               label: t('category_short.safety'),               color: '#22c55e' },
  { key: 'discrimination',       label: t('category_short.discrimination'),       color: '#3b82f6' },
  { key: 'procurement',          label: t('category_short.procurement'),          color: '#8b5cf6' },
  { key: 'other',                label: t('category_short.other'),                color: '#64748b' },
])

const statCards = computed(() => [
  { label: t('stats.total'),       value: stats.value?.total                  || 0, icon: '📋', bg: 'bg-brand-600/20'  },
  { label: t('stats.new'),         value: stats.value?.by_status?.new         || 0, icon: '🆕', bg: 'bg-blue-500/20'   },
  { label: t('stats.in_progress'), value: stats.value?.by_status?.in_progress || 0, icon: '🔄', bg: 'bg-yellow-500/20' },
  { label: t('stats.critical'),    value: stats.value?.by_priority?.critical  || 0, icon: '🔴', bg: 'bg-red-500/20'    },
])

const monthlyBars = computed(() => {
  const monthly = stats.value?.monthly_trend || []
  const maxCount = Math.max(...monthly.map(m => m.count), 1)
  return monthly.map(m => ({
    count:  m.count,
    height: Math.max(Math.round((m.count / maxCount) * 120), m.count > 0 ? 4 : 0),
    label:  m.month?.length > 7 ? m.month.slice(5) : m.month,
  }))
})

function getPercent(val) {
  if (!stats.value?.total || !val) return 0
  return Math.min(Math.round((val / stats.value.total) * 100), 100)
}
function getCatPercent(key) {
  const total = Object.values(stats.value?.by_category || {}).reduce((a, b) => a + b, 0)
  if (!total) return 0
  return Math.min(Math.round(((stats.value?.by_category?.[key] || 0) / total) * 100), 100)
}

onMounted(() => {
  readFromUrl()
  loadStats()
})

onUnmounted(() => {
  if (abortCtrl) abortCtrl.abort()
})
</script>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
