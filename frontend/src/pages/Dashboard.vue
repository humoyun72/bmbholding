<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white">Bosh sahifa</h1>
      <p class="text-surface-400 text-sm mt-1">Barcha murojaatlar va tizim holati</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="flex flex-col items-center gap-3">
        <div class="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-surface-400 text-sm">Ma'lumotlar yuklanmoqda...</span>
      </div>
    </div>

    <template v-else>
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

        <!-- Monthly trend — SVG bar chart -->
        <div class="card p-6 lg:col-span-2">
          <div class="mb-5">
            <h3 class="font-semibold text-white">Oylik dinamika</h3>
            <p class="text-surface-500 text-xs mt-0.5">So'nggi 6 oy</p>
          </div>
          <div class="flex items-end justify-between gap-2 h-40">
            <div v-for="(item, i) in monthlyBars" :key="i"
              class="flex flex-col items-center gap-1 flex-1">
              <span class="text-surface-400 text-xs">{{ item.count }}</span>
              <div class="w-full rounded-t-md bg-brand-600 transition-all duration-700"
                :style="{ height: item.height + 'px' }"></div>
              <span class="text-surface-500 text-xs">{{ item.label }}</span>
            </div>
          </div>
        </div>

        <!-- Category donut — CSS-only -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">Kategoriya bo'yicha</h3>
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
        <!-- Status -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">Holat bo'yicha</h3>
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

        <!-- Priority -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">Ustuvorlik bo'yicha</h3>
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
import { ref, computed, onMounted } from 'vue'
import api from '@/utils/api'

const loading = ref(true)
const stats = ref(null)

const statusItems = [
  { key: 'new',         label: 'Yangi',              dot: 'bg-blue-400',   bar: 'bg-blue-400'   },
  { key: 'in_progress', label: "Ko'rib chiqilmoqda", dot: 'bg-yellow-400', bar: 'bg-yellow-400' },
  { key: 'needs_info',  label: "Ma'lumot kerak",     dot: 'bg-orange-400', bar: 'bg-orange-400' },
  { key: 'completed',   label: 'Yakunlandi',          dot: 'bg-green-400',  bar: 'bg-green-400'  },
  { key: 'rejected',    label: 'Rad etildi',          dot: 'bg-red-400',    bar: 'bg-red-400'    },
]

const priorityItems = [
  { key: 'critical', label: 'Kritik',  emoji: '🔴', bar: 'bg-red-500'    },
  { key: 'high',     label: 'Yuqori',  emoji: '🟠', bar: 'bg-orange-500' },
  { key: 'medium',   label: "O'rta",   emoji: '🟡', bar: 'bg-yellow-500' },
  { key: 'low',      label: 'Past',    emoji: '🟢', bar: 'bg-green-500'  },
]

const categoryItems = [
  { key: 'corruption',          label: 'Korrupsiya',   color: '#ef4444' },
  { key: 'conflict_of_interest',label: 'Manfaat to\'q', color: '#f97316' },
  { key: 'fraud',               label: 'Firibgarlik',  color: '#eab308' },
  { key: 'safety',              label: 'Xavfsizlik',   color: '#22c55e' },
  { key: 'discrimination',      label: 'Kamsitish',    color: '#3b82f6' },
  { key: 'procurement',         label: 'Tender',       color: '#8b5cf6' },
  { key: 'other',               label: 'Boshqa',       color: '#64748b' },
]

const statCards = computed(() => [
  { label: 'Jami murojaatlar',    value: stats.value?.total                    || 0, icon: '📋', bg: 'bg-brand-600/20'  },
  { label: 'Yangi',               value: stats.value?.by_status?.new           || 0, icon: '🆕', bg: 'bg-blue-500/20'   },
  { label: "Ko'rib chiqilmoqda",  value: stats.value?.by_status?.in_progress   || 0, icon: '🔄', bg: 'bg-yellow-500/20' },
  { label: 'Kritik',              value: stats.value?.by_priority?.critical     || 0, icon: '🔴', bg: 'bg-red-500/20'    },
])

// Monthly bar chart — max height 120px
const monthlyBars = computed(() => {
  const monthly = stats.value?.monthly_trend || []
  const maxCount = Math.max(...monthly.map(m => m.count), 1)
  return monthly.map(m => ({
    count: m.count,
    height: Math.max(Math.round((m.count / maxCount) * 120), 4),
    label: m.month?.slice(5) || m.month, // show "MM" only
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

onMounted(async () => {
  try {
    const { data } = await api.get('/v1/cases/stats')
    stats.value = data
  } finally {
    loading.value = false
  }
})
</script>

