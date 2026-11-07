"""Cycle statistics, predictions, phases and a schematic hormone curve.

Pure logic: no customtkinter, no file access.

A period is a dict {"start": date, "end": date | None}; "end" is None while a
period is still going or was never logged. Cycle day 1 is a period's first day,
so cycle day n is start + (n - 1) days.

Methods (sources in README.md):
    next period   last start + average of the last CYCLES_TO_AVERAGE cycles
    ovulation     next period - LUTEAL_PHASE_DAYS (NHS: usually 10-16 days before)
    fertile days  calendar method (Office on Women's Health): cycle day
                  (shortest - 18) to cycle day (longest - 11), widened while
                  few cycles are known
    range         next period +/- the usual variation
Once this cycle's ovulation is known (a temperature shift or a positive LH
test), with_ovulation_sign() counts the next period from it instead.

These choices were checked against 1,665 real cycles from 159 women (Fehring,
Marquette University). The average of the last 6 cycles was within 3 days 81%
of the time; counting from a known ovulation cut the average error from 2.0 to
1.2 days. Every prediction is still an estimate, and the screens say so.
"""

import math
import statistics
from dataclasses import dataclass, replace
from datetime import date, timedelta

DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = 5
CYCLES_TO_AVERAGE = 6
LUTEAL_PHASE_DAYS = 14
CALENDAR_SHORTEST_OFFSET = 18
CALENDAR_LONGEST_OFFSET = 11
TYPICAL_MIN_CYCLE_DAYS = 24  # FIGO 2018: a normal adult cycle lasts 24 to 38 days.
TYPICAL_MAX_CYCLE_DAYS = 38
TEEN_MIN_CYCLE_DAYS = 21  # ACOG: the first years after a first period run 21 to 45.
TEEN_MAX_CYCLE_DAYS = 45
ADULT_FROM_AGE = 20
PROLONGED_PERIOD_DAYS = 8  # FIGO 2018: bleeding beyond 8 days is "prolonged".
NO_PERIOD_ALERT_DAYS = 90  # About 3 missed periods: worth raising with a doctor.
MAX_PERIOD_DAYS = 15  # Design choice: longer entries are almost always typos.
MISSED_LOG_DAYS = 60  # Design choice: a longer gap is treated as a missed log.
MIN_DAYS_BETWEEN_STARTS = 10  # Design choice: closer starts are almost always typos.
# Extra fertile days on each side while few cycles are known. Backtest, ovulation
# inside the window: 1 cycle 68% -> 90%, 2-3 cycles 88% -> 93%, 4+ cycles 95%+.
SHORT_HISTORY_MARGIN = {0: 2, 1: 2, 2: 1, 3: 1}
# From a known ovulation, the next period came 14 days later on average in the
# backtest (a luteal phase of about 13 days after the ovulation day).
OVULATION_TO_PERIOD_DAYS = 14
UNCERTAIN_RANGE_DAYS = 5  # With 0 or 1 known cycles, 80% of real errors were <= 5.
MIN_RANGE_DAYS = 2
SIGN_RANGE_DAYS = 2  # With a known ovulation, 80-88% of real errors were <= 2.

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
        earliest_next: Start of the range the next period will probably begin in.
        latest_next: End of that range (about 8 times in 10, in the backtest).
        fertile_from: Days from a cycle's first day to its first fertile day.
        fertile_to: Days from a cycle's first day to its last fertile day.
        basis: How ovulation is known: "calendar", "temperature" or "LH test".
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
    earliest_next: date | None = None
    latest_next: date | None = None
    fertile_from: int = 9
    fertile_to: int = 16
    basis: str = "calendar"


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
            15 days, a start already logged (T16), an overlap, or a start within
            10 days of another period's start.
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
        if abs((start - period["start"]).days) < MIN_DAYS_BETWEEN_STARTS:
            raise ValueError(
                f"This is too close to the period that started on {period['start']:%b} {period['start'].day}. "
                "If it is the same period, select its last day and choose Period Ended."
            )
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


def extendable_period(periods: list[dict], day: date) -> dict | None:
    """Return the latest period that could still end on `day`, or None.

    A period with no end date only covers its assumed length on the calendar, so
    a long period's real last day can fall after it; a logged end can be moved
    too. The day must be within MAX_PERIOD_DAYS of the start, before any later
    period starts.
    """
    earlier = [period for period in periods if period["start"] < day]
    if not earlier:
        return None
    latest = max(earlier, key=lambda period: period["start"])
    if (day - latest["start"]).days + 1 > MAX_PERIOD_DAYS:
        return None
    return latest


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


def usable_lengths(starts: list[date]) -> list[int]:
    """Return the cycle lengths without gaps over MISSED_LOG_DAYS (forgotten logs).

    If every gap is that long, they are all kept: they may be the person's real
    pattern.
    """
    lengths = cycle_lengths(starts)
    return [n for n in lengths if n <= MISSED_LOG_DAYS] or lengths


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
    """Rate a prediction by how many cycles back it up and how much they vary.

    Backtest, average error in days: high 1.6, medium 2.2, low 3.4. One measured
    cycle says nothing about variation, so it stays "low".
    """
    if uses_default or len(lengths) < 2:
        return "low"
    spread = max(lengths) - min(lengths)
    if len(lengths) >= 3 and spread <= 4:
        return "high"
    if spread <= 8:
        return "medium"
    return "low"


def _range_days(lengths: list[int], uses_default: bool) -> int:
    """Return how many days either side of next_start the period may begin."""
    if uses_default or len(lengths) < 2:
        return UNCERTAIN_RANGE_DAYS
    return max(MIN_RANGE_DAYS, math.ceil(statistics.stdev(lengths)))


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
        7. margin = 2 days with up to 1 known cycle, 1 day with 2 or 3, else 0.
        8. fertile_start = last start + (shortest - 18 - margin - 1) days, never
           before the last start (T19); fertile_end = last start +
           (longest - 11 + margin - 1) days, never before fertile_start. The
           "- 1" is because day 1 is the start itself.

    Examples:
        Starts 2026-01-01, 2026-01-29 and 2026-02-26: next 2026-03-26,
        ovulation 2026-03-12, fertile 2026-03-06 to 2026-03-15 (T09).
    """
    starts = period_starts(periods)
    if not starts:
        return None
    usable = usable_lengths(starts)
    if usable:
        lengths = usable[-CYCLES_TO_AVERAGE:]
        uses_default = False
    else:
        lengths = [default_length]
        uses_default = True

    average = round(sum(lengths) / len(lengths))
    last_start = starts[-1]
    period_length = average_period_length(periods, default_period_length)
    next_start = last_start + timedelta(days=average)
    margin = SHORT_HISTORY_MARGIN.get(0 if uses_default else len(lengths), 0)
    fertile_from = max(0, min(lengths) - CALENDAR_SHORTEST_OFFSET - margin - 1)
    fertile_to = max(fertile_from, max(lengths) - CALENDAR_LONGEST_OFFSET + margin - 1)
    spread = timedelta(days=_range_days(lengths, uses_default))
    return CyclePrediction(
        last_start=last_start,
        next_start=next_start,
        next_end=next_start + timedelta(days=period_length - 1),
        ovulation=next_start - timedelta(days=LUTEAL_PHASE_DAYS),
        fertile_start=last_start + timedelta(days=fertile_from),
        fertile_end=last_start + timedelta(days=fertile_to),
        average_length=average,
        period_length=period_length,
        uses_default_length=uses_default,
        confidence=_confidence(lengths, uses_default),
        earliest_next=max(last_start + timedelta(days=1), next_start - spread),
        latest_next=next_start + spread,
        fertile_from=fertile_from,
        fertile_to=fertile_to,
    )


def with_ovulation_sign(
    prediction: CyclePrediction,
    ovulation: date,
    source: str,
    days_to_period: int | None = None,
) -> CyclePrediction:
    """Return the prediction updated once this cycle's ovulation is known.

    The luteal phase varies less than the follicular phase, so counting from a
    known ovulation beats the calendar. Backtest on 1,238 real cycles, average
    error: calendar 2.0 days, ovulation + 14 days 1.7, ovulation + the person's
    own usual gap 1.2.

    Args:
        prediction: The calendar prediction for this cycle.
        ovulation: The ovulation day shown by the sign.
        source: What showed it: "temperature" or "LH test".
        days_to_period: This person's usual days from ovulation to period, if
            known from past cycles; OVULATION_TO_PERIOD_DAYS otherwise.
    """
    gap = days_to_period or OVULATION_TO_PERIOD_DAYS
    next_start = ovulation + timedelta(days=gap)
    spread = timedelta(days=SIGN_RANGE_DAYS)
    window_start = max(
        prediction.last_start,
        min(prediction.fertile_start, ovulation - timedelta(days=5)),
    )
    return replace(
        prediction,
        next_start=next_start,
        next_end=next_start + timedelta(days=prediction.period_length - 1),
        ovulation=ovulation,
        fertile_start=window_start,
        fertile_end=ovulation + timedelta(days=1),
        confidence="high",
        earliest_next=next_start - spread,
        latest_next=next_start + spread,
        basis=source,
    )


def rolled_forward(prediction: CyclePrediction, today: date) -> CyclePrediction:
    """Return the prediction with a late period's date moved up to today.

    A late period has not started yet, so it cannot have started on a past day,
    and later cycles should be counted from no earlier than today.
    """
    if prediction.next_start >= today:
        return prediction
    return replace(
        prediction,
        next_start=today,
        next_end=today + timedelta(days=prediction.period_length - 1),
    )


def is_stale(prediction: CyclePrediction, today: date) -> bool:
    """Return True when no period has been logged for so long that dates mean little."""
    return (today - prediction.next_start).days > MISSED_LOG_DAYS


def typical_range(age_years: int | None = None) -> tuple[int, int]:
    """Return the (shortest, longest) typical cycle for an age.

    Adults 24-38 days (FIGO 2018); under 20, 21-45 days, because cycles often
    take years to settle after a first period (ACOG Committee Opinion 651).
    """
    if age_years is not None and age_years < ADULT_FROM_AGE:
        return TEEN_MIN_CYCLE_DAYS, TEEN_MAX_CYCLE_DAYS
    return TYPICAL_MIN_CYCLE_DAYS, TYPICAL_MAX_CYCLE_DAYS


def lengths_outside_typical_range(
    lengths: list[int], age_years: int | None = None
) -> list[int]:
    """Return the cycle lengths outside the typical range, in their order."""
    low, high = typical_range(age_years)
    return [n for n in lengths if n < low or n > high]


def allowed_variation(age_years: int | None = None) -> int:
    """Return the days cycles may vary and still count as regular (FIGO 2018).

    Shortest to longest: up to 9 days at ages 18-25 and 42-45, 7 days at 26-41.
    """
    if age_years is not None and 26 <= age_years <= 41:
        return 7
    return 9


def prolonged_periods(periods: list[dict]) -> list[dict]:
    """Return the logged periods that lasted longer than 8 days (FIGO 2018)."""
    return [
        period
        for period in periods
        if period.get("end") is not None
        and (period["end"] - period["start"]).days + 1 > PROLONGED_PERIOD_DAYS
    ]


def fertile_window_ahead(
    prediction: CyclePrediction, today: date
) -> tuple[date, date, bool]:
    """Return (start, end, is_this_cycle) of the current or next fertile window."""
    if today <= prediction.fertile_end:
        return prediction.fertile_start, prediction.fertile_end, True
    cycle_start = max(prediction.next_start, today)
    return (
        cycle_start + timedelta(days=prediction.fertile_from),
        cycle_start + timedelta(days=prediction.fertile_to),
        False,
    )


def cycle_stats(periods: list[dict]) -> dict | None:
    """Return count, average, shortest, longest and spread of past cycles."""
    lengths = usable_lengths(period_starts(periods))
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


def projected_cycle(prediction: CyclePrediction, day: date) -> tuple[int, date]:
    """Return (k, first day) of the cycle containing a day on or after last_start.

    k = 0 is the current cycle; k = 1 starts on next_start; later cycles repeat
    every average_length days.
    """
    if day < prediction.next_start:
        return 0, prediction.last_start
    k = 1 + (day - prediction.next_start).days // prediction.average_length
    extra = timedelta(days=(k - 1) * prediction.average_length)
    return k, prediction.next_start + extra


def ovulation_of_cycle(prediction: CyclePrediction, k: int, first_day: date) -> date:
    """Return the ovulation day of cycle k, which starts on first_day."""
    if k == 0:
        return prediction.ovulation
    days = prediction.average_length - LUTEAL_PHASE_DAYS
    return first_day + timedelta(days=days)


def phase_segments(prediction: CyclePrediction) -> list[tuple[float, float, str]]:
    """Return this cycle as (start 0-1, end 0-1, part) pieces, for the cycle wheel.

    The parts are "menstrual", "follicular", "fertile", "ovulation" and "luteal".
    """
    length = max((prediction.next_start - prediction.last_start).days, 1)

    def day_of(moment: date) -> int:
        return min(max((moment - prediction.last_start).days, 0), length)

    period_end_day = min(prediction.period_length, length)
    ovulation = day_of(prediction.ovulation)
    fertile_from = max(day_of(prediction.fertile_start), period_end_day)
    ovulation_from = max(ovulation - 1, fertile_from)
    ovulation_to = max(min(ovulation + 2, length), ovulation_from)
    edges = (
        (0, period_end_day, MENSTRUAL),
        (period_end_day, fertile_from, FOLLICULAR),
        (fertile_from, ovulation_from, "fertile"),
        (ovulation_from, ovulation_to, OVULATION),
        (ovulation_to, length, LUTEAL),
    )
    return [(a / length, b / length, part) for a, b, part in edges if b > a]


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
        if is_stale(prediction, day):
            return None  # too long since the last log to say anything useful
        k, first_day = projected_cycle(prediction, day)
        if k >= 1 and day <= first_day + timedelta(days=prediction.period_length - 1):
            return MENSTRUAL
        ovulation = ovulation_of_cycle(prediction, k, first_day)
    gap = (day - ovulation).days
    if abs(gap) <= 1:
        return OVULATION
    return FOLLICULAR if gap < 0 else LUTEAL


def days_until(target: date, today: date) -> int:
    """Return whole days from today to target (negative when target has passed)."""
    return (target - today).days


# A schematic hormone pattern, for teaching ---------------------------------------


def schematic_ovulation_day(cycle_length: int) -> int:
    """Return the cycle day of ovulation, matching next_start - LUTEAL_PHASE_DAYS.

    The next period is cycle day (length + 1), so a 28-day cycle ovulates on day 15.
    """
    return cycle_length + 1 - LUTEAL_PHASE_DAYS


def _bump(x: float, centre: float, width: float, height: float) -> float:
    """Return one smooth bell-shaped bump (a Gaussian)."""
    return height * math.exp(-((x - centre) ** 2) / (2 * width * width))


def hormone_levels(day_number: float, cycle_length: int) -> dict[str, float]:
    """Return relative levels (0-1) of four hormones on a cycle day.

    A typical textbook pattern, scaled to this cycle's length: estrogen peaks
    just before ovulation and again mid-luteal, LH and FSH surge at ovulation,
    and progesterone rises after it. It is not a measurement of the user.
    """
    ovulation_day = schematic_ovulation_day(cycle_length)
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
