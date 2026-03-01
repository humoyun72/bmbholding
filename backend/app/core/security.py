from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import pyotp
import qrcode
import io
import base64
from app.core.config import settings


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# AES-256-GCM encryption for sensitive fields
def _encrypt_with_key(plaintext: str, key_bytes: bytes) -> str:
    """Berilgan kalit bilan shifrlaydi, base64 qaytaradi."""
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def _decrypt_with_key(encrypted: str, key_bytes: bytes) -> str:
    """Berilgan kalit bilan ochadi."""
    combined = base64.b64decode(encrypted.encode("utf-8"))
    nonce = combined[:12]
    ciphertext = combined[12:]
    return AESGCM(key_bytes).decrypt(nonce, ciphertext, None).decode("utf-8")


def encrypt_text(plaintext: str) -> str:
    """Umumiy shifrlash — asosiy ENCRYPTION_KEY ishlatadi (backwards compat)."""
    return _encrypt_with_key(plaintext, settings.encryption_key_bytes)


def decrypt_text(encrypted: str) -> str:
    """Umumiy ochish — asosiy ENCRYPTION_KEY ishlatadi (backwards compat)."""
    return _decrypt_with_key(encrypted, settings.encryption_key_bytes)


def encrypt_case_content(plaintext: str) -> str:
    """
    Case.description_encrypted uchun shifrlash.
    CASE_ENCRYPTION_KEY berilgan bo'lsa uni, aks holda ENCRYPTION_KEY ishlatadi.
    """
    return _encrypt_with_key(plaintext, settings.case_encryption_key_bytes)


def decrypt_case_content(encrypted: str) -> str:
    """
    Case.description_encrypted uchun ochish.
    Avval CASE_ENCRYPTION_KEY bilan urinadi, xato bo'lsa ENCRYPTION_KEY bilan.
    (Kalit rotatsiyasi paytida backwards compatibility uchun.)
    """
    # Asosiy kalit bilan urinish
    try:
        return _decrypt_with_key(encrypted, settings.case_encryption_key_bytes)
    except Exception:
        # Fallback: asosiy ENCRYPTION_KEY bilan (migratsiya davri uchun)
        if settings.CASE_ENCRYPTION_KEY:
            return _decrypt_with_key(encrypted, settings.encryption_key_bytes)
        raise


def encrypt_comment_content(plaintext: str) -> str:
    """
    CaseComment.content_encrypted uchun shifrlash.
    COMMENT_ENCRYPTION_KEY berilgan bo'lsa uni, aks holda ENCRYPTION_KEY ishlatadi.
    """
    return _encrypt_with_key(plaintext, settings.comment_encryption_key_bytes)


def decrypt_comment_content(encrypted: str) -> str:
    """
    CaseComment.content_encrypted uchun ochish.
    Avval COMMENT_ENCRYPTION_KEY bilan urinadi, xato bo'lsa ENCRYPTION_KEY bilan.
    """
    try:
        return _decrypt_with_key(encrypted, settings.comment_encryption_key_bytes)
    except Exception:
        if settings.COMMENT_ENCRYPTION_KEY:
            return _decrypt_with_key(encrypted, settings.encryption_key_bytes)
        raise


# TOTP for 2FA
def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=settings.APP_NAME
    )


def generate_qr_code(totp_uri: str) -> str:
    """Generate QR code as base64 PNG"""
    img = qrcode.make(totp_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
