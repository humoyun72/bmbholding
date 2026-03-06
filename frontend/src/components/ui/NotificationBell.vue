<template>
  <div class="relative" ref="containerRef">
    <!-- Bell button -->
    <button
      @click="togglePanel"
      class="relative w-9 h-9 flex items-center justify-center rounded-xl text-surface-400
             hover:text-white hover:bg-surface-800 transition-colors"
      :title="connected ? 'Real-time ulanish faol' : 'Ulanish yo\'q'"
    >
      <!-- Bell icon -->
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      <!-- Unread badge -->
      <span v-if="store.unreadCount > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-red-500 text-white
               text-[10px] font-bold rounded-full flex items-center justify-center px-1 animate-pulse-once">
        {{ store.unreadCount > 99 ? '99+' : store.unreadCount }}
      </span>
      <!-- Connection dot -->
      <span :class="['absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full border border-surface-900',
        store.connected ? 'bg-green-400' : 'bg-surface-600']"></span>
    </button>

    <!-- Dropdown panel — teleport to body to escape any parent overflow/z-index -->
    <Teleport to="body">
      <Transition name="dropdown">
        <div v-if="open"
          class="w-80 sm:w-96 bg-surface-900 border border-surface-700 rounded-2xl
                 shadow-2xl flex flex-col overflow-hidden"
          :style="panelStyle">

          <!-- Header -->
          <div class="flex items-center justify-between px-4 py-3 border-b border-surface-800">
            <div class="flex items-center gap-2">
              <span class="text-white font-semibold text-sm">{{ t('notifications.title') }}</span>
              <span v-if="store.unreadCount > 0"
                class="bg-red-500/20 text-red-400 text-xs font-medium px-2 py-0.5 rounded-full">
                {{ t('notifications.new_count', { count: store.unreadCount }) }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span :class="['text-xs flex items-center gap-1', store.connected ? 'text-green-400' : 'text-surface-500']">
                <span :class="['w-1.5 h-1.5 rounded-full', store.connected ? 'bg-green-400' : 'bg-surface-500']"></span>
                {{ store.connected ? t('notifications.connected') : t('notifications.disconnected') }}
              </span>
              <button v-if="store.notifications.length"
                @click="store.markAllRead()"
                class="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                {{ t('notifications.mark_all_read') }}
              </button>
            </div>
          </div>

          <!-- List -->
          <div class="overflow-y-auto flex-1">
            <!-- Empty -->
            <div v-if="!store.notifications.length"
              class="flex flex-col items-center justify-center py-12 text-surface-600">
              <svg class="w-10 h-10 mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <p class="text-sm">{{ t('notifications.no_notifications') }}</p>
            </div>

            <!-- Items -->
            <div v-for="n in store.notifications" :key="n.id"
              @click="handleClick(n)"
              :class="['flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors border-b border-surface-800/50',
                n.read ? 'hover:bg-surface-800/30' : 'bg-brand-600/5 hover:bg-brand-600/10']">
              <div :class="['w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0 mt-0.5',
                priorityBg(n.priority)]">
                {{ priorityIcon(n.priority) }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-white text-sm font-medium">{{ n.title }}</span>
                  <span v-if="!n.read" class="w-2 h-2 bg-brand-500 rounded-full flex-shrink-0"></span>
                </div>
                <p class="text-surface-400 text-xs mt-0.5 truncate">{{ n.body }}</p>
                <p class="text-surface-600 text-xs mt-1">{{ timeAgo(n.at) }}</p>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div v-if="store.notifications.length"
            class="px-4 py-2.5 border-t border-surface-800 flex justify-end">
            <button @click="store.clear()" class="text-xs text-surface-500 hover:text-surface-300 transition-colors">
              {{ t('notifications.clear_all') }}
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { useNotificationStore } from '@/stores/notifications'
import { useI18n } from '@/composables/useI18n'

const store = useNotificationStore()
const router = useRouter()
const { t } = useI18n()
const open = ref(false)
const containerRef = ref(null)

const panelTop  = ref(0)
const panelLeft = ref(0)

const panelStyle = computed(() => ({
  position: 'fixed',
  top:  panelTop.value  + 'px',
  left: panelLeft.value + 'px',
  maxHeight: '520px',
  zIndex: 99999,
}))

onClickOutside(containerRef, () => { open.value = false })

async function togglePanel() {
  if (!open.value) {
    open.value = true
    await nextTick()          // DOM render bo'lishini kutamiz
    calcPosition()
  } else {
    open.value = false
  }
  if (open.value && store.unreadCount > 0) {
    setTimeout(() => store.markAllRead(), 1500)
  }
}

function calcPosition() {
  const btn = containerRef.value
  if (!btn) return
  const rect = btn.getBoundingClientRect()
  const panelWidth  = window.innerWidth < 640 ? 320 : 384
  const panelHeight = 520

  // Yuqoridan: tugma pastidan 8px
  let top = rect.bottom + 8
  // Pastga joy bo'lmasa — tugma ustiga chiqar
  if (top + panelHeight > window.innerHeight - 8) {
    top = Math.max(8, rect.top - panelHeight - 8)
  }

  // Chapdan: tugmaning o'ng chetigiga hizalab, kerak bo'lsa chapga siljit
  let left = rect.right - panelWidth
  if (left < 8) left = 8
  if (left + panelWidth > window.innerWidth - 8) {
    left = window.innerWidth - panelWidth - 8
  }

  panelTop.value  = top
  panelLeft.value = left
}

function handleClick(n) {
  store.markRead(n.id)
  if (n.case_id) {
    open.value = false
    router.push(`/cases/${n.case_id}`)
  }
}

const PRIORITY_BG = {
  critical: 'bg-red-500/20',
  high:     'bg-orange-500/20',
  medium:   'bg-yellow-500/20',
  low:      'bg-green-500/20',
}
const PRIORITY_ICON = {
  critical: '🔴',
  high:     '🟠',
  medium:   '🟡',
  low:      '🟢',
}
function priorityBg(p)   { return PRIORITY_BG[p]   || 'bg-surface-700' }
function priorityIcon(p) { return PRIORITY_ICON[p] || '📋' }

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60)  return t('notifications.seconds_ago', { count: diff })
  if (diff < 3600) return t('notifications.minutes_ago', { count: Math.floor(diff / 60) })
  if (diff < 86400) return t('notifications.hours_ago', { count: Math.floor(diff / 3600) })
  return new Date(iso).toLocaleDateString()
}
</script>

<style>
.dropdown-enter-active, .dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}
</style>

<style scoped>
@keyframes pulse-once {
  0%, 100% { transform: scale(1); }
  50%       { transform: scale(1.3); }
}
.animate-pulse-once {
  animation: pulse-once 0.4s ease;
}
</style>

