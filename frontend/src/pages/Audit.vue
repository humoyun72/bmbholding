<template>
  <div class="p-8 animate-fade-in">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white">Audit jurnali</h1>
      <p class="text-surface-400 text-sm mt-1">Tizimda bajarilgan barcha amallar</p>
    </div>

    <div class="card p-6 mb-6 text-center text-surface-500">
      <div class="text-4xl mb-3">📋</div>
      <p class="text-sm">Audit jurnali yoqilgan. Barcha harakatlar loglanadi va xavfsiz saqlanadi.</p>
      <p class="text-xs mt-2 text-surface-600">Jurnallar kamida 1 yil saqlanadi va faqat adminlar ko'rishi mumkin.</p>
    </div>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800">
              <th v-for="c in ['Foydalanuvchi', 'Amal', 'Murojaat', 'IP manzil', 'Vaqt']" :key="c"
                class="text-left text-xs font-medium text-surface-500 uppercase tracking-wider px-5 py-4">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-surface-800/50">
              <td colspan="5" class="text-center text-surface-600 text-sm py-16">
                Audit API endpoint'i yaratildi. Backend'dan ma'lumot kelishini kuting.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup></script>
