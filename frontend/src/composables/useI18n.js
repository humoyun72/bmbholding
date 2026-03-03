/**
 * useI18n — Frontend i18n composable (vue-i18n ga bog'liq emas)
 * =============================================================
 * Ishlatish:
 *   import { useI18n } from '@/composables/useI18n'
 *   const { t, currentLang, setLang } = useI18n()
 *
 *   t('nav.dashboard')           → "Bosh sahifa"
 *   t('status.new')              → "Yangi"
 *   t('audit.page_of', { current: 1, total: 5 }) → "1 / 5 sahifa"
 *
 * Til localStorage "app_lang" kaliti bilan saqlanadi.
 * Tarjima topilmasa — kalit o'zi qaytariladi (tushib qolmaydi).
 */

import { ref } from 'vue'

// ── Locales lazy import ──────────────────────────────────────────────────────
import uz from '@/locales/uz.json'
import ru from '@/locales/ru.json'
import en from '@/locales/en.json'

const TRANSLATIONS = { uz, ru, en }
const SUPPORTED_LANGS = ['uz', 'ru', 'en']
const STORAGE_KEY = 'app_lang'
const DEFAULT_LANG = 'uz'

// ── Reaktiv til holati (modul darajasida — barcha komponentlar uchun umumiy) ─
function getInitialLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && SUPPORTED_LANGS.includes(saved)) return saved
  } catch {
    // localStorage mavjud bo'lmasa (SSR, etc.)
  }
  return DEFAULT_LANG
}

const currentLang = ref(getInitialLang())

// ── Asosiy t() funksiyasi ────────────────────────────────────────────────────
/**
 * Kalit bo'yicha joriy tildagi tarjimani qaytaradi.
 * @param {string} key      - Nuqta bilan ajratilgan kalit: "nav.dashboard"
 * @param {object} [params] - Shablon parametrlari: { current: 1, total: 5 }
 * @returns {string}
 */
function t(key, params) {
  const lang = currentLang.value
  const dict = TRANSLATIONS[lang] || TRANSLATIONS[DEFAULT_LANG]

  // Kalit bo'yicha nested lookup: "nav.dashboard" → dict.nav.dashboard
  const value = key.split('.').reduce((obj, k) => {
    if (obj && typeof obj === 'object') return obj[k]
    return undefined
  }, dict)

  if (value === undefined || value === null) {
    // Fallback: DEFAULT_LANG dan urinib ko'r
    if (lang !== DEFAULT_LANG) {
      const fallbackDict = TRANSLATIONS[DEFAULT_LANG]
      const fallback = key.split('.').reduce((obj, k) => {
        if (obj && typeof obj === 'object') return obj[k]
        return undefined
      }, fallbackDict)
      if (fallback !== undefined && fallback !== null) {
        return applyParams(String(fallback), params)
      }
    }
    // Kalit topilmasa — kalitning o'zi
    return key
  }

  return applyParams(String(value), params)
}

/**
 * {placeholder} shablon o'rnini to'ldiradi.
 */
function applyParams(text, params) {
  if (!params || typeof params !== 'object') return text
  return text.replace(/\{(\w+)}/g, (_, k) =>
    params[k] !== undefined ? String(params[k]) : `{${k}}`
  )
}

// ── setLang funksiyasi ───────────────────────────────────────────────────────
/**
 * Tilni o'zgartiradi va localStorage ga saqlaydi.
 * @param {'uz'|'ru'|'en'} lang
 */
function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) return
  currentLang.value = lang
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // ignore
  }
}

// ── Composable ───────────────────────────────────────────────────────────────
export function useI18n() {
  return {
    t,
    currentLang,       // ref — reaktiv, watch/v-bind uchun
    setLang,
    supportedLangs: SUPPORTED_LANGS,
  }
}

// ── Global singleton uchun to'g'ridan eksport ────────────────────────────────
export { t, currentLang, setLang, SUPPORTED_LANGS }

