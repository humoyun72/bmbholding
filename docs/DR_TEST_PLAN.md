# 🛡️ IntegrityBot — Disaster Recovery (DR) Test Rejasi

**Versiya:** 1.0  
**Sana:** 2026-yil 2-mart  
**Toifasi:** Ishonchlilik va Tiklanish Rejasi  
**Ko'rib chiqish davri:** Har 6 oyda bir marta

---

## 📋 MUNDARIJA

1. [Maqsad va Qamrov](#1-maqsad-va-qamrov)
2. [RTO / RPO Maqsadlari](#2-rto--rpo-maqsadlari)
3. [Muammo Toifalari](#3-muammo-toifalari)
4. [Scenariy 1: DB Ma'lumotlarini Tiklash](#4-scenariy-1-db-malumotlarini-tiklash)
5. [Scenariy 2: To'liq Server Yo'qolishi](#5-scenariy-2-toliq-server-yoqolishi)
6. [Scenariy 3: WAL Point-in-Time Recovery](#6-scenariy-3-wal-point-in-time-recovery)
7. [Scenariy 4: Fayl Saqlash (S3) Tiklanish](#7-scenariy-4-fayl-saqlash-s3-tiklanish)
8. [Scenariy 5: Shifrlash Kaliti Yo'qolishi](#8-scenariy-5-shifrlash-kaliti-yoqolishi)
9. [DR Test Jadvali](#9-dr-test-jadvali)
10. [Natijalar Qayd Etish Shakli](#10-natijalar-qayd-etish-shakli)
11. [Aloqa Rejasi](#11-aloqa-rejasi)

---

## 1. Maqsad va Qamrov

### 1.1 Maqsad

Bu hujjat IntegrityBot tizimida yuz berishi mumkin bo'lgan nosozliklarni aniqlash, ularni qayta tiklash protseduralarini belgilash va muntazam DR testlar o'tkazish rejasini taqdim etadi.

### 1.2 Qamrov

Quyidagi komponentlar qamrovga olindi:

| Komponent | Muhimlik darajasi | Javobgar |
|-----------|------------------|----------|
| PostgreSQL ma'lumotlar bazasi | 🔴 Kritik | DevOps |
| Backend (FastAPI) | 🔴 Kritik | Backend dev |
| Redis (kesh/queue) | 🟠 Yuqori | DevOps |
| Telegram Bot | 🟠 Yuqori | Backend dev |
| Frontend (Vue.js) | 🟡 O'rta | Frontend dev |
| Fayl saqlash (S3/Local) | 🟡 O'rta | DevOps |
| Monitoring | 🟢 Past | DevOps |

---

## 2. RTO / RPO Maqsadlari

| Ko'rsatkich | Ta'rif | Maqsad |
|-------------|--------|--------|
| **RTO** (Recovery Time Objective) | Tizim qayta ishlashga tayyor bo'lgunga qadar maksimal vaqt | **< 4 soat** |
| **RPO** (Recovery Point Objective) | Yo'qotish mumkin bo'lgan maksimal ma'lumot hajmi | **< 24 soat** (kunlik dump) / **< 5 daqiqa** (WAL bilan) |

---

## 3. Muammo Toifalari

| Toifa | Ta'rif | Misol |
|-------|--------|-------|
| **P1 — Kritik** | Butun tizim ishlamayapti | Server o'chib qoldi, DB buzildi |
| **P2 — Yuqori** | Asosiy funksiya ishlamayapti | Bot xabar qabul qilmayapti |
| **P3 — O'rta** | Qisman nosozlik | Fayllar yuklanmayapti |
| **P4 — Past** | Kichik muammo | Grafana dashboardi ko'rinmayapti |

---

## 4. Scenariy 1: DB Ma'lumotlarini Tiklash

### 4.1 Tavsif

PostgreSQL ma'lumotlar bazasi to'liq yo'qolgan yoki buzilgan.

### 4.2 Muammo Belgilari

```bash
# Quyidagi xatoliklar kuzatiladi:
docker compose logs backend | grep "connection refused"
docker compose logs backend | grep "FATAL"
curl http://localhost/api/health  # {"status": "error"}
```

### 4.3 Tiklash Tartibi

**Qadam 1: Muammoni tasdiqlash**
```bash
docker compose ps db
# Agar status "Exit" bo'lsa — DB to'xtab qolgan
```

**Qadam 2: Container'ni qayta ishga tushirishga urinish**
```bash
docker compose restart db
# 30 soniya kuting, keyin tekshiring:
docker compose ps db
```

**Qadam 3: Agar konteyner ishlamasa — oxirgi dump'dan tiklash**
```bash
# Mavjud dump fayllarini ko'rish
docker compose run --rm db-backup ls /backups/

# Eng yangi dump'ni tanlash
LATEST_DUMP=$(docker compose run --rm db-backup ls /backups/ | sort -r | head -1)
echo "Tiklanadigan dump: $LATEST_DUMP"

# DB'ni to'xtatish va volumeni o'chirish
docker compose stop db
docker volume rm integrity-bot_postgres_data

# DB'ni qayta ishga tushirish (bo'sh)
docker compose up -d db
sleep 10

# Dump'dan tiklash
docker compose run --rm db-backup cat /backups/$LATEST_DUMP | \
  docker compose exec -T db psql -U postgres integritybot

echo "✅ DB tiklash yakunlandi"
```

**Qadam 4: Tekshirish**
```bash
# Backend'ni qayta ishga tushirish
docker compose restart backend

# Health check
curl http://localhost/api/health
# Kutilgan javob: {"status": "ok"}

# Test login
curl -X POST http://localhost/api/v1/auth/token \
  -d "username=admin&password=Admin@123456"
```

**Qadam 5: Ma'lumotlar yaxlitligini tekshirish**
```bash
docker compose exec db psql -U postgres integritybot -c "
SELECT COUNT(*) as cases FROM cases;
SELECT COUNT(*) as users FROM users;
SELECT COUNT(*) as audit_logs FROM audit_logs;
"
```

### 4.4 Kutilgan RTO

| Qadam | Taxminiy vaqt |
|-------|---------------|
| Muammoni aniqlash | 5 daqiqa |
| Container restart | 2 daqiqa |
| Dump tiklash | 10-30 daqiqa |
| Tekshirish | 5 daqiqa |
| **JAMI** | **~45 daqiqa** |

---

## 5. Scenariy 2: To'liq Server Yo'qolishi

### 5.1 Tavsif

Butun server (VM) ishdan chiqdi yoki o'chirildi.

### 5.2 Zarur Narsalar

- [ ] Yangi server (Ubuntu 22.04+ yoki AlmaLinux 9+)
- [ ] Zaxira dump fayllari (S3 yoki tashqi saqlash)
- [ ] `.env` fayli zaxirasi (xavfsiz joyda)
- [ ] Kod repository'si (GitHub/GitLab)

### 5.3 Tiklash Tartibi

**Qadam 1: Yangi serverni tayyorlash**
```bash
# Docker o'rnatish
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# Docker Compose o'rnatish
apt-get install -y docker-compose-plugin

# Git o'rnatish
apt-get install -y git
```

**Qadam 2: Kod'ni klonlash**
```bash
git clone https://github.com/sizning-org/integrity-bot.git
cd integrity-bot
```

**Qadam 3: `.env` faylini tiklash**
```bash
# Zaxiradan ko'chirish (xavfsiz saqlash joyidan)
cp /path/to/backup/.env .env

# Yoki yangi `.env` yaratish (barcha kalitlar kerak!)
# ENCRYPTION_KEY va SECRET_KEY yangilari ma'lumotlarni ochib bo'lmaydi!
```

> ⚠️ **JUDA MUHIM:** `ENCRYPTION_KEY` va `SECRET_KEY` eski qiymatlari aynan saqlanishi kerak! Yangi kalit bilan eski ma'lumotlar o'qilmaydi.

**Qadam 4: DB dump'ni tashqi saqlashdan olish**
```bash
# S3 dan dump olish (agar S3 backup sozlangan bo'lsa)
aws s3 cp s3://your-backup-bucket/latest_dump.sql.gz .
gunzip latest_dump.sql.gz

# Yoki qo'lda ko'chirish (SCP/SFTP orqali)
scp admin@old-server:/backups/latest_dump.sql .
```

**Qadam 5: Tizimni ishga tushirish**
```bash
# Asosiy servislarni ishga tushirish
docker compose up -d db redis
sleep 15

# Dump'ni tiklash
cat latest_dump.sql | docker compose exec -T db psql -U postgres integritybot

# Barcha servislarni ishga tushirish
docker compose up -d
docker compose --profile production up -d
```

**Qadam 6: HTTPS sertifikatini yangilash**
```bash
certbot certonly --webroot -w /var/www/html -d sizning-domen.uz
cp /etc/letsencrypt/live/sizning-domen.uz/fullchain.pem nginx/certs/cert.pem
cp /etc/letsencrypt/live/sizning-domen.uz/privkey.pem nginx/certs/key.pem
docker compose restart nginx
```

**Qadam 7: Telegram Webhook yangilash (agar Webhook rejimida)**
```bash
curl https://api.telegram.org/bot<TOKEN>/setWebhook \
  -d "url=https://yangi-server-ip/api/telegram/webhook&secret_token=<WEBHOOK_SECRET>"
```

**Qadam 8: To'liq tekshirish**
```bash
# Health check
curl https://sizning-domen.uz/api/health

# Murojaatlar mavjudligini tekshirish
curl https://sizning-domen.uz/api/v1/cases \
  -H "Authorization: Bearer <token>"

# Bot ishlashini tekshirish (botga /start yuboring)
```

### 5.4 Kutilgan RTO

| Qadam | Taxminiy vaqt |
|-------|---------------|
| Server tayyorlash | 30 daqiqa |
| O'rnatish va konfiguratsiya | 20 daqiqa |
| DB tiklash | 30 daqiqa |
| Tekshirish | 15 daqiqa |
| **JAMI** | **~1.5 soat** |

---

## 6. Scenariy 3: WAL Point-in-Time Recovery

### 6.1 Tavsif

Ma'lumotlar bazasidagi ma'lumotlar noto'g'ri o'zgartirildi yoki o'chirildi. WAL orqali aniq vaqtga qaytish kerak.

### 6.2 Qachon Ishlatiladi

- Noto'g'ri `DELETE` yoki `UPDATE` buyrugi bajarildi
- Zararli o'zgarish aniqlanmadi (masalan, 1 soat oldin)
- Kunlik dump'dan tiklasganda kerakli ma'lumot yo'qoladi

### 6.3 Tiklash Tartibi

**Qadam 1: WAL arxiv holatini tekshirish**
```bash
docker compose exec db psql -U postgres -c "
SELECT last_archived_wal, last_archived_time,
       last_failed_wal, last_failed_time,
       archived_count, failed_count
FROM pg_stat_archiver;
"
```

**Qadam 2: Tiklanish nuqtasini aniqlash**
```bash
# Audit log'dan noto'g'ri amal vaqtini aniqlang
docker compose exec db psql -U postgres integritybot -c "
SELECT created_at, action, payload, ip_address
FROM audit_logs
WHERE created_at > NOW() - INTERVAL '2 hours'
ORDER BY created_at DESC
LIMIT 20;
"
```

**Qadam 3: Recovery konfiguratsiyasi**
```bash
# DB'ni to'xtatish
docker compose stop db

# recovery.conf yaratish
cat > /tmp/recovery.conf << EOF
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2026-03-02 14:30:00 UTC'
recovery_target_action = 'promote'
EOF

# recovery.conf ni DB konteyneriga ko'chirish
docker compose run --rm -v /tmp/recovery.conf:/tmp/recovery.conf db \
  cp /tmp/recovery.conf /var/lib/postgresql/data/recovery.conf
```

**Qadam 4: DB'ni recovery rejimida ishga tushirish**
```bash
docker compose up -d db

# Recovery progres kuzatish
docker compose logs db -f | grep -i "recovery\|restored\|consistent"
```

**Qadam 5: Tekshirish va tasdiqlash**
```bash
docker compose exec db psql -U postgres integritybot -c "
SELECT COUNT(*) FROM cases;
-- Kutilgan sonni tekshiring
"
```

---

## 7. Scenariy 4: Fayl Saqlash (S3) Tiklanish

### 7.1 Tavsif

S3 bucket yoki local fayl saqlash ishlashdan to'xtadi.

### 7.2 Local → S3 Migratsiya

```bash
# Local fayllarni S3 ga ko'chirish
aws s3 sync /app/uploads s3://sizning-bucket/uploads/ \
  --storage-class STANDARD_IA

# .env ni yangilash
STORAGE_TYPE=s3
AWS_BUCKET_NAME=sizning-bucket
```

### 7.3 S3 → Local Fallback

```bash
# S3 dan barcha fayllarni yuklash
aws s3 sync s3://sizning-bucket/uploads/ /app/uploads/

# .env ni yangilash
STORAGE_TYPE=local

# Backend qayta ishga tushirish
docker compose restart backend
```

### 7.4 S3 Bucket Tiklanish

```bash
# Versioning yoqilgan bo'lsa — o'chirilgan fayllarni tiklash
aws s3api list-object-versions --bucket sizning-bucket \
  --prefix uploads/ --query 'DeleteMarkers[*].[Key,VersionId]' \
  --output text | while read key version; do
    aws s3api delete-object --bucket sizning-bucket \
      --key $key --version-id $version
done
```

---

## 8. Scenariy 5: Shifrlash Kaliti Yo'qolishi

### 8.1 Tavsif

`ENCRYPTION_KEY` yo'qoldi — barcha shifrlangan ma'lumotlar (murojaat mazmuni, izohlar) o'qib bo'lmaydi.

### 8.2 Oldini Olish Choralari

> ⚠️ **Bu eng xavfli scenariy.** Kalit yo'qolsa ma'lumotlarni tiklash MUMKIN EMAS.

**Kalit saqlanishi kerak bo'lgan joylar:**
- [ ] HashiCorp Vault (asosiy)
- [ ] AWS Secrets Manager (zaxira)
- [ ] Xavfsiz parol menejer (IT Admin shaxsiy)
- [ ] Shifrlangan USB (offline zaxira, seyf ichida)
- [ ] Qog'ozda (offline, fizik seyfda)

### 8.3 Kalit Mavjudligini Tekshirish

```bash
# Vault'da mavjudligini tekshirish
vault kv get secret/integritybot | grep ENCRYPTION_KEY

# AWS Secrets Manager'da
aws secretsmanager get-secret-value --secret-id integritybot/prod \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('ENCRYPTION_KEY' in json.loads(d['SecretString']))"
```

### 8.4 Kalit Rotatsiyasi (Ehtiyot Chorasi)

Agar kalit almashtirish kerak bo'lsa (barcha ma'lumotlarni qayta shifrlash kerak):

```bash
# 1. Barcha ma'lumotlarni eski kalit bilan decode qiling
# 2. Yangi ENCRYPTION_KEY yarating
# 3. Barcha ma'lumotlarni yangi kalit bilan encode qiling
# 4. DB'ni yangilang
# Bu jarayon maxsus skript talab qiladi — DevOps bilan mulahoqa qiling
```

---

## 9. DR Test Jadvali

### 9.1 Muntazam Test Jadvali

| Test | Chastota | Javobgar | Oxirgi test | Natija |
|------|----------|----------|-------------|--------|
| DB dump tiklash (Scenariy 1) | Oyda 1 marta | DevOps | — | — |
| To'liq server tiklash (Scenariy 2) | 6 oyda 1 marta | DevOps + Backend | — | — |
| WAL PITR (Scenariy 3) | Oyda 1 marta | DevOps | — | — |
| S3 tiklash (Scenariy 4) | Chorakda 1 marta | DevOps | — | — |
| Kalit zaxira tekshirish (Scenariy 5) | Oyda 1 marta | IT Admin | — | — |

### 9.2 Test Muhiti

DR testlari **alohida test muhitida** o'tkaziladi:
- Production ma'lumotlari ta'sirlanmaydi
- Test serverida dump yuklash va tiklash amalga oshiriladi

### 9.3 Test O'tkazish Tartibi

1. **Oldindan:** Test muhitini tayyorlash, oxirgi dump olish
2. **Test paytida:** Tartiblarga qat'iy amal qilish, vaqtlarni qayd etish
3. **Keyin:** Natijalarni hujjatlashtirish, muammolarni bartaraf etish

---

## 10. Natijalar Qayd Etish Shakli

```
DR TEST NATIJASI
================
Sana: ___________
Test o'tkazuvchi: ___________
Test turi (Scenariy #): ___________
Test muhiti: ___________

BAJARILGAN QADAM | BOShLANISH VAQTI | TUGASH VAQTI | NATIJA
─────────────────────────────────────────────────────────────
1. _____________ | ______________ | ____________ | ✅/❌
2. _____________ | ______________ | ____________ | ✅/❌
3. _____________ | ______________ | ____________ | ✅/❌

JAMI TIKLANISH VAQTI: _______
RTO MAQSADIGA ERISHILDI: Ha / Yo'q
RPO MAQSADIGA ERISHILDI: Ha / Yo'q

MUAMMOLAR:
1. ___________
2. ___________

TAVSIYALAR:
1. ___________
2. ___________

Test tasdiqlovchi imzosi: ___________
```

---

## 11. Aloqa Rejasi

### 11.1 Insident Paytidagi Aloqa Zanjiri

```
Muammo aniqlandi
       ↓
Dastlabki tekshiruv (5 daqiqa)
       ↓
P1/P2 bo'lsa: IT Admin'ni xabardor qiling
       ↓
Tiklanish boshlanadi
       ↓
Jarayon davomida har 30 daqiqada yangilanish
       ↓
Tizim tiklandi → Barcha manfaatdor tomonlarni xabardor qiling
       ↓
Insident hisobotini yozing
```

### 11.2 Aloqa Ma'lumotlari

| Rol | Mas'ul shaxs | Aloqa |
|-----|-------------|-------|
| IT Admin | _____________ | _____________ |
| DevOps | _____________ | _____________ |
| Backend Dev | _____________ | _____________ |
| Compliance Manager | _____________ | _____________ |

### 11.3 Insident Hisoboti Tarkibi

Har qanday P1/P2 insident'dan keyin hisobot yoziladi:

1. **Insident tavsifi** — nima bo'ldi?
2. **Muammo sababi** — nega yuz berdi?
3. **Tiklanish jarayoni** — nima qilindi?
4. **Tiklanish vaqti** — qancha vaqt ketdi?
5. **Yo'qotilgan ma'lumotlar** — nima yo'qoldi (agar bo'lsa)?
6. **Oldini olish choralari** — kelajakda bunday bo'lmasligi uchun nima qilinadi?

---

## ✅ DR Checklist (Qayta Ishga Tushirishdan Oldin)

```
□ Barcha Docker containerlar ishlayapti (docker compose ps)
□ DB ulanish ishlayapti (api/health)
□ Redis ishlayapti (redis-cli ping → PONG)
□ Bot xabar qabul qiladi (/start buyrug'i)
□ Admin panelga kirib bo'ladi
□ Murojaatlar ko'rinadi va shifrlanmagan
□ Fayllar yuklanadi va yuklab olinadi
□ WebSocket ulanadi (dashboard real-time yangilanadi)
□ Audit log yozilmoqda
□ HTTPS sertifikat amal qilmoqda
□ Monitoring (Prometheus/Grafana) ishlayapti
```

---

*Hujjat versiyasi: 1.0 | 2026-yil 2-mart*  
*Keyingi ko'rib chiqish: 2026-yil 2-sentabr*

