from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crud import exercise_suggestions, latest_weight, onboarded_profile, targets_for
from ..db import get_db
from ..deps import require_consent
from ..models import CardioSession, ExerciseState, User, Workout
from ..schemas import CardioIn, WorkoutIn
from ..services import calories, progression
from ..services.planner import DUMBBELLS, EXERCISES, generate_plan, rep_range

router = APIRouter(tags=["training"])
HEALTH = Depends(require_consent("health_data"))


@router.get("/plan")
def get_plan(user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    p, h = onboarded_profile(db, user.id)
    plan = generate_plan(p.goal, p.level, p.days_per_week, exercise_suggestions(db, user.id))
    notes = {r.exercise_id: r.note for r in db.execute(select(ExerciseState).where(ExerciseState.user_id == user.id)).scalars()}
    used = {e["id"] for d in plan if d["type"] == "lift" for e in d["exercises"]}
    since = date.today() - timedelta(days=14)
    done = db.execute(select(Workout.day).where(Workout.user_id == user.id, Workout.day >= since)).scalars().all()
    weight = latest_weight(db, user.id, h["weight_kg"])
    return {
        "plan": plan,
        "exercises": {k: v for k, v in EXERCISES.items() if k in used},
        "notes": {k: v for k, v in notes.items() if k in used},
        "dumbbells": DUMBBELLS,
        "targets": targets_for(p, h, weight),
        "adherence": progression.adherence_advice(p.days_per_week, len(done)),
    }


@router.post("/workouts", status_code=201)
def save_workout(body: WorkoutIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    p, _ = onboarded_profile(db, user.id)
    if body.day > date.today() + timedelta(days=1):
        raise HTTPException(422, "The date cannot be in the future.")
    unknown = {s.ex for s in body.sets} - set(EXERCISES)
    if unknown:
        raise HTTPException(422, "Unknown exercise")
    db.add(Workout(user_id=user.id, day=body.day, name=body.name, minutes=body.minutes, sets=[s.model_dump() for s in body.sets]))

    nxt: dict[str, dict] = {}
    by_ex: dict[str, list[dict]] = {}
    for s in body.sets:
        by_ex.setdefault(s.ex, []).append(s.model_dump())
    for ex_id, sets in by_ex.items():
        ex = EXERCISES[ex_id]
        lo, hi = rep_range(p.goal, ex)
        state = db.get(ExerciseState, (user.id, ex_id))
        if state is None:
            state = ExerciseState(user_id=user.id, exercise_id=ex_id, weight=0, note="", history=[])
            db.add(state)
        hist = list(state.history or [])
        hist.append(progression.session_summary(body.day.isoformat(), sets))
        hist = hist[-progression.HISTORY_LIMIT:]
        rec = progression.recommend(hist, hist[-1]["w"], lo, hi, bodyweight=ex["bw"])
        state.history, state.weight, state.note, state.effort_bias = hist, rec["weight"], rec["note"], rec["bias"]
        nxt[ex_id] = {"weight": rec["weight"], "note": rec["note"]}
    return {"saved": True, "next": nxt}


@router.get("/workouts")
def list_workouts(limit: int = Query(20, ge=1, le=100), user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    rows = db.execute(select(Workout).where(Workout.user_id == user.id).order_by(Workout.day.desc(), Workout.created_at.desc()).limit(limit)).scalars().all()
    return [{"id": w.id, "day": w.day.isoformat(), "name": w.name, "minutes": w.minutes, "sets": len(w.sets)} for w in rows]


# ---------- cardio ----------
def _estimate(db: Session, user: User, body: CardioIn):
    _, h = onboarded_profile(db, user.id)
    weight = latest_weight(db, user.id, h["weight_kg"])
    try:
        return calories.estimate(body.kind, body.seconds, body.steps, body.distance_m, weight, h["height_cm"])
    except calories.ImplausibleSession as e:
        raise HTTPException(422, str(e))


def _est_out(est: calories.CardioEstimate) -> dict:
    return {"distance_m": est.distance_m, "kcal": est.kcal, "speed_kmh": est.speed_kmh, "met": est.met, "method": est.method,
            "note": "Active calories only (above resting). An estimate with roughly 20% error."}


@router.post("/cardio/estimate")
def cardio_estimate(body: CardioIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    return _est_out(_estimate(db, user, body))


@router.post("/cardio", status_code=201)
def save_cardio(body: CardioIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    if body.started_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(422, "The start time cannot be in the future.")
    est = _estimate(db, user, body)
    started = body.started_at if body.started_at.tzinfo else body.started_at.replace(tzinfo=timezone.utc)
    row = CardioSession(user_id=user.id, started_at=started, kind=body.kind, seconds=body.seconds, steps=body.steps,
                        distance_m=est.distance_m, kcal=est.kcal)
    db.add(row)
    db.flush()
    return {"id": row.id, **_est_out(est)}


@router.get("/cardio")
def list_cardio(days: int = Query(30, ge=1, le=365), user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(select(CardioSession).where(CardioSession.user_id == user.id, CardioSession.started_at >= since)
                      .order_by(CardioSession.started_at.desc())).scalars().all()
    return [{"id": c.id, "started_at": c.started_at.isoformat(), "kind": c.kind, "seconds": c.seconds, "steps": c.steps,
             "distance_m": c.distance_m, "kcal": c.kcal} for c in rows]


@router.get("/cardio/summary")
def cardio_summary(tz_offset_minutes: int = Query(0, ge=-720, le=840), user: User = Depends(require_consent("health_data")),
                   db: Session = Depends(get_db)):
    tz = timezone(timedelta(minutes=tz_offset_minutes))
    today = datetime.now(tz).date()
    since = datetime.now(timezone.utc) - timedelta(days=8)
    rows = db.execute(select(CardioSession).where(CardioSession.user_id == user.id, CardioSession.started_at >= since)).scalars().all()
    days = {(today - timedelta(days=i)).isoformat(): {"steps": 0, "distance_m": 0, "kcal": 0, "seconds": 0} for i in range(7)}
    for c in rows:
        d = c.started_at.astimezone(tz).date().isoformat()
        if d in days:
            for k, v in (("steps", c.steps), ("distance_m", c.distance_m), ("kcal", c.kcal), ("seconds", c.seconds)):
                days[d][k] += v
    ordered = [{"day": k, **v} for k, v in sorted(days.items())]
    return {"today": days[today.isoformat()], "week": ordered,
            "week_total": {k: sum(x[k] for x in ordered) for k in ("steps", "distance_m", "kcal", "seconds")}}
