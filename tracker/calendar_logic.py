"""Month grid and day colours for the calendar.

Pure logic: no customtkinter, no file access.
"""

import calendar
from datetime import date, timedelta

from tracker.cycle import (
    DEFAULT_PERIOD_LENGTH,
    CyclePrediction,
    period_end,
    projected_cycle,
)

WEEK_STARTS_ON = calendar.SUNDAY  # Use calendar.MONDAY for Monday-first weeks.

STATUS_PERIOD = "period"  # a logged period day
STATUS_PREDICTED = "predicted"  # a day of a predicted period
STATUS_OVULATION = "ovulation"
STATUS_FERTILE = "fertile"
STATUS_NONE = ""


def month_grid(year: int, month: int) -> list[list[date | None]]:
    """Return a month as rows of 7 days; cells outside the month are None.

    Example:
        February 2026 starts on a Sunday and has 28 days, so
        month_grid(2026, 2) has exactly 4 rows and no None.
    """
    weeks = calendar.Calendar(WEEK_STARTS_ON).monthdayscalendar(year, month)
    grid = []
    for week in weeks:
        row = []
        for day_number in week:
            row.append(date(year, month, day_number) if day_number else None)
        grid.append(row)
    return grid


def weekday_names() -> list[str]:
    """Return short weekday names in grid order, e.g. ["Sun", "Mon", ...]."""
    names = []
    for index in calendar.Calendar(WEEK_STARTS_ON).iterweekdays():
        names.append(calendar.day_abbr[index])
    return names


def day_status(
    day: date,
    periods: list[dict],
    prediction: CyclePrediction | None,
    period_length: int = DEFAULT_PERIOD_LENGTH,
) -> str:
    """Return how the calendar should colour one day.

    Checks, in order: a logged period, a predicted period, the ovulation day,
    the fertile window. Predictions repeat for future cycles every
    average_length days, so months ahead are coloured too.
    """
    for period in periods:
        if period["start"] <= day <= period_end(period, period_length):
            return STATUS_PERIOD
    if prediction is None or day < prediction.last_start:
        return STATUS_NONE

    k, shift = projected_cycle(prediction, day)
    cycle_start = prediction.last_start + shift
    predicted_end = cycle_start + timedelta(days=prediction.period_length - 1)
    if k >= 1 and cycle_start <= day <= predicted_end:
        return STATUS_PREDICTED
    if day == prediction.ovulation + shift:
        return STATUS_OVULATION
    if prediction.fertile_start + shift <= day <= prediction.fertile_end + shift:
        return STATUS_FERTILE
    return STATUS_NONE


def next_month(year: int, month: int) -> tuple[int, int]:
    """Return the (year, month) after this one; (2026, 12) gives (2027, 1)."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def previous_month(year: int, month: int) -> tuple[int, int]:
    """Return the (year, month) before this one; (2027, 1) gives (2026, 12)."""
    if month == 1:
        return year - 1, 12
    return year, month - 1
