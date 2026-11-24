"""Food table used by the meal generator.

Values are approximate per 100 g of the food as eaten (cooked where that is how it is eaten),
based on typical USDA and South African (SAFOODS) figures. Good enough for planning, not for
clinical diets. Users can add their own protein shakes with exact label values.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Food:
    id: str
    name: str
    role: str  # protein | carb | veg | fat | fruit | dairy
    kcal: float
    p: float
    c: float
    f: float
    unit_g: float  # one natural unit (egg, slice, banana) or serving step
    unit_name: str
    min_g: float
    max_g: float
    slots: tuple[str, ...]  # breakfast | main | snack
    tags: tuple[str, ...] = field(default_factory=tuple)  # allergens / diet flags


def _f(*a, **k):
    return Food(*a, **k)


FOODS: dict[str, Food] = {
    x.id: x
    for x in [
        _f("eggs", "Eggs", "protein", 143, 12.6, 0.7, 9.5, 50, "egg", 100, 250, ("breakfast", "main"), ("egg", "animal")),
        _f("chicken_breast", "Chicken breast", "protein", 165, 31, 0, 3.6, 100, "100 g", 100, 250, ("main",), ("meat", "animal")),
        _f("chicken_thigh", "Chicken thigh (no skin)", "protein", 209, 26, 0, 10.9, 100, "100 g", 100, 250, ("main",), ("meat", "animal")),
        _f("beef_mince", "Lean beef mince", "protein", 215, 26, 0, 12, 100, "100 g", 100, 220, ("main",), ("meat", "animal")),
        _f("hake", "Hake", "protein", 110, 22, 0, 2, 100, "100 g", 100, 250, ("main",), ("fish", "animal")),
        _f("tuna", "Tuna (canned in water)", "protein", 116, 26, 0, 0.8, 100, "100 g", 80, 200, ("main",), ("fish", "animal")),
        _f("pilchards", "Pilchards in tomato", "protein", 140, 17, 3, 6.5, 100, "100 g", 100, 200, ("main",), ("fish", "animal")),
        _f("beans", "Beans (cooked)", "protein", 127, 8.7, 22.8, 0.5, 100, "100 g", 100, 300, ("main",), ()),
        _f("lentils", "Lentils (cooked)", "protein", 116, 9, 20, 0.4, 100, "100 g", 100, 300, ("main",), ()),
        _f("cottage_cheese", "Cottage cheese", "dairy", 98, 11, 3.4, 4.3, 100, "100 g", 100, 250, ("breakfast", "snack"), ("dairy", "animal")),
        _f("yoghurt", "Plain low-fat yoghurt", "dairy", 63, 5.3, 7, 1.6, 175, "tub", 175, 350, ("breakfast", "snack"), ("dairy", "animal")),
        _f("amasi", "Amasi (maas)", "dairy", 62, 3.3, 4.7, 3.3, 250, "250 ml", 250, 500, ("breakfast", "snack"), ("dairy", "animal")),
        _f("milk", "Low-fat milk", "dairy", 46, 3.4, 4.9, 1.5, 250, "250 ml", 250, 500, ("breakfast", "snack"), ("dairy", "animal")),
        _f("rice", "Rice (cooked)", "carb", 130, 2.7, 28, 0.3, 50, "50 g", 100, 400, ("main",), ()),
        _f("pap", "Pap (stiff maize porridge)", "carb", 95, 2.0, 20, 0.5, 50, "50 g", 100, 450, ("main", "breakfast"), ()),
        _f("potato", "Potato (boiled)", "carb", 87, 1.9, 20, 0.1, 100, "100 g", 150, 450, ("main",), ()),
        _f("sweet_potato", "Sweet potato (baked)", "carb", 90, 2, 21, 0.1, 100, "100 g", 150, 400, ("main",), ()),
        _f("pasta", "Pasta (cooked)", "carb", 158, 5.8, 31, 0.9, 50, "50 g", 100, 350, ("main",), ("gluten",)),
        _f("oats", "Oats (cooked)", "carb", 71, 2.5, 12, 1.5, 50, "50 g", 200, 500, ("breakfast",), ("gluten",)),
        _f("bread", "Wholewheat bread", "carb", 247, 13, 41, 3.4, 35, "slice", 70, 210, ("breakfast", "snack", "main"), ("gluten",)),
        _f("spinach", "Spinach or morogo (cooked)", "veg", 23, 3, 3.6, 0.3, 50, "50 g", 100, 250, ("main",), ()),
        _f("cabbage", "Cabbage (cooked)", "veg", 25, 1.3, 6, 0.1, 50, "50 g", 100, 250, ("main",), ()),
        _f("carrots", "Carrots (cooked)", "veg", 35, 0.8, 8, 0.2, 50, "50 g", 80, 200, ("main",), ()),
        _f("broccoli", "Broccoli (cooked)", "veg", 35, 2.4, 7, 0.4, 50, "50 g", 100, 250, ("main",), ()),
        _f("tomato", "Tomato", "veg", 18, 0.9, 3.9, 0.2, 100, "tomato", 100, 250, ("main", "breakfast"), ()),
        _f("butternut", "Butternut (cooked)", "veg", 45, 1, 12, 0.1, 50, "50 g", 100, 250, ("main",), ()),
        _f("banana", "Banana", "fruit", 89, 1.1, 23, 0.3, 120, "banana", 120, 240, ("breakfast", "snack"), ()),
        _f("apple", "Apple", "fruit", 52, 0.3, 14, 0.2, 180, "apple", 180, 360, ("breakfast", "snack"), ()),
        _f("peanut_butter", "Peanut butter", "fat", 588, 25, 20, 50, 15, "tbsp", 15, 45, ("breakfast", "snack"), ("nuts",)),
        _f("peanuts", "Peanuts", "fat", 567, 26, 16, 49, 30, "handful", 30, 60, ("snack",), ("nuts",)),
        _f("olive_oil", "Olive oil", "fat", 884, 0, 0, 100, 5, "tsp", 5, 15, ("main",), ()),
        _f("avocado", "Avocado", "fat", 160, 2, 9, 15, 50, "half", 50, 100, ("main", "breakfast"), ()),
        _f("cheese", "Cheddar cheese", "fat", 403, 25, 1.3, 33, 30, "30 g", 20, 60, ("breakfast", "snack"), ("dairy", "animal")),
    ]
}

# User-facing avoid keywords map to tags.
AVOID_TAGS = {"dairy", "gluten", "nuts", "egg", "fish", "meat", "animal"}


def catalogue() -> list[dict]:
    return [
        {"id": f.id, "name": f.name, "role": f.role, "kcal": f.kcal, "protein": f.p, "carbs": f.c, "fat": f.f, "tags": list(f.tags)}
        for f in FOODS.values()
    ]
