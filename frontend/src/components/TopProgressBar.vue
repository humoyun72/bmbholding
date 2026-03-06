<template>
  <Transition name="progress">
    <div v-if="active" class="progress-bar">
      <div class="progress-bar__fill" :style="{ width: percent + '%' }"></div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'

const active  = ref(false)
const percent = ref(0)
let _timer    = null
let _reqCount = 0

function start() {
  _reqCount++
  if (_reqCount === 1) {
    active.value  = true
    percent.value = 15
    clearInterval(_timer)
    _timer = setInterval(() => {
      // Tezlik kamayib boradi — hech qachon 90% dan oshmaydi
      if (percent.value < 90) {
        percent.value += (90 - percent.value) * 0.08
      }
    }, 200)
  }
}

function finish() {
  _reqCount = Math.max(0, _reqCount - 1)
  if (_reqCount === 0) {
    clearInterval(_timer)
    percent.value = 100
    setTimeout(() => {
      active.value  = false
      percent.value = 0
    }, 300)
  }
}

onBeforeUnmount(() => { clearInterval(_timer) })

defineExpose({ start, finish })
</script>

<style scoped>
.progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  z-index: 99999;
  overflow: hidden;
}
.progress-bar__fill {
  height: 100%;
  background: linear-gradient(90deg, #6271f5, #8194fb, #6271f5);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  transition: width 0.3s ease;
  border-radius: 0 2px 2px 0;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.progress-enter-active { transition: opacity 0.15s ease; }
.progress-leave-active { transition: opacity 0.4s ease; }
.progress-enter-from, .progress-leave-to { opacity: 0; }
</style>

