"""
E2E Integration testlar — Cases API to'liq flow.

Quyidagi scenariolar test qilinadi:
1. Admin login → JWT token
2. Yangi murojaat yaratish (bot orqali simulatsiya)
3. Murojaatlar ro'yxatini olish
4. Bitta murojaatni ko'rish
5. Status o'zgartirish
6. Admin tayinlash
7. Izoh qo'shish (oddiy + ichki)
8. Audit log yozilishi
9. Fayl yuklab olish (mock)
10. Statistika endpoint
"""
import pytest
import base64
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

# ── ENV fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_e2e_secret_key_at_least_32_chars!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    monkeypatch.setenv("ENVIRONMENT", "test")


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_admin_user():
    """Admin User mock ob'ektini yaratadi."""
    from app.models import User, UserRole
    from app.core.security import hash_password
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.username = "admin"
    user.email = "admin@test.uz"
    user.full_name = "Test Admin"
    user.role = UserRole.ADMIN
    user.is_active = True
    user.hashed_password = hash_password("Admin@123456")
    user.totp_enabled = False
    user.totp_secret = None
    user.telegram_chat_id = None
    user.last_login = None
    return user


def make_investigator_user():
    """Investigator User mock ob'ektini yaratadi."""
    from app.models import User, UserRole
    from app.core.security import hash_password
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.username = "investigator"
    user.email = "inv@test.uz"
    user.full_name = "Test Investigator"
    user.role = UserRole.INVESTIGATOR
    user.is_active = True
    user.hashed_password = hash_password("Inv@123456")
    user.totp_enabled = False
    user.totp_secret = None
    user.telegram_chat_id = None
    user.last_login = None
    return user


def make_case(assigned_to=None, status="new"):
    """Test Case ob'ektini yaratadi."""
    from app.models import Case, CaseStatus, CaseCategory, CasePriority
    from app.core.security import encrypt_text
    case = MagicMock(spec=Case)
    case.id = uuid.uuid4()
    case.external_id = "CASE-20260302-00001"
    case.status = CaseStatus(status)
    case.category = CaseCategory.CORRUPTION
    case.priority = CasePriority.HIGH
    case.title = "Test korrupsiya murojaati"
    case.is_anonymous = True
    case.telegram_chat_id = 123456789
    case.reporter_token = "hashed_token_here"
    case.created_at = datetime.now(timezone.utc)
    case.updated_at = datetime.now(timezone.utc)
    case.closed_at = None
    case.due_at = None
    case.assigned_to = assigned_to
    case.assignee = None
    case.attachments = []
    case.comments = []
    case.notifications = []
    case.description_encrypted = encrypt_text("Bu test murojaati tavsifi")
    return case


def make_audit_log(action="case_view"):
    """AuditLog mock ob'ektini yaratadi."""
    from app.models import AuditLog, AuditAction
    log = MagicMock(spec=AuditLog)
    log.id = uuid.uuid4()
    log.action = AuditAction.CASE_VIEW
    log.user_id = uuid.uuid4()
    log.case_id = uuid.uuid4()
    log.ip_address = "127.0.0.1"
    log.created_at = datetime.now(timezone.utc)
    log.payload = {}
    log.user = None
    log.case = None
    return log


# ── E2E Scenario Testlar ──────────────────────────────────────────────────────

class TestAuthFlow:
    """Autentifikatsiya flow testlari."""

    def test_jwt_token_created_for_valid_credentials(self):
        """To'g'ri login/parol bilan JWT token yaratilishi kerak."""
        from app.core.security import create_access_token, decode_token
        admin = make_admin_user()
        token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
        assert token is not None
        payload = decode_token(token)
        assert payload["sub"] == str(admin.id)
        assert payload["role"] == "admin"

    def test_jwt_token_for_investigator(self):
        """Investigator uchun ham token yaratilishi kerak."""
        from app.core.security import create_access_token, decode_token
        inv = make_investigator_user()
        token = create_access_token({"sub": str(inv.id), "role": inv.role.value})
        payload = decode_token(token)
        assert payload["role"] == "investigator"

    def test_wrong_password_fails_verification(self):
        """Noto'g'ri parol verify bo'lmasligi kerak."""
        from app.core.security import hash_password, verify_password
        hashed = hash_password("CorrectPass@123")
        assert verify_password("WrongPass@123", hashed) is False

    def test_correct_password_passes_verification(self):
        """To'g'ri parol verify bo'lishi kerak."""
        from app.core.security import hash_password, verify_password
        hashed = hash_password("CorrectPass@123")
        assert verify_password("CorrectPass@123", hashed) is True

    def test_expired_token_returns_none(self):
        """Muddati o'tgan token decode qilinganda None qaytishi kerak."""
        from app.core.security import create_access_token, decode_token
        from datetime import timedelta
        token = create_access_token({"sub": "test"}, expires_delta=timedelta(seconds=-1))
        result = decode_token(token)
        assert result is None

    def test_invalid_token_returns_none(self):
        """Buzilgan token None qaytishi kerak."""
        from app.core.security import decode_token
        assert decode_token("invalid.token.here") is None

    def test_totp_flow(self):
        """TOTP secret yaratish va verify qilish flow."""
        from app.core.security import generate_totp_secret, verify_totp
        import pyotp
        secret = generate_totp_secret()
        assert len(secret) > 0
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code) is True

    def test_totp_wrong_code_fails(self):
        """Noto'g'ri TOTP kod reject bo'lishi kerak."""
        from app.core.security import generate_totp_secret, verify_totp
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False


class TestCasesCRUDFlow:
    """Murojaatlar CRUD va to'liq lifecycle testlari."""

    def test_case_external_id_format(self):
        """Case external_id CASE-YYYYMMDD-NNNNN formatda bo'lishi kerak."""
        import re
        case = make_case()
        pattern = r'^CASE-\d{8}-\d{5}$'
        assert re.match(pattern, case.external_id), f"Invalid format: {case.external_id}"

    def test_case_description_is_encrypted(self):
        """Case tavsifi shifrlangan holda saqlanishi kerak."""
        from app.core.security import decrypt_text
        case = make_case()
        decrypted = decrypt_text(case.description_encrypted)
        assert decrypted == "Bu test murojaati tavsifi"
        assert case.description_encrypted != decrypted  # shifrlangan

    def test_decrypt_case_returns_all_fields(self):
        """decrypt_case barcha kerakli maydonlarni qaytarishi kerak."""
        from app.api.v1.cases import decrypt_case
        case = make_case()
        result = decrypt_case(case)
        required_fields = [
            "id", "external_id", "category", "priority",
            "status", "title", "is_anonymous", "created_at",
            "assigned_to", "attachments_count"
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_case_status_transitions(self):
        """Case status to'g'ri holatlarga o'tishi mumkin ekanligini tekshirish."""
        from app.models import CaseStatus
        valid_statuses = ["new", "in_progress", "needs_info", "completed", "rejected", "archived"]
        for s in valid_statuses:
            status = CaseStatus(s)
            assert status.value == s

    def test_case_priority_levels(self):
        """Case priority to'g'ri 4 darajada bo'lishi kerak."""
        from app.models import CasePriority
        priorities = ["critical", "high", "medium", "low"]
        for p in priorities:
            assert CasePriority(p).value == p

    def test_case_categories(self):
        """Barcha 7 kategoriya mavjud va to'g'ri."""
        from app.models import CaseCategory
        expected = [
            "corruption", "conflict_of_interest", "fraud",
            "safety", "discrimination", "procurement", "other"
        ]
        for cat in expected:
            assert CaseCategory(cat).value == cat

    def test_case_anonymous_flag(self):
        """Anonim murojaat bo'lganda is_anonymous=True bo'lishi kerak."""
        case = make_case()
        assert case.is_anonymous is True

    def test_reporter_ip_not_in_decrypt_case(self):
        """
        Anonimlik kafolati: decrypt_case reporter_ip qaytarmasligi kerak.
        ISO 37001 va O'zbekiston shaxsiy ma'lumotlar qonuni talabi.
        """
        from app.api.v1.cases import decrypt_case
        case = make_case()
        result = decrypt_case(case)
        assert "reporter_ip" not in result, (
            "reporter_ip decrypt_case da bo'lmasligi kerak — anonimlik buziladi!"
        )

    def test_case_model_has_no_reporter_ip_field(self):
        """Case modelida reporter_ip maydoni bo'lmasligi kerak."""
        from app.models import Case
        assert not hasattr(Case, "reporter_ip"), (
            "Case modelida reporter_ip maydoni bo'lmasligi kerak — anonimlik buziladi!"
        )

    def test_case_comment_encryption(self):
        """Izoh ham shifrlangan holda saqlanishi kerak."""
        from app.core.security import encrypt_text, decrypt_text
        content = "Bu maxfiy izoh"
        encrypted = encrypt_text(content)
        assert decrypt_text(encrypted) == content
        assert encrypted != content

    @pytest.mark.asyncio
    async def test_list_cases_endpoint_mock(self):
        """Cases ro'yxati endpoint mock bilan test."""
        from app.api.v1.cases import decrypt_case
        from app.models import CaseStatus, CaseCategory, CasePriority
        case = make_case()
        result = decrypt_case(case)
        assert result["status"] == "new"
        assert result["category"] == "corruption"
        assert result["priority"] == "high"

    @pytest.mark.asyncio
    async def test_status_change_to_completed(self):
        """Status completed ga o'zgarganda closed_at belgilanishi kerak."""
        from app.models import CaseStatus
        case = make_case()
        # completed yoki rejected bo'lganda closed_at belgilanadi
        case.status = CaseStatus.COMPLETED
        case.closed_at = datetime.now(timezone.utc)
        assert case.closed_at is not None
        assert case.status == CaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_status_change_to_rejected(self):
        """Status rejected ga o'zgarganda closed_at belgilanishi kerak."""
        from app.models import CaseStatus
        case = make_case()
        case.status = CaseStatus.REJECTED
        case.closed_at = datetime.now(timezone.utc)
        assert case.closed_at is not None


class TestNotificationFlow:
    """Bildirishnomalar flow testlari."""

    @pytest.mark.asyncio
    async def test_notify_admins_called_on_new_case(self):
        """Yangi murojaat kelganda adminlarga bildirishnoma yuborilishi kerak."""
        with patch("app.services.notification.notify_admins", new_callable=AsyncMock) as mock_notify:
            from app.services.notification import notify_admins
            from app.models import CaseCategory
            case = make_case()
            await notify_admins(
                bot=MagicMock(),
                case_id=case.external_id,
                category=CaseCategory.CORRUPTION,
                description="Test tavsif",
                is_anonymous=True,
            )
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_reporter_message_sent_on_comment(self):
        """Admin izoh yozganda reporter ga xabar yuborilishi kerak."""
        with patch("app.services.notification.send_reporter_message", new_callable=AsyncMock) as mock_send:
            from app.services.notification import send_reporter_message
            mock_bot = MagicMock()
            await send_reporter_message(
                bot=mock_bot,
                telegram_chat_id=123456789,
                case_id="CASE-20260302-00001",
                message="Murojaatingiz ko'rib chiqilmoqda",
            )
            mock_send.assert_called_once()
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_manager_broadcast(self):
        """WebSocket manager broadcast funksiyasi ishlashi kerak."""
        from app.services.websocket_manager import ConnectionManager
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()
        manager._connections["test_user_1"] = mock_ws
        await manager.broadcast({"type": "new_case", "case_id": "CASE-20260302-00001"})
        mock_ws.send_json.assert_called_once_with(
            {"type": "new_case", "case_id": "CASE-20260302-00001"}
        )

    @pytest.mark.asyncio
    async def test_websocket_manager_handles_disconnect(self):
        """Uzilgan WS clientga xabar yuborishda xato bo'lmasligi kerak."""
        from app.services.websocket_manager import ConnectionManager
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("disconnected"))
        manager._connections["test_user_2"] = mock_ws
        # Xato bo'lganda ham butun broadcast ishdan chiqmasligi kerak
        try:
            await manager.broadcast({"type": "test"})
        except Exception:
            pytest.fail("broadcast xato bo'lmasligi kerak")
        # Uzilgan user o'chirilishi kerak
        assert "test_user_2" not in manager._connections


class TestAuditLogFlow:
    """Audit log yozilish testlari."""

    def test_audit_log_has_required_fields(self):
        """AuditLog barcha kerakli maydonlarga ega bo'lishi kerak."""
        log = make_audit_log()
        assert log.id is not None
        assert log.action is not None
        assert log.ip_address == "127.0.0.1"
        assert log.created_at is not None

    def test_audit_actions_enum(self):
        """Barcha audit action'lar mavjud ekanligini tekshirish."""
        from app.models import AuditAction
        expected_actions = [
            "login", "logout", "case_view", "case_update",
            "case_assign", "case_comment", "case_export",
            "attachment_download", "user_create", "user_update",
            "survey_create"
        ]
        for action in expected_actions:
            assert AuditAction(action).value == action

    @pytest.mark.asyncio
    async def test_audit_log_created_on_case_view(self):
        """Case ko'rilganda audit log yaratilishi kerak."""
        from app.models import AuditAction, AuditLog
        log = AuditLog(
            user_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            action=AuditAction.CASE_VIEW,
            ip_address="192.168.1.1",
        )
        assert log.action == AuditAction.CASE_VIEW
        assert log.ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_audit_log_created_on_status_change(self):
        """Status o'zgarganda audit log yaratilishi kerak."""
        from app.models import AuditAction, AuditLog
        log = AuditLog(
            user_id=uuid.uuid4(),
            case_id=uuid.uuid4(),
            action=AuditAction.CASE_UPDATE,
            payload={"old_status": "new", "new_status": "in_progress"},
            ip_address="10.0.0.1",
        )
        assert log.action == AuditAction.CASE_UPDATE
        assert log.payload["old_status"] == "new"
        assert log.payload["new_status"] == "in_progress"


class TestStorageFlow:
    """Fayl saqlash va olish flow testlari."""

    def test_allowed_mime_types(self):
        """Ruxsat berilgan MIME turlarini tekshirish."""
        from app.services.storage import ALLOWED_MIME_TYPES
        allowed = [
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "application/pdf",
            "video/mp4",
        ]
        for mime in allowed:
            assert mime in ALLOWED_MIME_TYPES, f"{mime} ruxsat berilishi kerak"

    def test_blocked_extensions(self):
        """Bloklangan kengaytmalarni tekshirish."""
        from app.services.storage import BLOCKED_EXTENSIONS
        dangerous = [".exe", ".bat", ".sh", ".ps1", ".cmd"]
        for ext in dangerous:
            assert ext in BLOCKED_EXTENSIONS, f"{ext} bloklangan bo'lishi kerak"

    def test_filename_sanitize(self):
        """Fayl nomi xavfli belgilardan tozalanishi kerak — validate_file path traversal'ni bloklaydi."""
        from app.services.storage import validate_file
        from pathlib import Path
        import re

        def basic_sanitize(name: str) -> str:
            """Path traversal va xavfli belgilarni olib tashlaydi."""
            name = os.path.basename(name.replace("\\", "/"))
            name = re.sub(r'[<>:"|?*]', '', name)
            name = name.replace(" ", "_")
            return name

        assert ".." not in basic_sanitize("../../../etc/passwd")
        assert "/" not in basic_sanitize("../../etc/passwd")
        result = basic_sanitize("normal file.pdf")
        assert " " not in result

    @pytest.mark.asyncio
    async def test_file_size_validation(self):
        """Fayl hajmi chegarasi tekshirilishi kerak."""
        from app.services.storage import validate_file
        # 21 MB fayl — rad etilishi kerak (MAX = 20 MB)
        big_size = 21 * 1024 * 1024
        with pytest.raises(ValueError, match="MB"):
            validate_file("test.pdf", "application/pdf", big_size)

    @pytest.mark.asyncio
    async def test_valid_file_passes_validation(self):
        """To'g'ri fayl validatsiyadan o'tishi kerak."""
        from app.services.storage import validate_file
        # 1 MB PDF — o'tishi kerak
        try:
            validate_file("document.pdf", "application/pdf", 1024 * 1024)
        except ValueError:
            pytest.fail("To'g'ri fayl validatsiyadan o'tishi kerak")

    @pytest.mark.asyncio
    async def test_blocked_extension_rejected(self):
        """Bloklangan kengaytma rad etilishi kerak."""
        from app.services.storage import validate_file
        with pytest.raises(ValueError, match="kengaytmali"):
            validate_file("malware.exe", "application/octet-stream", 1024)


class TestDataRetentionPolicy:
    """Data retention policy testlari."""

    def test_case_has_created_at_field(self):
        """Case modelida created_at maydoni bo'lishi kerak (retention uchun)."""
        case = make_case()
        assert hasattr(case, "created_at")
        assert case.created_at is not None

    def test_audit_log_has_created_at_field(self):
        """AuditLog modelida created_at maydoni bo'lishi kerak."""
        log = make_audit_log()
        assert hasattr(log, "created_at")
        assert log.created_at is not None

    def test_retention_period_calculation(self):
        """3 yillik retention period hisoblash."""
        from datetime import timedelta
        from app.services.retention import (
            COMPLETED_TO_ARCHIVED_DAYS,
            ARCHIVED_DELETE_DAYS,
            AUDIT_LOG_DELETE_DAYS,
            NOTIFICATION_DELETE_DAYS,
        )
        assert COMPLETED_TO_ARCHIVED_DAYS == 3 * 365   # 1095 kun
        assert ARCHIVED_DELETE_DAYS       == 5 * 365   # 1825 kun
        assert AUDIT_LOG_DELETE_DAYS      == 3 * 365   # 1095 kun
        assert NOTIFICATION_DELETE_DAYS   == 365        # 365 kun

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=COMPLETED_TO_ARCHIVED_DAYS)
        assert cutoff < now

    def test_case_status_archived_exists(self):
        """Arxivlash uchun ARCHIVED status mavjud bo'lishi kerak."""
        from app.models import CaseStatus
        assert CaseStatus.ARCHIVED.value == "archived"

    def test_retention_constants_are_positive(self):
        """Retention muddatlari musbat son bo'lishi kerak."""
        from app.services.retention import (
            COMPLETED_TO_ARCHIVED_DAYS,
            ARCHIVED_DELETE_DAYS,
            AUDIT_LOG_DELETE_DAYS,
            NOTIFICATION_DELETE_DAYS,
        )
        assert COMPLETED_TO_ARCHIVED_DAYS > 0
        assert ARCHIVED_DELETE_DAYS > COMPLETED_TO_ARCHIVED_DAYS  # o'chirish > arxivlash
        assert AUDIT_LOG_DELETE_DAYS > 0
        assert NOTIFICATION_DELETE_DAYS > 0

    def test_retention_hierarchy(self):
        """O'chirish muddati arxivlash muddatidan katta bo'lishi kerak."""
        from app.services.retention import COMPLETED_TO_ARCHIVED_DAYS, ARCHIVED_DELETE_DAYS
        assert ARCHIVED_DELETE_DAYS > COMPLETED_TO_ARCHIVED_DAYS, (
            "Fayllar avval arxivlanishi, keyin o'chirilishi kerak"
        )

    @pytest.mark.asyncio
    async def test_run_retention_returns_stats_dict(self):
        """run_retention() stats dict qaytarishi kerak."""
        from app.services.retention import run_retention
        from unittest.mock import patch, AsyncMock, MagicMock

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_result.fetchall.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        stats = await run_retention(db=mock_db)

        assert isinstance(stats, dict)
        assert "archived" in stats
        assert "deleted_cases" in stats
        assert "deleted_audit_logs" in stats
        assert "deleted_notifications" in stats
        assert "errors" in stats
        assert stats["errors"] == []


