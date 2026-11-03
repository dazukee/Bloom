"""Made-up demo data for presentations and testing: about 90 days of logs.

Pure logic: no customtkinter, no file access. The numbers follow realistic
patterns (a two-phase temperature curve, symptoms near the period, mood that
tracks sleep), so every chart and insight has something to show. A fixed
random seed makes the demo the same every time.
"""

import random
from datetime import date, timedelta

from tracker import activity, storage

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "bloom2026"


def make_demo_data(today: date, seed: int = 7) -> dict:
    """Return a complete, onboarded user's data ending on `today`."""
    rng = random.Random(seed)
    data = storage.new_user_data()
    data["profile"].update(
        display_name="Maria Santos",
        birth_date=date(2004, 3, 15),
        height_cm=160.0,
        weight_kg=55.4,
        activity_level="light",
        focus=["wellness", "cycle"],
        cycle_length=28,
        period_length=5,
        onboarded=True,
    )
    data["goals"].update(steps=8000, water_ml=2000, sleep_h=8.0, active_min=30)

    starts = [today - timedelta(days=offset) for offset in (104, 76, 47, 19)]
    for start in starts:
        data["periods"].append(
            {"start": start, "end": start + timedelta(days=rng.choice((4, 4, 5)))}
        )

    weight = 56.4
    for offset in range(84, -1, -7):
        weight += rng.uniform(-0.3, 0.1)
        data["weights"].append(
            {"date": today - timedelta(days=offset), "weight_kg": round(weight, 1)}
        )
    data["profile"]["weight_kg"] = data["weights"][-1]["weight_kg"]

    for offset in range(90, -1, -1):
        day = today - timedelta(days=offset)
        data["days"][day] = _demo_day(day, starts, rng)
    # Leave a few things for today so the checklist has work in it.
    for key in (
        "mood",
        "energy",
        "stress",
        "symptoms",
        "sleep_h",
        "sleep_quality",
        "steps",
        "workouts",
        "meals",
    ):
        data["days"][today].pop(key, None)
    data["days"][today]["water_ml"] = 750
    return data


def _demo_day(day: date, starts: list[date], rng: random.Random) -> dict:
    """Return one realistic day's log."""
    earlier = [s for s in starts if s <= day]
    cycle_day = (day - earlier[-1]).days + 1 if earlier else 14 + (day.toordinal() % 28)
    in_period = cycle_day <= 5
    luteal = cycle_day >= 15

    log: dict = {}
    temp = 36.62 if luteal else 36.32
    log["bbt_c"] = round(temp + rng.uniform(-0.07, 0.07), 2)
    log["bbt_time"] = f"06:{rng.randint(5, 40):02d}"

    sleep = round(rng.choice((6.0, 6.5, 7.0, 7.5, 8.0, 8.0, 8.5)), 1)
    log["sleep_h"] = sleep
    log["sleep_quality"] = 4 if sleep >= 7.5 else 3 if sleep >= 6.5 else 2
    mood = 4 if sleep >= 7.5 else 3
    if luteal and cycle_day >= 24:
        mood -= 1
    log["mood"] = max(1, min(5, mood + rng.choice((0, 0, 1, -1))))
    log["energy"] = max(1, min(5, log["mood"] + rng.choice((0, -1))))
    log["stress"] = rng.choice((2, 2, 3, 3, 4))

    symptoms = []
    if in_period:
        log["flow"] = ("heavy", "medium", "medium", "light", "spotting")[cycle_day - 1]
        symptoms += ["Cramps"] if cycle_day <= 3 else []
        symptoms += ["Fatigue"] if rng.random() < 0.5 else []
    if cycle_day >= 24:
        symptoms += rng.sample(
            ["Bloating", "Cravings", "Headache", "Breast tenderness"], k=2
        )
    if symptoms:
        log["symptoms"] = sorted(set(symptoms))
    if 12 <= cycle_day <= 14:
        log["mucus"] = "egg white"
        log["lh"] = "positive" if cycle_day == 13 else "negative"

    log["rhr"] = rng.randint(62, 70) + (2 if luteal else 0)
    if rng.random() < 0.4:
        log["bp_sys"] = rng.randint(108, 124)
        log["bp_dia"] = rng.randint(68, 79)
        log["spo2"] = rng.randint(97, 99)

    log["steps"] = rng.randint(3500, 11500)
    if rng.random() < 0.45:
        kind = rng.choice(
            ["Brisk walking", "Yoga", "Running", "Dancing", "Strength training"]
        )
        log["workouts"] = [
            {
                "type": kind,
                "minutes": rng.choice((20, 30, 45)),
                "met": activity.WORKOUTS[kind],
            }
        ]
    log["water_ml"] = rng.choice((1250, 1500, 1750, 2000, 2250))
    log["caffeine_mg"] = rng.choice((0, 95, 95, 142, 190))
    log["fruit_veg"] = rng.randint(2, 6)
    if rng.random() < 0.15:
        log["alcohol"] = 1
    if rng.random() < 0.5:
        log["meals"] = [
            {"name": "Oatmeal with banana", "kcal": 320},
            {"name": "Chicken adobo with rice", "kcal": 620},
            {"name": "Fruit and yogurt", "kcal": 210},
        ]
    return log
