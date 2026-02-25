# 🛡️ IntegrityBot — Anonim Whistleblowing Tizimi

**Compliance departamenti uchun to'liq yechim:** Telegram bot + FastAPI backend + Vue.js admin panel

---

## 📦 Tarkib

| Komponent | Texnologiya |
|-----------|-------------|
| Telegram Bot | python-telegram-bot 21 |
| Backend API | FastAPI + SQLAlchemy Async |
| Admin Panel | Vue 3 + Tailwind CSS |
| Ma'lumotlar bazasi | PostgreSQL 16 |
| Kesh | Redis 7 |
| Veb-server | Nginx |
| CI/CD | GitHub Actions |
| Konteynerlashtirish | Docker Compose |

---

## 🚀 Tez ishga tushirish

### 1. Reponi klonlash
```bash
git clone https://github.com/yourorg/integrity-bot.git
cd integrity-bot
```

### 2. `.env` faylini sozlash
```bash
cp .env.example .env
nano .env   # Barcha qiymatlarni to'ldiring
```

**Muhim qiymatlar:**
```bash
# Telegram BotFather dan oling
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUVwxyz

# Shifrlash kalitini yarating:
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
ENCRYPTION_KEY=<yuqoridagi natija>

# Kuchli parollar
POSTGRES_PASSWORD=uzunvamurakkabparol123!
SECRET_KEY=juda_uzun_random_string_kamida_64_ta_belgi_bolsin
```

### 3. Docker Compose bilan ishga tushirish
```bash
docker compose up -d
```

### 4. Webhook ulash
```bash
# Admin panelga kiring: http://localhost/
# Login: admin / Admin@123456
# Sozlamalar sahifasida "Webhook ulash" tugmasini bosing
# YOKI:
curl -X POST http://localhost/api/telegram/set-webhook
```

### 5. **DARHOL QILING** — Default admin parolini o'zgartiring!
Admin panelga kirib, sozlamalarda parolingizni o'zgartiring.

---

## 🔑 Default kirish
| Maydon | Qiymat |
|--------|--------|
| URL | http://localhost |
| Login | `admin` |
| Parol | `Admin@123456` |

> ⚠️ **BIRINCHI KIRISHDA PAROLNI O'ZGARTIRING!**

---

## 🤖 Bot imkoniyatlari (3-variant)

- ✅ **Anonim murojaat** — shaxsiyat saqlanadi
- ✅ **Fayl biriktirish** — rasm va hujjatlar (20 MB gacha)
- ✅ **Kategoriyalar** — Korrupsiya, Firibgarlik, Xavfsizlik va h.k.
- ✅ **Murojaat kuzatuvi** — ID raqam orqali holat tekshirish
- ✅ **Anonim javob** — admin tokenli muloqot
- ✅ **So'rovnomalar** — Telegram native poll

## 🖥️ Admin panel imkoniyatlari

- ✅ **Dashboard** — statistika va grafiklar
- ✅ **Murojaatlar** — ro'yxat, filtrlar, sahifalash
- ✅ **Murojaat kartochkasi** — batafsil ko'rish, tayinlash, holat o'zgartirish
- ✅ **Muloqot** — reporter bilan anonim suhbat
- ✅ **So'rovnomalar** — yaratish, faollashtirish, natijalar
- ✅ **Foydalanuvchilar** — rol boshqaruvi (Admin / Investigator / Viewer)
- ✅ **2FA** — TOTP ikki bosqichli autentifikatsiya
- ✅ **Audit jurnali** — barcha harakatlar loglash

---

## 🔒 Xavfsizlik

- **AES-256-GCM** — barcha matn shifrlangan saqlanadi
- **JWT** — stateless autentifikatsiya
- **TOTP 2FA** — Google Authenticator, Authy
- **Rol asosida kirish** — Viewer / Investigator / Admin
- **Rate limiting** — Nginx darajasida
- **Webhook validatsiya** — Secret-Token tekshiruvi
- **Fayl tekshiruvi** — .exe va zararli fayllar bloklangan

---

## 📁 Loyiha tuzilmasi

```
integrity-bot/
├── backend/
│   ├── app/
│   │   ├── api/v1/       # FastAPI endpoints
│   │   ├── bot/          # Telegram bot handlers
│   │   ├── core/         # Config, DB, Security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Storage, Notifications
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/        # Vue sahifalari
│   │   ├── components/   # Qayta ishlatiladigan komponentlar
│   │   ├── stores/       # Pinia state management
│   │   └── utils/        # API client va helpers
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── .github/workflows/
│   └── ci-cd.yml
├── docker-compose.yml
└── .env.example
```

---

## 🛠️ Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## 📊 GitHub Actions CI/CD

Pipeline bosqichlari:
1. **Test** — Backend pytest, Frontend build
2. **Build** — Docker images → GitHub Container Registry
3. **Deploy** — SSH orqali serverga (**manual approval**)
4. **Notify** — Muvaffaqiyatsizlikda Telegram xabar

GitHub Secrets qo'shish (`Settings → Secrets → Actions`):
```
DEPLOY_HOST=yourdomain.com
DEPLOY_USER=ubuntu
DEPLOY_SSH_KEY=<ssh private key>
TELEGRAM_BOT_TOKEN=...
ADMIN_CHAT_ID=...
```

---

## 📝 API Dokumentatsiya

Development rejimida (`DEBUG=true`):
- Swagger: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
