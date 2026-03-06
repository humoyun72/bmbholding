<template>
  <div class="flex flex-col items-center justify-center py-16 px-4">
    <span class="text-4xl mb-4">{{ icon }}</span>
    <h3 class="text-white font-semibold text-base mb-1">{{ title || t('empty_state.default_title') }}</h3>
    <p v-if="description" class="text-surface-500 text-sm text-center max-w-xs mb-5">{{ description }}</p>
    <button v-if="action && actionFn" @click="actionFn" class="btn-ghost text-sm">
      {{ action }}
    </button>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'
const { t } = useI18n()

defineProps({
  icon:        { type: String, default: '📭' },
  title:       { type: String, default: '' },
  description: { type: String, default: '' },
  action:      { type: String, default: '' },
  actionFn:    { type: Function, default: null },
})
</script>
