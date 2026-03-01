"""
Cases API unit testlari.
- Murojaatlar ro'yxati
- Murojaat detail
- Status o'zgartirish
- Izoh qo'shish
- Fayl yuklab olish
"""
import pytest
import uuid
import base64
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


def make_test_case(status="new", category="corruption"):
    """Test uchun Case ob'ekti yaratadi."""
    from app.core.security import encrypt_text
    from app.models import Case, CaseStatus, CaseCategory, CasePriority
    case = MagicMock(spec=Case)
    case.id = uuid.uuid4()
    case.external_id = f"CASE-20260301-00001"
    case.status = CaseStatus(status)
    case.category = CaseCategory(category)
    case.priority = CasePriority.HIGH
    case.title = "Test murojaat"
    case.is_anonymous = True
    case.created_at = datetime.now(timezone.utc)
    case.updated_at = datetime.now(timezone.utc)
    case.closed_at = None
    case.due_at = None
    case.assigned_to = None
    case.attachments = []
    case.comments = []
    case.assignee = None
    case.description_encrypted = encrypt_text("Test tavsif")
    return case


class TestCasesAPI:
    """Cases API endpointlari uchun testlar."""

    def test_decrypt_case_returns_correct_fields(self):
        """decrypt_case funksiyasi to'g'ri maydonlarni qaytarishi kerak."""
        from app.api.v1.cases import decrypt_case
        case = make_test_case()
        result = decrypt_case(case)
        assert "id" in result
        assert "external_id" in result
        assert "status" in result
        assert "category" in result
        assert "priority" in result
        assert "is_anonymous" in result

    def test_case_status_values(self):
        """CaseStatus enum barcha kerakli qiymatlarni o'z ichiga olishi kerak."""
        from app.models import CaseStatus
        statuses = [s.value for s in CaseStatus]
        assert "new" in statuses
        assert "in_progress" in statuses
        assert "needs_info" in statuses
        assert "completed" in statuses
        assert "rejected" in statuses
        assert "archived" in statuses

    def test_case_category_values(self):
        """CaseCategory enum barcha kerakli kategoriyalarni o'z ichiga olishi kerak."""
        from app.models import CaseCategory
        categories = [c.value for c in CaseCategory]
        assert "corruption" in categories
        assert "fraud" in categories
        assert "conflict_of_interest" in categories
        assert "safety" in categories
        assert "discrimination" in categories
        assert "procurement" in categories
        assert "other" in categories

    def test_case_priority_values(self):
        from app.models import CasePriority
        priorities = [p.value for p in CasePriority]
        assert "critical" in priorities
        assert "high" in priorities
        assert "medium" in priorities
        assert "low" in priorities

    def test_encrypt_decrypt_description(self):
        """Murojaat tavsifi shifrlangan/deshifrlangan holda mos kelishi kerak."""
        from app.core.security import encrypt_text, decrypt_text
        original = "Bu korrupsiya haqida murojaat tavsifi"
        encrypted = encrypt_text(original)
        assert decrypt_text(encrypted) == original

    def test_user_role_access_levels(self):
        """Rol darajalari to'g'ri tartibda bo'lishi kerak."""
        from app.models import UserRole
        roles = [r.value for r in UserRole]
        assert "viewer" in roles
        assert "investigator" in roles
        assert "admin" in roles

    def test_audit_action_values(self):
        """AuditAction barcha kerakli harakatlarni o'z ichiga olishi kerak."""
        from app.models import AuditAction
        actions = [a.value for a in AuditAction]
        assert "login" in actions
        assert "case_view" in actions
        assert "case_update" in actions
        assert "case_assign" in actions
        assert "case_comment" in actions
        assert "case_export" in actions
        assert "attachment_download" in actions

