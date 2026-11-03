"""Unit conversions and display formats. Data is always stored in metric.

The user picks kg or lb, cm or feet and inches, and °C or °F in Settings;
screens convert at the edges with these functions.
"""

KG_PER_LB = 0.45359237
CM_PER_INCH = 2.54


def kg_to_lb(kg: float) -> float:
    """Convert kilograms to pounds."""
    return kg / KG_PER_LB


def lb_to_kg(lb: float) -> float:
    """Convert pounds to kilograms."""
    return lb * KG_PER_LB


def cm_to_ft_in(cm: float) -> tuple[int, float]:
    """Convert centimetres to (feet, inches), with inches to 1 decimal place."""
    total_inches = cm / CM_PER_INCH
    feet = int(total_inches // 12)
    inches = round(total_inches - feet * 12, 1)
    if inches >= 12:  # rounding can carry, e.g. 11.96 in becomes 12.0
        feet += 1
        inches = 0.0
    return feet, inches


def ft_in_to_cm(feet: float, inches: float) -> float:
    """Convert feet and inches to centimetres."""
    return (feet * 12 + inches) * CM_PER_INCH


def c_to_f(celsius: float) -> float:
    """Convert degrees Celsius to Fahrenheit."""
    return celsius * 9 / 5 + 32


def f_to_c(fahrenheit: float) -> float:
    """Convert degrees Fahrenheit to Celsius."""
    return (fahrenheit - 32) * 5 / 9


def format_weight(kg: float, unit: str) -> str:
    """Return a weight for display, e.g. "55.5 kg" or "122.4 lb"."""
    if unit == "lb":
        return f"{kg_to_lb(kg):.1f} lb"
    return f"{kg:.1f} kg"


def format_height(cm: float, unit: str) -> str:
    """Return a height for display, e.g. "160 cm" or "5 ft 3 in"."""
    if unit == "ft":
        feet, inches = cm_to_ft_in(cm)
        return f"{feet} ft {inches:g} in"
    return f"{cm:g} cm"


def format_temp(celsius: float, unit: str) -> str:
    """Return a body temperature for display, e.g. "36.45 °C" or "97.61 °F"."""
    if unit == "f":
        return f"{c_to_f(celsius):.2f} °F"
    return f"{celsius:.2f} °C"


def temp_in_unit(celsius: float, unit: str) -> float:
    """Return a Celsius temperature in the user's unit."""
    return c_to_f(celsius) if unit == "f" else celsius


def temp_step(unit: str) -> float:
    """Return the +/- step for a thermometer reading in this unit."""
    return 0.1 if unit == "f" else 0.05
