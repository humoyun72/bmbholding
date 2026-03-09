from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password, hash_password, create_access_token, decode_token,
    generate_totp_secret, get_totp_uri, generate_qr_code, verify_totp
)
from app.models import User, UserRole, AuditLog, AuditAction
from app.schemas.auth import (
    TokenResponse, LoginRequest, UserCreate, UserResponse,
    Setup2FAResponse, Verify2FARequest
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Noto'g'ri token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Noto'g'ri token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi")
    return user


def require_roles(*roles: UserRole):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat etilmagan")
        return current_user
    return checker


def is_superuser(user: User) -> bool:
    """Faqat birinchi yaratilgan admin (username='admin') superuser hisoblanadi."""
    return user.username == "admin"


require_admin = require_roles(UserRole.ADMIN)
require_superadmin = require_roles(UserRole.ADMIN)  # is_superuser() tekshiruvi endpoint ichida
require_investigator_or_above = require_roles(UserRole.ADMIN, UserRole.INVESTIGATOR)


@router.post("/token", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    ip = request.client.host if request.client else None
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    # ── LDAP autentifikatsiya (lokal foydalanuvchi topilmasa yoki LDAP yoqilgan bo'lsa) ──
    from app.services.ldap_auth import is_ldap_enabled, authenticate_ldap, get_role_from_ldap_groups
    if is_ldap_enabled() and (not user or not user.hashed_password):
        ldap_user = await authenticate_ldap(form_data.username, form_data.password)
        if ldap_user:
            # DB da foydalanuvchi yo'q bo'lsa — avtomatik yaratish
            if not user:
                from app.core.security import hash_password as _hp
                role = get_role_from_ldap_groups(ldap_user.groups)
                user = User(
                    username=ldap_user.username,
                    email=ldap_user.email,
                    full_name=ldap_user.full_name,
                    hashed_password=_hp("__ldap__"),   # LDAP foydalanuvchilar lokal parolsiz
                    role=role,
                    is_active=True,
                )
                db.add(user)
                db.add(AuditLog(
                    action=AuditAction.USER_CREATE,
                    entity_type="user",
                    payload={"username": ldap_user.username, "source": "ldap", "role": role},
                ))
            else:
                # Mavjud foydalanuvchini yangilash (ism, email)
                user.full_name = ldap_user.full_name
                user.email = ldap_user.email

            user.last_login = datetime.now(timezone.utc)
            db.add(AuditLog(
                user_id=user.id if user.id else None,
                action=AuditAction.LOGIN,
                ip_address=ip,
                payload={"source": "ldap"},
            ))
            await db.commit()
            if not user.id:
                await db.refresh(user)

            token = create_access_token({"sub": str(user.id), "role": user.role})
            return TokenResponse(
                access_token=token,
                token_type="bearer",
                role=user.role,
                username=user.username,
                full_name=user.full_name,
                totp_enabled=user.totp_enabled,
                force_password_change=user.force_password_change,
            )
        else:
            # LDAP ham muvaffaqiyatsiz
            try:
                from app.services.siem import siem_service
                await siem_service.send_security_event(
                    event_type="LOGIN_FAILED",
                    severity="medium",
                    ip_address=ip,
                    details={"username": form_data.username, "reason": "ldap_failed"},
                )
            except Exception:
                pass
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login yoki parol noto'g'ri")

    # ── Lokal autentifikatsiya ────────────────────────────────────────────
    if not user or not verify_password(form_data.password, user.hashed_password):
        try:
            from app.services.siem import siem_service
            await siem_service.send_security_event(
                event_type="LOGIN_FAILED",
                severity="medium",
                ip_address=ip,
                details={"username": form_data.username, "reason": "invalid_credentials"},
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login yoki parol noto'g'ri")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hisob o'chirilgan")

    # 2FA talab qilinishini tekshirish
    if user.totp_enabled:
        totp_code = form_data.scopes[0] if form_data.scopes else None
        if not totp_code or not verify_totp(user.totp_secret, totp_code):
            try:
                from app.services.siem import siem_service
                await siem_service.send_security_event(
                    event_type="LOGIN_2FA_FAILED",
                    severity="high",
                    ip_address=ip,
                    user_id=str(user.id),
                    details={"username": user.username},
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA kodi kerak yoki noto'g'ri",
                headers={"X-2FA-Required": "true"}
            )

    user.last_login = datetime.now(timezone.utc)
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        ip_address=ip,
    ))
    await db.commit()

    try:
        from app.services.siem import siem_service
        await siem_service.send_audit_event(
            action="LOGIN",
            user_id=str(user.id),
            ip_address=ip,
            details={"username": user.username, "role": user.role},
        )
    except Exception:
        pass

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        totp_enabled=user.totp_enabled,
        force_password_change=user.force_password_change,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/setup-2fa", response_model=Setup2FAResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)
    qr = generate_qr_code(uri)

    current_user.totp_secret = secret
    await db.commit()

    return Setup2FAResponse(secret=secret, qr_code=f"data:image/png;base64,{qr}", uri=uri)


@router.post("/verify-2fa")
async def verify_2fa(
    body: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA sozlanmagan")
    if not verify_totp(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Noto'g'ri kod")

    current_user.totp_enabled = True
    await db.commit()
    return {"message": "2FA muvaffaqiyatli yoqildi"}


@router.post("/disable-2fa")
async def disable_2fa(
    body: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """2FA ni o'chirish — joriy kodni tasdiqlash kerak"""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA yoqilmagan")
    if not verify_totp(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Noto'g'ri 2FA kodi")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    return {"message": "2FA muvaffaqiyatli o'chirildi"}


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    # Oddiy admin admin roli bilan foydalanuvchi yarata olmaydi
    if not is_superuser(current_user) and body.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Faqat superadmin boshqa adminlarni yarata oladi")

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu foydalanuvchi nomi allaqachon mavjud")

    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_CREATE,
        entity_type="user",
        payload={"username": body.username, "role": body.role},
    ))
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if is_superuser(current_user):
        result = await db.execute(select(User).order_by(User.created_at.desc()))
    else:
        # Oddiy admin: faqat investigatorlar va o'zi
        result = await db.execute(
            select(User).where(
                (User.role == UserRole.INVESTIGATOR) | (User.id == current_user.id)
            ).order_by(User.created_at.desc())
        )
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Foydalanuvchini tahrirlash — admin huquqi kerak."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    # Oddiy admin cheklovlari
    if not is_superuser(current_user):
        # Boshqa adminlarni tahrirlay olmaydi (superuser bundan mustasno)
        if target.role == UserRole.ADMIN and target.id != current_user.id:
            raise HTTPException(status_code=403, detail="Boshqa adminlarni tahrirlash uchun superadmin huquqi kerak")
        # Admin rolini tayinlay olmaydi
        if "role" in body and body["role"] == "admin":
            raise HTTPException(status_code=403, detail="Admin rolini tayinlash uchun superadmin huquqi kerak")

    # O'zgartirilishi mumkin bo'lgan maydonlar
    if "full_name" in body and body["full_name"] is not None:
        target.full_name = body["full_name"].strip() or target.full_name

    if "email" in body and body["email"]:
        new_email = body["email"].strip().lower()
        dup = await db.execute(
            select(User).where(User.email == new_email, User.id != target.id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bu email allaqachon ishlatilmoqda")
        target.email = new_email

    if "role" in body and body["role"]:
        # Superuser (username=admin) rolini o'zgartirib bo'lmaydi
        if target.username == "admin":
            raise HTTPException(status_code=400, detail="Superuser roli o'zgartirib bo'lmaydi")
        try:
            target.role = UserRole(body["role"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Noto'g'ri rol")

    if "is_active" in body and body["is_active"] is not None:
        if target.username == "admin" and not body["is_active"]:
            raise HTTPException(status_code=400, detail="Superuserni o'chirib bo'lmaydi")
        target.is_active = bool(body["is_active"])

    if "password" in body and body["password"]:
        pw = body["password"]
        if len(pw) < 8:
            raise HTTPException(status_code=400, detail="Parol kamida 8 belgi bo'lishi kerak")
        target.hashed_password = hash_password(pw)
        target.force_password_change = body.get("force_password_change", False)

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(target.id),
        payload={"updated_fields": [k for k in body if k != "password"], "by": str(current_user.id)},
    ))
    await db.commit()
    await db.refresh(target)
    return UserResponse.model_validate(target)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Foydalanuvchini o'chirish — superuser (username=admin) o'chirilmaydi."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    # Superuserni himoya qilish
    if target.username == "admin":
        raise HTTPException(status_code=400, detail="Superuserni o'chirish mumkin emas")

    # Oddiy admin faqat investigatorlarni o'chira oladi
    if not is_superuser(current_user) and target.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Boshqa adminlarni o'chirish uchun superadmin huquqi kerak")

    # O'zini o'chira olmaydi
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="O'z akkauntingizni o'chirib bo'lmaydi")

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(target.id),
        payload={"action": "user_deleted", "username": target.username},
    ))
    await db.flush()   # AuditLog ni yozib, keyin user ni o'chirish
    await db.delete(target)
    await db.commit()
    return {"message": f"Foydalanuvchi '{target.username}' o'chirildi"}


@router.post("/users/{user_id}/telegram-link")
async def generate_telegram_link_for_user(
    user_id: str,
    current_user: User = Depends(require_admin),
):
    """Admin boshqa foydalanuvchi uchun Telegram bog'lash havolasi yaratadi."""
    import secrets as _secrets
    import redis.asyncio as aioredis

    token = _secrets.token_urlsafe(32)
    redis_key = f"tg_link:{token}"

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.setex(redis_key, 600, user_id)
        await r.aclose()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis xatosi: {e}")

    try:
        from app.api.v1.telegram import get_bot_app
        bot_app = get_bot_app()
        await bot_app.initialize()
        me = await bot_app.bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = None

    link = f"https://t.me/{bot_username}?start=link_{token}" if bot_username else None
    return {"token": token, "link": link, "bot_username": bot_username, "expires_in": 600}


@router.get("/ldap/status")
async def ldap_status(_: User = Depends(require_admin)):
    """LDAP/SSO ulanish holati — faqat admin ko'ra oladi."""
    from app.services.ldap_auth import is_ldap_enabled
    enabled = is_ldap_enabled()
    ldap_url = getattr(settings, "LDAP_URL", None)
    ldap_domain = getattr(settings, "LDAP_DOMAIN", None)
    return {
        "enabled": enabled,
        "configured": bool(ldap_url),
        "url": ldap_url if enabled else None,
        "domain": ldap_domain if enabled else None,
        "user_filter": getattr(settings, "LDAP_USER_FILTER", "(sAMAccountName={username})"),
        "use_ssl": getattr(settings, "LDAP_USE_SSL", False),
    }


@router.post("/ldap/test")
async def ldap_test(
    body: dict,
    _: User = Depends(require_admin),
):
    """LDAP ulanishini test qiladi — test foydalanuvchi bilan."""
    from app.services.ldap_auth import is_ldap_enabled, authenticate_ldap
    if not is_ldap_enabled():
        return {"ok": False, "message": "LDAP o'chirilgan (LDAP_ENABLED=false)"}

    test_username = body.get("username", "")
    test_password = body.get("password", "")
    if not test_username or not test_password:
        return {"ok": False, "message": "username va password kerak"}

    try:
        ldap_user = await authenticate_ldap(test_username, test_password)
        if ldap_user:
            from app.services.ldap_auth import get_role_from_ldap_groups
            role = get_role_from_ldap_groups(ldap_user.groups)
            return {
                "ok": True,
                "message": "LDAP ulanish muvaffaqiyatli",
                "user": {
                    "username": ldap_user.username,
                    "email": ldap_user.email,
                    "full_name": ldap_user.full_name,
                    "groups_count": len(ldap_user.groups),
                    "assigned_role": role,
                },
            }
        return {"ok": False, "message": "Autentifikatsiya muvaffaqiyatsiz (noto'g'ri login/parol)"}
    except Exception as e:
        return {"ok": False, "message": f"Xato: {str(e)}"}


@router.post("/forgot-password")
async def forgot_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Parolni tiklash so'rovi — email yuboradi.
    Foydalanuvchi mavjudligini oshkor etmaydi (xavfsizlik).
    """
    import secrets as _secrets
    import redis.asyncio as aioredis

    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email kiritilishi kerak")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Foydalanuvchi yo'q bo'lsa — xato bermayiz (security best practice)
    if not user or not user.is_active:
        return {"message": "Agar bu email tizimda mavjud bo'lsa, tiklash havolasi yuborildi"}

    token = _secrets.token_urlsafe(32)
    redis_key = f"pw_reset:{token}"

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.setex(redis_key, 3600, str(user.id))  # 1 soat
        await r.aclose()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis xatosi: {e}")

    reset_url = settings.FRONTEND_URL or ""
    reset_link = f"{reset_url}/reset-password?token={token}" if reset_url else f"Token: {token}"

    try:
        from app.services.email import send_email
        import logging as _log
        _auth_log = _log.getLogger(__name__)

        name = user.full_name or user.username
        body_text = (
            f"Salom {name}!\n\n"
            f"Parolingizni tiklash uchun quyidagi havolani bosing:\n\n"
            f"{reset_link}\n\n"
            f"Havola 1 soat amal qiladi.\n\n"
            f"Agar siz bu so'rovni yubormagan bo'lsangiz, ushbu xatni e'tiborsiz qoldiring."
        )
        body_html = f"""
<html><body style="font-family:Arial,sans-serif;background:#f0f2f5;margin:0;padding:20px">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:10px;
              padding:36px 32px;box-shadow:0 2px 8px rgba(0,0,0,.08)">
    <h2 style="margin:0 0 8px;color:#1e1e2e;font-size:20px">🔐 Parolni tiklash</h2>
    <p style="color:#555;margin:0 0 20px;font-size:14px">
      Salom, <strong>{name}</strong>!
    </p>
    <p style="color:#555;font-size:14px;margin:0 0 24px">
      Parolingizni tiklash so'rovi qabul qilindi. Quyidagi tugmani bosing:
    </p>
    <div style="text-align:center;margin:0 0 28px">
      <a href="{reset_link}"
        style="display:inline-block;background:#4f46e5;color:#ffffff;
               padding:13px 30px;border-radius:7px;font-size:15px;font-weight:600;
               text-decoration:none;letter-spacing:.3px">
        Parolni tiklash
      </a>
    </div>
    <p style="color:#888;font-size:12px;margin:0 0 8px">
      Tugma ishlamasa, ushbu havolani brauzeringizga nusxalang:
    </p>
    <p style="background:#f5f5f5;border-radius:5px;padding:10px;font-size:11px;
              color:#555;word-break:break-all;margin:0 0 24px">{reset_link}</p>
    <hr style="border:none;border-top:1px solid #eee;margin:0 0 16px">
    <p style="color:#aaa;font-size:11px;margin:0">
      ⏱ Havola <strong>1 soat</strong> amal qiladi.<br>
      Agar bu so'rov siz tomondan yuborilmagan bo'lsa, ushbu xatni e'tiborsiz qoldiring.
    </p>
  </div>
</body></html>"""

        sent = await send_email(
            to=user.email,
            subject="IntegrityBot — Parolni tiklash",
            body=body_text,
            html=body_html,
        )
        if sent:
            _auth_log.info(f"Parol tiklash emaili yuborildi: {user.email}")
        else:
            _auth_log.error(
                f"Parol tiklash emaili yuborilmadi ({user.email}). "
                f"SMTP sozlamalarini tekshiring: host={settings.SMTP_HOST} "
                f"port={settings.SMTP_PORT} user={settings.SMTP_USER!r}"
            )
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).error(f"Parol tiklash emaili xatosi ({user.email}): {e}")

    return {"message": "Agar bu email tizimda mavjud bo'lsa, tiklash havolasi yuborildi"}


@router.post("/reset-password")
async def reset_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Token asosida parolni tiklash."""
    import redis.asyncio as aioredis

    token = body.get("token", "").strip()
    new_password = body.get("new_password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token va yangi parol kiritilishi kerak")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Parol kamida 8 belgidan iborat bo'lishi kerak")

    redis_key = f"pw_reset:{token}"
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        user_id_str = await r.get(redis_key)
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Token yaroqsiz yoki muddati o'tgan")
        await r.delete(redis_key)
        await r.aclose()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis xatosi: {e}")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id_str)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Foydalanuvchi topilmadi")

    user.hashed_password = hash_password(new_password)
    user.force_password_change = False
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(user.id),
        payload={"action": "password_reset"},
    ))
    await db.commit()
    return {"message": "Parol muvaffaqiyatli tiklandi"}


@router.post("/change-password")
async def change_password(    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Parol o'zgartirish.
    force_password_change=True bo'lsa — joriy parol talab qilinmaydi (birinchi kirish).
    """
    new_password = body.get("new_password", "")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Parol kamida 8 belgidan iborat bo'lishi kerak")

    # Majburiy o'zgartirish rejimida emas bo'lsa — joriy parolni tekshirish
    if not current_user.force_password_change:
        current_password = body.get("current_password", "")
        if not current_password or not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Joriy parol noto'g'ri")

    current_user.hashed_password = hash_password(new_password)
    current_user.force_password_change = False

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(current_user.id),
        payload={"action": "password_changed"},
    ))
    await db.commit()
    return {"message": "Parol muvaffaqiyatli o'zgartirildi"}


@router.post("/telegram-link/generate")
async def generate_telegram_link(
    current_user: User = Depends(get_current_user),
):
    """
    Bir martalik Telegram bog'lash tokeni yaratadi.
    Frontend shu tokenni t.me/Bot?start=link_{token} havolasiga joylashtiradi.
    Token 10 daqiqa amal qiladi, Redis da saqlanadi.
    """
    import secrets as _secrets
    import redis.asyncio as aioredis

    token = _secrets.token_urlsafe(32)
    redis_key = f"tg_link:{token}"

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        # Token → user_id mapping, 10 daqiqa TTL
        await r.setex(redis_key, 600, str(current_user.id))
        await r.aclose()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis xatosi: {e}")

    # Bot username ni olish
    try:
        from app.api.v1.telegram import get_bot_app
        bot_app = get_bot_app()
        await bot_app.initialize()
        me = await bot_app.bot.get_me()
        bot_username = me.username
    except Exception:
        bot_username = None

    link = f"https://t.me/{bot_username}?start=link_{token}" if bot_username else None

    return {
        "token": token,
        "link": link,
        "bot_username": bot_username,
        "expires_in": 600,
    }


@router.get("/telegram-link/status")
async def telegram_link_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Foydalanuvchining Telegram bog'lanish holatini qaytaradi."""
    await db.refresh(current_user)
    return {
        "linked": current_user.telegram_chat_id is not None,
        "telegram_chat_id": current_user.telegram_chat_id,
    }


@router.delete("/telegram-link")
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Telegram bog'lanishini uzish."""
    current_user.telegram_chat_id = None
    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(current_user.id),
        payload={"action": "telegram_unlinked"},
    ))
    await db.commit()
    return {"message": "Telegram bog'lanishi uzildi"}


@router.put("/profile")
async def update_profile(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Foydalanuvchi o'z profilini (full_name, email) yangilaydi."""
    from sqlalchemy import select as sa_select

    full_name = body.get("full_name", "").strip()
    email = body.get("email", "").strip().lower()

    if full_name:
        current_user.full_name = full_name

    if email:
        # Email uniqueness tekshirish
        existing = await db.execute(
            sa_select(User).where(User.email == email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bu email allaqachon ishlatilmoqda")
        current_user.email = email

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(current_user.id),
        payload={"action": "profile_updated", "fields": list(body.keys())},
    ))
    await db.commit()
    await db.refresh(current_user)
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "totp_enabled": current_user.totp_enabled,
    }


