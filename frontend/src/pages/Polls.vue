<template>
  <div class="p-8 animate-fade-in">
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold text-white">So'rovnomalar</h1>
        <p class="text-surface-400 text-sm mt-1">Telegram orqali so'rovnomalar yaratish va boshqarish</p>
      </div>
      <button @click="showCreate = true" class="btn-primary">
        + Yangi so'rovnoma
      </button>
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
              <span>{{ poll.questions_count }} ta savol</span>
              <span>{{ poll.total_votes }} ta ovoz</span>
              <span>{{ formatDate(poll.created_at) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="poll.status === 'draft'" @click.stop="activatePoll(poll.id)"
              class="btn-primary text-xs px-3 py-1.5">
              ▶ Faollashtirish
            </button>
            <button v-if="poll.status === 'active'" @click.stop="closePoll(poll.id)"
              class="btn-ghost text-xs px-3 py-1.5 text-red-400 hover:text-red-300">
              ■ Yopish
            </button>
          </div>
        </div>
      </div>

      <div v-if="!loading && !polls.length" class="card p-12 text-center text-surface-500">
        Hali so'rovnomalar yo'q. Birinchisini yarating!
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-slide-up">
        <div class="p-6 border-b border-surface-800 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-white">Yangi so'rovnoma</h2>
          <button @click="showCreate = false" class="text-surface-400 hover:text-white transition-colors">✕</button>
        </div>
        <div class="p-6 space-y-5">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">So'rovnoma nomi *</label>
            <input v-model="form.title" class="input" placeholder="Masalan: Mart oyi anonim so'rovnomasi" />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-2">Tavsif</label>
            <textarea v-model="form.description" class="input resize-none" rows="2" placeholder="Qo'shimcha ma'lumot..."></textarea>
          </div>

          <!-- Questions -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <label class="text-sm font-medium text-surface-300">Savollar</label>
              <button @click="addQuestion" class="text-brand-400 text-sm hover:text-brand-300 transition-colors">+ Savol qo'shish</button>
            </div>
            <div class="space-y-4">
              <div v-for="(q, qi) in form.questions" :key="qi" class="bg-surface-800 rounded-xl p-4">
                <div class="flex items-start gap-3 mb-3">
                  <input v-model="q.question_text" class="input flex-1 text-sm" :placeholder="`${qi + 1}-savol matni`" />
                  <button @click="removeQuestion(qi)" class="text-surface-500 hover:text-red-400 transition-colors mt-2">✕</button>
                </div>
                <!-- Options -->
                <div class="space-y-2 ml-3">
                  <div v-for="(opt, oi) in q.options" :key="oi" class="flex items-center gap-2">
                    <span class="text-surface-500 text-xs w-5">{{ oi + 1 }}.</span>
                    <input v-model="opt.option_text" class="input flex-1 text-sm" :placeholder="`Variant ${oi + 1}`" />
                    <button @click="removeOption(qi, oi)" class="text-surface-500 hover:text-red-400 transition-colors">✕</button>
                  </div>
                  <button @click="addOption(qi)" class="text-brand-400 text-xs hover:text-brand-300 transition-colors ml-5">+ Variant qo'shish</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="p-6 border-t border-surface-800 flex gap-3 justify-end">
          <button @click="showCreate = false" class="btn-ghost">Bekor qilish</button>
          <button @click="createPoll" :disabled="saving" class="btn-primary">
            {{ saving ? 'Saqlanmoqda...' : 'Yaratish' }}
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

const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const showCreate = ref(false)
const polls = ref([])

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
  await api.post(`/v1/polls/${id}/activate`)
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
  return s === 'active' ? '● Faol' : s === 'closed' ? 'Yopiq' : 'Qoralama'
}
function formatDate(d) { return d ? format(new Date(d), 'dd.MM.yyyy') : '' }

onMounted(loadPolls)
</script>
