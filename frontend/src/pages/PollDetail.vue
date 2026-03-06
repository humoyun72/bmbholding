<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <button @click="$router.back()" class="btn-ghost text-sm mb-4 -ml-2">← {{ t('poll_detail.back') }}</button>

    <div v-if="loading" class="flex items-center justify-center h-48">
      <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else-if="poll">
      <!-- Header -->
      <div class="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <div class="flex items-center gap-2 flex-wrap mb-2">
            <h1 class="text-xl sm:text-2xl font-bold text-white">{{ poll.title }}</h1>
            <span :class="statusClass(poll.status)" class="badge">{{ statusLabel(poll.status) }}</span>
            <span v-if="poll.status === 'active'"
              class="flex items-center gap-1.5 text-xs text-green-400">
              <span class="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
              {{ t('poll_detail.live') }}
            </span>
          </div>
          <p v-if="poll.description" class="text-surface-400 text-sm">{{ poll.description }}</p>
        </div>

        <!-- Telegram delivery info -->
        <div v-if="poll.status === 'active' && hasTelegramPoll"
          class="bg-blue-500/10 border border-blue-500/20 rounded-xl px-3 py-2 text-sm">
          <div class="text-blue-400 font-medium">📤 {{ t('poll_detail.tg_active') }}</div>
          <div class="text-surface-400 text-xs">{{ t('poll_detail.tg_votes_auto') }}</div>
        </div>
        <div v-else-if="poll.status === 'active' && !hasTelegramPoll"
          class="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-3 py-2 text-sm">
          <div class="text-yellow-400 font-medium">⚠️ {{ t('poll_detail.tg_not_sent') }}</div>
          <div class="text-surface-400 text-xs">{{ t('poll_detail.tg_not_configured') }}</div>
        </div>
      </div>

      <!-- Total stats -->
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div class="card p-4 flex items-center gap-3">
          <div class="w-9 h-9 bg-brand-600/20 rounded-xl flex items-center justify-center text-lg">📊</div>
          <div>
            <div class="text-white font-bold text-xl">{{ totalVotes }}</div>
            <div class="text-surface-500 text-xs">{{ t('poll_detail.total_votes') }}</div>
          </div>
        </div>
        <div class="card p-4 flex items-center gap-3">
          <div class="w-9 h-9 bg-purple-500/20 rounded-xl flex items-center justify-center text-lg">❓</div>
          <div>
            <div class="text-white font-bold text-xl">{{ poll.questions?.length || 0 }}</div>
            <div class="text-surface-500 text-xs">{{ t('poll_detail.questions') }}</div>
          </div>
        </div>
        <div v-if="lastVoteAt" class="card p-4 flex items-center gap-3">
          <div class="w-9 h-9 bg-green-500/20 rounded-xl flex items-center justify-center text-lg">🕐</div>
          <div>
            <div class="text-white font-bold text-sm">{{ lastVoteAt }}</div>
            <div class="text-surface-500 text-xs">{{ t('poll_detail.last_vote') }}</div>
          </div>
        </div>
      </div>

      <!-- Questions -->
      <div class="space-y-6">
        <div v-for="q in poll.questions" :key="q.id" class="card p-6">
          <div class="flex items-center justify-between mb-5">
            <h3 class="font-semibold text-white">{{ q.question_text }}</h3>
            <span class="text-surface-500 text-xs">
              {{ q.options.reduce((s, o) => s + o.vote_count, 0) }} {{ t('poll_detail.votes') }}
            </span>
          </div>
          <div class="space-y-3">
            <div v-for="opt in q.options" :key="opt.id" class="space-y-1.5">
              <div class="flex items-center justify-between text-sm">
                <span class="text-surface-200">{{ opt.option_text }}</span>
                <div class="flex items-center gap-2 text-surface-400">
                  <span class="font-medium">{{ opt.vote_count }}</span>
                  <span class="text-surface-600 text-xs">
                    ({{ getPercent(q.options, opt.vote_count) }}%)
                  </span>
                </div>
              </div>
              <div class="w-full bg-surface-800 rounded-full h-2.5 overflow-hidden">
                <div class="h-full rounded-full transition-all duration-700"
                  :class="getBarColor(q.options, opt)"
                  :style="{ width: `${getPercent(q.options, opt.vote_count)}%` }"></div>
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
import { useRoute } from 'vue-router'
import api from '@/utils/api'
import { useNotificationStore } from '@/stores/notifications'
import { watch } from 'vue'
import { useI18n } from '@/composables/useI18n'

const route = useRoute()
const { t } = useI18n()
const loading = ref(true)
const poll = ref(null)
const lastVoteAt = ref(null)
const notifStore = useNotificationStore()

const totalVotes = computed(() => {
  if (!poll.value) return 0
  return poll.value.questions?.reduce((sum, q) =>
    sum + q.options.reduce((s, o) => s + o.vote_count, 0), 0) || 0
})

const hasTelegramPoll = computed(() =>
  poll.value?.questions?.some(q => q.telegram_message_id)
)

async function loadPoll() {
  try {
    const { data } = await api.get(`/v1/polls/${route.params.id}`)
    poll.value = data
  } catch (e) {
    console.error(e)
  }
}

// Watch WebSocket notifications for poll_vote events
watch(() => notifStore.notifications, (newNotifs) => {
  if (!newNotifs.length) return
  const latest = newNotifs[0]
  if (latest?.type === 'poll_vote' && latest?.poll_id === route.params.id) {
    lastVoteAt.value = new Date().toLocaleTimeString('uz-UZ')
    loadPoll()  // reload updated vote counts
  }
}, { deep: true })

function getPercent(options, count) {
  const total = options.reduce((s, o) => s + o.vote_count, 0)
  return total ? Math.round((count / total) * 100) : 0
}

const BAR_COLORS = [
  'bg-brand-500', 'bg-green-500', 'bg-blue-500', 'bg-yellow-500',
  'bg-purple-500', 'bg-pink-500', 'bg-orange-500', 'bg-cyan-500',
]
function getBarColor(options, opt) {
  const idx = options.indexOf(opt)
  return BAR_COLORS[idx % BAR_COLORS.length]
}

function statusClass(s) {
  return s === 'active' ? 'bg-green-500/15 text-green-400 border border-green-500/20'
    : s === 'closed' ? 'bg-surface-700/50 text-surface-400'
    : 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20'
}
function statusLabel(s) {
  return s === 'active' ? t('polls.status_active') : s === 'closed' ? t('polls.status_closed') : t('polls.status_draft')
}

onMounted(async () => {
  loading.value = true
  await loadPoll()
  loading.value = false
})
</script>
