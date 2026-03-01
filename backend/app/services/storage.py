"""
Storage service — local disk va AWS S3 ikkisini qo'llab-quvvatlaydi.
STORAGE_TYPE=local  → /app/uploads ichida saqlaydi
STORAGE_TYPE=s3     → AWS S3 bucket ga yuklaydi
"""
import hashlib
import io
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

import aiofiles
from telegram import Bot

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Xavfsizlik: ruxsat etilgan MIME turlar ──────────────────────────────────
ALLOWED_MIME_TYPES = {
    # Rasmlar
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
    # Hujjatlar
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Matn
    "text/plain", "text/csv",
    # Arxiv
    "application/zip", "application/x-rar-compressed", "application/x-7z-compressed",
    # Video/Audio
    "video/mp4", "video/avi", "video/quicktime",
    "audio/mpeg", "audio/wav", "audio/ogg",
}

# ── Bloklangan kengaytmalar (bajariladigan fayllar) ─────────────────────────
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".ps2",
    ".msi", ".dll", ".vbs", ".js", ".jar", ".com",
    ".scr", ".pif", ".reg", ".hta", ".cpl",
}

MAX_FILE_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


async def scan_with_clamav(data: bytes, filename: str) -> None:
    """
    ClamAV bilan faylni skanerlaydi.
    CLAMAV_ENABLED=False bo'lsa — skanerlash o'tkazib yuboriladi va WARNING log yoziladi.
    Virus topilsa — ValueError chiqaradi.
    """
    if not settings.CLAMAV_ENABLED:
        logger.warning(
            f"⚠️  ClamAV O'CHIRILGAN (CLAMAV_ENABLED=false) — '{filename}' skanlanmadi. "
            "Production muhitida ClamAV yoqilishi tavsiya etiladi."
        )
        return

    try:
        import asyncio
        reader, writer = await asyncio.open_connection(
            settings.CLAMAV_HOST, settings.CLAMAV_PORT
        )
        # ClamAV INSTREAM protokoli
        writer.write(b"zINSTREAM\0")
        chunk_size = len(data)
        writer.write(chunk_size.to_bytes(4, byteorder="big"))
        writer.write(data)
        writer.write((0).to_bytes(4, byteorder="big"))
        await writer.drain()

        response = await asyncio.wait_for(reader.read(1024), timeout=30)
        writer.close()
        await writer.wait_closed()

        result = response.decode("utf-8", errors="ignore").strip()
        logger.info(f"ClamAV scan '{filename}': {result}")

        if "FOUND" in result:
            virus_name = result.split("FOUND")[0].strip().split(":")[-1].strip()
            raise ValueError(f"Fayl zararli deb topildi: {virus_name}")
    except ValueError:
        raise
    except Exception as e:
        # ClamAV mavjud bo'lmasa yoki ulanmasa — warning, lekin fayl qabul qilinadi
        logger.warning(f"ClamAV scan failed for '{filename}': {e}. Skipping scan.")


def validate_file(filename: str, mime_type: str, size_bytes: int) -> None:
    """Fayl xavfsizligini tekshiradi. Xato bo'lsa ValueError chiqaradi."""
    # Hajm tekshiruvi
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"Fayl hajmi {settings.MAX_FILE_SIZE_MB} MB dan oshmasligi kerak")

    # Kengaytma tekshiruvi
    suffix = Path(filename).suffix.lower()
    if suffix in BLOCKED_EXTENSIONS:
        raise ValueError(f"'{suffix}' kengaytmali fayllar qabul qilinmaydi")

    # MIME tekshiruvi
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        # Noma'lum MIME — kengaytmadan taxmin qilamiz
        guessed, _ = mimetypes.guess_type(filename)
        if guessed not in ALLOWED_MIME_TYPES:
            raise ValueError(f"'{mime_type}' turdagi fayllar qabul qilinmaydi")


def sanitize_filename(filename: str) -> str:
    """Fayl nomidan xavfli belgilarni tozalaydi."""
    # Faqat xarf, raqam, nuqta, tire, pastki chiziq va bo'shliqqa ruxsat
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ")
    # Ketma-ket nuqtalarni bitta nuqtaga aylantirish (path traversal himoyasi)
    while ".." in safe:
        safe = safe.replace("..", ".")
    # Bosh va oxiridagi nuqtalar/bo'shliqlarni olib tashlash
    safe = safe.strip(". ")
    return safe or "attachment"


# ── S3 helper ────────────────────────────────────────────────────────────────

def _s3_session():
    """aioboto3 sessiyasini yaratadi (AWS yoki S3-compatible)."""
    try:
        import aioboto3
    except ImportError:
        raise RuntimeError("aioboto3 o'rnatilmagan: pip install aioboto3")
    return aioboto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def _s3_client_kwargs() -> dict:
    """endpoint_url ni S3-compatible servislar uchun qo'shadi."""
    kwargs = {}
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    return kwargs


async def _upload_to_s3(data: bytes, s3_key: str, mime_type: str) -> str:
    """Faylni S3 ga yuklaydi. s3_key ni qaytaradi."""
    session = _s3_session()
    async with session.client("s3", **_s3_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=s3_key,
            Body=data,
            ContentType=mime_type,
            ServerSideEncryption="AES256",
        )
    logger.info(f"S3 upload: s3://{settings.AWS_BUCKET_NAME}/{s3_key}")
    return s3_key


async def _download_from_s3(s3_key: str) -> bytes:
    """S3 dan fayl yuklab oladi."""
    session = _s3_session()
    async with session.client("s3", **_s3_client_kwargs()) as s3:
        response = await s3.get_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key)
        return await response["Body"].read()


async def _delete_from_s3(s3_key: str) -> None:
    """S3 dan faylni o'chiradi."""
    session = _s3_session()
    async with session.client("s3", **_s3_client_kwargs()) as s3:
        await s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=s3_key)
    logger.info(f"S3 delete: {s3_key}")


async def _generate_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """S3 fayli uchun vaqtinchalik URL yaratadi (default 1 soat)."""
    # Agar public CDN URL bo'lsa — to'g'ridan-to'g'ri qaytaramiz
    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{s3_key}"

    session = _s3_session()
    async with session.client("s3", **_s3_client_kwargs()) as s3:
        url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expires_in,
        )
    return url


# ── Asosiy public funksiyalar ────────────────────────────────────────────────

async def save_telegram_file(
    bot: Bot,
    file_id: str,
    filename: str,
    case_id: str,
    mime_type: str = "application/octet-stream",
) -> tuple[str, str, int]:
    """
    Telegram faylini yuklab oladi va saqlaydi.
    Returns: (storage_path, sha256_checksum, size_bytes)

    storage_path:
      - local:  /app/uploads/<case_id>/<name>
      - s3:     cases/<case_id>/<name>   (S3 key)
    """
    tg_file = await bot.get_file(file_id)

    # Faylni xotiraga yuklab olamiz
    buf = io.BytesIO()
    await tg_file.download_to_memory(buf)
    data = buf.getvalue()
    size = len(data)

    # Xavfsizlik tekshiruvi
    safe_name = sanitize_filename(filename)
    validate_file(safe_name, mime_type, size)

    # ClamAV antivirus skanerlash
    await scan_with_clamav(data, safe_name)

    # Checksum
    checksum = hashlib.sha256(data).hexdigest()

    if settings.STORAGE_TYPE == "s3":
        # S3 path
        s3_key = f"cases/{case_id}/{file_id[:8]}_{safe_name}"
        await _upload_to_s3(data, s3_key, mime_type)
        return s3_key, checksum, size
    else:
        # Local path
        case_dir = Path(settings.UPLOADS_DIR) / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{file_id[:8]}_{safe_name}"
        file_path = case_dir / unique_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)
        return str(file_path), checksum, size


async def get_file_content(storage_path: str) -> bytes:
    """Faylni o'qiydi — local yoki S3 dan."""
    if settings.STORAGE_TYPE == "s3":
        return await _download_from_s3(storage_path)
    else:
        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()


async def get_download_url(storage_path: str, expires_in: int = 3600) -> Optional[str]:
    """
    S3 rejimida vaqtinchalik URL qaytaradi.
    Local rejimda None qaytaradi (to'g'ridan-to'g'ri endpoint ishlatiladi).
    """
    if settings.STORAGE_TYPE == "s3":
        return await _generate_presigned_url(storage_path, expires_in)
    return None


async def delete_file(storage_path: str) -> None:
    """Faylni o'chiradi — local yoki S3 dan."""
    if settings.STORAGE_TYPE == "s3":
        await _delete_from_s3(storage_path)
    else:
        try:
            os.remove(storage_path)
        except FileNotFoundError:
            pass


async def check_s3_connection() -> dict:
    """S3 ulanishini tekshiradi. Health check uchun."""
    if settings.STORAGE_TYPE != "s3":
        return {"type": "local", "status": "ok", "path": settings.UPLOADS_DIR}

    try:
        session = _s3_session()
        async with session.client("s3", **_s3_client_kwargs()) as s3:
            await s3.head_bucket(Bucket=settings.AWS_BUCKET_NAME)
        return {
            "type": "s3",
            "status": "ok",
            "bucket": settings.AWS_BUCKET_NAME,
            "region": settings.AWS_REGION,
            "endpoint": settings.S3_ENDPOINT_URL or "aws",
        }
    except Exception as e:
        return {"type": "s3", "status": "error", "error": str(e)}


async def check_clamav_health() -> dict:
    """ClamAV ulanishini tekshiradi. Health check uchun."""
    if not settings.CLAMAV_ENABLED:
        return {
            "enabled": False,
            "status": "disabled",
            "warning": "ClamAV o'chirilgan — yuklangan fayllar skanlanmaydi",
        }
    try:
        import asyncio as _asyncio
        reader, writer = await _asyncio.wait_for(
            _asyncio.open_connection(settings.CLAMAV_HOST, settings.CLAMAV_PORT),
            timeout=5,
        )
        writer.write(b"zPING\0")
        await writer.drain()
        response = await _asyncio.wait_for(reader.read(10), timeout=5)
        writer.close()
        await writer.wait_closed()
        if b"PONG" in response:
            return {"enabled": True, "status": "ok", "host": settings.CLAMAV_HOST}
        return {"enabled": True, "status": "error", "error": "PONG kelmadi"}
    except Exception as e:
        return {"enabled": True, "status": "error", "error": str(e)}

