"""Meal plan generator from what the user actually has (pantry foods + protein shakes).

Deterministic and explainable: slots take a share of the day's calories, each slot is composed from
the foods the user owns, then portions are tuned across the whole day to hit calorie and protein
targets within realistic portion limits. Protein shakes are added only if they help.
Anything we cannot achieve is reported in `warnings` instead of being hidden.
"""
from dataclasses import dataclass, field

from .foods import AVOID_TAGS, FOODS, Food

SLOTS = {
    3: [("Breakfast", "breakfast", 0.28), ("Lunch", "main", 0.36), ("Dinner", "main", 0.36)],
    4: [("Breakfast", "breakfast", 0.25), ("Lunch", "main", 0.30), ("Snack", "snack", 0.15), ("Dinner", "main", 0.30)],
    5: [("Breakfast", "breakfast", 0.22), ("Snack", "snack", 0.10), ("Lunch", "main", 0.28), ("Workout snack", "snack", 0.10), ("Dinner", "main", 0.30)],
}
GRAM_STEP = 5


@dataclass
class Item:
    name: str
    role: str
    grams: float
    kcal100: float
    p100: float
    c100: float
    f100: float
    unit_g: float
    unit_name: str
    min_g: float
    max_g: float
    adjustable: bool
    kind: str = "food"  # food | shake
    fid: str = ""

    def kcal(self):
        return self.kcal100 * self.grams / 100

    def p(self):
        return self.p100 * self.grams / 100

    def c(self):
        return self.c100 * self.grams / 100

    def f(self):
        return self.f100 * self.grams / 100

    def step(self):
        return self.unit_g if self.unit_g in (35, 50) and self.fid in ("eggs", "bread") else GRAM_STEP

    def set_grams(self, g: float):
        g = max(self.min_g, min(self.max_g, g))
        s = self.step()
        self.grams = max(self.min_g, round(g / s) * s)


def _item(food: Food, grams: float, adjustable: bool) -> Item:
    # Adjustable carbs may shrink to half the usual minimum so small calorie targets stay reachable.
    lo = food.min_g * 0.5 if (adjustable and food.role == "carb") else food.min_g
    it = Item(food.name, food.role, grams, food.kcal, food.p, food.c, food.f, food.unit_g, food.unit_name,
              lo, food.max_g * 1.15, adjustable, "food", food.id)
    it.set_grams(grams)
    return it


def _shake_item(s: dict) -> Item:
    # Per-serving label values are stored as 100 g = one serving, so grams = 100 means one serving.
    return Item(s["name"], "shake", 100, s["kcal"], s["protein_g"], s.get("carbs_g", 0), s.get("fat_g", 0),
                100, "serving", 100, 100, False, "shake", "shake:" + s["name"])


def _pick(options: list[Food], rot: int, used: set[str]) -> Food | None:
    if not options:
        return None
    ordered = options[rot % len(options):] + options[: rot % len(options)]
    for f in ordered:
        if f.id not in used:
            return f
    return ordered[0]


def _build_meal(kind: str, pool: list[Food], rot: int, used: set[str], budget: float, p_target: float) -> list[Item]:
    by = lambda role, slot: [f for f in pool if f.role == role and slot in f.slots]  # noqa: E731
    items: list[Item] = []

    def add(food: Food | None, grams: float, adjustable=False):
        if food is not None:
            used.add(food.id)
            items.append(_item(food, grams, adjustable))

    if kind == "breakfast":
        prot = _pick(by("protein", "breakfast") + by("dairy", "breakfast"), rot, used)
        carb = _pick(by("carb", "breakfast"), rot, used)
        fruit = _pick(by("fruit", "breakfast"), rot, used)
        add(prot, prot.unit_g * 2 if prot else 0, True)
        add(carb, 250 if carb and carb.id == "oats" else 105, True)
        add(fruit, fruit.unit_g if fruit else 0)
    elif kind == "main":
        prot = _pick(by("protein", "main"), rot, used)
        carb = _pick(by("carb", "main"), rot, used)
        veg = _pick(by("veg", "main"), rot, used)
        oil = next((f for f in pool if f.id == "olive_oil"), None)
        add(prot, 150, True)
        add(carb, 200, True)
        add(veg, 150)
        add(oil, 5)
    else:  # snack
        dairy = _pick(by("dairy", "snack"), rot, used)
        fruit = _pick(by("fruit", "snack"), rot, used)
        fat = _pick(by("fat", "snack"), rot + 1, used)
        add(dairy, dairy.unit_g if dairy else 0, True)
        add(fruit, fruit.unit_g if fruit else 0)
        if fat is not None and (dairy is None or fruit is None):
            add(fat, fat.unit_g)
    # Start the adjustable protein at the share of protein this meal should provide.
    for it in items:
        if it.adjustable and it.role in ("protein", "dairy") and it.p100 > 0:
            it.set_grams(p_target * 100 / it.p100 * 0.7)
    return items


def _totals(meals: list[list[Item]]) -> dict:
    allit = [i for m in meals for i in m]
    return {
        "kcal": sum(i.kcal() for i in allit),
        "protein": sum(i.p() for i in allit),
        "carbs": sum(i.c() for i in allit),
        "fat": sum(i.f() for i in allit),
    }


def _tune(meals: list[list[Item]], target: dict) -> None:
    items = [i for m in meals for i in m]
    prot_items = [i for i in items if i.adjustable and i.role in ("protein", "dairy")]
    carb_items = [i for i in items if i.adjustable and i.role == "carb"]
    for _ in range(40):
        t = _totals(meals)
        kerr, perr = target["kcal"] - t["kcal"], target["protein"] - t["protein"]
        if abs(kerr) <= 0.03 * target["kcal"] and abs(perr) <= 0.06 * target["protein"]:
            return
        changed = False
        if abs(perr) > 0.06 * target["protein"] and prot_items:
            have = sum(i.p() for i in prot_items)
            if have > 0:
                k = max(0.6, min(1.5, 1 + perr / have))
                for i in prot_items:
                    before = i.grams
                    i.set_grams(i.grams * k)
                    changed |= i.grams != before
        t = _totals(meals)
        kerr = target["kcal"] - t["kcal"]
        if abs(kerr) > 0.03 * target["kcal"] and carb_items:
            have = sum(i.kcal() for i in carb_items)
            if have > 0:
                k = max(0.6, min(1.6, 1 + kerr / have))
                for i in carb_items:
                    before = i.grams
                    i.set_grams(i.grams * k)
                    changed |= i.grams != before
        if not changed:
            return


def _fmt_amount(i: Item) -> str:
    if i.kind == "shake":
        return "1 serving"
    if i.fid == "eggs":
        n = round(i.grams / 50)
        return f"{n} egg{'s' if n != 1 else ''}"
    if i.fid == "bread":
        n = round(i.grams / 35)
        return f"{n} slice{'s' if n != 1 else ''}"
    if i.unit_name in ("banana", "apple", "tub", "tomato") and abs(i.grams / i.unit_g - round(i.grams / i.unit_g)) < 0.01:
        n = round(i.grams / i.unit_g)
        return f"{n} {i.unit_name}{'s' if n != 1 and i.unit_name != 'tub' else ''}" if i.unit_name != "tub" else f"{n} tub"
    if i.unit_name == "250 ml":
        return f"{int(i.grams)} ml"
    return f"{int(i.grams)} g"


def _score(meals, target):
    t = _totals(meals)
    return abs(t["kcal"] - target["kcal"]) / target["kcal"] + 1.5 * abs(t["protein"] - target["protein"]) / max(1, target["protein"])


def shake_tags(s: dict) -> set[str]:
    """Allergen tags for a shake: what the user declared plus a safety guess from the name."""
    tags = set(s.get("contains", []))
    name = s.get("name", "").lower()
    if any(w in name for w in ("whey", "casein", "milk", "dairy")):
        tags.add("dairy")
    if any(w in name for w in ("peanut", "almond", "nut")):
        tags.add("nuts")
    if "egg" in name:
        tags.add("egg")
    return tags


def clean_avoid(avoid: list[str]) -> tuple[set[str], set[str]]:
    """Split user avoid list into allergen tags and specific food ids."""
    tags, ids = set(), set()
    for a in avoid or []:
        a = a.strip().lower()
        (tags if a in AVOID_TAGS else ids).add(a)
    return tags, ids


def generate_day(target: dict, food_ids: list[str], shakes: list[dict], avoid: list[str], meals_per_day: int = 4,
                 max_shakes: int = 2, rot: int = 0) -> dict:
    tags, avoid_ids = clean_avoid(avoid)
    pool = [FOODS[i] for i in food_ids if i in FOODS and i not in avoid_ids and not (set(FOODS[i].tags) & tags)]
    shakes = [s for s in shakes if not (shake_tags(s) & tags)]
    slots = SLOTS.get(meals_per_day, SLOTS[4])
    warnings: list[str] = []

    mains = [f for f in pool if f.role == "protein" and "main" in f.slots]
    carbs = [f for f in pool if f.role == "carb"]
    if not mains:
        warnings.append("Add at least one protein food for lunch and dinner (for example chicken, eggs, beans, tuna).")
    if not carbs:
        warnings.append("Add a carbohydrate food such as rice, pap, potatoes or oats so portions can reach your calorie target.")
    if not [f for f in pool if f.role == "veg"]:
        warnings.append("No vegetables selected. Add some for fibre and vitamins.")

    best = None
    for k in range(0, (min(max_shakes, 2) if shakes else 0) + 1):
        used: set[str] = set()
        shake_slots = set()
        if k >= 1:
            shake_slots.add(next((n for n, kd, _ in slots if kd == "snack"), slots[0][0]))
        if k >= 2:
            shake_slots.add(slots[0][0] if slots[0][0] not in shake_slots else slots[1][0])
        meals, shake_idx = [], 0
        shake_protein = shakes[0]["protein_g"] * k if shakes else 0
        for name, kind, share in slots:
            extra = []
            if name in shake_slots:
                s = shakes[shake_idx % len(shakes)]
                shake_idx += 1
                extra = [_shake_item(s)]
            budget = max(100, share * target["kcal"] - sum(e.kcal() for e in extra))
            p_meal = max(5, (target["protein"] - shake_protein) * share)
            items = _build_meal(kind, pool, rot, used, budget, p_meal) + extra
            meals.append(items)
        _tune(meals, target)
        sc = _score(meals, target) + 0.02 * k
        if best is None or sc < best[0]:
            best = (sc, meals, k)
    _, meals, k = best

    t = _totals(meals)
    if t["protein"] < 0.85 * target["protein"]:
        warnings.append(f"Your foods reach about {t['protein']:.0f} g protein of your {target['protein']:.0f} g target. Add a protein shake or a protein food like eggs, chicken or cottage cheese.")
    if t["kcal"] < 0.9 * target["kcal"]:
        warnings.append("Your foods are not enough to reach your calorie target. Add a carb or healthy fat you enjoy.")
    elif t["kcal"] > 1.1 * target["kcal"]:
        warnings.append("This plan is above your calorie target because of minimum portion sizes. Remove a food or shake.")

    out_meals = []
    for (name, kind, share), items in zip(slots, meals):
        its = [
            {"name": i.name, "amount": _fmt_amount(i), "grams": int(i.grams) if i.kind == "food" else None, "kind": i.kind,
             "kcal": round(i.kcal()), "protein": round(i.p(), 1), "carbs": round(i.c(), 1), "fat": round(i.f(), 1)}
            for i in items
        ]
        out_meals.append({"name": name, "items": its,
                          "kcal": sum(x["kcal"] for x in its), "protein": round(sum(x["protein"] for x in its)),
                          "carbs": round(sum(x["carbs"] for x in its)), "fat": round(sum(x["fat"] for x in its))})
    return {
        "meals": out_meals,
        "totals": {k2: round(v) for k2, v in t.items()},
        "targets": {k2: round(v) for k2, v in target.items()},
        "shakes_used": k,
        "warnings": warnings,
    }


def generate_week(target, food_ids, shakes, avoid, meals_per_day=4, max_shakes=2, days=7):
    return [generate_day(target, food_ids, shakes, avoid, meals_per_day, max_shakes, rot=d) for d in range(days)]
