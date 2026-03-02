# ✅ IntegrityBot — QA va Ishga Tushirish Tekshiruv Ro'yxati

**Loyiha:** IntegrityBot — Anonim Whistleblowing Tizimi  
**Hujjat turi:** QA Checklist (Sifat Nazorati)  
**Sana:** 2026-yil 2-mart  
**Maqsad:** Ishga tushirishdan oldin barcha funksiyalar tekshirilsin

---

## 📋 1. Muhit va Konfiguratsiya

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 1.1 | `.env` faylida barcha `CHANGE_ME` qiymatlar o'zgartirilgan | ⬜ | |
| 1.2 | `ADMIN_DEFAULT_PASSWORD` kuchli parol (16+ belgi) | ⬜ | |
| 1.3 | `ENCRYPTION_KEY` yangi 32-byte kalit (base64) | ⬜ | |
| 1.4 | `SECRET_KEY` kamida 64 belgi | ⬜ | |
| 1.5 | `TELEGRAM_BOT_TOKEN` to'g'ri (BotFather dan) | ⬜ | |
| 1.6 | `WEBHOOK_URL` HTTPS bilan to'g'ri sozlangan | ⬜ | |
| 1.7 | `ALLOWED_ORIGINS` faqat kerakli domenlar | ⬜ | |
| 1.8 | `POSTGRES_PASSWORD` kuchli (16+ belgi) | ⬜ | |
| 1.9 | `DEBUG=false` production da | ⬜ | |
| 1.10 | SSL sertifikati o'rnatilgan va ishlaydi | ⬜ | |

---

## 🤖 2. Telegram Bot Funksionallik

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 2.1 | `/start` buyrug'i — xush kelibsiz xabar ko'rinadi | ⬜ | |
| 2.2 | Kategoriya menyusi to'g'ri ko'rinadi | ⬜ | |
| 2.3 | Matn bilan murojaat yuborish ishlaydi | ⬜ | |
| 2.4 | Rasm bilan murojaat yuborish ishlaydi | ⬜ | |
| 2.5 | PDF fayl bilan murojaat yuborish ishlaydi | ⬜ | |
| 2.6 | Anonim yuborish — IP saqlanmaydi | ⬜ | |
| 2.7 | Case ID to'g'ri format: `CASE-YYYYMMDD-NNNNN` | ⬜ | |
| 2.8 | Murojaat yuborilgandan keyin tasdiqlash xabari keladi | ⬜ | |
| 2.9 | Admin guruhiga bildirishnoma ketadi | ⬜ | |
| 2.10 | Holat tekshirish — token bilan ishlaydi | ⬜ | |
| 2.11 | Admin javobi → foydalanuvchiga yetib boradi | ⬜ | |
| 2.12 | 20MB dan katta fayl — xato xabari ko'rinadi | ⬜ | |
| 2.13 | `.exe` fayl yuklash — rad etiladi | ⬜ | |
| 2.14 | Rate limiting — 5+ murojaat/5 daqiqa bloklaydi | ⬜ | |
| 2.15 | `/menu` — asosiy menyu ko'rinadi | ⬜ | |
| 2.16 | Ortga qaytish tugmalari ishlaydi | ⬜ | |

---

## 🖥️ 3. Admin Panel — Autentifikatsiya

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 3.1 | Login sahifasi ochiladi | ⬜ | |
| 3.2 | To'g'ri login/parol bilan kirish ishlaydi | ⬜ | |
| 3.3 | Noto'g'ri parol — xato xabari ko'rinadi | ⬜ | |
| 3.4 | 2FA sozlash ishlaydi (QR kod) | ⬜ | |
| 3.5 | 2FA bilan kirish ishlaydi | ⬜ | |
| 3.6 | Birinchi kirishda parol o'zgartirish talab qilinadi | ⬜ | |
| 3.7 | Token muddati o'tsa — login sahifasiga redirect | ⬜ | |
| 3.8 | LDAP login ishlaydi (agar sozlangan bo'lsa) | ⬜ | N/A |

---

## 📊 4. Admin Panel — Dashboard

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 4.1 | Dashboard yuklanadi | ⬜ | |
| 4.2 | Statistika raqamlari ko'rinadi (jami, yangi, jarayonda) | ⬜ | |
| 4.3 | Murojaatlar ro'yxati ko'rinadi | ⬜ | |
| 4.4 | Filtrlash ishlaydi (status, kategoriya, sana) | ⬜ | |
| 4.5 | Qidiruv ishlaydi | ⬜ | |
| 4.6 | Murojaat kartochkasiga o'tish ishlaydi | ⬜ | |
| 4.7 | Real-time bildirishnomalar ishlaydi (WebSocket) | ⬜ | |
| 4.8 | Yangi murojaat kelib tushganda ovoz/bildirishnoma | ⬜ | |

---

## 📁 5. Admin Panel — Murojaat Boshqaruvi

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 5.1 | Murojaat tafsilotlari ko'rinadi | ⬜ | |
| 5.2 | Status o'zgartirish ishlaydi | ⬜ | |
| 5.3 | Investigator tayinlash ishlaydi | ⬜ | |
| 5.4 | Izoh yozish ishlaydi | ⬜ | |
| 5.5 | Foydalanuvchi bilan yozishmalar ishlaydi | ⬜ | |
| 5.6 | Ilovalarni ko'rish/yuklab olish ishlaydi | ⬜ | |
| 5.7 | Rasm preview ishlaydi | ⬜ | |
| 5.8 | PDF preview ishlaydi | ⬜ | |
| 5.9 | Excel/PDF hisobot eksport ishlaydi | ⬜ | |
| 5.10 | Jira tiket yaratish ishlaydi (agar sozlangan) | ⬜ | N/A |

---

## 📋 6. Admin Panel — Audit Log

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 6.1 | Audit jurnal sahifasi ochiladi | ⬜ | |
| 6.2 | Login hodisalari qayd etiladi | ⬜ | |
| 6.3 | Status o'zgartirish qayd etiladi | ⬜ | |
| 6.4 | Tayinlash hodisalari qayd etiladi | ⬜ | |
| 6.5 | Filtrlash ishlaydi | ⬜ | |
| 6.6 | Viewer roli audit logni ko'ra olmaydi | ⬜ | |

---

## 🔐 7. Xavfsizlik Tekshiruvi

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 7.1 | HTTP → HTTPS redirect ishlaydi | ⬜ | |
| 7.2 | `X-Frame-Options: DENY` header bor | ⬜ | |
| 7.3 | `X-Content-Type-Options: nosniff` header bor | ⬜ | |
| 7.4 | `Strict-Transport-Security` header bor | ⬜ | |
| 7.5 | `/api/docs` production da o'chirilgan | ⬜ | |
| 7.6 | Viewer roli admin funksiyalarni bajara olmaydi (403) | ⬜ | |
| 7.7 | Autentifikatsiyasiz API so'rovlar 401 qaytaradi | ⬜ | |
| 7.8 | SQL injection urinishlari bloklangan | ⬜ | |
| 7.9 | XSS urinishlari bloklangan | ⬜ | |
| 7.10 | Rate limiting API da ishlaydi | ⬜ | |
| 7.11 | CORS faqat ruxsat berilgan domenlarda | ⬜ | |
| 7.12 | Fayl upload — MIME type tekshiriladi | ⬜ | |
| 7.13 | `.env` fayl veb orqali ochilmaydi | ⬜ | |

---

## 💾 8. Ma'lumotlar va Zaxira

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 8.1 | DB zaxira nusxalari yaratilmoqda (kunlik) | ⬜ | |
| 8.2 | Zaxira nusxasini tiklash tekshirildi | ⬜ | |
| 8.3 | Fayl yuklash ishlaydi (local/S3) | ⬜ | |
| 8.4 | Shifrlangan ma'lumotlar DB da o'qib bo'lmaydi | ⬜ | |
| 8.5 | WAL arxivlash ishlaydi | ⬜ | |
| 8.6 | Ma'lumot saqlash muddati ishlaydi (retention) | ⬜ | |

---

## 📈 9. Monitoring va Ishlash

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 9.1 | `/api/health` — `"status": "ok"` qaytaradi | ⬜ | |
| 9.2 | Prometheus metrikalari `/api/metrics` da ko'rinadi | ⬜ | |
| 9.3 | Grafana dashboard ishlaydi | ⬜ | N/A |
| 9.4 | Log yozuvlari JSON formatda | ⬜ | |
| 9.5 | Xatoliklar logga yozilmoqda | ⬜ | |

---

## 🚀 10. Ishga Tushirishdan Oldin Yakuniy

| # | Tekshirish | Natija | Izoh |
|---|-----------|--------|------|
| 10.1 | Barcha Docker containerlar ishlaydi | ⬜ | |
| 10.2 | Telegram webhook muvaffaqiyatli ulangan | ⬜ | |
| 10.3 | Test murojaat yuborib ko'rildi — to'liq flow | ⬜ | |
| 10.4 | Admin panelga kirish tekshirildi | ⬜ | |
| 10.5 | Email bildirishnoma ishlaydi | ⬜ | |
| 10.6 | SSL sertifikati 30+ kun amal qiladi | ⬜ | |
| 10.7 | Zaxira nusxasi olindi | ⬜ | |
| 10.8 | Monitoring sozlangan | ⬜ | |

---

## 📝 Tekshiruv Natijasi

**Tekshiruvchi:** ___________________________  
**Sana:** ___________________________  
**Versiya:** ___________________________

| Bo'lim | Jami | O'tdi | Muvaffaqiyatsiz | N/A |
|--------|------|-------|-----------------|-----|
| 1. Konfiguratsiya | 10 | | | |
| 2. Telegram Bot | 16 | | | |
| 3. Autentifikatsiya | 8 | | | |
| 4. Dashboard | 8 | | | |
| 5. Murojaat boshqaruvi | 10 | | | |
| 6. Audit Log | 6 | | | |
| 7. Xavfsizlik | 13 | | | |
| 8. Ma'lumotlar | 6 | | | |
| 9. Monitoring | 5 | | | |
| 10. Yakuniy | 8 | | | |
| **JAMI** | **90** | | | |

**Xulosa:** ⬜ Ishga tushirishga tayyor / ⬜ Qayta tekshirish kerak

**Izohlar:**
```
_______________________________________________
_______________________________________________
```

