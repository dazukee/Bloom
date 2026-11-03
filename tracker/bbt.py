"""Basal body temperature (BBT): readings and the ovulation thermal shift.

Pure logic: no customtkinter, no file access.

After ovulation, progesterone raises the resting temperature by a few tenths
of a degree. The common "3 over 6" rule (as in the symptothermal method)
confirms the rise afterwards:
    - the coverline is the highest of the 6 readings before a rise;
    - 3 readings in a row must all be above the coverline;
    - the third must be at least 0.2 °C above it.
Ovulation most likely happened the day before the first high reading. This
only confirms ovulation after it happens; it does not predict it.
"""

from dataclasses import dataclass
from datetime import date, timedelta

BASELINE_READINGS = 6
HIGH_READINGS = 3
MIN_RISE_C = 0.2
FEVER_C = 38.0  # CDC treats 38.0 °C (100.4 °F) as a fever.


@dataclass(frozen=True)
class ThermalShift:
    """A confirmed temperature rise.

    Attributes:
        coverline_c: The highest of the 6 baseline readings, in °C.
        first_high: Date of the first reading above the coverline.
        ovulation: Most likely ovulation day (the day before first_high).
    """

    coverline_c: float
    first_high: date
    ovulation: date


def readings_between(days: dict, start: date, end: date) -> list[tuple[date, float]]:
    """Return (date, °C) readings from start to end, oldest first.

    Fever readings (38.0 °C or more) are left out: illness, not ovulation,
    raised them.
    """
    readings = []
    for day in sorted(days):
        if start <= day <= end and "bbt_c" in days[day]:
            temp = days[day]["bbt_c"]
            if not is_fever(temp):
                readings.append((day, temp))
    return readings


def detect_thermal_shift(readings: list[tuple[date, float]]) -> ThermalShift | None:
    """Return the first thermal shift in the readings, or None.

    Readings must be oldest first. Gaps between days are allowed; the rule
    uses the readings in order.
    """
    temps = [temp for _, temp in readings]
    for i in range(BASELINE_READINGS, len(temps) - HIGH_READINGS + 1):
        coverline = max(temps[i - BASELINE_READINGS : i])
        highs = temps[i : i + HIGH_READINGS]
        all_above = all(temp > coverline for temp in highs)
        big_enough = round(highs[-1] - coverline, 2) >= MIN_RISE_C
        if all_above and big_enough:
            first_high = readings[i][0]
            return ThermalShift(
                coverline_c=round(coverline, 2),
                first_high=first_high,
                ovulation=first_high - timedelta(days=1),
            )
    return None


def baseline_progress(readings: list[tuple[date, float]]) -> int:
    """Return how many of the 6 baseline readings exist (for a progress hint)."""
    return min(len(readings), BASELINE_READINGS)


def is_fever(temp_c: float) -> bool:
    """Return True for a reading of 38.0 °C or more."""
    return temp_c >= FEVER_C
