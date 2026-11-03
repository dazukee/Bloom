"""Cycle statistics, predictions, phases and a schematic hormone curve.

Pure logic: no customtkinter, no file access.

A period is a dict {"start": date, "end": date | None}; "end" is None while a
period is still going or was never logged. Cycle day 1 is a period's first day,
so cycle day n is start + (n - 1) days.

Methods (sources in README.md):
    next period   last start + average of the last CYCLES_TO_AVERAGE cycles
    ovulation     next period - LUTEAL_PHASE_DAYS (NHS: usually 10-16 days before)
    fertile days  calendar method (Office on Women's Health): cycle day
                  (shortest - 18) to cycle day (longest - 11)
Every prediction is an estimate, and the screens say so.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = 5
CYCLES_TO_AVERAGE = 6
LUTEAL_PHASE_DAYS = 14
CALENDAR_SHORTEST_OFFSET = 18
CALENDAR_LONGEST_OFFSET = 11
TYPICAL_MIN_CYCLE_DAYS = 24  # FIGO 2018: a normal adult cycle lasts 24 to 38 days.
TYPICAL_MAX_CYCLE_DAYS = 38
MAX_PERIOD_DAYS = 15  # Design choice: longer entries are almost always typos.
MISSED_LOG_DAYS = 60  # Design choice: a longer gap is treated as a missed log.

MENSTRUAL = "menstrual"
FOLLICULAR = "follicular"
OVULATION = "ovulation"
LUTEAL = "luteal"

# phase: (name, what happens, a gentle suggestion). Educational, not advice.
PHASES = {
    MENSTRUAL: (
        "Menstrual",
        "Your period. Estrogen and progesterone are at their lowest, so energy "
        "can dip.",
        "Rest when you need it; warmth and gentle movement can ease cramps.",
    ),
    FOLLICULAR: (
        "Follicular",
        "Estrogen rises as an egg matures. Many people feel more energetic.",
        "A good time for harder workouts and starting new plans.",
    ),
    OVULATION: (
        "Ovulation",
        "A surge of LH releases an egg. This is the most fertile time.",
        "If you track temperature, a rise after this confirms ovulation.",
    ),
    LUTEAL: (
        "Luteal",
        "Progesterone rises and your temperature stays higher. PMS symptoms can "
        "appear late in this phase.",
        "Prioritise sleep, regular meals and gentle movement.",
    ),
}


@dataclass(frozen=True)
class CyclePrediction:
    """The result of predict_cycle. Every date in it is an estimate.

    Attributes:
        last_start: Start of the most recent logged period (cycle day 1).
        next_start: First day of the next period. It is in the past when no
            recent period was logged; screens then show "late by N days".
        next_end: Last day of the next period.
        ovulation: Estimated ovulation day of the current cycle.
        fertile_start: First fertile day, never before last_start (T19).
        fertile_end: Last fertile day.
        average_length: Average cycle length in days.
        period_length: Average period length in days.
        uses_default_length: True when fewer than 2 periods are logged (T10).
        confidence: "low", "medium" or "high", from how much cycles vary.
    """

    last_start: date
    next_start: date
    next_end: date
    ovulation: date
    fertile_start: date
    fertile_end: date
    average_length: int
    period_length: int
    uses_default_length: bool
    confidence: str


def period_end(period: dict, period_length: int = DEFAULT_PERIOD_LENGTH) -> date:
    """Return a period's last day, assuming `period_length` days if not logged."""
    if period.get("end") is not None:
        return period["end"]
    return period["start"] + timedelta(days=period_length - 1)


def add_period(
    periods: list[dict],
    start: date,
    end: date | None,
    today: date,
    period_length: int = DEFAULT_PERIOD_LENGTH,
) -> list[dict]:
    """Return a new list with this period added, sorted oldest first.

    The original list is not changed. A period with no end date counts as
    `period_length` days long when checking overlaps.

    Raises:
        ValueError: For a future date, an end before the start, a period over
            15 days, a start already logged (T16) or an overlap.
    """
    if start > today:
        raise ValueError("The start date cannot be in the future.")
    if end is not None:
        _check_end(start, end, today)
    new_end = end if end is not None else start + timedelta(days=period_length - 1)
    for period in periods:
        if period["start"] == start:
            raise ValueError("This period is already logged.")
        if start <= period_end(period, period_length) and period["start"] <= new_end:
            raise ValueError("This period overlaps one you already logged.")
    new_list = [dict(period) for period in periods]
    new_list.append({"start": start, "end": end})
    return sorted(new_list, key=lambda period: period["start"])


def _check_end(start: date, end: date, today: date) -> None:
    """Raise ValueError when a period's end date breaks a rule."""
    if end > today:
        raise ValueError("The end date cannot be in the future.")
    if end < start:
        raise ValueError("The end date cannot be before the start date.")
    if (end - start).days + 1 > MAX_PERIOD_DAYS:
        raise ValueError("A period cannot last more than 15 days.")


def set_period_end(
    periods: list[dict], start: date, end: date, today: date
) -> list[dict]:
    """Return a new list where the period starting on `start` ends on `end`."""
    _check_end(start, end, today)
    found = False
    new_list = []
    for period in periods:
        copy = dict(period)
        if copy["start"] == start:
            copy["end"] = end
            found = True
        elif start < copy["start"] <= end:
            raise ValueError("This period would overlap the next one.")
        new_list.append(copy)
    if not found:
        raise ValueError("No period starts on that date.")
    return sorted(new_list, key=lambda period: period["start"])


def remove_period(periods: list[dict], start: date) -> list[dict]:
    """Return a new list without the period that starts on `start`."""
    kept = [dict(period) for period in periods if period["start"] != start]
    return sorted(kept, key=lambda period: period["start"])


def period_starts(periods: list[dict]) -> list[date]:
    """Return the start dates of the periods, oldest first."""
    return sorted(period["start"] for period in periods)


def cycle_lengths(starts: list[date]) -> list[int]:
    """Return the days between each pair of consecutive starts.

    Example:
        Starts 2026-01-03, 2026-01-28, 2026-03-04 and 2026-04-03 give
        [25, 35, 30] (T13).
    """
    lengths = []
    for earlier, later in zip(starts, starts[1:], strict=False):  # pairs neighbours
        lengths.append((later - earlier).days)
    return lengths


def average_period_length(
    periods: list[dict], default: int = DEFAULT_PERIOD_LENGTH
) -> int:
    """Return the average period length in days, counting the first and last day.

    Uses the last CYCLES_TO_AVERAGE periods that have an end date.
    """
    ordered = sorted(periods, key=lambda period: period["start"])
    lengths = []
    for period in ordered:
        if period.get("end") is not None:
            lengths.append((period["end"] - period["start"]).days + 1)
    recent = lengths[-CYCLES_TO_AVERAGE:]
    if not recent:
        return default
    return round(sum(recent) / len(recent))


def _confidence(lengths: list[int], uses_default: bool) -> str:
    """Rate a prediction by how many cycles back it up and how much they vary."""
    if uses_default:
        return "low"
    spread = max(lengths) - min(lengths)
    if len(lengths) >= 3 and spread <= 4:
        return "high"
    if spread <= 8:
        return "medium"
    return "low"


def predict_cycle(
    periods: list[dict],
    default_length: int = DEFAULT_CYCLE_LENGTH,
    default_period_length: int = DEFAULT_PERIOD_LENGTH,
) -> CyclePrediction | None:
    """Predict the next period, ovulation and fertile window.

    Steps (the flowchart):
        1. No periods: return None.
        2. One period: lengths = [default_length]; uses_default_length is True.
        3. Otherwise: the last CYCLES_TO_AVERAGE cycle lengths, skipping gaps
           over MISSED_LOG_DAYS (a forgotten log) when others exist.
        4. average = round(sum / count). round() sends halves to the even
           number, so 28.5 gives 28 (T14).
        5. next_start = last start + average days.
        6. ovulation = next_start - LUTEAL_PHASE_DAYS.
        7. fertile_start = last start + (shortest - 18 - 1) days, never before
           the last start (T19); fertile_end = last start + (longest - 11 - 1)
           days. The "- 1" is because day 1 is the start itself.

    Examples:
        Starts 2026-01-01, 2026-01-29 and 2026-02-26: next 2026-03-26,
        ovulation 2026-03-12, fertile 2026-03-07 to 2026-03-14 (T09).
    """
    starts = period_starts(periods)
    if not starts:
        return None
    if len(starts) == 1:
        lengths = [default_length]
        uses_default = True
    else:
        all_lengths = cycle_lengths(starts)
        usable = [n for n in all_lengths if n <= MISSED_LOG_DAYS] or all_lengths
        lengths = usable[-CYCLES_TO_AVERAGE:]
        uses_default = False

    average = round(sum(lengths) / len(lengths))
    last_start = starts[-1]
    period_length = average_period_length(periods, default_period_length)
    next_start = last_start + timedelta(days=average)
    shortest_offset = min(lengths) - CALENDAR_SHORTEST_OFFSET - 1
    longest_offset = max(lengths) - CALENDAR_LONGEST_OFFSET - 1
    return CyclePrediction(
        last_start=last_start,
        next_start=next_start,
        next_end=next_start + timedelta(days=period_length - 1),
        ovulation=next_start - timedelta(days=LUTEAL_PHASE_DAYS),
        fertile_start=max(last_start, last_start + timedelta(days=shortest_offset)),
        fertile_end=last_start + timedelta(days=longest_offset),
        average_length=average,
        period_length=period_length,
        uses_default_length=uses_default,
        confidence=_confidence(lengths, uses_default),
    )


def lengths_outside_typical_range(lengths: list[int]) -> list[int]:
    """Return the cycle lengths below 24 or above 38 days, in their order."""
    return [
        n for n in lengths if n < TYPICAL_MIN_CYCLE_DAYS or n > TYPICAL_MAX_CYCLE_DAYS
    ]


def cycle_stats(periods: list[dict]) -> dict | None:
    """Return count, average, shortest, longest and spread of past cycles."""
    lengths = cycle_lengths(period_starts(periods))
    if not lengths:
        return None
    return {
        "count": len(lengths),
        "average": round(sum(lengths) / len(lengths)),
        "shortest": min(lengths),
        "longest": max(lengths),
        "spread": max(lengths) - min(lengths),
    }


def cycle_day(periods: list[dict], day: date) -> int | None:
    """Return the cycle day of `day` (1 on a period's first day), or None."""
    earlier = [start for start in period_starts(periods) if start <= day]
    if not earlier:
        return None
    return (day - earlier[-1]).days + 1


def projected_cycle(prediction: CyclePrediction, day: date) -> tuple[int, timedelta]:
    """Return (k, shift) for the cycle containing a day on or after last_start.

    k = 0 is the current cycle; k = 1 starts on next_start; later cycles repeat
    every average_length days. `shift` moves cycle-0 dates into cycle k.
    """
    k = (day - prediction.last_start).days // prediction.average_length
    return k, timedelta(days=k * prediction.average_length)


def phase_on(
    day: date,
    periods: list[dict],
    prediction: CyclePrediction | None,
    period_length: int = DEFAULT_PERIOD_LENGTH,
) -> str | None:
    """Return the cycle phase on `day`, or None before the first logged period."""
    for period in periods:
        if period["start"] <= day <= period_end(period, period_length):
            return MENSTRUAL
    starts = period_starts(periods)
    earlier = [start for start in starts if start <= day]
    if not earlier or prediction is None:
        return None

    later = [start for start in starts if start > day]
    if later:  # a finished cycle: its real next start is known
        ovulation = later[0] - timedelta(days=LUTEAL_PHASE_DAYS)
    else:
        k, shift = projected_cycle(prediction, day)
        cycle_start = prediction.last_start + shift
        if k >= 1 and day <= cycle_start + timedelta(days=prediction.period_length - 1):
            return MENSTRUAL
        ovulation = prediction.ovulation + shift
    gap = (day - ovulation).days
    if abs(gap) <= 1:
        return OVULATION
    return FOLLICULAR if gap < 0 else LUTEAL


def days_until(target: date, today: date) -> int:
    """Return whole days from today to target (negative when target has passed)."""
    return (target - today).days


# A schematic hormone pattern, for teaching ---------------------------------------


def _bump(x: float, centre: float, width: float, height: float) -> float:
    """Return one smooth bell-shaped bump (a Gaussian)."""
    return height * math.exp(-((x - centre) ** 2) / (2 * width * width))


def hormone_levels(day_number: float, cycle_length: int) -> dict[str, float]:
    """Return relative levels (0-1) of four hormones on a cycle day.

    A typical textbook pattern, scaled to this cycle's length: estrogen peaks
    just before ovulation and again mid-luteal, LH and FSH surge at ovulation,
    and progesterone rises after it. It is not a measurement of the user.
    """
    ovulation_day = cycle_length - LUTEAL_PHASE_DAYS
    luteal_peak = ovulation_day + 7
    estrogen = 0.18 + _bump(day_number, ovulation_day - 1, 2.6, 0.82)
    estrogen += _bump(day_number, luteal_peak, 3.4, 0.45)
    progesterone = 0.05 + _bump(day_number, luteal_peak, 3.2, 0.9)
    lh = 0.1 + _bump(day_number, ovulation_day - 0.5, 0.9, 0.9)
    fsh = (
        0.15
        + _bump(day_number, 3, 3.0, 0.3)
        + _bump(day_number, ovulation_day - 0.5, 1.1, 0.5)
    )
    return {
        "Estrogen": min(estrogen, 1.0),
        "Progesterone": min(progesterone, 1.0),
        "LH": min(lh, 1.0),
        "FSH": min(fsh, 1.0),
    }
