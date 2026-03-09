<template>
  <div class="p-4 sm:p-6 lg:p-8 animate-fade-in">
    <div class="mb-6">
      <h1 class="text-xl sm:text-2xl font-bold text-white">{{ t('settings.title') }}</h1>
      <p class="text-surface-400 text-sm mt-1">{{ t('settings.subtitle') }}</p>
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
        <h3 class="font-semibold text-white mb-5">{{ t('settings.profile_info') }}</h3>
        <div class="flex items-center gap-4 mb-6">
          <div class="w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl flex items-center justify-center text-2xl text-white font-bold flex-shrink-0">
            {{ initials }}
          </div>
          <div>
            <div class="text-white font-semibold text-lg">{{ auth.user?.fullName || auth.user?.username }}</div>
            <div class="text-surface-400 text-sm">{{ roleLabel }}</div>
            <div class="text-surface-500 text-xs mt-0.5">{{ auth.user?.email || '—' }}</div>
            <div class="mt-2">
              <span
                @click="activeTab = 'telegram'"
                :class="tgLinked
                  ? 'bg-green-500/15 text-green-400 border-green-500/30 cursor-default'
                  : 'bg-surface-700/50 text-surface-500 border-surface-600 cursor-pointer hover:border-brand-500/50 hover:text-brand-400'"
                class="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-all">
                <span>✈️</span>
                {{ tgLinked ? t('settings.tg_linked_info') : t('settings.tg_link_connect') }}
              </span>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.fullname') }}</label>
              <input v-model="profileForm.full_name" type="text" class="input w-full" :placeholder="t('settings.placeholder_name')" />
            </div>
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.email') }}</label>
              <input v-model="profileForm.email" type="email" class="input w-full" placeholder="email@company.uz" />
            </div>
          </div>

          <!-- Interfeys tili -->
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.ui_lang') }}</label>
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
              {{ profileSaving ? '⏳ ' + t('settings.saving') : '💾 ' + t('settings.save_btn') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Parol o'zgartirish -->
      <div class="card p-6">
        <h3 class="font-semibold text-white mb-5">{{ t('settings.change_password') }}</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.current_password') }}</label>
            <input v-model="pwdForm.current" type="password" class="input w-full" placeholder="••••••••" autocomplete="current-password" />
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.new_password') }}</label>
              <input v-model="pwdForm.new1" type="password" class="input w-full" :placeholder="t('settings.placeholder_pwd')" autocomplete="new-password" />
            </div>
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.confirm_password') }}</label>
              <input v-model="pwdForm.new2" type="password" class="input w-full" placeholder="••••••••" autocomplete="new-password" />
            </div>
          </div>
          <p v-if="pwdForm.new1 && pwdForm.new2 && pwdForm.new1 !== pwdForm.new2" class="text-red-400 text-xs">
            ⚠️ {{ t('settings.password_mismatch') }}
          </p>
          <div class="flex items-center justify-between pt-1 border-t border-surface-800">
            <p v-if="pwdMsg" :class="pwdMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ pwdMsg.text }}</p>
            <span v-else />
            <button @click="changePassword"
              :disabled="pwdSaving || !pwdForm.current || !pwdForm.new1 || pwdForm.new1 !== pwdForm.new2"
              class="btn-primary">
              {{ pwdSaving ? '⏳ ' + t('settings.saving') : '🔑 ' + t('settings.change_password_btn') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════════════════
         2. XAVFSIZLIK (2FA) — disabled
    ════════════════════════════════════════════ -->
    <div v-if="false && activeTab === 'security'" class="space-y-5">
      <div class="card p-6">
        <div class="flex items-start justify-between mb-5">
          <div>
            <h3 class="font-semibold text-white">{{ t('settings.tfa_title') }}</h3>
            <p class="text-surface-500 text-sm mt-1">{{ t('settings.tfa_desc') }}</p>
          </div>
          <span :class="auth.user?.totpEnabled
              ? 'bg-green-500/15 text-green-400 border-green-500/30'
              : 'bg-surface-700/50 text-surface-400 border-surface-600'"
            class="text-xs px-3 py-1 rounded-full border flex-shrink-0">
            {{ auth.user?.totpEnabled ? '● ' + t('settings.tfa_enabled') : '○ ' + t('settings.tfa_disabled') }}
          </span>
        </div>

        <!-- 2FA yo'q -->
        <template v-if="!auth.user?.totpEnabled">
          <p class="text-surface-400 text-sm mb-4">
            {{ t('settings.tfa_info') }}
          </p>
          <button v-if="!setupData" @click="setup2FA" :disabled="twoFaLoading" class="btn-primary">
            {{ twoFaLoading ? '⏳ ' + t('settings.tfa_loading') : '🔐 ' + t('settings.tfa_enable') }}
          </button>
          <div v-if="setupData" class="mt-5 space-y-4">
            <p class="text-surface-400 text-sm">{{ t('settings.tfa_scan_qr') }}</p>
            <div class="bg-white p-4 rounded-2xl w-fit">
              <img :src="setupData.qr_code" alt="QR" class="w-52 h-52" />
            </div>
            <p class="text-surface-400 text-sm">{{ t('settings.tfa_enter_code') }}</p>
            <div class="flex gap-3">
              <input v-model="totpCode" class="input font-mono tracking-widest text-center w-44"
                placeholder="000000" maxlength="6" inputmode="numeric" />
              <button @click="verify2FA" :disabled="totpCode.length !== 6 || verifying" class="btn-primary">
                {{ verifying ? '...' : '✅ ' + t('settings.tfa_verify') }}
              </button>
              <button @click="setupData = null; totpCode = ''" class="btn-ghost">{{ t('settings.tfa_cancel') }}</button>
            </div>
            <p v-if="setupError" class="text-red-400 text-sm">{{ setupError }}</p>
          </div>
        </template>

        <!-- 2FA yoqilgan -->
        <div v-else class="space-y-4">
          <div class="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
            <span class="text-2xl">🛡️</span>
            <div>
              <div class="text-green-300 font-medium text-sm">{{ t('settings.tfa_active') }}</div>
              <div class="text-green-500/70 text-xs mt-0.5">{{ t('settings.tfa_active_desc') }}</div>
            </div>
          </div>
          <div v-if="!showDisable2FA">
            <button @click="showDisable2FA = true" class="btn-danger text-sm">🔓 {{ t('settings.tfa_disable') }}</button>
          </div>
          <div v-else class="space-y-3 p-4 bg-red-500/5 border border-red-500/20 rounded-xl">
            <p class="text-red-400 text-sm font-medium">⚠️ {{ t('settings.tfa_disable_prompt') }}</p>
            <div class="flex gap-3">
              <input v-model="disableTotpCode" type="text" inputmode="numeric"
                class="input font-mono tracking-widest text-center w-44" placeholder="000000" maxlength="6" />
              <button @click="disable2FA" :disabled="!disableTotpCode || disabling" class="btn-danger">
                {{ disabling ? '...' : t('settings.tfa_disable_btn') }}
              </button>
              <button @click="showDisable2FA = false; disableTotpCode = ''; disableError = ''" class="btn-ghost">{{ t('settings.tfa_cancel') }}</button>
            </div>
            <p v-if="disableError" class="text-red-400 text-sm">{{ disableError }}</p>
          </div>
        </div>
      </div>

      <!-- Sessiya ma'lumoti -->
      <div class="card p-6">
        <h3 class="font-semibold text-white mb-4">🔒 {{ t('settings.session_security') }}</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between py-2 border-b border-surface-800">
            <span class="text-surface-400">{{ t('settings.last_login') }}</span>
            <span class="text-surface-200">{{ t('settings.current_session') }}</span>
          </div>
          <div class="flex justify-between py-2 border-b border-surface-800">
            <span class="text-surface-400">{{ t('settings.token_expiry') }}</span>
            <span class="text-surface-200">{{ t('settings.token_hours') }}</span>
          </div>
          <div class="flex justify-between py-2">
            <span class="text-surface-400">{{ t('settings.ip_address') }}</span>
            <span class="text-surface-200">{{ currentIp || t('settings.ip_detecting') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════════════════
         3. TELEGRAM BOG'LASH
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'telegram'" class="space-y-5">

      <!-- Hozirgi holat -->
      <div class="card p-6">
        <div class="flex items-start justify-between mb-5">
          <div>
            <h3 class="font-semibold text-white">{{ t('settings.tg_connect_title') }}</h3>
            <p class="text-surface-500 text-sm mt-1">
              {{ t('settings.tg_connect_desc') }}
            </p>
          </div>
          <span
            :class="tgLinked
              ? 'bg-green-500/15 text-green-400 border-green-500/30'
              : 'bg-surface-700/50 text-surface-400 border-surface-600'"
            class="text-xs px-3 py-1 rounded-full border flex-shrink-0">
            {{ tgLinked ? '● ' + t('settings.tg_linked') : '○ ' + t('settings.tg_not_linked') }}
          </span>
        </div>

        <!-- Bog'langan holat -->
        <div v-if="tgLinked" class="space-y-4">
          <div class="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
            <span class="text-3xl">✈️</span>
            <div>
              <div class="text-green-300 font-medium">{{ t('settings.tg_linked_info') }}</div>
              <div class="text-green-500/70 text-xs mt-0.5">
                {{ t('settings.tg_chat_id') }} <code class="font-mono">{{ tgChatId }}</code>
              </div>
            </div>
          </div>
          <div v-if="!showUnlink">
            <button @click="showUnlink = true" class="btn-danger text-sm">
              🔌 {{ t('settings.tg_unlink') }}
            </button>
          </div>
          <div v-else class="p-4 bg-red-500/5 border border-red-500/20 rounded-xl space-y-3">
            <p class="text-red-400 text-sm">⚠️ {{ t('settings.tg_unlink_confirm') }}</p>
            <div class="flex gap-2">
              <button @click="unlinkTelegram" :disabled="tgUnlinking" class="btn-danger text-sm">
                {{ tgUnlinking ? '⏳...' : '✅ ' + t('settings.tg_unlink_yes') }}
              </button>
              <button @click="showUnlink = false" class="btn-ghost text-sm">{{ t('settings.tg_cancel') }}</button>
            </div>
          </div>
        </div>

        <!-- Bog'lanmagan holat -->
        <div v-else class="space-y-5">
          <div class="flex items-start gap-3 p-4 bg-surface-700/40 border border-surface-700 rounded-xl">
            <span class="text-xl mt-0.5">ℹ️</span>
            <div class="text-surface-400 text-sm space-y-1">
              <p>{{ t('settings.tg_instructions_title') }}</p>
              <ol class="list-decimal list-inside space-y-1 text-surface-500 ml-1">
                <li>{{ t('settings.tg_step_1') }}</li>
                <li>{{ t('settings.tg_step_2') }}</li>
                <li>{{ t('settings.tg_step_3') }}</li>
                <li>{{ t('settings.tg_step_4') }}</li>
              </ol>
            </div>
          </div>

          <!-- Havola generatsiya -->
          <div v-if="!tgLinkData">
            <button @click="generateTgLink" :disabled="tgLinkLoading" class="btn-primary">
              {{ tgLinkLoading ? '⏳ ' + t('settings.tg_loading') : '🔗 ' + t('settings.tg_get_link') }}
            </button>
          </div>

          <!-- Havola tayyor -->
          <div v-else class="space-y-4">
            <!-- Havola + nusxa -->
            <div class="p-4 bg-surface-800 border border-surface-700 rounded-xl space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-surface-400 text-xs font-medium">{{ t('settings.tg_link_label') }}</span>
                <span class="text-surface-600 text-xs">{{ t('settings.tg_countdown', { seconds: tgLinkCountdown }) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <code class="flex-1 text-brand-300 text-xs bg-surface-900 px-3 py-2 rounded-lg break-all">
                  {{ tgLinkData.link }}
                </code>
                <button @click="copyLink" class="btn-ghost text-xs px-3 flex-shrink-0">
                  {{ linkCopied ? '✅' : '📋' }}
                </button>
              </div>

              <!-- Telegram da ochish tugmasi -->
              <a :href="tgLinkData.link" target="_blank" rel="noopener"
                class="btn-primary text-sm flex items-center justify-center gap-2 w-full">
                <span>✈️</span> {{ t('settings.tg_open_telegram') }}
              </a>
            </div>

            <!-- Polling: bog'lanish kutilmoqda -->
            <div class="flex items-center gap-3 p-3 bg-surface-800/60 rounded-xl border border-surface-700">
              <svg class="w-4 h-4 animate-spin text-brand-400 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <span class="text-surface-400 text-sm">{{ t('settings.tg_waiting') }}</span>
              <button @click="resetTgLink" class="ml-auto text-surface-600 text-xs hover:text-surface-400">
                {{ t('settings.tg_cancel') }}
              </button>
            </div>
          </div>

          <p v-if="tgLinkError" class="text-red-400 text-sm">{{ tgLinkError }}</p>
        </div>
      </div>

      <!-- Foyda qismi -->
      <div class="card p-5">
        <h4 class="text-sm font-semibold text-surface-300 mb-3">📲 {{ t('settings.tg_why_title') }}</h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div class="flex items-start gap-2 text-surface-400">
            <span class="text-green-400 mt-0.5">✓</span>
            <span>{{ t('settings.tg_benefit_1') }}</span>
          </div>
          <div class="flex items-start gap-2 text-surface-400">
            <span class="text-green-400 mt-0.5">✓</span>
            <span>{{ t('settings.tg_benefit_2') }}</span>
          </div>
          <div class="flex items-start gap-2 text-surface-400">
            <span class="text-green-400 mt-0.5">✓</span>
            <span>{{ t('settings.tg_benefit_3') }}</span>
          </div>
          <div class="flex items-start gap-2 text-surface-400">
            <span class="text-green-400 mt-0.5">✓</span>
            <span>{{ t('settings.tg_benefit_4') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════════════════════════════════════════
         4. DEADLINE & BILDIRISHNOMALAR
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'deadlines'" class="space-y-5">
      <div v-if="dlLoading" class="card p-6 text-center text-surface-400">⏳ {{ t('settings.loading') }}</div>
      <template v-else>

        <!-- Deadline bo'limi -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-2">📅 {{ t('settings.deadline_settings') }}</h3>
          <p class="text-surface-500 text-xs mb-5">{{ t('settings.deadline_desc') }}</p>

          <div class="border border-surface-700 rounded-xl overflow-hidden">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-surface-800/60">
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">{{ t('settings.deadline_priority') }}</th>
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">{{ t('settings.deadline_hours') }}</th>
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">{{ t('settings.deadline_description') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in deadlinePriorities" :key="p.key"
                  class="border-t border-surface-800">
                  <td class="px-4 py-3">
                    <span class="flex items-center gap-2 text-surface-200 font-medium">
                      {{ p.emoji }} {{ p.label }}
                    </span>
                  </td>
                  <td class="px-4 py-3">
                    <input type="number" min="1" v-model.number="dlForm[p.key]"
                      class="input w-24 text-center text-sm" />
                  </td>
                  <td class="px-4 py-3 text-surface-500 text-xs">
                    ≈ {{ formatDeadlineHours(dlForm[p.key]) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-if="dlValidationError" class="text-red-400 text-xs mt-3">⚠️ {{ dlValidationError }}</p>

          <div class="flex items-center justify-between pt-4">
            <p v-if="dlMsg" :class="dlMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ dlMsg.text }}</p>
            <span v-else />
            <button @click="saveDeadlines" :disabled="dlSaving" class="btn-primary">
              {{ dlSaving ? '⏳ ' + t('settings.saving') : '💾 ' + t('settings.save_btn') }}
            </button>
          </div>
        </div>

        <!-- Bildirishnoma togglelari -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-2">🔔 {{ t('settings.notification_settings') }}</h3>
          <p class="text-surface-500 text-xs mb-5">{{ t('settings.notification_desc') }}</p>

          <div class="space-y-4">
            <ToggleSwitch v-model="notifForm.notify_24h_before"
              :label="t('settings.notify_24h')"
              :description="t('settings.notify_24h_desc')" />
            <ToggleSwitch v-model="notifForm.notify_2h_before"
              :label="t('settings.notify_2h')"
              :description="t('settings.notify_2h_desc')" />
            <div class="border-t border-surface-800 pt-4">
              <ToggleSwitch v-model="notifForm.notify_on_overdue"
                :label="t('settings.notify_overdue')"
                :description="t('settings.notify_overdue_desc')" />
            </div>
            <ToggleSwitch v-model="notifForm.notify_overdue_daily"
              :label="t('settings.notify_overdue_daily')"
              :description="t('settings.notify_overdue_daily_desc')" />
          </div>

          <!-- Kanal tanlash -->
          <div class="mt-5 pt-4 border-t border-surface-800">
            <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('settings.notification_channel') }}</label>
            <div class="flex gap-2">
              <button v-for="ch in channelOptions" :key="ch.value"
                @click="notifForm.notify_channel = ch.value"
                :class="notifForm.notify_channel === ch.value
                  ? 'border-brand-500 bg-brand-500/15 text-brand-300'
                  : 'border-surface-600 text-surface-400 hover:border-surface-500'"
                class="flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-all">
                {{ ch.icon }} {{ ch.label }}
              </button>
            </div>
          </div>
        </div>

        <!-- Hisobot jadvali -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">📊 {{ t('settings.auto_reports') }}</h3>
          <div class="space-y-4">

            <!-- Kunlik hisobot -->
            <div class="border border-surface-700 rounded-xl p-4 space-y-3">
              <ToggleSwitch v-model="notifForm.daily_report_enabled"
                :label="'📅 ' + t('settings.daily_report')"
                :description="t('settings.daily_report_desc')" />
              <div v-if="notifForm.daily_report_enabled" class="flex items-center gap-3 pt-1 pl-1">
                <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('settings.daily_report_time') }}</label>
                <input v-model="notifForm.daily_report_time" type="time" class="input w-28 text-sm" />
                <span class="text-surface-600 text-xs">UTC+5</span>
                <button @click="sendTestDaily" :disabled="testDailyLoading"
                  class="btn-ghost text-xs px-3 py-1.5 ml-auto flex items-center gap-1.5">
                  <svg v-if="testDailyLoading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span v-else>🧪</span>
                  Test
                </button>
              </div>
            </div>

            <!-- Haftalik hisobot -->
            <div class="border border-surface-700 rounded-xl p-4 space-y-3">
              <ToggleSwitch v-model="notifForm.weekly_report_enabled"
                :label="'📈 ' + t('settings.weekly_report')"
                :description="t('settings.weekly_report_desc')" />
              <div v-if="notifForm.weekly_report_enabled" class="flex items-center gap-3 flex-wrap pt-1 pl-1">
                <div class="flex items-center gap-2">
                  <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('settings.weekly_report_day') }}</label>
                  <select v-model.number="notifForm.weekly_report_day" class="input text-sm w-36">
                    <option v-for="d in dlWeekDays" :key="d.num" :value="d.num">{{ d.label }}</option>
                  </select>
                </div>
                <div class="flex items-center gap-2">
                  <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('settings.weekly_report_time') }}</label>
                  <input v-model="notifForm.weekly_report_time" type="time" class="input w-28 text-sm" />
                  <span class="text-surface-600 text-xs">UTC+5</span>
                </div>
                <button @click="sendTestWeekly" :disabled="testWeeklyLoading"
                  class="btn-ghost text-xs px-3 py-1.5 ml-auto flex items-center gap-1.5">
                  <svg v-if="testWeeklyLoading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span v-else>🧪</span>
                  Test
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Saqlash -->
        <div class="flex items-center justify-between">
          <p v-if="notifMsg" :class="notifMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ notifMsg.text }}</p>
          <span v-else />
          <button @click="saveNotifications" :disabled="notifSaving" class="btn-primary">
            {{ notifSaving ? '⏳ ' + t('settings.saving') : '💾 ' + t('settings.save_notifications') }}
          </button>
        </div>
      </template>
    </div>

    <!-- ════════════════════════════════════════════
         5. BOT SOZLAMALARI
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'bot'" class="space-y-5">
      <div v-if="sysLoading" class="card p-6 text-center text-surface-400">⏳ {{ t('settings.loading') }}</div>
      <template v-else>

        <!-- Asosiy bot sozlamalari -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">🤖 {{ t('settings.bot_settings') }}</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                {{ t('settings.bot_admin_group_id') }}
                <span class="text-surface-500 font-normal ml-1">({{ t('settings.bot_admin_group_hint') }})</span>
              </label>
              <input v-model="sysForm.bot_admin_group_id" type="text" class="input w-full font-mono"
                placeholder="-100xxxxxxxxxx" />
              <p class="text-surface-600 text-xs mt-1">{{ t('settings.bot_admin_group_tip') }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                🗳️ So'rovnoma kanal/guruh ID
                <span class="text-surface-500 font-normal ml-1">(POLL_CHAT_ID)</span>
              </label>
              <input v-model="sysForm.poll_chat_id" type="text" class="input w-full font-mono"
                placeholder="-100xxxxxxxxxx" />
              <p class="text-surface-600 text-xs mt-1">So'rovnomalar shu kanal yoki guruhga yuboriladi</p>
            </div>

            <!-- Ish vaqti -->
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-2">
                {{ t('settings.bot_working_hours') }}
              </label>
              <div class="flex items-center gap-3">
                <input v-model="sysForm.bot_working_hours_start" type="time" class="input w-36" />
                <span class="text-surface-400">—</span>
                <input v-model="sysForm.bot_working_hours_end" type="time" class="input w-36" />
              </div>
              <p class="text-surface-600 text-xs mt-1">{{ t('settings.bot_working_hours_hint') }}</p>
            </div>

            <!-- Ish kunlari -->
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('settings.bot_working_days') }}</label>
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
              <label class="block text-sm font-medium text-surface-300 mb-2">{{ t('settings.bot_languages') }}</label>
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
          <h3 class="font-semibold text-white mb-5">💬 {{ t('settings.bot_messages') }}</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                {{ t('settings.bot_welcome_msg') }}
                <span class="text-surface-500 font-normal ml-1">({{ t('settings.bot_welcome_hint') }})</span>
              </label>
              <textarea v-model="sysForm.bot_welcome_message" rows="3"
                class="input w-full resize-none"
                :placeholder="t('settings.bot_welcome_placeholder')" />
            </div>
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">
                {{ t('settings.bot_outside_hours_msg') }}
              </label>
              <textarea v-model="sysForm.bot_outside_hours_message" rows="2"
                class="input w-full resize-none"
                :placeholder="t('settings.bot_outside_hours_placeholder')" />
            </div>
          </div>
        </div>

        <!-- Saqlash tugmasi -->
        <div class="flex items-center justify-between">
          <p v-if="sysMsg" :class="sysMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ sysMsg.text }}</p>
          <span v-else />
          <button @click="saveSysSettings" :disabled="sysSaving" class="btn-primary">
            {{ sysSaving ? '⏳ ' + t('settings.saving') : '💾 ' + t('settings.save_btn') }}
          </button>
        </div>
      </template>
    </div>

    <!-- ════════════════════════════════════════════
         5. TIZIM SOZLAMALARI
    ════════════════════════════════════════════ -->
    <div v-if="activeTab === 'system'" class="space-y-5">
      <div v-if="sysLoading" class="card p-6 text-center text-surface-400">⏳ {{ t('settings.loading') }}</div>
      <template v-else>

        <div class="card p-6">
          <h3 class="font-semibold text-white mb-5">🏢 {{ t('settings.section_system') }}</h3>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.company_name') }}</label>
              <input v-model="sysForm.company_name" type="text" class="input w-full"
                placeholder="Company LLC" />
              <p class="text-surface-600 text-xs mt-1">{{ t('settings.company_name_hint') }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-surface-300 mb-1.5">🖥️ Admin panel nomi</label>
              <input v-model="sysForm.admin_panel_name" type="text" class="input w-full"
                placeholder="IntegrityBot" />
              <p class="text-surface-600 text-xs mt-1">Admin panel sarlavhasida ko'rinadigan nom</p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.system_lang') }}</label>
                <select v-model="sysForm.system_language" class="input w-full">
                  <option value="uz">🇺🇿 O'zbek</option>
                  <option value="ru">🇷🇺 Русский</option>
                  <option value="en">🇬🇧 English</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-surface-300 mb-1.5">{{ t('settings.timezone') }}</label>
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
          <h3 class="font-semibold text-white mb-5">📊 {{ t('settings.auto_reports') }}</h3>
          <div class="space-y-4">

            <!-- Kunlik hisobot -->
            <div class="border border-surface-700 rounded-xl p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm font-medium text-white">📅 {{ t('settings.daily_report') }}</div>
                  <div class="text-xs text-surface-500 mt-0.5">{{ t('settings.daily_report_desc') }}</div>
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
                <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('settings.daily_report_time') }}</label>
                <input v-model="sysForm.notify_daily_report_time" type="time"
                  class="input w-28 text-sm" />
                <span class="text-surface-600 text-xs">UTC+5</span>
              </div>
            </div>

            <!-- Haftalik hisobot -->
            <div class="border border-surface-700 rounded-xl p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-sm font-medium text-white">📈 {{ t('settings.weekly_report') }}</div>
                  <div class="text-xs text-surface-500 mt-0.5">{{ t('settings.weekly_report_desc') }}</div>
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
                  <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('settings.weekly_report_day') }}</label>
                  <select v-model="sysForm.notify_weekly_report_day" class="input text-sm w-36">
                    <option v-for="d in reportWeekDays" :key="d.num" :value="String(d.num)">{{ d.label }}</option>
                  </select>
                </div>
                <div class="flex items-center gap-2">
                  <label class="text-surface-400 text-xs whitespace-nowrap">{{ t('settings.weekly_report_time') }}</label>
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
                Test
              </button>
              <span class="text-surface-600 text-xs">{{ t('settings.test') }}</span>
            </div>

          </div>
        </div>

        <!-- SMTP test -->
        <div class="card p-6">
          <h3 class="font-semibold text-white mb-2">📧 {{ t('settings.smtp_test_title') }}</h3>
          <p class="text-surface-500 text-xs mb-4">{{ t('settings.smtp_test_desc') }}</p>
          <div class="flex items-center gap-3 flex-wrap">
            <input v-model="smtpTestEmail" type="email" class="input flex-1 text-sm min-w-48"
              :placeholder="auth.user?.email || 'test@example.com'" />
            <button @click="sendTestEmail" :disabled="smtpTestLoading"
              class="btn-ghost text-sm flex items-center gap-2 disabled:opacity-50 whitespace-nowrap">
              <svg v-if="smtpTestLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <span v-else>🧪</span>
              {{ t('settings.smtp_test_btn') }}
            </button>
          </div>
        </div>

        <!-- Saqlash -->
        <div class="flex items-center justify-between">
          <p v-if="sysMsg" :class="sysMsg.ok ? 'text-green-400' : 'text-red-400'" class="text-sm">{{ sysMsg.text }}</p>
          <span v-else />
          <button @click="saveSysSettings" :disabled="sysSaving" class="btn-primary">
            {{ sysSaving ? '⏳ ' + t('settings.saving') : '💾 ' + t('settings.save_btn') }}
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'
import ToggleSwitch from '@/components/ToggleSwitch.vue'
import { useI18n } from '@/composables/useI18n'

const auth = useAuthStore()
const { t, setLang } = useI18n()
const activeTab = ref('profile')

const tabs = computed(() => {
  const baseTabs = [
    { id: 'profile',  icon: '👤', label: t('settings.tab_profile')  },
    { id: 'telegram', icon: '✈️', label: t('settings.tab_telegram') },
  ]
  if (auth.isAdmin) {
    baseTabs.push({ id: 'deadlines', icon: '⏰', label: t('settings.tab_deadlines') })
    baseTabs.push({ id: 'bot',    icon: '🤖', label: t('settings.tab_bot')    })
    baseTabs.push({ id: 'system', icon: '⚙️', label: t('settings.tab_system') })
  }
  return baseTabs
})

const roleLabel = computed(() => {
  const r = auth.user?.role
  if (r === 'admin') return t('users.role_admin')
  if (r === 'investigator') return t('users.role_investigator')
  if (r === 'viewer') return t('users.role_viewer')
  return r || ''
})
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
    showToast('✅ ' + t('settings.test_report_sent') + ` (chat_id: ${data.chat_id})`)
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || t('settings.error')), false)
  } finally {
    testReportLoading.value = false
  }
}

// ── DEADLINE & BILDIRISHNOMALAR ─────────────────────────────────
const dlLoading = ref(true)
const dlSaving = ref(false)
const dlMsg = ref(null)
const dlForm = ref({
  critical_hours: 24,
  high_hours: 72,
  medium_hours: 168,
  low_hours: 720,
})

const deadlinePriorities = computed(() => [
  { key: 'critical_hours', emoji: '🔴', label: t('priority.critical') },
  { key: 'high_hours',     emoji: '🟠', label: t('priority.high') },
  { key: 'medium_hours',   emoji: '🟡', label: t('priority.medium') },
  { key: 'low_hours',      emoji: '⚪', label: t('priority.low') },
])

const dlWeekDays = [
  { num: 0, label: 'Dushanba'  },
  { num: 1, label: 'Seshanba'  },
  { num: 2, label: 'Chorshanba'},
  { num: 3, label: 'Payshanba' },
  { num: 4, label: 'Juma'      },
  { num: 5, label: 'Shanba'    },
  { num: 6, label: 'Yakshanba' },
]

const channelOptions = [
  { value: 'telegram', icon: '✈️', label: 'Telegram' },
  { value: 'both',     icon: '📬', label: 'Ikkalasi' },
]

const dlValidationError = computed(() => {
  const c = dlForm.value.critical_hours
  const h = dlForm.value.high_hours
  const m = dlForm.value.medium_hours
  const l = dlForm.value.low_hours
  if (!c || !h || !m || !l) return t('settings.validation_all_required')
  if (c < 1) return t('settings.validation_min_1h')
  if (!(c < h && h < m && m < l)) return t('settings.validation_order')
  return ''
})

// test

function formatDeadlineHours(h) {
  if (!h || h < 1) return '—'
  if (h < 24) return `${h} ${t('common.hours')}`
  const d = Math.floor(h / 24)
  const rem = h % 24
  return rem ? `${d} ${t('common.days')} ${rem} ${t('common.hours')}` : `${d} ${t('common.days')}`
}

const notifForm = ref({
  notify_24h_before: true,
  notify_2h_before: false,
  notify_on_overdue: true,
  notify_overdue_daily: true,
  notify_channel: 'telegram',
  daily_report_enabled: true,
  daily_report_time: '18:00',
  weekly_report_enabled: true,
  weekly_report_day: 0,
  weekly_report_time: '09:00',
})
const notifSaving = ref(false)
const notifMsg = ref(null)
const testDailyLoading = ref(false)
const testWeeklyLoading = ref(false)
const smtpTestEmail = ref('')
const smtpTestLoading = ref(false)

async function loadDeadlineSettings() {
  dlLoading.value = true
  try {
    const [dlResp, notifResp] = await Promise.all([
      api.get('/v1/settings/deadlines'),
      api.get('/v1/settings/notifications'),
    ])
    Object.assign(dlForm.value, dlResp.data)
    Object.assign(notifForm.value, notifResp.data)
  } catch (e) {
    console.error('Deadline/notif settings yuklanmadi:', e)
  } finally {
    dlLoading.value = false
  }
}

async function saveDeadlines() {
  if (dlValidationError.value) {
    dlMsg.value = { ok: false, text: '❌ ' + dlValidationError.value }
    return
  }
  dlSaving.value = true
  dlMsg.value = null
  try {
    await api.put('/v1/settings/deadlines', dlForm.value)
    dlMsg.value = { ok: true, text: '✅ ' + t('settings.deadline_saved') }
    showToast('✅ ' + t('settings.deadline_applied'))
    setTimeout(() => { dlMsg.value = null }, 3000)
  } catch (e) {
    dlMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || t('settings.error')) }
  } finally {
    dlSaving.value = false
  }
}

async function saveNotifications() {
  notifSaving.value = true
  notifMsg.value = null
  try {
    await api.put('/v1/settings/notifications', notifForm.value)
    // Apply scheduler
    try { await api.post('/v1/settings/notifications/apply') } catch { /* ok */ }
    notifMsg.value = { ok: true, text: '✅ ' + t('settings.notif_saved') }
    showToast('✅ ' + t('settings.notif_saved'))
    setTimeout(() => { notifMsg.value = null }, 3000)
  } catch (e) {
    notifMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || t('settings.error')) }
  } finally {
    notifSaving.value = false
  }
}

async function sendTestDaily() {
  testDailyLoading.value = true
  try {
    const { data } = await api.post('/v1/settings/test-report')
    showToast('✅ ' + t('settings.test_daily_sent') + ` (chat_id: ${data.chat_id})`)
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || t('settings.error')), false)
  } finally {
    testDailyLoading.value = false
  }
}

async function sendTestWeekly() {
  testWeeklyLoading.value = true
  try {
    const { data } = await api.post('/v1/settings/test-weekly-report')
    showToast('✅ ' + t('settings.test_weekly_sent') + ` (chat_id: ${data.chat_id})`)
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || t('settings.error')), false)
  } finally {
    testWeeklyLoading.value = false
  }
}

async function sendTestEmail() {
  smtpTestLoading.value = true
  try {
    const email = smtpTestEmail.value.trim() || auth.user?.email
    const { data } = await api.post('/v1/settings/test-email', { email })
    showToast(`✅ ${t('settings.smtp_test_sent')} → ${data.to}`)
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || t('settings.error')), false)
  } finally {
    smtpTestLoading.value = false
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
  // Telegram holat
  await loadTgStatus()
  // Bot & system settings yuklash
  await loadSysSettings()
  // Deadline & bildirishnoma settings
  await loadDeadlineSettings()
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
    setLang(profileForm.value.ui_lang)
    profileMsg.value = { ok: true, text: '✅ ' + t('settings.profile_saved') }
    setTimeout(() => { profileMsg.value = null }, 3000)
  } catch (e) {
    profileMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || t('settings.error')) }
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
    pwdMsg.value = { ok: true, text: '✅ ' + t('settings.password_changed') }
    pwdForm.value = { current: '', new1: '', new2: '' }
    setTimeout(() => { pwdMsg.value = null }, 4000)
  } catch (e) {
    pwdMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || t('settings.error')) }
  } finally {
    pwdSaving.value = false
  }
}

onUnmounted(() => { resetTgLink() })

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
    alert(e.response?.data?.detail || t('settings.error'))
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
    setupError.value = t('settings.wrong_code')
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
      ? t('settings.wrong_code') : (e.response?.data?.detail || t('settings.error'))
  } finally {
    disabling.value = false
  }
}

// ── TELEGRAM BOG'LASH ───────────────────────────────────────────
const tgLinked       = ref(false)
const tgChatId       = ref(null)
const tgLinkLoading  = ref(false)
const tgLinkData     = ref(null)   // { link, token, expires_in }
const tgLinkError    = ref('')
const tgLinkCountdown = ref(0)
const tgUnlinking    = ref(false)
const showUnlink     = ref(false)
const linkCopied     = ref(false)

let _tgPollTimer   = null
let _tgCountTimer  = null

async function loadTgStatus() {
  try {
    const { data } = await api.get('/v1/auth/telegram-link/status')
    tgLinked.value  = data.linked
    tgChatId.value  = data.telegram_chat_id
  } catch { /* jim */ }
}

async function generateTgLink() {
  tgLinkLoading.value = true
  tgLinkError.value   = ''
  try {
    const { data } = await api.post('/v1/auth/telegram-link/generate')
    tgLinkData.value     = data
    tgLinkCountdown.value = data.expires_in  // 600s

    // Countdown timer
    _tgCountTimer = setInterval(() => {
      tgLinkCountdown.value--
      if (tgLinkCountdown.value <= 0) resetTgLink()
    }, 1000)

    // Polling — har 3 soniyada bog'lanish holatini tekshirish
    _tgPollTimer = setInterval(async () => {
      const { data: st } = await api.get('/v1/auth/telegram-link/status')
      if (st.linked) {
        tgLinked.value  = true
        tgChatId.value  = st.telegram_chat_id
        resetTgLink()
        showToast('✅ ' + t('settings.tg_linked_success'))
      }
    }, 3000)

  } catch (e) {
    tgLinkError.value = '❌ ' + (e.response?.data?.detail || t('settings.error'))
  } finally {
    tgLinkLoading.value = false
  }
}

function resetTgLink() {
  clearInterval(_tgPollTimer)
  clearInterval(_tgCountTimer)
  _tgPollTimer  = null
  _tgCountTimer = null
  tgLinkData.value     = null
  tgLinkCountdown.value = 0
}

async function unlinkTelegram() {
  tgUnlinking.value = true
  try {
    await api.delete('/v1/auth/telegram-link')
    tgLinked.value   = false
    tgChatId.value   = null
    showUnlink.value = false
    showToast(t('settings.tg_unlinked'))
  } catch (e) {
    showToast('❌ ' + (e.response?.data?.detail || t('settings.error')), false)
  } finally {
    tgUnlinking.value = false
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(tgLinkData.value?.link || '')
    linkCopied.value = true
    setTimeout(() => { linkCopied.value = false }, 2000)
  } catch { /* jim */ }
}

// ── BOT & TIZIM SOZLAMALARI ──────────────────────────────────────
const sysLoading = ref(true)
const sysSaving = ref(false)
const sysMsg = ref(null)
const sysForm = ref({
  company_name: 'Company',
  admin_panel_name: 'IntegrityBot',
  system_language: 'uz',
  timezone: 'Asia/Tashkent',
  bot_admin_group_id: '',
  bot_welcome_message: '',
  bot_working_hours_start: '08:00',
  bot_working_hours_end: '18:00',
  bot_working_days: '1,2,3,4,5',
  bot_languages: 'uz,ru,en',
  bot_outside_hours_message: '',
  poll_chat_id: '',
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
    sysMsg.value = { ok: true, text: '✅ ' + t('settings.settings_saved') }
    setTimeout(() => { sysMsg.value = null }, 3000)
  } catch (e) {
    sysMsg.value = { ok: false, text: '❌ ' + (e.response?.data?.detail || t('settings.error')) }
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
    webhookMsg.value = { ok: true, text: '✅ ' + t('settings.webhook_success') }
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

