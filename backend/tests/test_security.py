"""
Xavfsizlik funksiyalari uchun unit testlar.
- AES-256-GCM shifrlash/deshifrlash
- JWT token yaratish/tekshirish
- Parol hash/verify
- TOTP secret yaratish
"""
import pytest
import base64
import os
from datetime import timedelta
from unittest.mock import patch


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """Test uchun minimal .env o'zgaruvchilari."""
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


# ── AES-256-GCM shifrlash testlari ───────────────────────────────────────────

class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Shifrlangan matn deshifrlanganda asl matn qaytishi kerak."""
        from app.core.security import encrypt_text, decrypt_text
        original = "Bu maxfiy ma'lumot: murojaat tavsifi"
        encrypted = encrypt_text(original)
        assert encrypted != original
        assert decrypt_text(encrypted) == original

    def test_encrypt_produces_different_output_each_time(self):
        """Har safar yangi nonce ishlatilgani uchun natija har xil bo'lishi kerak."""
        from app.core.security import encrypt_text
        text = "xuddi shu matn"
        enc1 = encrypt_text(text)
        enc2 = encrypt_text(text)
        assert enc1 != enc2   # nonce farqi

    def test_encrypt_empty_string(self):
        from app.core.security import encrypt_text, decrypt_text
        assert decrypt_text(encrypt_text("")) == ""

    def test_encrypt_unicode(self):
        from app.core.security import encrypt_text, decrypt_text
        text = "O'zbek tili: ✅ 🔒 korrupsiya haqida murojaat"
        assert decrypt_text(encrypt_text(text)) == text

    def test_encrypt_long_text(self):
        from app.core.security import encrypt_text, decrypt_text
        text = "A" * 10000
        assert decrypt_text(encrypt_text(text)) == text

    def test_decrypt_invalid_raises(self):
        from app.core.security import decrypt_text
        with pytest.raises(Exception):
            decrypt_text("bu_noto'g'ri_shifrlangan_matn")


# ── JWT token testlari ────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode_token(self):
        from app.core.security import create_access_token, decode_token
        data = {"sub": "user-uuid-123", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-uuid-123"
        assert decoded["role"] == "admin"

    def test_expired_token_returns_none(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "test"}, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_invalid_token_returns_none(self):
        from app.core.security import decode_token
        assert decode_token("bu.yaroqsiz.token") is None

    def test_token_contains_exp(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "test"})
        decoded = decode_token(token)
        assert "exp" in decoded


# ── Parol hash testlari ───────────────────────────────────────────────────────

class TestPassword:
    def test_hash_and_verify(self):
        from app.core.security import hash_password, verify_password
        password = "MyStr0ng@Pass!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_same_password_different_hashes(self):
        """bcrypt salt tufayli har xil hash bo'lishi kerak."""
        from app.core.security import hash_password
        p = "same_password"
        assert hash_password(p) != hash_password(p)


# ── TOTP testlari ─────────────────────────────────────────────────────────────

class TestTOTP:
    def test_generate_totp_secret(self):
        from app.core.security import generate_totp_secret
        secret = generate_totp_secret()
        assert len(secret) >= 16
        assert secret.isupper() or secret.isalnum()

    def test_totp_verify_valid(self):
        import pyotp
        from app.core.security import generate_totp_secret
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        # verify_totp funksiyasi mavjud bo'lsa
        try:
            from app.core.security import verify_totp
            assert verify_totp(secret, current_code)
        except ImportError:
            pytest.skip("verify_totp not implemented yet")

class TestSeparateEncryptionKeys:
    """Case va Comment uchun alohida kalitlar testlari."""
    def test_fallback_to_main_key_when_no_separate_keys(self):
        """Alohida kalitlar yo''q bo''lsa ENCRYPTION_KEY ishlatilishi kerak."""
        from app.core.security import (
            encrypt_case_content, decrypt_case_content,
            encrypt_comment_content, decrypt_comment_content,
        )
        text = "Oddiy matn"
        case_enc = encrypt_case_content(text)
        comment_enc = encrypt_comment_content(text)
        assert decrypt_case_content(case_enc) == text
        assert decrypt_comment_content(comment_enc) == text
    def test_case_comment_different_functions_exist(self):
        """Alohida funksiyalar mavjud bo''lishi kerak."""
        from app.core.security import (
            encrypt_case_content, decrypt_case_content,
            encrypt_comment_content, decrypt_comment_content,
        )
        assert callable(encrypt_case_content)
        assert callable(decrypt_case_content)
        assert callable(encrypt_comment_content)
        assert callable(decrypt_comment_content)
    def test_case_roundtrip(self):
        """encrypt_case_content ? decrypt_case_content roundtrip."""
        from app.core.security import encrypt_case_content, decrypt_case_content
        text = "Murojaat: Korrupsiya haqida"
        assert decrypt_case_content(encrypt_case_content(text)) == text
    def test_comment_roundtrip(self):
        """encrypt_comment_content ? decrypt_comment_content roundtrip."""
        from app.core.security import encrypt_comment_content, decrypt_comment_content
        text = "Admin izohi: ko''rib chiqildi"
        assert decrypt_comment_content(encrypt_comment_content(text)) == text
