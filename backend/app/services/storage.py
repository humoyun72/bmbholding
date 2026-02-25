import hashlib
import os
import aiofiles
from pathlib import Path
from telegram import Bot
from app.core.config import settings


async def save_telegram_file(bot: Bot, file_id: str, filename: str, case_id: str) -> tuple[str, str, int]:
    """Download file from Telegram and save locally. Returns (path, checksum, size)"""
    file = await bot.get_file(file_id)

    # Sanitize filename
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
    if not safe_name:
        safe_name = "attachment"

    case_dir = Path(settings.UPLOADS_DIR) / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    # Unique filename
    unique_name = f"{file_id[:8]}_{safe_name}"
    file_path = case_dir / unique_name

    # Download
    await file.download_to_drive(str(file_path))

    # Checksum
    sha256 = hashlib.sha256()
    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            sha256.update(chunk)

    size = file_path.stat().st_size
    return str(file_path), sha256.hexdigest(), size


async def get_file_content(storage_path: str) -> bytes:
    async with aiofiles.open(storage_path, "rb") as f:
        return await f.read()


def delete_file(storage_path: str):
    try:
        os.remove(storage_path)
    except FileNotFoundError:
        pass
