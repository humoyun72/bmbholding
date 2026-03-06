<template>
  <div class="flex items-center justify-between px-5 py-4 border-t border-surface-800 flex-wrap gap-3">
    <!-- Left: total and per_page selector -->
    <div class="flex items-center gap-3">
      <span class="text-surface-500 text-sm">
        Sahifa {{ modelValue.page }} / {{ modelValue.pages }} (Jami: {{ modelValue.total }} ta yozuv)
      </span>
      <select
        :value="modelValue.per_page"
        @change="changePerPage(Number($event.target.value))"
        class="input text-sm py-1 px-2 w-20"
      >
        <option v-for="size in pageSizes" :key="size" :value="size">{{ size }}</option>
      </select>
    </div>

    <!-- Right: page navigation -->
    <div class="flex items-center gap-1">
      <button
        @click="changePage(modelValue.page - 1)"
        :disabled="modelValue.page <= 1"
        class="btn-ghost text-sm px-2 py-1 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ← Oldingi
      </button>

      <template v-for="p in visiblePages" :key="p">
        <span v-if="p === '...'" class="text-surface-600 px-1 text-sm">…</span>
        <button
          v-else
          @click="changePage(p)"
          :class="[
            'text-sm px-2.5 py-1 rounded transition-colors',
            p === modelValue.page
              ? 'bg-brand-600 text-white'
              : 'btn-ghost'
          ]"
        >
          {{ p }}
        </button>
      </template>

      <button
        @click="changePage(modelValue.page + 1)"
        :disabled="modelValue.page >= modelValue.pages"
        class="btn-ghost text-sm px-2 py-1 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Keyingi →
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
    // { page, per_page, total, pages }
  },
  pageSizes: {
    type: Array,
    default: () => [25, 50, 100],
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const visiblePages = computed(() => {
  const total = props.modelValue.pages
  const current = props.modelValue.page
  if (total <= 7) {
    const pages = []
    for (let i = 1; i <= total; i++) pages.push(i)
    return pages
  }

  const pages = []

  // Always show first page
  pages.push(1)

  if (current > 3) {
    pages.push('...')
  }

  // Pages around current
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (current < total - 2) {
    pages.push('...')
  }

  // Always show last page
  if (total > 1) {
    pages.push(total)
  }

  return pages
})

function changePage(p) {
  if (p < 1 || p > props.modelValue.pages) return
  emit('update:modelValue', { ...props.modelValue, page: p })
  emit('change')
}

function changePerPage(size) {
  emit('update:modelValue', { ...props.modelValue, per_page: size, page: 1 })
  emit('change')
}
</script>
