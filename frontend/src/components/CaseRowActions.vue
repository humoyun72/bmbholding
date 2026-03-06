<template>
  <!-- View button -->
  <button @click.stop="$emit('view')"
    class="p-1.5 rounded-lg text-surface-400 hover:text-brand-400 hover:bg-surface-700 transition-colors"
    :title="t('case_actions.view')">
    👀
  </button>

  <!-- Kebab menu trigger -->
  <div class="relative" ref="triggerRef">
    <button @click.stop="toggle" ref="btnRef"
      class="p-1.5 rounded-lg text-surface-400 hover:text-white hover:bg-surface-700 transition-colors">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z"/>
      </svg>
    </button>
  </div>

  <!-- Dropdown via Teleport -->
  <Teleport to="body">
    <Transition name="dropdown">
      <div v-if="open" ref="menuRef"
        class="fixed z-[99998] w-48 bg-surface-800 border border-surface-700 rounded-xl shadow-2xl overflow-hidden"
        :style="menuStyle"
        @click.stop>

        <!-- Boshlash — faqat new -->
        <button v-if="caseItem.status === 'new'"
          @click="doAction('start')"
          class="menu-item">
          <span>▶️</span> {{ t('case_actions.start') }}
        </button>

        <!-- Tayinlash — har doim -->
        <button @click="doAction('assign')" class="menu-item">
          <span>👤</span> {{ t('case_actions.assign') }}
        </button>

        <!-- Yakunlash — faqat in_progress -->
        <button v-if="caseItem.status === 'in_progress'"
          @click="doAction('complete')"
          class="menu-item">
          <span>✅</span> {{ t('case_actions.complete') }}
        </button>

        <!-- Rad etish — new va in_progress -->
        <button v-if="caseItem.status === 'new' || caseItem.status === 'in_progress'"
          @click="doAction('reject')"
          class="menu-item text-red-400 hover:!bg-red-500/10">
          <span>❌</span> {{ t('case_actions.reject') }}
        </button>

        <!-- Ajratgich -->
        <div class="border-t border-surface-700 my-1"></div>

        <!-- PDF eksport -->
        <button @click="doAction('pdf')" class="menu-item">
          <span>📄</span> {{ t('case_actions.pdf_export') }}
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from '@/composables/useI18n'
const { t } = useI18n()

defineProps({
  caseItem: { type: Object, required: true },
})

const emit = defineEmits(['view', 'action'])

const open = ref(false)
const btnRef = ref(null)
const menuRef = ref(null)
const triggerRef = ref(null)
const menuStyle = ref({})

function toggle() {
  if (open.value) {
    open.value = false
    return
  }
  open.value = true
  nextTick(positionMenu)
}

function positionMenu() {
  if (!btnRef.value) return
  const rect = btnRef.value.getBoundingClientRect()
  const menuW = 192 // w-48 = 12rem = 192px
  const menuH = 260 // approximate max height

  let top = rect.bottom + 4
  let left = rect.right - menuW

  // Pastga chiqib ketmasligi
  if (top + menuH > window.innerHeight) {
    top = rect.top - menuH - 4
  }
  // Chapga chiqib ketmasligi
  if (left < 8) left = 8

  menuStyle.value = {
    top: `${top}px`,
    left: `${left}px`,
  }
}

function doAction(action) {
  open.value = false
  emit('action', action)
}

function handleClickOutside(e) {
  if (open.value
    && triggerRef.value && !triggerRef.value.contains(e.target)
    && menuRef.value && !menuRef.value.contains(e.target)
  ) {
    open.value = false
  }
}

function handleScroll() {
  if (open.value) open.value = false
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside, true)
  document.addEventListener('scroll', handleScroll, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside, true)
  document.removeEventListener('scroll', handleScroll, true)
})
</script>

<style scoped>
.menu-item {
  @apply w-full text-left px-4 py-2.5 text-sm text-surface-200 hover:bg-surface-700 transition-colors flex items-center gap-2.5;
}
</style>
<style>
.dropdown-enter-active, .dropdown-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px) scale(0.97); }
</style>

