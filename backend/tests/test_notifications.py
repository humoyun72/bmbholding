"""
Notification service unit testlari (mock bilan).
"""
import pytest
import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


class TestCategoryLabels:
    def test_all_categories_have_labels(self):
        from app.services.notification import CATEGORY_LABELS
        from app.models import CaseCategory
        for cat in CaseCategory:
            assert cat in CATEGORY_LABELS
            assert len(CATEGORY_LABELS[cat]) > 0

    def test_labels_contain_emoji(self):
        from app.services.notification import CATEGORY_LABELS
        for label in CATEGORY_LABELS.values():
            # Har bir label emoji bilan boshlanishi kerak
            assert any(ord(c) > 127 for c in label)


class TestNotifyAdmins:
    @pytest.mark.asyncio
    async def test_notify_sends_telegram_message(self):
        from app.services.notification import notify_admins
        from app.models import CaseCategory

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with patch("app.services.notification.send_email_notification", new=AsyncMock()):
            await notify_admins(
                bot=mock_bot,
                case_id="CASE-20260301-00001",
                category=CaseCategory.CORRUPTION,
                description="Test murojaat tavsifi",
                is_anonymous=True,
            )

        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args
        # Message matni case_id ni o'z ichiga olishi kerak
        assert "CASE-20260301-00001" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_notify_handles_telegram_error_gracefully(self):
        """Telegram xato bersa — exception ko'tarilmasligi kerak."""
        from app.services.notification import notify_admins
        from app.models import CaseCategory

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Telegram error"))

        with patch("app.services.notification.send_email_notification", new=AsyncMock()):
            # Exception ko'tarilmasligi kerak
            await notify_admins(
                bot=mock_bot,
                case_id="CASE-20260301-00002",
                category=CaseCategory.FRAUD,
                description="Test",
                is_anonymous=False,
            )

    @pytest.mark.asyncio
    async def test_notify_description_truncated(self):
        """300 belgidan uzun tavsif qisqartirilishi kerak."""
        from app.services.notification import notify_admins
        from app.models import CaseCategory

        long_desc = "X" * 500
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with patch("app.services.notification.send_email_notification", new=AsyncMock()):
            await notify_admins(
                bot=mock_bot,
                case_id="CASE-TEST",
                category=CaseCategory.OTHER,
                description=long_desc,
                is_anonymous=True,
            )

        call_text = str(mock_bot.send_message.call_args)
        # Qisqartirilganda "..." belgisi ko'rinishi kerak
        assert "..." in call_text

    @pytest.mark.asyncio
    async def test_anonymous_flag_shown_in_message(self):
        from app.services.notification import notify_admins
        from app.models import CaseCategory

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with patch("app.services.notification.send_email_notification", new=AsyncMock()):
            await notify_admins(
                bot=mock_bot,
                case_id="CASE-ANON",
                category=CaseCategory.SAFETY,
                description="xavfsizlik",
                is_anonymous=True,
            )

        call_text = str(mock_bot.send_message.call_args)
        assert "Anonim" in call_text

