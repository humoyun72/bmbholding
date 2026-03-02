<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in max-w-6xl">
    <button @click="$router.back()" class="btn-ghost text-sm mb-4 -ml-2">← Orqaga</button>

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
        <div class="flex items-center gap-2 flex-wrap">
          <select v-model="newStatus" @change="updateStatus" class="input text-sm">
            <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <button @click="exportCase" class="btn-ghost text-sm whitespace-nowrap">📄 Eksport</button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main content -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Description -->
          <div class="card p-6">
            <h3 class="font-semibold text-white mb-4">📝 Murojaat mazmuni</h3>
            <p class="text-surface-200 leading-relaxed whitespace-pre-wrap">{{ caseData.description }}</p>
          </div>

          <!-- Attachments — foydalanuvchi yuborgan fayllar -->
          <div v-if="reporterAttachments.length" class="card p-6">
            <h3 class="font-semibold text-white mb-4">
              📎 Yuboruvchi yuborgan fayllar
              <span class="text-surface-500 text-sm font-normal ml-2">({{ reporterAttachments.length }} ta)</span>
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div v-for="att in reporterAttachments" :key="att.id"
                class="border border-surface-700 rounded-xl overflow-hidden bg-surface-900 hover:border-surface-600 transition-colors">

                <!-- Rasm thumbnail -->
                <div v-if="isImage(att)" @click="attUrl(att) && openPreview(att)"
                  class="bg-surface-950 flex items-center justify-center overflow-hidden"
                  :class="attUrl(att) ? 'cursor-pointer' : 'cursor-wait'"
                  style="height:180px">
                  <div v-if="!attUrl(att)" class="flex flex-col items-center gap-2 text-surface-600">
                    <div class="w-6 h-6 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin"></div>
                    <span class="text-xs">Yuklanmoqda...</span>
                  </div>
                  <img v-else :src="attUrl(att)" :alt="att.filename"
                    class="w-full h-full object-cover hover:opacity-90 transition-opacity" />
                </div>

                <!-- Video player — lazy blob load -->
                <div v-else-if="isVideo(att)" class="bg-black relative" style="height:180px">
                  <!-- Blob yuklanmagan — play tugmasi ko'rsatamiz -->
                  <div v-if="!attUrl(att)"
                    class="w-full h-full flex flex-col items-center justify-center gap-2 cursor-pointer hover:bg-white/5 transition-colors"
                    @click="loadBlobUrl(att)">
                    <div v-if="loadingBlobs[att.id]" class="w-8 h-8 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin"></div>
                    <template v-else>
                      <div class="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                        <svg class="w-6 h-6 text-white ml-1" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                      </div>
                      <span class="text-surface-400 text-xs">Videoni yuklash uchun bosing</span>
                    </template>
                  </div>
                  <!-- Blob tayyor — video player -->
                  <video v-else controls class="w-full h-full object-contain">
                    <source :src="attUrl(att)" :type="att.mime_type" />
                  </video>
                </div>

                <!-- Audio player — lazy blob load -->
                <div v-else-if="isAudio(att)"
                  class="bg-surface-800 flex flex-col items-center justify-center gap-2 p-4" style="height:120px">
                  <div class="text-2xl">🎵</div>
                  <div v-if="!attUrl(att)"
                    class="flex items-center gap-2 cursor-pointer hover:text-white transition-colors text-surface-400 text-xs"
                    @click="loadBlobUrl(att)">
                    <div v-if="loadingBlobs[att.id]" class="w-4 h-4 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin"></div>
                    <span v-else>▶ Ovozni yuklash uchun bosing</span>
                  </div>
                  <audio v-else controls class="w-full max-w-full" style="height:36px">
                    <source :src="attUrl(att)" :type="att.mime_type" />
                  </audio>
                </div>


                <!-- PDF -->
                <div v-else-if="isPdf(att)" @click="openPreview(att)"
                  class="cursor-pointer bg-red-900/20 flex items-center justify-center gap-3 p-4" style="height:100px">
                  <span class="text-4xl">📄</span>
                  <span class="text-red-300 text-sm">PDF — ko'rish uchun bosing</span>
                </div>

                <!-- Boshqa fayllar -->
                <div v-else class="bg-surface-800 flex items-center justify-center gap-2 p-4" style="height:80px">
                  <span class="text-3xl">{{ getFileIcon(att.mime_type) }}</span>
                  <span class="text-surface-400 text-sm">{{ att.mime_type }}</span>
                </div>

                <!-- Footer -->
                <div class="flex items-center justify-between p-3 bg-surface-800 border-t border-surface-700">
                  <div class="min-w-0 flex-1">
                    <div class="text-white text-xs font-medium truncate">{{ att.filename }}</div>
                    <div class="text-surface-500 text-xs">{{ formatSize(att.size_bytes) }}</div>
                  </div>
                  <div class="flex items-center gap-1 ml-2 flex-shrink-0">
                    <button v-if="isPreviewable(att)" @click="openPreview(att)"
                      class="p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors" title="Ko'rish">
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                    </button>
                    <!-- Blob URL bor bo'lsa — to'g'ri download, yo'q bo'lsa — API orqali yuklab olish -->
                    <a v-if="attUrl(att)" :href="attUrl(att)" :download="att.filename"
                      class="p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors" title="Yuklab olish">
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                    </a>
                    <button v-else @click="downloadAtt(att)"
                      class="p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors" title="Yuklab olish">
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat / Muloqot -->
          <div class="card p-6">
            <div class="flex items-center justify-between mb-5">
              <h3 class="font-semibold text-white">💬 Muloqot</h3>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="newComment.is_internal" class="w-4 h-4 rounded accent-brand-500" />
                <span class="text-surface-400 text-sm">Ichki eslatma</span>
              </label>
            </div>

            <!-- Xabarlar -->
            <div ref="chatEl" class="space-y-3 mb-5 max-h-96 overflow-y-auto pr-1">
              <div v-if="!caseData.comments?.length" class="text-center text-surface-600 text-sm py-10">
                Hali xabarlar yo'q
              </div>
              <div v-for="c in caseData.comments" :key="c.id"
                :class="['flex gap-2', c.is_from_reporter ? 'flex-row' : 'flex-row-reverse']">
                <!-- Avatar -->
                <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-1"
                  :class="c.is_from_reporter ? 'bg-surface-700 text-surface-300' : 'bg-brand-600 text-white'">
                  {{ c.is_from_reporter ? '👤' : (c.author?.[0]?.toUpperCase() || 'A') }}
                </div>
                <!-- Xabar bubble -->
                <div class="max-w-xs lg:max-w-sm">
                  <div :class="[
                    'p-3 rounded-2xl text-sm',
                    c.is_from_reporter
                      ? 'bg-surface-800 text-surface-200 rounded-tl-none'
                      : c.is_internal
                        ? 'bg-amber-900/30 border border-amber-700/40 text-amber-200 rounded-tr-none'
                        : 'bg-brand-600/25 border border-brand-500/25 text-white rounded-tr-none'
                  ]">
                    <div class="text-xs opacity-50 mb-1 font-medium">
                      {{ c.is_from_reporter ? '👤 Murojaat yuborguvchi' : `👨‍💼 ${c.author}` }}
                      <span v-if="c.is_internal" class="ml-1 text-amber-400">🔒</span>
                    </div>
                    <!-- Fayl xabari -->
                    <div v-if="c._attachment" class="mb-2">
                      <!-- Inline rasm -->
                      <img v-if="isImage(c._attachment)"
                        :src="attUrl(c._attachment)" :alt="c._attachment.filename"
                        @click="openPreview(c._attachment)"
                        class="rounded-lg max-w-full cursor-pointer hover:opacity-90 transition-opacity mb-1"
                        style="max-height:200px; object-fit:cover" />
                      <!-- Video -->
                      <video v-else-if="isVideo(c._attachment)" controls
                        class="rounded-lg max-w-full mb-1" style="max-height:180px">
                        <source :src="attUrl(c._attachment)" :type="c._attachment.mime_type" />
                      </video>
                      <!-- Audio -->
                      <audio v-else-if="isAudio(c._attachment)" controls class="w-full mb-1">
                        <source :src="attUrl(c._attachment)" :type="c._attachment.mime_type" />
                      </audio>
                      <!-- Boshqa -->
                      <div v-else class="flex items-center gap-2 bg-surface-700/50 rounded-lg p-2 mb-1">
                        <span>{{ getFileIcon(c._attachment.mime_type) }}</span>
                        <span class="text-xs truncate">{{ c._attachment.filename }}</span>
                        <a :href="attUrl(c._attachment)" :download="c._attachment.filename"
                          class="text-brand-400 hover:text-brand-300 text-xs ml-auto flex-shrink-0">⬇</a>
                      </div>
                    </div>
                    <div class="whitespace-pre-wrap break-words">{{ c.content }}</div>
                    <div class="text-xs opacity-35 mt-1.5 text-right">{{ formatDate(c.created_at) }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Input area -->
            <div class="border-t border-surface-800 pt-4 space-y-3">
              <!-- Hint -->
              <div v-if="!newComment.is_internal" class="flex items-center gap-2 text-xs text-surface-500">
                <span>📬</span>
                <span>{{ caseData.is_anonymous ? 'Anonim — javob Telegram orqali yuboriladi' : 'Javob Telegram orqali yuboriladi' }}</span>
              </div>
              <div v-else class="flex items-center gap-2 text-xs text-amber-500/70">
                <span>🔒</span><span>Ichki eslatma — faqat adminlar ko'radi</span>
              </div>

              <!-- Fayl preview (upload uchun tanlangan) -->
              <div v-if="uploadFile" class="flex items-center gap-2 bg-surface-800 rounded-xl px-3 py-2">
                <span class="text-lg">{{ getFileIcon(uploadFile.type) }}</span>
                <span class="text-sm text-white truncate flex-1">{{ uploadFile.name }}</span>
                <span class="text-xs text-surface-500">{{ formatSize(uploadFile.size) }}</span>
                <button @click="uploadFile = null" class="text-surface-400 hover:text-red-400 transition-colors ml-1">✕</button>
              </div>

              <!-- Matn + tugmalar -->
              <div class="flex gap-2 items-end">
                <!-- Fayl biriktirish -->
                <label class="flex-shrink-0 w-9 h-9 rounded-xl hover:bg-surface-700 flex items-center justify-center text-surface-400 hover:text-white cursor-pointer transition-colors" title="Fayl biriktirish">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
                  <input type="file" class="hidden" ref="fileInputRef"
                    accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.zip,.txt"
                    @change="onFileSelect" />
                </label>

                <textarea v-model="newComment.content" rows="2"
                  class="input flex-1 resize-none text-sm"
                  :placeholder="newComment.is_internal ? 'Ichki eslatma...' : 'Xabar yozing...'"
                  @keydown.ctrl.enter="sendMessage">
                </textarea>

                <button @click="sendMessage"
                  :disabled="(!newComment.content.trim() && !uploadFile) || sending"
                  class="flex-shrink-0 w-9 h-9 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 rounded-xl flex items-center justify-center transition-colors">
                  <svg v-if="sending" class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <svg v-else class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                  </svg>
                </button>
              </div>
              <p class="text-xs text-surface-600">Ctrl+Enter — yuborish</p>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="space-y-5">
          <!-- Case info -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">Murojaat ma'lumotlari</h3>
            <dl class="space-y-3 text-sm">
              <div><dt class="text-surface-500 text-xs mb-1">Kategoriya</dt><dd class="text-surface-200">{{ categoryLabel(caseData.category) }}</dd></div>
              <div><dt class="text-surface-500 text-xs mb-1">Ustuvorlik</dt><dd><PriorityBadge :priority="caseData.priority" /></dd></div>
              <div><dt class="text-surface-500 text-xs mb-1">Holat</dt><dd><StatusBadge :status="caseData.status" /></dd></div>
              <div v-if="caseData.due_at"><dt class="text-surface-500 text-xs mb-1">Muddat</dt><dd class="text-surface-200">{{ formatDate(caseData.due_at) }}</dd></div>
              <div v-if="caseData.closed_at"><dt class="text-surface-500 text-xs mb-1">Yopilgan</dt><dd class="text-surface-200">{{ formatDate(caseData.closed_at) }}</dd></div>
            </dl>
          </div>

          <!-- Assignment -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">Tayinlash</h3>
            <select v-model="assignedTo" @change="assignCase" class="input text-sm w-full">
              <option value="">Tayinlanmagan</option>
              <option v-for="u in users" :key="u.id" :value="u.id">{{ u.full_name || u.username }}</option>
            </select>
          </div>

          <!-- Tezkor amallar -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">Tezkor amallar</h3>
            <div class="space-y-2">
              <button @click="setStatus('in_progress')" class="btn-ghost w-full text-sm justify-start">🔄 Ko'rib chiqishni boshlash</button>
              <button @click="setStatus('needs_info')" class="btn-ghost w-full text-sm justify-start">❓ Qo'shimcha ma'lumot so'rash</button>
              <button @click="setStatus('completed')" class="btn-ghost w-full text-sm justify-start text-green-400 hover:text-green-300">✅ Yakunlash</button>
              <button @click="setStatus('rejected')" class="btn-ghost w-full text-sm justify-start text-red-400 hover:text-red-300">❌ Rad etish</button>
            </div>
          </div>

          <!-- Jira Ticket -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">🎫 Tiket tizimi</h3>
            <div v-if="caseData.jira_ticket_id" class="space-y-2">
              <div class="text-xs text-green-400">✅ Tiket yaratilgan</div>
              <div class="bg-surface-800 rounded-lg p-3">
                <div class="text-white font-mono text-sm">{{ caseData.jira_ticket_id }}</div>
                <a v-if="caseData.jira_ticket_url" :href="caseData.jira_ticket_url" target="_blank"
                  class="text-brand-400 hover:text-brand-300 text-xs flex items-center gap-1 mt-1">🔗 Tiketni ochish</a>
              </div>
            </div>
            <div v-else class="space-y-2">
              <p class="text-surface-500 text-xs">Tiket yaratilmagan.</p>
              <button @click="createTicket" :disabled="ticketCreating"
                class="btn-ghost w-full text-sm justify-center disabled:opacity-50">
                <svg v-if="ticketCreating" class="w-4 h-4 animate-spin mr-1" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                <span v-else class="mr-1">🎫</span>
                {{ ticketCreating ? 'Yaratilmoqda...' : 'Tiket yaratish' }}
              </button>
              <p v-if="ticketError" class="text-red-400 text-xs">{{ ticketError }}</p>
              <p v-if="ticketSkipped" class="text-surface-500 text-xs">{{ ticketSkipped }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Preview Modal ── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="preview.open" class="fixed inset-0 z-[99999] flex items-center justify-center p-4"
          @click.self="preview.open = false">
          <div class="absolute inset-0 bg-black/85 backdrop-blur-sm"></div>
          <div class="relative z-10 bg-surface-900 rounded-2xl border border-surface-700 shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden">
            <!-- Header -->
            <div class="flex items-center justify-between px-5 py-3 border-b border-surface-800 flex-shrink-0">
              <div class="flex items-center gap-3 min-w-0">
                <span class="text-xl flex-shrink-0">{{ getFileIcon(preview.att?.mime_type) }}</span>
                <div class="min-w-0">
                  <div class="text-white text-sm font-medium truncate">{{ preview.att?.filename }}</div>
                  <div class="text-surface-500 text-xs">{{ formatSize(preview.att?.size_bytes) }} · {{ preview.att?.mime_type }}</div>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0 ml-3">
                <a :href="attUrl(preview.att)" :download="preview.att?.filename"
                  class="btn-ghost text-xs px-3 py-1.5">⬇ Yuklab olish</a>
                <button @click="preview.open = false"
                  class="w-8 h-8 rounded-lg hover:bg-surface-700 flex items-center justify-center text-surface-400 hover:text-white transition-colors">✕</button>
              </div>
            </div>
            <!-- Content -->
            <div class="flex-1 overflow-auto flex items-center justify-center bg-black/50 p-4 min-h-0">
              <img v-if="isImage(preview.att)"
                :src="attUrl(preview.att)" :alt="preview.att?.filename"
                class="max-w-full max-h-full object-contain rounded-lg" />

              <iframe v-else-if="isPdf(preview.att)"
                :src="attUrl(preview.att)"
                class="w-full rounded-lg border-0" style="height:75vh" title="PDF" />

              <video v-else-if="isVideo(preview.att)" controls autoplay
                class="max-w-full max-h-full rounded-lg">
                <source v-if="attUrl(preview.att)" :src="attUrl(preview.att)" :type="preview.att?.mime_type" />
                <div v-else class="text-surface-400 text-sm p-8">Video yuklanmoqda...</div>
              </video>

              <div v-else-if="isAudio(preview.att)" class="text-center py-12 space-y-4">
                <div class="text-6xl">🎵</div>
                <div class="text-white font-medium">{{ preview.att?.filename }}</div>
                <audio v-if="attUrl(preview.att)" controls autoplay class="w-80">
                  <source :src="attUrl(preview.att)" :type="preview.att?.mime_type" />
                </audio>
                <div v-else class="flex items-center justify-center gap-2 text-surface-400 text-sm">
                  <div class="w-5 h-5 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin"></div>
                  Yuklanmoqda...
                </div>
              </div>

              <div v-else class="text-center py-16 space-y-4">
                <div class="text-6xl">📎</div>
                <p class="text-surface-400 text-sm">Bu fayl tur ko'rib bo'lmaydi</p>
                <a :href="attUrl(preview.att)" :download="preview.att?.filename" class="btn-primary text-sm">⬇ Yuklab olish</a>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'
import { format } from 'date-fns'
import api from '@/utils/api'

const route = useRoute()
const loading = ref(true)
const sending = ref(false)
const caseData = ref(null)
const users = ref([])
const newStatus = ref('')
const assignedTo = ref('')
const newComment = reactive({ content: '', is_internal: false })
const ticketCreating = ref(false)
const ticketError = ref('')
const ticketSkipped = ref('')
const preview = reactive({ open: false, att: null })
const chatEl = ref(null)
const fileInputRef = ref(null)
const uploadFile = ref(null)

// ── Blob URL cache — JWT bilan fayllarni olish ──────────────────────────────
const blobCache = reactive({})   // att.id → { url, mime }
const loadingBlobs = reactive({})

function attApiPath(att) {
  if (!att) return ''
  return `/v1/cases/${caseData.value?.external_id}/attachments/${att.id}`
}

async function loadBlobUrl(att) {
  if (!att?.id) return
  if (blobCache[att.id]) return
  if (loadingBlobs[att.id]) return
  loadingBlobs[att.id] = true
  try {
    const resp = await api.get(attApiPath(att), { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    blobCache[att.id] = { url, mime: att.mime_type }
  } catch (e) {
    console.warn('Attachment yuklab bo\'lmadi:', att.filename, e)
  } finally {
    delete loadingBlobs[att.id]
  }
}

function attUrl(att) {
  if (!att?.id) return ''
  return blobCache[att.id]?.url || ''
}

async function loadAllBlobs() {
  const atts = caseData.value?.attachments || []
  const eager = atts.filter(a => isImage(a) || isPdf(a))
  await Promise.all(eager.map(a => loadBlobUrl(a)))
}

onUnmounted(() => {
  Object.values(blobCache).forEach(({ url }) => URL.revokeObjectURL(url))
})
function isImage(att) { return att?.mime_type?.startsWith('image/') }
function isVideo(att) { return att?.mime_type?.startsWith('video/') }
function isAudio(att) { return att?.mime_type?.startsWith('audio/') }
function isPdf(att)   { return att?.mime_type === 'application/pdf' }
function isPreviewable(att) { return isImage(att) || isVideo(att) || isAudio(att) || isPdf(att) }

function getFileIcon(mime) {
  if (!mime) return '📎'
  if (mime.startsWith('image/')) return '🖼️'
  if (mime.startsWith('video/')) return '🎬'
  if (mime.startsWith('audio/')) return '🎵'
  if (mime.includes('pdf'))    return '📄'
  if (mime.includes('word') || mime.includes('document')) return '📝'
  if (mime.includes('excel') || mime.includes('sheet'))   return '📊'
  if (mime.includes('zip') || mime.includes('rar'))       return '🗜️'
  return '📎'
}

// Reporter yuborgan fayllar (is_from_reporter ga asoslanib yoki admin attachment bo'lmagan)
const reporterAttachments = computed(() => {
  if (!caseData.value?.attachments) return []
  // Comment bilan bog'liq attachment ID larni chiqaramiz
  const commentAttIds = new Set(
    (caseData.value.comments || [])
      .filter(c => c._attachment)
      .map(c => c._attachment.id)
  )
  return caseData.value.attachments.filter(a => !commentAttIds.has(a.id))
})

function openPreview(att) {
  preview.att = att
  preview.open = true
  // Video/audio uchun blob yuklaymiz (modal ochilganda)
  if ((isVideo(att) || isAudio(att)) && !attUrl(att)) {
    loadBlobUrl(att)
  }
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function loadCase() {
  loading.value = true
  try {
    const { data } = await api.get(`/v1/cases/${route.params.id}`)
    caseData.value = data
    newStatus.value = data.status
    assignedTo.value = data.assigned_to || ''
    // Blob URL larni yuklash (JWT token bilan, 401 muammosini hal qiladi)
    await loadAllBlobs()
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

function scrollChatBottom() {
  nextTick(() => {
    if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
  })
}

// ── Actions ──────────────────────────────────────────────────────────────────
async function updateStatus() {
  try {
    await api.post(`/v1/cases/${caseData.value.external_id}/status`, { status: newStatus.value })
    caseData.value.status = newStatus.value
  } catch {}
}
async function setStatus(status) { newStatus.value = status; await updateStatus() }
async function assignCase() {
  try { await api.post(`/v1/cases/${caseData.value.external_id}/assign`, { user_id: assignedTo.value || null }) } catch {}
}

function onFileSelect(e) {
  const f = e.target.files?.[0]
  if (f) uploadFile.value = f
  // input ni reset — qayta xuddi faylni tanlasa ham ishlaydi
  e.target.value = ''
}

async function sendMessage() {
  const hasText = newComment.content.trim()
  const hasFile = !!uploadFile.value
  if (!hasText && !hasFile) return
  sending.value = true
  try {
    if (hasFile) {
      // Fayl bilan birga yuborish
      const fd = new FormData()
      fd.append('file', uploadFile.value)
      fd.append('caption', newComment.content.trim())
      fd.append('is_internal', newComment.is_internal ? 'true' : 'false')
      await api.post(`/v1/cases/${caseData.value.external_id}/send-file`, fd)
      // Content-Type headerini bermaymiz — axios FormData uchun o'zi boundary bilan belgilaydi
      uploadFile.value = null
      newComment.content = ''
    } else {
      // Faqat matn
      await api.post(`/v1/cases/${caseData.value.external_id}/comment`, {
        content: newComment.content,
        is_internal: newComment.is_internal,
      })
      newComment.content = ''
    }
    await loadCase()
    // Yangi fayllar uchun blob URL larni yuklash
    scrollChatBottom()
  } catch (e) {
    alert(e.response?.data?.detail || 'Xatolik yuz berdi')
  } finally {
    sending.value = false
  }
}

// Blob URL yo'q bo'lsa — yuklab olib download qilish
async function downloadAtt(att) {
  await loadBlobUrl(att)
  const url = blobCache[att.id]?.url
  if (!url) return
  const a = document.createElement('a')
  a.href = url
  a.download = att.filename
  a.click()
}

async function exportCase() {
  window.open(`/api/v1/cases/${caseData.value.external_id}/export`, '_blank')
}

async function createTicket() {
  ticketCreating.value = true; ticketError.value = ''; ticketSkipped.value = ''
  try {
    const { data } = await api.post(`/v1/tickets/${caseData.value.external_id}/create`)
    if (data.created || data.already_exists) {
      caseData.value.jira_ticket_id = data.ticket_id
      caseData.value.jira_ticket_url = data.ticket_url
    } else if (data.skipped) {
      ticketSkipped.value = data.message || 'Tiket yaratilmadi'
    }
  } catch (e) {
    ticketError.value = e.response?.data?.detail || 'Tiket yaratishda xato'
  } finally {
    ticketCreating.value = false
  }
}

// ── Formatters ────────────────────────────────────────────────────────────────
function formatDate(d) { return d ? format(new Date(d), 'dd.MM.yyyy HH:mm') : '—' }
function formatSize(b) {
  if (!b) return '—'
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / (1024 * 1024)).toFixed(1) + ' MB'
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
  fraud: '💸 Firibgarlik',
  safety: '⚠️ Xavfsizlik buzilishi',
  discrimination: '🚫 Kamsitish',
  procurement: '📋 Tender buzilishi',
  other: '❓ Boshqa',
}
function categoryLabel(c) { return catLabels[c] || c }

// ── Badges ────────────────────────────────────────────────────────────────────
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

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active :deep(.relative.z-10),
.modal-leave-active :deep(.relative.z-10) { transition: transform 0.2s ease, opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from :deep(.relative.z-10),
.modal-leave-to :deep(.relative.z-10) { transform: scale(0.95); opacity: 0; }
</style>

