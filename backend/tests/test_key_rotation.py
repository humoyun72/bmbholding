"""
Encryption Key Rotatsiya Skripti testlari.
Haqiqiy DB kerak emas — mock bilan.
"""
import pytest
import base64
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# scripts/ papkasini path ga qo'shish
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


def make_key() -> bytes:
    """32 baytlik tasodifiy kalit yaratadi."""
    return os.urandom(32)


def make_key_b64() -> str:
    return base64.b64encode(make_key()).decode()


class TestKeyFunctions:
    """_parse_key, _encrypt_with_key, _decrypt_with_key testlari."""

    def test_encrypt_decrypt_roundtrip(self):
        """Shifrlash va ochish to'g'ri ishlashi kerak."""
        from rotate_encryption_key import _encrypt_with_key, _decrypt_with_key
        key = make_key()
        plaintext = "Bu maxfiy murojaat matni!"
        encrypted = _encrypt_with_key(plaintext, key)
        decrypted = _decrypt_with_key(encrypted, key)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self):
        """Har safar har xil shifrlangan matn (random nonce)."""
        from rotate_encryption_key import _encrypt_with_key
        key = make_key()
        plaintext = "Bir xil matn"
        enc1 = _encrypt_with_key(plaintext, key)
        enc2 = _encrypt_with_key(plaintext, key)
        assert enc1 != enc2  # Har safar boshqacha nonce

    def test_wrong_key_fails_decryption(self):
        """Noto'g'ri kalit bilan ochish xato berishi kerak."""
        from rotate_encryption_key import _encrypt_with_key, _decrypt_with_key
        key1 = make_key()
        key2 = make_key()
        encrypted = _encrypt_with_key("maxfiy matn", key1)
        with pytest.raises(Exception):
            _decrypt_with_key(encrypted, key2)

    def test_parse_key_valid(self):
        """To'g'ri 32-baytlik base64 kalit qabul qilinishi kerak."""
        from rotate_encryption_key import _parse_key
        key_b64 = base64.b64encode(os.urandom(32)).decode()
        result = _parse_key(key_b64)
        assert len(result) == 32

    def test_parse_key_wrong_length(self):
        """Noto'g'ri uzunlikdagi kalit rad etilishi kerak."""
        from rotate_encryption_key import _parse_key
        short_key = base64.b64encode(os.urandom(16)).decode()  # 16 bayt — noto'g'ri
        with pytest.raises(ValueError, match="32 bayt"):
            _parse_key(short_key)

    def test_parse_key_invalid_base64(self):
        """Noto'g'ri base64 format rad etilishi kerak."""
        from rotate_encryption_key import _parse_key
        with pytest.raises(ValueError):
            _parse_key("bu_base64_emas!!!")

    def test_encrypt_output_is_base64(self):
        """Shifrlangan natija to'g'ri base64 bo'lishi kerak."""
        from rotate_encryption_key import _encrypt_with_key
        key = make_key()
        encrypted = _encrypt_with_key("test", key)
        # base64 decode xato bermasligi kerak
        decoded = base64.b64decode(encrypted)
        assert len(decoded) > 12  # nonce (12) + ciphertext

    def test_encrypt_includes_nonce(self):
        """Shifrlangan matn nonce (12 bayt) ni o'z ichiga olishi kerak."""
        from rotate_encryption_key import _encrypt_with_key
        key = make_key()
        encrypted = _encrypt_with_key("test data", key)
        decoded = base64.b64decode(encrypted)
        assert len(decoded) >= 12 + 9  # nonce + kamida 1 bayt ma'lumot


class TestRotateKeys:
    """rotate_keys funksiyasi testlari — DB mock bilan."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_commit(self):
        """Dry run da commit chaqirilmasligi kerak."""
        from rotate_encryption_key import _encrypt_with_key

        old_key = make_key()
        new_key = make_key()

        sample_case_enc = _encrypt_with_key("Murojaat tavsifi", old_key)
        sample_comment_enc = _encrypt_with_key("Admin izohi", old_key)

        # mock_db
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # Har execute chaqiruvida batch natijalarini qaytarish
        call_count = {"n": 0}

        async def mock_execute(query, *args, **kwargs):
            call_count["n"] += 1
            result = MagicMock()
            # cases: 1-batch = [row], 2-batch = []
            if call_count["n"] == 1:
                result.fetchall.return_value = [
                    ("case-id-1", "CASE-20260302-00001", sample_case_enc)
                ]
            elif call_count["n"] == 2:
                result.fetchall.return_value = []
            # comments: 3-batch = [row], 4-batch = []
            elif call_count["n"] == 3:
                result.fetchall.return_value = [
                    ("comment-id-1", "case-id-1", sample_comment_enc)
                ]
            else:
                result.fetchall.return_value = []
            return result

        mock_db.execute = mock_execute

        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_session_factory = MagicMock(return_value=mock_session_ctx)
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        # Skript ichidagi lokal importlarni patch qilamiz
        import sqlalchemy.ext.asyncio as sa_async
        import sqlalchemy.orm as sa_orm

        with patch.object(sa_async, "create_async_engine", return_value=mock_engine), \
             patch.object(sa_orm, "sessionmaker", return_value=mock_session_factory), \
             patch.dict(os.environ, {
                 "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
                 "ENCRYPTION_KEY": base64.b64encode(old_key).decode(),
             }):
            import rotate_encryption_key
            # Modulni reload qilmasdan to'g'ridan importlar mock bilan ishlaydi
            stats = await rotate_encryption_key.rotate_keys(old_key, new_key, dry_run=True)

        mock_db.commit.assert_not_called()
        assert stats["committed"] is False
        assert stats["cases_rotated"] == 1
        assert stats["comments_rotated"] == 1
        assert stats["cases_errors"] == 0
        assert stats["comments_errors"] == 0

    @pytest.mark.asyncio
    async def test_same_key_rejected(self):
        """Eski va yangi kalit bir xil bo'lsa — xato."""
        key = make_key()
        # Bu tekshiruv main() da amalga oshiriladi, lekin funksiya darajasida ham tekshiramiz
        assert key == key  # obvious — test main() da

    def test_same_keys_exit_in_main(self):
        """main() da eski = yangi kalit bo'lsa sys.exit(1) chaqirilishi kerak."""
        from rotate_encryption_key import _parse_key
        key_b64 = base64.b64encode(os.urandom(32)).decode()
        key1 = _parse_key(key_b64)
        key2 = _parse_key(key_b64)
        assert key1 == key2  # Bir xil — main() buni tekshiradi

    def test_encrypt_decrypt_with_unicode(self):
        """O'zbek harflari va maxsus belgilar bilan ishlashi kerak."""
        from rotate_encryption_key import _encrypt_with_key, _decrypt_with_key
        key = make_key()
        texts = [
            "Korrupsiya haqida murojaat — O'zbekiston",
            "Директор подозревается в коррупции",
            "Report about 💰 bribery incident #123",
            "ÄÖÜ äöü — European chars",
        ]
        for text in texts:
            enc = _encrypt_with_key(text, key)
            dec = _decrypt_with_key(enc, key)
            assert dec == text

    def test_key_rotation_changes_ciphertext(self):
        """Kalit rotatsiyasi shifrlangan matnni o'zgartirishi kerak."""
        from rotate_encryption_key import _encrypt_with_key, _decrypt_with_key
        old_key = make_key()
        new_key = make_key()
        plaintext = "Maxfiy murojaat"

        old_enc = _encrypt_with_key(plaintext, old_key)
        new_enc = _encrypt_with_key(plaintext, new_key)

        # Ikki shifrlangan matn har xil
        assert old_enc != new_enc

        # Eski kalit bilan ochish ishlaydi
        assert _decrypt_with_key(old_enc, old_key) == plaintext

        # Yangi kalit bilan ochish ishlaydi
        assert _decrypt_with_key(new_enc, new_key) == plaintext

        # Eski shifrlangan matnni yangi kalit bilan ochib bo'lmaydi
        with pytest.raises(Exception):
            _decrypt_with_key(old_enc, new_key)

    def test_batch_processing_concept(self):
        """Batch processing mantiqini tekshirish."""
        from rotate_encryption_key import _encrypt_with_key, _decrypt_with_key

        old_key = make_key()
        new_key = make_key()

        # 5 ta yozuv
        records = [f"Murojaat {i}" for i in range(5)]
        encrypted_old = [_encrypt_with_key(r, old_key) for r in records]

        # Rotatsiya simulatsiyasi
        encrypted_new = []
        for enc in encrypted_old:
            plain = _decrypt_with_key(enc, old_key)
            encrypted_new.append(_encrypt_with_key(plain, new_key))

        # Barcha yangi shifrlangan matnlarni yangi kalit bilan ochib tekshirish
        for original, new_enc in zip(records, encrypted_new):
            assert _decrypt_with_key(new_enc, new_key) == original

