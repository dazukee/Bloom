"""Activity: workouts, calories burned and weekly active minutes.

Pure logic: no customtkinter, no file access.

Calories use MET values (approximate, from the Compendium of Physical
Activities): kcal per minute = MET x 3.5 x weight_kg / 200.
WHO recommends at least 150 minutes of moderate activity a week; a vigorous
minute counts as two moderate minutes.
"""

from datetime import date, timedelta

# activity: MET (approximate)
WORKOUTS = {
    "Walking": 3.5,
    "Brisk walking": 4.3,
    "Running": 9.8,
    "Cycling": 7.5,
    "Swimming": 6.0,
    "Yoga": 2.5,
    "Pilates": 3.0,
    "Strength training": 3.5,
    "Dancing": 5.0,
    "HIIT": 8.0,
    "Hiking": 6.0,
    "Badminton": 5.5,
    "Basketball": 6.5,
    "Volleyball": 4.0,
}

MODERATE_MET = 3.0
VIGOROUS_MET = 6.0
WHO_WEEKLY_MINUTES = 150


def workout_kcal(met: float, weight_kg: float, minutes: float) -> int:
    """Return calories burned in a workout, rounded."""
    return round(met * 3.5 * weight_kg / 200 * minutes)


def intensity(met: float) -> str:
    """Return "light", "moderate" or "vigorous" for a MET value."""
    if met >= VIGOROUS_MET:
        return "vigorous"
    if met >= MODERATE_MET:
        return "moderate"
    return "light"


def moderate_minutes(workouts: list[dict]) -> int:
    """Return moderate-equivalent minutes: vigorous minutes count twice."""
    total = 0
    for workout in workouts:
        level = intensity(workout["met"])
        if level == "vigorous":
            total += 2 * workout["minutes"]
        elif level == "moderate":
            total += workout["minutes"]
    return total


def active_minutes(workouts: list[dict]) -> int:
    """Return plain minutes of moderate or vigorous activity."""
    return sum(w["minutes"] for w in workouts if intensity(w["met"]) != "light")


def weekly_moderate_minutes(days: dict, today: date) -> int:
    """Return moderate-equivalent minutes over the last 7 days, today included."""
    total = 0
    for offset in range(7):
        log = days.get(today - timedelta(days=offset), {})
        total += moderate_minutes(log.get("workouts", []))
    return total


def day_kcal(workouts: list[dict], weight_kg: float | None) -> int:
    """Return calories burned in a day's workouts (0 without a weight)."""
    if weight_kg is None:
        return 0
    return sum(workout_kcal(w["met"], weight_kg, w["minutes"]) for w in workouts)
