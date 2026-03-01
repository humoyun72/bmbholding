"""
🚀 IntegrityBot — Yuklanish Testi (Locust)
==========================================

TZ talabi (bo'lim 4.3): 1000 xabar/oy bilan ishlash imkoniyati
TZ qabul qilish mezoni (bo'lim 18): Yuklanish testi o'tgan (1000 xabar/oy, pik yuklanish)

Maqsadli ko'rsatkichlar:
  - Murojaatlar/oy       : 1,000+
  - Bir vaqtdagi users   : 50+
  - API javob (o'rtacha) : < 500ms
  - API javob (p95)      : < 2000ms
  - Xato darajasi        : < 1%

Ishlatish:
  # 1. Locust o'rnatish:
  pip install locust

  # 2. Backend ishga tushirish (lokal yoki docker):
  docker compose up -d backend db redis

  # 3. Web UI bilan ishga tushirish:
  locust -f tests/load_test.py --host=http://localhost

  # 4. Headless (CI uchun):
  locust -f tests/load_test.py --host=http://localhost \
    --users=50 --spawn-rate=5 --run-time=2m --headless \
    --csv=tests/load_test_results

  # 5. Pik yuklanish testi:
  locust -f tests/load_test.py --host=http://localhost \
    --users=100 --spawn-rate=10 --run-time=5m --headless

Natijalarni ko'rish:
  - Web UI: http://localhost:8089
  - CSV: tests/load_test_results_stats.csv
"""

import json
import random
import string
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# ── Konfiguratsiya ────────────────────────────────────────────────────────────

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@CHANGE_ME_NOW!"   # .env dagi ADMIN_DEFAULT_PASSWORD

# Test case ID lari (mavjud bo'lsa)
SAMPLE_CASE_IDS = []

# ── Yordamchi funksiyalar ─────────────────────────────────────────────────────

def random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_case_description() -> str:
    templates = [
        "Rahbariyat tomonidan tender jarayonida qoidabuzarlik aniqlandi. "
        "Shartnoma raqami: {code}. Summa: {amount} so'm.",
        "Xodim ish vaqtida shaxsiy manfaat ko'zlab {code} loyihasiga zarar yetkazdi.",
        "Moliyaviy hisobotlarda {code} raqamli kamchilik aniqlandi. "
        "Miqdor: {amount} so'm. Sana: 2026-02-{day:02d}.",
        "Xavfsizlik qoidalari buzildi: {code} ob'ektida litsenziyasiz faoliyat.",
        "Kamsitish holati qayd etildi. Hodisa sanasi: 2026-{month:02d}-{day:02d}.",
    ]
    return random.choice(templates).format(
        code=random_string(8).upper(),
        amount=random.randint(1_000_000, 100_000_000),
        day=random.randint(1, 28),
        month=random.randint(1, 12),
    )


# ── Foydalanuvchi sinflari ────────────────────────────────────────────────────

class AdminUser(HttpUser):
    """
    Admin paneli foydalanuvchisi — ko'p o'qiydi, kam yozadi.
    Tipik: compliance officer ish kunida 50 marta API chaqiradi.
    """
    wait_time = between(1, 4)
    weight = 3   # 3x ko'p admin foydalanuvchisi
    token: str | None = None

    def on_start(self):
        """Kirish — token olish."""
        resp = self.client.post(
            "/api/v1/auth/token",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/api/v1/auth/token [login]",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
        else:
            self.token = None

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(10)
    def list_cases(self):
        """Murojaatlar ro'yxati — eng ko'p ishlatiladigan endpoint."""
        page = random.randint(1, 3)
        self.client.get(
            f"/api/v1/cases?page={page}&per_page=20",
            headers=self._auth(),
            name="/api/v1/cases [list]",
        )

    @task(5)
    def list_cases_filtered(self):
        """Filtrlangan murojaatlar."""
        statuses = ["new", "in_review", "resolved"]
        status = random.choice(statuses)
        self.client.get(
            f"/api/v1/cases?status={status}&page=1&per_page=20",
            headers=self._auth(),
            name="/api/v1/cases [filtered]",
        )

    @task(4)
    def get_case_detail(self):
        """Bitta murojaat tafsilotlari."""
        if SAMPLE_CASE_IDS:
            case_id = random.choice(SAMPLE_CASE_IDS)
        else:
            # Mavhum ID — 404 bo'lsa ham yuklanish o'lchanadi
            today = time.strftime("%Y%m%d")
            case_id = f"CASE-{today}-{random.randint(1, 100):05d}"

        self.client.get(
            f"/api/v1/cases/{case_id}",
            headers=self._auth(),
            name="/api/v1/cases/{id} [detail]",
        )

    @task(3)
    def dashboard_stats(self):
        """Dashboard statistikasi."""
        self.client.get(
            "/api/v1/cases/stats",
            headers=self._auth(),
            name="/api/v1/cases/stats [dashboard]",
        )

    @task(2)
    def audit_log(self):
        """Audit jurnal."""
        self.client.get(
            "/api/v1/audit?page=1&per_page=20",
            headers=self._auth(),
            name="/api/v1/audit [list]",
        )

    @task(1)
    def health_check(self):
        """Tizim holati."""
        self.client.get(
            "/api/health",
            name="/api/health",
        )

    @task(1)
    def list_polls(self):
        """So'rovnomalar ro'yxati."""
        self.client.get(
            "/api/v1/polls?page=1&per_page=10",
            headers=self._auth(),
            name="/api/v1/polls [list]",
        )

    @task(2)
    def change_case_status(self):
        """Murojaat statusini o'zgartirish — yozish operatsiyasi."""
        if not SAMPLE_CASE_IDS:
            return
        case_id = random.choice(SAMPLE_CASE_IDS)
        statuses = ["in_review", "pending_info"]
        self.client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": random.choice(statuses)},
            headers=self._auth(),
            name="/api/v1/cases/{id}/status [update]",
        )

    @task(1)
    def add_internal_comment(self):
        """Ichki izoh qo'shish."""
        if not SAMPLE_CASE_IDS:
            return
        case_id = random.choice(SAMPLE_CASE_IDS)
        self.client.post(
            f"/api/v1/cases/{case_id}/comments",
            json={
                "content": f"Ichki izoh: {random_string(50)}",
                "is_internal": True,
            },
            headers=self._auth(),
            name="/api/v1/cases/{id}/comments [add]",
        )


class ReporterBotSimulator(HttpUser):
    """
    Telegram bot orqali murojaat yuborayotgan foydalanuvchini simulatsiya qiladi.
    Webhook endpoint ga to'g'ridan-to'g'ri POST qiladi.
    """
    wait_time = between(5, 15)   # Odamlar telegram da sekinroq yozadi
    weight = 1

    def _make_telegram_update(self, chat_id: int, text: str) -> dict:
        """Telegram Update JSON formatini yaratadi."""
        return {
            "update_id": random.randint(100000, 999999),
            "message": {
                "message_id": random.randint(1, 9999),
                "from": {
                    "id": chat_id,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": f"testuser_{chat_id}",
                },
                "chat": {
                    "id": chat_id,
                    "type": "private",
                },
                "date": int(time.time()),
                "text": text,
            },
        }

    def _make_callback_query(self, chat_id: int, data: str) -> dict:
        """Inline keyboard callback query yaratadi."""
        return {
            "update_id": random.randint(100000, 999999),
            "callback_query": {
                "id": str(random.randint(1000000, 9999999)),
                "from": {
                    "id": chat_id,
                    "is_bot": False,
                    "first_name": "Test",
                },
                "message": {
                    "message_id": random.randint(1, 9999),
                    "chat": {"id": chat_id, "type": "private"},
                    "date": int(time.time()),
                    "text": "...",
                },
                "data": data,
            },
        }

    @task(3)
    def send_start_command(self):
        """/start buyrug'ini yuborish."""
        chat_id = random.randint(100000000, 999999999)
        update = self._make_telegram_update(chat_id, "/start")
        self.client.post(
            "/api/telegram/webhook",
            json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
            name="/api/telegram/webhook [/start]",
        )

    @task(2)
    def click_report_button(self):
        """'Murojaat yuborish' tugmasini bosish."""
        chat_id = random.randint(100000000, 999999999)
        update = self._make_callback_query(chat_id, "report")
        self.client.post(
            "/api/telegram/webhook",
            json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
            name="/api/telegram/webhook [callback:report]",
        )

    @task(1)
    def check_status(self):
        """Murojaat holatini tekshirish."""
        chat_id = random.randint(100000000, 999999999)
        today = time.strftime("%Y%m%d")
        case_id = f"CASE-{today}-{random.randint(1, 50):05d}"
        update = self._make_telegram_update(chat_id, case_id)
        self.client.post(
            "/api/telegram/webhook",
            json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token": "test_secret"},
            name="/api/telegram/webhook [check_status]",
        )


class ReadOnlyUser(HttpUser):
    """
    Faqat o'qiydigan foydalanuvchi (Viewer roli).
    Dashboard ko'rish, statistika olish.
    """
    wait_time = between(2, 8)
    weight = 2
    token: str | None = None

    def on_start(self):
        """Viewer sifatida kirish urinishi."""
        # Viewer foydalanuvchi yo'q bo'lishi mumkin — admin bilan kiramiz
        resp = self.client.post(
            "/api/v1/auth/token",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/api/v1/auth/token [viewer-login]",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def read_cases(self):
        self.client.get(
            "/api/v1/cases?page=1&per_page=20",
            headers=self._auth(),
            name="/api/v1/cases [viewer-read]",
        )

    @task(3)
    def read_stats(self):
        self.client.get(
            "/api/v1/cases/stats",
            headers=self._auth(),
            name="/api/v1/cases/stats [viewer]",
        )

    @task(1)
    def health(self):
        self.client.get("/api/health", name="/api/health [viewer]")


# ── Locust event hooks ────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test boshlanishida maqsadlarni chop etish."""
    print("\n" + "=" * 60)
    print("🚀 IntegrityBot Load Test boshlanmoqda")
    print("=" * 60)
    print("📊 Maqsadli ko'rsatkichlar:")
    print("   ✅ Javob vaqti (o'rtacha) : < 500ms")
    print("   ✅ Javob vaqti (p95)      : < 2000ms")
    print("   ✅ Xato darajasi          : < 1%")
    print("   ✅ TPS (transaction/sec)  : > 10")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test yakunida natijalarni tahlil qilish."""
    stats = environment.stats.total
    print("\n" + "=" * 60)
    print("📊 YUKLANISH TESTI NATIJASI")
    print("=" * 60)

    if stats.num_requests == 0:
        print("⚠️  Hech qanday so'rov yuborilmadi!")
        return

    avg_ms = stats.avg_response_time
    p95_ms = stats.get_response_time_percentile(0.95) or 0
    fail_pct = (stats.num_failures / stats.num_requests * 100) if stats.num_requests > 0 else 0
    rps = stats.current_rps

    print(f"   So'rovlar jami    : {stats.num_requests:,}")
    print(f"   Xatolar           : {stats.num_failures:,} ({fail_pct:.2f}%)")
    print(f"   Javob (o'rtacha)  : {avg_ms:.0f}ms")
    print(f"   Javob (p95)       : {p95_ms:.0f}ms")
    print(f"   RPS (joriy)       : {rps:.1f}")

    # Maqsad tekshiruvi
    print("\n📋 Maqsad tekshiruvi:")
    checks = [
        ("Javob vaqti (o'rtacha) < 500ms", avg_ms < 500),
        ("Javob vaqti (p95) < 2000ms",     p95_ms < 2000),
        ("Xato darajasi < 1%",              fail_pct < 1.0),
    ]
    all_passed = True
    for name, passed in checks:
        icon = "✅" if passed else "❌"
        print(f"   {icon} {name}")
        if not passed:
            all_passed = False

    print("\n" + ("✅ BARCHA MAQSADLAR BAJARILDI!" if all_passed else "❌ Ba'zi maqsadlar bajarilmadi!"))
    print("=" * 60 + "\n")

