"""Nutrition and lifestyle: water, caffeine, alcohol, fruit and vegetables, meals.

Pure logic: no customtkinter, no file access.

References:
    FDA: up to 400 mg of caffeine a day is not generally linked to harm in
    healthy adults. ACOG: under 200 mg while pregnant, the cautious figure for
    people trying to conceive. American Academy of Pediatrics: teens 12-18 under
    100 mg.
    Alcohol: the US Dietary Guidelines 2025-2030 say to drink less for better
    health and no longer set a number; 1 drink a day was the limit for women in
    2020-2025 and stays here as the marker. Not advised under 18.
    WHO: at least 400 g (about 5 portions) of fruit and vegetables a day.
    Nutrient needs: US Dietary Reference Intakes (NIH Office of Dietary
    Supplements). Food values: USDA FoodData Central; mixed dishes are estimates.
"""

from datetime import datetime

CAFFEINE_LIMIT_MG = 400
CAFFEINE_LIMIT_CONCEIVING_MG = 200
CAFFEINE_LIMIT_TEEN_MG = 100
ADULT_FROM_AGE = 18
ALCOHOL_LIMIT_DRINKS = 1
FRUIT_VEG_GOAL = 5
GLASS_ML = 250
WAKING_START_HOUR = 7
WAKING_END_HOUR = 22

# drink: caffeine in mg (approximate, one cup or can)
CAFFEINE_DRINKS = {"Coffee": 95, "Tea": 47, "Soft drink": 34, "Energy drink": 80}

# food: (kcal, protein in g) for one usual serving; approximate
COMMON_FOODS = {
    "Rice, 1 cup": (205, 4),
    "Pandesal, 2 pieces": (200, 6),
    "Boiled egg": (78, 6),
    "Banana": (105, 1),
    "Apple": (95, 0),
    "Milk, 1 cup": (149, 8),
    "Oatmeal, 1 cup": (158, 6),
    "Chicken adobo": (300, 25),
    "Tinola, 1 bowl": (200, 22),
    "Sinigang, 1 bowl": (280, 20),
    "Monggo, 1 cup": (212, 14),
    "Fried fish": (200, 20),
    "Tokwa, 100 g": (144, 16),
    "Instant noodles": (380, 8),
}
PROTEIN_G_PER_KG = ((14, 0.95), (19, 0.85))  # (below this age, RDA); adults below
ADULT_PROTEIN_G_PER_KG = 0.8


def expected_water_by_now(goal_ml: int, now: datetime) -> int:
    """Return how much of the water goal is due by now, spread from 7:00 to 22:00."""
    hours_awake = WAKING_END_HOUR - WAKING_START_HOUR
    elapsed = now.hour + now.minute / 60 - WAKING_START_HOUR
    share = min(max(elapsed / hours_awake, 0.0), 1.0)
    return round(goal_ml * share)


def caffeine_limit(
    age_years: int | None = None, trying_to_conceive: bool = False
) -> int:
    """Return the daily caffeine mark in mg, the lowest that applies."""
    if age_years is not None and age_years < ADULT_FROM_AGE:
        return CAFFEINE_LIMIT_TEEN_MG
    if trying_to_conceive:
        return CAFFEINE_LIMIT_CONCEIVING_MG
    return CAFFEINE_LIMIT_MG


def caffeine_note(
    total_mg: int, trying_to_conceive: bool = False, age_years: int | None = None
) -> tuple[str, str]:
    """Return (note, tone) for a day's caffeine."""
    limit = caffeine_limit(age_years, trying_to_conceive)
    if total_mg > limit:
        if limit == CAFFEINE_LIMIT_TEEN_MG:
            return "Over the 100 mg a day suggested for teens", "warning"
        if limit == CAFFEINE_LIMIT_CONCEIVING_MG:
            return "Over the 200 mg a day advised around pregnancy", "warning"
        return "Over the 400 mg the FDA cites for healthy adults", "warning"
    if trying_to_conceive and total_mg > 0:
        return f"Under the {limit} mg a day advised around pregnancy", "info"
    return f"{limit - total_mg} mg under the {limit} mg daily mark", "good"


def alcohol_note(drinks: int, age_years: int | None = None) -> tuple[str, str]:
    """Return (note, tone) for a day's alcoholic drinks."""
    if drinks == 0:
        return "No alcohol logged", "good"
    if age_years is not None and age_years < ADULT_FROM_AGE:
        return "Alcohol is not advised for anyone under 18", "warning"
    if drinks <= ALCOHOL_LIMIT_DRINKS:
        return "Within 1 drink a day; for health, less is better", "info"
    return "Over 1 drink a day; for health, less is better", "warning"


def protein_target_g(weight_kg: float, age_years: int | None = None) -> int:
    """Return the protein RDA in grams a day for this weight and age."""
    per_kg = ADULT_PROTEIN_G_PER_KG
    if age_years is not None:
        for below_age, value in PROTEIN_G_PER_KG:
            if age_years < below_age:
                per_kg = value
                break
    return round(weight_kg * per_kg)


def daily_nutrients(age_years: int | None = None) -> dict[str, tuple[str, str]]:
    """Return {nutrient: (daily amount, foods that have it)} for a girl or woman.

    Iron is highest from 14 to 50 because of monthly blood loss.
    """
    if age_years is not None and age_years < 14:
        iron, calcium, folate = 8, 1300, 300
    elif age_years is not None and age_years < 19:
        iron, calcium, folate = 15, 1300, 400
    elif age_years is not None and age_years > 50:
        iron, calcium, folate = 8, 1200, 400
    else:
        iron, calcium, folate = 18, 1000, 400
    return {
        "Iron": (f"{iron} mg", "Liver, lean meat, monggo, tokwa, kangkong, malunggay"),
        "Calcium": (f"{calcium:,} mg", "Milk, yogurt, dilis, tokwa, malunggay"),
        "Folate": (f"{folate} mcg", "Leafy greens, monggo, liver, citrus fruit"),
    }


def protein_eaten(meals: list[dict]) -> int:
    """Return the protein in grams of the meals that have a value."""
    return sum(meal.get("protein", 0) for meal in meals)


def kcal_eaten(meals: list[dict]) -> int:
    """Return the calories of a day's meals."""
    return sum(meal["kcal"] for meal in meals)
