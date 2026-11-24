"""Per-user progression model.

This is a small model that learns from each user's own logged sets (it never uses other users' data):

1. Strength estimate. Each set gives an estimated 1-rep max with the Epley formula, corrected by how
   hard the user said it felt (reserve reps: easy=3, just right=1.5, hard=0). The estimates are
   smoothed with an exponential moving average, so one bad day does not swing the plan.
2. Load recommendation. The next working weight is the dumbbell that lets the user reach the top of
   the rep range with about 2 reps in reserve. It never jumps more than one dumbbell step per session.
3. Safety valve. If the estimate drops two sessions in a row, or the user keeps missing the bottom of
   the rep range, we suggest a lighter load (deload) instead of pushing harder.
4. Adherence. Compares workouts done with workouts planned and suggests a realistic schedule.

Everything is explainable, so the app can tell the user why a weight was suggested.
"""
from .planner import size_down, size_up, snap_dumbbell

RIR = {"easy": 3.0, "good": 1.5, "hard": 0.0}
EMA_ALPHA = 0.5
HISTORY_LIMIT = 12


def e1rm(weight: float, reps: int, effort: str) -> float:
    if weight <= 0 or reps <= 0:
        return 0.0
    return weight * (1 + (reps + RIR.get(effort, 1.5)) / 30)


def session_summary(day: str, sets: list[dict]) -> dict:
    return {"day": day, "w": max(s["w"] for s in sets), "reps": [s["reps"] for s in sets], "eff": [s["eff"] for s in sets],
            "ws": [s["w"] for s in sets]}


def session_e1rm(sess: dict) -> float:
    vals = [e1rm(w, r, e) for w, r, e in zip(sess["ws"], sess["reps"], sess["eff"]) if w > 0]
    return max(vals) if vals else 0.0


def smoothed_strength(history: list[dict]) -> float:
    est = 0.0
    for sess in history:
        v = session_e1rm(sess)
        if v > 0:
            est = v if est == 0 else EMA_ALPHA * v + (1 - EMA_ALPHA) * est
    return est


def recommend(history: list[dict], current_weight: float, reps_lo: int, reps_hi: int, bodyweight: bool = False) -> dict:
    """Return {weight, note, bias} for the next session of one exercise."""
    if bodyweight:
        last = history[-1] if history else None
        if last and all(r >= reps_hi for r in last["reps"]):
            return {"weight": 0, "note": f"You hit {reps_hi} on every set. Make it harder: slow down or add a pause.", "bias": 0.0}
        return {"weight": 0, "note": f"Aim for {reps_hi} on every set.", "bias": 0.0}
    if not history:
        return {"weight": current_weight, "note": "Start here and tell us how it feels.", "bias": 0.0}

    strength = smoothed_strength(history)
    last = history[-1]
    w = last["w"] or current_weight
    # Learned bias: how often the user ends below the bottom of the range at the weight we suggested.
    recent = history[-3:]
    misses = sum(1 for s in recent for r in s["reps"] if r < reps_lo)
    total = sum(len(s["reps"]) for s in recent) or 1
    bias = round(misses / total, 2)

    drops = False
    if len(history) >= 3:
        a, b, c = (session_e1rm(history[-3]), session_e1rm(history[-2]), session_e1rm(history[-1]))
        drops = b < a * 0.97 and c < b * 0.97
    if drops or bias >= 0.5:
        nw = size_down(w)
        return {"weight": nw, "note": f"Your last sessions were tougher than planned. Take it lighter at {nw} kg and rebuild.", "bias": bias}

    all_top = all(r >= reps_hi for r in last["reps"]) and "hard" not in last["eff"]
    target = strength / (1 + (reps_hi + 2) / 30) if strength else w
    model_w = snap_dumbbell(target)
    if all_top:
        nw = size_up(w)  # one dumbbell step at a time, never a jump
        return {"weight": nw, "note": f"You hit {reps_hi} reps on every set at {w:g} kg. Go to {nw:g} kg.", "bias": bias}
    if model_w > w and last["eff"] and last["eff"].count("easy") >= len(last["eff"]) // 2 + 1:
        nw = size_up(w)
        return {"weight": nw, "note": f"Those sets felt easy at {w:g} kg. Try {nw:g} kg.", "bias": bias}
    return {"weight": w, "note": f"Stay at {w:g} kg and aim for {reps_hi} reps on every set.", "bias": bias}


def adherence_advice(planned_per_week: int, done_last_14_days: int) -> dict:
    expected = planned_per_week * 2
    rate = done_last_14_days / expected if expected else 1.0
    if expected and rate < 0.5:
        suggested = max(2, planned_per_week - 1)
        return {"rate": round(rate, 2), "suggest_days": suggested,
                "message": f"You did {done_last_14_days} of {expected} planned workouts in the last two weeks. A plan you can keep beats a perfect plan. Try {suggested} days a week."}
    if expected and rate >= 1.0 and planned_per_week < 5:
        return {"rate": round(rate, 2), "suggest_days": planned_per_week + 1,
                "message": "You hit every workout. If you feel recovered, you can add one more training day."}
    return {"rate": round(rate, 2), "suggest_days": planned_per_week, "message": "Your schedule matches what you are doing. Keep going."}


def needs_deload(workout_days_last_6_weeks: int, planned_per_week: int) -> bool:
    return planned_per_week > 0 and workout_days_last_6_weeks >= planned_per_week * 6 * 0.9
