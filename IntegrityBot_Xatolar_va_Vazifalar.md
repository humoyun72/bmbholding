# 🛠️ IntegrityBot — 14 Ta Xato va Vazifalar Ro'yxati

**Loyiha:** IntegrityBot — Anonim Whistleblowing Tizimi  
**Hujjat turi:** Texnik muammolar va tuzatish rejalari  
**Sana:** 2026-yil 2-mart  
**Holat:** Tahlil asosida aniqlangan

---

## 📌 Muhimlik Darajalari

| Daraja | Belgi | Ta'rif |
|--------|-------|--------|
| Kritik | 🚨 | Darhol tuzatilishi shart — production ga chiqishdan oldin |
| O'rta | ⚠️ | Tez orada tuzatilishi kerak — xavfsizlik yoki funksionallik ta'sirlanadi |
| Kichik | 📋 | Kelajakda qo'shilishi mumkin — opsional yoki takomillashtirish |

---

## 🚨 KRITIK XATOLAR (1–4)

---

### 1. Default Admin Paroli Hardcoded

**Daraja:** 🚨 Kritik  
**Joylashuv:** `README.md`, `backend/app/core/seed.py` (yoki shunga o'xshash init fayl)  
**Muammo:**

`README.md` faylida ochiq holda yozilgan:
```
Login: admin
Parol: Admin@123456
```

Bu parol CI/CD pipeline orqali avtomatik production muhitiga ham tushishi mumkin. Agar kimdir reponi topsa — admin panelga kirib oladi.

**Xavf:** Ruxsatsiz kirish, barcha murojaatlar ma'lumotlari ochilib qolishi.

**Tuzatish:**

1. `README.md` dan default parolni olib tashlash — faqat `CHANGE_ME` yozish:
```markdown
# ❌ Noto'g'ri (hozirgi holat):
Login: admin / Parol: Admin@123456

# ✅ To'g'ri:
Login: admin / Parol: [.env faylida ADMIN_DEFAULT_PASSWORD ni sozlang]
```

2. `.env.example` ga qo'shish:
```env
ADMIN_DEFAULT_PASSWORD=CHANGE_ME_strong_password_min_16_chars
```

3. Seed skriptda hardcoded parolni o'chirish:
```python
# ❌ Noto'g'ri:
hashed_password = hash_password("Admin@123456")

# ✅ To'g'ri:
hashed_password = hash_password(settings.ADMIN_DEFAULT_PASSWORD)
```

4. Birinchi kirish uchun majburiy parol o'zgartirish oynasini qo'shish (`force_password_change` flag).

**Taxminiy vaqt:** 2–3 soat

---

### 2. `reporter_ip` Saqlash — Anonimlik Bilan Ziddiyat

**Daraja:** 🚨 Kritik  
**Joylashuv:** `backend/app/models.py` → `Case` modeli, `frontend/src/pages/CaseDetail.vue`  
**Muammo:**

TZ talabi (bo'lim 4.1):
> *"Anonimlik: nельзя saqlash/ko'rsatish IP/telefon otправителя admin panelida"*

Lekin hozirgi kodda:
- `cases` jadvalida `reporter_ip` maydoni mavjud
- Admin panel kartochkasida bu IP **ochiq ko'rinadi**

Bu ISO 37001 va O'zbekiston shaxsiy ma'lumotlar to'g'risidagi qonuniga zid.

**Xavf:** Yuborayotgan shaxsning anonimlik kafolati buziladi → xodimlar xabar yuborishdan qo'rqadi.

**Tuzatish:**

**Variant A — IP ni umuman saqlamaslik (tavsiya etiladi):**
```python
# models.py da reporter_ip maydonini o'chirish yoki:
reporter_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, default=None)
```
Webhook handlerda IP ni DB ga yozmaslik:
```python
# ❌ Noto'g'ri:
case.reporter_ip = request.client.host

# ✅ To'g'ri:
# IP saqlanmaydi — anonimlik kafolati
```

**Variant B — Faqat hash sifatida saqlash (qisman yechim):**
```python
import hashlib
ip_hash = hashlib.sha256(request.client.host.encode()).hexdigest()[:16]
case.reporter_ip_hash = ip_hash  # Asl IP tiklab bo'lmaydi
```

Admin paneldan `reporter_ip` ustunini olib tashlash yoki faqat `admin` roli ko'rishi uchun cheklash.

**Taxminiy vaqt:** 3–4 soat

---

### 3. Telegram Bot — Rate Limiting Yo'q

**Daraja:** 🚨 Kritik  
**Joylashuv:** `backend/app/bot/handlers.py`  
**Muammo:**

Admin panel uchun `slowapi` rate limiting bor, lekin Telegram bot handlerlari uchun hech qanday cheklash yo'q. Bitta foydalanuvchi yoki bot sekundiga yuzlab xabar yubora oladi:

```python
# Hozirgi holat — hech qanday cheklash yo'q:
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Har xil foydalanuvchi cheksiz marta chaqira oladi
    await update.message.reply_text(WELCOME_TEXT, ...)
```

**Xavf:** Backend yuklanib qoladi, DB ga ortiqcha yozuvlar tushadi, servis ishlamay qoladi (DoS).

**Tuzatish:**

Redis yordamida bot-level rate limiting qo'shish:
```python
# bot/middleware/rate_limit.py

import redis.asyncio as aioredis
from app.core.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL)

async def check_rate_limit(user_id: int, action: str, limit: int = 10, window: int = 60) -> bool:
    """
    Bir daqiqa ichida limit marta dan ko'p so'rov qilishni bloklaydi.
    Qaytaradi: True = ruxsat, False = bloklangan
    """
    key = f"rate:{user_id}:{action}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, window)
    return count <= limit

# handlers.py da ishlatish:
async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_rate_limit(user_id, "report", limit=5, window=300):
        await update.message.reply_text("⚠️ Juda ko'p so'rov. 5 daqiqadan so'ng urinib ko'ring.")
        return
    # ... davomi
```

Tavsiya etilgan limitlar:
- `/start` — 30/daqiqa
- Murojaat yuborish — 5/5 daqiqa
- Fayl yuklash — 10/daqiqa
- Holat tekshirish — 20/daqiqa

**Taxminiy vaqt:** 4–6 soat

---

### 4. ClamAV Default O'chirilgan

**Daraja:** 🚨 Kritik  
**Joylashuv:** `.env.example`, `docker-compose.yml`  
**Muammo:**

`.env.example` faylida `CLAMAV_ENABLED` ning default qiymati ko'rsatilmagan yoki `false`. Admin o'rnatishda buni bilmasa — antivirus ishlamaydi, zararli fayllar (.exe nomi .pdf deb nomlanib) tizimga kirishi mumkin.

```env
# .env.example da hozirgi holat:
CLAMAV_ENABLED=   # Bo'sh yoki yo'q
```

**Xavf:** Zararli fayllar tizimga kiradi, server xavf ostida qoladi.

**Tuzatish:**

`.env.example` da default `true` qilish:
```env
# ===== ANTIVIRUS =====
# ClamAV antivirus skanerlash (STRONGLY RECOMMENDED: true)
CLAMAV_ENABLED=true
```

`docker-compose.yml` da ClamAV ni asosiy profile ga qo'shish (production profile emas):
```yaml
# ❌ Hozir faqat --profile production bilan:
profiles: ["production"]

# ✅ To'g'ri — har doim ishga tushsin:
# profiles: [] — yoki umuman olib tashlash
```

`storage.py` da ClamAV o'chiq bo'lsa ogohlantirish:
```python
import logging
if not settings.CLAMAV_ENABLED:
    logging.warning(
        "⚠️ OGOHLANTIRISH: ClamAV o'chirilgan! "
        "Zararli fayllar tekshirilmaydi. Production da yoqing."
    )
```

**Taxminiy vaqt:** 2–3 soat

---

## ⚠️ O'RTA DARAJALI MUAMMOLAR (5–8)

---

### 5. Encryption Key Rotatsiya Skripti Yo'q

**Daraja:** ⚠️ O'rta  
**Joylashuv:** `backend/app/core/security.py`, `DR_TEST_PLAN.md`  
**Muammo:**

DR_TEST_PLAN.md da o'zi yozilgan:
> *"Bu jarayon maxsus skript talab qiladi — DevOps bilan mulahoqa qiling"*

Lekin bu skript yozilmagan. `ENCRYPTION_KEY` o'zgartirish kerak bo'lganda (xavfsizlik audit, kalit kompromis, muntazam rotatsiya) — barcha shifrlangan ma'lumotlarni qayta shifrlash uchun vosita yo'q.

**Xavf:** Kalit almashtirish imkonsiz → eski kalit muammosi kuchayganda tizim xavf ostida.

**Tuzatish — `scripts/rotate_encryption_key.py`:**

```python
"""
Encryption key rotatsiya skripti.
Ishlatish: python rotate_encryption_key.py --old-key OLD_B64_KEY --new-key NEW_B64_KEY
"""
import asyncio
import argparse
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models import Case, CaseComment

def decrypt_with_key(ciphertext_b64: str, key_b64: str) -> str:
    key = base64.b64decode(key_b64)
    data = base64.b64decode(ciphertext_b64)
    nonce, ct = data[:12], data[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()

def encrypt_with_key(plaintext: str, key_b64: str) -> str:
    import os
    key = base64.b64decode(key_b64)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

async def rotate_keys(old_key: str, new_key: str, dry_run: bool = True):
    print(f"{'[DRY RUN] ' if dry_run else ''}Kalit rotatsiyasi boshlanmoqda...")
    async with AsyncSessionLocal() as db:
        # Cases
        cases = (await db.execute(select(Case))).scalars().all()
        for case in cases:
            if case.description:
                plain = decrypt_with_key(case.description, old_key)
                if not dry_run:
                    case.description = encrypt_with_key(plain, new_key)
        # Comments
        comments = (await db.execute(select(CaseComment))).scalars().all()
        for comment in comments:
            if comment.content:
                plain = decrypt_with_key(comment.content, old_key)
                if not dry_run:
                    comment.content = encrypt_with_key(plain, new_key)

        if not dry_run:
            await db.commit()
            print(f"✅ {len(cases)} case, {len(comments)} comment qayta shifrlandi.")
        else:
            print(f"[DRY RUN] {len(cases)} case, {len(comments)} comment topildi. --apply flag bilan ishga tushiring.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-key", required=True)
    parser.add_argument("--new-key", required=True)
    parser.add_argument("--apply", action="store_true", help="Haqiqatda o'zgartirish")
    args = parser.parse_args()
    asyncio.run(rotate_keys(args.old_key, args.new_key, dry_run=not args.apply))
```

**Taxminiy vaqt:** 1 kun

---

### 6. Webhook va Polling Konflikti

**Daraja:** ⚠️ O'rta  
**Joylashuv:** `backend/app/main.py` yoki `backend/app/bot/handlers.py`  
**Muammo:**

`.env.example` da `WEBHOOK_URL` bo'sh qoldirilsa — tizim qaysi rejimda ishlashini aniq bilmaydi. Agar ikkalasi bir vaqtda urinib ko'rsa — Telegram API dan `409 Conflict` xatosi keladi va bot umuman ishlamay qoladi.

```env
# .env.example da muammo:
WEBHOOK_URL=https://yourdomain.com/api/telegram/webhook
# Agar bo'sh qolsa: WEBHOOK_URL=
```

**Xavf:** Bot to'xtab qolishi, xabarlar qabul qilinmasligi.

**Tuzatish:**

`main.py` da aniq rejim tanlash:
```python
from app.core.config import settings

async def start_bot():
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )
    # Handlerlarni qo'shish...
    add_handlers(app)

    if settings.WEBHOOK_URL and settings.WEBHOOK_URL.startswith("https://"):
        # Webhook rejimi
        await app.bot.set_webhook(
            url=f"{settings.WEBHOOK_URL}",
            secret_token=settings.WEBHOOK_SECRET,
        )
        logger.info(f"✅ Bot webhook rejimida: {settings.WEBHOOK_URL}")
        # Polling ni ISHGA TUSHIRMASLIK
    else:
        # Long-polling rejimi (lokal dev uchun)
        await app.bot.delete_webhook()  # Eski webhookni o'chirish
        logger.info("✅ Bot long-polling rejimida (lokal dev)")
        await app.run_polling()
```

`.env.example` ga izoh qo'shish:
```env
# Production: to'liq HTTPS URL kiriting
# Lokal dev: bo'sh qoldiring (polling rejimi)
WEBHOOK_URL=
```

**Taxminiy vaqt:** 4–6 soat

---

### 7. Admin va Foydalanuvchi Izohlari Bir Xil Kalit Bilan Shifrlangan

**Daraja:** ⚠️ O'rta  
**Joylashuv:** `backend/app/core/security.py`, `backend/app/models.py`  
**Muammo:**

Hozirda `Case.description` (foydalanuvchi xabari) va `CaseComment.content` (admin izohlari) bir xil `ENCRYPTION_KEY` bilan shifrlangan. Bu quyidagi muammolarga olib keladi:

1. Kalit rotatsiyasi qilinganda — hamma narsa bir vaqtda o'zgaradi (atomik operatsiya bo'lmasa, qisman holat yuzaga keladi)
2. Kelajakda turli ma'lumot turlari uchun turli kalitlar ishlatib bo'lmaydi
3. Audit maqsadida foydalanuvchi ma'lumotlari va admin izohlari farqlanmaydi

**Tuzatish:**

```python
# config.py ga qo'shish:
CASE_ENCRYPTION_KEY: str = ""      # Foydalanuvchi xabarlari uchun
COMMENT_ENCRYPTION_KEY: str = ""   # Admin izohlari uchun
# Agar bo'sh bo'lsa — ENCRYPTION_KEY dan foydalanish (backwards compatibility)

# security.py:
def encrypt_case_content(text: str) -> str:
    key = settings.CASE_ENCRYPTION_KEY or settings.ENCRYPTION_KEY
    return _encrypt(text, key)

def encrypt_comment_content(text: str) -> str:
    key = settings.COMMENT_ENCRYPTION_KEY or settings.ENCRYPTION_KEY
    return _encrypt(text, key)
```

**.env.example:**
```env
# Asosiy kalit (backwards compatibility)
ENCRYPTION_KEY=CHANGE_ME_base64_encoded_32byte_key

# Ixtiyoriy: alohida kalitlar (xavfsizroq)
# CASE_ENCRYPTION_KEY=
# COMMENT_ENCRYPTION_KEY=
```

**Taxminiy vaqt:** 6–8 soat

---

### 8. Load Testing O'tkazilmagan

**Daraja:** ⚠️ O'rta  
**Joylashuv:** `tests/` papkasi  
**Muammo:**

TZ talabi (bo'lim 4.3):
> *"1000 xabar/oy bilan ishlash imkoniyati"*

TZ qabul qilish mezoni (bo'lim 18):
> *"Yuklanish testi o'tgan (1000 xabar/oy, pik yuklanish)"*

Lekin `tests/` papkasida load test fayli yo'q. PROGRESS_REPORT.md da ham `❌` belgisi bor.

**Xavf:** Haqiqiy yuklanishda tizim ishlamay qolishi — ishga tushirgandan keyin bilinadi.

**Tuzatish — `tests/load_test.py` (Locust bilan):**

```python
"""
Yuklanish testi — Locust
Ishlatish: locust -f tests/load_test.py --host=http://localhost
"""
from locust import HttpUser, task, between
import json

class ComplianceAPIUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Login qilish"""
        resp = self.client.post("/api/v1/auth/token", data={
            "username": "admin",
            "password": "Admin@123456"
        })
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def list_cases(self):
        """Murojaatlar ro'yxatini olish (eng ko'p ishlatiladigan)"""
        self.client.get("/api/v1/cases?page=1&limit=20", headers=self.auth_headers())

    @task(3)
    def get_case_detail(self):
        """Bitta murojaat ma'lumotlari"""
        self.client.get("/api/v1/cases/CASE-20251201-00001", headers=self.auth_headers())

    @task(1)
    def health_check(self):
        self.client.get("/api/health")

    @task(2)
    def dashboard_stats(self):
        self.client.get("/api/v1/cases/stats", headers=self.auth_headers())
```

**Maqsadli ko'rsatkichlar:**
| Metrika | Maqsad |
|---------|--------|
| Murojaatlar/oy | 1,000+ |
| Bir vaqtdagi foydalanuvchilar | 50+ |
| API javob vaqti (o'rtacha) | < 500ms |
| API javob vaqti (95-percentil) | < 2000ms |
| Xato darajasi | < 1% |

**Taxminiy vaqt:** 1–2 kun

---

## 📋 KICHIK MUAMMOLAR (9–14)

---

### 9. Bot Tillari To'liq Emas (i18n Yo'q)

**Daraja:** 📋 Kichik  
**Joylashuv:** `backend/app/bot/handlers.py`  
**Muammo:**

Bot menyusida "Sozlamalar" bo'limi bor va u yerda til tanlash tugmasi mavjud, lekin haqiqiy ko'p-tillilik (UZ/RU/EN) amalga oshirilmagan. Barcha matnlar faqat o'zbekcha.

TZ da talab yo'q, lekin O'zbekistonda rus tilida murojaat qiluvchilar ham bor.

**Tuzatish:**

```python
# bot/i18n/uz.py
MESSAGES = {
    "welcome": "🛡️ *Integrity Hotline Bot*\n\nXavfsiz va anonim tarzda...",
    "choose_category": "📋 *Murojaat kategoriyasini tanlang:*",
    # ...
}

# bot/i18n/ru.py
MESSAGES = {
    "welcome": "🛡️ *Integrity Hotline Bot*\n\nБезопасно и анонимно...",
    "choose_category": "📋 *Выберите категорию обращения:*",
    # ...
}

# handlers.py da:
def get_message(key: str, lang: str = "uz") -> str:
    from bot.i18n import uz, ru, en
    modules = {"uz": uz, "ru": ru, "en": en}
    return modules.get(lang, uz).MESSAGES.get(key, uz.MESSAGES[key])
```

**Taxminiy vaqt:** 2–3 kun

---

### 10. Jira/Redmine Integratsiyasi ✅ BAJARILDI

**Daraja:** 📋 Kichik  
**Joylashuv:** `backend/app/services/jira_integration.py`  
**Holat:** ✅ Amalga oshirildi (2026-03-02)

**Bajarilgan ishlar:**

1. `backend/app/services/jira_integration.py` — Jira Cloud, Jira Server/DC va Redmine uchun to'liq integratsiya servisi
2. `backend/app/models/__init__.py` — `Case` modeliga `jira_ticket_id` va `jira_ticket_url` maydonlari qo'shildi
3. `backend/app/bot/handlers.py` — Yangi case yaratilganda tiket avtomatik ochiladi va ID case ga saqlanadi
4. `backend/app/api/v1/tickets.py` — Yangi API:
   - `GET /api/v1/tickets/status` — Jira/Redmine ulanish holati
   - `POST /api/v1/tickets/{case_id}/create` — Qo'lda tiket yaratish
   - `GET /api/v1/tickets/{case_id}` — Tiket ma'lumotlari
5. `backend/app/api/v1/cases.py` — Case response ga `jira_ticket_id` va `jira_ticket_url` qo'shildi
6. `backend/migrations/add_jira_ticket_fields.sql` — DB migration skripti
7. `frontend/src/pages/CaseDetail.vue` — Sidebar da Jira tiket widget (ko'rish + qo'lda yaratish)
8. `frontend/src/pages/Settings.vue` — Tiket tizimi holati kartasi

**.env sozlash:**
```env
JIRA_URL=https://yourcompany.atlassian.net
JIRA_TOKEN=your_api_token
JIRA_USER_EMAIL=admin@yourcompany.com   # Cloud uchun
JIRA_PROJECT_KEY=COMP
JIRA_ISSUE_TYPE=Task
JIRA_MIN_PRIORITY=critical   # critical | high | all
```

---

### 11. SIEM/Log Forwarding ✅ BAJARILDI

**Daraja:** 📋 Kichik  
**Joylashuv:** `backend/app/services/siem.py`, `backend/app/core/logging_config.py`  
**Holat:** ✅ Amalga oshirildi (2026-03-02)

**Bajarilgan ishlar:**

1. `backend/app/core/logging_config.py` — `structlog` bilan JSON structured logging:
   - `SIEM_LOG_FORMAT=json` (default) → har bir log yozuvi JSON formatida
   - `SIEM_LOG_FORMAT=text` → development uchun oddiy matn
   - `setup_logging()` — main.py da startup da chaqiriladi

2. `backend/requirements.txt` — `structlog==24.4.0` qo'shildi

3. `backend/app/services/siem.py` — To'liq SIEM forwarding servisi:
   - **Splunk HEC** (HTTP Event Collector)
   - **Elasticsearch** (direct REST API, API key yoki Basic auth)
   - **Graylog** (GELF over HTTP)
   - **Webhook** (har qanday HTTP endpoint)
   - `siem_service.send_audit_event()` — audit hodisalar
   - `siem_service.send_security_event()` — login xatolari, brute-force
   - `siem_service.send_case_event()` — yangi murojaatlar

4. `backend/app/core/config.py` — SIEM sozlamalari:
   - `SIEM_ENABLED`, `SIEM_BACKEND`, `SIEM_URL`, `SIEM_TOKEN`, `SIEM_INDEX`

5. `backend/app/api/v1/auth.py` — Login hodisalari SIEM ga yuboriladi:
   - `LOGIN_FAILED`, `LOGIN_2FA_FAILED`, `LOGIN` (muvaffaqiyatli)

6. `backend/app/bot/handlers.py` — Yangi case yaratilganda `CASE_CREATED` SIEM ga

7. `backend/app/main.py` — `setup_logging()` startup da, health endpointda SIEM holati

8. `filebeat.yml` — Filebeat konfiguratsiyasi (Docker → Elastic/Splunk)

9. `docker-compose.yml` — `filebeat` service (`--profile siem`)

10. `.env.example` — SIEM muhit o'zgaruvchilari

11. `frontend/src/pages/Settings.vue` — SIEM holati kartasi

**.env sozlash:**
```env
SIEM_ENABLED=true
SIEM_BACKEND=splunk         # splunk | elastic | graylog | webhook
SIEM_URL=https://splunk.company.uz:8088/services/collector
SIEM_TOKEN=your-hec-token
SIEM_INDEX=integritybot-logs
SIEM_LOG_FORMAT=json
```

**Filebeat bilan (Docker logs → Elastic):**
```bash
docker compose --profile siem up -d
```

---

### 12. Kubernetes Manifests ✅ BAJARILDI

**Daraja:** 📋 Kichik  
**Joylashuv:** `k8s/` papkasi  
**Holat:** ✅ Amalga oshirildi (2026-03-02)

**Bajarilgan ishlar:**

```
k8s/
├── namespace.yaml               — integritybot namespace
├── configmap.yaml               — Maxfiy bo'lmagan sozlamalar
├── secrets.yaml                 — Maxfiy qiymatlar (git da yo'q: .gitignore da)
├── README.md                    — Deploy qo'llanmasi
├── deployments/
│   ├── backend.yaml             — FastAPI (2 replica, zero-downtime, PVC)
│   ├── frontend.yaml            — Vue.js+nginx (2 replica)
│   └── redis.yaml               — Redis 7 + PVC 2Gi
├── services/
│   └── services.yaml            — Backend, Frontend, Redis ClusterIP
├── ingress/
│   └── ingress.yaml             — NGINX Ingress + cert-manager (Let's Encrypt)
├── hpa/
│   └── hpa.yaml                 — HPA: backend 2→10, frontend 2→5
└── jobs/
    └── db-migration.yaml        — DB migration Job (deploy oldidan)
```

**Xususiyatlar:**
- Zero-downtime rolling update
- Pod anti-affinity (podlar turli nodlarda)
- Security context (non-root user, capabilities drop)
- Liveness + Readiness + Startup probes
- Resource limits/requests
- HPA: CPU 70%, Memory 80% da avtomatik scale

---

### 13. SSO/LDAP Integratsiyasi ✅ BAJARILDI

**Daraja:** 📋 Kichik  
**Joylashuv:** `backend/app/services/ldap_auth.py`  
**Holat:** ✅ Amalga oshirildi (2026-03-02)

**Bajarilgan ishlar:**

1. `backend/app/services/ldap_auth.py` — To'liq LDAP/AD servisi:
   - Microsoft Active Directory (AD)
   - OpenLDAP / FreeIPA
   - Azure AD (LDAPS orqali)
   - LDAP injection himoyasi (`_escape_ldap`)
   - `get_role_from_ldap_groups()` — guruh → IntegrityBot roli

2. `backend/app/core/config.py` — LDAP sozlamalari (13 ta yangi parametr):
   `LDAP_ENABLED`, `LDAP_URL`, `LDAP_DOMAIN`, `LDAP_BASE_DN`, `LDAP_BIND_DN` va h.k.

3. `backend/requirements.txt` — `ldap3==2.9.1` qo'shildi

4. `backend/app/api/v1/auth.py` — Login endpointiga LDAP fallback:
   - Lokal foydalanuvchi yo'q → LDAP ga urinib ko'radi
   - LDAP muvaffaqiyatli → DB da foydalanuvchi avtomatik yaratiladi
   - Guruhlardan roli aniqlanadi (admin/investigator/viewer)
   - `GET /api/v1/auth/ldap/status` — LDAP holati (admin uchun)
   - `POST /api/v1/auth/ldap/test` — Test foydalanuvchi bilan tekshirish

5. `.env.example` — LDAP sozlamalari bilan to'ldirildi

6. `frontend/src/pages/Settings.vue` — LDAP/SSO holat kartasi:
   - Holat ko'rsatish (ulangan/sozlanmagan/o'chirilgan)
   - Test forma (username + parol → natija)

**.env sozlash (Active Directory uchun):**
```env
LDAP_ENABLED=true
LDAP_URL=ldap://dc.yourcompany.uz
LDAP_DOMAIN=yourcompany.uz
LDAP_BASE_DN=DC=yourcompany,DC=uz
LDAP_BIND_DN=CN=ldap-reader,OU=ServiceAccounts,DC=yourcompany,DC=uz
LDAP_BIND_PASSWORD=service_account_password
LDAP_GROUP_ADMIN=CN=IntegrityBot-Admins,OU=Groups,DC=yourcompany,DC=uz
LDAP_GROUP_INVESTIGATOR=CN=IntegrityBot-Investigators,OU=Groups,DC=yourcompany,DC=uz
```

**Ishlash tartibi:**
1. Foydalanuvchi login → parol kiritadi
2. DB da topilmasa → LDAP ga urinib ko'riladi
3. LDAP muvaffaqiyatli → DB ga yangi foydalanuvchi yaratiladi (guruhdan roli)
4. Keyingi kirishlarda ham xuddi shu oqim

---

### 14. Pentest va QA Checklist ✅ BAJARILDI

**Daraja:** 📋 Kichik  
**Joylashuv:** `docs/` papkasi  
**Holat:** ✅ Amalga oshirildi (2026-03-02)

**Bajarilgan ishlar:**

1. **`docs/QA_CHECKLIST.md`** — 90 ta tekshiruv bandi (10 bo'lim):
   - Konfiguratsiya (10 ta)
   - Telegram Bot funksionallik (16 ta)
   - Autentifikatsiya (8 ta)
   - Dashboard (8 ta)
   - Murojaat boshqaruvi (10 ta)
   - Audit Log (6 ta)
   - Xavfsizlik (13 ta)
   - Ma'lumotlar va Zaxira (6 ta)
   - Monitoring (5 ta)
   - Yakuniy (8 ta)

2. **`docs/SECURITY_CHECKLIST.md`** — OWASP Top 10 asosida pentest qo'llanmasi:
   - Autentifikatsiya va Avtorizatsiya (A01, A07)
   - SQL Injection (A03) — sqlmap buyruqlari
   - XSS (A03) — payload ro'yxati
   - Fayl Yuklash Xavfsizligi (A04)
   - Transport Xavfsizligi (A02) — TLS, HSTS
   - Maxfiy Ma'lumotlar — `.env`, Swagger, parollar
   - CORS va CSRF
   - Rate Limiting va DoS
   - OWASP ZAP avtomatik skan buyruqlari
   - Foydali toollar: nikto, sqlmap, nmap, gobuster, testssl.sh

3. **`tests/security_test.py`** — Avtomatlashtirilgan xavfsizlik test skripti (Python):
   - Suite 1: Xavfsizlik Headerlari (X-Frame-Options, HSTS, Referrer-Policy)
   - Suite 2: Autentifikatsiya (default parollar, JWT falsifikatsiya, brute force)
   - Suite 3: Maxfiy Fayllar (`.env`, `.git`, Swagger)
   - Suite 4: CORS
   - Suite 5: Fayl Yuklash (`.exe`, `.php`, path traversal, 21MB)
   - Suite 6: Rate Limiting
   - Rangli chiqish (colorama), yakuniy baho

4. **`backend/requirements-load-test.txt`** — `httpx` va `colorama` qo'shildi

**Ishlatish:**
```bash
# O'rnatish
pip install httpx colorama

# Asosiy tekshirish (lokal)
python tests/security_test.py --host http://localhost

# To'liq tekshirish (parol bilan)
python tests/security_test.py --host http://localhost \
  --password your_admin_pass --full

# OWASP ZAP skan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://your-domain.uz -r zap_report.html
```

---

## 📊 Umumiy Xulosa

| # | Muammo | Daraja | Taxminiy vaqt |
|---|--------|--------|---------------|
| 1 | Default admin paroli hardcoded | 🚨 Kritik | 2–3 soat |
| 2 | reporter_ip anonimlikni buzadi | 🚨 Kritik | 3–4 soat |
| 3 | Bot rate limiting yo'q | 🚨 Kritik | 4–6 soat |
| 4 | ClamAV default o'chirilgan | 🚨 Kritik | 2–3 soat |
| 5 | Encryption key rotatsiya skripti yo'q | ⚠️ O'rta | 1 kun |
| 6 | Webhook/Polling konflikti | ⚠️ O'rta | 4–6 soat |
| 7 | Admin/User izohlari bir xil kalit | ⚠️ O'rta | 6–8 soat |
| 8 | Load testing o'tkazilmagan | ⚠️ O'rta | 1–2 kun |
| 9 | Bot i18n (ko'p-tillilik) yo'q | 📋 Kichik | 2–3 kun |
| 10 | Jira/Redmine integratsiya yo'q | 📋 Kichik | ✅ Bajarildi |
| 11 | SIEM/Log forwarding yo'q | 📋 Kichik | ✅ Bajarildi |
| 12 | Kubernetes manifests yo'q | 📋 Kichik | ✅ Bajarildi |
| 13 | SSO/LDAP integratsiya yo'q | 📋 Kichik | ✅ Bajarildi |
| 14 | Pentest va QA checklist yo'q | 📋 Kichik | ✅ Bajarildi |
| | **JAMI** | | **~21–35 ish kuni** |

---

## 🚀 Tavsiya Etilgan Prioritet Rejasi

### Sprint 1 (1 hafta) — Kritik xatolar
1️⃣ Default parol → 2️⃣ IP saqlash → 3️⃣ Rate limiting → 4️⃣ ClamAV default

### Sprint 2 (2 hafta) — O'rta muammolar  
5️⃣ Key rotatsiya → 6️⃣ Webhook fix → 7️⃣ Separate keys → 8️⃣ Load test

### Sprint 3 (3–4 hafta) — Kichik takomillashtirish  
9️⃣ i18n → ✅ Jira → 1️⃣1️⃣ SIEM → 1️⃣2️⃣ K8s → 1️⃣3️⃣ SSO → 1️⃣4️⃣ Pentest

---

*Hujjat tayyorlandi: 2026-yil 2-mart*  
*Keyingi ko'rib chiqish: Sprint 1 yakunida*
