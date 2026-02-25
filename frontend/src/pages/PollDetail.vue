<template>
  <div class="p-8 animate-fade-in">
    <button @click="$router.back()" class="btn-ghost text-sm mb-6 -ml-2">← Orqaga</button>

    <div v-if="loading" class="flex items-center justify-center h-48">
      <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else-if="poll">
      <div class="flex items-center gap-3 mb-2">
        <h1 class="text-2xl font-bold text-white">{{ poll.title }}</h1>
        <span :class="statusClass(poll.status)" class="badge">{{ statusLabel(poll.status) }}</span>
      </div>
      <p v-if="poll.description" class="text-surface-400 text-sm mb-8">{{ poll.description }}</p>

      <div class="space-y-6">
        <div v-for="q in poll.questions" :key="q.id" class="card p-6">
          <h3 class="font-semibold text-white mb-5">{{ q.question_text }}</h3>
          <div class="space-y-3">
            <div v-for="opt in q.options" :key="opt.id" class="space-y-1.5">
              <div class="flex items-center justify-between text-sm">
                <span class="text-surface-200">{{ opt.option_text }}</span>
                <span class="text-surface-400 font-medium">{{ opt.vote_count }} ovoz</span>
              </div>
              <div class="w-full bg-surface-800 rounded-full h-2 overflow-hidden">
                <div class="h-full bg-brand-500 rounded-full transition-all duration-700"
                  :style="{ width: `${getPercent(q.options, opt.vote_count)}%` }"></div>
              </div>
            </div>
          </div>
          <div class="text-surface-600 text-xs mt-4">
            Jami: {{ q.options.reduce((s, o) => s + o.vote_count, 0) }} ovoz
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/utils/api'

const route = useRoute()
const loading = ref(true)
const poll = ref(null)

function getPercent(options, count) {
  const total = options.reduce((s, o) => s + o.vote_count, 0)
  return total ? Math.round((count / total) * 100) : 0
}
function statusClass(s) {
  return s === 'active' ? 'bg-green-500/15 text-green-400 border border-green-500/20'
    : s === 'closed' ? 'bg-surface-700/50 text-surface-400'
    : 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20'
}
function statusLabel(s) {
  return s === 'active' ? '● Faol' : s === 'closed' ? 'Yopiq' : 'Qoralama'
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get(`/v1/polls/${route.params.id}`)
    poll.value = data
  } finally {
    loading.value = false
  }
})
</script>
