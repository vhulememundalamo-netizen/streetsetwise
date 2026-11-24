import pytest

from app.services import calories, mealgen, planner, progression


def test_calories_walk_uses_active_met():
    e = calories.estimate("walk", 3600, 0, 5000, 80, 175)  # 5 km/h for an hour
    assert e.method == "met" and 2.5 < e.speed_kmh < 5.5
    assert 150 < e.kcal < 280  # ~ (3.7-1) * 80 kg * 1 h


def test_calories_from_steps_only_derives_distance():
    e = calories.estimate("walk", 0, 10000, 0, 70, 170)
    assert 6000 < e.distance_m < 8000 and e.kcal > 100 and e.method == "steps"


def test_calories_rejects_impossible_speed():
    with pytest.raises(calories.ImplausibleSession):
        calories.estimate("walk", 600, 0, 5000, 70, 170)  # 30 km/h on foot


def test_calories_time_only_is_conservative():
    e = calories.estimate("walk", 1800, 0, 0, 70, 170)
    assert 0 < e.kcal < 120


PANTRY = ["eggs", "chicken_breast", "beans", "tuna", "rice", "pap", "potato", "oats", "bread", "spinach", "carrots", "tomato",
          "banana", "apple", "yoghurt", "peanut_butter", "olive_oil"]
SHAKE = [{"name": "Whey vanilla", "protein_g": 24, "kcal": 130, "carbs_g": 3, "fat_g": 2}]


@pytest.mark.parametrize("kcal,protein", [(1500, 120), (1950, 160), (2300, 120), (2900, 150)])
def test_meal_plan_hits_targets(kcal, protein):
    r = mealgen.generate_day({"kcal": kcal, "protein": protein, "carbs": 0, "fat": 0}, PANTRY, SHAKE, [], 4)
    assert abs(r["totals"]["kcal"] - kcal) / kcal < 0.06
    assert abs(r["totals"]["protein"] - protein) / protein < 0.10


def test_meal_plan_respects_allergies_and_shake_name_inference():
    r = mealgen.generate_day({"kcal": 2200, "protein": 140, "carbs": 0, "fat": 0}, PANTRY, SHAKE, ["dairy", "gluten", "egg"], 4)
    names = [i["name"] for m in r["meals"] for i in m["items"]]
    assert "Whey vanilla" not in names  # whey implies dairy
    assert not {"Eggs", "Plain low-fat yoghurt", "Wholewheat bread", "Oats (cooked)"} & set(names)


def test_meal_plan_warns_when_pantry_is_thin():
    r = mealgen.generate_day({"kcal": 2200, "protein": 150, "carbs": 0, "fat": 0}, ["banana", "apple"], [], [], 3)
    assert r["warnings"]


def test_week_rotates_foods():
    wk = mealgen.generate_week({"kcal": 2200, "protein": 140, "carbs": 0, "fat": 0}, PANTRY, SHAKE, [], 4, 2, 7)
    lunches = {tuple(i["name"] for i in d["meals"][1]["items"]) for d in wk}
    assert len(lunches) > 1


def test_plan_shape_and_goal_rules():
    plan = planner.generate_plan("lose", "beginner", 3)
    assert [d["type"] for d in plan].count("lift") == 3 and any(d["type"] == "cardio" for d in plan)
    strength = planner.generate_plan("strength", "advanced", 4)
    ex = next(d for d in strength if d["type"] == "lift")["exercises"][0]
    assert (ex["reps_lo"], ex["reps_hi"]) == (4, 6) and ex["sets"] == 4


def test_nutrition_never_below_floor():
    t = planner.nutrition_targets("lose", "f", 40, 155, 52, 2)
    assert t["kcal"] >= 1200 and t["protein"] <= round(52 * 2.2)


def hist(w, reps, eff, n=1):
    return [{"day": f"2026-01-{i + 1:02d}", "w": w, "ws": [w] * len(reps), "reps": reps, "eff": eff} for i in range(n)]


def test_progression_goes_up_one_step_when_top_of_range_hit():
    r = progression.recommend(hist(10, [12, 12, 12], ["good", "good", "good"]), 10, 8, 12)
    assert r["weight"] == 12  # one dumbbell step, not a jump


def test_progression_holds_when_not_at_top():
    r = progression.recommend(hist(10, [10, 9, 9], ["good", "hard", "hard"]), 10, 8, 12)
    assert r["weight"] == 10


def test_progression_deloads_when_missing_range():
    r = progression.recommend(hist(14, [5, 5, 4], ["hard", "hard", "hard"], n=2), 14, 8, 12)
    assert r["weight"] < 14


def test_progression_deload_on_two_dropping_sessions():
    h = [{"day": "d1", "w": 14, "ws": [14], "reps": [10], "eff": ["good"]},
         {"day": "d2", "w": 14, "ws": [14], "reps": [8], "eff": ["good"]},
         {"day": "d3", "w": 14, "ws": [14], "reps": [8], "eff": ["hard"]}]
    assert progression.recommend(h, 14, 6, 12)["weight"] < 14


def test_adherence_suggests_fewer_days_when_missing():
    assert progression.adherence_advice(4, 2)["suggest_days"] == 3
