# 🔒 IntegrityBot — Xavfsizlik Tekshiruvi (Security Checklist)

**Loyiha:** IntegrityBot — Anonim Whistleblowing Tizimi  
**Hujjat turi:** Pentest va Xavfsizlik Nazorat Ro'yxati  
**Sana:** 2026-yil 2-mart  
**Standartlar:** OWASP Top 10, ISO 27001, GDPR

---

## 🎯 1. Autentifikatsiya va Avtorizatsiya (OWASP A01, A07)

### Tekshirish usuli: Qo'lda + Burp Suite

| # | Zaiflik | Test | Kutilgan natija | Holat |
|---|---------|------|-----------------|-------|
| 1.1 | Default parol | `admin:Admin@123456` bilan kirish | 401 — ishlamaydi | ⬜ |
| 1.2 | Brute force | 10+ noto'g'ri parol urinish | Rate limit yoki lock | ⬜ |
| 1.3 | Token falsefikatsiya | JWT signature o'zgartirish | 401 | ⬜ |
| 1.4 | Token muddati | Muddati o'tgan token bilan so'rov | 401 | ⬜ |
| 1.5 | Privilege escalation | Viewer token bilan admin endpoint | 403 | ⬜ |
| 1.6 | IDOR | Boshqa foydalanuvchi case ID si | 403 yoki 404 | ⬜ |
| 1.7 | 2FA bypass | 2FA kodi kiritmasdan kirish | 401 + X-2FA-Required | ⬜ |
| 1.8 | Parol sudrab olish | Token decode qilib parol izlash | Parol token da yo'q | ⬜ |

### Avtomatlashtirilgan test buyruqlari:

```bash
# 1. JWT signature tekshirish
TOKEN="eyJhbGc..."
FAKE_TOKEN=$(echo $TOKEN | sed 's/\(.*\)\..*/\1.fakesignature/')
curl -H "Authorization: Bearer $FAKE_TOKEN" http://localhost/api/v1/cases
# Kutilgan: 401

# 2. Privilege escalation
VIEWER_TOKEN="..."
curl -X POST -H "Authorization: Bearer $VIEWER_TOKEN" \
  http://localhost/api/v1/cases/CASE-001/status \
  -d '{"status": "closed"}'
# Kutilgan: 403

# 3. Autentifikatsiyasiz kirish
curl http://localhost/api/v1/cases
# Kutilgan: 401
```

---

## 💉 2. SQL Injection (OWASP A03)

### Tekshirish usuli: sqlmap + qo'lda

| # | Payload | Endpoint | Kutilgan natija | Holat |
|---|---------|----------|-----------------|-------|
| 2.1 | `' OR '1'='1` | `/api/v1/cases?status=` | 422 yoki xavfsiz natija | ⬜ |
| 2.2 | `'; DROP TABLE cases;--` | Barcha input maydonlar | Xato, lekin DB sog' | ⬜ |
| 2.3 | `UNION SELECT` | `/api/v1/cases?search=` | 422 yoki bo'sh natija | ⬜ |
| 2.4 | Blind SQL | Time-based payload | Normal javob vaqti | ⬜ |

```bash
# sqlmap bilan avtomatik test
pip install sqlmap
sqlmap -u "http://localhost/api/v1/cases?status=open" \
  --headers="Authorization: Bearer $ADMIN_TOKEN" \
  --level=3 --risk=2 --batch
# Kutilgan: "no SQL injection vulnerabilities detected"
```

---

## 🕸️ 3. XSS — Cross-Site Scripting (OWASP A03)

| # | Payload | Joylashuv | Kutilgan natija | Holat |
|---|---------|----------|-----------------|-------|
| 3.1 | `<script>alert(1)</script>` | Case izoh | Escape qilingan ko'rinadi | ⬜ |
| 3.2 | `<img src=x onerror=alert(1)>` | Murojaat matni | Escaped | ⬜ |
| 3.3 | `javascript:alert(1)` | URL maydonlar | Bloklangan | ⬜ |
| 3.4 | Stored XSS | DB ga saqlab, qayta ochish | Script ishlamaydi | ⬜ |

```bash
# Content-Security-Policy header tekshirish
curl -I http://localhost/ | grep -i "content-security-policy"
# Kutilgan: CSP header mavjud
```

---

## 📁 4. Fayl Yuklash Xavfsizligi (OWASP A04)

| # | Tekshirish | Test fayl | Kutilgan natija | Holat |
|---|-----------|----------|-----------------|-------|
| 4.1 | .exe yuklash | `malware.exe` | 400 — rad etiladi | ⬜ |
| 4.2 | .php yuklash | `shell.php` | 400 — rad etiladi | ⬜ |
| 4.3 | .js yuklash | `xss.js` | 400 — rad etiladi | ⬜ |
| 4.4 | Double extension | `file.pdf.exe` | 400 — rad etiladi | ⬜ |
| 4.5 | MIME bypass | `.jpg` nomi, `.exe` kontent | 400 — rad etiladi | ⬜ |
| 4.6 | 20MB+ fayl | 21MB fayl | 413 — rad etiladi | ⬜ |
| 4.7 | ZIP bomb | 1MB zip, 1GB ochiladi | 400 yoki limit | ⬜ |
| 4.8 | Path traversal | `../../etc/passwd` nomi | Sanitize qilingan | ⬜ |

```bash
# MIME type bypass test
# .txt kontent bilan .exe kengaytmali fayl
echo "MZ" > fake.exe
curl -F "file=@fake.exe;type=image/jpeg" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost/api/v1/cases/CASE-001/attachments
# Kutilgan: 400
```

---

## 🌐 5. Transport Xavfsizligi (OWASP A02)

| # | Tekshirish | Usul | Kutilgan natija | Holat |
|---|-----------|------|-----------------|-------|
| 5.1 | HTTP redirect | `http://domain.uz` ochish | HTTPS ga redirect | ⬜ |
| 5.2 | TLS versiyasi | `nmap --script ssl-enum-ciphers` | TLS 1.2+ | ⬜ |
| 5.3 | HSTS header | `curl -I` | `Strict-Transport-Security` bor | ⬜ |
| 5.4 | Zaif cipher | SSL Labs test | A yoki A+ baho | ⬜ |

```bash
# SSL/TLS tekshirish
nmap --script ssl-enum-ciphers -p 443 your-domain.uz

# Security headers tekshirish
curl -I https://your-domain.uz | grep -E "X-Frame|X-Content|Strict-Transport|X-XSS"

# Online: https://securityheaders.com
```

---

## 🔑 6. Maxfiy Ma'lumotlar (OWASP A02)

| # | Tekshirish | Usul | Kutilgan natija | Holat |
|---|-----------|------|-----------------|-------|
| 6.1 | `.env` ochiq emas | `curl http://domain.uz/.env` | 404 | ⬜ |
| 6.2 | `docker-compose.yml` ochiq emas | HTTP orqali | 404 | ⬜ |
| 6.3 | API response da parol yo'q | Case response | Shifrlangan/yo'q | ⬜ |
| 6.4 | Log da parol yo'q | Container log | Parol ko'rinmaydi | ⬜ |
| 6.5 | DB da parol hash | DB da tekshirish | bcrypt hash | ⬜ |
| 6.6 | Swagger production da o'chirilgan | `/api/docs` | 404 yoki 403 | ⬜ |

```bash
# Maxfiy fayllar tekshirish
for file in .env .env.local config.py settings.py docker-compose.yml; do
    curl -s -o /dev/null -w "%{http_code} $file\n" https://your-domain.uz/$file
done
# Kutilgan: barcha 404

# Swagger tekshirish (production da o'chirilgan bo'lishi kerak)
curl -o /dev/null -w "%{http_code}" https://your-domain.uz/api/docs
# Kutilgan: 404
```

---

## 🔒 7. CORS va CSRF

| # | Tekshirish | Usul | Kutilgan natija | Holat |
|---|-----------|------|-----------------|-------|
| 7.1 | CORS — ruxsatsiz domen | `Origin: https://evil.com` header | CORS header yo'q | ⬜ |
| 7.2 | CORS — ruxsat berilgan domen | To'g'ri origin | Header qaytadi | ⬜ |
| 7.3 | Preflight | OPTIONS so'rov | To'g'ri javob | ⬜ |

```bash
# CORS tekshirish
curl -H "Origin: https://evil-site.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS https://your-domain.uz/api/v1/cases -v 2>&1 | grep -i "access-control"
# Kutilgan: access-control-allow-origin: https://evil-site.com YO'Q
```

---

## ⚡ 8. Rate Limiting va DoS Himoyasi

| # | Tekshirish | Usul | Kutilgan natija | Holat |
|---|-----------|------|-----------------|-------|
| 8.1 | API rate limiting | 100+ so'rov/daqiqa | 429 Too Many Requests | ⬜ |
| 8.2 | Bot rate limiting | 10+ `/start` | Bloklash xabari | ⬜ |
| 8.3 | Login brute force | 20+ noto'g'ri urinish | 429 yoki lock | ⬜ |
| 8.4 | Katta payload | 100MB JSON body | 413 | ⬜ |

```bash
# Rate limiting tekshirish
for i in $(seq 1 50); do
    curl -s -o /dev/null -w "%{http_code}\n" \
      http://localhost/api/v1/cases \
      -H "Authorization: Bearer $TOKEN"
done
# Kutilgan: bir nechta 429 ko'rinadi
```

---

## 🔍 9. OWASP ZAP Avtomatik Skan

```bash
# Docker bilan OWASP ZAP skan
docker run --rm -t owasp/zap2docker-stable zap-baseline.py \
  -t https://your-domain.uz \
  -r /tmp/zap_report.html \
  -I

# API skan (OpenAPI schema bilan)
docker run --rm -t owasp/zap2docker-stable zap-api-scan.py \
  -t https://your-domain.uz/api/openapi.json \
  -f openapi \
  -r /tmp/zap_api_report.html
```

### ZAP natijalarini baholash:
| Daraja | Maqbul soni | Izoh |
|--------|-------------|------|
| 🔴 High | 0 | Ishga tushirishdan oldin tuzatilsin |
| 🟠 Medium | 0–2 | Kuzatib borilsin |
| 🟡 Low | < 5 | Kelajakda tuzatilsin |
| ℹ️ Info | Cheksiz | Xabar sifatida |

---

## 📊 10. Pentest Xulosasi

**Pentest o'tkazuvchi:** ___________________________  
**Sana:** ___________________________  
**Versiya:** ___________________________  
**Muhit:** ⬜ Staging / ⬜ Production

### Topilgan zaifliklar:

| # | Zaiflik | Daraja | Joylashuv | Holat |
|---|---------|--------|-----------|-------|
| | | | | |

### Umumiy baho:

| Kategoriya | Ball (0-10) |
|-----------|-------------|
| Autentifikatsiya | |
| Avtorizatsiya | |
| Ma'lumotlar himoyasi | |
| Transport xavfsizligi | |
| Fayl xavfsizligi | |
| **O'rtacha** | |

**Xulosa:** ⬜ Ishga tushirishga tayyor / ⬜ Qayta tekshirish kerak

---

## 🛠️ 11. Foydali Toollar

```bash
# 1. nikto — veb server zaiflik skaneri
nikto -h https://your-domain.uz

# 2. sqlmap — SQL injection
sqlmap -u "https://your-domain.uz/api/v1/cases?status=open" \
  --headers="Authorization: Bearer TOKEN" --batch

# 3. nmap — port va SSL skan
nmap -sV --script ssl-cert,ssl-enum-ciphers -p 80,443 your-domain.uz

# 4. OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://your-domain.uz

# 5. JWT xavfsizligi
pip install jwt_tool
python3 jwt_tool.py TOKEN -t https://your-domain.uz/api/v1/cases

# 6. Gobuster — yashirin fayl/endpoint qidirish
gobuster dir -u https://your-domain.uz -w /usr/share/wordlists/dirb/common.txt

# 7. testssl.sh — SSL/TLS tekshirish
docker run --rm -ti drwetter/testssl.sh your-domain.uz:443
```

---

## 📚 Manbalar

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Security Headers Check](https://securityheaders.com/)
- [SSL Labs Test](https://www.ssllabs.com/ssltest/)

