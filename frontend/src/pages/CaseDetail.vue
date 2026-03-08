<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in max-w-6xl">
    <button @click="$router.back()" class="btn-ghost text-sm mb-4 -ml-2">← {{ t('case_detail.back') }}</button>

    <SkeletonLoader v-if="loading" type="detail" />

    <ErrorState v-else-if="loadError" :message="loadError" :retry="loadCase" />

    <template v-else-if="caseData">
      <!-- Title row -->
      <div class="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <div class="flex items-center gap-2 flex-wrap mb-2">
            <span class="font-mono text-brand-400 text-base sm:text-lg font-semibold">{{ caseData.external_id }}</span>
            <StatusBadge :status="caseData.status" />
            <PriorityBadge :priority="caseData.priority" />
            <span v-if="caseData.is_anonymous" class="badge bg-surface-800 text-surface-400 border border-surface-700">🔒 {{ t('case_detail.anonymous_badge') }}</span>
          </div>
          <p class="text-surface-400 text-sm">{{ t('case_detail.sent_at', { date: formatDate(caseData.created_at) }) }}</p>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <button @click="openStatusModal" class="btn-ghost text-sm whitespace-nowrap">🔄 {{ t('case_detail.change_status') }}</button>
          <button @click="exportCase" class="btn-ghost text-sm whitespace-nowrap">📄 {{ t('case_detail.export_case') }}</button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main content -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Description -->
          <div class="card p-6">
            <h3 class="font-semibold text-white mb-4">📝 {{ t('case_detail.description') }}</h3>
            <p class="text-surface-200 leading-relaxed whitespace-pre-wrap">{{ caseData.description }}</p>
          </div>

          <!-- Reporter fayllari -->
          <div v-if="reporterAttachments.length" class="card p-6">
            <h3 class="font-semibold text-white mb-4">
              {{ caseData.is_anonymous ? '📸 ' + t('case_detail.reporter_files') : '📸 ' + t('case_detail.sender_files') }}
              <span class="text-surface-500 text-sm font-normal ml-2">{{ t('case_detail.file_count', { count: reporterAttachments.length }) }}</span>
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <AttachmentCard v-for="att in reporterAttachments" :key="att.id"
                :att="att" :blob-url="attUrl(att)" :loading="loadingBlobs[att.id]"
                @preview="openPreview" @load="loadBlobUrl" @download="downloadAtt" />
            </div>
          </div>

          <!-- Admin (tekshiruv) fayllari -->
          <div v-if="adminAttachments.length" class="card p-6">
            <h3 class="font-semibold text-white mb-4">
              📎 {{ t('case_detail.admin_files') }}
              <span class="text-surface-500 text-sm font-normal ml-2">{{ t('case_detail.file_count', { count: adminAttachments.length }) }}</span>
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <AttachmentCard v-for="att in adminAttachments" :key="att.id"
                :att="att" :blob-url="attUrl(att)" :loading="loadingBlobs[att.id]"
                @preview="openPreview" @load="loadBlobUrl" @download="downloadAtt" />
            </div>
          </div>

          <!-- Chat / Muloqot -->
          <div class="card p-6">
            <div class="flex items-center justify-between mb-5">
              <h3 class="font-semibold text-white">💬 {{ t('case_detail.chat') }}</h3>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="newComment.is_internal" class="w-4 h-4 rounded accent-brand-500" />
                <span class="text-surface-400 text-sm">{{ t('case_detail.internal_comment') }}</span>
              </label>
            </div>

            <!-- Xabarlar -->
            <div ref="chatEl" class="space-y-3 mb-5 max-h-96 overflow-y-auto pr-1">
              <div v-if="!caseData.comments?.length" class="text-center text-surface-600 text-sm py-10">
                {{ t('case_detail.no_comments') }}
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
                      {{ c.is_from_reporter ? '👤 ' + t('case_detail.reporter_label') : `👨‍💼 ${c.author}` }}
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
                <span>{{ caseData.is_anonymous ? t('case_detail.anonymous_reply_hint') : t('case_detail.reply_hint') }}</span>
              </div>
              <div v-else class="flex items-center gap-2 text-xs text-amber-500/70">
                <span>🔒</span><span>{{ t('case_detail.internal_note_hint') }}</span>
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
                <label class="flex-shrink-0 w-9 h-9 rounded-xl hover:bg-surface-700 flex items-center justify-center text-surface-400 hover:text-white cursor-pointer transition-colors" :title="t('case_detail.attach_file')">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
                  <input type="file" class="hidden" ref="fileInputRef"
                    accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.zip,.txt"
                    @change="onFileSelect" />
                </label>

                <textarea v-model="newComment.content" rows="2"
                  class="input flex-1 resize-none text-sm"
                  :placeholder="newComment.is_internal ? t('case_detail.internal_note_placeholder') : t('case_detail.comment_placeholder')"
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
              <p class="text-xs text-surface-600">{{ t('case_detail.ctrl_enter_send') }}</p>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div class="space-y-5">
          <!-- Case info -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">{{ t('case_detail.case_info') }}</h3>
            <dl class="space-y-3 text-sm">
              <div><dt class="text-surface-500 text-xs mb-1">{{ t('case_detail.category') }}</dt><dd class="text-surface-200">{{ categoryLabel(caseData.category) }}</dd></div>
              <div><dt class="text-surface-500 text-xs mb-1">{{ t('case_detail.priority') }}</dt><dd><PriorityBadge :priority="caseData.priority" /></dd></div>
              <div><dt class="text-surface-500 text-xs mb-1">{{ t('case_detail.status') }}</dt><dd><StatusBadge :status="caseData.status" /></dd></div>
              <div v-if="caseData.due_at"><dt class="text-surface-500 text-xs mb-1">{{ t('case_detail.due_at') }}</dt><dd class="text-surface-200">{{ formatDate(caseData.due_at) }}</dd></div>
              <div v-if="caseData.closed_at"><dt class="text-surface-500 text-xs mb-1">{{ t('case_detail.closed_at') }}</dt><dd class="text-surface-200">{{ formatDate(caseData.closed_at) }}</dd></div>
            </dl>
          </div>

          <!-- Assignment -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">{{ t('case_detail.assign_section') }}</h3>
            <select v-model="assignedTo" @change="assignCase" class="input text-sm w-full">
              <option value="">{{ t('case_detail.not_assigned') }}</option>
              <option v-for="u in users" :key="u.id" :value="u.id">{{ u.full_name || u.username }}</option>
            </select>
          </div>

          <!-- Tezkor amallar -->
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">{{ t('case_detail.quick_actions') }}</h3>
            <div v-if="allowedStatusOptions.length === 0" class="text-surface-500 text-sm text-center py-2">
              {{ t('case_detail.no_transition') }}
            </div>
            <div v-else class="space-y-2">
              <p class="text-surface-500 text-xs mb-3">{{ statusHint }}</p>
              <button v-if="isAllowed('in_progress')" @click="openStatusModalWith('in_progress')" class="btn-ghost w-full text-sm justify-start">🔄 {{ t('case_detail.start_review') }}</button>
              <button v-if="isAllowed('needs_info')" @click="openStatusModalWith('needs_info')" class="btn-ghost w-full text-sm justify-start">❓ {{ t('case_detail.request_info') }}</button>
              <button v-if="isAllowed('completed')" @click="openStatusModalWith('completed')" class="btn-ghost w-full text-sm justify-start text-green-400 hover:text-green-300">✅ {{ t('case_detail.complete') }}</button>
              <button v-if="isAllowed('rejected')" @click="openStatusModalWith('rejected')" class="btn-ghost w-full text-sm justify-start text-red-400 hover:text-red-300">❌ {{ t('case_detail.reject') }}</button>
              <button v-if="isAllowed('archived')" @click="openStatusModalWith('archived')" class="btn-ghost w-full text-sm justify-start text-surface-400">🗄️ {{ t('case_detail.archive') }}</button>
            </div>
          </div>

          <!-- Jira Ticket (commented out)
          <div class="card p-5">
            <h3 class="font-semibold text-white mb-4 text-sm">🎫 {{ t('case_detail.ticket_system') }}</h3>
            <div v-if="caseData.jira_ticket_id" class="space-y-2">
              <div class="text-xs text-green-400">✅ {{ t('case_detail.ticket_created') }}</div>
              <div class="bg-surface-800 rounded-lg p-3">
                <div class="text-white font-mono text-sm">{{ caseData.jira_ticket_id }}</div>
                <a v-if="caseData.jira_ticket_url" :href="caseData.jira_ticket_url" target="_blank"
                  class="text-brand-400 hover:text-brand-300 text-xs flex items-center gap-1 mt-1">🔗 {{ t('case_detail.open_ticket') }}</a>
              </div>
            </div>
            <div v-else class="space-y-2">
              <p class="text-surface-500 text-xs">{{ t('case_detail.ticket_not_created') }}</p>
              <button @click="createTicket" :disabled="ticketCreating"
                class="btn-ghost w-full text-sm justify-center disabled:opacity-50">
                <svg v-if="ticketCreating" class="w-4 h-4 animate-spin mr-1" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                <span v-else class="mr-1">🎫</span>
                {{ ticketCreating ? t('case_detail.creating_ticket') : t('case_detail.create_ticket') }}
              </button>
              <p v-if="ticketError" class="text-red-400 text-xs">{{ ticketError }}</p>
              <p v-if="ticketSkipped" class="text-surface-500 text-xs">{{ ticketSkipped }}</p>
            </div>
          </div>
          -->
        </div>
      </div>
    </template>

    <!-- ── Status O'zgartirish Modal ── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="statusModal.open" class="fixed inset-0 z-[99998] flex items-center justify-center p-4"
          @click.self="statusModal.open = false">
          <div class="absolute inset-0 bg-black/75 backdrop-blur-sm"></div>
          <div class="relative z-10 bg-surface-900 rounded-2xl border border-surface-700 shadow-2xl w-full max-w-md">
            <div class="flex items-center justify-between px-5 py-4 border-b border-surface-800">
              <h3 class="font-semibold text-white">🔄 {{ t('case_detail.change_status') }}</h3>
              <button @click="statusModal.open = false"
                class="w-8 h-8 rounded-lg hover:bg-surface-700 flex items-center justify-center text-surface-400 hover:text-white transition-colors">✕</button>
            </div>
            <div class="p-5 space-y-4">
              <!-- Joriy holat -->
              <div class="flex items-center gap-3 bg-surface-800 rounded-xl p-3">
                <span class="text-surface-400 text-sm">{{ t('case_detail.current_status') }}</span>
                <StatusBadge :status="caseData.status" />
              </div>

              <!-- Yangi holat tanlash -->
              <div>
                <label class="text-surface-400 text-xs mb-2 block">{{ t('case_detail.new_status') }}</label>
                <div class="grid grid-cols-2 gap-2">
                  <button v-for="opt in allowedStatusOptions" :key="opt.value"
                    @click="statusModal.selected = opt.value"
                    :class="[
                      'px-3 py-2 rounded-xl text-sm font-medium border transition-all text-left',
                      statusModal.selected === opt.value
                        ? 'border-brand-500 bg-brand-500/15 text-brand-300'
                        : 'border-surface-700 bg-surface-800 text-surface-300 hover:border-surface-600'
                    ]">
                    {{ opt.label }}
                  </button>
                </div>
                <p v-if="!allowedStatusOptions.length" class="text-surface-500 text-sm text-center py-3">
                  {{ t('case_detail.no_transition') }}
                </p>
              </div>

              <!-- Izoh maydoni -->
              <div>
                <label class="text-surface-400 text-xs mb-2 block">
                  {{ t('case_detail.reason_label') }}
                  <span v-if="statusModal.selected === 'rejected'" class="text-red-400 ml-1">* {{ t('case_detail.reason_required') }}</span>
                  <span v-else class="text-surface-600 ml-1">{{ t('case_detail.reason_optional') }}</span>
                </label>
                <textarea v-model="statusModal.reason" rows="3"
                  class="input w-full resize-none text-sm"
                  :placeholder="statusModal.selected === 'rejected' ? t('case_detail.reject_reason_placeholder') : t('case_detail.reason_placeholder')"
                ></textarea>
              </div>

              <!-- Xato xabari -->
              <p v-if="statusModal.error" class="text-red-400 text-sm bg-red-500/10 rounded-lg px-3 py-2">
                {{ statusModal.error }}
              </p>
            </div>
            <div class="flex items-center justify-end gap-3 px-5 py-4 border-t border-surface-800">
              <button @click="statusModal.open = false" class="btn-ghost text-sm">{{ t('case_detail.cancel') }}</button>
              <button @click="submitStatusChange"
                :disabled="!statusModal.selected || statusModal.saving || (statusModal.selected === 'rejected' && !statusModal.reason.trim())"
                class="btn-primary text-sm disabled:opacity-40">
                <svg v-if="statusModal.saving" class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {{ t('case_detail.confirm') }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

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
                  class="btn-ghost text-xs px-3 py-1.5">⬇ {{ t('case_detail.download') }}</a>
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
                <div v-else class="text-surface-400 text-sm p-8">{{ t('case_detail.loading_file') }}</div>
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
                <p class="text-surface-400 text-sm">{{ t('case_detail.file_preview_unavailable') }}</p>
                <a :href="attUrl(preview.att)" :download="preview.att?.filename" class="btn-primary text-sm">⬇ {{ t('case_detail.download') }}</a>
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
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useI18n } from '@/composables/useI18n'

const route = useRoute()
const { t } = useI18n()
const loading = ref(true)
const loadError = ref('')
const sending = ref(false)
const caseData = ref(null)
const users = ref([])
const assignedTo = ref('')
const newComment = reactive({ content: '', is_internal: false })
const ticketCreating = ref(false)
const ticketError = ref('')
const ticketSkipped = ref('')
const preview = reactive({ open: false, att: null })
const chatEl = ref(null)
const fileInputRef = ref(null)
const uploadFile = ref(null)

// ── Status Modal ──────────────────────────────────────────────────────────────
const statusModal = reactive({ open: false, selected: '', reason: '', error: '', saving: false })

const TRANSITIONS = {
  new:         ['in_progress', 'rejected', 'needs_info'],
  in_progress: ['completed', 'rejected', 'needs_info', 'new'],
  needs_info:  ['in_progress', 'rejected'],
  completed:   ['archived'],
  rejected:    ['archived'],
  archived:    [],
}
const ALL_STATUS_OPTIONS = computed(() => [
  { value: 'new',         label: '🔵 ' + t('status.new') },
  { value: 'in_progress', label: '🟡 ' + t('status.in_progress') },
  { value: 'needs_info',  label: '🟠 ' + t('status.needs_info') },
  { value: 'completed',   label: '✅ ' + t('status.completed') },
  { value: 'rejected',    label: '❌ ' + t('status.rejected') },
  { value: 'archived',    label: '🗄️ ' + t('status.archived') },
])
const allowedStatusOptions = computed(() => {
  if (!caseData.value) return []
  const allowed = TRANSITIONS[caseData.value.status] || []
  return ALL_STATUS_OPTIONS.value.filter(o => allowed.includes(o.value))
})
function isAllowed(status) {
  const allowed = TRANSITIONS[caseData.value?.status] || []
  return allowed.includes(status)
}

const statusHint = computed(() => {
  if (!caseData.value) return ''
  const hints = {
    new: '💡 Murojaatni ko\'rib chiqishni boshlash uchun "Ko\'rib chiqish boshlandi" tugmasini bosing',
    in_progress: '💡 Ko\'rib chiqish davom etmoqda. Qo\'shimcha ma\'lumot so\'rang yoki yakunlang.',
    needs_info: '💡 Murojaatchi javob kutmoqda. Javob kelgach ko\'rib chiqishni davom ettiring.',
    completed: '✅ Murojaat yakunlangan.',
    rejected: '❌ Murojaat rad etilgan.',
    archived: '🗄️ Murojaat arxivlangan.',
  }
  return hints[caseData.value.status] || ''
})

function openStatusModal() {
  statusModal.selected = ''; statusModal.reason = ''; statusModal.error = ''; statusModal.open = true
}
function openStatusModalWith(status) {
  const allowed = TRANSITIONS[caseData.value?.status] || []
  if (!allowed.includes(status)) return
  statusModal.selected = status; statusModal.reason = ''; statusModal.error = ''; statusModal.open = true
}
async function submitStatusChange() {
  if (!statusModal.selected) return
  if (statusModal.selected === 'rejected' && !statusModal.reason.trim()) {
    statusModal.error = t('case_detail.reject_reason_required'); return
  }
  statusModal.saving = true; statusModal.error = ''
  try {
    await api.post(`/v1/cases/${caseData.value.external_id}/status`, {
      status: statusModal.selected,
      reason: statusModal.reason.trim() || null,
    })
    statusModal.open = false
    await loadCase()
  } catch (e) {
    statusModal.error = e.response?.data?.detail || t('case_detail.error_occurred')
  } finally {
    statusModal.saving = false
  }
}

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

// Reporter va admin fayllarini ajratish (uploaded_by_admin maydoniga qarab)
const reporterAttachments = computed(() => {
  if (!caseData.value?.attachments) return []
  return caseData.value.attachments.filter(a => !a.uploaded_by_admin)
})
const adminAttachments = computed(() => {
  if (!caseData.value?.attachments) return []
  return caseData.value.attachments.filter(a => a.uploaded_by_admin)
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
  loadError.value = ''
  try {
    const { data } = await api.get(`/v1/cases/${route.params.id}`)
    caseData.value = data
    assignedTo.value = data.assigned_to || ''
    await loadAllBlobs()
  } catch (e) {
    loadError.value = e.response?.data?.detail || t('case_detail.load_error')
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
    alert(e.response?.data?.detail || t('case_detail.error_occurred'))
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
  try {
    const resp = await api.get(`/v1/cases/${caseData.value.external_id}/export`, { params: { format: 'pdf' }, responseType: 'blob' })
    const filename = `case_${caseData.value.external_id}.pdf`
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(e.response?.data?.detail || 'Export xatosi')
  }
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

function categoryLabel(c) {
  const map = {
    corruption: '🔴 ' + t('category.corruption'),
    conflict_of_interest: "⚖️ " + t('category.conflict_of_interest'),
    fraud: '💸 ' + t('category.fraud'),
    safety: '⚠️ ' + t('category.safety'),
    discrimination: '🚫 ' + t('category.discrimination'),
    procurement: '📋 ' + t('category.procurement'),
    other: '❓ ' + t('category.other'),
  }
  return map[c] || c
}

// ── Badges ────────────────────────────────────────────────────────────────────
const StatusBadge = defineComponent({
  props: ['status'],
  setup(props) {
    return () => {
      const map = {
        new:         { text: t('status.new'),         cls: 'bg-blue-500/15 text-blue-400 border border-blue-500/20' },
        in_progress: { text: t('status.in_progress'), cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20' },
        needs_info:  { text: t('status.needs_info'),  cls: 'bg-orange-500/15 text-orange-400 border border-orange-500/20' },
        completed:   { text: t('status.completed'),   cls: 'bg-green-500/15 text-green-400 border border-green-500/20' },
        rejected:    { text: t('status.rejected'),    cls: 'bg-red-500/15 text-red-400 border border-red-500/20' },
        archived:    { text: t('status.archived'),    cls: 'bg-surface-700 text-surface-400 border border-surface-600' },
      }
      const s = map[props.status] || { text: props.status, cls: 'bg-surface-700 text-surface-400' }
      return h('span', { class: `badge ${s.cls}` }, s.text)
    }
  }
})

const PriorityBadge = defineComponent({
  props: ['priority'],
  setup(props) {
    return () => {
      const map = {
        critical: { text: '🔴 ' + t('priority.critical'), cls: 'bg-red-500/15 text-red-400 border border-red-500/20' },
        high: { text: '🟠 ' + t('priority.high'), cls: 'bg-orange-500/15 text-orange-400 border border-orange-500/20' },
        medium: { text: '🟡 ' + t('priority.medium'), cls: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20' },
        low: { text: '🟢 ' + t('priority.low'), cls: 'bg-green-500/15 text-green-400 border border-green-500/20' },
      }
      const p = map[props.priority] || { text: props.priority, cls: '' }
      return h('span', { class: `badge ${p.cls}` }, p.text)
    }
  }
})

onMounted(() => { loadCase(); loadUsers() })

// ── AttachmentCard inline component ──────────────────────────────────────────
const AttachmentCard = defineComponent({
  props: ['att', 'blobUrl', 'loading'],
  emits: ['preview', 'load', 'download'],
  setup(props, { emit }) {
    return () => {
      const att = props.att
      const url = props.blobUrl
      const isImg = att?.mime_type?.startsWith('image/')
      const isVid = att?.mime_type?.startsWith('video/')
      const isAud = att?.mime_type?.startsWith('audio/')
      const isPdfFile = att?.mime_type === 'application/pdf'
      const fmt = (b) => !b ? '—' : b < 1024 ? b+' B' : b < 1048576 ? (b/1024).toFixed(1)+' KB' : (b/1048576).toFixed(1)+' MB'
      const icon = isImg ? '🖼️' : isVid ? '🎬' : isAud ? '🎵' : isPdfFile ? '📄'
        : att?.mime_type?.includes('word') ? '📝' : att?.mime_type?.includes('excel') ? '📊'
        : att?.mime_type?.includes('zip') ? '🗜️' : '📎'

      let previewEl
      if (isImg) {
        previewEl = url
          ? h('div', { class: 'bg-surface-950 overflow-hidden cursor-pointer group', style: 'height:180px',
              title: `${att.mime_type} • ${fmt(att.size_bytes)}`, onClick: () => emit('preview', att) },
              [h('img', { src: url, alt: att.filename, class: 'w-full h-full object-cover group-hover:opacity-90 transition-opacity' })])
          : h('div', { class: 'bg-surface-950 flex flex-col items-center justify-center gap-2 text-surface-600', style: 'height:180px' },
              [h('div', { class: 'w-6 h-6 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin' }),
               h('span', { class: 'text-xs' }, t('case_detail.loading_file'))])
      } else if (isVid) {
        previewEl = url
          ? h('div', { class: 'bg-black', style: 'height:180px' },
              [h('video', { controls: true, class: 'w-full h-full object-contain' }, [h('source', { src: url, type: att.mime_type })])])
          : h('div', { class: 'bg-black flex flex-col items-center justify-center gap-2 cursor-pointer hover:bg-white/5 transition-colors',
              style: 'height:180px', onClick: () => emit('load', att) },
              props.loading
                ? [h('div', { class: 'w-8 h-8 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin' })]
                : [h('div', { class: 'w-12 h-12 rounded-full bg-white/20 flex items-center justify-center' },
                    [h('svg', { class: 'w-6 h-6 text-white ml-1', fill: 'currentColor', viewBox: '0 0 24 24' }, [h('path', { d: 'M8 5v14l11-7z' })])]),
                   h('span', { class: 'text-surface-400 text-xs' }, t('case_detail.click_to_load_video'))])
      } else if (isAud) {
        previewEl = h('div', { class: 'bg-surface-800 flex flex-col items-center justify-center gap-2 p-4', style: 'height:100px' },
          [h('div', { class: 'text-2xl' }, '🎵'),
           url
             ? h('audio', { controls: true, class: 'w-full', style: 'height:36px' }, [h('source', { src: url, type: att.mime_type })])
             : h('div', { class: 'flex items-center gap-2 cursor-pointer hover:text-white transition-colors text-surface-400 text-xs', onClick: () => emit('load', att) },
                 props.loading
                   ? [h('div', { class: 'w-4 h-4 border-2 border-surface-600 border-t-brand-500 rounded-full animate-spin' })]
                   : [h('span', {}, '▶ ' + t('case_detail.click_to_load_audio'))])])
      } else if (isPdfFile) {
        previewEl = h('div', { class: 'cursor-pointer bg-red-900/20 flex items-center justify-center gap-3 p-4',
            style: 'height:90px', title: `${att.mime_type} • ${fmt(att.size_bytes)}`, onClick: () => emit('preview', att) },
          [h('span', { class: 'text-4xl' }, '📄'), h('span', { class: 'text-red-300 text-sm' }, t('case_detail.pdf_click_to_view'))])
      } else {
        previewEl = h('div', { class: 'bg-surface-800 flex items-center justify-center gap-2 p-4', style: 'height:80px',
            title: `${att.mime_type} • ${fmt(att.size_bytes)}` },
          [h('span', { class: 'text-3xl' }, icon), h('span', { class: 'text-surface-400 text-xs' }, att.mime_type)])
      }

      const dlIcon = h('svg', { class: 'w-4 h-4', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
        [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4' })])
      const eyeIcon = h('svg', { class: 'w-4 h-4', fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
        [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z' })])

      const dlBtn = url
        ? h('a', { href: url, download: att.filename, class: 'p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors', title: t('case_detail.download') }, [dlIcon])
        : h('button', { class: 'p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors', title: t('case_detail.download'), onClick: () => emit('download', att) }, [dlIcon])

      return h('div', { class: 'border border-surface-700 rounded-xl overflow-hidden bg-surface-900 hover:border-surface-600 transition-colors' }, [
        previewEl,
        h('div', { class: 'flex items-center justify-between p-3 bg-surface-800 border-t border-surface-700' }, [
          h('div', { class: 'min-w-0 flex-1' }, [
            h('div', { class: 'text-white text-xs font-medium truncate', title: att.filename }, att.filename),
            h('div', { class: 'text-surface-500 text-xs' }, fmt(att.size_bytes)),
          ]),
          h('div', { class: 'flex items-center gap-1 ml-2 flex-shrink-0' }, [
            (isImg || isPdfFile || isVid || isAud) && h('button', {
              class: 'p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors',
              title: t('case_detail.view_btn'), onClick: () => emit('preview', att)
            }, [eyeIcon]),
            dlBtn
          ])
        ])
      ])
    }
  }
})
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active :deep(.relative.z-10),
.modal-leave-active :deep(.relative.z-10) { transition: transform 0.2s ease, opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from :deep(.relative.z-10),
.modal-leave-to :deep(.relative.z-10) { transform: scale(0.95); opacity: 0; }
</style>

