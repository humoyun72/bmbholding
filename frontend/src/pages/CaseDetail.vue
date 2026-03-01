<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in max-w-6xl">
    <!-- Back -->
    <button @click="$router.back()" class="btn-ghost text-sm mb-4 -ml-2">
      ← Orqaga
    </button>

    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <template v-else-if="caseData">
      <!-- Title row -->
      <div class="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <div class="flex items-center gap-2 flex-wrap mb-2">
            <span class="font-mono text-brand-400 text-base sm:text-lg font-semibold">{{ caseData.external_id }}</span>
            <StatusBadge :status="caseData.status" />
            <PriorityBadge :priority="caseData.priority" />
            <span v-if="caseData.is_anonymous" class="badge bg-surface-800 text-surface-400 border border-surface-700">🔒 Anonim</span>
          </div>
          <p class="text-surface-400 text-sm">{{ formatDate(caseData.created_at) }} da yuborilgan</p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2 flex-wrap">
          <select v-model="newStatus" @change="updateStatus" class="input text-sm">
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <button @click="exportCase" class="btn-ghost text-sm whitespace-nowrap">
            📄 Eksport
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main content - left 2/3 -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Description -->
          <div class="card p-6">
            <h3 class="font-semibold text-white mb-4">📝 Murojaat mazmuni</h3>
            <p class="text-surface-200 leading-relaxed whitespace-pre-wrap">{{ caseData.description }}</p>
          </div>

          <!-- Attachments -->
          <div v-if="caseData.attachments?.length" class="card p-6">
            <h3 class="font-semibold text-white mb-4">📎 Biriktirilgan fayllar</h3>
            <div class="space-y-3">
              <div v-for="att in caseData.attachments" :key="att.id"
                class="border border-surface-700 rounded-xl overflow-hidden">

                <!-- Image preview -->
                <div v-if="att.mime_type?.startsWith('image/')"
                  class="bg-surface-950 flex items-center justify-center cursor-pointer max-h-64 overflow-hidden"
                  @click="openPreview(att)">
                  <img
                    :src="`/api/v1/cases/${caseData.external_id}/attachments/${att.id}`"
                    :alt="att.filename"
                    class="max-h-64 max-w-full object-contain hover:opacity-90 transition-opacity"
                    @error="att._imgError = true"
                  />
                </div>

                <!-- Video preview -->
                <div v-else-if="att.mime_type?.startsWith('video/')">
                  <video controls class="w-full max-h-48 bg-black rounded-t-xl">
                    <source :src="`/api/v1/cases/${caseData.external_id}/attachments/${att.id}`"
                      :type="att.mime_type" />
                  </video>
                </div>

                <!-- PDF preview -->
                <div v-else-if="att.mime_type === 'application/pdf'"
                  class="bg-surface-950 cursor-pointer"
                  @click="openPreview(att)">
                  <div class="flex items-center gap-3 p-3 bg-red-500/10 border-b border-surface-700">
                    <span class="text-2xl">📄</span>
                    <span class="text-red-300 text-sm font-medium">PDF hujjat — ko'rish uchun bosing</span>
                  </div>
                </div>

                <!-- File info row -->
                <div class="flex items-center justify-between p-3 bg-surface-800">
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-sm flex-shrink-0">{{ getFileIcon(att.mime_type) }}</span>
                    <div class="min-w-0">
                      <div class="text-white text-sm font-medium truncate">{{ att.filename }}</div>
                      <div class="text-surface-500 text-xs">{{ formatSize(att.size_bytes) }} · {{ att.mime_type }}</div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 flex-shrink-0 ml-3">
                    <button v-if="isPreviewable(att)"
                      @click="openPreview(att)"
                      class="btn-ghost text-xs px-3 py-1.5">
                      👁 Ko'rish
                    </button>
                    <a :href="`/api/v1/cases/${caseData.external_id}/attachments/${att.id}`"
                      class="btn-ghost text-xs px-3 py-1.5"
                      :download="att.filename">
                      ⬇ Yuklab olish
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat / Comments -->
          <div class="card p-6">
            <div class="flex items-center justify-between mb-5">
              <h3 class="font-semibold text-white">💬 Muloqot</h3>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="newComment.is_internal" class="w-4 h-4 rounded accent-brand-500" />
                <span class="text-surface-400 text-sm">Ichki eslatma</span>
              </label>
            </div>

            <!-- Messages -->
            <div class="space-y-4 mb-6 max-h-80 overflow-y-auto">
              <div v-if="!caseData.comments?.length" class="text-center text-surface-600 text-sm py-8">
                Hali xabarlar yo'q
              </div>
              <div v-for="c in caseData.comments" :key="c.id"
                :class="[
                  'flex gap-3',
                  c.is_from_reporter ? 'flex-row' : 'flex-row-reverse'
                ]">
                <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                  :class="c.is_from_reporter ? 'bg-surface-700 text-surface-300' : 'bg-brand-600 text-white'">
                  {{ c.is_from_reporter ? '👤' : (c.author?.[0] || 'A') }}
                </div>
                <div :class="[
                  'max-w-sm p-3 rounded-xl text-sm',
                  c.is_from_reporter
                    ? 'bg-surface-800 text-surface-200'
                    : c.is_internal
                    ? 'bg-amber-900/30 border border-amber-700/30 text-amber-200'
                    : 'bg-brand-600/20 border border-brand-500/20 text-white'
                ]">
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="font-medium text-xs opacity-60">
                      {{ c.is_from_reporter ? 'Murojaat yuborguvchi' : c.author }}
                    </span>
                    <span v-if="c.is_internal" class="text-xs opacity-50">🔒 Ichki</span>
                  </div>
                  {{ c.content }}
                  <div class="text-xs opacity-40 mt-1.5">{{ formatDate(c.created_at) }}</div>
                </div>
              </div>
            </div>

            <!-- Input -->
            <div class="space-y-2">
              <!-- Telegram reply hint -->
              <div v-if="!newComment.is_internal"
                class="flex items-center gap-2 text-xs text-surface-500 px-1">
                <span>📬</span>
                <span v-if="caseData.is_anonymous">
                  Anonim murojaat — javob Telegram orqali yuboriladi (shaxsiyat oshkor bo'lmaydi)
                </span>
                <span v-else>
                  Javob Telegram orqali murojaat yuborguvchiga yuboriladi
                </span>
              </div>
              <div v-else class="flex items-center gap-2 text-xs text-amber-500/70 px-1">
                <span>🔒</span>
                <span>Ichki eslatma — faqat adminlar ko'radi, reporterga yuborilmaydi</span>
              </div>

              <div class="flex gap-3">
                <textarea v-model="newComment.content" rows="2"
                  class="input flex-1 resize-none"
                  :placeholder="newComment.is_internal ? 'Ichki eslatma yozing...' : 'Yuboruvchiga xabar yozing...'">
                </textarea>
                <button @click="sendComment" :disabled="!newComment.content.trim() || sending"
                  class="btn-primary px-4 self-end disabled:opacity-50">
                  <svg v-if="sending" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar - right 1/3 -->
        <div class="space-y-5">
          <!-- Case info -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">Murojaat ma'lumotlari</h3>
            <dl class="space-y-3 text-sm">
              <div>
                <dt class="text-surface-500 text-xs mb-1">Kategoriya</dt>
                <dd class="text-surface-200">{{ categoryLabel(caseData.category) }}</dd>
              </div>
              <div>
                <dt class="text-surface-500 text-xs mb-1">Ustuvorlik</dt>
                <dd><PriorityBadge :priority="caseData.priority" /></dd>
              </div>
              <div>
                <dt class="text-surface-500 text-xs mb-1">Holat</dt>
                <dd><StatusBadge :status="caseData.status" /></dd>
              </div>
              <div v-if="caseData.due_at">
                <dt class="text-surface-500 text-xs mb-1">Muddat</dt>
                <dd class="text-surface-200">{{ formatDate(caseData.due_at) }}</dd>
              </div>
              <div v-if="caseData.closed_at">
                <dt class="text-surface-500 text-xs mb-1">Yopilgan</dt>
                <dd class="text-surface-200">{{ formatDate(caseData.closed_at) }}</dd>
              </div>
              <!-- Reporter IP -->
              <div v-if="caseData.reporter_ip">
                <dt class="text-surface-500 text-xs mb-1">Reporter IP</dt>
                <dd class="text-surface-400 font-mono text-xs">{{ caseData.reporter_ip }}</dd>
              </div>
            </dl>
          </div>

          <!-- Assignment -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">Tayinlash</h3>
            <select v-model="assignedTo" @change="assignCase" class="input text-sm w-full">
              <option value="">Tayinlanmagan</option>
              <option v-for="u in users" :key="u.id" :value="u.id">
                {{ u.full_name || u.username }}
              </option>
            </select>
          </div>

          <!-- Quick actions -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">Tezkor amallar</h3>
            <div class="space-y-2">
              <button @click="setStatus('in_progress')" class="btn-ghost w-full text-sm justify-start">
                🔄 Ko'rib chiqishni boshlash
              </button>
              <button @click="setStatus('needs_info')" class="btn-ghost w-full text-sm justify-start">
                ❓ Qo'shimcha ma'lumot so'rash
              </button>
              <button @click="setStatus('completed')" class="btn-ghost w-full text-sm justify-start text-green-400 hover:text-green-300">
                ✅ Yakunlash
              </button>
              <button @click="setStatus('rejected')" class="btn-ghost w-full text-sm justify-start text-red-400 hover:text-red-300">
                ❌ Rad etish
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Preview Modal ─────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="preview.open"
          class="fixed inset-0 z-[99999] flex items-center justify-center p-4"
          @click.self="preview.open = false">
          <!-- Backdrop -->
          <div class="absolute inset-0 bg-black/80 backdrop-blur-sm"></div>
          <!-- Panel -->
          <div class="relative z-10 bg-surface-900 rounded-2xl border border-surface-700
                      shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
            <!-- Header -->
            <div class="flex items-center justify-between px-5 py-3 border-b border-surface-800">
              <div class="flex items-center gap-3">
                <span>{{ getFileIcon(preview.att?.mime_type) }}</span>
                <span class="text-white text-sm font-medium truncate max-w-xs">{{ preview.att?.filename }}</span>
                <span class="text-surface-500 text-xs">{{ formatSize(preview.att?.size_bytes) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <a :href="`/api/v1/cases/${caseData?.external_id}/attachments/${preview.att?.id}`"
                  :download="preview.att?.filename"
                  class="btn-ghost text-xs px-3 py-1.5">
                  ⬇ Yuklab olish
                </a>
                <button @click="preview.open = false"
                  class="w-8 h-8 rounded-lg hover:bg-surface-700 flex items-center justify-center text-surface-400 hover:text-white transition-colors">
                  ✕
                </button>
              </div>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-auto flex items-center justify-center bg-surface-950 p-4">
              <!-- Image -->
              <img v-if="preview.att?.mime_type?.startsWith('image/')"
                :src="`/api/v1/cases/${caseData?.external_id}/attachments/${preview.att?.id}`"
                :alt="preview.att?.filename"
                class="max-w-full max-h-full object-contain rounded-lg" />

              <!-- PDF -->
              <iframe v-else-if="preview.att?.mime_type === 'application/pdf'"
                :src="`/api/v1/cases/${caseData?.external_id}/attachments/${preview.att?.id}`"
                class="w-full h-[70vh] rounded-lg border-0"
                title="PDF viewer" />

              <!-- Video -->
              <video v-else-if="preview.att?.mime_type?.startsWith('video/')"
                controls autoplay
                class="max-w-full max-h-full rounded-lg">
                <source :src="`/api/v1/cases/${caseData?.external_id}/attachments/${preview.att?.id}`"
                  :type="preview.att?.mime_type" />
              </video>

              <!-- Audio -->
              <audio v-else-if="preview.att?.mime_type?.startsWith('audio/')"
                controls autoplay class="w-full max-w-md">
                <source :src="`/api/v1/cases/${caseData?.external_id}/attachments/${preview.att?.id}`"
                  :type="preview.att?.mime_type" />
              </audio>

              <!-- Other — download only -->
              <div v-else class="text-center text-surface-400 py-16">
                <div class="text-5xl mb-4">📎</div>
                <p class="text-sm mb-4">Bu fayl tur ko'rib bo'lmaydi</p>
                <a :href="`/api/v1/cases/${caseData?.external_id}/attachments/${preview.att?.id}`"
                  :download="preview.att?.filename"
                  class="btn-primary text-sm">
                  ⬇ Yuklab olish
                </a>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { format } from 'date-fns'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const sending = ref(false)
const caseData = ref(null)
const users = ref([])
const newStatus = ref('')
const assignedTo = ref('')
const newComment = reactive({ content: '', is_internal: false })

// Preview modal state
const preview = reactive({ open: false, att: null })

function openPreview(att) {
  preview.att = att
  preview.open = true
}

function isPreviewable(att) {
  if (!att?.mime_type) return false
  return att.mime_type.startsWith('image/') ||
    att.mime_type.startsWith('video/') ||
    att.mime_type.startsWith('audio/') ||
    att.mime_type === 'application/pdf'
}

const statusOptions = [
  { value: 'new', label: 'Yangi' },
  { value: 'in_progress', label: "Ko'rib chiqilmoqda" },
  { value: 'needs_info', label: "Ma'lumot kerak" },
  { value: 'completed', label: 'Yakunlandi' },
  { value: 'rejected', label: 'Rad etildi' },
]

const catLabels = {
  corruption: '🔴 Korrupsiya / Pora',
  conflict_of_interest: "⚖️ Manfaatlar to'qnashuvi",
  fraud: '💸 Firibgarlik / O\'g\'irlik',
  safety: '⚠️ Xavfsizlik buzilishi',
  discrimination: '🚫 Kamsitish / Bezovtalik',
  procurement: '📋 Tender buzilishi',
  other: '❓ Boshqa',
}

function categoryLabel(c) { return catLabels[c] || c }

async function loadCase() {
  loading.value = true
  try {
    const { data } = await api.get(`/v1/cases/${route.params.id}`)
    caseData.value = data
    newStatus.value = data.status
    assignedTo.value = data.assigned_to || ''
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  try {
    const { data } = await api.get('/v1/auth/users')
    users.value = data
  } catch {}
}

async function updateStatus() {
  try {
    await api.post(`/v1/cases/${caseData.value.external_id}/status`, { status: newStatus.value })
    caseData.value.status = newStatus.value
  } catch {}
}

async function setStatus(status) {
  newStatus.value = status
  await updateStatus()
}

async function assignCase() {
  try {
    await api.post(`/v1/cases/${caseData.value.external_id}/assign`, { user_id: assignedTo.value || null })
  } catch {}
}

async function sendComment() {
  if (!newComment.content.trim()) return
  sending.value = true
  try {
    await api.post(`/v1/cases/${caseData.value.external_id}/comment`, {
      content: newComment.content,
      is_internal: newComment.is_internal,
    })
    newComment.content = ''
    await loadCase()
  } finally {
    sending.value = false
  }
}

async function exportCase() {
  window.open(`/api/v1/cases/${caseData.value.external_id}/export`, '_blank')
}

function formatDate(d) { return d ? format(new Date(d), 'dd.MM.yyyy HH:mm') : '—' }
function formatSize(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / (1024 * 1024)).toFixed(1) + ' MB'
}
function getFileIcon(mime) {
  if (mime?.includes('image')) return '🖼️'
  if (mime?.includes('pdf')) return '📄'
  if (mime?.includes('word')) return '📝'
  return '📎'
}

const StatusBadge = defineComponent({
  props: ['status'],
  setup(props) {
    const map = {
      new: { text: 'Yangi', cls: 'bg-blue-500/15 text-blue-400 border border-blue-500/20' },
      in_progress: { text: "Ko'rib chiqilmoqda", cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20' },
      needs_info: { text: "Ma'lumot kerak", cls: 'bg-orange-500/15 text-orange-400 border border-orange-500/20' },
      completed: { text: 'Yakunlandi', cls: 'bg-green-500/15 text-green-400 border border-green-500/20' },
      rejected: { text: 'Rad etildi', cls: 'bg-red-500/15 text-red-400 border border-red-500/20' },
    }
    return () => {
      const s = map[props.status] || { text: props.status, cls: 'bg-surface-700 text-surface-400' }
      return h('span', { class: `badge ${s.cls}` }, s.text)
    }
  }
})

const PriorityBadge = defineComponent({
  props: ['priority'],
  setup(props) {
    const map = {
      critical: { text: '🔴 Kritik', cls: 'bg-red-500/15 text-red-400 border border-red-500/20' },
      high: { text: '🟠 Yuqori', cls: 'bg-orange-500/15 text-orange-400 border border-orange-500/20' },
      medium: { text: "🟡 O'rta", cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20' },
      low: { text: '🟢 Past', cls: 'bg-green-500/15 text-green-400 border border-green-500/20' },
    }
    return () => {
      const p = map[props.priority] || { text: props.priority, cls: '' }
      return h('span', { class: `badge ${p.cls}` }, p.text)
    }
  }
})

onMounted(() => { loadCase(); loadUsers() })
</script>

<style>
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active .relative.z-10,
.modal-leave-active .relative.z-10 {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from .relative.z-10,
.modal-leave-to .relative.z-10 {
  transform: scale(0.95);
  opacity: 0;
}
</style>

