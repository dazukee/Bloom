"""Nutrition and lifestyle: water, caffeine, alcohol, fruit and vegetables, meals.

Pure logic: no customtkinter, no file access.

References:
    FDA: up to 400 mg of caffeine a day is not generally linked to harm in
    healthy adults; people trying to conceive should ask their provider.
    Dietary Guidelines for Americans: women, 1 alcoholic drink or less a day.
    WHO: at least 400 g (about 5 portions) of fruit and vegetables a day.
"""

from datetime import datetime

CAFFEINE_LIMIT_MG = 400
ALCOHOL_LIMIT_DRINKS = 1
FRUIT_VEG_GOAL = 5
GLASS_ML = 250
WAKING_START_HOUR = 7
WAKING_END_HOUR = 22

# drink: caffeine in mg (approximate, one cup or can)
CAFFEINE_DRINKS = {"Coffee": 95, "Tea": 47, "Soft drink": 34, "Energy drink": 80}


def expected_water_by_now(goal_ml: int, now: datetime) -> int:
    """Return how much of the water goal is due by now, spread from 7:00 to 22:00."""
    hours_awake = WAKING_END_HOUR - WAKING_START_HOUR
    elapsed = now.hour + now.minute / 60 - WAKING_START_HOUR
    share = min(max(elapsed / hours_awake, 0.0), 1.0)
    return round(goal_ml * share)


def caffeine_note(total_mg: int, trying_to_conceive: bool = False) -> tuple[str, str]:
    """Return (note, tone) for today's caffeine."""
    if total_mg > CAFFEINE_LIMIT_MG:
        return "Over the 400 mg the FDA cites for healthy adults", "warning"
    if trying_to_conceive and total_mg > 0:
        return (
            "Trying to conceive? The FDA suggests asking your provider about caffeine",
            "info",
        )
    return f"{CAFFEINE_LIMIT_MG - total_mg} mg under the 400 mg daily mark", "good"


def alcohol_note(drinks: int) -> tuple[str, str]:
    """Return (note, tone) for today's alcoholic drinks."""
    if drinks == 0:
        return "No alcohol today", "good"
    if drinks <= ALCOHOL_LIMIT_DRINKS:
        return "Within the 1 drink a day guideline for women", "info"
    return "More than the 1 drink a day guideline for women", "warning"


def kcal_eaten(meals: list[dict]) -> int:
    """Return the calories of a day's meals."""
    return sum(meal["kcal"] for meal in meals)
