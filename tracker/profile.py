"""The user's profile: activity levels, goals, energy needs and onboarding.

Pure logic: no customtkinter, no file access.

Energy needs use the Mifflin-St Jeor equation for women,
    BMR = 10 x weight_kg + 6.25 x height_cm - 5 x age - 161,
multiplied by the usual activity factor (1.2 to 1.9).
"""

from datetime import date

from tracker.bmi import calculate_age

# key: (label, description, activity factor)
ACTIVITY_LEVELS = {
    "sedentary": ("Mostly sitting", "Little or no exercise", 1.2),
    "light": ("Lightly active", "Light exercise 1-3 days a week", 1.375),
    "moderate": ("Moderately active", "Moderate exercise 3-5 days a week", 1.55),
    "active": ("Very active", "Hard exercise 6-7 days a week", 1.725),
    "athlete": ("Extra active", "Physical job or training twice a day", 1.9),
}

# key: (label, description)
FOCUS_OPTIONS = {
    "wellness": ("General wellness", "Habits, energy, sleep and body"),
    "cycle": ("Understand my cycle", "Periods, phases and symptoms"),
    "conceive": ("Trying to conceive", "Fertile window, BBT and ovulation"),
    "avoid": ("Avoiding pregnancy", "Cycle awareness only; not birth control"),
}
# Reasons that cannot both be true: picking one unticks the other.
OPPOSITE_FOCUS = {"conceive": "avoid", "avoid": "conceive"}

MIN_CYCLE_LENGTH = 21
MAX_CYCLE_LENGTH = 45
MIN_PERIOD_LENGTH = 2
MAX_PERIOD_LENGTH = 10


def bmr_mifflin_st_jeor(weight_kg: float, height_cm: float, age_years: int) -> float:
    """Return basal metabolic rate (kcal a day) for a woman."""
    return 10 * weight_kg + 6.25 * height_cm - 5 * age_years - 161


def daily_calorie_target(
    weight_kg: float, height_cm: float, age_years: int, activity_level: str
) -> int:
    """Return maintenance calories a day, rounded to the nearest 10."""
    factor = ACTIVITY_LEVELS[activity_level][2]
    calories = bmr_mifflin_st_jeor(weight_kg, height_cm, age_years) * factor
    return int(round(calories / 10) * 10)


def suggested_water_ml(weight_kg: float | None) -> int:
    """Return a daily drinks goal: about 33 ml per kg, between 1.5 and 3.5 L.

    A common rule of thumb, rounded to a 250 ml glass; the user can change it.
    """
    if weight_kg is None:
        return 2000
    millilitres = round(weight_kg * 33 / 250) * 250
    return int(min(max(millilitres, 1500), 3500))


def current_weight(data: dict) -> float | None:
    """Return the newest logged weight, or the profile weight."""
    weights = data.get("weights", [])
    if weights:
        newest = max(weights, key=lambda entry: entry["date"])
        return newest["weight_kg"]
    return data["profile"].get("weight_kg")


def age_of(profile: dict, today: date) -> int | None:
    """Return the user's age, or None when no birth date is saved."""
    birth_date = profile.get("birth_date")
    if birth_date is None:
        return None
    return calculate_age(birth_date, today)


def calorie_target(data: dict, today: date) -> int | None:
    """Return the user's daily calorie target, or None if details are missing."""
    profile = data["profile"]
    weight = current_weight(data)
    age = age_of(profile, today)
    if weight is None or profile.get("height_cm") is None or age is None:
        return None
    level = profile.get("activity_level", "light")
    return daily_calorie_target(weight, profile["height_cm"], age, level)


def focus_list(profile: dict) -> list[str]:
    """Return the user's reasons for using the app, e.g. ["wellness", "cycle"].

    Older files saved one reason as text, so a single string is accepted too.
    """
    value = profile.get("focus") or []
    if isinstance(value, str):
        value = [value]
    return [key for key in FOCUS_OPTIONS if key in value]


def has_focus(profile: dict, key: str) -> bool:
    """Return True if the user ticked this reason (a FOCUS_OPTIONS key)."""
    return key in focus_list(profile)


def toggle_focus(chosen: list[str], key: str) -> list[str]:
    """Tick or untick one reason and return the new list (in menu order).

    Trying to conceive and avoiding pregnancy exclude each other.
    """
    if key in chosen:
        keep = set(chosen) - {key}
    else:
        keep = (set(chosen) | {key}) - {OPPOSITE_FOCUS.get(key)}
    return [option for option in FOCUS_OPTIONS if option in keep]


def is_onboarded(profile: dict) -> bool:
    """Return True once the setup questions have been answered."""
    return bool(profile.get("onboarded"))


def initials(name: str) -> str:
    """Return up to two capital initials for an avatar, e.g. "MS"."""
    parts = [part for part in name.split() if part]
    if not parts:
        return "?"
    letters = parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")
    return letters.upper()
