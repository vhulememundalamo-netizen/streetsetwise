"""Estimated energy cost of cardio.

Method: MET values from the Compendium of Physical Activities, interpolated by speed.
We report ACTIVE calories (MET - 1) x kg x hours, because resting energy is already inside the
daily calorie target. This is an estimate: expect +/- 20% error, more for steps-only data.
"""
from dataclasses import dataclass

# (speed km/h, MET)
_TABLES = {
    "walk": [(2.0, 2.0), (3.2, 2.8), (4.0, 3.0), (4.8, 3.5), (5.6, 4.3), (6.4, 5.0), (7.2, 6.3)],
    "run": [(8.0, 8.3), (9.7, 9.8), (11.3, 11.0), (12.9, 11.8), (14.5, 12.8), (16.1, 14.5)],
    "cycle": [(10.0, 3.5), (16.0, 6.8), (19.0, 8.0), (22.0, 10.0), (25.0, 12.0), (30.0, 14.0)],
}
MAX_SPEED = {"walk": 9.0, "run": 25.0, "cycle": 55.0}  # km/h, plausibility ceiling
# kcal per kg per km, used when only steps/distance are known (no duration)
_KCAL_PER_KG_KM = {"walk": 0.5, "run": 0.95, "cycle": 0.3}
_STRIDE_FACTOR = {"walk": 0.415, "run": 0.60}  # x height = metres per step


def met_for(kind: str, speed_kmh: float) -> float:
    tbl = _TABLES[kind]
    if speed_kmh <= tbl[0][0]:
        return tbl[0][1]
    if speed_kmh >= tbl[-1][0]:
        return tbl[-1][1]
    for (s0, m0), (s1, m1) in zip(tbl, tbl[1:]):
        if s0 <= speed_kmh <= s1:
            return m0 + (m1 - m0) * (speed_kmh - s0) / (s1 - s0)
    return tbl[-1][1]


def distance_from_steps(kind: str, steps: int, height_cm: float) -> int:
    f = _STRIDE_FACTOR.get(kind)
    return int(round(steps * height_cm / 100 * f)) if f else 0


@dataclass
class CardioEstimate:
    distance_m: int
    kcal: int
    speed_kmh: float
    met: float
    method: str  # "met" | "distance" | "steps"


class ImplausibleSession(ValueError):
    pass


def estimate(kind: str, seconds: int, steps: int, distance_m: int, weight_kg: float, height_cm: float) -> CardioEstimate:
    if kind not in _TABLES:
        raise ImplausibleSession("Unknown cardio type")
    if seconds < 0 or seconds > 8 * 3600:
        raise ImplausibleSession("Duration looks wrong")
    dist = distance_m
    method = "met"
    if dist <= 0 and steps > 0:
        dist = distance_from_steps(kind, steps, height_cm)
        method = "steps"
    if seconds >= 60 and dist > 0:
        speed = dist / 1000 / (seconds / 3600)
        if speed > MAX_SPEED[kind]:
            raise ImplausibleSession(f"A {kind} speed of {speed:.0f} km/h is not realistic. Check the distance.")
        met = met_for(kind, speed)
        kcal = max(0.0, met - 1.0) * weight_kg * seconds / 3600
        return CardioEstimate(int(dist), int(round(kcal)), round(speed, 2), round(met, 2), method)
    if dist > 0:
        kcal = _KCAL_PER_KG_KM[kind] * weight_kg * dist / 1000
        return CardioEstimate(int(dist), int(round(kcal)), 0.0, 0.0, "distance" if method == "met" else "steps")
    if seconds >= 60:
        # time only: assume an easy pace so we never overstate
        default_speed = {"walk": 4.5, "run": 8.5, "cycle": 16.0}[kind]
        met = met_for(kind, default_speed)
        kcal = max(0.0, met - 1.0) * weight_kg * seconds / 3600
        return CardioEstimate(0, int(round(kcal)), 0.0, round(met, 2), "met")
    return CardioEstimate(0, 0, 0.0, 0.0, "met")
