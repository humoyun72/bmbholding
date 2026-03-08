<template>
  <div class="flex h-screen bg-surface-950 overflow-hidden">

    <!-- Mobile overlay -->
    <Transition name="fade">
      <div v-if="sidebarOpen"
        class="fixed inset-0 bg-black/60 z-30 lg:hidden"
        @click="sidebarOpen = false" />
    </Transition>

    <!-- Sidebar -->
    <aside :class="[
      'fixed lg:static inset-y-0 left-0 z-40 w-64 flex-shrink-0',
      'bg-surface-900 border-r border-surface-800 flex flex-col',
      'transition-transform duration-300 ease-in-out',
      sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]">
      <!-- Logo -->
      <div class="p-5 border-b border-surface-800">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-glow-sm">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-bold text-white text-sm">{{ adminPanelName }}</div>
            <div class="text-surface-500 text-xs">{{ t('common.control_panel') }}</div>
          </div>
          <!-- Close btn mobile -->
          <button @click="sidebarOpen = false"
            class="lg:hidden w-7 h-7 flex items-center justify-center rounded-lg text-surface-400 hover:text-white hover:bg-surface-800">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
          <!-- Bell desktop (inside sidebar header) -->
          <div class="hidden lg:flex items-center gap-1">
            <NotificationBell v-if="auth.isAdmin || auth.isInvestigator" />
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path"
          :class="['sidebar-link', { 'active': isActive(item.path) }]"
          @click="sidebarOpen = false">
          <component :is="item.icon" class="w-4 h-4 flex-shrink-0" />
          {{ item.label }}
          <span v-if="item.badge" class="ml-auto badge bg-brand-600/20 text-brand-400 border border-brand-500/20">
            {{ item.badge }}
          </span>
        </RouterLink>
      </nav>

      <!-- Language switcher -->
      <div class="px-4 pb-3">
        <div class="flex gap-1 bg-surface-800 rounded-xl p-1">
          <button v-for="lang in supportedLangs" :key="lang"
            @click="selectLang(lang)"
            :class="[
              'flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-all',
              currentLang === lang
                ? 'bg-surface-600 text-white shadow-sm'
                : 'text-surface-400 hover:text-surface-200'
            ]">
            {{ langFlags[lang] }}
          </button>
        </div>
      </div>

      <!-- User info -->
      <div class="p-4 border-t border-surface-800">
        <div class="flex items-center gap-3 p-3 rounded-xl hover:bg-surface-800 transition-colors cursor-pointer group">
          <div class="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {{ userInitials }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-white text-sm font-medium truncate">{{ auth.user?.fullName || auth.user?.username }}</div>
            <div class="text-surface-500 text-xs capitalize">{{ auth.user?.role }}</div>
          </div>
          <button @click="handleLogout" class="text-surface-500 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main content wrapper -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">

      <!-- Mobile top bar -->
      <header class="lg:hidden flex items-center justify-between px-4 h-14 bg-surface-900 border-b border-surface-800 flex-shrink-0">
        <button @click="sidebarOpen = true"
          class="w-9 h-9 flex items-center justify-center rounded-xl text-surface-400 hover:text-white hover:bg-surface-800">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 bg-brand-600 rounded-lg flex items-center justify-center">
            <svg class="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <span class="text-white font-semibold text-sm">{{ adminPanelName }}</span>
        </div>
        <div class="flex items-center gap-2">
          <NotificationBell v-if="auth.isAdmin || auth.isInvestigator" />
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto">
        <RouterView v-slot="{ Component, route: r }">
          <component :is="Component" :key="r.path" />
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h, watch, onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notifications'
import NotificationBell from '@/components/ui/NotificationBell.vue'
import { useI18n } from '@/composables/useI18n'
import api from '@/utils/api'

const { t, currentLang, setLang, supportedLangs } = useI18n()

const auth = useAuthStore()
const notif = useNotificationStore()
const route = useRoute()
const router = useRouter()

const sidebarOpen = ref(false)
const adminPanelName = ref('IntegrityBot')

watch(() => route.path, () => { sidebarOpen.value = false })

onMounted(async () => {
  notif.connect()
  try {
    const { data } = await api.get('/v1/settings/public')
    if (data.admin_panel_name) adminPanelName.value = data.admin_panel_name
  } catch (_) {}
})
onUnmounted(() => {
  notif.disconnect()
})

const userInitials = computed(() => {
  const name = auth.user?.fullName || auth.user?.username || 'U'
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
})

const langFlags = {
  uz: '🇺🇿 UZ',
  ru: '🇷🇺 RU',
  en: '🇬🇧 EN',
}

function selectLang(lang) {
  setLang(lang)
}

const icons = {
  dashboard: { render: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
    [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' })]
  )},
  cases: { render: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
    [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' })]
  )},
  polls: { render: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
    [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' })]
  )},
  users: { render: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
    [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' })]
  )},
  audit: { render: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
    [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' })]
  )},
  settings: { render: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor' },
    [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' })]
  )},
}

const navItems = computed(() => [
  { path: '/dashboard', label: t('nav.dashboard'), icon: icons.dashboard },
  { path: '/cases', label: t('nav.cases'), icon: icons.cases },
  { path: '/polls', label: t('nav.polls'), icon: icons.polls },
  ...(auth.isAdmin ? [{ path: '/users', label: t('nav.users'), icon: icons.users }] : []),
  ...(auth.isAdmin ? [{ path: '/audit', label: t('nav.audit'), icon: icons.audit }] : []),
  { path: '/settings', label: t('nav.settings'), icon: icons.settings },
])

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.dropdown-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.dropdown-leave-active { transition: opacity 0.1s ease, transform 0.1s ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }

/* Sahifa o'tish animatsiyasi */
.page-enter-active { transition: opacity 0.15s ease; }
.page-leave-active { transition: opacity 0.1s ease; }
.page-enter-from, .page-leave-to { opacity: 0; }
</style>
