#!/usr/bin/env python3
"""
🔑 Encryption Key Rotatsiya Skripti
=====================================
IntegrityBot — AES-256-GCM shifrlangan maydonlarni yangi kalit bilan qayta shifrlaydi.

Shifrlangan maydonlar:
  - cases.description_encrypted        → CASE_ENCRYPTION_KEY (yoki ENCRYPTION_KEY)
  - case_comments.content_encrypted    → COMMENT_ENCRYPTION_KEY (yoki ENCRYPTION_KEY)

Alohida kalit rotatsiyasi:
  # Faqat case kalitini almashtirish:
  python scripts/rotate_encryption_key.py \\
    --old-key "eski_case_kalit" \\
    --new-key "yangi_case_kalit" \\
    --target cases --apply

  # Faqat comment kalitini almashtirish:
  python scripts/rotate_encryption_key.py \\
    --old-key "eski_comment_kalit" \\
    --new-key "yangi_comment_kalit" \\
    --target comments --apply

  # Ikkalasini bir xil kalit bilan (eski ENCRYPTION_KEY dan migration):
  python scripts/rotate_encryption_key.py \\
    --old-key "eski_umumiy_kalit" \\
    --new-key "yangi_kalit" \\
    --apply


Xavfsizlik eslatmalari:
  ⚠️  --old-key va --new-key ni command line argumenti sifatida BERMASLIK tavsiya etiladi
      (ps aux orqali ko'rinib qoladi). Buning o'rniga environment variable ishlatish:

  OLD_KEY=$(cat /secure/old.key) NEW_KEY=$(cat /secure/new.key) python rotate_encryption_key.py --from-env --apply

  ⚠️  Skriptni ishga tushirishdan oldin DB zaxira nusxasini oling!
  ⚠️  Production da backend ni to'xtatib, so'ng ishga tushiring.
"""

import asyncio
import argparse
import base64
import os
import sys
import time
import logging
from pathlib import Path

# Backend app papkasini path ga qo'shish
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Kalit bilan ishlash funksiyalari ─────────────────────────────────────────

def _decrypt_with_key(ciphertext_b64: str, key_bytes: bytes) -> str:
    """Base64 formatdagi shifrlangan matnni berilgan kalit bilan ochadi."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    combined = base64.b64decode(ciphertext_b64.encode("utf-8"))
    nonce = combined[:12]
    ciphertext = combined[12:]
    return AESGCM(key_bytes).decrypt(nonce, ciphertext, None).decode("utf-8")


def _encrypt_with_key(plaintext: str, key_bytes: bytes) -> str:
    """Matnni berilgan kalit bilan shifrlaydi, Base64 qaytaradi."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ciphertext = AESGCM(key_bytes).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def _parse_key(key_str: str) -> bytes:
    """Base64 kalit stringini bytes ga aylantiradi va tekshiradi."""
    try:
        key_bytes = base64.b64decode(key_str)
    except Exception:
        raise ValueError("Kalit to'g'ri Base64 formatda emas")
    if len(key_bytes) != 32:
        raise ValueError(f"Kalit 32 bayt bo'lishi kerak, {len(key_bytes)} bayt berildi")
    return key_bytes


# ── Asosiy rotatsiya logikasi ─────────────────────────────────────────────────

async def rotate_keys(
    old_key_bytes: bytes,
    new_key_bytes: bytes,
    dry_run: bool = True,
    batch_size: int = 100,
    target: str = "all",
) -> dict:
    """
    Barcha shifrlangan maydonlarni eski kalit bilan ochib, yangi kalit bilan qayta shifrlaydi.

    Returns:
        dict: statistika — nechta yozuv qayta shifrlandi, nechta xato bo'ldi
    """
    # Import larni bu yerda qilamiz — sys.path allaqachon sozlangan
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/integritybot")
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
    os.environ.setdefault("SECRET_KEY", "dummy_secret_key_for_rotation_script_only")
    os.environ.setdefault("ENCRYPTION_KEY", base64.b64encode(old_key_bytes).decode())

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, text

    from app.core.config import settings
    from app.models import Case, CaseComment

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stats = {
        "cases_processed": 0,
        "cases_rotated": 0,
        "cases_errors": 0,
        "comments_processed": 0,
        "comments_rotated": 0,
        "comments_errors": 0,
        "errors": [],
    }

    prefix = "[DRY RUN] " if dry_run else ""

    async with AsyncSessionLocal() as db:
        # ── 1. Case.description_encrypted ────────────────────────────────────
        if target in ("all", "cases"):
            logger.info(f"{prefix}Cases.description_encrypted ni rotatsiya qilinmoqda...")
            offset = 0
            while True:
                result = await db.execute(
                    select(Case.id, Case.external_id, Case.description_encrypted)
                    .offset(offset).limit(batch_size)
                )
                rows = result.fetchall()
                if not rows:
                    break
                for case_id, external_id, encrypted in rows:
                    stats["cases_processed"] += 1
                    try:
                        plaintext = _decrypt_with_key(encrypted, old_key_bytes)
                        new_encrypted = _encrypt_with_key(plaintext, new_key_bytes)
                        if not dry_run:
                            await db.execute(
                                text("UPDATE cases SET description_encrypted = :enc WHERE id = :id"),
                                {"enc": new_encrypted, "id": case_id},
                            )
                        stats["cases_rotated"] += 1
                        if stats["cases_processed"] % 10 == 0:
                            logger.info(
                                f"{prefix}Cases: {stats['cases_processed']} ta qayta ishlandi, "
                                f"{stats['cases_rotated']} ta rotatsiya qilindi"
                            )
                    except Exception as e:
                        stats["cases_errors"] += 1
                        err_msg = f"Case {external_id}: {e}"
                        stats["errors"].append(err_msg)
                        logger.error(f"{prefix}XATO — {err_msg}")
                offset += batch_size
        else:
            logger.info(f"{prefix}Cases o'tkazib yuborildi (--target={target})")

        # ── 2. CaseComment.content_encrypted ─────────────────────────────────
        if target in ("all", "comments"):
            logger.info(f"{prefix}CaseComments.content_encrypted ni rotatsiya qilinmoqda...")
            offset = 0
            while True:
                result = await db.execute(
                    select(CaseComment.id, CaseComment.case_id, CaseComment.content_encrypted)
                    .offset(offset).limit(batch_size)
                )
                rows = result.fetchall()
                if not rows:
                    break
                for comment_id, case_id, encrypted in rows:
                    stats["comments_processed"] += 1
                    try:
                        plaintext = _decrypt_with_key(encrypted, old_key_bytes)
                        new_encrypted = _encrypt_with_key(plaintext, new_key_bytes)
                        if not dry_run:
                            await db.execute(
                                text("UPDATE case_comments SET content_encrypted = :enc WHERE id = :id"),
                                {"enc": new_encrypted, "id": comment_id},
                            )
                        stats["comments_rotated"] += 1
                    except Exception as e:
                        stats["comments_errors"] += 1
                        err_msg = f"Comment {comment_id} (case {case_id}): {e}"
                        stats["errors"].append(err_msg)
                        logger.error(f"{prefix}XATO — {err_msg}")
                offset += batch_size
        else:
            logger.info(f"{prefix}Comments o'tkazib yuborildi (--target={target})")

        # ── Commit (faqat --apply da) ─────────────────────────────────────────
        if not dry_run:
            if stats["cases_errors"] + stats["comments_errors"] > 0:
                logger.error(
                    f"{stats['cases_errors'] + stats['comments_errors']} ta xato bor. "
                    "Rollback qilinmoqda..."
                )
                await db.rollback()
                stats["committed"] = False
            else:
                await db.commit()
                stats["committed"] = True
                logger.info("✅ Barcha o'zgarishlar saqlandi (commit).")
        else:
            stats["committed"] = False

    await engine.dispose()
    return stats


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="IntegrityBot — AES-256-GCM encryption key rotatsiyasi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Misol:
  # Dry run (hech narsa o'zgarmaydi):
  python rotate_encryption_key.py --old-key OLD_B64 --new-key NEW_B64

  # Haqiqiy rotatsiya:
  python rotate_encryption_key.py --old-key OLD_B64 --new-key NEW_B64 --apply

  # Environment variable orqali (xavfsizroq):
  python rotate_encryption_key.py --from-env --apply
  # (OLD_ENCRYPTION_KEY va NEW_ENCRYPTION_KEY env o'zgaruvchilari kerak)

  # Yangi kalit yaratish:
  python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
        """,
    )
    parser.add_argument("--old-key", help="Eski shifrlash kaliti (Base64)")
    parser.add_argument("--new-key", help="Yangi shifrlash kaliti (Base64)")
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Kalitlarni OLD_ENCRYPTION_KEY va NEW_ENCRYPTION_KEY env o'zgaruvchisidan olish",
    )
    parser.add_argument(
        "--target",
        choices=["all", "cases", "comments"],
        default="all",
        help="Qaysi maydonlarni rotatsiya qilish: all (default), cases, comments",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Haqiqiy o'zgartirish — bu flag bo'lmasa faqat dry-run",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Har bir batch da nechta yozuv qayta ishlanadi (default: 100)",
    )
    args = parser.parse_args()

    # Kalitlarni olish
    if args.from_env:
        old_key_str = os.environ.get("OLD_ENCRYPTION_KEY")
        new_key_str = os.environ.get("NEW_ENCRYPTION_KEY")
        if not old_key_str or not new_key_str:
            parser.error(
                "--from-env uchun OLD_ENCRYPTION_KEY va NEW_ENCRYPTION_KEY "
                "environment o'zgaruvchilari kerak"
            )
    else:
        if not args.old_key or not args.new_key:
            parser.error("--old-key va --new-key berilishi shart (yoki --from-env)")
        old_key_str = args.old_key
        new_key_str = args.new_key

    # Kalitlarni tekshirish
    try:
        old_key_bytes = _parse_key(old_key_str)
        new_key_bytes = _parse_key(new_key_str)
    except ValueError as e:
        logger.error(f"Kalit xatosi: {e}")
        sys.exit(1)

    if old_key_bytes == new_key_bytes:
        logger.error("Eski va yangi kalit bir xil! Rotatsiya bekor qilindi.")
        sys.exit(1)

    # Rejim
    dry_run = not args.apply
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN rejimi — hech narsa o'zgarmaydi")
        logger.info("Haqiqiy rotatsiya uchun --apply flag qo'shing")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("⚠️  HAQIQIY ROTATSIYA REJIMI")
        logger.warning("⚠️  Ma'lumotlar bazasi o'zgartiriladi!")
        logger.warning("⚠️  Davom etishdan oldin DB zaxira nusxasi borligini tasdiqlang.")
        logger.warning("=" * 60)
        confirm = input("Davom etasizmi? (yes/no): ").strip().lower()
        if confirm != "yes":
            logger.info("Rotatsiya bekor qilindi.")
            sys.exit(0)

    # Rotatsiyani bajarish
    start_time = time.time()
    stats = asyncio.run(
        rotate_keys(
            old_key_bytes=old_key_bytes,
            new_key_bytes=new_key_bytes,
            dry_run=dry_run,
            batch_size=args.batch_size,
        )
    )
    elapsed = time.time() - start_time

    # Natijalar
    logger.info("=" * 60)
    logger.info("ROTATSIYA NATIJASI:")
    logger.info(f"  Cases     : {stats['cases_rotated']}/{stats['cases_processed']} rotatsiya qilindi")
    logger.info(f"  Comments  : {stats['comments_rotated']}/{stats['comments_processed']} rotatsiya qilindi")
    logger.info(f"  Xatolar   : {stats['cases_errors'] + stats['comments_errors']} ta")
    logger.info(f"  Vaqt      : {elapsed:.1f} soniya")

    if stats["errors"]:
        logger.error("Xatolar ro'yxati:")
        for err in stats["errors"][:10]:  # Faqat birinchi 10 ta
            logger.error(f"  - {err}")
        if len(stats["errors"]) > 10:
            logger.error(f"  ... va yana {len(stats['errors']) - 10} ta xato")

    if not dry_run:
        if stats.get("committed"):
            logger.info("✅ Barcha o'zgarishlar muvaffaqiyatli saqlandi!")
            logger.info("⚡ .env faylida ENCRYPTION_KEY ni yangi kalit bilan yangilang!")
            logger.info("🔄 Backend ni qayta ishga tushiring: docker compose restart backend")
        else:
            logger.error("❌ Xatolar sababli o'zgarishlar saqlanmadi (rollback).")
            sys.exit(1)
    else:
        logger.info("ℹ️  Dry run yakunlandi. Haqiqiy rotatsiya uchun --apply qo'shing.")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()

