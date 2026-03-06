<template>
  <div class="min-h-screen bg-surface-950 flex items-center justify-center p-4 relative overflow-hidden">
    <!-- Background decoration -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-96 h-96 bg-brand-800/10 rounded-full blur-3xl"></div>
    </div>

    <div class="relative animate-fade-in text-center max-w-lg">
      <!-- Icon -->
      <div class="inline-flex items-center justify-center w-24 h-24 rounded-3xl mb-6"
        :class="config.iconBg">
        <span class="text-5xl">{{ config.icon }}</span>
      </div>

      <!-- Error code -->
      <div class="text-8xl font-black tracking-tight mb-2"
        :class="config.codeColor">
        {{ code }}
      </div>

      <!-- Title -->
      <h1 class="text-2xl font-bold text-white mb-3">{{ config.title }}</h1>

      <!-- Description -->
      <p class="text-surface-400 text-sm leading-relaxed max-w-sm mx-auto mb-8">
        {{ config.description }}
      </p>

      <!-- Actions -->
      <div class="flex items-center justify-center gap-3 flex-wrap">
        <button @click="goBack" class="btn-ghost text-sm">
          ← {{ t('error_page.back') }}
        </button>
        <router-link to="/dashboard" class="btn-primary text-sm">
          🏠 {{ t('error_page.home') }}
        </router-link>
      </div>

      <!-- Decorative line -->
      <div class="mt-10 flex items-center gap-3 justify-center">
        <div class="h-px w-12 bg-surface-800"></div>
        <span class="text-surface-600 text-xs">IntegrityBot</span>
        <div class="h-px w-12 bg-surface-800"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  code: { type: [Number, String], default: 404 },
})

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

// Route meta dan override qilish imkoniyati
const code = computed(() => route.meta?.errorCode || props.code)

const ERROR_MAP = computed(() => ({
  403: {
    icon: '🔒',
    iconBg: 'bg-amber-500/10 border border-amber-500/20',
    codeColor: 'text-amber-500/80',
    title: t('error_page.403_title'),
    description: t('error_page.403_desc'),
  },
  404: {
    icon: '🔍',
    iconBg: 'bg-brand-500/10 border border-brand-500/20',
    codeColor: 'text-brand-500/80',
    title: t('error_page.404_title'),
    description: t('error_page.404_desc'),
  },
  500: {
    icon: '⚠️',
    iconBg: 'bg-red-500/10 border border-red-500/20',
    codeColor: 'text-red-500/80',
    title: t('error_page.500_title'),
    description: t('error_page.500_desc'),
  },
  502: {
    icon: '🔌',
    iconBg: 'bg-orange-500/10 border border-orange-500/20',
    codeColor: 'text-orange-500/80',
    title: t('error_page.502_title'),
    description: t('error_page.502_desc'),
  },
  503: {
    icon: '🛠️',
    iconBg: 'bg-yellow-500/10 border border-yellow-500/20',
    codeColor: 'text-yellow-500/80',
    title: t('error_page.503_title'),
    description: t('error_page.503_desc'),
  },
  429: {
    icon: '🐌',
    iconBg: 'bg-purple-500/10 border border-purple-500/20',
    codeColor: 'text-purple-500/80',
    title: t('error_page.429_title'),
    description: t('error_page.429_desc'),
  },
}))

const FALLBACK = computed(() => ({
  icon: '❌',
  iconBg: 'bg-red-500/10 border border-red-500/20',
  codeColor: 'text-red-500/80',
  title: t('error_page.default_title'),
  description: t('error_page.default_desc'),
}))

const config = computed(() => ERROR_MAP.value[code.value] || FALLBACK.value)

function goBack() {
  if (window.history.length > 2) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}
</script>
