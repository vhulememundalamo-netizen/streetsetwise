from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crud import latest_weight, onboarded_profile, targets_for
from ..db import get_db
from ..deps import require_consent
from ..models import FoodProfile, MealPlan, User
from ..schemas import MealPlanIn, PantryIn
from ..services import mealgen
from ..services.foods import FOODS, catalogue

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/foods")
def foods(user: User = Depends(require_consent("health_data"))):
    return {"foods": catalogue()}


@router.get("/pantry")
def get_pantry(user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    fp = db.get(FoodProfile, user.id)
    return fp.data if fp else {"foods": [], "shakes": [], "avoid": [], "meals_per_day": 4, "max_shakes": 2}


@router.put("/pantry")
def put_pantry(body: PantryIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    unknown = [f for f in body.foods if f not in FOODS]
    if unknown:
        raise HTTPException(422, f"Unknown food: {unknown[0]}")
    data = body.model_dump()
    fp = db.get(FoodProfile, user.id)
    if fp:
        fp.data = data
    else:
        db.add(FoodProfile(user_id=user.id, data=data))
    return data


@router.post("/plan")
def make_plan(body: MealPlanIn, user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    p, h = onboarded_profile(db, user.id)
    fp = db.get(FoodProfile, user.id)
    if not fp or not fp.data.get("foods"):
        raise HTTPException(409, detail={"code": "pantry_required"})
    d = fp.data
    avoid = list(d.get("avoid", [])) + list(h.get("restrictions", []))
    t = targets_for(p, h, latest_weight(db, user.id, h["weight_kg"]))
    target = {"kcal": t["kcal"], "protein": t["protein"], "carbs": t["carbs"], "fat": t["fat"]}
    days = mealgen.generate_week(target, d["foods"], d.get("shakes", []), avoid, d.get("meals_per_day", 4),
                                 d.get("max_shakes", 2), body.days)
    out = {"targets": t, "days": days}
    db.add(MealPlan(user_id=user.id, day=date.today(), plan=out))
    return out


@router.get("/plan/latest")
def latest_plan(user: User = Depends(require_consent("health_data")), db: Session = Depends(get_db)):
    row = db.execute(select(MealPlan).where(MealPlan.user_id == user.id).order_by(MealPlan.created_at.desc()).limit(1)).scalar_one_or_none()
    return {"created": row.day.isoformat(), **row.plan} if row else None
