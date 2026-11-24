"""Workout plan generation and daily nutrition targets. Single source of truth for the mobile app."""
from datetime import date

DUMBBELLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 40, 45, 50]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _e(n, m, t, cue, start=0, one=False, bw=False, timed=False):
    return {"name": n, "muscles": m, "type": t, "cue": cue, "start": start, "one": one, "bw": bw, "timed": timed}


EXERCISES = {
    "goblet_squat": _e("Goblet squat", "Quads, glutes", "c", "Hold one dumbbell at your chest. Sit down between your hips, chest tall, heels flat.", 10, one=True),
    "db_bench": _e("Dumbbell bench press", "Chest, triceps", "c", "Lie on a bench, dumbbells over your chest. Lower to chest level, press back up.", 10),
    "db_incline": _e("Incline dumbbell press", "Upper chest", "c", "Bench at a low incline. Press up and slightly in, shoulder blades pinned back.", 8),
    "db_ohp": _e("Shoulder press", "Shoulders", "c", "Dumbbells at shoulder height. Press overhead, ribs down, no leaning back.", 6),
    "lat_raise": _e("Lateral raise", "Side shoulders", "i", "Slight bend in the elbows. Raise to shoulder height, lead with the elbows, no swinging.", 3),
    "tri_ext": _e("Overhead triceps extension", "Triceps", "i", "Hold one dumbbell with both hands overhead. Lower behind your head, elbows pointing up.", 6, one=True),
    "pushup": _e("Push-up", "Chest, triceps", "c", "Body in one line from head to heels. Chest to the floor, push away. Use your knees if needed.", bw=True),
    "db_row": _e("One-arm dumbbell row", "Back, biceps", "c", "One hand and knee on a bench. Pull the dumbbell to your hip and squeeze your back.", 10),
    "db_bent_row": _e("Bent-over row", "Back", "c", "Hinge forward with a flat back. Row both dumbbells toward your lower ribs.", 8),
    "rear_delt_fly": _e("Reverse fly", "Rear shoulders", "i", "Hinge forward, arms hanging. Open wide to the sides and squeeze your shoulder blades.", 3),
    "biceps_curl": _e("Dumbbell curl", "Biceps", "i", "Elbows pinned to your sides. Curl up, then lower slowly over 2 to 3 seconds.", 6),
    "hammer_curl": _e("Hammer curl", "Biceps, forearms", "i", "Palms facing each other. Curl up without swinging your torso.", 6),
    "db_rdl": _e("Romanian deadlift", "Hamstrings, glutes", "c", "Soft knees. Slide the dumbbells down your thighs, hips back, until your hamstrings stretch. Stand tall.", 12),
    "lunge": _e("Reverse lunge", "Quads, glutes", "c", "Step back, lower until both knees are near 90 degrees, push through the front heel.", 8),
    "bulgarian": _e("Split squat (rear foot up)", "Quads, glutes", "c", "Rear foot on a bench. Lower straight down with the front foot flat, then drive up.", 6),
    "db_hip_thrust": _e("Dumbbell hip thrust", "Glutes", "c", "Upper back on a bench, dumbbell on your hips. Drive up and squeeze your glutes at the top.", 16, one=True),
    "step_up": _e("Step-up", "Quads, glutes", "c", "Step onto a sturdy bench, drive through the whole front foot, lower slowly.", 6),
    "calf_raise": _e("Calf raise", "Calves", "i", "Rise onto your toes, pause one second at the top, lower slowly.", 12),
    "plank": _e("Plank hold", "Core", "i", "Elbows under shoulders, body in a straight line. Breathe. Log the seconds you held.", bw=True, timed=True),
    "russian_twist": _e("Russian twist", "Core", "i", "Lean back slightly, feet down, dumbbell at your chest. Rotate side to side.", 4, one=True),
}

TEMPLATES = {
    "fullA": ["goblet_squat", "db_bench", "db_row", "db_rdl", "lat_raise", "plank"],
    "fullB": ["lunge", "db_ohp", "db_bent_row", "db_hip_thrust", "biceps_curl", "plank"],
    "upperA": ["db_bench", "db_row", "db_ohp", "rear_delt_fly", "biceps_curl", "tri_ext"],
    "upperB": ["db_incline", "db_bent_row", "lat_raise", "hammer_curl", "tri_ext", "pushup"],
    "lowerA": ["goblet_squat", "db_rdl", "lunge", "calf_raise", "plank"],
    "lowerB": ["bulgarian", "db_hip_thrust", "step_up", "calf_raise", "russian_twist"],
    "push": ["db_bench", "db_ohp", "db_incline", "lat_raise", "tri_ext"],
    "pull": ["db_row", "db_bent_row", "rear_delt_fly", "biceps_curl", "hammer_curl"],
    "legs": ["goblet_squat", "db_rdl", "lunge", "db_hip_thrust", "calf_raise"],
}
TEMPLATE_NAMES = {"fullA": "Full body A", "fullB": "Full body B", "upperA": "Upper A", "upperB": "Upper B", "lowerA": "Lower A",
                  "lowerB": "Lower B", "push": "Push", "pull": "Pull", "legs": "Legs"}
SPLITS = {
    2: ([0, 3], ["fullA", "fullB"]),
    3: ([0, 2, 4], ["fullA", "fullB", "fullA"]),
    4: ([0, 1, 3, 4], ["upperA", "lowerA", "upperB", "lowerB"]),
    5: ([0, 1, 2, 4, 5], ["push", "pull", "legs", "upperA", "lowerB"]),
    6: ([0, 1, 2, 3, 4, 5], ["push", "pull", "legs", "push", "pull", "legs"]),
}
GOALS = {"lose", "muscle", "strength", "fit"}
LEVELS = {"beginner", "intermediate", "advanced"}


def rep_range(goal: str, ex: dict) -> tuple[int, int]:
    if ex["timed"]:
        return (20, 45)
    compound = {"muscle": (8, 12), "strength": (4, 6), "lose": (12, 15), "fit": (10, 12)}
    isolation = {"muscle": (10, 15), "strength": (8, 10), "lose": (12, 15), "fit": (10, 15)}
    return (compound if ex["type"] == "c" else isolation)[goal]


def sets_for(level: str, goal: str, ex: dict) -> int:
    if ex["type"] == "c":
        if level == "beginner":
            return 3
        if level == "advanced":
            return 4
        return 4 if goal in ("muscle", "strength") else 3
    return 2 if level == "beginner" else 3


def snap_dumbbell(w: float) -> float:
    return min(DUMBBELLS, key=lambda x: abs(x - w))


def size_up(w: float) -> float:
    return next((x for x in DUMBBELLS if x > w), w)


def size_down(w: float) -> float:
    return next((x for x in reversed(DUMBBELLS) if x < w), w)


def generate_plan(goal: str, level: str, days: int, suggestions: dict[str, float] | None = None) -> list[dict]:
    suggestions = suggestions or {}
    idx, names = SPLITS.get(days, SPLITS[3])
    lift = dict(zip(idx, names))
    rest_days = [i for i in range(7) if i not in lift]
    plan = []
    for i in range(7):
        if i in lift:
            key = lift[i]
            ex_ids = list(TEMPLATES[key])
            if goal == "lose" and len(ex_ids) > 5:
                ex_ids = ex_ids[:5]
            plan.append({"day": DAYS[i], "type": "lift", "name": TEMPLATE_NAMES[key], "exercises": [
                {"id": eid, "sets": sets_for(level, goal, EXERCISES[eid]),
                 "reps_lo": rep_range(goal, EXERCISES[eid])[0], "reps_hi": rep_range(goal, EXERCISES[eid])[1],
                 "start_weight": suggestions.get(eid) or (snap_dumbbell(EXERCISES[eid]["start"]) if not EXERCISES[eid]["bw"] else 0)}
                for eid in ex_ids]})
        else:
            pos = rest_days.index(i)
            last = pos == len(rest_days) - 1
            if goal == "lose" and not last:
                plan.append({"day": DAYS[i], "type": "cardio", "name": "Cardio", "note": "30 to 40 minutes of brisk walking, cycling or an easy jog. You should still be able to talk in short sentences."})
            elif goal == "fit" and pos % 2 == 0 and not last:
                plan.append({"day": DAYS[i], "type": "cardio", "name": "Active day", "note": "30 minutes of any cardio you enjoy. Finish with 5 minutes of stretching."})
            else:
                plan.append({"day": DAYS[i], "type": "rest", "name": "Rest day", "note": "Muscles grow while you recover. Take an easy walk if you like, stretch, and sleep 7 to 9 hours."})
    return plan


def age_from_dob(dob: date, today: date | None = None) -> int:
    t = today or date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))


def nutrition_targets(goal: str, sex: str, age: int, height_cm: float, weight_kg: float, days: int) -> dict:
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex == "m" else -161 if sex == "f" else -78)
    activity = 1.725 if days >= 6 else 1.55 if days >= 4 else 1.375
    tdee = bmr * activity
    floor = max(bmr, 1200)  # never plan below resting needs or 1200 kcal
    kcal = {"lose": max(tdee * 0.8, floor), "muscle": tdee * 1.1, "strength": tdee * 1.05}.get(goal, tdee)
    kcal = round(kcal / 10) * 10
    protein = round(weight_kg * {"lose": 2.0, "muscle": 1.8, "strength": 1.8, "fit": 1.4}[goal])
    protein = min(protein, round(weight_kg * 2.2))
    fat = round(kcal * 0.27 / 9)
    carbs = max(0, round((kcal - protein * 4 - fat * 9) / 4))
    return {"kcal": kcal, "protein": protein, "carbs": carbs, "fat": fat, "water_l": round(weight_kg * 0.035, 1),
            "maintenance_kcal": round(tdee / 10) * 10}
