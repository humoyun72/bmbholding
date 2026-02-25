<template>
  <div class="p-8 animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-white">Murojaatlar</h1>
        <p class="text-surface-400 text-sm mt-1">Barcha kelgan murojaatlar ro'yxati</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-6">
      <div class="flex items-center gap-4 flex-wrap">
        <select v-model="filters.status" class="input w-auto min-w-40" @change="loadCases">
          <option value="">Barcha holatlar</option>
          <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="filters.category" class="input w-auto min-w-40" @change="loadCases">
          <option value="">Barcha kategoriyalar</option>
          <option v-for="c in categoryOptions" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
        <select v-model="filters.priority" class="input w-auto min-w-40" @change="loadCases">
          <option value="">Barcha ustuvorliklar</option>
          <option v-for="p in priorityOptions" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
        <button @click="resetFilters" class="btn-ghost text-sm">
          Filtrni tozalash
        </button>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
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
              <td class="px-5 py-4">
                <CategoryBadge :category="c.category" />
              </td>
              <td class="px-5 py-4">
                <PriorityBadge :priority="c.priority" />
              </td>
              <td class="px-5 py-4">
                <StatusBadge :status="c.status" />
              </td>
              <td class="px-5 py-4">
                <span :class="c.is_anonymous ? 'text-surface-400' : 'text-green-400'" class="text-xs">
                  {{ c.is_anonymous ? '🔒 Anonim' : '👤 Ochiq' }}
                </span>
              </td>
              <td class="px-5 py-4 text-surface-400 text-sm">
                {{ formatDate(c.created_at) }}
              </td>
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
      <div v-if="pagination.pages > 1" class="flex items-center justify-between px-5 py-4 border-t border-surface-800">
        <span class="text-surface-500 text-sm">
          Jami {{ pagination.total }} ta murojaat
        </span>
        <div class="flex items-center gap-2">
          <button @click="changePage(pagination.page - 1)"
            :disabled="pagination.page <= 1"
            class="btn-ghost text-sm disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5">
            ← Oldingi
          </button>
          <span class="text-surface-400 text-sm">{{ pagination.page }} / {{ pagination.pages }}</span>
          <button @click="changePage(pagination.page + 1)"
            :disabled="pagination.page >= pagination.pages"
            class="btn-ghost text-sm disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5">
            Keyingi →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'
import { format } from 'date-fns'
import api from '@/utils/api'

const router = useRouter()
const loading = ref(true)
const cases = ref([])
const pagination = reactive({ page: 1, pages: 1, total: 0, per_page: 20 })

const filters = reactive({ status: '', category: '', priority: '' })

const columns = [
  { key: 'id', label: 'Murojaat ID' },
  { key: 'category', label: 'Kategoriya' },
  { key: 'priority', label: 'Ustuvorlik' },
  { key: 'status', label: 'Holat' },
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

async function loadCases() {
  loading.value = true
  try {
    const params = { page: pagination.page, per_page: pagination.per_page }
    if (filters.status) params.status = filters.status
    if (filters.category) params.category = filters.category
    if (filters.priority) params.priority = filters.priority

    const { data } = await api.get('/v1/cases', { params })
    cases.value = data.items
    Object.assign(pagination, { page: data.page, pages: data.pages, total: data.total })
  } finally {
    loading.value = false
  }
}

function changePage(p) {
  pagination.page = p
  loadCases()
}

function resetFilters() {
  filters.status = ''
  filters.category = ''
  filters.priority = ''
  pagination.page = 1
  loadCases()
}

function goToCase(id) {
  router.push(`/cases/${id}`)
}

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

onMounted(loadCases)
</script>
