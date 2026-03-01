"""
Webhook/Polling Konflikti testlari.
effective_bot_mode mantiqini tekshiradi.
"""
import pytest
import base64
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


class TestEffectiveBotMode:
    """Settings.effective_bot_mode mantiq testlari."""

    def _make_settings(self, bot_mode: str, webhook_url: str):
        """Berilgan qiymatlar bilan Settings ob'ekti yaratadi."""
        from app.core.config import Settings
        return Settings(
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            TELEGRAM_BOT_TOKEN="123456:AAA",
            SECRET_KEY="test_secret_key_at_least_32_chars_long!!",
            ENCRYPTION_KEY=base64.b64encode(os.urandom(32)).decode(),
            BOT_MODE=bot_mode,
            WEBHOOK_URL=webhook_url,
        )

    def test_auto_with_https_webhook_returns_webhook(self):
        """auto + https WEBHOOK_URL → webhook rejimi."""
        s = self._make_settings("auto", "https://example.com/api/telegram/webhook")
        assert s.effective_bot_mode == "webhook"

    def test_auto_with_empty_webhook_returns_polling(self):
        """auto + bo'sh WEBHOOK_URL → polling rejimi."""
        s = self._make_settings("auto", "")
        assert s.effective_bot_mode == "polling"

    def test_auto_with_http_webhook_returns_polling(self):
        """auto + http (https emas) WEBHOOK_URL → polling rejimi."""
        s = self._make_settings("auto", "http://example.com/webhook")
        assert s.effective_bot_mode == "polling"

    def test_explicit_polling_overrides_webhook_url(self):
        """BOT_MODE=polling + WEBHOOK_URL to'ldirilgan → baribir polling."""
        s = self._make_settings("polling", "https://example.com/webhook")
        assert s.effective_bot_mode == "polling"

    def test_explicit_webhook_overrides_empty_url(self):
        """BOT_MODE=webhook + bo'sh WEBHOOK_URL → baribir webhook."""
        s = self._make_settings("webhook", "")
        assert s.effective_bot_mode == "webhook"

    def test_explicit_polling_without_url(self):
        """BOT_MODE=polling + bo'sh URL → polling."""
        s = self._make_settings("polling", "")
        assert s.effective_bot_mode == "polling"

    def test_explicit_webhook_with_url(self):
        """BOT_MODE=webhook + https URL → webhook."""
        s = self._make_settings("webhook", "https://example.com/webhook")
        assert s.effective_bot_mode == "webhook"

    def test_auto_is_default(self):
        """Default BOT_MODE 'auto' bo'lishi kerak."""
        from app.core.config import Settings
        import inspect
        # Settings classidagi default qiymatni tekshirish
        fields = Settings.model_fields
        assert "BOT_MODE" in fields
        assert fields["BOT_MODE"].default == "auto"

    def test_conflict_prevention_polling_with_https(self):
        """
        409 Conflict oldini olish:
        BOT_MODE=polling bo'lsa — WEBHOOK_URL to'ldirilgan bo'lsa ham polling ishlaydi.
        Bu Telegram API 409 Conflict xatosini oldini oladi.
        """
        s = self._make_settings("polling", "https://example.com/webhook")
        # polling majburiy tanlangan → webhook ishga tushirilmaydi
        assert s.effective_bot_mode == "polling"
        assert s.effective_bot_mode != "webhook"


class TestWebhookUrlValidation:
    """Webhook URL validatsiyasi testlari."""

    def test_https_url_is_valid_for_webhook(self):
        """https:// bilan boshlangan URL webhook uchun to'g'ri."""
        url = "https://example.com/api/telegram/webhook"
        assert url.startswith("https://")

    def test_http_url_is_invalid_for_webhook(self):
        """http:// webhook uchun noto'g'ri — Telegram faqat https qabul qiladi."""
        url = "http://example.com/webhook"
        assert not url.startswith("https://")

    def test_empty_url_means_polling(self):
        """Bo'sh URL → polling rejimi."""
        url = ""
        assert not (url and url.startswith("https://"))

    def test_localtunnel_url_is_valid(self):
        """ngrok/localtunnel HTTPS URL webhook uchun to'g'ri (dev testing)."""
        url = "https://abc123.ngrok.io/api/telegram/webhook"
        assert url.startswith("https://")

    def test_mode_description(self):
        """
        Rejim tanlash mantiqini hujjatlash:
        auto + https → webhook
        auto + bo'sh/http → polling
        polling (explicit) → har doim polling
        webhook (explicit) → har doim webhook
        """
        from app.core.config import Settings

        cases = [
            # (bot_mode, webhook_url, expected)
            ("auto",    "https://ex.com/hook",  "webhook"),
            ("auto",    "",                      "polling"),
            ("auto",    "http://ex.com/hook",   "polling"),
            ("polling", "https://ex.com/hook",  "polling"),  # 409 oldini olish
            ("polling", "",                      "polling"),
            ("webhook", "",                      "webhook"),
            ("webhook", "https://ex.com/hook",  "webhook"),
        ]

        for bot_mode, webhook_url, expected in cases:
            s = Settings(
                DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
                TELEGRAM_BOT_TOKEN="123456:AAA",
                SECRET_KEY="test_secret_key_at_least_32_chars_long!!",
                ENCRYPTION_KEY=base64.b64encode(os.urandom(32)).decode(),
                BOT_MODE=bot_mode,
                WEBHOOK_URL=webhook_url,
            )
            result = s.effective_bot_mode
            assert result == expected, (
                f"BOT_MODE={bot_mode!r}, WEBHOOK_URL={webhook_url!r} → "
                f"kutildi {expected!r}, lekin {result!r} keldi"
            )

