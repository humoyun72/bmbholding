from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_roles(*roles: UserRole):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker


require_admin = require_roles(UserRole.ADMIN)
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

    if not user or not verify_password(form_data.password, user.hashed_password):
        # SIEM: login muvaffaqiyatsiz
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Check if 2FA required
    if user.totp_enabled:
        totp_code = form_data.scopes[0] if form_data.scopes else None
        if not totp_code or not verify_totp(user.totp_secret, totp_code):
            # SIEM: 2FA muvaffaqiyatsiz
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
                detail="2FA code required or invalid",
                headers={"X-2FA-Required": "true"}
            )

    user.last_login = datetime.now(timezone.utc)
    db.add(AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN,
        ip_address=ip,
    ))
    await db.commit()

    # SIEM: muvaffaqiyatli login
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
        raise HTTPException(status_code=400, detail="2FA not set up")
    if not verify_totp(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.totp_enabled = True
    await db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/disable-2fa")
async def disable_2fa(
    body: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """2FA ni o'chirish — joriy kodni tasdiqlash kerak"""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    if not verify_totp(current_user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    return {"message": "2FA disabled successfully"}


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

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
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/change-password")
async def change_password(
    body: dict,
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
    current_user.force_password_change = False  # Majburiy o'zgartirish bajarildi

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="user",
        entity_id=str(current_user.id),
        payload={"action": "password_changed"},
    ))
    await db.commit()
    return {"message": "Parol muvaffaqiyatli o'zgartirildi"}

