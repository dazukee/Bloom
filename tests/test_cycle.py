"""Tests for tracker/cycle.py and tracker/calendar_logic.py."""

from datetime import date

import pytest

from tracker import calendar_logic as cal
from tracker import cycle


def periods_from(*starts, length=5):
    """Make logged periods from start dates, each `length` days long."""
    result = []
    for start in starts:
        result.append(
            {"start": start, "end": date.fromordinal(start.toordinal() + length - 1)}
        )
    return result


def test_t09_regular_cycles():
    p = cycle.predict_cycle(
        periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 2, 26))
    )
    assert p.average_length == 28
    assert p.next_start == date(2026, 3, 26)
    assert p.ovulation == date(2026, 3, 12)
    # Two known cycles: the calendar window (Mar 7-14) plus a 1-day margin each side.
    assert (p.fertile_start, p.fertile_end) == (date(2026, 3, 6), date(2026, 3, 15))
    assert p.uses_default_length is False


def test_t10_one_period_uses_default():
    p = cycle.predict_cycle(periods_from(date(2026, 2, 26)))
    assert p.next_start == date(2026, 3, 26)
    # No known cycle: a 2-day margin each side (cycle days 8 to 19).
    assert (p.fertile_start, p.fertile_end) == (date(2026, 3, 5), date(2026, 3, 16))
    assert p.uses_default_length is True
    assert p.confidence == "low"


def test_t11_year_boundary():
    p = cycle.predict_cycle(periods_from(date(2025, 11, 12), date(2025, 12, 10)))
    assert p.next_start == date(2026, 1, 7)


def test_t12_leap_year():
    leap = cycle.predict_cycle(periods_from(date(2028, 1, 18), date(2028, 2, 15)))
    plain = cycle.predict_cycle(periods_from(date(2027, 1, 18), date(2027, 2, 15)))
    assert leap.next_start == date(2028, 3, 14)
    assert plain.next_start == date(2027, 3, 15)


def test_t13_irregular_cycles():
    starts = [date(2026, 1, 3), date(2026, 1, 28), date(2026, 3, 4), date(2026, 4, 3)]
    assert cycle.cycle_lengths(starts) == [25, 35, 30]
    p = cycle.predict_cycle(periods_from(*starts))
    assert p.average_length == 30
    assert p.next_start == date(2026, 5, 3)
    assert p.ovulation == date(2026, 4, 19)
    assert (p.fertile_start, p.fertile_end) == (date(2026, 4, 8), date(2026, 4, 27))
    assert cycle.lengths_outside_typical_range([25, 35, 30]) == []


def test_t14_rounding_halves_to_even():
    p = cycle.predict_cycle(
        periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 2, 27))
    )
    assert p.average_length == 28  # round(28.5) == 28


def test_t16_duplicate_start_rejected():
    periods = periods_from(date(2026, 10, 1))
    with pytest.raises(ValueError, match="already logged"):
        cycle.add_period(periods, date(2026, 10, 1), None, date(2026, 10, 31))


def test_t19_fertile_window_never_before_period():
    p = cycle.predict_cycle(
        periods_from(date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 6))
    )
    assert p.fertile_start == date(2026, 2, 6)
    assert cycle.lengths_outside_typical_range([18, 18]) == [18, 18]


def test_add_period_rules_and_no_mutation():
    today = date(2026, 10, 31)
    original = periods_from(date(2026, 10, 1))
    added = cycle.add_period(original, date(2026, 10, 25), None, today)
    assert len(original) == 1 and len(added) == 2
    with pytest.raises(ValueError, match="future"):
        cycle.add_period(original, date(2026, 11, 2), None, today)
    with pytest.raises(ValueError, match="overlaps"):
        cycle.add_period(original, date(2026, 10, 3), None, today)
    with pytest.raises(ValueError, match="15 days"):
        cycle.add_period(original, date(2026, 10, 10), date(2026, 10, 30), today)
    with pytest.raises(ValueError, match="before the start"):
        cycle.add_period(original, date(2026, 10, 20), date(2026, 10, 19), today)


def test_set_and_remove_period():
    today = date(2026, 10, 31)
    periods = [{"start": date(2026, 10, 25), "end": None}]
    finished = cycle.set_period_end(
        periods, date(2026, 10, 25), date(2026, 10, 29), today
    )
    assert finished[0]["end"] == date(2026, 10, 29)
    assert cycle.remove_period(finished, date(2026, 10, 25)) == []


def test_missed_log_gap_is_skipped():
    p = cycle.predict_cycle(
        periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 4, 1))
    )
    assert p.average_length == 28  # the 62-day gap is treated as a missed log


def test_confidence_levels():
    steady = periods_from(
        date(2026, 1, 1), date(2026, 1, 29), date(2026, 2, 26), date(2026, 3, 26)
    )
    assert cycle.predict_cycle(steady).confidence == "high"


def test_phases_across_a_cycle():
    periods = periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 2, 26))
    p = cycle.predict_cycle(periods)
    assert cycle.phase_on(date(2026, 2, 27), periods, p) == cycle.MENSTRUAL
    assert cycle.phase_on(date(2026, 3, 5), periods, p) == cycle.FOLLICULAR
    assert cycle.phase_on(date(2026, 3, 12), periods, p) == cycle.OVULATION
    assert cycle.phase_on(date(2026, 3, 20), periods, p) == cycle.LUTEAL
    assert cycle.phase_on(date(2026, 3, 27), periods, p) == cycle.MENSTRUAL  # predicted
    assert cycle.phase_on(date(2025, 12, 1), periods, p) is None


def test_cycle_day_and_stats():
    periods = periods_from(date(2026, 1, 1), date(2026, 1, 29))
    assert cycle.cycle_day(periods, date(2026, 2, 1)) == 4
    assert cycle.cycle_stats(periods)["average"] == 28


def test_hormone_pattern_peaks():
    before = cycle.hormone_levels(5, 28)
    at_ovulation = cycle.hormone_levels(14.5, 28)
    luteal = cycle.hormone_levels(21, 28)
    assert at_ovulation["LH"] > 0.9 > before["LH"]
    assert luteal["Progesterone"] > before["Progesterone"]


def test_month_grid_rows():
    february = cal.month_grid(2026, 2)
    assert len(february) == 4 and all(
        day is not None for week in february for day in week
    )
    assert len(cal.month_grid(2026, 8)) == 6
    assert cal.weekday_names()[0] == "Sun"


def test_month_navigation():
    assert cal.next_month(2026, 12) == (2027, 1)
    assert cal.previous_month(2027, 1) == (2026, 12)


def test_day_status_order_and_projection():
    periods = periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 2, 26))
    p = cycle.predict_cycle(periods)
    assert cal.day_status(date(2026, 2, 27), periods, p) == cal.STATUS_PERIOD
    assert cal.day_status(date(2026, 3, 12), periods, p) == cal.STATUS_OVULATION
    assert cal.day_status(date(2026, 3, 8), periods, p) == cal.STATUS_FERTILE
    assert cal.day_status(date(2026, 3, 27), periods, p) == cal.STATUS_PREDICTED
    assert (
        cal.day_status(date(2026, 4, 9), periods, p) == cal.STATUS_OVULATION
    )  # next cycle
    assert cal.day_status(date(2026, 3, 1), periods, None) == cal.STATUS_PERIOD
    assert cal.day_status(date(2026, 3, 20), periods, None) == cal.STATUS_NONE
