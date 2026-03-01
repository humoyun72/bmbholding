# 📘 IntegrityBot — Administrator Qo'llanmasi

**Versiya:** 1.0  
**Sana:** 2026-yil 2-mart  
**Maqsad:** Tizim administratorlari uchun to'liq boshqaruv qo'llanmasi

---

## 📋 MUNDARIJA

1. [Tizimga Kirish](#1-tizimga-kirish)
2. [Dashboard](#2-dashboard)
3. [Murojaatlarni Boshqarish](#3-murojaatlarni-boshqarish)
4. [Foydalanuvchilarni Boshqarish](#4-foydalanuvchilarni-boshqarish)
5. [So'rovnomalar Moduli](#5-sorovnomalar-moduli)
6. [Audit Jurnali](#6-audit-jurnali)
7. [Hisobotlar va Eksport](#7-hisobotlar-va-eksport)
8. [Tizim Sozlamalari](#8-tizim-sozlamalari)
9. [Xavfsizlik Sozlamalari](#9-xavfsizlik-sozlamalari)
10. [Monitoring va Zaxira](#10-monitoring-va-zaxira)
11. [Muammolarni Bartaraf Etish](#11-muammolarni-bartaraf-etish)

---

## 1. Tizimga Kirish

### 1.1 Dastlabki Kirish

Tizim birinchi marta o'rnatilganda avtomatik admin yaratiladi:

| Maydon | Qiymat |
|--------|--------|
| Login | `admin` |
| Parol | `Admin@123456` |
| URL | `https://sizning-domen.uz/` |

> ⚠️ **DIQQAT:** Birinchi kirishdan so'ng parolni albatta o'zgartiring!

### 1.2 Login Jarayoni

1. Brauzerda admin panel manziliga o'ting
2. Login va parolni kiriting
3. **"Kirish"** tugmasini bosing
4. Agar 2FA yoqilgan bo'lsa — Authenticator ilovasidan 6 raqamli kodni kiriting

### 1.3 Ikki Bosqichli Autentifikatsiya (2FA)

**Yoqish:**
1. Profil sozlamalariga o'ting (yuqori o'ng burchak → `Sozlamalar`)
2. **"2FA ni yoqish"** tugmasini bosing
3. QR kodni Google Authenticator / Authy ilovasi bilan skanerlang
4. Ilova ko'rsatgan 6 raqamli kodni tasdiqlash maydoniga kiriting
5. **"Tasdiqlash"** tugmasini bosing

> ✅ 2FA yoqilgandan so'ng har safar login qilganda kod so'raladi.

**O'chirish (faqat shoshilinch holatda):**
```bash
# Server'ga SSH orqali kiring
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.models import User
from sqlalchemy import select, update

async def disable_2fa(username):
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User).where(User.username == username)
            .values(totp_enabled=False, totp_secret=None)
        )
        await db.commit()
        print(f'{username} uchun 2FA o\\'chirildi')

asyncio.run(disable_2fa('admin'))
"
```

---

## 2. Dashboard

### 2.1 Ko'rsatkichlar

Dashboard quyidagi real-time statistikani ko'rsatadi:

| Ko'rsatkich | Tavsif |
|-------------|--------|
| **Jami murojaatlar** | Barcha vaqt uchun |
| **Yangi** | Hali ko'rib chiqilmagan |
| **Ko'rib chiqilmoqda** | Jarayonda |
| **Yakunlangan** | Yopilgan (completed) |
| **Oylik trend** | Oxirgi 6 oy grafigi |
| **Kategoriya bo'yicha** | Doira diagrammasi |

### 2.2 Real-time Yangilanish

Dashboard WebSocket orqali avtomatik yangilanadi — sahifani yangilash shart emas.

Agar yangilanish to'xtatilsa: brauzer konsolida `WebSocket` ulanish xatosini tekshiring.

---

## 3. Murojaatlarni Boshqarish

### 3.1 Murojaatlar Ro'yxati

**Filtrlar:**
- **Holat:** Yangi / Ko'rib chiqilmoqda / Ma'lumot kerak / Yakunlandi / Rad etildi / Arxivlandi
- **Kategoriya:** Korrupsiya / Manfaatlar to'qnashuvi / Firibgarlik / Xavfsizlik / Kamsitish / Tender / Boshqa
- **Ustuvorlik:** Kritik / Yuqori / O'rta / Past
- **Tayinlangan:** Xodim bo'yicha filtrlash
- **Qidiruv:** Murojaat ID bo'yicha

### 3.2 Murojaat Statuslari

```
YANGI → KO'RIB CHIQILMOQDA → YAKUNLANDI
  ↓              ↓                ↑
  └──────► MA'LUMOT KERAK ────────┘
                 ↓
            RAD ETILDI
                ↓
         ARXIVLANDI (3 yildan keyin avtomatik)
```

| Status | Rang | Tavsif |
|--------|------|--------|
| 🔵 Yangi | Ko'k | Hali hech kim ko'rmagan |
| 🟡 Ko'rib chiqilmoqda | Sariq | Xodim ishlayapti |
| 🟠 Ma'lumot kerak | To'q sariq | Qo'shimcha ma'lumot so'ralgan |
| 🟢 Yakunlandi | Yashil | Muvaffaqiyatli yopilgan |
| 🔴 Rad etildi | Qizil | Asossiz topilgan |
| ⚫ Arxivlandi | Kulrang | 3 yil o'tgan, arxivda |

### 3.3 Murojaat Kartochkasi

Murojaat kartochkasida quyidagilar mavjud:

**Chap panel (2/3):**
- Murojaat mazmuni (shifrlangan, faqat sizga ko'rinadi)
- Biriktirilgan fayllar (inline preview + yuklab olish)
- Muloqot tarix (admin ↔ reporter)

**O'ng panel (1/3):**
- Kategoriya, ustuvorlik, holat
- Muddat (due_at)
- Reporter IP (agar mavjud)
- Tayinlash (xodim tanlash)
- Tezkor amallar

### 3.4 Javob Yuborish

1. Murojaat kartochkasini oching
2. Pastdagi matn maydoniga javob yozing
3. **"Ichki eslatma"** checkboxini belgilang — agar faqat adminlar ko'rishi kerak bo'lsa
4. Yuborish tugmasini bosing

> 📬 Oddiy javob avtomatik ravishda Telegram orqali murojaat yuborguvchiga yuboriladi.  
> 🔒 Ichki eslatmalar faqat admin panelda ko'rinadi.

### 3.5 Fayl Preview

| Format | Ko'rish usuli |
|--------|---------------|
| Rasm (JPG, PNG, GIF, WebP) | Inline + modal zoom |
| PDF | iframe viewer |
| Video (MP4, AVI, MOV) | HTML5 player |
| Audio (MP3, WAV, OGG) | HTML5 player |
| Boshqalar | Faqat yuklab olish |

### 3.6 Eksport

- **PDF eksport:** Murojaat kartochkasidan `📄 Eksport` tugmasi
- **Excel/CSV hisobot:** `Hisobotlar` menyusidan

---

## 4. Foydalanuvchilarni Boshqarish

### 4.1 Rollar

| Rol | Huquqlar |
|-----|----------|
| **Viewer** | Faqat ko'rish |
| **Investigator** | Ko'rish + javob berish + status o'zgartirish |
| **Admin** | Barcha huquqlar + foydalanuvchi boshqaruvi |

### 4.2 Yangi Foydalanuvchi Qo'shish

1. Chap menyu → `Foydalanuvchilar`
2. **"+ Yangi foydalanuvchi"** tugmasi
3. Maydonlarni to'ldiring:
   - Ism familiya
   - Login (username)
   - Email
   - Rol
   - Parol (kamida 8 belgi, katta harf, raqam)
4. **"Saqlash"** tugmasini bosing

### 4.3 Foydalanuvchini O'chirish / Bloklash

- **Bloklash:** Foydalanuvchi profilida `Faol` kalitini o'chiring
- **O'chirish:** Foydalanuvchi profilida `O'chirish` tugmasini bosing

> ⚠️ O'chirilgan foydalanuvchining audit loglari saqlanib qoladi.

---

## 5. So'rovnomalar Moduli

### 5.1 So'rovnoma Yaratish

1. Chap menyu → `So'rovnomalar`
2. **"+ Yangi so'rovnoma"** tugmasi
3. Sarlavha va tavsif kiriting
4. Savollar qo'shing (har bir savol uchun javob variantlari)
5. **"Draft sifatida saqlash"** yoki **"Faollashtirish"**

### 5.2 Telegram Kanalga Yuborish

So'rovnoma `active` holatga o'tkazilganda avtomatik ravishda `.env` faylida ko'rsatilgan `POLL_CHAT_ID` (guruh yoki kanal) ga yuboriladi.

```env
POLL_CHAT_ID=-1001234567890  # Guruh ID (minus belgisi bilan)
```

> 📊 Ovoz berilganda real-time natijalar admin panelda ko'rinadi.

### 5.3 So'rovnomani Yopish

So'rovnoma kartochkasidan `Yopish` tugmasi → natijalar arxivlanadi.

---

## 6. Audit Jurnali

### 6.1 Qayd Etiladigan Harakatlar

| Harakat | Tavsif |
|---------|--------|
| `login` | Tizimga kirish |
| `logout` | Tizimdan chiqish |
| `case_view` | Murojaat ko'rildi |
| `case_update` | Status o'zgartirildi |
| `case_assign` | Tayinlash o'zgartirildi |
| `case_comment` | Izoh qo'shildi |
| `case_export` | PDF eksport qilindi |
| `attachment_download` | Fayl yuklab olindi |
| `user_create` | Yangi foydalanuvchi yaratildi |
| `user_update` | Foydalanuvchi ma'lumotlari o'zgartirildi |
| `survey_create` | So'rovnoma yaratildi |

### 6.2 Filtrlar

- **Harakat turi** bo'yicha
- **Foydalanuvchi** bo'yicha
- **Sana oralig'i** bo'yicha

### 6.3 Data Retention (Ma'lumotlarni Saqlash Muddati)

| Ma'lumot turi | Arxivlash muddati | O'chirish muddati |
|---------------|-------------------|-------------------|
| Yopilgan murojaatlar | 3 yil | 5 yil |
| Audit loglari (case'ga bog'liq emas) | — | 3 yil |
| Bildirishnomalar | — | 1 yil |

**Qo'lda ishga tushirish:**
```bash
# API orqali
curl -X POST https://sizning-domen.uz/api/v1/audit/retention/run \
  -H "Authorization: Bearer <admin_token>"

# Retention statistikasini ko'rish
curl https://sizning-domen.uz/api/v1/audit/retention/stats \
  -H "Authorization: Bearer <admin_token>"
```

---

## 7. Hisobotlar va Eksport

### 7.1 Oylik Hisobot (Excel)

1. `Hisobotlar` menyusiga o'ting
2. Oy va yilni tanlang
3. **"Excel yuklash"** tugmasi

### 7.2 Choraklik PDF Hisobot

1. `Hisobotlar` menyusiga o'ting
2. Chorakni tanlang
3. **"PDF yuklash"** tugmasi

### 7.3 Murojaat PDF Eksporti

Murojaat kartochkasidan → `📄 Eksport` → PDF yuklanadi.

---

## 8. Tizim Sozlamalari

### 8.1 `.env` Fayl Asosiy O'zgaruvchilari

```env
# Ilova
APP_NAME=IntegrityBot
COMPANY_NAME=Sizning Kompaniyangiz

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/integritybot

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...
ADMIN_CHAT_ID=-1001234567890    # Admin guruh ID
POLL_CHAT_ID=-1001234567891     # So'rovnomalar uchun guruh/kanal ID

# Xavfsizlik
SECRET_KEY=kamida_32_belgidan_iborat_maxfiy_kalit
ENCRYPTION_KEY=base64_encoded_32_bytes_key

# Fayl saqlash
STORAGE_TYPE=local              # local | s3
MAX_FILE_SIZE_MB=20

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=admin@company.uz
SMTP_PASSWORD=smtp_parol
```

### 8.2 Encryption Key Yaratish

```bash
# Python bilan
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# OpenSSL bilan
openssl rand -base64 32
```

### 8.3 S3 Storage Sozlash

```env
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_BUCKET_NAME=integritybot-uploads
AWS_REGION=us-east-1

# MinIO (o'z serveringizda) uchun:
S3_ENDPOINT_URL=http://minio:9000

# Yandex Cloud uchun:
S3_ENDPOINT_URL=https://storage.yandexcloud.net
AWS_REGION=ru-central1
```

---

## 9. Xavfsizlik Sozlamalari

### 9.1 HTTPS Sertifikat (Let's Encrypt)

```bash
# Certbot bilan
certbot certonly --webroot -w /var/www/html -d sizning-domen.uz

# Sertifikatni nginx ga ko'chirish
cp /etc/letsencrypt/live/sizning-domen.uz/fullchain.pem nginx/certs/cert.pem
cp /etc/letsencrypt/live/sizning-domen.uz/privkey.pem nginx/certs/key.pem

# Containerlarni qayta ishga tushirish
docker compose --profile production restart nginx
```

### 9.2 ClamAV Antivirus

```env
# .env faylida yoqish
CLAMAV_ENABLED=true
CLAMAV_HOST=clamav
CLAMAV_PORT=3310
```

```bash
# Production profileda ClamAV ishga tushirish
docker compose --profile production up -d clamav

# ClamAV bazasini yangilash
docker compose exec clamav freshclam
```

### 9.3 Vault (Maxfiy Kalitlar Boshqaruvi)

```bash
# Vault'ni ishga tushirish
docker compose --profile vault up -d vault

# Vault'ni sozlash
sh scripts/vault_setup.sh

# .env da ulash
SECRETS_BACKEND=vault
VAULT_ADDR=http://vault:8200
VAULT_ROLE_ID=your_role_id
VAULT_SECRET_ID=your_secret_id
```

### 9.4 Rate Limiting

Tizimda `slowapi` orqali himoya mavjud:
- API so'rovlari: 100 ta/daqiqa (IP bo'yicha)
- Login urinishlari: 5 ta/daqiqa

---

## 10. Monitoring va Zaxira

### 10.1 Monitoring Ishga Tushirish

```bash
docker compose --profile monitoring up -d

# Grafana: http://sizning-domen.uz/grafana
# Default login: admin / admin123
# Prometheus: http://sizning-domen.uz/metrics (ichki)
```

### 10.2 Grafana Dashboardlar

Tizimda quyidagi dashboardlar oldindan sozlangan:
- **Umumiy metrikalar** — so'rovlar soni, latency, xatoliklar
- **DB ko'rsatkichlari** — ulanishlar, so'rovlar
- **Bot aktivligi** — yangi murojaatlar dinamikasi

### 10.3 Health Check

```bash
# Tizim holati
curl https://sizning-domen.uz/api/health

# Javob namunasi:
{
  "status": "ok",
  "version": "1.0.0",
  "storage": {"type": "local", "status": "ok"}
}
```

### 10.4 Zaxira Nusxalar

**Avtomatik (Production):**
- Kunlik: 7 kunlik nusxa saqlanadi
- Haftalik: 4 haftalik nusxa
- Oylik: 6 oylik nusxa
- Joylashuv: `db_backups` Docker volumeda

```bash
# Qo'lda zaxira olish
docker compose exec db pg_dump -U postgres integritybot > backup_$(date +%Y%m%d).sql

# Zaxiradan tiklash
cat backup_20260302.sql | docker compose exec -T db psql -U postgres integritybot
```

### 10.5 WAL Arxivlash (Point-in-Time Recovery)

WAL fayllari `wal_archive` Docker volumeda saqlanadi.

```bash
# WAL arxiv holatini tekshirish
docker compose exec db psql -U postgres -c "SELECT * FROM pg_stat_archiver;"

# Ma'lum vaqtga tiklash (server'da)
# pg_restore_command: restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
```

### 10.6 Containerlarni Boshqarish

```bash
# Barcha servislar holati
docker compose ps

# Loglarni ko'rish
docker compose logs backend --tail=100 -f
docker compose logs db --tail=50

# Container'ni qayta ishga tushirish
docker compose restart backend

# To'liq to'xtatish
docker compose down

# Production bilan ishga tushirish
docker compose --profile production up -d
```

---

## 11. Muammolarni Bartaraf Etish

### 11.1 Tez-tez Uchraydigan Muammolar

**Login imkoni yo'q (401 xato):**
```bash
# Token muddati o'tgan bo'lishi mumkin — qayta login qiling
# 2FA muammo bo'lsa — server'da 2FA o'chiring (1.3 bo'limga qarang)
```

**Bot xabar qabul qilmayapti:**
```bash
# Bot loglarini tekshiring
docker compose logs backend | grep -i "telegram\|bot\|polling"

# Bot tokenini tekshiring
curl https://api.telegram.org/bot<TOKEN>/getMe
```

**DB ulanmayapti:**
```bash
# DB container holati
docker compose ps db

# DB loglar
docker compose logs db --tail=50

# Ulanishni tekshirish
docker compose exec backend python -c "
import asyncio
from app.core.database import engine
async def test(): 
    async with engine.connect() as c: print('DB OK')
asyncio.run(test())
"
```

**Fayl yuklab bo'lmayapti (S3):**
```bash
# S3 ulanishini tekshirish
curl https://sizning-domen.uz/api/health
# storage.status: "ok" bo'lishi kerak

# S3 credentials'ni tekshirish
docker compose exec backend env | grep AWS
```

**WebSocket ulanmayapti:**
```bash
# Redis ishlab turganligini tekshirish
docker compose ps redis
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} ping
# Javob: PONG
```

**"502 Bad Gateway" xatosi:**
```bash
# Backend ishlab turganligini tekshirish
docker compose ps backend
docker compose logs backend --tail=20

# nginx konfiguratsiyasini tekshirish
docker compose exec nginx nginx -t
```

### 11.2 Parolni Tiklash

```bash
docker compose exec backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import User
from sqlalchemy import select, update

async def reset_password(username, new_password):
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User).where(User.username == username)
            .values(hashed_password=hash_password(new_password))
        )
        await db.commit()
        print(f'{username} paroli yangilandi')

asyncio.run(reset_password('admin', 'YangiParol@123'))
"
```

### 11.3 Log Darajasini O'zgartirish

```env
# .env faylida
DEBUG=true   # Batafsil loglar
```

```bash
docker compose restart backend
```

---

## 📞 Texnik Yordam

Muammo hal bo'lmasa:
1. `docker compose logs` natijasini saqlang
2. `/api/health` endpoint javobini saqlang
3. Murojaat kartochkasi URL'ini belgilang
4. Texnik qo'llab-quvvatlash guruhiga yuboring

---

*Hujjat versiyasi: 1.0 | 2026-yil 2-mart*

