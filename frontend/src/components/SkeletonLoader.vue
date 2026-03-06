<template>
  <template v-for="n in count" :key="n">
    <!-- Card skeleton -->
    <div v-if="type === 'card'" class="card p-5 flex items-center gap-4">
      <div class="w-12 h-12 rounded-xl bg-surface-800 animate-pulse flex-shrink-0"></div>
      <div class="flex-1 space-y-2">
        <div class="h-5 w-16 bg-surface-800 rounded animate-pulse"></div>
        <div class="h-3 w-24 bg-surface-800/70 rounded animate-pulse"></div>
      </div>
    </div>

    <!-- Table row skeleton -->
    <tr v-else-if="type === 'table-row'" class="border-b border-surface-800/50">
      <td v-for="col in cols" :key="col" class="px-5 py-4">
        <div class="h-4 rounded animate-pulse bg-surface-800"
          :style="{ width: randomWidth(col) }"></div>
      </td>
    </tr>

    <!-- Text skeleton -->
    <div v-else-if="type === 'text'" class="space-y-2.5">
      <div class="h-3.5 bg-surface-800 rounded animate-pulse" :style="{ width: '100%' }"></div>
      <div class="h-3.5 bg-surface-800 rounded animate-pulse" :style="{ width: '85%' }"></div>
      <div class="h-3.5 bg-surface-800 rounded animate-pulse" :style="{ width: '60%' }"></div>
    </div>

    <!-- Avatar skeleton -->
    <div v-else-if="type === 'avatar'" class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-full bg-surface-800 animate-pulse flex-shrink-0"></div>
      <div class="space-y-1.5">
        <div class="h-3.5 w-24 bg-surface-800 rounded animate-pulse"></div>
        <div class="h-2.5 w-16 bg-surface-800/70 rounded animate-pulse"></div>
      </div>
    </div>

    <!-- Chart skeleton -->
    <div v-else-if="type === 'chart'" class="card p-6">
      <div class="h-4 w-28 bg-surface-800 rounded animate-pulse mb-2"></div>
      <div class="h-3 w-20 bg-surface-800/60 rounded animate-pulse mb-5"></div>
      <div class="flex items-end justify-between gap-1.5 h-40">
        <div v-for="b in 8" :key="b" class="flex-1 rounded-t-md bg-surface-800 animate-pulse"
          :style="{ height: (20 + Math.random() * 80) + '%' }"></div>
      </div>
    </div>

    <!-- Detail page skeleton -->
    <div v-else-if="type === 'detail'" class="space-y-6">
      <!-- Title row -->
      <div class="flex items-center gap-3">
        <div class="h-6 w-28 bg-surface-800 rounded animate-pulse"></div>
        <div class="h-5 w-20 bg-surface-800 rounded-full animate-pulse"></div>
        <div class="h-5 w-16 bg-surface-800 rounded-full animate-pulse"></div>
      </div>
      <div class="h-3 w-40 bg-surface-800/60 rounded animate-pulse"></div>

      <!-- Content grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 space-y-6">
          <!-- Description card -->
          <div class="card p-6 space-y-3">
            <div class="h-4 w-32 bg-surface-800 rounded animate-pulse"></div>
            <div class="h-3.5 w-full bg-surface-800/70 rounded animate-pulse"></div>
            <div class="h-3.5 w-4/5 bg-surface-800/70 rounded animate-pulse"></div>
            <div class="h-3.5 w-3/5 bg-surface-800/70 rounded animate-pulse"></div>
          </div>
          <!-- Chat card -->
          <div class="card p-6 space-y-4">
            <div class="h-4 w-24 bg-surface-800 rounded animate-pulse"></div>
            <div v-for="i in 3" :key="i" class="flex gap-2" :class="i % 2 ? '' : 'flex-row-reverse'">
              <div class="w-7 h-7 rounded-full bg-surface-800 animate-pulse flex-shrink-0"></div>
              <div class="h-16 w-48 rounded-2xl bg-surface-800 animate-pulse"></div>
            </div>
          </div>
        </div>
        <!-- Sidebar -->
        <div class="space-y-6">
          <div class="card p-5 space-y-4">
            <div class="h-4 w-20 bg-surface-800 rounded animate-pulse"></div>
            <div v-for="i in 5" :key="i" class="flex justify-between">
              <div class="h-3 w-16 bg-surface-800/60 rounded animate-pulse"></div>
              <div class="h-3 w-20 bg-surface-800 rounded animate-pulse"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
</template>

<script setup>
defineProps({
  type:  { type: String, default: 'text' },
  count: { type: Number, default: 1 },
  cols:  { type: Number, default: 6 },
})

const widths = ['40%', '55%', '70%', '30%', '50%', '60%', '45%', '65%']
function randomWidth(col) {
  return widths[(col * 3 + 7) % widths.length]
}
</script>

