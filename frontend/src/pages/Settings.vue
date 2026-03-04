<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in max-w-3xl">
    <div class="mb-6">
      <h1 class="text-xl sm:text-2xl font-bold text-white">Sozlamalar</h1>
      <p class="text-surface-400 text-sm mt-1">Profil, xavfsizlik, bot va tizim sozlamalari</p>
    </div>

    <!-- ── Tabs ── -->
    <div class="flex gap-1 mb-6 bg-surface-800 p-1 rounded-xl flex-wrap">
      <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
        :class="activeTab === tab.id ? 'bg-surface-600 text-white shadow-sm' : 'text-surface-400 hover:text-surface-200'"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap">
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- ════════════════════════════════════════════
         1. PROFIL
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'profile'" class="space-y-5">

      <!-- Avatar + info -->
      <div class="card p-6">
        <h3 class="font-semibold text-white mb-5">Profil ma'lumotlari</h3>
        <div class="flex items-center gap-4 mb-6">
          <div class="w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl flex items-center justify-center text-2xl text-white font-bold flex-shrink-0">
            {{ initials }}
          </div>
          <div>
            <div class="text-white font-semibold text-lg">{{ auth.user?.fullName || auth.user?.username }}</div>
            <div class="text-surface-400 text-sm">{{ roleLabel }}</div>
            <div class="text-surface-500 text-xs mt-0.5">{{ auth.user?.email || '—' }}</div>
          </div>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">To'liq ism</label>
              <input v-model="profileForm.full_name" type="text" class="input w-full" placeholder="Ism Familiya" />
            </div>
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">Email</label>
              <input v-model="profileForm.email" type="email" class="input w-full" placeholder="email@company.uz" />
            </div>
          </div>

          <!-- Interfeys tili -->
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">Interfeys tili</label>
            <div class="flex gap-2">
              <button v-for="lang in uiLangs" :key="lang.code"
                @click="profileForm.ui_lang = lang.code"
                :class="profileForm.ui_lang === lang.code
                  ? 'border-brand-500 bg-brand-500/15 text-brand-300'
                  : 'border-surface-600 text-surface-400 hover:border-surface-500'"
                class="flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all">
                {{ lang.flag }} {{ lang.label }}
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between pt-1 border-t border-surface-800">
            <p v-if="profileMsg" :class="profileMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">
              {{ profileMsg.text }}
            </p>
            <span v-else />
            <button @click="saveProfile" :disabled="profileSaving" class="btn-primary">
              {{ profileSaving ? '⏳ Saqlanmoqda...' : '💾 Saqlash' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Parol o'zgartirish -->
      <div class="card p-6">
        <h3 class="font-semibold text-white mb-5">Parol o'zgartirish</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">Joriy parol</label>
            <input v-model="pwdForm.current" type="password" class="input w-full" placeholder="••••••••" autocomplete="current-password" />
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">Yangi parol</label>
              <input v-model="pwdForm.new1" type="password" class="input w-full" placeholder="Kamida 8 belgi" autocomplete="new-password" />
            </div>
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">Tasdiqlash</label>
              <input v-model="pwdForm.new2" type="password" class="input w-full" placeholder="••••••••" autocomplete="new-password" />
            </div>
          </div>
          <p v-if="pwdForm.new1 && pwdForm.new2 && pwdForm.new1 !== pwdForm.new2" class="text-red-400 text-xs">
            ⚠️ Parollar mos kelmaydi
          </p>
          <div class="flex items-center justify-between pt-1 border-t border-surface-800">
            <p v-if="pwdMsg" :class="pwdMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ pwdMsg.text }}</p>
            <span v-else />
            <button @click="changePassword"
              :disabled="pwdSaving || !pwdForm.current || !pwdForm.new1 || pwdForm.new1 !== pwdForm.new2"
              class="btn-primary">
              {{ pwdSaving ? '⏳ Saqlanmoqda...' : '🔑 Parolni o\'zgartirish' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════════════════
         2. XAVFSIZLIK (2FA)
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'security'" class="space-y-5">
      <div class="card p-6">
        <div class="flex items-start justify-between mb-5">
          <div>
            <h3 class="font-semibold text-white">Ikki bosqichli autentifikatsiya (2FA)</h3>
            <p class="text-surface-500 text-sm mt-1">Google Authenticator yoki Authy bilan xavfsizlikni oshiring</p>
          </div>
          <span :class="auth.user?.totpEnabled
              ? 'bg-green-500/15 text-green-400 border-green-500/30'
              : 'bg-surface-700/50 text-surface-400 border-surface-600'"
            class="text-xs px-3 py-1 rounded-full border flex-shrink-0">
            {{ auth.user?.totpEnabled ? '● Yoqilgan' : '○ O\'chirilgan' }}
          </span>
        </div>

        <!-- 2FA yo'q -->
        <template v-if="!auth.user?.totpEnabled">
          <p class="text-surface-400 text-sm mb-4">
            2FA yoqilganda har safar kirishda Authenticator ilovasidan 6 xonali kod talab qilinadi.
          </p>
          <button v-if="!setupData" @click="setup2FA" :disabled="twoFaLoading" class="btn-primary">
            {{ twoFaLoading ? '⏳ Yuklanmoqda...' : '🔐 2FA ni yoqish' }}
          </button>
          <div v-if="setupData" class="mt-5 space-y-4">
            <p class="text-surface-400 text-sm">1. Quyidagi QR kodni Authenticator ilovangizga skanerlang:</p>
            <div class="bg-white p-4 rounded-2xl w-fit">
              <img :src="setupData.qr_code" alt="QR" class="w-52 h-52" />
            </div>
            <p class="text-surface-400 text-sm">2. Ilovada ko'rsatilgan 6 xonali kodni kiriting:</p>
            <div class="flex gap-3">
              <input v-model="totpCode" class="input font-mono tracking-widest text-center w-44"
                placeholder="000000" maxlength="6" inputmode="numeric" />
              <button @click="verify2FA" :disabled="totpCode.length !== 6 || verifying" class="btn-primary">
                {{ verifying ? '...' : '✅ Tasdiqlash' }}
              </button>
              <button @click="setupData = null; totpCode = ''" class="btn-ghost">Bekor</button>
            </div>
            <p v-if="setupError" class="text-red-400 text-sm">{{ setupError }}</p>
          </div>
        </template>

        <!-- 2FA yoqilgan -->
        <div v-else class="space-y-4">
          <div class="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
            <span class="text-2xl">🛡️</span>
            <div>
              <div class="text-green-300 font-medium text-sm">2FA faol</div>
              <div class="text-green-500/70 text-xs mt-0.5">Har safar kirishda Authenticator kodi talab qilinadi</div>
            </div>
          </div>
          <div v-if="!showDisable2FA">
            <button @click="showDisable2FA = true" class="btn-danger text-sm">🔓 2FA ni o'chirish</button>
          </div>
          <div v-else class="space-y-3 p-4 bg-red-500/5 border border-red-500/20 rounded-xl">
            <p class="text-red-400 text-sm font-medium">⚠️ O'chirish uchun hozirgi Authenticator kodini kiriting:</p>
            <div class="flex gap-3">
              <input v-model="disableTotpCode" type="text" inputmode="numeric"
                class="input font-mono tracking-widest text-center w-44" placeholder="000000" maxlength="6" />
              <button @click="disable2FA" :disabled="!disableTotpCode || disabling" class="btn-danger">
                {{ disabling ? '...' : 'O\'chirish' }}
              </button>
              <button @click="showDisable2FA = false; disableTotpCode = ''; disableError = ''" class="btn-ghost">Bekor</button>
            </div>
            <p v-if="disableError" class="text-red-400 text-sm">{{ disableError }}</p>
          </div>
        </div>
      </div>

      <!-- Sessiya ma'lumoti -->
      <div class="card p-6">
        <h3 class="font-semibold text-white mb-4">🔒 Sessiya xavfsizligi</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between py-2 border-b border-surface-800">
            <span class="text-surface-400">Oxirgi kirish</span>
            <span class="text-surface-200">Hozir (joriy sessiya)</span>
          </div>
          <div class="flex justify-between py-2 border-b border-surface-800">
            <span class="text-surface-400">Token muddati</span>
            <span class="text-surface-200">24 soat</span>
          </div>
          <div class="flex justify-between py-2">
            <span class="text-surface-400">IP manzil</span>
            <span class="text-surface-200">{{ currentIp || 'Aniqlanmoqda...' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════════════════
         3. BOT SOZLAMALARI
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'bot'" class="space-y-5">
      <div v-if="sysLoading" class="card p-6 text-center text-surface-400">⏳ Yuklanmoqda...</div>
      <template v-else>

        <!-- Asosiy bot sozlamalari -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">🤖 Bot asosiy sozlamalari</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                Admin guruh Telegram ID
                <span class="text-surface-500 font-normal ml-1">(yangi murojaatlar shu guruhga yuboriladi)</span>
              </label>
              <input v-model="sysForm.bot_admin_group_id" type="text" class="input w-full font-mono"
                placeholder="-100xxxxxxxxxx" />
              <p class="text-surface-600 text-xs mt-1">Guruh ID ni olish: guruhga @userinfobot ni qo'shing</p>
            </div>

            <!-- Ish vaqti -->
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-2">
                Murojaat qabul qilish vaqt oralig'i
              </label>
              <div class="flex items-center gap-3">
                <input v-model="sysForm.bot_working_hours_start" type="time" class="input w-36" />
                <span class="text-surface-400">—</span>
                <input v-model="sysForm.bot_working_hours_end" type="time" class="input w-36" />
              </div>
              <p class="text-surface-600 text-xs mt-1">Ish vaqtidan tashqarida kelgan murojaatlar ham qabul qilinadi, faqat xabar ko'rsatiladi</p>
            </div>

            <!-- Ish kunlari -->
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-2">Ish kunlari</label>
              <div class="flex gap-2 flex-wrap">
                <button v-for="day in weekDays" :key="day.num"
                  @click="toggleWorkDay(day.num)"
                  :class="workDaySet.has(day.num)
                    ? 'bg-brand-500/20 border-brand-500/50 text-brand-300'
                    : 'border-surface-600 text-surface-500 hover:border-surface-500'"
                  class="px-3 py-1.5 rounded-lg border text-sm transition-all">
                  {{ day.label }}
                </button>
              </div>
            </div>

            <!-- Qabul qilish tillari -->
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-2">Qabul qilinadigan tillar</label>
              <div class="flex gap-2">
                <button v-for="lang in botLangs" :key="lang.code"
                  @click="toggleBotLang(lang.code)"
                  :class="activeBotLangs.has(lang.code)
                    ? 'bg-brand-500/20 border-brand-500/50 text-brand-300'
                    : 'border-surface-600 text-surface-500 hover:border-surface-500'"
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm transition-all">
                  {{ lang.flag }} {{ lang.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Bot xabarlari -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">💬 Bot xabarlari</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                Xush kelibsiz xabari
                <span class="text-surface-500 font-normal ml-1">(/start buyrug'ida ko'rsatiladi)</span>
              </label>
              <textarea v-model="sysForm.bot_welcome_message" rows="3"
                class="input w-full resize-none"
                placeholder="Xush kelibsiz! Bu bot orqali anonim murojaat yuborishingiz mumkin." />
            </div>
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                Ish vaqtidan tashqari xabar
              </label>
              <textarea v-model="sysForm.bot_outside_hours_message" rows="2"
                class="input w-full resize-none"
                placeholder="Ish vaqti 08:00-18:00. Murojaatingiz qabul qilindi." />
            </div>
          </div>
        </div>

        <!-- Webhook -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-2">🔗 Telegram Webhook</h3>
          <p class="text-surface-400 text-sm mb-4">Bot polling rejimida ishlaса bu kerak emas. Webhook rejimida ulash uchun bosing.</p>
          <div class="flex items-center gap-3 flex-wrap">
            <button @click="setWebhook" :disabled="webhookLoading" class="btn-ghost text-sm">
              {{ webhookLoading ? '⏳ Ulanmoqda...' : '🔗 Webhook ulash' }}
            </button>
            <p v-if="webhookMsg" :class="webhookMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ webhookMsg.text }}</p>
          </div>
        </div>

        <!-- Saqlash tugmasi -->
        <div class="flex items-center justify-between">
          <p v-if="sysMsg" :class="sysMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ sysMsg.text }}</p>
          <span v-else />
          <button @click="saveSysSettings" :disabled="sysSaving" class="btn-primary">
            {{ sysSaving ? '⏳ Saqlanmoqda...' : '💾 Bot sozlamalarini saqlash' }}
          </button>
        </div>
      </template>
    </div>

    <!-- ════════════════════════════════════════════
         4. TIZIM SOZLAMALARI
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'system'" class="space-y-5">
      <div v-if="sysLoading" class="card p-6 text-center text-surface-400">⏳ Yuklanmoqda...</div>
      <template v-else>

        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">🏢 Tizim sozlamalari</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">Kompaniya nomi</label>
              <input v-model="sysForm.company_name" type="text" class="input w-full"
                placeholder="Company LLC" />
              <p class="text-surface-600 text-xs mt-1">Bot xabarlarida va hisobotlarda ko'rsatiladi</p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-surface-300 mb-1.5">Tizim tili</label>
                <select v-model="sysForm.system_language" class="input w-full">
                  <option value="uz">🇺🇿 O'zbek</option>
                  <option value="ru">🇷🇺 Русский</option>
                  <option value="en">🇬🇧 English</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-surface-300 mb-1.5">Vaqt zonasi</label>
                <select v-model="sysForm.timezone" class="input w-full">
                  <option value="Asia/Tashkent">Asia/Tashkent (UTC+5)</option>
                  <option value="Asia/Almaty">Asia/Almaty (UTC+5)</option>
                  <option value="Asia/Baku">Asia/Baku (UTC+4)</option>
                  <option value="Europe/Moscow">Europe/Moscow (UTC+3)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Bildirishnomalar -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">📊 Avtomatik Hisobotlar</h3>
          <div class="space-y-4">

            <!-- Kunlik hisobot -->
            <div class="border border-surface-700 rounded-xl p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm font-medium text-white">📅 Kunlik hisobot</div>
                  <div class="text-xs text-surface-500 mt-0.5">Har kuni belgilangan vaqtda ADMIN_CHAT_ID ga yuboriladi</div>
                </div>
                <button
                  @click="sysForm.notify_daily_report = sysForm.notify_daily_report === 'true' ? 'false' : 'true'"
                  :class="sysForm.notify_daily_report === 'true' ? 'bg-brand-500' : 'bg-surface-600'"
                  class="w-10 h-6 rounded-full transition-colors relative flex-shrink-0">
                  <span
                    :class="sysForm.notify_daily_report === 'true' ? 'translate-x-5' : 'translate-x-1'"
                    class="block w-4 h-4 bg-white rounded-full transition-transform absolute top-1"></span>
                </button>
              </div>
              <div v-if="sysForm.notify_daily_report === 'true'" class="flex items-center gap-3 pt-1">
                <label class="text-surface-400 text-xs whitespace-nowrap">Vaqt (O'zbekiston):</label>
                <input v-model="sysForm.notify_daily_report_time" type="time"
                  class="input w-28 text-sm" />
                <span class="text-surface-600 text-xs">UTC+5</span>
              </div>
            </div>

            <!-- Haftalik hisobot -->
            <div class="border border-surface-700 rounded-xl p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm font-medium text-white">📈 Haftalik hisobot</div>
                  <div class="text-xs text-surface-500 mt-0.5">Tanlangan kunda haftalik tahlil yuboriladi</div>
                </div>
                <button
                  @click="sysForm.notify_weekly_report = sysForm.notify_weekly_report === 'true' ? 'false' : 'true'"
                  :class="sysForm.notify_weekly_report === 'true' ? 'bg-brand-500' : 'bg-surface-600'"
                  class="w-10 h-6 rounded-full transition-colors relative flex-shrink-0">
                  <span
                    :class="sysForm.notify_weekly_report === 'true' ? 'translate-x-5' : 'translate-x-1'"
                    class="block w-4 h-4 bg-white rounded-full transition-transform absolute top-1"></span>
                </button>
              </div>
              <div v-if="sysForm.notify_weekly_report === 'true'" class="flex items-center gap-3 flex-wrap pt-1">
                <div class="flex items-center gap-2">
                  <label class="text-surface-400 text-xs whitespace-nowrap">Kun:</label>
                  <select v-model="sysForm.notify_weekly_report_day" class="input text-sm w-36">
                    <option v-for="d in reportWeekDays" :key="d.num" :value="String(d.num)">{{ d.label }}</option>
                  </select>
                </div>
                <div class="flex items-center gap-2">
                  <label class="text-surface-400 text-xs whitespace-nowrap">Vaqt:</label>
                  <input v-model="sysForm.notify_weekly_report_time" type="time" class="input w-28 text-sm" />
                  <span class="text-surface-600 text-xs">UTC+5</span>
                </div>
              </div>
            </div>

            <!-- Test yuborish -->
            <div class="flex items-center gap-3 pt-1">
              <button @click="sendTestReport" :disabled="testReportLoading"
                class="btn-ghost text-sm flex items-center gap-2 disabled:opacity-50">
                <svg v-if="testReportLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                <span v-else>🧪</span>
                Test hisobot yuborish
              </button>
              <span class="text-surface-600 text-xs">Darhol kunlik hisobot yuboriladi</span>
            </div>

          </div>
        </div>

        <!-- Tizim ma'lumoti -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-4">ℹ️ Tizim ma'lumoti</h3>
          <div class="text-sm divide-y divide-surface-800">
            <div class="flex justify-between py-2.5">
              <span class="text-surface-400">Versiya</span>
              <span class="text-surface-200">IntegrityBot v1.0</span>
            </div>
            <div class="flex justify-between py-2.5">
              <span class="text-surface-400">Muhit</span>
              <span class="text-green-400">● Development</span>
            </div>
            <div class="flex justify-between py-2.5">
              <span class="text-surface-400">Monitoring yoqish</span>
              <code class="text-surface-500 text-xs">docker-compose --profile monitoring up -d</code>
            </div>
          </div>
        </div>

        <!-- Saqlash -->
        <div class="flex items-center justify-between">
          <p v-if="sysMsg" :class="sysMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ sysMsg.text }}</p>
          <span v-else />
          <button @click="saveSysSettings" :disabled="sysSaving" class="btn-primary">
            {{ sysSaving ? '⏳ Saqlanmoqda...' : '💾 Tizim sozlamalarini saqlash' }}
          </button>
        </div>
      </template>
    </div>

  </div>

  <!-- Toast -->
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="toast.show"
        :class="toast.ok ? 'bg-green-900/90 border-green-700 text-green-200' : 'bg-red-900/90 border-red-700 text-red-200'"
        class="fixed bottom-6 right-6 z-[99999] flex items-center gap-3 border px-4 py-3 rounded-xl shadow-xl backdrop-blur-sm">
        <span>{{ toast.ok ? '✅' : '❌' }}</span>
        <span class="text-sm font-medium">{{ toast.msg }}</span>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'

const auth = useAuthStore()
const activeTab = ref('profile')

const tabs = [
  { id: 'profile',  icon: '👤', label: 'Profil'    },
  { id: 'security', icon: '🔐', label: 'Xavfsizlik' },
  { id: 'bot',      icon: '🤖', label: 'Bot'        },
  { id: 'system',   icon: '⚙️', label: 'Tizim'      },
]

const roleLabels = { admin: 'Administrator', investigator: 'Terguvchi', viewer: 'Kuzatuvchi' }
const roleLabel = computed(() => roleLabels[auth.user?.role] || auth.user?.role || '')
const initials = computed(() => {
  const name = auth.user?.fullName || auth.user?.username || 'U'
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
})

const uiLangs = [
  { code: 'uz', flag: '🇺🇿', label: "O'zbek" },
  { code: 'ru', flag: '🇷🇺', label: 'Русский' },
  { code: 'en', flag: '🇬🇧', label: 'English' },
]
const botLangs = [
  { code: 'uz', flag: '🇺🇿', label: "O'zbek" },
  { code: 'ru', flag: '🇷🇺', label: 'Русский' },
  { code: 'en', flag: '🇬🇧', label: 'English' },
]
const weekDays = [
  { num: 1, label: 'Du' }, { num: 2, label: 'Se' }, { num: 3, label: 'Ch' },
  { num: 4, label: 'Pa' }, { num: 5, label: 'Ju' }, { num: 6, label: 'Sh' },
  { num: 7, label: 'Ya' },
]

const reportWeekDays = [
  { num: 1, label: 'Dushanba'  },
  { num: 2, label: 'Seshanba'  },
  { num: 3, label: 'Chorshanba'},
  { num: 4, label: 'Payshanba' },
  { num: 5, label: 'Juma'      },
  { num: 6, label: 'Shanba'    },
  { num: 7, label: 'Yakshanba' },
]

const toast = ref({ show: false, ok: true, msg: '' })
function showToast(msg, ok = true) {
  toast.value = { show: true, ok, msg }
  setTimeout(() => { toast.value.show = false }, 3500)
}

const testReportLoading = ref(false)
async function sendTestReport() {
  testReportLoading.value = true
  try {
    const { data } = await api.post('/v1/settings/test-report')
    showToast(`✅ Test hisobot yuborildi (chat_id: ${data.chat_id})`)
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || 'Xatolik'), false)
  } finally {
    testReportLoading.value = false
  }
}

// ── PROFIL ──────────────────────────────────────────────────────
const profileForm = ref({ full_name: '', email: '', ui_lang: 'uz' })
const profileSaving = ref(false)
const profileMsg = ref(null)
const pwdForm = ref({ current: '', new1: '', new2: '' })
const pwdSaving = ref(false)
const pwdMsg = ref(null)
const currentIp = ref('')

onMounted(async () => {
  profileForm.value.full_name = auth.user?.fullName || ''
  profileForm.value.email = auth.user?.email || ''
  profileForm.value.ui_lang = localStorage.getItem('ui_lang') || 'uz'
  // Bot & system settings yuklash
  await loadSysSettings()
})

async function saveProfile() {
  profileSaving.value = true
  profileMsg.value = null
  try {
    const { data } = await api.put('/v1/auth/profile', {
      full_name: profileForm.value.full_name,
      email: profileForm.value.email,
    })
    if (auth.user) {
      auth.user.fullName = data.full_name
      auth.user.email = data.email
      localStorage.setItem('user', JSON.stringify(auth.user))
    }
    // Interfeys tilini saqlash
    localStorage.setItem('ui_lang', profileForm.value.ui_lang)
    profileMsg.value = { ok: true, text: '✅ Profil saqlandi' }
    setTimeout(() => { profileMsg.value = null }, 3000)
  } catch (e) {
    profileMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || 'Xatolik') }
  } finally {
    profileSaving.value = false
  }
}

async function changePassword() {
  pwdSaving.value = true
  pwdMsg.value = null
  try {
    await api.post('/v1/auth/change-password', {
      current_password: pwdForm.value.current,
      new_password: pwdForm.value.new1,
    })
    pwdMsg.value = { ok: true, text: '✅ Parol muvaffaqiyatli o\'zgartirildi' }
    pwdForm.value = { current: '', new1: '', new2: '' }
    setTimeout(() => { pwdMsg.value = null }, 4000)
  } catch (e) {
    pwdMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || 'Xatolik') }
  } finally {
    pwdSaving.value = false
  }
}

// ── 2FA ──────────────────────────────────────────────────────────
const twoFaLoading = ref(false)
const verifying = ref(false)
const setupData = ref(null)
const totpCode = ref('')
const setupError = ref('')
const showDisable2FA = ref(false)
const disableTotpCode = ref('')
const disableError = ref('')
const disabling = ref(false)

async function setup2FA() {
  twoFaLoading.value = true
  try {
    const { data } = await api.post('/v1/auth/setup-2fa')
    setupData.value = data
  } catch (e) {
    alert(e.response?.data?.detail || 'Xatolik')
  } finally {
    twoFaLoading.value = false
  }
}

async function verify2FA() {
  verifying.value = true
  setupError.value = ''
  try {
    await api.post('/v1/auth/verify-2fa', { code: totpCode.value })
    auth.user.totpEnabled = true
    localStorage.setItem('user', JSON.stringify(auth.user))
    setupData.value = null
    totpCode.value = ''
  } catch {
    setupError.value = 'Noto\'g\'ri kod. Qayta urinib ko\'ring.'
  } finally {
    verifying.value = false
  }
}

async function disable2FA() {
  disabling.value = true
  disableError.value = ''
  try {
    await api.post('/v1/auth/disable-2fa', { code: disableTotpCode.value })
    auth.user.totpEnabled = false
    localStorage.setItem('user', JSON.stringify(auth.user))
    showDisable2FA.value = false
    disableTotpCode.value = ''
  } catch (e) {
    disableError.value = e.response?.data?.detail === 'Invalid 2FA code'
      ? 'Noto\'g\'ri kod.' : (e.response?.data?.detail || 'Xatolik')
  } finally {
    disabling.value = false
  }
}

// ── BOT & TIZIM SOZLAMALARI ──────────────────────────────────────
const sysLoading = ref(true)
const sysSaving = ref(false)
const sysMsg = ref(null)
const sysForm = ref({
  company_name: 'Company',
  system_language: 'uz',
  timezone: 'Asia/Tashkent',
  bot_admin_group_id: '',
  bot_welcome_message: '',
  bot_working_hours_start: '08:00',
  bot_working_hours_end: '18:00',
  bot_working_days: '1,2,3,4,5',
  bot_languages: 'uz,ru,en',
  bot_outside_hours_message: '',
  notify_daily_report: 'true',
  notify_daily_report_time: '18:00',
  notify_weekly_report: 'true',
  notify_weekly_report_day: '1',
  notify_weekly_report_time: '09:00',
})

const workDaySet = computed({
  get: () => new Set(sysForm.value.bot_working_days.split(',').map(Number).filter(Boolean)),
  set: (s) => { sysForm.value.bot_working_days = [...s].sort().join(',') }
})

const activeBotLangs = computed({
  get: () => new Set(sysForm.value.bot_languages.split(',').filter(Boolean)),
  set: (s) => { sysForm.value.bot_languages = [...s].join(',') }
})

function toggleWorkDay(num) {
  const s = new Set(workDaySet.value)
  s.has(num) ? s.delete(num) : s.add(num)
  sysForm.value.bot_working_days = [...s].sort().join(',')
}

function toggleBotLang(code) {
  const s = new Set(activeBotLangs.value)
  if (s.has(code) && s.size <= 1) return // Kamida 1 til bo'lishi kerak
  s.has(code) ? s.delete(code) : s.add(code)
  sysForm.value.bot_languages = [...s].join(',')
}

async function loadSysSettings() {
  sysLoading.value = true
  try {
    const { data } = await api.get('/v1/settings')
    Object.keys(sysForm.value).forEach(k => {
      if (data[k] !== undefined) sysForm.value[k] = data[k]
    })
  } catch (e) {
    console.error('Settings yuklanmadi:', e)
  } finally {
    sysLoading.value = false
  }
}

async function saveSysSettings() {
  sysSaving.value = true
  sysMsg.value = null
  try {
    await api.put('/v1/settings', sysForm.value)
    sysMsg.value = { ok: true, text: '✅ Sozlamalar saqlandi' }
    setTimeout(() => { sysMsg.value = null }, 3000)
  } catch (e) {
    sysMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || 'Xatolik') }
  } finally {
    sysSaving.value = false
  }
}

// ── WEBHOOK ──────────────────────────────────────────────────────
const webhookLoading = ref(false)
const webhookMsg = ref(null)

async function setWebhook() {
  webhookLoading.value = true
  webhookMsg.value = null
  try {
    await api.post('/telegram/set-webhook')
    webhookMsg.value = { ok: true, text: '✅ Webhook muvaffaqiyatli ulandi!' }
  } catch (e) {
    webhookMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || e.message) }
  } finally {
    webhookLoading.value = false
  }
}
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(12px); }
</style>

