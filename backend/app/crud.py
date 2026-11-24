from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ExerciseState, Profile, WeightLog
from .services.planner import age_from_dob, nutrition_targets


def get_profile(db: Session, user_id: str) -> Profile:
    p = db.get(Profile, user_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    return p


def onboarded_profile(db: Session, user_id: str) -> tuple[Profile, dict]:
    p = get_profile(db, user_id)
    h = p.health
    if not h.get("onboarded") or not h.get("weight_kg") or not h.get("height_cm"):
        raise HTTPException(409, detail={"code": "onboarding_required"})
    return p, h


def latest_weight(db: Session, user_id: str, fallback: float) -> float:
    row = db.execute(select(WeightLog).where(WeightLog.user_id == user_id).order_by(WeightLog.day.desc()).limit(1)).scalar_one_or_none()
    return float(row.kg) if row else float(fallback)


def targets_for(p: Profile, h: dict, weight: float) -> dict:
    age = age_from_dob(date.fromisoformat(h["dob"]))
    return nutrition_targets(p.goal, h.get("sex", "x"), age, h["height_cm"], weight, p.days_per_week)


def exercise_suggestions(db: Session, user_id: str) -> dict[str, float]:
    rows = db.execute(select(ExerciseState).where(ExerciseState.user_id == user_id)).scalars().all()
    return {r.exercise_id: r.weight for r in rows if r.weight}
