from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..crud import exercise_suggestions, latest_weight, onboarded_profile, targets_for
from ..db import get_db
from ..deps import consent_state, rate_limit, require_consent
from ..models import CardioSession, CoachMessage, ExerciseState, User, WeightLog, Workout
from ..schemas import CoachIn
from ..services import coach as svc
from ..services import progression
from ..services.planner import EXERCISES

router = APIRouter(prefix="/coach", tags=["coach"])
DAILY_LIMIT = 30


def build_context(db: Session, user: User) -> dict:
    """Minimised summary for the coach. No name, email, ids, date of birth, exact weight or exact dates."""
    p, h = onboarded_profile(db, user.id)
    weight = latest_weight(db, user.id, h["weight_kg"])
    since = date.today() - timedelta(days=14)
    done = db.execute(select(func.count(Workout.id)).where(Workout.user_id == user.id, Workout.day >= since)).scalar() or 0
    states = db.execute(select(ExerciseState).where(ExerciseState.user_id == user.id)).scalars().all()
    notes = {EXERCISES[s.exercise_id]["name"]: f"{s.weight:g} kg. {s.note}" for s in states if s.exercise_id in EXERCISES and s.note}
    week_since = datetime.now(timezone.utc) - timedelta(days=7)
    cardio = db.execute(select(CardioSession).where(CardioSession.user_id == user.id, CardioSession.started_at >= week_since)).scalars().all()
    old = db.execute(select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.day <= date.today() - timedelta(days=28))
                     .order_by(WeightLog.day.desc()).limit(1)).scalar_one_or_none()
    return {
        "age_band": svc.age_band(h["dob"]), "goal": p.goal, "level": p.level, "days_per_week": p.days_per_week,
        "restrictions": h.get("restrictions", []), "targets": targets_for(p, h, weight),
        "weight_change_4w_kg": round(weight - float(old.kg), 1) if old else None,
        "workouts_last_14_days": done, "adherence": progression.adherence_advice(p.days_per_week, done),
        "exercise_notes": dict(list(notes.items())[:8]),
        "cardio_week": {"steps": sum(c.steps for c in cardio), "distance_m": sum(c.distance_m for c in cardio), "kcal": sum(c.kcal for c in cardio)},
    }


@router.post("", dependencies=[Depends(rate_limit("coach", 30, 600))])
def ask(body: CoachIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used = db.execute(select(func.count(CoachMessage.id)).where(CoachMessage.user_id == user.id, CoachMessage.role == "user",
                                                                CoachMessage.created_at >= today_start)).scalar() or 0
    if used >= DAILY_LIMIT:
        raise HTTPException(429, "You have reached today's coach limit. Try again tomorrow.")
    ai_ok = bool(consent_state(db, user.id).get("ai_coach")) and bool(get_settings().anthropic_api_key)
    hist_rows = db.execute(select(CoachMessage).where(CoachMessage.user_id == user.id).order_by(CoachMessage.created_at.desc()).limit(8)).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in reversed(hist_rows)]
    text, source = svc.reply(body.message, history, build_context(db, user), ai_ok)
    if source != "safety":  # crisis and medical messages are answered but never stored (data minimisation)
        db.add(CoachMessage(user_id=user.id, role="user", content=body.message))
        db.add(CoachMessage(user_id=user.id, role="assistant", content=text))
    hint = None
    if source == "rules" and not consent_state(db, user.id).get("ai_coach"):
        hint = "Turn on the AI coach in Privacy for open-ended answers. It is optional and you can switch it off any time."
    return {"reply": text, "source": source, "hint": hint}


@router.get("/history")
def history(user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    rows = db.execute(select(CoachMessage).where(CoachMessage.user_id == user.id).order_by(CoachMessage.created_at.desc()).limit(40)).scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


@router.delete("/history", status_code=204)
def clear_history(user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    db.execute(delete(CoachMessage).where(CoachMessage.user_id == user.id))
