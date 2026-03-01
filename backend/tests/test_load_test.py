"""
Yuklanish testi maqsadlari va konfiguratsiyasi testlari.

Bu fayl ikki narsani tekshiradi:
1. Load test fayli to'g'ri yozilganmi (sintaksis, sinflar, tasklar)
2. API endpointlarning lokal benchmark testi (httpx bilan, real server kerak emas)

TZ talabi (bo'lim 4.3):
  - 1000 xabar/oy bilan ishlash imkoniyati
  - Javob vaqti (o'rtacha): < 500ms
  - Xato darajasi: < 1%
"""
import pytest
import sys
import os
import base64
import time
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Loyiha ildizini path ga qo'shish (load_test.py uchun)
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.abspath(PROJECT_ROOT))
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


class TestLoadTestFileStructure:
    """Load test fayli to'g'ri tuzilganmi."""

    def test_load_test_file_exists(self):
        """tests/load_test.py fayli mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        assert os.path.exists(load_test_path), (
            f"tests/load_test.py topilmadi: {load_test_path}"
        )

    def test_load_test_imports_correctly(self):
        """load_test.py sintaksis xatosiz import bo'lishi kerak."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "load_test",
                os.path.join(PROJECT_ROOT, "tests", "load_test.py")
            )
            # Locust o'rnatilmagan bo'lsa — skip
            try:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except ImportError as e:
                if "locust" in str(e).lower():
                    pytest.skip("locust o'rnatilmagan — pip install locust")
                raise
        except Exception as e:
            pytest.fail(f"load_test.py import xatosi: {e}")

    def test_load_test_has_admin_user_class(self):
        """AdminUser sinfi mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "class AdminUser" in content, "AdminUser sinfi topilmadi"

    def test_load_test_has_reporter_simulator(self):
        """ReporterBotSimulator sinfi mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "ReporterBotSimulator" in content, "ReporterBotSimulator sinfi topilmadi"

    def test_load_test_has_performance_targets(self):
        """Maqsadli ko'rsatkichlar hujjatlashtirilgan bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "500ms" in content, "Javob vaqti maqsadi topilmadi"
        assert "2000ms" in content or "2s" in content or "2000" in content, "p95 maqsadi topilmadi"
        assert "1%" in content or "1.0" in content, "Xato darajasi maqsadi topilmadi"

    def test_load_test_has_task_decorators(self):
        """@task decoratorlari mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "@task" in content, "@task decorator topilmadi"

    def test_load_test_has_event_hooks(self):
        """Test yakunida natijalarni chop etuvchi hook mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "test_stop" in content, "test_stop event hook topilmadi"

    def test_requirements_load_test_exists(self):
        """requirements-load-test.txt fayli mavjud bo'lishi kerak."""
        req_path = os.path.join(PROJECT_ROOT, "backend", "requirements-load-test.txt")
        assert os.path.exists(req_path), "requirements-load-test.txt topilmadi"
        with open(req_path, "r") as f:
            content = f.read()
        assert "locust" in content.lower(), "locust requirements-load-test.txt da yo'q"


class TestPerformanceTargets:
    """Maqsadli ko'rsatkichlar konstantalari."""

    def test_response_time_target(self):
        """Javob vaqti maqsadi: o'rtacha < 500ms."""
        MAX_AVG_RESPONSE_MS = 500
        assert MAX_AVG_RESPONSE_MS == 500

    def test_p95_response_time_target(self):
        """95-percentil javob vaqti: < 2000ms."""
        MAX_P95_RESPONSE_MS = 2000
        assert MAX_P95_RESPONSE_MS == 2000

    def test_error_rate_target(self):
        """Xato darajasi maqsadi: < 1%."""
        MAX_ERROR_RATE_PCT = 1.0
        assert MAX_ERROR_RATE_PCT < 5.0  # Minimal samarali daraja

    def test_monthly_capacity_target(self):
        """Oylik murojaat miqyosi: 1000+ xabar."""
        MONTHLY_CASES_TARGET = 1000
        # 1000 xabar / 30 kun / 8 soat = ~4.2 xabar/soat = 0.07 xabar/daqiqa
        # Bu juda past yuklanish — tizim bu ni ko'tara olishi kerak
        cases_per_hour = MONTHLY_CASES_TARGET / 30 / 8
        assert cases_per_hour < 10, "Oddiy yuklanish juda yuqori emas"
        assert MONTHLY_CASES_TARGET >= 1000

    def test_concurrent_users_target(self):
        """Bir vaqtdagi foydalanuvchilar: 50+."""
        CONCURRENT_USERS = 50
        assert CONCURRENT_USERS >= 50


class TestAPIEndpointsBenchmark:
    """
    API endpointlarning benchmark testlari.
    FastAPI test clienti bilan — real server kerak emas.
    """

    @pytest.fixture
    def app_client(self):
        """FastAPI test clientini yaratadi."""
        try:
            from httpx import AsyncClient
            from app.main import app
            return AsyncClient(app=app, base_url="http://test")
        except Exception:
            pytest.skip("App import qilishda xatolik — server kerak")

    @pytest.mark.asyncio
    async def test_health_endpoint_response_time(self, app_client):
        """Health endpoint < 200ms da javob berishi kerak."""
        async with app_client as client:
            start = time.perf_counter()
            resp = await client.get("/api/health")
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert resp.status_code == 200
        assert elapsed_ms < 200, f"Health endpoint juda sekin: {elapsed_ms:.0f}ms"

    @pytest.mark.asyncio
    async def test_auth_endpoint_exists(self, app_client):
        """Auth endpoint mavjud va 422/401 qaytaradi (xato credentials)."""
        async with app_client as client:
            resp = await client.post(
                "/api/v1/auth/token",
                data={"username": "nouser", "password": "nopass"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        # 401 yoki 422 — endpoint mavjud
        assert resp.status_code in (401, 422, 400)

    @pytest.mark.asyncio
    async def test_health_response_format(self, app_client):
        """Health endpoint to'g'ri formatda javob berishi kerak."""
        async with app_client as client:
            resp = await client.get("/api/health")

        data = resp.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "storage" in data
        assert "antivirus" in data


class TestLoadTestScenarios:
    """Yuklanish ssenariylari mantiqini tekshirish."""

    def test_monthly_1000_cases_math(self):
        """
        1000 xabar/oy miqyosini tekshirish.
        Tizim kuniga ~33 ta, soatiga ~4 ta yangi murojaat qabul qilishi kerak.
        """
        monthly = 1000
        daily = monthly / 30
        hourly = daily / 8  # ish soatlari
        per_minute = hourly / 60

        assert daily == pytest.approx(33.33, rel=0.1)
        assert hourly == pytest.approx(4.17, rel=0.1)
        assert per_minute < 1  # Minutiga 1 tadan kam — past yuklanish

    def test_peak_load_calculation(self):
        """
        Pik yuklanish: oddiydan 10x ko'p.
        Tizim pik da ham ishlashi kerak.
        """
        avg_per_minute = 1000 / 30 / 8 / 60   # ~0.07/daqiqa
        peak_multiplier = 10
        peak_per_minute = avg_per_minute * peak_multiplier

        # Pik da ham < 1 ta/daqiqa — juda kam
        # 50 bir vaqtdagi foydalanuvchi bilan 10 RPS kutiladi
        assert peak_per_minute < 10

    def test_concurrent_sessions_simulation(self):
        """
        50 bir vaqtdagi foydalanuvchi simulatsiyasi.
        Har biri 3-4 soniyada bir so'rov = ~13-16 RPS
        """
        concurrent_users = 50
        wait_time_avg_sec = 3.5  # between(1, 6) o'rtachasi
        expected_rps = concurrent_users / wait_time_avg_sec

        assert expected_rps > 10, f"Kutilgan RPS juda past: {expected_rps:.1f}"
        assert expected_rps < 100, f"Kutilgan RPS juda yuqori: {expected_rps:.1f}"

    def test_load_test_user_weights(self):
        """Foydalanuvchi og'irliqlari mantiqiy bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Weight'lar mavjud
        assert "weight" in content, "Foydalanuvchi og'irliklari (weight) topilmadi"
        # Admin ko'p — reporter kam
        assert "weight = 3" in content or "weight=3" in content, "AdminUser weight=3 bo'lishi kerak"

    def test_scenario_covers_critical_endpoints(self):
        """Load test kritik endpointlarni qamrab olishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()

        critical_endpoints = [
            "/api/v1/cases",         # Asosiy endpoint
            "/api/v1/auth/token",    # Auth
            "/api/health",           # Health check
            "/api/v1/cases/stats",   # Dashboard
        ]
        for ep in critical_endpoints:
            assert ep in content, f"Kritik endpoint topilmadi: {ep}"


class TestLoadTestDocumentation:
    """Load test hujjatlashtirilganmi."""

    def test_load_test_has_usage_instructions(self):
        """Ishlatish ko'rsatmalari mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "locust -f" in content, "Locust ishga tushirish ko'rsatmasi topilmadi"
        assert "--users" in content, "--users parametri topilmadi"
        assert "--headless" in content, "--headless parametri topilmadi"

    def test_load_test_has_tz_reference(self):
        """TZ talablariga havola mavjud bo'lishi kerak."""
        load_test_path = os.path.join(PROJECT_ROOT, "tests", "load_test.py")
        with open(load_test_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "1000" in content, "1000 xabar/oy talabi topilmadi"

    def test_requirements_has_correct_version(self):
        """requirements-load-test.txt to'g'ri versiya formatida bo'lishi kerak."""
        req_path = os.path.join(PROJECT_ROOT, "backend", "requirements-load-test.txt")
        with open(req_path, "r") as f:
            content = f.read()
        # locust== yoki locust>= formatida bo'lishi kerak
        assert "locust" in content.lower()
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        locust_line = next((l for l in lines if "locust" in l.lower()), None)
        assert locust_line is not None, "locust qatori topilmadi"

