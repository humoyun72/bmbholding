<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <div class="flex items-center justify-between mb-6 gap-3 flex-wrap">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-white">{{ t('polls.title') }}</h1>
        <p class="text-surface-400 text-sm mt-1">{{ t('polls.subtitle') }}</p>
      </div>
      <button @click="showCreate = true" class="btn-primary whitespace-nowrap">
        + {{ t('polls.create') }}
      </button>
    </div>

    <!-- Warning banner -->
    <div v-if="activateWarning"
      class="mb-6 flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/30 rounded-xl px-4 py-3">
      <span class="text-yellow-400 text-lg flex-shrink-0">⚠️</span>
      <div>
        <p class="text-yellow-300 text-sm font-medium">{{ t('polls.activate_warning_title') }}</p>
        <p class="text-yellow-400/70 text-xs mt-0.5">{{ activateWarning }}</p>
        <p class="text-surface-500 text-xs mt-1">{{ t('polls.activate_warning_hint') }}</p>
      </div>
      <button @click="activateWarning = ''" class="ml-auto text-surface-500 hover:text-white">✕</button>
    </div>

    <!-- List -->
    <div class="grid gap-4">
      <div v-if="loading" class="card p-8 text-center">
        <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      </div>

      <div v-for="poll in polls" :key="poll.id"
        class="card p-6 hover:border-surface-700 transition-colors cursor-pointer"
        @click="router.push(`/polls/${poll.id}`)">
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="font-semibold text-white">{{ poll.title }}</h3>
              <span :class="statusClass(poll.status)" class="badge">{{ statusLabel(poll.status) }}</span>
            </div>
            <p v-if="poll.description" class="text-surface-400 text-sm mb-3">{{ poll.description }}</p>
            <div class="flex items-center gap-4 text-surface-500 text-xs">
              <span>{{ t('polls.questions_count', { count: poll.questions_count }) }}</span>
              <span>{{ t('polls.votes_count', { count: poll.total_votes }) }}</span>
              <span>{{ formatDate(poll.created_at) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="poll.status === 'draft'" @click.stop="activatePoll(poll.id)"
              class="btn-primary text-xs px-3 py-1.5">
              ▶ {{ t('polls.activate') }}
            </button>
            <button v-if="poll.status === 'active'" @click.stop="closePoll(poll.id)"
              class="btn-ghost text-xs px-3 py-1.5 text-red-400 hover:text-red-300">
              ■ {{ t('polls.close') }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="!loading && !polls.length" class="card p-12 text-center text-surface-500">
        {{ t('polls.no_polls') }}
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-slide-up">
        <div class="p-6 border-b border-surface-800 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-white">{{ t('polls.create_title') }}</h2>
          <button @click="showCreate = false" class="text-surface-400 hover:text-white transition-colors">✕</button>
        </div>
        <div class="p-6 space-y-5">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('polls.poll_name') }} *</label>
            <input v-model="form.title" class="input" :placeholder="t('polls.poll_name_placeholder')" />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('polls.poll_description') }}</label>
            <textarea v-model="form.description" class="input resize-none" rows="2" :placeholder="t('polls.poll_description_placeholder')"></textarea>
          </div>

          <!-- Questions -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <label class="text-sm font-medium text-surface-300">{{ t('polls.questions_label') }}</label>
              <button @click="addQuestion" class="text-brand-400 text-sm hover:text-brand-300 transition-colors">+ {{ t('polls.add_question') }}</button>
            </div>
            <div class="space-y-4">
              <div v-for="(q, qi) in form.questions" :key="qi" class="bg-surface-800 rounded-xl p-4">
                <div class="flex items-start gap-3 mb-3">
                  <input v-model="q.question_text" class="input flex-1 text-sm" :placeholder="t('polls.question_placeholder', { num: qi + 1 })" />
                  <button @click="removeQuestion(qi)" class="text-surface-500 hover:text-red-400 transition-colors mt-2">✕</button>
                </div>
                <!-- Options -->
                <div class="space-y-2 ml-3">
                  <div v-for="(opt, oi) in q.options" :key="oi" class="flex items-center gap-2">
                    <span class="text-surface-500 text-xs w-5">{{ oi + 1 }}.</span>
                    <input v-model="opt.option_text" class="input flex-1 text-sm" :placeholder="t('polls.option_placeholder', { num: oi + 1 })" />
                    <button @click="removeOption(qi, oi)" class="text-surface-500 hover:text-red-400 transition-colors">✕</button>
                  </div>
                  <button @click="addOption(qi)" class="text-brand-400 text-xs hover:text-brand-300 transition-colors ml-5">+ {{ t('polls.add_option') }}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="p-6 border-t border-surface-800 flex gap-3 justify-end">
          <button @click="showCreate = false" class="btn-ghost">{{ t('polls.cancel') }}</button>
          <button @click="createPoll" :disabled="saving" class="btn-primary">
            {{ saving ? t('polls.saving') : t('polls.create_btn') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { format } from 'date-fns'
import api from '@/utils/api'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const { t } = useI18n()
const loading = ref(true)
const saving = ref(false)
const showCreate = ref(false)
const polls = ref([])
const activateWarning = ref('')

const form = reactive({
  title: '',
  description: '',
  questions: [{ question_text: '', options: [{ option_text: '' }, { option_text: '' }] }]
})

function addQuestion() {
  form.questions.push({ question_text: '', options: [{ option_text: '' }, { option_text: '' }] })
}
function removeQuestion(i) { form.questions.splice(i, 1) }
function addOption(qi) { form.questions[qi].options.push({ option_text: '' }) }
function removeOption(qi, oi) { form.questions[qi].options.splice(oi, 1) }

async function loadPolls() {
  loading.value = true
  try {
    const { data } = await api.get('/v1/polls')
    polls.value = data
  } finally {
    loading.value = false
  }
}

async function createPoll() {
  saving.value = true
  try {
    const payload = {
      title: form.title,
      description: form.description || null,
      questions: form.questions.map((q, i) => ({
        question_text: q.question_text,
        order: i,
        options: q.options.map((o, j) => ({ option_text: o.option_text, order: j }))
      }))
    }
    await api.post('/v1/polls', payload)
    showCreate.value = false
    form.title = ''
    form.description = ''
    form.questions = [{ question_text: '', options: [{ option_text: '' }, { option_text: '' }] }]
    await loadPolls()
  } finally {
    saving.value = false
  }
}

async function activatePoll(id) {
  try {
    const { data } = await api.post(`/v1/polls/${id}/activate`)
    if (data.warning) {
      activateWarning.value = data.warning
      setTimeout(() => { activateWarning.value = '' }, 8000)
    }
  } catch (e) {
    console.error(e)
  }
  await loadPolls()
}

async function closePoll(id) {
  await api.post(`/v1/polls/${id}/close`)
  await loadPolls()
}

function statusClass(s) {
  return s === 'active' ? 'bg-green-500/15 text-green-400 border border-green-500/20'
    : s === 'closed' ? 'bg-surface-700/50 text-surface-400'
    : 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20'
}
function statusLabel(s) {
  return s === 'active' ? t('polls.status_active') : s === 'closed' ? t('polls.status_closed') : t('polls.status_draft')
}
function formatDate(d) { return d ? format(new Date(d), 'dd.MM.yyyy') : '' }

onMounted(loadPolls)
</script>
