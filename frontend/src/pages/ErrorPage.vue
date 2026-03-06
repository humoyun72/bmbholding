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
          ← Orqaga
        </button>
        <router-link to="/dashboard" class="btn-primary text-sm">
          🏠 Bosh sahifaga
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

const props = defineProps({
  code: { type: [Number, String], default: 404 },
})

const router = useRouter()
const route = useRoute()

// Route meta dan override qilish imkoniyati
const code = computed(() => route.meta?.errorCode || props.code)

const ERROR_MAP = {
  403: {
    icon: '🔒',
    iconBg: 'bg-amber-500/10 border border-amber-500/20',
    codeColor: 'text-amber-500/80',
    title: 'Ruxsat berilmagan',
    description: 'Sizda bu sahifaga kirish huquqi yo\'q. Agar bu xato deb o\'ylasangiz, administratorga murojaat qiling.',
  },
  404: {
    icon: '🔍',
    iconBg: 'bg-brand-500/10 border border-brand-500/20',
    codeColor: 'text-brand-500/80',
    title: 'Sahifa topilmadi',
    description: 'Siz qidirayotgan sahifa mavjud emas, o\'chirilgan yoki manzil noto\'g\'ri kiritilgan bo\'lishi mumkin.',
  },
  500: {
    icon: '⚠️',
    iconBg: 'bg-red-500/10 border border-red-500/20',
    codeColor: 'text-red-500/80',
    title: 'Server xatosi',
    description: 'Serverda kutilmagan xatolik yuz berdi. Iltimos, biroz kutib qayta urinib ko\'ring yoki administratorga xabar bering.',
  },
  502: {
    icon: '🔌',
    iconBg: 'bg-orange-500/10 border border-orange-500/20',
    codeColor: 'text-orange-500/80',
    title: 'Server javob bermayapti',
    description: 'Backend server hozirda ishlamayapti yoki texnik xizmat ko\'rsatilmoqda. Biroz kutib qayta urinib ko\'ring.',
  },
  503: {
    icon: '🛠️',
    iconBg: 'bg-yellow-500/10 border border-yellow-500/20',
    codeColor: 'text-yellow-500/80',
    title: 'Texnik xizmat',
    description: 'Tizimda texnik ishlar olib borilmoqda. Iltimos, biroz vaqtdan keyin qayta kiring.',
  },
  429: {
    icon: '🐌',
    iconBg: 'bg-purple-500/10 border border-purple-500/20',
    codeColor: 'text-purple-500/80',
    title: 'Juda ko\'p so\'rov',
    description: 'Siz juda ko\'p so\'rov yubordingiz. Iltimos, biroz kutib qayta urinib ko\'ring.',
  },
}

const FALLBACK = {
  icon: '❌',
  iconBg: 'bg-red-500/10 border border-red-500/20',
  codeColor: 'text-red-500/80',
  title: 'Xatolik yuz berdi',
  description: 'Kutilmagan xatolik. Iltimos qayta urinib ko\'ring yoki administratorga murojaat qiling.',
}

const config = computed(() => ERROR_MAP[code.value] || FALLBACK)

function goBack() {
  if (window.history.length > 2) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}
</script>

