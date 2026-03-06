<template>
  <button
    :disabled="loading || disabled"
    :class="[variant === 'danger' ? 'btn-danger' : variant === 'ghost' ? 'btn-ghost' : 'btn-primary', $attrs.class]"
    @click="!loading && !disabled && $emit('click', $event)"
  >
    <svg v-if="loading" class="w-4 h-4 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
    </svg>
    <slot />
  </button>
</template>

<script setup>
defineProps({
  loading:  { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  variant:  { type: String,  default: 'primary' }, // 'primary' | 'danger' | 'ghost'
})
defineEmits(['click'])
</script>

