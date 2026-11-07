"""Basal body temperature (BBT): readings and the ovulation thermal shift.

Pure logic: no customtkinter, no file access.

After ovulation, progesterone raises the resting temperature by a few tenths
of a degree. The common "3 over 6" rule (as in the symptothermal method)
confirms the rise afterwards:
    - the coverline is the highest of the 6 readings before a rise;
    - 3 readings in a row must all be above the coverline;
    - the third must be at least 0.2 °C above it; if it is not, a fourth reading
      above the coverline also confirms the rise (the rule's first exception).
Ovulation most likely happened the day before the first high reading. This
only confirms ovulation after it happens; it does not predict it.

Fevers (38 °C or more) and readings the user marks as disturbed (a cold, alcohol,
a late night) are left out, so one odd day cannot fake or hide a rise.
"""

from dataclasses import dataclass
from datetime import date, timedelta

BASELINE_READINGS = 6
HIGH_READINGS = 3
MIN_RISE_C = 0.2
FEVER_C = 38.0  # CDC treats 38.0 °C (100.4 °F) as a fever.
LH_TO_OVULATION_DAYS = 1  # Ovulation usually follows a first positive by 24-36 h.
SOURCE_TEMPERATURE = "temperature"
SOURCE_LH = "LH test"
MIN_DAYS_TO_PERIOD = 9  # Outside 9-19 days, a past cycle's sign was probably wrong.
MAX_DAYS_TO_PERIOD = 19
CYCLES_FOR_USUAL_GAP = 6
UNUSUAL_TIME_MINUTES = 90
MIN_READINGS_FOR_USUAL_TIME = 5


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
    raised them. So are readings the user marked as disturbed.
    """
    readings = []
    for day in sorted(days):
        if start <= day <= end and "bbt_c" in days[day]:
            temp = days[day]["bbt_c"]
            if not is_fever(temp) and not days[day].get("bbt_skip"):
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
        fourth = temps[i + HIGH_READINGS : i + HIGH_READINGS + 1]
        fourth_above = bool(fourth) and fourth[0] > coverline
        if all_above and (big_enough or fourth_above):
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


def ovulation_sign(days: dict, start: date, end: date) -> tuple[date, str] | None:
    """Return (ovulation day, source) shown by the days from start to end, or None.

    A positive LH test is the closer marker, so it comes first; a temperature
    shift confirms ovulation afterwards. Neither is certain.
    """
    for day in sorted(days):
        if start <= day <= end and days[day].get("lh") == "positive":
            return day + timedelta(days=LH_TO_OVULATION_DAYS), SOURCE_LH
    shift = detect_thermal_shift(readings_between(days, start, end))
    if shift is not None:
        return shift.ovulation, SOURCE_TEMPERATURE
    return None


def usual_days_to_period(days: dict, starts: list[date]) -> int | None:
    """Return this person's usual days from ovulation to period, or None.

    Measured in past cycles that show a sign, so the prediction becomes personal.
    Gaps outside 9-19 days are ignored as probable mistakes.
    """
    gaps = []
    for start, next_start in zip(starts, starts[1:], strict=False):  # pairs neighbours
        sign = ovulation_sign(days, start, next_start - timedelta(days=1))
        if sign is not None:
            gap = (next_start - sign[0]).days
            if MIN_DAYS_TO_PERIOD <= gap <= MAX_DAYS_TO_PERIOD:
                gaps.append(gap)
    recent = gaps[-CYCLES_FOR_USUAL_GAP:]
    if not recent:
        return None
    return round(sum(recent) / len(recent))


def _minutes(text: str) -> int:
    """Return minutes after midnight for "HH:MM" text."""
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


def unusual_time_note(days: dict, day: date) -> str | None:
    """Return a note when a reading was taken far from the usual time, or None.

    Temperature climbs through the morning, so a late reading can run high.
    """
    log = days.get(day, {})
    if "bbt_time" not in log:
        return None
    others = sorted(
        _minutes(days[other]["bbt_time"])
        for other in sorted(days)[-30:]
        if other != day and "bbt_time" in days[other]
    )
    if len(others) < MIN_READINGS_FOR_USUAL_TIME:
        return None
    gap = _minutes(log["bbt_time"]) - others[len(others) // 2]
    if abs(gap) < UNUSUAL_TIME_MINUTES:
        return None
    hours = round(abs(gap) / 60, 1)
    if gap > 0:
        return f"Taken about {hours:g} hours later than usual, so it may read a little high."
    return (
        f"Taken about {hours:g} hours earlier than usual, so it may read a little low."
    )
