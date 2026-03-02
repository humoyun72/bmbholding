# 🛡️ IntegrityBot — To'liq Ishga Tushirish Yo'riqnomasi

> **Versiya:** 1.0 | **Yangilangan:** 2026-03-03  
> Bu qo'llanma loyihani birinchi marta o'rnatish va kundalik boshqarishni qamrab oladi.

---

## 📋 Mundarija

1. [Talablar](#1-talablar)
2. [Tezkor Boshlash (5 daqiqa)](#2-tezkor-boshlash)
3. [.env Konfiguratsiyasi](#3-env-konfiguratsiyasi)
4. [Servislarni Boshqarish](#4-servislarni-boshqarish)
5. [Telegram Bot Sozlash](#5-telegram-bot-sozlash)
6. [Admin Panel](#6-admin-panel)
7. [Production Deployment](#7-production-deployment)
8. [Monitoring](#8-monitoring)
9. [Xatoliklarni Bartaraf Etish](#9-xatoliklarni-bartaraf-etish)
10. [Arxitektura](#10-arxitektura)

---

## 1. Talablar

### Minimal
| Komponent | Versiya | Tekshirish |
|-----------|---------|-----------|
| Docker Desktop | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker-compose --version` |
| RAM | 4 GB+ | (dev uchun) |
| Disk | 10 GB+ | — |

### Windows uchun qo'shimcha
```powershell
# PowerShell execution policy (bir marta)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Telegram Bot Token
1. Telegramda [@BotFather](https://t.me/BotFather) ga boring
2. `/newbot` yuboring
3. Bot nomini kiriting (masalan: `IntegrityHotlineBot`)
4. Tokenni oling: `8598776999:AAGx_1TQWvf5l...`

---

## 2. Tezkor Boshlash

```powershell
# 1. Loyihani yuklash
git clone https://github.com/yourorg/integrity-bot.git
cd integrity-bot

# 2. .env faylini sozlash
copy .env.example .env
# .env faylini tahrirlang (quyidagi bo'limga qarang)

# 3. Ishga tushirish (Windows)
.\manage.ps1 up

# 3. Ishga tushirish (Linux/macOS)
chmod +x manage.sh
./manage.sh up
```

**Tayyor!** Biroz kuting (30-60 soniya), keyin:
- 🌐 **Frontend:** http://localhost:5173
- 🔧 **API:** http://localhost:8000
- 📚 **API Docs:** http://localhost:8000/docs

---

## 3. .env Konfiguratsiyasi

`.env` faylini ochib quyidagilarni to'ldiring:

### Majburiy o'zgaruvchilar

```dotenv
# ── DATABASE ──────────────────────────────────────────────────────
POSTGRES_PASSWORD=SizdagiKuchliParol123!
DATABASE_URL=postgresql+asyncpg://postgres:SizdagiKuchliParol123!@db:5432/integritybot

# ── REDIS ─────────────────────────────────────────────────────────
REDIS_PASSWORD=RedisParol456!
REDIS_URL=redis://:RedisParol456!@redis:6379/0

# ── TELEGRAM BOT ──────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=1234567890:AAGx_tokeningiz
BOT_MODE=polling          # Lokal dev uchun polling
ADMIN_CHAT_ID=-100123456789    # Admin guruh ID (quyida izoh)

# ── XAVFSIZLIK ────────────────────────────────────────────────────
SECRET_KEY=kamida-64-belgili-tasodifiy-string-buni-ozgartiring
ENCRYPTION_KEY=base64-encoded-32-byte-key-buni-ham-ozgartiring
ADMIN_DEFAULT_PASSWORD=AdminParol@2026!

# ── MUHIT ─────────────────────────────────────────────────────────
ENVIRONMENT=development
DEBUG=true
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8000
```

### Kalitlar generatsiyasi

```powershell
# SECRET_KEY yaratish
python -c "import secrets; print(secrets.token_hex(64))"

# ENCRYPTION_KEY yaratish
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# WEBHOOK_SECRET yaratish
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Admin guruh ID olish

1. Guruh yarating va botni qo'shing
2. Guruhga `@userinfobot` qo'shing
3. `/start` yuboring — guruh ID ni ko'rasiz (`-100XXXXXXXXXX`)
4. `.env` da `ADMIN_CHAT_ID=-100XXXXXXXXXX` qiling

---

## 4. Servislarni Boshqarish

### Windows PowerShell (manage.ps1)

```powershell
# ── ISHGA TUSHIRISH ────────────────────────────────────────────
.\manage.ps1 up              # Dev rejimda ishga tushirish
.\manage.ps1 up              # Imagelarni build qilib ishga tushirish

# ── TO'XTATISH ────────────────────────────────────────────────
.\manage.ps1 down            # Faqat konteynerlarni to'xtatish
.\manage.ps1 down -Clean     # Ma'lumotlar bilan to'xtatish ⚠️

# ── RESTART ───────────────────────────────────────────────────
.\manage.ps1 restart                      # Barcha servislar
.\manage.ps1 restart -Service backend     # Faqat backend

# ── LOGLAR ────────────────────────────────────────────────────
.\manage.ps1 logs                         # Barcha servislar
.\manage.ps1 logs -Service backend        # Faqat backend
.\manage.ps1 logs -Service frontend       # Faqat frontend
.\manage.ps1 logs -Service db             # Faqat DB

# ── HOLAT ─────────────────────────────────────────────────────
.\manage.ps1 status          # Konteynerlar holati va resurslar

# ── SHELL ─────────────────────────────────────────────────────
.\manage.ps1 shell                        # Backend ichiga kirish
.\manage.ps1 shell -Service db            # DB ichiga kirish

# ── MA'LUMOTLAR BAZASI ────────────────────────────────────────
.\manage.ps1 migrate         # Migratsiyalarni qo'llash
.\manage.ps1 seed            # Boshlang'ich ma'lumotlar

# ── TESTLAR ───────────────────────────────────────────────────
.\manage.ps1 test            # Barcha testlarni ishga tushirish

# ── PRODUCTION ────────────────────────────────────────────────
.\manage.ps1 prod            # Production rejimi
.\manage.ps1 monitoring      # Prometheus + Grafana

# ── TOZALASH ──────────────────────────────────────────────────
.\manage.ps1 build           # Imagelarni rebuild
.\manage.ps1 clean           # BARCHA ma'lumotlarni o'chirish ⚠️
```

### Linux/macOS (manage.sh)

```bash
# Xuddi shu buyruqlar, faqat boshqacha sintaksis:
./manage.sh up
./manage.sh down
./manage.sh down --clean
./manage.sh logs --service backend
./manage.sh shell --service db
./manage.sh restart --service backend
```

### To'g'ridan docker-compose buyruqlari

```powershell
# Asosiy servislar (dev)
docker-compose up -d
docker-compose up -d --build          # Rebuild bilan
docker-compose down
docker-compose down -v                 # Volume bilan

# Alohida servislar
docker-compose up -d backend          # Faqat backend
docker-compose up -d db redis         # Faqat DB + Redis
docker-compose restart backend        # Backend restart

# Production (nginx + clamav + db-backup)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d

# Monitoring
docker-compose --profile monitoring up -d

# SIEM (Filebeat)
docker-compose --profile siem up -d

# Vault (Secrets)
docker-compose --profile vault up -d

# Loglar
docker-compose logs -f backend
docker-compose logs -f --tail=100

# Holat
docker-compose ps
docker stats
```

---

## 5. Telegram Bot Sozlash

### Polling rejimi (lokal dev) — tavsiya qilinadi

```dotenv
BOT_MODE=polling
WEBHOOK_URL=
```
Bot to'g'ridan-to'g'ri Telegramga so'rov yuboradi. Servis ishga tushgach avtomatik ishlaydi.

### Webhook rejimi (production)

```dotenv
BOT_MODE=webhook
WEBHOOK_URL=https://yourdomain.com/api/telegram/webhook
WEBHOOK_SECRET=your_32_char_secret
```

### So'rovnomalar uchun guruh/kanal

1. Guruh/kanal yarating
2. Botni admin qiling
3. ID ni oling va `.env` ga qo'shing:
   ```dotenv
   POLL_CHAT_ID=-1001234567890
   ```

### Bot buyruqlari

```
/start   — Bosh menyu
/help    — Yordam
/lang    — Til tanlash (🇺🇿/🇷🇺/🇬🇧)
/cancel  — Bekor qilish
```

---

## 6. Admin Panel

**URL:** http://localhost:5173  
**Login sahifasi:** http://localhost:5173/login

### Birinchi kirish

1. `.env` da `ADMIN_DEFAULT_PASSWORD` ni ko'ring
2. **Username:** `admin`
3. **Parol:** `.env` dagi `ADMIN_DEFAULT_PASSWORD` qiymati

### Admin panel bo'limlari

| Bo'lim | Tavsif | URL |
|--------|--------|-----|
| Dashboard | Umumiy statistika | `/` |
| Murojaatlar | Barcha cases | `/cases` |
| So'rovnomalar | Poll boshqaruv | `/polls` |
| Foydalanuvchilar | Admin/Investigator | `/users` |
| Audit jurnali | Barcha harakatlar | `/audit` |
| Bildirishnomalar | Real-time notify | Qo'ng'iroq ikonkasi |
| Sozlamalar | Tizim sozlamalari | `/settings` |

### Rollar

| Rol | Huquqlar |
|-----|----------|
| `admin` | To'liq huquq |
| `investigator` | Murojaatlar ko'rish/tahrirlash |
| `viewer` | Faqat ko'rish |

---

## 7. Production Deployment

### SSL Sertifikat sozlash

```bash
# Self-signed (test uchun)
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/certs/privkey.pem \
    -out nginx/certs/fullchain.pem

# Let's Encrypt (production)
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/certs/
```

### .env production sozlamalari

```dotenv
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com
BOT_MODE=webhook
WEBHOOK_URL=https://yourdomain.com/api/telegram/webhook
VITE_API_URL=https://yourdomain.com/api
CLAMAV_ENABLED=true
```

### Production ishga tushirish

```powershell
# Windows
.\manage.ps1 prod

# Linux
./manage.sh prod
```

---

## 8. Monitoring

```powershell
# Monitoring stekini ishga tushirish
.\manage.ps1 monitoring
```

| Servis | URL | Login |
|--------|-----|-------|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / GRAFANA_PASSWORD |

### Muhim metrikalar (Grafana)

- HTTP so'rovlar/saniya
- API javob vaqti (p50, p95, p99)
- Faol WebSocket ulanishlar
- DB ulanish pool holati
- Redis cache hit rate
- Xato darajasi (4xx, 5xx)

---

## 9. Xatoliklarni Bartaraf Etish

### "POSTGRES_PASSWORD required" xatosi

```powershell
# Sabab: .env fayli yo'q yoki to'ldirilmagan
copy .env.example .env
# .env ni tahrirlang va POSTGRES_PASSWORD ni to'ldiring
```

### Frontend build xatosi (CSS)

```
error: The `placeholder-surface-400` class does not exist
```
**Hal qilindi** ✅ — `style.css` yangilangan.

### "502 Bad Gateway"

```powershell
# Backend ishlayaptimi tekshiring
.\manage.ps1 logs -Service backend
.\manage.ps1 status
```

### Bot javob bermayapti

```powershell
# Bot loglarini ko'ring
.\manage.ps1 logs -Service backend
# Polling ishlayaptimi?
docker-compose exec backend python -c "
from app.core.config import settings
print('Token:', settings.TELEGRAM_BOT_TOKEN[:20], '...')
print('Mode:', settings.BOT_MODE)
"
```

### DB ulanish muammosi

```powershell
# DB holati
docker-compose exec db pg_isready -U postgres
# DB ga kirish
.\manage.ps1 shell -Service db
# ichida:
psql -U postgres -d integritybot
\dt  # Jadvallarni ko'rish
```

### Konteyner RAM ko'p yeyapti (WSL muammosi)

```powershell
# RAM yeyotgan konteynerlarni ko'ring
docker stats --no-stream

# Monitoring va SIEM ni o'chiring (lokal devda kerak emas)
docker-compose stop prometheus grafana filebeat

# Faqat keraklilarini ishlatish
docker-compose up -d backend frontend db redis
```

### Migratsiya xatosi

```powershell
# Migratsiya holatini ko'ring
docker-compose exec backend alembic current
docker-compose exec backend alembic history

# Rollback
docker-compose exec backend alembic downgrade -1
```

---

## 10. Arxitektura

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │ Frontend │    │ Backend  │    │   PostgreSQL 16   │  │
│  │ Vue3+Vite│◄──►│FastAPI   │◄──►│   (Primary DB)   │  │
│  │ Port:5173│    │Port:8000 │    │   Port:5432       │  │
│  └──────────┘    │          │    └──────────────────┘  │
│                  │  Python  │    ┌──────────────────┐  │
│  ┌──────────┐    │  3.12    │◄──►│   Redis 7        │  │
│  │ Telegram │◄──►│          │    │   (Cache+Queue)  │  │
│  │   Bot    │    │  Bot +   │    │   Port:6379       │  │
│  └──────────┘    │  API +   │    └──────────────────┘  │
│                  │ WebSocket│                           │
│  [Optional]      └──────────┘                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Nginx   │  │Prometheus│  │ Grafana  │             │
│  │ (prod)   │  │(monitor) │  │(dashbrd) │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

### Servislar profillari

| Profil | Servislar | Ishlatish |
|--------|-----------|-----------|
| *(default)* | backend, frontend, db, redis | `docker-compose up -d` |
| `production` | + nginx, clamav, db-backup | `--profile production` |
| `monitoring` | + prometheus, grafana | `--profile monitoring` |
| `vault` | + hashicorp vault | `--profile vault` |
| `siem` | + filebeat | `--profile siem` |

---

## 🔐 Xavfsizlik Eslatmalar

> ⚠️ **MUHIM:** Quyidagilarni HECH QACHON git ga push qilmang:
> - `.env` fayli
> - `nginx/certs/` sertifikatlar
> - `SECRET_KEY`, `ENCRYPTION_KEY` qiymatlari

```gitignore
# .gitignore da bo'lishi shart:
.env
nginx/certs/*.pem
nginx/certs/*.key
```

---

## 📞 Yordam

- **API Dokumentatsiya:** http://localhost:8000/docs
- **Redoc:** http://localhost:8000/redoc
- **Loyiha hujjatlari:** `docs/` papkasi
- **Xatolar jurnali:** `.\manage.ps1 logs`

