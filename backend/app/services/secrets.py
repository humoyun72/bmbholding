"""
Secrets manager — HashiCorp Vault yoki AWS KMS dan kalitlarni yuklaydi.
SECRETS_BACKEND=vault  → Vault dan yuklaydi
SECRETS_BACKEND=awskms → AWS KMS dan yuklaydi
SECRETS_BACKEND=env    → .env dan yuklaydi (default, development uchun)
"""
import logging
import os

logger = logging.getLogger(__name__)


async def load_secrets_from_vault(
    vault_addr: str,
    vault_token: str,
    secret_path: str,
) -> dict:
    """
    HashiCorp Vault dan secret'larni yuklaydi.
    KV v2 engine ishlatiladi: secret/data/<path>
    """
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx o'rnatilmagan")

    url = f"{vault_addr}/v1/{secret_path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"X-Vault-Token": vault_token},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        # KV v2 format: data.data.data
        secrets = data.get("data", {}).get("data", data.get("data", {}))
        logger.info(f"✅ Vault dan {len(secrets)} ta secret yuklandi: {secret_path}")
        return secrets


async def load_secrets_from_aws_kms(
    secret_name: str,
    region: str,
) -> dict:
    """
    AWS Secrets Manager dan secret'larni yuklaydi.
    Secret JSON formatda saqlanishi kerak.
    """
    try:
        import aioboto3
        import json
    except ImportError:
        raise RuntimeError("aioboto3 o'rnatilmagan")

    session = aioboto3.Session()
    async with session.client("secretsmanager", region_name=region) as client:
        resp = await client.get_secret_value(SecretId=secret_name)
        secret_string = resp.get("SecretString", "{}")
        secrets = json.loads(secret_string)
        logger.info(f"✅ AWS Secrets Manager dan {len(secrets)} ta secret yuklandi: {secret_name}")
        return secrets


async def inject_secrets_to_env(secrets: dict) -> None:
    """
    Secret'larni environment variable sifatida inject qiladi.
    Bu mavjud settings ni override qiladi.
    """
    for key, value in secrets.items():
        if value and not os.environ.get(key):
            os.environ[key] = str(value)
            logger.debug(f"Secret injected: {key}")
        elif value:
            # Allaqachon mavjud — override qilmaymiz (xavfsizlik uchun)
            logger.debug(f"Secret already set (skipping override): {key}")


async def bootstrap_secrets() -> None:
    """
    Ilovа start bo'lganda secrets backenddan kalitlarni yuklaydi.
    main.py lifespan'da chaqiriladi.
    """
    backend = os.environ.get("SECRETS_BACKEND", "env").lower()

    if backend == "env":
        logger.info("Secrets backend: .env (development mode)")
        return

    elif backend == "vault":
        vault_addr  = os.environ.get("VAULT_ADDR", "http://vault:8200")
        vault_token = os.environ.get("VAULT_TOKEN", "")
        vault_path  = os.environ.get("VAULT_SECRET_PATH", "secret/data/integritybot")

        if not vault_token:
            # AppRole auth orqali token olish
            role_id   = os.environ.get("VAULT_ROLE_ID", "")
            secret_id = os.environ.get("VAULT_SECRET_ID", "")
            if role_id and secret_id:
                vault_token = await _vault_approle_login(vault_addr, role_id, secret_id)
            else:
                logger.warning("Vault token yoki AppRole credentials yo'q — env ga o'tilmoqda")
                return

        try:
            secrets = await load_secrets_from_vault(vault_addr, vault_token, vault_path)
            await inject_secrets_to_env(secrets)
        except Exception as e:
            logger.error(f"Vault dan secret yuklash xato: {e} — env ishlatiladi")

    elif backend == "awskms":
        secret_name = os.environ.get("AWS_SECRET_NAME", "integritybot/prod")
        region      = os.environ.get("AWS_REGION", "us-east-1")
        try:
            secrets = await load_secrets_from_aws_kms(secret_name, region)
            await inject_secrets_to_env(secrets)
        except Exception as e:
            logger.error(f"AWS Secrets Manager xato: {e} — env ishlatiladi")

    else:
        logger.warning(f"Noma'lum SECRETS_BACKEND: {backend} — env ishlatiladi")


async def _vault_approle_login(vault_addr: str, role_id: str, secret_id: str) -> str:
    """Vault AppRole orqali token oladi."""
    import httpx
    url = f"{vault_addr}/v1/auth/approle/login"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"role_id": role_id, "secret_id": secret_id},
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json()["auth"]["client_token"]
        logger.info("✅ Vault AppRole login muvaffaqiyatli")
        return token

