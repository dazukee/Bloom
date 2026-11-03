"""BMI calculations for adults, plus age from a birth date.

Pure logic: no customtkinter, no file access.

Reference values:
    CDC adult categories (ages 20 and older): below 18.5 underweight,
    18.5 to below 25 healthy weight, 25 to below 30 overweight, 30 and above
    obesity.
    Asia-Pacific cut-offs (WHO Western Pacific Region, 2000): below 18.5
    underweight, 18.5 to below 23 healthy, 23 to below 25 overweight,
    25 to below 30 obesity class I, 30 and above obesity class II.
"""

from datetime import date

MIN_WEIGHT_KG = 20.0
MAX_WEIGHT_KG = 300.0
MIN_HEIGHT_CM = 50.0
MAX_HEIGHT_CM = 250.0

ADULT_AGE_YEARS = 20  # CDC: the adult categories apply from age 20.

UNDERWEIGHT = "Underweight"
HEALTHY_WEIGHT = "Healthy weight"
OVERWEIGHT = "Overweight"
OBESITY = "Obesity"
OBESITY_1 = "Obesity class I"
OBESITY_2 = "Obesity class II"

CDC = "cdc"
ASIA_PACIFIC = "asia"

# (upper limit, category, colour name). A BMI below a limit belongs to that row.
CATEGORY_TABLES = {
    CDC: [
        (18.5, UNDERWEIGHT, "fertile"),
        (25.0, HEALTHY_WEIGHT, "success"),
        (30.0, OVERWEIGHT, "warning"),
        (float("inf"), OBESITY, "danger"),
    ],
    ASIA_PACIFIC: [
        (18.5, UNDERWEIGHT, "fertile"),
        (23.0, HEALTHY_WEIGHT, "success"),
        (25.0, OVERWEIGHT, "warning"),
        (30.0, OBESITY_1, "danger"),
        (float("inf"), OBESITY_2, "danger"),
    ],
}
HEALTHY_RANGES = {CDC: (18.5, 24.9), ASIA_PACIFIC: (18.5, 22.9)}


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Return body mass index rounded to 1 decimal place.

    BMI = weight_kg / (height_cm / 100) ** 2

    Raises:
        ValueError: If the weight or height is outside its range.

    Examples:
        calculate_bmi(55, 160) returns 21.5 (test T01).
        calculate_bmi(47.36, 160) returns 18.5; the raw value is 18.4999 (T03).
    """
    if not MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG:
        raise ValueError("Weight must be between 20 and 300 kg.")
    if not MIN_HEIGHT_CM <= height_cm <= MAX_HEIGHT_CM:
        raise ValueError("Height must be between 50 and 250 cm.")
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 1)


def classify_bmi(bmi: float, standard: str = CDC) -> str:
    """Return the category for a BMI that is already rounded.

    Classify the rounded value from calculate_bmi so the label always matches
    the number on screen: 18.5 is "Healthy weight", not "Underweight" (T03).
    """
    for upper_limit, category, _ in CATEGORY_TABLES[standard]:
        if bmi < upper_limit:
            return category
    return CATEGORY_TABLES[standard][-1][1]


def category_color(bmi: float, standard: str = CDC) -> str:
    """Return the theme colour name for a BMI's category."""
    for upper_limit, _, color_name in CATEGORY_TABLES[standard]:
        if bmi < upper_limit:
            return color_name
    return "danger"


def healthy_weight_range(height_cm: float, standard: str = CDC) -> tuple[float, float]:
    """Return (lowest_kg, highest_kg) that give a healthy BMI at this height.

    Example:
        healthy_weight_range(160) returns (47.4, 63.7) (T05).
    """
    if not MIN_HEIGHT_CM <= height_cm <= MAX_HEIGHT_CM:
        raise ValueError("Height must be between 50 and 250 cm.")
    low_bmi, high_bmi = HEALTHY_RANGES[standard]
    height_m = height_cm / 100
    return round(low_bmi * height_m**2, 1), round(high_bmi * height_m**2, 1)


def calculate_age(birth_date: date, today: date) -> int:
    """Return completed years of age on `today`.

    The birthday counts once (month, day) of today reaches (month, day) of the
    birth date, so someone born on 29 February turns a year older on 1 March
    in years without a 29 February.

    Raises:
        ValueError: If birth_date is after today.
    """
    if birth_date > today:
        raise ValueError("The birth date cannot be in the future.")
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def adult_categories_apply(age_years: int) -> bool:
    """Return True when the adult categories apply (age 20 and up, T20)."""
    return age_years >= ADULT_AGE_YEARS
