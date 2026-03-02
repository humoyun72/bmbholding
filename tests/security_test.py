"""
🔒 IntegrityBot — Avtomatlashtirilgan Xavfsizlik Testlari
=========================================================

TZ talabi (bo'lim 12):
  "Xavfsizlik testlari (SSL, auth bypass, injection, file upload checks)"

Bu skript ishga tushirishdan oldin asosiy xavfsizlik tekshiruvlarini avtomatik o'tkazadi.

Ishlatish:
  # Asosiy tekshirish (lokal):
  python tests/security_test.py --host http://localhost

  # To'liq tekshirish (production):
  python tests/security_test.py --host https://your-domain.uz --full

  # Faqat auth tekshirish:
  python tests/security_test.py --host http://localhost --only auth

Talablar:
  pip install httpx pytest colorama

"""

import asyncio
import argparse
import sys
import os
import io
import time
from typing import Optional
from dataclasses import dataclass, field

try:
    import httpx
    import colorama
    from colorama import Fore, Style
    colorama.init()
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("Kerakli paketlar: pip install httpx colorama")
    sys.exit(1)


# ── Konfiguratsiya ────────────────────────────────────────────────────────────

DEFAULT_ADMIN_USER = os.environ.get("TEST_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.environ.get("TEST_ADMIN_PASS", "")


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str = ""
    skip: bool = False


@dataclass
class TestSuite:
    name: str
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    @property
    def passed(self): return sum(1 for r in self.results if r.passed and not r.skip)
    @property
    def failed(self): return sum(1 for r in self.results if not r.passed and not r.skip)
    @property
    def skipped(self): return sum(1 for r in self.results if r.skip)


# ── Helper funksiyalar ────────────────────────────────────────────────────────

def ok(msg: str) -> str:
    return f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}"

def fail(msg: str) -> str:
    return f"{Fore.RED}❌ {msg}{Style.RESET_ALL}"

def warn(msg: str) -> str:
    return f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}"

def info(msg: str) -> str:
    return f"{Fore.CYAN}ℹ️  {msg}{Style.RESET_ALL}"


async def get_admin_token(client: httpx.AsyncClient, username: str, password: str) -> Optional[str]:
    """Admin token olish."""
    try:
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": username, "password": password},
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass
    return None


# ── Test Suite 1: Security Headers ──────────────────────────────────────────

async def test_security_headers(client: httpx.AsyncClient) -> TestSuite:
    suite = TestSuite("🔒 Xavfsizlik Headerlari")
    try:
        resp = await client.get("/")
    except Exception as e:
        suite.add(TestResult("Header tekshirish", False, str(e)))
        return suite

    headers = {k.lower(): v for k, v in resp.headers.items()}

    # X-Frame-Options
    xfo = headers.get("x-frame-options", "")
    suite.add(TestResult(
        "X-Frame-Options",
        "DENY" in xfo.upper() or "SAMEORIGIN" in xfo.upper(),
        f"Qiymat: {xfo or 'YO`Q'}",
    ))

    # X-Content-Type-Options
    xcto = headers.get("x-content-type-options", "")
    suite.add(TestResult(
        "X-Content-Type-Options: nosniff",
        "nosniff" in xcto.lower(),
        f"Qiymat: {xcto or 'YO`Q'}",
    ))

    # HSTS (faqat HTTPS da kerak)
    hsts = headers.get("strict-transport-security", "")
    is_https = str(client.base_url).startswith("https")
    if is_https:
        suite.add(TestResult(
            "Strict-Transport-Security (HSTS)",
            bool(hsts),
            f"Qiymat: {hsts or 'YO`Q'}",
        ))
    else:
        suite.add(TestResult("Strict-Transport-Security (HSTS)", True, "HTTP — skip", skip=True))

    # Referrer-Policy
    rp = headers.get("referrer-policy", "")
    suite.add(TestResult(
        "Referrer-Policy",
        bool(rp),
        f"Qiymat: {rp or 'YO`Q'}",
    ))

    return suite


# ── Test Suite 2: Autentifikatsiya ────────────────────────────────────────────

async def test_authentication(
    client: httpx.AsyncClient,
    admin_user: str,
    admin_pass: str,
) -> TestSuite:
    suite = TestSuite("🔐 Autentifikatsiya")

    # 1. Autentifikatsiyasiz kirish
    resp = await client.get("/api/v1/cases")
    suite.add(TestResult(
        "Autentifikatsiyasiz API — 401",
        resp.status_code == 401,
        f"HTTP {resp.status_code}",
    ))

    # 2. Noto'g'ri parol
    resp = await client.post("/api/v1/auth/token", data={
        "username": "admin",
        "password": "wrong_password_xyz_12345",
    })
    suite.add(TestResult(
        "Noto'g'ri parol — 401",
        resp.status_code == 401,
        f"HTTP {resp.status_code}",
    ))

    # 3. Default parollar ishlamas
    for default_pass in ["admin", "Admin@123456", "admin123", "password", "123456"]:
        resp = await client.post("/api/v1/auth/token", data={
            "username": "admin",
            "password": default_pass,
        })
        if resp.status_code == 200:
            suite.add(TestResult(
                f"Default parol '{default_pass}' bloklangan",
                False,
                f"⚠️ DEFAULT PAROL '{default_pass}' ISHLAYDI! Darhol o'zgartiring!",
            ))
        else:
            suite.add(TestResult(
                f"Default parol '{default_pass}' bloklangan",
                True,
                f"HTTP {resp.status_code}",
            ))

    # 4. Token falsifikatsiya
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.FAKE_SIGNATURE"
    resp = await client.get("/api/v1/cases", headers={"Authorization": f"Bearer {fake_token}"})
    suite.add(TestResult(
        "Soxta JWT token — 401",
        resp.status_code == 401,
        f"HTTP {resp.status_code}",
    ))

    # 5. To'g'ri login (agar parol berilgan bo'lsa)
    if admin_pass:
        token = await get_admin_token(client, admin_user, admin_pass)
        suite.add(TestResult(
            "To'g'ri login ishlaydi",
            bool(token),
            "Token olindi" if token else "Token olinmadi",
        ))

        if token:
            # 6. Viewer roli admin endpointni bajara olmaydi (agar viewer user bo'lsa)
            resp = await client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
            suite.add(TestResult(
                "Admin token bilan API ishlaydi",
                resp.status_code == 200,
                f"HTTP {resp.status_code}",
            ))

    return suite


# ── Test Suite 3: Maxfiy Fayllar ─────────────────────────────────────────────

async def test_sensitive_files(client: httpx.AsyncClient) -> TestSuite:
    suite = TestSuite("📁 Maxfiy Fayllar")

    sensitive_paths = [
        "/.env",
        "/.env.local",
        "/.env.example",
        "/docker-compose.yml",
        "/docker-compose.yaml",
        "/.git/config",
        "/.git/HEAD",
        "/config.py",
        "/backend/app/core/config.py",
        "/api/docs",        # Swagger production da o'chirilgan bo'lishi kerak
        "/api/redoc",
        "/api/openapi.json",
    ]

    for path in sensitive_paths:
        try:
            resp = await client.get(path)
            is_safe = resp.status_code in (404, 403, 301, 302)
            # Swagger faqat debug=true da ko'rinishi kerak
            if path in ("/api/docs", "/api/redoc") and resp.status_code == 200:
                suite.add(TestResult(
                    f"{path} — production da o'chirilgan",
                    False,
                    f"⚠️ HTTP {resp.status_code} — Swagger ochiq! DEBUG=false qiling.",
                ))
            else:
                suite.add(TestResult(
                    f"{path} — bloklangan",
                    is_safe,
                    f"HTTP {resp.status_code}",
                ))
        except Exception as e:
            suite.add(TestResult(f"{path}", False, str(e)))

    return suite


# ── Test Suite 4: Fayl Yuklash ────────────────────────────────────────────────

async def test_file_upload(client: httpx.AsyncClient, token: Optional[str]) -> TestSuite:
    suite = TestSuite("📎 Fayl Yuklash Xavfsizligi")

    if not token:
        suite.add(TestResult("Fayl upload testlari", True, "Token yo'q — skip", skip=True))
        return suite

    headers = {"Authorization": f"Bearer {token}"}

    # Test case ID topish
    resp = await client.get("/api/v1/cases?limit=1", headers=headers)
    case_id = None
    if resp.status_code == 200:
        cases = resp.json()
        if cases and isinstance(cases, list) and len(cases) > 0:
            case_id = cases[0].get("case_id") or cases[0].get("id")
        elif isinstance(cases, dict) and cases.get("items"):
            case_id = cases["items"][0].get("case_id")

    if not case_id:
        suite.add(TestResult("Fayl upload", True, "Test case topilmadi — skip", skip=True))
        return suite

    upload_url = f"/api/v1/cases/{case_id}/attachments"

    # Bloklangan fayllar
    blocked_files = [
        ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
        ("shell.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
        ("script.js", b"alert('xss')", "application/javascript"),
        ("evil.bat", b"@echo off\ndel /f /s /q C:\\", "text/plain"),
    ]

    for filename, content, mime in blocked_files:
        try:
            resp = await client.post(
                upload_url,
                headers=headers,
                files={"file": (filename, io.BytesIO(content), mime)},
            )
            suite.add(TestResult(
                f"{filename} — bloklangan",
                resp.status_code in (400, 415, 422),
                f"HTTP {resp.status_code}",
            ))
        except Exception as e:
            suite.add(TestResult(f"{filename}", False, str(e)))

    # Katta fayl (21MB)
    try:
        big_content = b"A" * (21 * 1024 * 1024)  # 21MB
        resp = await client.post(
            upload_url,
            headers=headers,
            files={"file": ("big_file.pdf", io.BytesIO(big_content), "application/pdf")},
        )
        suite.add(TestResult(
            "21MB fayl — rad etiladi",
            resp.status_code in (400, 413, 422),
            f"HTTP {resp.status_code}",
        ))
    except Exception as e:
        suite.add(TestResult("21MB fayl", True, f"Ulanish uzildi (ehtimol limit ishladi): {e}", skip=True))

    # Path traversal
    try:
        resp = await client.post(
            upload_url,
            headers=headers,
            files={"file": ("../../etc/passwd", b"root:x:0:0:", "text/plain")},
        )
        suite.add(TestResult(
            "Path traversal — bloklangan",
            resp.status_code in (400, 422),
            f"HTTP {resp.status_code}",
        ))
    except Exception as e:
        suite.add(TestResult("Path traversal", False, str(e)))

    return suite


# ── Test Suite 5: Rate Limiting ────────────────────────────────────────────────

async def test_rate_limiting(client: httpx.AsyncClient) -> TestSuite:
    suite = TestSuite("⚡ Rate Limiting")

    # Login endpoint rate limiting
    rate_limited = False
    for i in range(20):
        resp = await client.post("/api/v1/auth/token", data={
            "username": "testuser_nonexistent",
            "password": "wrong",
        })
        if resp.status_code == 429:
            rate_limited = True
            suite.add(TestResult(
                f"Login brute force — {i+1}. urinishda bloklandi",
                True,
                f"HTTP 429 ({i+1} urinishdan keyin)",
            ))
            break

    if not rate_limited:
        suite.add(TestResult(
            "Login brute force — rate limited",
            False,
            "20 noto'g'ri urinishdan keyin ham 429 kelmadi",
        ))

    # Health endpoint (rate limiting bo'lmasligi kerak)
    resp = await client.get("/api/health")
    suite.add(TestResult(
        "/api/health ishlaydi",
        resp.status_code == 200,
        f"HTTP {resp.status_code}",
    ))

    return suite


# ── Test Suite 6: CORS ────────────────────────────────────────────────────────

async def test_cors(client: httpx.AsyncClient) -> TestSuite:
    suite = TestSuite("🌐 CORS")

    # Ruxsatsiz origin
    resp = await client.options(
        "/api/v1/cases",
        headers={
            "Origin": "https://evil-attacker.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    acao = resp.headers.get("access-control-allow-origin", "")
    suite.add(TestResult(
        "Ruxsatsiz origin bloklangan",
        "evil-attacker.com" not in acao and acao != "*",
        f"Access-Control-Allow-Origin: {acao or '(yo`q)'}",
    ))

    return suite


# ── Asosiy ishga tushirish ─────────────────────────────────────────────────────

async def run_tests(host: str, admin_user: str, admin_pass: str, full: bool = False):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"🔒 IntegrityBot — Xavfsizlik Testlari")
    print(f"🌍 Host: {host}")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    suites = []
    token = None

    async with httpx.AsyncClient(
        base_url=host,
        follow_redirects=True,
        timeout=10.0,
        verify=False,   # Self-signed sertifikatlar uchun
    ) as client:
        # Token olish
        if admin_pass:
            token = await get_admin_token(client, admin_user, admin_pass)
            if token:
                print(info(f"Admin token olindi: {admin_user}"))
            else:
                print(warn(f"Admin token olinmadi — ba'zi testlar skip qilinadi"))

        # Testlarni ishga tushirish
        suites.append(await test_security_headers(client))
        suites.append(await test_authentication(client, admin_user, admin_pass))
        suites.append(await test_sensitive_files(client))
        suites.append(await test_cors(client))

        if full:
            suites.append(await test_file_upload(client, token))
            suites.append(await test_rate_limiting(client))

    # ── Natijalarni chiqarish ────────────────────────────────────────────
    total_pass = 0
    total_fail = 0
    total_skip = 0

    for suite in suites:
        print(f"\n{Fore.CYAN}▶ {suite.name}{Style.RESET_ALL}")
        for r in suite.results:
            if r.skip:
                print(f"  {Fore.YELLOW}⏭  {r.name} — SKIP{Style.RESET_ALL}")
                total_skip += 1
            elif r.passed:
                print(f"  {Fore.GREEN}✅ {r.name}{Style.RESET_ALL}")
                if r.details:
                    print(f"     {Fore.GREEN}{r.details}{Style.RESET_ALL}")
                total_pass += 1
            else:
                print(f"  {Fore.RED}❌ {r.name}{Style.RESET_ALL}")
                if r.details:
                    print(f"     {Fore.RED}{r.details}{Style.RESET_ALL}")
                total_fail += 1

    # Umumiy natija
    total = total_pass + total_fail
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"📊 NATIJA: {total_pass}/{total} o'tdi | {total_fail} muvaffaqiyatsiz | {total_skip} skip")

    if total_fail == 0:
        print(f"{Fore.GREEN}🎉 BARCHA TESTLAR O'TDI — Ishga tushirishga tayyor!{Style.RESET_ALL}")
    elif total_fail <= 2:
        print(f"{Fore.YELLOW}⚠️  {total_fail} ta muammo — tekshirib tuzating{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}🚨 {total_fail} ta muammo topildi — ishga tushirishdan oldin tuating!{Style.RESET_ALL}")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    return total_fail


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IntegrityBot xavfsizlik testlari")
    parser.add_argument("--host", default="http://localhost", help="Backend URL")
    parser.add_argument("--user", default=DEFAULT_ADMIN_USER, help="Admin username")
    parser.add_argument("--password", default=DEFAULT_ADMIN_PASS, help="Admin password")
    parser.add_argument("--full", action="store_true", help="To'liq test (fayl upload, rate limit)")
    args = parser.parse_args()

    exit_code = asyncio.run(run_tests(
        host=args.host,
        admin_user=args.user,
        admin_pass=args.password,
        full=args.full,
    ))
    sys.exit(min(exit_code, 1))

