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

    <!-- Dropdown panel — fixed positioning to avoid going off-screen -->
    <Transition name="dropdown">
      <div v-if="open"
        class="fixed w-80 sm:w-96 bg-surface-900 border border-surface-700 rounded-2xl
               shadow-2xl z-[9999] flex flex-col overflow-hidden"
        :style="panelStyle">

        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-surface-800">
          <div class="flex items-center gap-2">
            <span class="text-white font-semibold text-sm">Bildirishnomalar</span>
            <span v-if="store.unreadCount > 0"
              class="bg-red-500/20 text-red-400 text-xs font-medium px-2 py-0.5 rounded-full">
              {{ store.unreadCount }} yangi
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span :class="['text-xs flex items-center gap-1', store.connected ? 'text-green-400' : 'text-surface-500']">
              <span :class="['w-1.5 h-1.5 rounded-full', store.connected ? 'bg-green-400' : 'bg-surface-500']"></span>
              {{ store.connected ? 'Jonli' : 'Uzilgan' }}
            </span>
            <button v-if="store.notifications.length"
              @click="store.markAllRead()"
              class="text-xs text-brand-400 hover:text-brand-300 transition-colors">
              Barchasini o'qi
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
            <p class="text-sm">Bildirishnomalar yo'q</p>
          </div>

          <!-- Items -->
          <div v-for="n in store.notifications" :key="n.id"
            @click="handleClick(n)"
            :class="['flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors border-b border-surface-800/50',
              n.read ? 'hover:bg-surface-800/30' : 'bg-brand-600/5 hover:bg-brand-600/10']">

            <!-- Icon -->
            <div :class="['w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0 mt-0.5',
              priorityBg(n.priority)]">
              {{ priorityIcon(n.priority) }}
            </div>

            <!-- Content -->
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
            Hammasini tozalash
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { useNotificationStore } from '@/stores/notifications'

const store = useNotificationStore()
const router = useRouter()
const open = ref(false)
const containerRef = ref(null)

// Panel pozitsiyasini saqlash
const panelTop = ref(0)
const panelRight = ref(0)

const panelStyle = computed(() => ({
  top: panelTop.value + 'px',
  right: panelRight.value + 'px',
  maxHeight: '520px',
}))

onClickOutside(containerRef, () => { open.value = false })

function togglePanel() {
  if (!open.value) {
    // Bell tugmasining ekrandagi pozitsiyasini olish
    const btn = containerRef.value
    if (btn) {
      const rect = btn.getBoundingClientRect()
      const panelWidth = window.innerWidth < 640 ? 320 : 384  // w-80 : w-96

      // Yuqoridan: tugma pastidan 8px pastga
      panelTop.value = rect.bottom + 8

      // O'ngdan: ekran o'ng chetidan hisoblash
      const rightEdge = window.innerWidth - rect.right
      // Panel ekrandan chiqib ketmasligi uchun
      panelRight.value = Math.max(8, Math.min(rightEdge, window.innerWidth - panelWidth - 8))
    }
  }
  open.value = !open.value
  if (open.value && store.unreadCount > 0) {
    setTimeout(() => store.markAllRead(), 1500)
  }
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
  if (diff < 60)  return `${diff}s oldin`
  if (diff < 3600) return `${Math.floor(diff / 60)}d oldin`
  if (diff < 86400) return `${Math.floor(diff / 3600)}s oldin`
  return new Date(iso).toLocaleDateString('uz-UZ')
}
</script>

<style scoped>
.dropdown-enter-active, .dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}

@keyframes pulse-once {
  0%, 100% { transform: scale(1); }
  50%       { transform: scale(1.3); }
}
.animate-pulse-once {
  animation: pulse-once 0.4s ease;
}
</style>

