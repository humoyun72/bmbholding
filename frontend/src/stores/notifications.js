import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'

const WS_URL = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/ws/notifications`
})()

const PING_INTERVAL = 25_000   // 25s
const RECONNECT_DELAY = 4_000  // 4s
const MAX_NOTIFICATIONS = 50

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref([])   // { id, type, title, body, case_id, category, priority, is_anonymous, at, read }
  const connected = ref(false)
  const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)

  let _ws = null
  let _pingTimer = null
  let _reconnectTimer = null
  let _intentionalClose = false

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function _add(notification) {
    notifications.value.unshift({
      id: Date.now() + Math.random(),
      read: false,
      at: new Date().toISOString(),
      ...notification,
    })
    if (notifications.value.length > MAX_NOTIFICATIONS) {
      notifications.value.splice(MAX_NOTIFICATIONS)
    }
  }

  function _handleMessage(data) {
    switch (data.type) {
      case 'new_case':
        _add({
          type: 'new_case',
          title: '🔔 Yangi murojaat!',
          body: `${data.case_id} — ${categoryLabel(data.category)}`,
          case_id: data.case_id,
          category: data.category,
          priority: data.priority,
          is_anonymous: data.is_anonymous,
        })
        _playSound()
        break
      case 'pong':
        break
      default:
        break
    }
  }

  function _playSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.setValueAtTime(880, ctx.currentTime)
      osc.frequency.setValueAtTime(660, ctx.currentTime + 0.1)
      gain.gain.setValueAtTime(0.15, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + 0.3)
    } catch (_) {}
  }

  // ─── WebSocket lifecycle ───────────────────────────────────────────────────

  function connect() {
    const auth = useAuthStore()
    if (!auth.token || !['admin', 'investigator'].includes(auth.user?.role)) return
    if (_ws && _ws.readyState <= 1) return  // already connecting/open

    _intentionalClose = false
    const url = `${WS_URL}?token=${auth.token}`
    _ws = new WebSocket(url)

    _ws.onopen = () => {
      connected.value = true
      _pingTimer = setInterval(() => {
        if (_ws?.readyState === WebSocket.OPEN) {
          _ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, PING_INTERVAL)
    }

    _ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        _handleMessage(data)
      } catch (_) {}
    }

    _ws.onclose = () => {
      connected.value = false
      clearInterval(_pingTimer)
      if (!_intentionalClose) {
        _reconnectTimer = setTimeout(connect, RECONNECT_DELAY)
      }
    }

    _ws.onerror = () => {
      _ws?.close()
    }
  }

  function disconnect() {
    _intentionalClose = true
    clearInterval(_pingTimer)
    clearTimeout(_reconnectTimer)
    _ws?.close()
    _ws = null
    connected.value = false
  }

  // ─── Public actions ────────────────────────────────────────────────────────

  function markRead(id) {
    const n = notifications.value.find(n => n.id === id)
    if (n) n.read = true
  }

  function markAllRead() {
    notifications.value.forEach(n => { n.read = true })
  }

  function clear() {
    notifications.value = []
  }

  return {
    notifications, connected, unreadCount,
    connect, disconnect, markRead, markAllRead, clear,
  }
})

// ─── Category labels ───────────────────────────────────────────────────────
const CATEGORY_LABELS = {
  corruption: 'Korrupsiya',
  conflict_of_interest: "Manfaat to'q.",
  fraud: 'Firibgarlik',
  safety: 'Xavfsizlik',
  discrimination: 'Kamsitish',
  procurement: 'Tender',
  other: 'Boshqa',
}
function categoryLabel(k) { return CATEGORY_LABELS[k] || k }

