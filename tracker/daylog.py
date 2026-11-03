"""Reading and writing one day's log inside the user's data.

Pure logic: no customtkinter, no file access.

data["days"] maps a date to a dict. Every key is optional:
    cycle      flow ("spotting", "light", "medium", "heavy"),
               mucus ("dry", "sticky", "creamy", "watery", "egg white"),
               lh ("negative", "positive")
    bbt        bbt_c (float, °C), bbt_time ("HH:MM")
    journal    mood, energy, stress (1-5), symptoms [str], note (str)
    vitals     rhr (bpm), bp_sys, bp_dia (mm Hg), spo2 (%)
    sleep      sleep_h (hours), sleep_quality (1-5)
    activity   steps (int), workouts [{"type", "minutes", "met"}]
    nutrition  water_ml, caffeine_mg, alcohol (drinks), fruit_veg (portions),
               meals [{"name", "kcal"}]
"""

from datetime import date, timedelta


def get_day(data: dict, day: date) -> dict:
    """Return the log for `day`, creating an empty one if needed."""
    return data["days"].setdefault(day, {})


def peek_day(data: dict, day: date) -> dict:
    """Return the log for `day` without creating one ({} when nothing logged)."""
    return data["days"].get(day, {})


def set_value(data: dict, day: date, key: str, value) -> None:
    """Store one value in a day's log; None removes it."""
    log = get_day(data, day)
    if value is None or value == [] or value == "":
        log.pop(key, None)
    else:
        log[key] = value
    if not log:
        data["days"].pop(day, None)


def add_amount(data: dict, day: date, key: str, amount: float, low: float = 0) -> float:
    """Add `amount` to a running total such as water_ml; never below `low`."""
    log = get_day(data, day)
    total = max(low, log.get(key, 0) + amount)
    set_value(data, day, key, total if total > 0 else None)
    return total


def values_between(
    data: dict, key: str, start: date, end: date
) -> list[tuple[date, float]]:
    """Return (day, value) pairs for `key` from start to end, oldest first."""
    pairs = []
    for day in sorted(data["days"]):
        if start <= day <= end and key in data["days"][day]:
            pairs.append((day, data["days"][day][key]))
    return pairs


def last_n_days(end: date, count: int) -> list[date]:
    """Return `count` dates ending on `end`, oldest first."""
    return [end - timedelta(days=offset) for offset in range(count - 1, -1, -1)]


def logged_any(data: dict, day: date) -> bool:
    """Return True when anything at all was logged on `day`."""
    return bool(data["days"].get(day))


def logging_streak(data: dict, today: date) -> int:
    """Return how many days in a row, ending today or yesterday, have a log."""
    day = today if logged_any(data, today) else today - timedelta(days=1)
    streak = 0
    while logged_any(data, day):
        streak += 1
        day -= timedelta(days=1)
    return streak
