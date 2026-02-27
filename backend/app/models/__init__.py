import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, ForeignKey,
    Enum as SAEnum, BigInteger, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ─── Enums ───────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    INVESTIGATOR = "investigator"
    ADMIN = "admin"


class CaseStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    NEEDS_INFO = "needs_info"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CasePriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseCategory(str, enum.Enum):
    CORRUPTION = "corruption"
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    FRAUD = "fraud"
    SAFETY = "safety"
    DISCRIMINATION = "discrimination"
    PROCUREMENT = "procurement"
    OTHER = "other"


class NotificationType(str, enum.Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    CASE_VIEW = "case_view"
    CASE_UPDATE = "case_update"
    CASE_ASSIGN = "case_assign"
    CASE_COMMENT = "case_comment"
    CASE_EXPORT = "case_export"
    ATTACHMENT_DOWNLOAD = "attachment_download"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    SURVEY_CREATE = "survey_create"


class PollStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


# ─── Models ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    assigned_cases: Mapped[list["Case"]] = relationship("Case", back_populates="assignee")
    comments: Mapped[list["CaseComment"]] = relationship("CaseComment", back_populates="author")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # CASE-20251201-00123
    reporter_token: Mapped[Optional[str]] = mapped_column(String(64))  # hashed token for anonymous follow-up
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)  # encrypted if non-anonymous
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped[CaseCategory] = mapped_column(SAEnum(CaseCategory), default=CaseCategory.OTHER)
    priority: Mapped[CasePriority] = mapped_column(SAEnum(CasePriority), default=CasePriority.MEDIUM)
    status: Mapped[CaseStatus] = mapped_column(SAEnum(CaseStatus), default=CaseStatus.NEW)

    # Encrypted fields
    description_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assignee: Mapped[Optional[User]] = relationship("User", back_populates="assigned_cases")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    attachments: Mapped[list["CaseAttachment"]] = relationship("CaseAttachment", back_populates="case", cascade="all, delete-orphan")
    comments: Mapped[list["CaseComment"]] = relationship("CaseComment", back_populates="case", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="case", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="case")


class CaseAttachment(Base):
    __tablename__ = "case_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="attachments")


class CaseComment(Base):
    __tablename__ = "case_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_from_reporter: Mapped[bool] = mapped_column(Boolean, default=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # internal = not sent to reporter
    content_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="comments")
    author: Mapped[Optional[User]] = relationship("User", back_populates="comments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"))
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction))
    entity_type: Mapped[Optional[str]] = mapped_column(String(64))
    entity_id: Mapped[Optional[str]] = mapped_column(String(64))
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[Optional[User]] = relationship("User", back_populates="audit_logs")
    case: Mapped[Optional[Case]] = relationship("Case", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    sent_to: Mapped[str] = mapped_column(String(255))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(32), default="sent")

    case: Mapped[Case] = relationship("Case", back_populates="notifications")


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[PollStatus] = mapped_column(SAEnum(PollStatus), default=PollStatus.DRAFT)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    questions: Mapped[list["PollQuestion"]] = relationship("PollQuestion", back_populates="poll", cascade="all, delete-orphan")


class PollQuestion(Base):
    __tablename__ = "poll_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("polls.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer)   # Telegram poll message ID
    telegram_poll_id: Mapped[Optional[str]] = mapped_column(String(64))   # Telegram internal poll ID

    poll: Mapped[Poll] = relationship("Poll", back_populates="questions")
    options: Mapped[list["PollOption"]] = relationship("PollOption", back_populates="question", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("poll_questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(String(512), nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    order: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped[PollQuestion] = relationship("PollQuestion", back_populates="options")
