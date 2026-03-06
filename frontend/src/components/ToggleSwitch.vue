<template>
  <div class="flex items-center justify-between gap-4">
    <div class="min-w-0">
      <div class="text-sm font-medium text-surface-200">{{ label }}</div>
      <div v-if="description" class="text-xs text-surface-500 mt-0.5">{{ description }}</div>
    </div>
    <button
      type="button"
      @click="$emit('update:modelValue', !modelValue)"
      :class="modelValue ? 'bg-brand-500' : 'bg-surface-600'"
      class="w-11 h-6 rounded-full transition-colors relative flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
      role="switch"
      :aria-checked="modelValue"
    >
      <span
        :class="modelValue ? 'translate-x-[22px]' : 'translate-x-1'"
        class="block w-4 h-4 bg-white rounded-full transition-transform duration-200 absolute top-1 shadow-sm"
      />
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, required: true },
  label:       { type: String,  default: '' },
  description: { type: String,  default: '' },
})
defineEmits(['update:modelValue'])
</script>

