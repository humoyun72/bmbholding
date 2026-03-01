from pydantic_settings import BaseSettings
from typing import Optional
import base64


class Settings(BaseSettings):
    # App
    APP_NAME: str = "IntegrityBot"
    COMPANY_NAME: str = "Company"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_SECRET: str = "changeme"
    WEBHOOK_URL: str = ""
    ADMIN_CHAT_ID: int = 0
    POLL_CHAT_ID: int = 0   # guruh yoki kanal ID — so'rovnomalar shu yerga yuboriladi
    # "webhook" yoki "polling"
    BOT_MODE: str = "polling"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ENCRYPTION_KEY: str  # base64 encoded 32 bytes

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True

    # Storage
    STORAGE_TYPE: str = "local"
    UPLOADS_DIR: str = "/app/uploads"
    MAX_FILE_SIZE_MB: int = 20

    # AWS S3 / S3-compatible (MinIO, Yandex Cloud, etc.)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BUCKET_NAME: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    # S3-compatible endpoint (MinIO: http://minio:9000, Yandex: https://storage.yandexcloud.net)
    S3_ENDPOINT_URL: Optional[str] = None
    # Public CDN URL (agar bor bo'lsa, presigned URL o'rniga ishlatiladi)
    S3_PUBLIC_BASE_URL: Optional[str] = None

    # ClamAV antivirus (docker-compose da clamav service kerak)
    CLAMAV_HOST: str = "clamav"
    CLAMAV_PORT: int = 3310
    CLAMAV_ENABLED: bool = False   # True qilish uchun clamav container healthcheck o'tishi kerak

    @property
    def encryption_key_bytes(self) -> bytes:
        return base64.b64decode(self.ENCRYPTION_KEY)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
