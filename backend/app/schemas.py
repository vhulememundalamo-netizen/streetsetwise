from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Goal = Literal["lose", "muscle", "strength", "fit"]
Level = Literal["beginner", "intermediate", "advanced"]
Sex = Literal["m", "f", "x"]
Purpose = Literal["terms_privacy", "health_data", "ai_coach"]
Effort = Literal["easy", "good", "hard"]
CardioKind = Literal["walk", "run", "cycle"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------- auth ----------
class SignupIn(Strict):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    date_of_birth: date
    accept_terms_privacy: bool
    consent_health_data: bool
    consent_ai_coach: bool = False


class LoginIn(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(Strict):
    refresh_token: str = Field(min_length=20, max_length=200)


class ChangePasswordIn(Strict):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class DeleteAccountIn(Strict):
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------- profile & consent ----------
class ProfileIn(Strict):
    goal: Goal
    level: Level
    days_per_week: int = Field(ge=2, le=6)
    sex: Sex
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=30, le=250)
    restrictions: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("restrictions")
    @classmethod
    def _clean(cls, v):
        return [x.strip().lower()[:30] for x in v if x.strip()]


class ConsentIn(Strict):
    purpose: Purpose
    granted: bool


class WeightIn(Strict):
    day: date | None = None
    kg: float = Field(ge=30, le=250)


# ---------- workouts ----------
class SetIn(Strict):
    ex: str = Field(max_length=40)
    w: float = Field(ge=0, le=100)
    reps: int = Field(ge=0, le=200)
    eff: Effort


class WorkoutIn(Strict):
    day: date
    name: str = Field(min_length=1, max_length=60)
    minutes: int = Field(ge=1, le=300)
    sets: list[SetIn] = Field(min_length=1, max_length=120)


# ---------- cardio ----------
class CardioIn(Strict):
    kind: CardioKind
    started_at: datetime
    seconds: int = Field(ge=0, le=8 * 3600)
    steps: int = Field(default=0, ge=0, le=100_000)
    distance_m: int = Field(default=0, ge=0, le=200_000)


# ---------- nutrition ----------
class ShakeIn(Strict):
    name: str = Field(min_length=1, max_length=40)
    protein_g: float = Field(ge=1, le=80)
    kcal: float = Field(ge=10, le=600)
    carbs_g: float = Field(default=0, ge=0, le=100)
    fat_g: float = Field(default=0, ge=0, le=60)
    contains: list[str] = Field(default_factory=list, max_length=6)


class PantryIn(Strict):
    foods: list[str] = Field(max_length=60)
    shakes: list[ShakeIn] = Field(default_factory=list, max_length=5)
    avoid: list[str] = Field(default_factory=list, max_length=12)
    meals_per_day: Literal[3, 4, 5] = 4
    max_shakes: int = Field(default=2, ge=0, le=2)


class MealPlanIn(Strict):
    days: int = Field(default=1, ge=1, le=7)


# ---------- coach ----------
class CoachIn(Strict):
    message: str = Field(min_length=1, max_length=800)
