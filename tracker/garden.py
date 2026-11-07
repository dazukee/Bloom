"""My Garden: a flower that grows a petal for each healthy thing done today.

Pure logic: no customtkinter, no file access. Six petals, six habits. Past days
become a garden of small flowers, and long-term habits unlock achievements.
"""

from datetime import date, timedelta

from tracker import activity, daylog

TOTAL_PETALS = 6
# key: (title, how to earn it, how much is needed)
ACHIEVEMENTS = {
    "seed": ("First Seed", "Log anything for the first time", 1),
    "sprout": ("Sprout", "Keep a 3-day logging streak", 3),
    "steady": ("Steady Stem", "Keep a 7-day logging streak", 7),
    "evergreen": ("Evergreen", "Keep a 30-day logging streak", 30),
    "full": ("Full Bloom", "Earn all 6 petals in one day", 1),
    "hydrated": ("Well Watered", "Reach your water goal on 7 days", 7),
    "rested": ("Well Rested", "Reach your sleep goal on 7 days", 7),
    "writer": ("Dear Diary", "Write 10 journal notes", 10),
    "cycle": ("In Rhythm", "Log 3 periods", 3),
}


def petals(log: dict, goals: dict) -> list[tuple[str, bool]]:
    """Return the six habits for one day's log and whether each was done."""
    minutes = activity.active_minutes(log.get("workouts", []))
    moved = log.get("steps", 0) >= goals["steps"] or minutes >= goals["active_min"]
    return [
        ("Moved enough", moved),
        ("Reached water goal", log.get("water_ml", 0) >= goals["water_ml"]),
        ("Slept enough", log.get("sleep_h", 0) >= goals["sleep_h"]),
        ("Checked in on your mood", "mood" in log),
        ("Logged a vital sign", "rhr" in log or "bp_sys" in log or "bbt_c" in log),
        ("Logged a meal", bool(log.get("meals"))),
    ]


def petal_count(data: dict, day: date) -> int:
    """Return how many petals `day` earned."""
    habits = petals(daylog.peek_day(data, day), data["goals"])
    return sum(1 for _, done in habits if done)


def next_petal(log: dict, goals: dict) -> dict | None:
    """Return the easiest petal still open as {"text", "page"}, or None.

    Quick taps come first, then what is closest to done. Sleep cannot be earned
    by the evening, so it only asks for a log when none exists yet.
    """
    habits = dict(petals(log, goals))
    if not habits["Checked in on your mood"]:
        return {"text": "Check in on your mood", "page": "journal"}
    if not habits["Logged a vital sign"]:
        return {"text": "Log your heart rate or temperature", "page": "vitals"}
    if not habits["Slept enough"] and "sleep_h" not in log:
        return {"text": "Log last night's sleep", "page": "vitals"}
    if not habits["Logged a meal"]:
        return {"text": "Log a meal", "page": "nutrition"}
    if not habits["Reached water goal"]:
        left = goals["water_ml"] - log.get("water_ml", 0)
        return {"text": f"Drink {left:,} ml more water", "page": "nutrition"}
    if not habits["Moved enough"]:
        left = goals["steps"] - log.get("steps", 0)
        return {"text": f"Walk {left:,} more steps", "page": "activity"}
    return None


def garden_days(data: dict, end: date, count: int = 28) -> list[tuple[date, int]]:
    """Return (day, petals) for the last `count` days, oldest first."""
    return [(day, petal_count(data, day)) for day in daylog.last_n_days(end, count)]


def longest_streak(data: dict) -> int:
    """Return the most days in a row that were ever logged."""
    best = current = 0
    previous = None
    for day in sorted(data["days"]):
        if not data["days"][day]:
            continue
        current = current + 1 if previous == day - timedelta(days=1) else 1
        best = max(best, current)
        previous = day
    return best


def achievement_progress(data: dict) -> dict[str, tuple[int, int]]:
    """Return {key: (how much so far, how much is needed)} for every achievement."""
    goals = data["goals"]
    logs = list(data["days"].values())
    streak = longest_streak(data)
    water = sum(1 for log in logs if log.get("water_ml", 0) >= goals["water_ml"])
    sleep = sum(1 for log in logs if log.get("sleep_h", 0) >= goals["sleep_h"])
    notes = sum(1 for log in logs if log.get("note"))
    full = any(all(done for _, done in petals(log, goals)) for log in logs)
    counts = {
        "seed": streak,
        "sprout": streak,
        "steady": streak,
        "evergreen": streak,
        "full": 1 if full else 0,
        "hydrated": water,
        "rested": sleep,
        "writer": notes,
        "cycle": len(data["periods"]),
    }
    return {
        key: (min(counts[key], need), need)
        for key, (_, _, need) in ACHIEVEMENTS.items()
    }


def earned_achievements(data: dict) -> set[str]:
    """Return the keys of every achievement the user has earned."""
    progress = achievement_progress(data)
    return {key for key, (have, need) in progress.items() if have >= need}
