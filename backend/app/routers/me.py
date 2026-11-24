"""Account, profile and data-subject rights (POPIA s5, s11, s23, s24)."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..crud import get_profile, latest_weight, targets_for
from ..db import get_db
from ..deps import audit, consent_state, current_user, rate_limit, require_consent
from ..models import (AuditLog, CardioSession, CoachMessage, Consent, ExerciseState, FoodProfile, MealPlan, User,
                      WeightLog, Workout)
from ..schemas import ConsentIn, DeleteAccountIn, ProfileIn, WeightIn
from ..security import verify_password

router = APIRouter(prefix="/me", tags=["me"])


def _profile_out(db: Session, user: User) -> dict:
    p = get_profile(db, user.id)
    h = p.health
    out = {"email": user.email_enc, "goal": p.goal, "level": p.level, "days_per_week": p.days_per_week,
           "sex": h.get("sex"), "height_cm": h.get("height_cm"), "weight_kg": h.get("weight_kg"),
           "restrictions": h.get("restrictions", []), "onboarded": bool(h.get("onboarded")), "targets": None}
    if out["onboarded"]:
        out["targets"] = targets_for(p, h, latest_weight(db, user.id, h["weight_kg"]))
    return out


@router.get("")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = get_settings()
    consents = consent_state(db, user.id)
    if consents.get("health_data"):
        profile = _profile_out(db, user)
    else:  # consent withdrawn: stop returning health information (POPIA s11, s27)
        profile = {"email": user.email_enc, "goal": "fit", "level": "beginner", "days_per_week": 3, "sex": None, "height_cm": None,
                   "weight_kg": None, "restrictions": [], "onboarded": False, "targets": None}
    return {**profile, "health_paused": not consents.get("health_data"), "consents": consents,
            "policy_version": s.policy_version, "information_officer": s.information_officer_email}


@router.put("/profile")
def update_profile(body: ProfileIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    p = get_profile(db, user.id)
    h = dict(p.health)
    h.update({"sex": body.sex, "height_cm": body.height_cm, "weight_kg": body.weight_kg,
              "restrictions": body.restrictions, "onboarded": True})
    p.health = h  # reassign so SQLAlchemy sees the change
    p.goal, p.level, p.days_per_week = body.goal, body.level, body.days_per_week
    today = date.today()
    row = db.execute(select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.day == today)).scalar_one_or_none()
    if row:
        row.kg = body.weight_kg
    else:
        db.add(WeightLog(user_id=user.id, day=today, kg=body.weight_kg))
    audit(db, user.id, "profile_updated")
    db.flush()
    return _profile_out(db, user)


@router.post("/weight", status_code=201)
def log_weight(body: WeightIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    day = body.day or date.today()
    if day > date.today():
        raise HTTPException(422, "The date cannot be in the future.")
    row = db.execute(select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.day == day)).scalar_one_or_none()
    if row:
        row.kg = body.kg
    else:
        db.add(WeightLog(user_id=user.id, day=day, kg=body.kg))
    return {"day": day.isoformat(), "kg": body.kg}


@router.get("/weights")
def weights(user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    rows = db.execute(select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.day)).scalars().all()
    return [{"day": r.day.isoformat(), "kg": r.kg} for r in rows][-120:]


# ---------- consent ----------
@router.get("/consents")
def get_consents(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"policy_version": get_settings().policy_version, "consents": consent_state(db, user.id)}


@router.post("/consents")
def set_consent(body: ConsentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.purpose == "terms_privacy" and not body.granted:
        raise HTTPException(422, "To withdraw this you can delete your account instead.")
    db.add(Consent(user_id=user.id, purpose=body.purpose, granted=body.granted, policy_version=get_settings().policy_version))
    if body.purpose == "ai_coach" and not body.granted:
        db.execute(delete(CoachMessage).where(CoachMessage.user_id == user.id))  # stop processing, remove chat history
    audit(db, user.id, "consent_changed", {"purpose": body.purpose, "granted": body.granted})
    db.flush()
    return {"consents": consent_state(db, user.id)}


# ---------- access & erasure ----------
@router.get("/export", dependencies=[Depends(rate_limit("export", 5, 3600))])
def export_my_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Everything we hold about the caller, decrypted, in one JSON document (POPIA s23)."""
    audit(db, user.id, "data_exported")

    def rows(model, order=None):
        q = select(model).where(model.user_id == user.id)
        return db.execute(q.order_by(order) if order is not None else q).scalars().all()

    p = get_profile(db, user.id)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": {"email": user.email_enc, "created_at": user.created_at.isoformat()},
        "profile": {"goal": p.goal, "level": p.level, "days_per_week": p.days_per_week, **p.health},
        "consents": [{"purpose": c.purpose, "granted": c.granted, "policy_version": c.policy_version,
                      "at": c.created_at.isoformat()} for c in rows(Consent, Consent.created_at)],
        "weights": [{"day": w.day.isoformat(), "kg": w.kg} for w in rows(WeightLog, WeightLog.day)],
        "workouts": [{"day": w.day.isoformat(), "name": w.name, "minutes": w.minutes, "sets": w.sets} for w in rows(Workout, Workout.day)],
        "exercise_state": [{"exercise": e.exercise_id, "weight": e.weight, "note": e.note, "history": e.history} for e in rows(ExerciseState)],
        "cardio": [{"started_at": c.started_at.isoformat(), "kind": c.kind, "seconds": c.seconds, "steps": c.steps,
                    "distance_m": c.distance_m, "kcal": c.kcal} for c in rows(CardioSession, CardioSession.started_at)],
        "food_profile": (rows(FoodProfile)[0].data if rows(FoodProfile) else None),
        "meal_plans": [{"day": m.day.isoformat(), "plan": m.plan} for m in rows(MealPlan, MealPlan.created_at)],
        "coach_messages": [{"role": m.role, "content": m.content, "at": m.created_at.isoformat()} for m in rows(CoachMessage, CoachMessage.created_at)],
        "security_events": [{"action": a.action, "detail": a.detail, "at": a.created_at.isoformat()}
                            for a in db.execute(select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at)).scalars()],
    }


@router.post("/delete", status_code=204, dependencies=[Depends(rate_limit("delete", 5, 3600))])
def delete_account(body: DeleteAccountIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Permanent erasure (POPIA s24). One DELETE; every table cascades from users."""
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Password is not correct.")
    audit(db, None, "account_deleted")  # no user id, no personal data
    db.delete(user)
