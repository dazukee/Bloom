"""Turn text typed on the screens into checked values.

Pure logic: no customtkinter, no file access.

Every function returns a clean value or raises ValueError. The screen shows
str(error) to the user as it is, so each message says what is wrong and how to
fix it. Username and password rules live in auth.py.
"""

import math
from datetime import date, datetime

from tracker import units
from tracker.bmi import (
    MAX_HEIGHT_CM,
    MAX_WEIGHT_KG,
    MIN_HEIGHT_CM,
    MIN_WEIGHT_KG,
    calculate_age,
)

DATE_FORMAT = "%Y-%m-%d"
MIN_AGE_YEARS = 10
MAX_AGE_YEARS = 120
MAX_NAME_LENGTH = 30
MIN_TEMP_C = 34.0
MAX_TEMP_C = 42.0


def parse_number(
    text: str,
    label: str,
    low: float,
    high: float,
    unit: str = "",
    example: str = "",
    whole: bool = False,
) -> float:
    """Return a number typed by the user, checked against a range.

    Args:
        text: What the user typed.
        label: The field's name in messages, e.g. "Weight".
        low: The smallest allowed value.
        high: The largest allowed value.
        unit: Unit shown in the range message, e.g. "kg".
        example: A sample value for the "must be a number" message.
        whole: True when only whole numbers are allowed.

    Returns:
        The number (an int when `whole` is True).

    Raises:
        ValueError: "Enter your <label>.", "<Label> must be a number, e.g. ...",
            "<Label> must be a whole number." or "<Label> must be between ...".
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError(f"Enter your {label.lower()}.")
    try:
        if "_" in cleaned:  # float() accepts "1_000"; a person never means that
            raise ValueError
        value = float(cleaned)
    except ValueError:
        hint = f", e.g. {example}" if example else ""
        raise ValueError(f"{label} must be a number{hint}.") from None
    if not math.isfinite(value):  # float() accepts "nan" and "inf"
        hint = f", e.g. {example}" if example else ""
        raise ValueError(f"{label} must be a number{hint}.")
    if whole and value != int(value):
        raise ValueError(f"{label} must be a whole number.")
    if not low <= value <= high:
        unit_text = f" {unit}" if unit else ""
        raise ValueError(f"{label} must be between {low:g} and {high:g}{unit_text}.")
    return int(value) if whole else value


def parse_weight(text: str, unit: str = "kg") -> float:
    """Return a weight in kilograms; the user may type kg or lb.

    Raises:
        ValueError: "Enter your weight." for blank text,
            "Weight must be a number, e.g. 55.5." for text like "abc" (T06),
            "Weight must be between 20 and 300 kg." when out of range.
    """
    if unit == "lb":
        low = round(units.kg_to_lb(MIN_WEIGHT_KG))
        high = round(units.kg_to_lb(MAX_WEIGHT_KG))
        pounds = parse_number(text, "Weight", low, high, "lb", "121")
        return units.lb_to_kg(pounds)
    return parse_number(text, "Weight", MIN_WEIGHT_KG, MAX_WEIGHT_KG, "kg", "55.5")


def parse_height(text: str) -> float:
    """Return a height in centimetres.

    Raises:
        ValueError: "Enter your height.", "Height must be a number, e.g. 160.",
            "Height must be between 50 and 250 cm." (T07); values above 0 and
            below 3 add " Did you enter metres? Type 160 for 1.60 m." (T08).
    """
    try:
        return parse_number(text, "Height", MIN_HEIGHT_CM, MAX_HEIGHT_CM, "cm", "160")
    except ValueError as error:
        message = str(error)
        try:
            value = float(text.strip())
        except ValueError:
            raise ValueError(message) from None
        if 0 < value < 3:
            message += " Did you enter metres? Type 160 for 1.60 m."
        raise ValueError(message) from None


def parse_feet_inches(feet_text: str, inches_text: str) -> float:
    """Return a height in centimetres from feet and inches boxes.

    A blank inches box counts as 0.
    """
    feet = parse_number(feet_text, "Feet", 1, 8, "ft", "5", whole=True)
    inches = 0.0
    if inches_text.strip():
        inches = parse_number(inches_text, "Inches", 0, 11.9, "in", "4")
    centimetres = units.ft_in_to_cm(feet, inches)
    if not MIN_HEIGHT_CM <= centimetres <= MAX_HEIGHT_CM:
        raise ValueError("Height must be between 1 ft 8 in and 8 ft 2 in.")
    return round(centimetres, 1)


def parse_temperature(text: str, unit: str = "c") -> float:
    """Return a body temperature in °C; the user may type °C or °F."""
    if unit == "f":
        low = round(units.c_to_f(MIN_TEMP_C), 1)
        high = round(units.c_to_f(MAX_TEMP_C), 1)
        value = parse_number(text, "Temperature", low, high, "°F", "97.7")
        return round(units.f_to_c(value), 2)
    return round(
        parse_number(text, "Temperature", MIN_TEMP_C, MAX_TEMP_C, "°C", "36.5"), 2
    )


def parse_date(text: str, today: date) -> date:
    """Return a date typed as YYYY-MM-DD.

    Only that format is accepted; date.fromisoformat() would also accept forms
    such as "20261031".

    Raises:
        ValueError: "Enter a date.", "Use the format YYYY-MM-DD, e.g.
            2026-10-31." (also for impossible dates such as 2026-02-30), or
            "The date cannot be in the future." (T15).
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Enter a date.")
    if len(cleaned) != 10 or cleaned[4] != "-" or cleaned[7] != "-":
        raise ValueError("Use the format YYYY-MM-DD, e.g. 2026-10-31.")
    try:
        value = datetime.strptime(cleaned, DATE_FORMAT).date()
    except ValueError:
        raise ValueError("Use the format YYYY-MM-DD, e.g. 2026-10-31.") from None
    if value > today:
        raise ValueError("The date cannot be in the future.")
    return value


def parse_optional_date(text: str, today: date) -> date | None:
    """Like parse_date, but blank text means "no date" and returns None."""
    if not text.strip():
        return None
    return parse_date(text, today)


def parse_birth_date(text: str, today: date) -> date:
    """Return a birth date (YYYY-MM-DD) that gives an age of 10 to 120."""
    birth_date = parse_date(text, today)
    age = calculate_age(birth_date, today)
    if not MIN_AGE_YEARS <= age <= MAX_AGE_YEARS:
        raise ValueError("Age must be between 10 and 120 years.")
    return birth_date


def parse_display_name(text: str) -> str:
    """Return the name to greet the user with, without spaces at either end."""
    name = text.strip()
    if not name:
        raise ValueError("Enter a name.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError("Use 30 characters or fewer.")
    return name


def parse_time(text: str) -> str:
    """Return a 24-hour time typed as HH:MM, e.g. "06:30"."""
    cleaned = text.strip()
    try:
        value = datetime.strptime(cleaned, "%H:%M")
    except ValueError:
        raise ValueError("Use the 24-hour format HH:MM, e.g. 06:30.") from None
    return value.strftime("%H:%M")
