"""Tests for bbt, vitals, activity, nutrition, journal and daylog."""

from datetime import date, datetime, timedelta

import pytest

from tracker import activity, bbt, daylog, journal, nutrition, vitals

START = date(2026, 10, 1)


def readings(*temps):
    """Make consecutive daily readings starting on START."""
    return [(START + timedelta(days=i), t) for i, t in enumerate(temps)]


def test_thermal_shift_three_over_six():
    temps = readings(36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.5, 36.55, 36.6)
    shift = bbt.detect_thermal_shift(temps)
    assert shift.coverline_c == 36.4
    assert shift.first_high == START + timedelta(days=6)
    assert shift.ovulation == START + timedelta(days=5)


def test_no_shift_when_third_rise_too_small():
    temps = readings(36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.45, 36.5, 36.55)
    assert bbt.detect_thermal_shift(temps) is None  # 36.55 is only 0.15 above


def test_no_shift_with_few_readings():
    assert bbt.detect_thermal_shift(readings(36.3, 36.6, 36.7)) is None


def test_fever_readings_left_out():
    days = {START: {"bbt_c": 36.4}, START + timedelta(days=1): {"bbt_c": 38.2}}
    assert bbt.readings_between(days, START, START + timedelta(days=5)) == [
        (START, 36.4)
    ]
    assert bbt.is_fever(38.0) and not bbt.is_fever(37.9)


@pytest.mark.parametrize(
    ("systolic", "diastolic", "category"),
    [
        (118, 76, "Normal"),
        (120, 79, "Elevated"),
        (125, 80, "Stage 1 hypertension"),
        (130, 70, "Stage 1 hypertension"),
        (140, 85, "Stage 2 hypertension"),
        (135, 90, "Stage 2 hypertension"),
        (181, 100, "Severe hypertension"),
        (150, 121, "Severe hypertension"),
    ],
)
def test_blood_pressure_categories(systolic, diastolic, category):
    assert vitals.bp_category(systolic, diastolic)[0] == category


def test_sleep_debt_and_averages():
    today = date(2026, 10, 31)
    days = {today: {"sleep_h": 6.0}, today - timedelta(days=1): {"sleep_h": 8.5}}
    assert vitals.sleep_debt(days, 8.0, today) == 2.0
    assert vitals.average_of(days, "sleep_h", today) == 7.25
    assert vitals.average_of({}, "sleep_h", today) is None


def test_heart_and_oxygen_notes():
    assert vitals.rhr_note(72)[1] == vitals.GOOD
    assert vitals.rhr_note(110)[1] == vitals.WARNING
    assert vitals.spo2_note(97)[1] == vitals.GOOD
    assert vitals.spo2_note(89)[1] == vitals.DANGER


def test_workout_calories_and_intensity():
    # 9.8 MET x 3.5 x 60 kg / 200 x 30 min = 308.7
    assert activity.workout_kcal(9.8, 60, 30) == 309
    assert activity.intensity(2.5) == "light"
    assert activity.intensity(4.3) == "moderate"
    assert activity.intensity(8.0) == "vigorous"


def test_vigorous_minutes_count_double():
    workouts = [
        {"met": 9.8, "minutes": 20},
        {"met": 3.5, "minutes": 30},
        {"met": 2.5, "minutes": 40},
    ]
    assert activity.moderate_minutes(workouts) == 70
    assert activity.active_minutes(workouts) == 50


def test_weekly_minutes_window():
    today = date(2026, 10, 31)
    days = {
        today: {"workouts": [{"met": 3.5, "minutes": 30}]},
        today - timedelta(days=6): {"workouts": [{"met": 3.5, "minutes": 30}]},
        today - timedelta(days=7): {"workouts": [{"met": 3.5, "minutes": 90}]},
    }
    assert activity.weekly_moderate_minutes(days, today) == 60


def test_water_pace_and_drinks():
    assert nutrition.expected_water_by_now(2000, datetime(2026, 10, 31, 6, 0)) == 0
    assert nutrition.expected_water_by_now(2000, datetime(2026, 10, 31, 14, 30)) == 1000
    assert nutrition.expected_water_by_now(2000, datetime(2026, 10, 31, 23, 0)) == 2000
    assert nutrition.caffeine_note(450)[1] == "warning"
    assert nutrition.caffeine_note(95, trying_to_conceive=True)[1] == "info"
    assert nutrition.caffeine_note(95)[1] == "good"
    assert nutrition.alcohol_note(2)[1] == "warning"
    assert nutrition.kcal_eaten([{"kcal": 400}, {"kcal": 250}]) == 650


def test_symptom_counts_and_correlation():
    days = {
        START: {"symptoms": ["Cramps", "Fatigue"]},
        START + timedelta(days=1): {"symptoms": ["Cramps"]},
    }
    assert journal.symptom_counts(days, START, START + timedelta(days=2)) == [
        ("Cramps", 2),
        ("Fatigue", 1),
    ]
    assert journal.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert journal.pearson([1, 1, 1], [1, 2, 3]) is None


def test_daylog_helpers_and_streak():
    data = {"days": {}}
    today = date(2026, 10, 31)
    daylog.add_amount(data, today, "water_ml", 250)
    daylog.add_amount(data, today, "water_ml", 250)
    assert data["days"][today]["water_ml"] == 500
    daylog.add_amount(data, today, "water_ml", -1000)
    assert today not in data["days"]  # an empty day is removed
    daylog.set_value(data, today, "mood", 4)
    daylog.set_value(data, today - timedelta(days=1), "mood", 3)
    assert daylog.logging_streak(data, today) == 2
    assert daylog.last_n_days(today, 3)[0] == today - timedelta(days=2)
