<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <div class="flex items-center justify-between mb-6 gap-3 flex-wrap">
      <div>
        <h1 class="text-xl sm:text-2xl font-bold text-white">{{ t('users.title') }}</h1>
        <p class="text-surface-400 text-sm mt-1">{{ t('users.subtitle') }}</p>
      </div>
      <button @click="openCreate" class="btn-primary whitespace-nowrap">+ {{ t('users.add_user') }}</button>
    </div>

    <!-- Desktop table -->
    <div class="card overflow-hidden hidden sm:block">
      <table class="w-full">
        <thead>
          <tr class="border-b border-surface-800">
            <th v-for="c in [t('users.col_name'), t('users.col_email'), t('users.col_role'), t('users.col_2fa'), t('users.col_telegram'), t('users.col_last_login'), t('users.col_status'), '']"
              :key="c" class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">
              {{ c }}
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Skeleton loading -->
          <template v-if="loading">
            <tr v-for="i in 5" :key="'sk'+i" class="border-b border-surface-800/50">
              <td class="px-5 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg bg-surface-800 animate-pulse"></div>
                  <div class="space-y-1.5">
                    <div class="h-3.5 w-28 bg-surface-800 rounded animate-pulse"></div>
                    <div class="h-2.5 w-16 bg-surface-800/60 rounded animate-pulse"></div>
                  </div>
                </div>
              </td>
              <td class="px-5 py-4"><div class="h-3.5 w-32 bg-surface-800 rounded animate-pulse"></div></td>
              <td class="px-5 py-4"><div class="h-5 w-20 bg-surface-800 rounded-full animate-pulse"></div></td>
              <td class="px-5 py-4"><div class="h-4 w-10 bg-surface-800 rounded animate-pulse"></div></td>
              <td class="px-5 py-4"><div class="h-4 w-10 bg-surface-800 rounded animate-pulse"></div></td>
              <td class="px-5 py-4"><div class="h-3.5 w-24 bg-surface-800 rounded animate-pulse"></div></td>
              <td class="px-5 py-4"><div class="h-5 w-14 bg-surface-800 rounded-full animate-pulse"></div></td>
              <td class="px-5 py-4"><div class="h-6 w-6 bg-surface-800 rounded animate-pulse"></div></td>
            </tr>
          </template>
          <tr v-else-if="!users.length">
            <td colspan="8">
              <EmptyState icon="👥" :title="t('users.no_users_empty')" :description="t('users.no_users_hint')" />
            </td>
          </tr>
          <tr v-for="u in users" :key="u.id"
            class="border-b border-surface-800/50 hover:bg-surface-800/20 transition-colors">
            <td class="px-5 py-4">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                  {{ (u.full_name || u.username)[0].toUpperCase() }}
                </div>
                <div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-white text-sm font-medium">{{ u.full_name || u.username }}</span>
                    <span v-if="u.username === 'admin'"
                      class="text-xs bg-amber-500/15 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded-full">
                      {{ t('users.superuser') }}
                    </span>
                  </div>
                  <div class="text-surface-500 text-xs">@{{ u.username }}</div>
                </div>
              </div>
            </td>
            <td class="px-5 py-4 text-surface-300 text-sm">{{ u.email }}</td>
            <td class="px-5 py-4">
              <span :class="roleClass(u.role)" class="badge">{{ roleLabel(u.role) }}</span>
            </td>
            <td class="px-5 py-4">
              <span :class="u.totp_enabled ? 'text-green-400' : 'text-surface-600'" class="text-sm">
                {{ u.totp_enabled ? '✓' : '✗' }}
              </span>
            </td>
            <td class="px-5 py-4">
              <span v-if="u.telegram_chat_id" class="text-green-400 text-sm">✈️ {{ t('users.linked') }}</span>
              <button v-else @click="openTgLink(u)"
                class="text-xs text-brand-400 hover:text-brand-300 underline underline-offset-2 transition-colors">
                {{ t('users.link') }}
              </button>
            </td>
            <td class="px-5 py-4 text-surface-400 text-sm">
              {{ u.last_login ? formatDate(u.last_login) : t('users.never') }}
            </td>
            <td class="px-5 py-4">
              <span :class="u.is_active ? 'text-green-400' : 'text-red-400'" class="text-sm">
                {{ u.is_active ? '● ' + t('users.active') : '○ ' + t('users.inactive') }}
              </span>
            </td>
            <!-- Actions -->
            <td class="px-5 py-4">
              <div class="flex items-center gap-1">
                <button @click="openEdit(u)" :title="t('users.edit')"
                  class="p-1.5 text-surface-400 hover:text-white hover:bg-surface-700 rounded-lg transition-all">
                  ✏️
                </button>
                <button v-if="u.username !== 'admin'" @click="confirmDelete(u)" :title="t('users.delete')"
                  class="p-1.5 text-surface-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all">
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile card list -->
    <div class="sm:hidden space-y-3">
      <div v-if="loading" class="card p-8 text-center">
        <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      </div>
      <div v-for="u in users" :key="u.id" class="card p-4">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            {{ (u.full_name || u.username)[0].toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="text-white text-sm font-medium truncate">{{ u.full_name || u.username }}</span>
              <span v-if="u.username === 'admin'"
                class="text-xs bg-amber-500/15 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded-full flex-shrink-0">
                super
              </span>
            </div>
            <div class="text-surface-500 text-xs">{{ u.email }}</div>
          </div>
          <span :class="u.is_active ? 'text-green-400' : 'text-red-400'" class="text-xs flex-shrink-0">
            {{ u.is_active ? '● ' + t('users.active') : '○ ' + t('users.inactive') }}
          </span>
        </div>
        <div class="flex items-center gap-2 flex-wrap mb-3">
          <span :class="roleClass(u.role)" class="badge">{{ roleLabel(u.role) }}</span>
          <span :class="u.totp_enabled ? 'text-green-400' : 'text-surface-600'" class="text-xs">
            {{ u.totp_enabled ? '🔐 2FA' : t('users.2fa_no') }}
          </span>
          <span v-if="u.telegram_chat_id" class="text-green-400 text-xs">✈️ {{ t('users.tg_linked') }}</span>
          <button v-else @click="openTgLink(u)" class="text-xs text-brand-400 underline">✈️ {{ t('users.tg_link') }}</button>
        </div>
        <div class="flex items-center gap-2 pt-2 border-t border-surface-800">
          <button @click="openEdit(u)"
            class="flex-1 text-xs py-1.5 px-3 bg-surface-700 hover:bg-surface-600 text-surface-300 hover:text-white rounded-lg transition-all text-center">
            ✏️ {{ t('users.edit') }}
          </button>
          <button v-if="u.username !== 'admin'" @click="confirmDelete(u)"
            class="flex-1 text-xs py-1.5 px-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-all text-center">
            🗑️ {{ t('users.delete') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════
         CREATE / EDIT MODAL
    ══════════════════════════════════════════ -->
    <div v-if="showForm" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-md animate-slide-up max-h-[90vh] overflow-y-auto">
        <div class="p-6 border-b border-surface-800 flex items-center justify-between sticky top-0 bg-surface-900 z-10">
          <h2 class="text-lg font-semibold text-white">
            {{ editMode ? t('users.edit_user') : t('users.new_user') }}
          </h2>
          <button @click="closeForm" class="text-surface-400 hover:text-white text-lg leading-none">✕</button>
        </div>
        <form @submit.prevent="saveUser" class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('users.username_label') }} *</label>
            <input v-model="form.username" class="input w-full"
              :disabled="editMode" :class="editMode ? 'opacity-50 cursor-not-allowed' : ''"
              placeholder="john.doe" :required="!editMode" />
            <p v-if="editMode" class="text-surface-600 text-xs mt-1">{{ t('users.username_hint') }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('users.fullname_label') }}</label>
            <input v-model="form.full_name" class="input w-full" placeholder="Ism Familiya" />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('users.email_label') }} *</label>
            <input v-model="form.email" class="input w-full" type="email" placeholder="john@company.uz" required />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('users.role_label') }} *</label>
            <select v-model="form.role" class="input w-full"
              :disabled="form.username === 'admin'"
              :class="form.username === 'admin' ? 'opacity-50 cursor-not-allowed' : ''">
              <option value="viewer">👁 {{ t('users.role_viewer_desc') }}</option>
              <option value="investigator">🔍 {{ t('users.role_investigator_desc') }}</option>
              <option value="admin">👑 {{ t('users.role_admin_desc') }}</option>
            </select>
          </div>
          <div v-if="editMode && form.username !== 'admin'"
            class="flex items-center justify-between p-3 bg-surface-800 rounded-xl">
            <span class="text-sm text-surface-300">{{ t('users.account_status') }}</span>
            <button type="button" @click="form.is_active = !form.is_active"
              :class="form.is_active ? 'bg-green-500' : 'bg-surface-600'"
              class="w-10 h-6 rounded-full transition-colors relative">
              <span :class="form.is_active ? 'translate-x-5' : 'translate-x-1'"
                class="block w-4 h-4 bg-white rounded-full transition-transform absolute top-1"></span>
            </button>
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">
              {{ editMode ? t('users.password_edit_label') : t('users.password_label') + ' *' }}
            </label>
            <input v-model="form.password" class="input w-full" type="password"
              :placeholder="editMode ? t('users.password_edit_placeholder') : t('users.password_placeholder')"
              :required="!editMode" autocomplete="new-password" />
            <p v-if="form.password && form.password.length < 8" class="text-red-400 text-xs mt-1">
              {{ t('users.password_min') }}
            </p>
          </div>
          <div v-if="form.password" class="flex items-center gap-3">
            <input id="force_pw" type="checkbox" v-model="form.force_password_change"
              class="w-4 h-4 rounded accent-brand-500" />
            <label for="force_pw" class="text-sm text-surface-400 cursor-pointer">
              {{ t('users.force_password_change') }}
            </label>
          </div>
          <p v-if="formError" class="text-red-400 text-sm p-3 bg-red-500/10 rounded-xl">{{ formError }}</p>
          <div class="flex gap-3 pt-2">
            <button type="button" @click="closeForm" class="btn-ghost flex-1">{{ t('users.cancel') }}</button>
            <button type="submit" :disabled="saving"
              :class="!editMode || !form.password || form.password.length >= 8 || !form.password ? '' : 'opacity-50'"
              class="btn-primary flex-1 justify-center">
              {{ saving ? '⏳ ' + t('users.saving') : (editMode ? '💾 ' + t('users.save') : '✅ ' + t('users.create')) }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ══════════════════════════════════════════
         DELETE CONFIRM MODAL
    ══════════════════════════════════════════ -->
    <div v-if="deleteTarget"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-sm animate-slide-up p-6 space-y-5">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 bg-red-500/15 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0">🗑️</div>
          <div>
            <h3 class="text-white font-semibold">{{ t('users.delete_title') }}</h3>
            <p class="text-surface-400 text-sm mt-0.5">{{ t('users.delete_warning') }}</p>
          </div>
        </div>
        <div class="p-3 bg-surface-800 rounded-xl text-sm">
          <span class="text-surface-400">{{ t('users.delete_target') }} </span>
          <span class="text-white font-medium">{{ deleteTarget.full_name || deleteTarget.username }}</span>
          <span class="text-surface-500 ml-1">(@{{ deleteTarget.username }})</span>
        </div>
        <p v-if="deleteError" class="text-red-400 text-sm">{{ deleteError }}</p>
        <div class="flex gap-3">
          <button @click="deleteTarget = null; deleteError = ''" class="btn-ghost flex-1">{{ t('common.cancel') }}</button>
          <button @click="deleteUser" :disabled="deleting" class="btn-danger flex-1 justify-center">
            {{ deleting ? '⏳...' : '🗑️ ' + t('users.delete_confirm') }}
          </button>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════
         TELEGRAM LINK MODAL
    ══════════════════════════════════════════ -->
    <div v-if="tgLinkTarget"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-md animate-slide-up p-6 space-y-5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="text-2xl">✈️</span>
            <div>
              <h3 class="text-white font-semibold">{{ t('users.tg_connect') }}</h3>
              <p class="text-surface-500 text-sm">{{ tgLinkTarget.full_name || tgLinkTarget.username }}</p>
            </div>
          </div>
          <button @click="closeTgLink" class="text-surface-400 hover:text-white">✕</button>
        </div>
        <div v-if="tgLinkLoading" class="flex items-center justify-center py-6">
          <div class="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <template v-else-if="tgLinkData">
          <div class="p-4 bg-surface-800 rounded-xl space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-surface-400 text-xs">{{ t('users.tg_link_label') }}</span>
              <span class="text-surface-600 text-xs">{{ t('users.tg_countdown', { seconds: tgLinkCountdown }) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-brand-300 text-xs bg-surface-900 px-3 py-2 rounded-lg break-all">
                {{ tgLinkData.link }}
              </code>
              <button @click="copyTgLink" class="btn-ghost text-xs px-3 flex-shrink-0">
                {{ tgLinkCopied ? '✅' : '📋' }}
              </button>
            </div>
            <a :href="tgLinkData.link" target="_blank" rel="noopener"
              class="btn-primary text-sm flex items-center justify-center gap-2 w-full">
              ✈️ {{ t('users.tg_open_telegram') }}
            </a>
          </div>
          <div class="flex items-center gap-3 p-3 bg-surface-800/60 rounded-xl border border-surface-700">
            <svg class="w-4 h-4 animate-spin text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            <span class="text-surface-400 text-sm">{{ t('users.tg_waiting') }}</span>
          </div>
          <div class="text-surface-500 text-xs">
            {{ t('users.tg_link_hint') }}
          </div>
        </template>
        <p v-if="tgLinkError" class="text-red-400 text-sm">{{ tgLinkError }}</p>
        <button @click="closeTgLink" class="btn-ghost w-full">{{ t('users.close') }}</button>
      </div>
    </div>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show"
          :class="toast.ok ? 'bg-green-900/90 border-green-700 text-green-200' : 'bg-red-900/90 border-red-700 text-red-200'"
          class="fixed bottom-6 right-6 z-[99999] flex items-center gap-3 border px-4 py-3 rounded-xl shadow-xl backdrop-blur-sm">
          <span>{{ toast.ok ? '✅' : '❌' }}</span>
          <span class="text-sm font-medium">{{ toast.msg }}</span>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted, onMounted } from 'vue'
import { format } from 'date-fns'
import api from '@/utils/api'
import EmptyState from '@/components/EmptyState.vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// ── State ─────────────────────────────────────────────────────────
const loading  = ref(true)
const saving   = ref(false)
const deleting = ref(false)
const users    = ref([])

// ── Toast ──────────────────────────────────────────────────────────
const toast = ref({ show: false, ok: true, msg: '' })
function showToast(msg, ok = true) {
  toast.value = { show: true, ok, msg }
  setTimeout(() => { toast.value.show = false }, 3500)
}

// ── Helpers ────────────────────────────────────────────────────────
function roleClass(r) {
  return r === 'admin'
    ? 'bg-brand-500/15 text-brand-400 border border-brand-500/20'
    : r === 'investigator'
      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
      : 'bg-surface-700/50 text-surface-400'
}
function roleLabel(r) {
  return r === 'admin' ? '👑 ' + t('users.role_admin') : r === 'investigator' ? '🔍 ' + t('users.role_investigator') : '👁 ' + t('users.role_viewer')
}
function formatDate(d) { return d ? format(new Date(d), 'dd.MM.yyyy HH:mm') : '—' }

// ── Load ───────────────────────────────────────────────────────────
async function loadUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/v1/auth/users')
    users.value = data
  } finally {
    loading.value = false
  }
}

// ── CREATE / EDIT FORM ─────────────────────────────────────────────
const showForm  = ref(false)
const editMode  = ref(false)
const editId    = ref(null)
const formError = ref('')
const form = reactive({
  username: '', full_name: '', email: '', role: 'viewer',
  password: '', is_active: true, force_password_change: false
})

function openCreate() {
  editMode.value = false
  editId.value   = null
  formError.value = ''
  Object.assign(form, { username: '', full_name: '', email: '', role: 'viewer',
    password: '', is_active: true, force_password_change: false })
  showForm.value = true
}

function openEdit(u) {
  editMode.value = true
  editId.value   = u.id
  formError.value = ''
  Object.assign(form, {
    username: u.username,
    full_name: u.full_name || '',
    email: u.email,
    role: u.role,
    password: '',
    is_active: u.is_active,
    force_password_change: false,
  })
  showForm.value = true
}

function closeForm() { showForm.value = false; formError.value = '' }

async function saveUser() {
  if (form.password && form.password.length < 8) return
  saving.value  = true
  formError.value = ''
  try {
    if (editMode.value) {
      const body = {
        full_name: form.full_name,
        email: form.email,
        role: form.role,
        is_active: form.is_active,
      }
      if (form.password) {
        body.password = form.password
        body.force_password_change = form.force_password_change
      }
      await api.put(`/v1/auth/users/${editId.value}`, body)
      showToast('✅ ' + t('users.user_updated'))
    } else {
      await api.post('/v1/auth/users', {
        username: form.username,
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        role: form.role,
      })
      showToast('✅ ' + t('users.user_created'))
    }
    closeForm()
    await loadUsers()
  } catch (e) {
    formError.value = '❌ ' + (e.response?.data?.detail || t('case_detail.error_occurred'))
  } finally {
    saving.value = false
  }
}

// ── DELETE ─────────────────────────────────────────────────────────
const deleteTarget = ref(null)
const deleteError  = ref('')

function confirmDelete(u) { deleteTarget.value = u; deleteError.value = '' }

async function deleteUser() {
  deleting.value = true
  deleteError.value = ''
  try {
    await api.delete(`/v1/auth/users/${deleteTarget.value.id}`)
    showToast('🗑️ ' + t('users.user_deleted', { username: deleteTarget.value.username }))
    deleteTarget.value = null
    await loadUsers()
  } catch (e) {
    deleteError.value = '❌ ' + (e.response?.data?.detail || t('common.error'))
  } finally {
    deleting.value = false
  }
}

// ── TELEGRAM LINK ──────────────────────────────────────────────────
const tgLinkTarget   = ref(null)
const tgLinkLoading  = ref(false)
const tgLinkData     = ref(null)
const tgLinkError    = ref('')
const tgLinkCountdown = ref(0)
const tgLinkCopied   = ref(false)
let _tgPollTimer  = null
let _tgCountTimer = null

async function openTgLink(u) {
  tgLinkTarget.value  = u
  tgLinkData.value    = null
  tgLinkError.value   = ''
  tgLinkLoading.value = true
  try {
    const { data } = await api.post(`/v1/auth/users/${u.id}/telegram-link`)
    tgLinkData.value      = data
    tgLinkCountdown.value = data.expires_in

    _tgCountTimer = setInterval(() => {
      tgLinkCountdown.value--
      if (tgLinkCountdown.value <= 0) closeTgLink()
    }, 1000)

    // Har 3 soniyada bog'lanish holatini tekshir
    _tgPollTimer = setInterval(async () => {
      try {
        const { data: st } = await api.get('/v1/auth/users')
        const updated = st.find(x => x.id === u.id)
        if (updated?.telegram_chat_id) {
          // Ro'yxatni yangilash
          const idx = users.value.findIndex(x => x.id === u.id)
          if (idx !== -1) users.value[idx] = updated
          closeTgLink()
          showToast(`✅ ${u.full_name || u.username} Telegram ga bog'landi!`)
        }
      } catch { /* jim */ }
    }, 3000)
  } catch (e) {
    tgLinkError.value = '❌ ' + (e.response?.data?.detail || t('common.error'))
  } finally {
    tgLinkLoading.value = false
  }
}

function closeTgLink() {
  clearInterval(_tgPollTimer)
  clearInterval(_tgCountTimer)
  _tgPollTimer  = null
  _tgCountTimer = null
  tgLinkTarget.value    = null
  tgLinkData.value      = null
  tgLinkCountdown.value = 0
}

async function copyTgLink() {
  try {
    await navigator.clipboard.writeText(tgLinkData.value?.link || '')
    tgLinkCopied.value = true
    setTimeout(() => { tgLinkCopied.value = false }, 2000)
  } catch { /* jim */ }
}

onMounted(loadUsers)
onUnmounted(closeTgLink)
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(12px); }
</style>

