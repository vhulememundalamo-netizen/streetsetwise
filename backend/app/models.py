"""Data model.

Data minimisation (POPIA condition 3/4): we store the least we need.
- No IP addresses, device ids, or advertising ids.
- Cardio keeps summaries (steps, distance, time, calories). Raw GPS routes never leave the phone.
- Health-related values are encrypted per field (EncryptedJSON).
- Every table that holds user data has user_id with ON DELETE CASCADE, so erasing a user is one DELETE.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .security import EncryptedJSON


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def UID() -> ForeignKey:
    return ForeignKey("users.id", ondelete="CASCADE")


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # HMAC, for lookup only
    email_enc = mapped_column(EncryptedJSON, nullable=False)  # readable only through the app key
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Consent(Base):
    """Append-only ledger. The current state of a purpose is its most recent row (POPIA s11, s27)."""

    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    purpose: Mapped[str] = mapped_column(String(32))  # terms_privacy | health_data | ai_coach
    granted: Mapped[bool] = mapped_column(Boolean)
    policy_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    family: Mapped[str] = mapped_column(String(36), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[str] = mapped_column(String(36), UID(), primary_key=True)
    goal: Mapped[str] = mapped_column(String(16))  # lose | muscle | strength | fit
    level: Mapped[str] = mapped_column(String(16))  # beginner | intermediate | advanced
    days_per_week: Mapped[int] = mapped_column(Integer)
    # Encrypted blob: {dob, sex, height_cm, weight_kg, restrictions: [..], name}
    health = mapped_column(EncryptedJSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class WeightLog(Base):
    __tablename__ = "weight_logs"
    __table_args__ = (UniqueConstraint("user_id", "day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    day: Mapped[date] = mapped_column(Date)
    kg = mapped_column(EncryptedJSON, nullable=False)


class Workout(Base):
    __tablename__ = "workouts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String(60))
    minutes: Mapped[int] = mapped_column(Integer)
    sets = mapped_column(EncryptedJSON, nullable=False)  # [{ex, w, reps, eff}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ExerciseState(Base):
    """Per-user, per-exercise learning state used by the progression model."""

    __tablename__ = "exercise_state"
    user_id: Mapped[str] = mapped_column(String(36), UID(), primary_key=True)
    exercise_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str] = mapped_column(String(200), default="")
    history = mapped_column(EncryptedJSON, nullable=False)  # last N sessions [{day,w,reps:[..],eff:[..]}]
    effort_bias: Mapped[float] = mapped_column(Float, default=0.0)  # learned: + means user finds it harder than reps suggest


class CardioSession(Base):
    __tablename__ = "cardio_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(12))  # walk | run | cycle
    seconds: Mapped[int] = mapped_column(Integer)
    steps: Mapped[int] = mapped_column(Integer, default=0)
    distance_m: Mapped[int] = mapped_column(Integer, default=0)
    kcal: Mapped[int] = mapped_column(Integer, default=0)


class FoodProfile(Base):
    """What the user has at home: pantry foods and protein shakes. One row per user."""

    __tablename__ = "food_profiles"
    user_id: Mapped[str] = mapped_column(String(36), UID(), primary_key=True)
    data = mapped_column(EncryptedJSON, nullable=False)  # {foods: [food_id], shakes: [{...}], avoid: [..]}
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class MealPlan(Base):
    __tablename__ = "meal_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    day: Mapped[date] = mapped_column(Date)
    plan = mapped_column(EncryptedJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CoachMessage(Base):
    __tablename__ = "coach_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(36), UID(), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content = mapped_column(EncryptedJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    """Security events only. Never contains health data or message content.
    user_id is set to NULL when the user is erased, so the trail survives without personal data."""

    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


Index("ix_audit_created", AuditLog.created_at)
