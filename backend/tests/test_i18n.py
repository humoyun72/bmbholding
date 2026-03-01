"""
Bot i18n (Ko'p-tillilik) testlari.
"""
import pytest
import base64
import os
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


def make_context(lang: str = "uz"):
    """Mock context.user_data bilan."""
    ctx = MagicMock()
    ctx.user_data = {"lang": lang}
    return ctx


class TestTranslationFunction:
    """t() funksiyasi testlari."""

    def test_uz_translation_returns_uzbek(self):
        from app.bot.i18n import t
        text = t("btn_report", "uz")
        assert "Murojaat" in text

    def test_ru_translation_returns_russian(self):
        from app.bot.i18n import t
        text = t("btn_report", "ru")
        assert "обращение" in text.lower() or "Отправить" in text

    def test_en_translation_returns_english(self):
        from app.bot.i18n import t
        text = t("btn_report", "en")
        assert "report" in text.lower() or "Submit" in text

    def test_unknown_lang_falls_back_to_uz(self):
        from app.bot.i18n import t
        text_unknown = t("btn_report", "fr")
        text_uz = t("btn_report", "uz")
        assert text_unknown == text_uz

    def test_none_lang_falls_back_to_default(self):
        from app.bot.i18n import t, DEFAULT_LANG
        text_none = t("btn_report", None)
        text_default = t("btn_report", DEFAULT_LANG)
        assert text_none == text_default

    def test_unknown_key_returns_key_itself(self):
        from app.bot.i18n import t
        result = t("nonexistent_key_xyz", "uz")
        assert result == "nonexistent_key_xyz"

    def test_format_parameters_applied(self):
        from app.bot.i18n import t
        result = t("case_submitted", "uz", case_id="CASE-20260302-00001", token="abc123")
        assert "CASE-20260302-00001" in result
        assert "abc123" in result

    def test_format_parameters_in_russian(self):
        from app.bot.i18n import t
        result = t("case_submitted", "ru", case_id="CASE-20260302-00001", token="abc123")
        assert "CASE-20260302-00001" in result

    def test_format_parameters_in_english(self):
        from app.bot.i18n import t
        result = t("case_submitted", "en", case_id="CASE-20260302-00001", token="abc123")
        assert "CASE-20260302-00001" in result

    def test_rate_limit_time_format(self):
        from app.bot.i18n import t
        result = t("rate_limit_exceeded", "uz", time_str="5 daqiqa")
        assert "5 daqiqa" in result

    def test_rate_limit_time_in_russian(self):
        from app.bot.i18n import t
        result = t("rate_limit_exceeded", "ru", time_str="5 минут")
        assert "5 минут" in result

    def test_case_not_found_with_id(self):
        from app.bot.i18n import t
        result = t("case_not_found", "uz", case_id="CASE-20260302-00001")
        assert "CASE-20260302-00001" in result


class TestSupportedLanguages:
    """Qo'llab-quvvatlanadigan tillar testlari."""

    def test_supported_langs_list(self):
        from app.bot.i18n import SUPPORTED_LANGS
        assert "uz" in SUPPORTED_LANGS
        assert "ru" in SUPPORTED_LANGS
        assert "en" in SUPPORTED_LANGS

    def test_default_lang_is_uzbek(self):
        from app.bot.i18n import DEFAULT_LANG
        assert DEFAULT_LANG == "uz"

    def test_all_keys_have_all_lang_translations(self):
        """Barcha tarjima kalitlari barcha tillarda mavjud bo'lishi kerak."""
        from app.bot.i18n import TRANSLATIONS, SUPPORTED_LANGS
        missing = []
        for key, langs in TRANSLATIONS.items():
            for lang in SUPPORTED_LANGS:
                if lang not in langs:
                    missing.append(f"{key}:{lang}")
        assert not missing, f"Quyidagi tarjimalar yo'q: {missing}"

    def test_no_empty_translations(self):
        """Hech bir tarjima bo'sh bo'lmasligi kerak."""
        from app.bot.i18n import TRANSLATIONS, SUPPORTED_LANGS
        empty = []
        for key, langs in TRANSLATIONS.items():
            for lang in SUPPORTED_LANGS:
                if lang in langs and not langs[lang].strip():
                    empty.append(f"{key}:{lang}")
        assert not empty, f"Bo'sh tarjimalar: {empty}"

    def test_lang_flags_cover_supported_langs(self):
        from app.bot.i18n import LANG_FLAGS, SUPPORTED_LANGS
        for lang in SUPPORTED_LANGS:
            assert lang in LANG_FLAGS, f"{lang} LANG_FLAGS da yo'q"


class TestUserLangFunctions:
    """get_user_lang / set_user_lang testlari."""

    def test_get_user_lang_returns_saved_lang(self):
        from app.bot.i18n import get_user_lang
        ctx = make_context("ru")
        assert get_user_lang(ctx) == "ru"

    def test_get_user_lang_default_when_not_set(self):
        from app.bot.i18n import get_user_lang, DEFAULT_LANG
        ctx = MagicMock()
        ctx.user_data = {}
        assert get_user_lang(ctx) == DEFAULT_LANG

    def test_set_user_lang_saves_correctly(self):
        from app.bot.i18n import set_user_lang, get_user_lang
        ctx = make_context("uz")
        set_user_lang(ctx, "en")
        assert get_user_lang(ctx) == "en"

    def test_set_user_lang_invalid_falls_back(self):
        from app.bot.i18n import set_user_lang, get_user_lang, DEFAULT_LANG
        ctx = make_context("uz")
        set_user_lang(ctx, "fr")  # Noto'g'ri til
        assert get_user_lang(ctx) == DEFAULT_LANG

    def test_set_all_supported_langs(self):
        from app.bot.i18n import set_user_lang, get_user_lang, SUPPORTED_LANGS
        for lang in SUPPORTED_LANGS:
            ctx = make_context("uz")
            set_user_lang(ctx, lang)
            assert get_user_lang(ctx) == lang


class TestLanguageKeyboard:
    """Til tanlash keyboard testi."""

    def test_language_keyboard_has_all_langs(self):
        from app.bot.i18n import get_language_keyboard, SUPPORTED_LANGS
        keyboard = get_language_keyboard()
        # InlineKeyboardMarkup.inline_keyboard - qatorlar
        all_callbacks = [
            btn.callback_data
            for row in keyboard.inline_keyboard
            for btn in row
        ]
        for lang in SUPPORTED_LANGS:
            assert f"lang_{lang}" in all_callbacks, f"lang_{lang} keyboard da yo'q"

    def test_language_keyboard_button_count(self):
        from app.bot.i18n import get_language_keyboard, SUPPORTED_LANGS
        keyboard = get_language_keyboard()
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == len(SUPPORTED_LANGS)


class TestMainKeyboardLocalization:
    """get_main_keyboard() lokalizatsiya testlari."""

    def test_main_keyboard_uz(self):
        from app.bot.handlers import get_main_keyboard
        kb = get_main_keyboard("uz")
        all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("Murojaat" in t for t in all_texts)

    def test_main_keyboard_ru(self):
        from app.bot.handlers import get_main_keyboard
        kb = get_main_keyboard("ru")
        all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("обращение" in t.lower() or "Отправить" in t for t in all_texts)

    def test_main_keyboard_en(self):
        from app.bot.handlers import get_main_keyboard
        kb = get_main_keyboard("en")
        all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("report" in t.lower() or "Submit" in t for t in all_texts)

    def test_main_keyboard_callback_data_unchanged(self):
        """Callback data til o'zgarmasa ham bir xil bo'lishi kerak."""
        from app.bot.handlers import get_main_keyboard
        kb_uz = get_main_keyboard("uz")
        kb_ru = get_main_keyboard("ru")
        callbacks_uz = {btn.callback_data for row in kb_uz.inline_keyboard for btn in row}
        callbacks_ru = {btn.callback_data for row in kb_ru.inline_keyboard for btn in row}
        assert callbacks_uz == callbacks_ru, "Callback data'lar bir xil bo'lishi kerak"

