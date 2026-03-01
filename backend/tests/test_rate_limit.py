"""
Bot Rate Limiting testlari.
Redis mock bilan — haqiqiy Redis kerak emas.
"""
import pytest
import base64
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")


def make_mock_redis(incr_return=1, ttl_return=30):
    """Standart mock Redis ob'ektini yaratadi."""
    mock = AsyncMock()
    mock.incr = AsyncMock(return_value=incr_return)
    mock.expire = AsyncMock()
    mock.ttl = AsyncMock(return_value=ttl_return)
    return mock


class TestRateLimitConfig:
    """Rate limit konfiguratsiyasi testlari."""

    def test_all_required_actions_have_limits(self):
        """Barcha kerakli amallar uchun limit belgilangan bo'lishi kerak."""
        # redis modulini mock qilib import qilamiz
        redis_mock = MagicMock()
        redis_mock.asyncio = MagicMock()
        redis_mock.asyncio.from_url = MagicMock(return_value=AsyncMock())
        with patch.dict(sys.modules, {'redis': redis_mock, 'redis.asyncio': redis_mock.asyncio}):
            # Modulni qayta yuklash
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import RATE_LIMITS
            required = ["start", "report", "file_upload", "check_status", "followup", "default"]
            for action in required:
                assert action in RATE_LIMITS, f"'{action}' uchun limit belgilanmagan"

    def test_report_limit_is_strict(self):
        """Murojaat yuborish limiti qattiq bo'lishi kerak."""
        redis_mock = MagicMock()
        with patch.dict(sys.modules, {'redis': redis_mock, 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import RATE_LIMITS
            limit, window = RATE_LIMITS["report"]
            assert limit <= 10, f"Murojaat limiti juda yuqori: {limit}"
            assert window >= 60, f"Murojaat oynasi juda qisqa: {window}s"

    def test_start_limit_is_reasonable(self):
        """/start limiti o'rtacha bo'lishi kerak."""
        redis_mock = MagicMock()
        with patch.dict(sys.modules, {'redis': redis_mock, 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import RATE_LIMITS
            limit, window = RATE_LIMITS["start"]
            assert limit <= 60
            assert window >= 30

    def test_limits_are_positive(self):
        """Barcha limit va window qiymatlari musbat bo'lishi kerak."""
        redis_mock = MagicMock()
        with patch.dict(sys.modules, {'redis': redis_mock, 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import RATE_LIMITS
            for action, (limit, window) in RATE_LIMITS.items():
                assert limit > 0
                assert window > 0


class TestRateLimitLogic:
    """Rate limiting mantiq testlari — Redis mock bilan."""

    @pytest.fixture(autouse=True)
    def setup_module(self):
        """Har test oldidan rate_limit modulini mock redis bilan yuklaydi."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock(return_value=AsyncMock())
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            import app.bot.rate_limit  # noqa
        yield
        # Keyingi testlar uchun modulni tozalash
        if 'app.bot.rate_limit' in sys.modules:
            del sys.modules['app.bot.rate_limit']

    @pytest.mark.asyncio
    async def test_first_request_allowed(self):
        """Birinchi so'rov har doim ruxsat berilishi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock(return_value=make_mock_redis(incr_return=1))
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit, RATE_LIMITS
            mock_r = make_mock_redis(incr_return=1)
            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                allowed, retry = await check_rate_limit(12345, "start")
            assert allowed is True
            assert retry == 0

    @pytest.mark.asyncio
    async def test_within_limit_allowed(self):
        """Limit ichidagi so'rovlar ruxsat berilishi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit
            mock_r = make_mock_redis(incr_return=3)  # 3-so'rov, limit=30
            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                allowed, _ = await check_rate_limit(12345, "start")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_over_limit_blocked(self):
        """Limit oshganda so'rov bloklanishi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit
            mock_r = make_mock_redis(incr_return=31, ttl_return=45)  # limit=30
            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                allowed, retry = await check_rate_limit(12345, "start")
            assert allowed is False
            assert retry == 45

    @pytest.mark.asyncio
    async def test_report_limit_5_per_5min(self):
        """Murojaat limiti: 5 ta / 5 daqiqa."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit
            mock_r = make_mock_redis(incr_return=6, ttl_return=240)  # limit=5
            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                allowed, retry = await check_rate_limit(99999, "report")
            assert allowed is False
            assert retry == 240

    @pytest.mark.asyncio
    async def test_redis_error_does_not_block(self):
        """Redis ishlamasa ham foydalanuvchi bloklanmasligi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit
            broken_redis = AsyncMock()
            broken_redis.incr = AsyncMock(side_effect=Exception("Redis down"))
            with patch('app.bot.rate_limit._get_redis', return_value=broken_redis):
                allowed, retry = await check_rate_limit(12345, "report")
            assert allowed is True   # Bloklamaymiz
            assert retry == 0

    @pytest.mark.asyncio
    async def test_different_users_independent_limits(self):
        """Har bir foydalanuvchining limiti mustaqil bo'lishi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit

            captured = {}

            async def mock_incr(key):
                captured[key] = captured.get(key, 0) + 1
                return captured[key]

            mock_r = AsyncMock()
            mock_r.incr = mock_incr
            mock_r.expire = AsyncMock()

            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                await check_rate_limit(111, "report")
                await check_rate_limit(222, "report")

            assert "bot:rl:111:report" in captured
            assert "bot:rl:222:report" in captured
            assert captured["bot:rl:111:report"] == 1
            assert captured["bot:rl:222:report"] == 1

    @pytest.mark.asyncio
    async def test_redis_key_format(self):
        """Redis kaliti to'g'ri formatda bo'lishi kerak: bot:rl:{user_id}:{action}"""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit

            captured_keys = []

            async def mock_incr(key):
                captured_keys.append(key)
                return 1

            mock_r = AsyncMock()
            mock_r.incr = mock_incr
            mock_r.expire = AsyncMock()

            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                await check_rate_limit(42, "report")

            assert len(captured_keys) == 1
            assert captured_keys[0] == "bot:rl:42:report"

    @pytest.mark.asyncio
    async def test_ttl_set_on_first_request(self):
        """Birinchi so'rovda TTL o'rnatilishi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit, RATE_LIMITS

            mock_r = AsyncMock()
            mock_r.incr = AsyncMock(return_value=1)  # birinchi so'rov
            mock_r.expire = AsyncMock()

            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                await check_rate_limit(99, "report")

            # expire chaqirilgan bo'lishi kerak
            mock_r.expire.assert_called_once()
            call_args = mock_r.expire.call_args
            assert call_args[0][0] == "bot:rl:99:report"
            _, window = RATE_LIMITS["report"]
            assert call_args[0][1] == window  # To'g'ri window

    @pytest.mark.asyncio
    async def test_ttl_not_reset_on_subsequent_requests(self):
        """Keyingi so'rovlarda TTL qayta o'rnatilmasligi kerak."""
        redis_mock = MagicMock()
        redis_mock.from_url = MagicMock()
        with patch.dict(sys.modules, {'redis': MagicMock(), 'redis.asyncio': redis_mock}):
            if 'app.bot.rate_limit' in sys.modules:
                del sys.modules['app.bot.rate_limit']
            from app.bot.rate_limit import check_rate_limit

            mock_r = AsyncMock()
            mock_r.incr = AsyncMock(return_value=5)  # 5-so'rov, birinchi emas
            mock_r.expire = AsyncMock()

            with patch('app.bot.rate_limit._get_redis', return_value=mock_r):
                await check_rate_limit(99, "report")

            # expire chaqirilmasligi kerak (count != 1)
            mock_r.expire.assert_not_called()
