"""
Storage service unit testlari.
- Fayl validatsiyasi (MIME, extension, hajm)
- Fayl nomi tozalash
- ClamAV scan (mock)
"""
import pytest
import io
from unittest.mock import AsyncMock, patch, MagicMock
import base64
import os


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


# ── validate_file testlari ────────────────────────────────────────────────────

class TestValidateFile:
    def test_valid_pdf(self):
        from app.services.storage import validate_file
        validate_file("report.pdf", "application/pdf", 1024 * 1024)  # 1MB

    def test_valid_image(self):
        from app.services.storage import validate_file
        validate_file("photo.jpg", "image/jpeg", 500 * 1024)

    def test_blocked_exe_extension(self):
        from app.services.storage import validate_file
        with pytest.raises(ValueError, match="kengaytmali fayllar"):
            validate_file("virus.exe", "application/octet-stream", 1024)

    def test_blocked_bat_extension(self):
        from app.services.storage import validate_file
        with pytest.raises(ValueError, match="kengaytmali fayllar"):
            validate_file("script.bat", "text/plain", 100)

    def test_blocked_extensions_list(self):
        from app.services.storage import validate_file, BLOCKED_EXTENSIONS
        for ext in [".exe", ".bat", ".cmd", ".sh", ".ps1", ".dll"]:
            with pytest.raises(ValueError):
                validate_file(f"file{ext}", "application/octet-stream", 100)

    def test_file_too_large(self):
        from app.services.storage import validate_file
        from app.core.config import settings
        too_large = (settings.MAX_FILE_SIZE_MB + 1) * 1024 * 1024
        with pytest.raises(ValueError, match="hajmi"):
            validate_file("big.pdf", "application/pdf", too_large)

    def test_unknown_mime_type_with_valid_extension(self):
        """Noma'lum MIME lekin kengaytmadan .pdf taxmin qilinadi."""
        from app.services.storage import validate_file
        validate_file("doc.pdf", "application/octet-stream", 1024)

    def test_truly_unknown_mime(self):
        """Ne kengaytma, ne MIME — qabul qilinmasligi kerak."""
        from app.services.storage import validate_file
        with pytest.raises(ValueError, match="turdagi fayllar"):
            validate_file("file.xyz123", "application/x-unknown-custom-type", 1024)


# ── sanitize_filename testlari ────────────────────────────────────────────────

class TestSanitizeFilename:
    def test_normal_filename(self):
        from app.services.storage import sanitize_filename
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_removes_dangerous_chars(self):
        from app.services.storage import sanitize_filename
        result = sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert ".." not in result
        assert result != ""  # fallback ham bo'lmasligi kerak (lekin attachment bo'lishi mumkin)

    def test_empty_filename_fallback(self):
        from app.services.storage import sanitize_filename
        assert sanitize_filename("") == "attachment"
        assert sanitize_filename("!!!@@@###") == "attachment"

    def test_unicode_filename(self):
        from app.services.storage import sanitize_filename
        result = sanitize_filename("fayl nomi.pdf")
        assert "fayl" in result


# ── ClamAV scan testlari (mock) ───────────────────────────────────────────────

class TestClamAVScan:
    @pytest.mark.asyncio
    async def test_scan_skipped_when_disabled(self):
        """CLAMAV_ENABLED=False bo'lsa — scan o'tkazib yuboriladi."""
        from app.services import storage
        from app.core.config import settings
        original = settings.CLAMAV_ENABLED
        settings.CLAMAV_ENABLED = False
        try:
            await storage.scan_with_clamav(b"test data", "test.pdf")
        finally:
            settings.CLAMAV_ENABLED = original

    @pytest.mark.asyncio
    async def test_scan_skipped_logs_warning(self):
        """CLAMAV_ENABLED=False bo'lsa — WARNING log yozilishi kerak."""
        import logging
        from app.services import storage
        from app.core.config import settings
        original = settings.CLAMAV_ENABLED
        settings.CLAMAV_ENABLED = False
        try:
            with patch.object(storage.logger, "warning") as mock_warn:
                await storage.scan_with_clamav(b"data", "file.pdf")
                mock_warn.assert_called_once()
                warn_msg = mock_warn.call_args[0][0]
                assert "ClamAV" in warn_msg
                assert "O'CHIRILGAN" in warn_msg or "CLAMAV_ENABLED" in warn_msg
        finally:
            settings.CLAMAV_ENABLED = original

    @pytest.mark.asyncio
    async def test_scan_virus_found_raises(self):
        """ClamAV virus topsa ValueError chiqarishi kerak."""
        from app.services import storage

        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"stream: Eicar-Test-Signature FOUND\n")
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "clamav"
            mock_settings.CLAMAV_PORT = 3310
            with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
                with pytest.raises(ValueError, match="zararli"):
                    await storage.scan_with_clamav(b"EICAR test", "eicar.txt")

    @pytest.mark.asyncio
    async def test_scan_clean_file_passes(self):
        """Toza fayl scan dan o'tishi kerak."""
        from app.services import storage

        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"stream: OK\n")
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "clamav"
            mock_settings.CLAMAV_PORT = 3310
            with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
                await storage.scan_with_clamav(b"clean file content", "clean.pdf")


class TestClamavHealth:
    """ClamAV health check testlari."""

    @pytest.mark.asyncio
    async def test_health_disabled_returns_warning(self):
        """ClamAV o'chirilganda health 'disabled' qaytarishi kerak."""
        from app.services.storage import check_clamav_health
        from app.core.config import settings
        original = settings.CLAMAV_ENABLED
        settings.CLAMAV_ENABLED = False
        try:
            result = await check_clamav_health()
            assert result["enabled"] is False
            assert result["status"] == "disabled"
            assert "warning" in result
        finally:
            settings.CLAMAV_ENABLED = original

    @pytest.mark.asyncio
    async def test_health_enabled_ok_when_pong(self):
        """ClamAV yoqilgan va PONG javob kelsa — status 'ok' bo'lishi kerak."""
        from app.services.storage import check_clamav_health

        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"PONG\0")
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "clamav"
            mock_settings.CLAMAV_PORT = 3310
            with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
                result = await check_clamav_health()
        assert result["enabled"] is True
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_enabled_error_when_unreachable(self):
        """ClamAV ulanmasa — status 'error' bo'lishi kerak."""
        from app.services.storage import check_clamav_health

        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "clamav"
            mock_settings.CLAMAV_PORT = 3310
            with patch("asyncio.open_connection", side_effect=ConnectionRefusedError("refused")):
                result = await check_clamav_health()
        assert result["enabled"] is True
        assert result["status"] == "error"
        assert "error" in result

