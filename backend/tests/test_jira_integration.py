"""
Jira / Redmine integratsiya testlari.
Haqiqiy server kerak emas — aiohttp mock bilan.
"""
import pytest
import base64
import os
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


def make_settings_with_jira(monkeypatch):
    monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_TOKEN", "test_token")
    monkeypatch.setenv("JIRA_USER_EMAIL", "admin@test.com")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "COMP")
    monkeypatch.setenv("JIRA_MIN_PRIORITY", "critical")


def make_settings_with_redmine(monkeypatch):
    monkeypatch.setenv("REDMINE_URL", "http://redmine.test.uz")
    monkeypatch.setenv("REDMINE_API_KEY", "test_api_key")
    monkeypatch.setenv("REDMINE_PROJECT_ID", "integritybot")


# ── TicketResult testlari ─────────────────────────────────────────────────────

class TestTicketResult:
    def test_default_values(self):
        from app.services.jira_integration import TicketResult
        r = TicketResult()
        assert r.created is False
        assert r.ticket_id is None
        assert r.url is None
        assert r.system is None
        assert r.error is None
        assert r.skipped is False

    def test_created_result(self):
        from app.services.jira_integration import TicketResult
        r = TicketResult(created=True, ticket_id="COMP-123", url="https://test.atlassian.net/browse/COMP-123", system="jira")
        assert r.created is True
        assert r.ticket_id == "COMP-123"
        assert r.system == "jira"

    def test_skipped_result(self):
        from app.services.jira_integration import TicketResult
        r = TicketResult(skipped=True, skip_reason="Priority past")
        assert r.skipped is True
        assert r.skip_reason == "Priority past"
        assert r.created is False


# ── JiraClient testlari ───────────────────────────────────────────────────────

class TestJiraClient:
    def test_not_configured_when_empty(self):
        from app.services.jira_integration import JiraClient
        from app.core.config import settings
        orig_url = settings.JIRA_URL
        orig_token = settings.JIRA_TOKEN
        settings.JIRA_URL = None
        settings.JIRA_TOKEN = None
        try:
            client = JiraClient()
            assert not client.is_configured()
        finally:
            settings.JIRA_URL = orig_url
            settings.JIRA_TOKEN = orig_token

    def test_configured_when_set(self, monkeypatch):
        make_settings_with_jira(monkeypatch)
        # Settings ni qayta yuklash
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import JiraClient
        client = JiraClient()
        assert client.is_configured()

    def test_cloud_auth_uses_basic(self, monkeypatch):
        """Atlassian Cloud: email + token → Basic auth."""
        make_settings_with_jira(monkeypatch)
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import JiraClient
        client = JiraClient()
        headers = client._get_headers()
        assert "Basic" in headers.get("Authorization", "")

    def test_server_auth_uses_bearer(self, monkeypatch):
        """Jira Server/DC: token → Bearer auth (email yo'q)."""
        monkeypatch.setenv("JIRA_URL", "https://jira.company.uz")
        monkeypatch.setenv("JIRA_TOKEN", "pat_token")
        monkeypatch.setenv("JIRA_USER_EMAIL", "")
        monkeypatch.setenv("JIRA_PROJECT_KEY", "COMP")
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import JiraClient
        client = JiraClient()
        headers = client._get_headers()
        assert "Bearer" in headers.get("Authorization", "")

    @pytest.mark.asyncio
    async def test_create_issue_not_configured_returns_error(self):
        from app.services.jira_integration import JiraClient
        from app.core.config import settings
        orig_url = settings.JIRA_URL
        settings.JIRA_URL = None
        try:
            client = JiraClient()
            result = await client.create_issue("CASE-001", "corruption", "critical", "Test", True)
            assert result.created is False
            assert result.error is not None
        finally:
            settings.JIRA_URL = orig_url

    @pytest.mark.asyncio
    async def test_create_issue_success(self, monkeypatch):
        """Jira 201 javob bersa — tiket yaratilgan bo'lishi kerak."""
        make_settings_with_jira(monkeypatch)
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import JiraClient

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={"key": "COMP-42", "id": "10042"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            client = JiraClient()
            result = await client.create_issue(
                "CASE-20260302-00001", "corruption", "critical", "Test tavsif", True
            )

        assert result.created is True
        assert result.ticket_id == "COMP-42"
        assert "COMP-42" in result.url
        assert result.system == "jira"

    @pytest.mark.asyncio
    async def test_create_issue_http_error(self, monkeypatch):
        """Jira 400/500 javob bersa — xato bo'lishi kerak."""
        make_settings_with_jira(monkeypatch)
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import JiraClient

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value='{"errorMessages":["Project \'COMP\' does not exist"]}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            client = JiraClient()
            result = await client.create_issue(
                "CASE-20260302-00001", "corruption", "critical", "Test", True
            )

        assert result.created is False
        assert result.error is not None
        assert "400" in result.error


# ── RedmineClient testlari ────────────────────────────────────────────────────

class TestRedmineClient:
    def test_not_configured_when_empty(self):
        from app.services.jira_integration import RedmineClient
        from app.core.config import settings
        orig = settings.REDMINE_URL
        settings.REDMINE_URL = None
        try:
            client = RedmineClient()
            assert not client.is_configured()
        finally:
            settings.REDMINE_URL = orig

    def test_configured_when_set(self, monkeypatch):
        make_settings_with_redmine(monkeypatch)
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import RedmineClient
        client = RedmineClient()
        assert client.is_configured()

    def test_redmine_auth_uses_api_key_header(self, monkeypatch):
        make_settings_with_redmine(monkeypatch)
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import RedmineClient
        client = RedmineClient()
        headers = client._get_headers()
        assert "X-Redmine-API-Key" in headers
        assert headers["X-Redmine-API-Key"] == "test_api_key"

    @pytest.mark.asyncio
    async def test_create_issue_not_configured(self):
        from app.services.jira_integration import RedmineClient
        from app.core.config import settings
        orig = settings.REDMINE_URL
        settings.REDMINE_URL = None
        try:
            client = RedmineClient()
            result = await client.create_issue("CASE-001", "corruption", "critical", "Test", True)
            assert result.created is False
        finally:
            settings.REDMINE_URL = orig


# ── TicketService testlari ────────────────────────────────────────────────────

class TestTicketService:
    def test_not_configured_when_nothing_set(self):
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig_jira = settings.JIRA_URL
        orig_redmine = settings.REDMINE_URL
        settings.JIRA_URL = None
        settings.REDMINE_URL = None
        try:
            svc = TicketService()
            assert not svc.is_configured()
            assert svc.active_system() is None
        finally:
            settings.JIRA_URL = orig_jira
            settings.REDMINE_URL = orig_redmine

    def test_active_system_jira_priority(self, monkeypatch):
        """Ikkalasi ham sozlangan bo'lsa — Jira ustunlik qiladi."""
        make_settings_with_jira(monkeypatch)
        make_settings_with_redmine(monkeypatch)
        import importlib
        import app.core.config as cfg
        importlib.reload(cfg)
        import app.services.jira_integration as jira_mod
        importlib.reload(jira_mod)
        from app.services.jira_integration import TicketService
        svc = TicketService()
        assert svc.active_system() == "jira"

    def test_priority_threshold_critical_only(self):
        """JIRA_MIN_PRIORITY=critical: faqat critical tiket ochilsin."""
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig = settings.JIRA_MIN_PRIORITY
        settings.JIRA_MIN_PRIORITY = "critical"
        try:
            svc = TicketService()
            should_c, _ = svc._should_create_ticket("critical")
            should_h, _ = svc._should_create_ticket("high")
            should_m, _ = svc._should_create_ticket("medium")
            assert should_c is True
            assert should_h is False
            assert should_m is False
        finally:
            settings.JIRA_MIN_PRIORITY = orig

    def test_priority_threshold_high(self):
        """JIRA_MIN_PRIORITY=high: critical va high tiket ochilsin."""
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig = settings.JIRA_MIN_PRIORITY
        settings.JIRA_MIN_PRIORITY = "high"
        try:
            svc = TicketService()
            should_c, _ = svc._should_create_ticket("critical")
            should_h, _ = svc._should_create_ticket("high")
            should_m, _ = svc._should_create_ticket("medium")
            assert should_c is True
            assert should_h is True
            assert should_m is False
        finally:
            settings.JIRA_MIN_PRIORITY = orig

    def test_priority_threshold_all(self):
        """JIRA_MIN_PRIORITY=all: barcha prioritylar uchun tiket ochilsin."""
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig = settings.JIRA_MIN_PRIORITY
        settings.JIRA_MIN_PRIORITY = "all"
        try:
            svc = TicketService()
            for p in ["critical", "high", "medium", "low"]:
                should, _ = svc._should_create_ticket(p)
                assert should is True, f"{p} uchun tiket ochilmadi"
        finally:
            settings.JIRA_MIN_PRIORITY = orig

    @pytest.mark.asyncio
    async def test_create_ticket_skipped_when_not_configured(self):
        """Tizim sozlanmagan — tiket o'tkazib yuboriladi."""
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig_jira = settings.JIRA_URL
        orig_redmine = settings.REDMINE_URL
        settings.JIRA_URL = None
        settings.REDMINE_URL = None
        try:
            svc = TicketService()
            result = await svc.create_ticket_for_case(
                "CASE-001", "corruption", "critical", "Test", True
            )
            assert result.skipped is True
        finally:
            settings.JIRA_URL = orig_jira
            settings.REDMINE_URL = orig_redmine

    @pytest.mark.asyncio
    async def test_create_ticket_skipped_for_low_priority(self):
        """Low priority — tiket o'tkazib yuboriladi (min=critical)."""
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig_min = settings.JIRA_MIN_PRIORITY
        orig_jira = settings.JIRA_URL
        settings.JIRA_MIN_PRIORITY = "critical"
        settings.JIRA_URL = "https://test.atlassian.net"
        settings.JIRA_TOKEN = "token"
        settings.JIRA_PROJECT_KEY = "COMP"
        try:
            svc = TicketService()
            result = await svc.create_ticket_for_case(
                "CASE-001", "other", "low", "Test", True
            )
            assert result.skipped is True
            assert result.skip_reason is not None
        finally:
            settings.JIRA_MIN_PRIORITY = orig_min
            settings.JIRA_URL = orig_jira

    @pytest.mark.asyncio
    async def test_health_check_disabled(self):
        """Tizim sozlanmagan — health disabled qaytaradi."""
        from app.services.jira_integration import TicketService
        from app.core.config import settings
        orig_jira = settings.JIRA_URL
        orig_redmine = settings.REDMINE_URL
        settings.JIRA_URL = None
        settings.REDMINE_URL = None
        try:
            svc = TicketService()
            result = await svc.health_check()
            assert result["enabled"] is False
            assert result["status"] == "disabled"
        finally:
            settings.JIRA_URL = orig_jira
            settings.REDMINE_URL = orig_redmine


# ── Priority mapping testlari ─────────────────────────────────────────────────

class TestPriorityMappings:
    def test_jira_priority_map_covers_all(self):
        from app.services.jira_integration import JIRA_PRIORITY_MAP
        for p in ["critical", "high", "medium", "low"]:
            assert p in JIRA_PRIORITY_MAP, f"{p} JIRA_PRIORITY_MAP da yo'q"

    def test_redmine_priority_map_covers_all(self):
        from app.services.jira_integration import REDMINE_PRIORITY_MAP
        for p in ["critical", "high", "medium", "low"]:
            assert p in REDMINE_PRIORITY_MAP, f"{p} REDMINE_PRIORITY_MAP da yo'q"

    def test_priority_order_correct(self):
        from app.services.jira_integration import PRIORITY_ORDER
        assert PRIORITY_ORDER[0] == "critical"
        assert PRIORITY_ORDER[-1] == "low"
        assert len(PRIORITY_ORDER) == 4

    def test_jira_critical_maps_to_critical(self):
        from app.services.jira_integration import JIRA_PRIORITY_MAP
        assert JIRA_PRIORITY_MAP["critical"] == "Critical"

    def test_redmine_critical_maps_to_immediate(self):
        from app.services.jira_integration import REDMINE_PRIORITY_MAP
        assert REDMINE_PRIORITY_MAP["critical"] == "Immediate"

