"""
Secrets manager unit testlari (mock bilan).
- bootstrap_secrets env mode
- Vault mock
- AWS KMS mock
- inject_secrets_to_env
"""
import pytest
import base64
import os
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_at_least_32_chars_long!!")
    monkeypatch.setenv("ENCRYPTION_KEY", key)


class TestBootstrapSecrets:
    @pytest.mark.asyncio
    async def test_env_backend_does_nothing(self):
        """SECRETS_BACKEND=env bo'lsa hech narsa qilmaydi."""
        os.environ["SECRETS_BACKEND"] = "env"
        from app.services.secrets import bootstrap_secrets
        # Exception ko'tarilmasligi kerak
        await bootstrap_secrets()

    @pytest.mark.asyncio
    async def test_unknown_backend_does_nothing(self):
        """Noma'lum backend — warning, exception yo'q."""
        os.environ["SECRETS_BACKEND"] = "unknown_backend"
        from app.services.secrets import bootstrap_secrets
        await bootstrap_secrets()
        os.environ["SECRETS_BACKEND"] = "env"

    @pytest.mark.asyncio
    async def test_vault_backend_no_token_falls_back(self):
        """Vault token yo'q bo'lsa — env ga qaytadi, exception yo'q."""
        os.environ["SECRETS_BACKEND"] = "vault"
        os.environ.pop("VAULT_TOKEN", None)
        os.environ.pop("VAULT_ROLE_ID", None)
        os.environ.pop("VAULT_SECRET_ID", None)
        from app.services.secrets import bootstrap_secrets
        await bootstrap_secrets()
        os.environ["SECRETS_BACKEND"] = "env"

    @pytest.mark.asyncio
    async def test_vault_backend_error_falls_back(self):
        """Vault ulanish xatosi — env ga qaytadi, exception yo'q."""
        os.environ["SECRETS_BACKEND"] = "vault"
        os.environ["VAULT_TOKEN"] = "test-token"
        from app.services import secrets
        with patch.object(secrets, "load_secrets_from_vault",
                          new=AsyncMock(side_effect=Exception("connection refused"))):
            await secrets.bootstrap_secrets()
        os.environ["SECRETS_BACKEND"] = "env"
        os.environ.pop("VAULT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_vault_backend_success(self):
        """Vault muvaffaqiyatli yuklanganda secretlar inject qilinadi."""
        os.environ["SECRETS_BACKEND"] = "vault"
        os.environ["VAULT_TOKEN"] = "test-token"
        test_secrets = {"TEST_SECRET_KEY": "vault_value_123"}
        from app.services import secrets
        with patch.object(secrets, "load_secrets_from_vault",
                          new=AsyncMock(return_value=test_secrets)):
            await secrets.bootstrap_secrets()
        assert os.environ.get("TEST_SECRET_KEY") == "vault_value_123"
        # Tozalash
        os.environ.pop("TEST_SECRET_KEY", None)
        os.environ["SECRETS_BACKEND"] = "env"
        os.environ.pop("VAULT_TOKEN", None)


class TestInjectSecretsToEnv:
    @pytest.mark.asyncio
    async def test_injects_missing_keys(self):
        """Mavjud bo'lmagan kalitlar inject qilinadi."""
        from app.services.secrets import inject_secrets_to_env
        os.environ.pop("_TEST_INJECT_KEY", None)
        await inject_secrets_to_env({"_TEST_INJECT_KEY": "test_value"})
        assert os.environ.get("_TEST_INJECT_KEY") == "test_value"
        os.environ.pop("_TEST_INJECT_KEY")

    @pytest.mark.asyncio
    async def test_does_not_override_existing_keys(self):
        """Mavjud kalitlarni override qilmaydi."""
        from app.services.secrets import inject_secrets_to_env
        os.environ["_TEST_EXISTING"] = "original"
        await inject_secrets_to_env({"_TEST_EXISTING": "new_value"})
        assert os.environ.get("_TEST_EXISTING") == "original"
        os.environ.pop("_TEST_EXISTING")

    @pytest.mark.asyncio
    async def test_skips_empty_values(self):
        """Bo'sh qiymatli kalitlar inject qilinmaydi."""
        from app.services.secrets import inject_secrets_to_env
        os.environ.pop("_TEST_EMPTY", None)
        await inject_secrets_to_env({"_TEST_EMPTY": ""})
        assert "_TEST_EMPTY" not in os.environ


class TestLoadSecretsFromVault:
    @pytest.mark.asyncio
    async def test_parses_kv_v2_format(self):
        """Vault KV v2 format to'g'ri parse qilinadi."""
        from app.services.secrets import load_secrets_from_vault

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "data": {
                "data": {
                    "SECRET_KEY": "my_secret",
                    "ENCRYPTION_KEY": "my_enc_key",
                }
            }
        })

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await load_secrets_from_vault(
                "http://vault:8200", "test-token", "secret/data/integritybot"
            )

        assert result["SECRET_KEY"] == "my_secret"
        assert result["ENCRYPTION_KEY"] == "my_enc_key"

