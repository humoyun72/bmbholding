from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models import UserRole, CaseStatus


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserRole
    username: str
    full_name: Optional[str]
    email: Optional[str] = None
    totp_enabled: bool
    force_password_change: bool = False


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    totp_enabled: bool
    force_password_change: bool = False
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v: UUID) -> str:
        return str(v)


class Setup2FAResponse(BaseModel):
    secret: str
    qr_code: str
    uri: str


class Verify2FARequest(BaseModel):
    code: str


# ─── Cases ────────────────────────────────────────────────────────────────────

class CaseListResponse(BaseModel):
    id: str
    external_id: str
    category: str
    priority: str
    status: str
    title: Optional[str]
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str]
    attachments_count: int


class CaseResponse(CaseListResponse):
    description: str
    comments: list[dict] = []
    attachments: list[dict] = []


class CaseDetailResponse(CaseResponse):
    pass


class AssignCaseRequest(BaseModel):
    user_id: Optional[str] = None


class ChangeStatusRequest(BaseModel):
    status: CaseStatus


class AddCommentRequest(BaseModel):
    content: str
    is_internal: bool = False


class CaseCommentResponse(BaseModel):
    id: str
    content: str
    is_from_reporter: bool
    is_internal: bool
    author: Optional[str]
    created_at: datetime
