<template>
  <div class="flex flex-col items-center justify-center py-16 px-4">
    <div class="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-2xl mb-4">
      ⚠️
    </div>
    <h3 class="text-white font-semibold text-base mb-1">{{ t('error_state.title') }}</h3>
    <p class="text-surface-500 text-sm text-center max-w-sm mb-5">{{ message || t('error_state.default_message') }}</p>
    <button v-if="retry" @click="retry" class="btn-ghost text-sm flex items-center gap-2">
      🔄 {{ t('error_state.retry') }}
    </button>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'
const { t } = useI18n()

defineProps({
  message: { type: String, default: '' },
  retry:   { type: Function, default: null },
})
</script>
