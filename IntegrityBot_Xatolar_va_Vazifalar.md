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

### 11. SIEM/Log Forwarding Yo'q

**Daraja:** 📋 Kichik  
**Joylashuv:** `backend/app/core/logging.py` yoki yangi `services/siem.py`  
**Muammo:**

TZ talabi (bo'lim 10):
> *"SIEM/Log management (Splunk/Elastic) — opsional"*

Hozirda loglar faqat Docker container stdout ga yoziladi. Splunk/Elastic/Graylog ga forwarding yo'q.

**Tuzatish:**

**Variant A — Filebeat (eng oson):**
```yaml
# docker-compose.yml ga qo'shish:
filebeat:
  image: docker.elastic.co/beats/filebeat:8.12.0
  volumes:
    - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
  profiles: ["siem"]
```

**Variant B — Structlog + Elastic:**
```python
# core/logging.py
import structlog
import logging

def setup_logging():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )
```

**Taxminiy vaqt:** 1–3 kun

---

### 12. Kubernetes Manifests Yo'q

**Daraja:** 📋 Kichik  
**Joylashuv:** Loyiha ildizi  
**Muammo:**

TZ talabi (bo'lim 5):
> *"Docker + Kubernetes — tavsiya etiladi"*

Hozirda faqat `docker-compose.yml` bor. Kubernetes uchun manifest fayllar yo'q.

**Tuzatish — `k8s/` papkasi tuzilmasi:**

```
k8s/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml          # (External Secrets Operator bilan)
├── deployments/
│   ├── backend.yaml
│   ├── frontend.yaml     # nginx + static
│   └── redis.yaml
├── services/
│   ├── backend-svc.yaml
│   └── redis-svc.yaml
├── ingress/
│   └── nginx-ingress.yaml
├── hpa/
│   └── backend-hpa.yaml  # Horizontal Pod Autoscaler
└── jobs/
    └── db-migration.yaml
```

**Backend deployment namunasi (`k8s/deployments/backend.yaml`):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: integritybot-backend
  namespace: integritybot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    spec:
      containers:
        - name: backend
          image: integritybot/backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: integritybot-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /api/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
```

**Taxminiy vaqt:** 2–3 kun

---

### 13. SSO/LDAP Integratsiyasi Yo'q

**Daraja:** 📋 Kichik  
**Joylashuv:** `backend/app/api/v1/auth.py`, `frontend/src/pages/Login.vue`  
**Muammo:**

TZ talabi (bo'lim 9):
> *"SSO/LDAP integratsiya (mumkin bo'lsa)"*

Admin panel faqat lokal username/parol bilan kiradi. Korporativ Active Directory/LDAP bilan integratsiya yo'q. Katta tashkilotlarda bu muhim — xodimlar alohida parol eslab qolmasligi kerak.

**Tuzatish:**

```python
# services/ldap_auth.py
import ldap3

async def authenticate_ldap(username: str, password: str) -> dict | None:
    """
    Active Directory / OpenLDAP orqali autentifikatsiya.
    """
    if not settings.LDAP_URL:
        return None  # LDAP sozlanmagan

    server = ldap3.Server(settings.LDAP_URL, use_ssl=settings.LDAP_USE_SSL)
    user_dn = f"{username}@{settings.LDAP_DOMAIN}"

    try:
        conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)
        # Foydalanuvchi ma'lumotlarini olish
        conn.search(
            settings.LDAP_BASE_DN,
            f"(sAMAccountName={username})",
            attributes=["displayName", "mail", "memberOf"]
        )
        if conn.entries:
            entry = conn.entries[0]
            return {
                "username": username,
                "email": str(entry.mail),
                "display_name": str(entry.displayName),
                "groups": [str(g) for g in entry.memberOf],
            }
    except ldap3.core.exceptions.LDAPBindError:
        return None  # Noto'g'ri parol
```

**.env.example:**
```env
# LDAP/Active Directory (opsional)
LDAP_URL=ldap://dc.yourcompany.uz
LDAP_DOMAIN=yourcompany.uz
LDAP_BASE_DN=DC=yourcompany,DC=uz
LDAP_USE_SSL=false
```

**Taxminiy vaqt:** 2–4 kun

---

### 14. Pentest va QA Checklist Yo'q

**Daraja:** 📋 Kichik  
**Joylashuv:** `docs/` papkasi, tashqi jarayon  
**Muammo:**

TZ talabi (bo'lim 12):
> *"Xavfsizlik testlari (SSL, auth bypass, injection, file upload checks)"*

TZ talabi (bo'lim 11):
> *"Pentest, code review — ishga tushirishdan oldin o'tkazish"*

Ne pentest o'tkazilgan, ne QA checklist hujjati mavjud.

**Tuzatish:**

**1. QA Checklist hujjati yaratish (`docs/QA_CHECKLIST.md`):**

```markdown
## Ishga tushirishdan oldin tekshiruv ro'yxati

### Bot funksionallik
- [ ] /start buyrug'i ishlaydi
- [ ] Murojaat yuborish (matn) ishlaydi
- [ ] Murojaat yuborish (fayl bilan) ishlaydi
- [ ] Anonim yuborish ishlaydi va IP saqlanmaydi
- [ ] Case ID to'g'ri format: CASE-YYYYMMDD-NNNNN
- [ ] Holat tekshirish token bilan ishlaydi
- [ ] Admin bilan follow-up ishlaydi
- [ ] Rate limiting ishlaydi (5 murojaat/5 daqiqadan ko'p bo'lsa bloklanadi)

### Xavfsizlik
- [ ] Admin panelga parol va 2FA kerak
- [ ] Viewer roli faqat ko'ra oladi, o'zgartira olmaydi
- [ ] .exe fayl yuklash rad etiladi
- [ ] 20MB dan katta fayl rad etiladi
- [ ] SQL injection urinishlari bloklanadi
- [ ] HTTPS ishlaydi (HTTP → HTTPS redirect)
- [ ] CORS faqat ruxsat berilgan domenlarda ishlaydi

### Admin panel
- [ ] Dashboard statistika ko'rinadi
- [ ] Murojaat statusini o'zgartirish ishlaydi
- [ ] PDF/Excel eksport ishlaydi
- [ ] Audit log to'ldirilmoqda
- [ ] Bildirishnomalar Telegram va Email ga ketmoqda
```

**2. Avtomatlashtirilgan xavfsizlik tekshiruvi (OWASP ZAP):**
```bash
# Docker bilan tez skan:
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://yourdomain.uz \
  -r zap_report.html
```

**3. Pentest uchun sohalari:**

| Soha | Tekshirish usuli |
|------|-----------------|
| SQL Injection | sqlmap, qo'lda |
| XSS | Burp Suite, OWASP ZAP |
| Auth bypass | Qo'lda + Burp |
| File upload bypass | Qo'lda |
| JWT zaifliklar | jwt_tool |
| CSRF | Burp Suite |
| Rate limiting | Qo'lda |

**Taxminiy vaqt:** 3–5 kun (pentest tashqi mutaxassis bilan)

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
| 11 | SIEM/Log forwarding yo'q | 📋 Kichik | 1–3 kun |
| 12 | Kubernetes manifests yo'q | 📋 Kichik | 2–3 kun |
| 13 | SSO/LDAP integratsiya yo'q | 📋 Kichik | 2–4 kun |
| 14 | Pentest va QA checklist yo'q | 📋 Kichik | 3–5 kun |
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
