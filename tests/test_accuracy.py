"""Tests for the health-accuracy rules: signs, age-based targets and percentiles."""

from datetime import date, datetime, timedelta

import pytest

from tracker import (
    activity,
    bbt,
    bmi,
    calendar_logic,
    cycle,
    growth,
    insights,
    nutrition,
    profile,
    report,
    storage,
    vitals,
)

TODAY = date(2026, 10, 31)


def periods_from(*starts, length=5):
    return [{"start": s, "end": s + timedelta(days=length - 1)} for s in starts]


def make_data(*starts):
    data = storage.new_user_data()
    data["periods"] = periods_from(*starts)
    return data


# Fertile window margin --------------------------------------------------------


def test_margin_shrinks_as_history_grows():
    starts = [date(2026, 1, 1) + timedelta(days=28 * i) for i in range(6)]
    widths = []
    for count in range(1, 7):
        p = cycle.predict_cycle(periods_from(*starts[:count]))
        widths.append((p.fertile_end - p.fertile_start).days + 1)
    assert widths == [12, 12, 10, 10, 8, 8]


def test_fertile_window_never_inverts_for_very_short_cycles():
    p = cycle.predict_cycle(periods_from(date(2026, 1, 1), date(2026, 1, 8)))
    assert p.fertile_start <= p.fertile_end


def test_next_period_range_widens_with_uncertainty():
    one = cycle.predict_cycle(periods_from(date(2026, 1, 1)))
    assert (one.latest_next - one.next_start).days == 5
    steady = cycle.predict_cycle(
        periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 2, 26))
    )
    assert (steady.latest_next - steady.next_start).days == 2
    varied = cycle.predict_cycle(
        periods_from(
            date(2026, 1, 1), date(2026, 1, 25), date(2026, 3, 1), date(2026, 3, 29)
        )
    )
    assert (varied.latest_next - varied.next_start).days > 2


def test_one_measured_cycle_is_low_confidence():
    p = cycle.predict_cycle(periods_from(date(2026, 1, 1), date(2026, 1, 29)))
    assert p.confidence == "low"


# Ovulation signs ---------------------------------------------------------------


def test_temperature_sign_moves_the_next_period():
    start = date(2026, 10, 1)
    data = make_data(date(2026, 9, 3), start)  # calendar: next period Oct 29
    temps = [36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.3, 36.4]
    temps += [36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.3, 36.4, 36.3]
    temps += [36.7, 36.75, 36.8]  # first high on cycle day 18
    for offset, temp in enumerate(temps):
        data["days"][start + timedelta(days=offset)] = {"bbt_c": temp}
    p = insights.prediction_for(data)
    assert p.basis == "temperature"
    assert p.ovulation == start + timedelta(days=16)
    assert p.next_start == p.ovulation + timedelta(days=14)
    assert p.confidence == "high"
    assert p.fertile_end == p.ovulation + timedelta(days=1)


def test_lh_test_comes_before_temperature():
    start = date(2026, 10, 1)
    data = make_data(date(2026, 9, 3), start)
    data["days"][start + timedelta(days=12)] = {"lh": "positive"}
    p = insights.prediction_for(data)
    assert p.basis == "LH test"
    assert p.ovulation == start + timedelta(days=13)


def test_personal_gap_is_learned_from_past_cycles():
    starts = [date(2026, 8, 1), date(2026, 8, 29), date(2026, 9, 26)]
    days = {
        starts[0] + timedelta(days=15): {"lh": "positive"},  # gap 28 - 16 = 12
        starts[1] + timedelta(days=15): {"lh": "positive"},  # gap 12
    }
    assert bbt.usual_days_to_period(days, starts) == 12
    assert bbt.usual_days_to_period({starts[0]: {"lh": "positive"}}, starts) is None


def test_personal_gap_is_used_in_the_prediction():
    starts = [date(2026, 8, 1), date(2026, 8, 29), date(2026, 9, 26)]
    data = make_data(*starts)
    data["days"][starts[0] + timedelta(days=15)] = {"lh": "positive"}
    data["days"][starts[1] + timedelta(days=15)] = {"lh": "positive"}
    data["days"][starts[2] + timedelta(days=10)] = {"lh": "positive"}
    p = insights.prediction_for(data)
    assert p.next_start == starts[2] + timedelta(days=11 + 12)


# The 3-over-6 rule ---------------------------------------------------------------


def test_fourth_reading_confirms_a_small_rise():
    start = date(2026, 10, 1)
    temps = [36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.45, 36.5, 36.55, 36.5]
    readings = [(start + timedelta(days=i), t) for i, t in enumerate(temps)]
    shift = bbt.detect_thermal_shift(readings)
    assert shift.first_high == start + timedelta(days=6)


def test_fourth_reading_on_the_coverline_does_not_confirm():
    start = date(2026, 10, 1)
    temps = [36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.45, 36.5, 36.55, 36.4]
    readings = [(start + timedelta(days=i), t) for i, t in enumerate(temps)]
    assert bbt.detect_thermal_shift(readings) is None


def test_disturbed_readings_are_left_out():
    start = date(2026, 10, 1)
    days = {
        start: {"bbt_c": 36.4},
        start + timedelta(days=1): {"bbt_c": 37.2, "bbt_skip": True},
    }
    assert bbt.readings_between(days, start, start + timedelta(days=5)) == [
        (start, 36.4)
    ]


def test_unusual_time_note():
    start = date(2026, 10, 1)
    days = {start + timedelta(days=i): {"bbt_time": "06:00"} for i in range(6)}
    days[start + timedelta(days=6)] = {"bbt_time": "09:00"}
    assert "later" in bbt.unusual_time_note(days, start + timedelta(days=6))
    assert bbt.unusual_time_note(days, start) is None


# Late, stale and unusual cycles --------------------------------------------------


def test_late_period_rolls_forward():
    p = cycle.predict_cycle(periods_from(date(2026, 9, 1), date(2026, 9, 29)))
    today = p.next_start + timedelta(days=4)
    moved = cycle.rolled_forward(p, today)
    assert moved.next_start == today
    assert cycle.rolled_forward(p, p.next_start) is p
    # A past day is not coloured as a predicted period once the date has moved up.
    past = p.next_start + timedelta(days=1)
    assert calendar_logic.day_status(past, [], moved) != calendar_logic.STATUS_PREDICTED
    assert (
        calendar_logic.day_status(today, [], moved) == calendar_logic.STATUS_PREDICTED
    )


def test_phase_is_unknown_long_after_the_last_log():
    periods = periods_from(date(2025, 1, 1), date(2025, 1, 29))
    p = cycle.predict_cycle(periods)
    assert cycle.is_stale(p, TODAY)
    assert cycle.phase_on(TODAY, periods, p) is None


def test_no_period_for_three_months_is_flagged():
    data = make_data(TODAY - timedelta(days=120), TODAY - timedelta(days=92))
    found = insights.cycle_insights(data, TODAY)
    assert found[0]["title"] == "No period logged for 92 days"


def test_typical_range_depends_on_age():
    assert cycle.lengths_outside_typical_range([22, 44], 16) == []
    assert cycle.lengths_outside_typical_range([22, 44], 30) == [22, 44]
    assert cycle.lengths_outside_typical_range([22, 44]) == [22, 44]


def test_variation_allowed_depends_on_age():
    assert cycle.allowed_variation(30) == 7
    assert cycle.allowed_variation(22) == 9


def test_prolonged_periods():
    long_one = {"start": date(2026, 1, 1), "end": date(2026, 1, 9)}
    usual = {"start": date(2026, 2, 1), "end": date(2026, 2, 8)}
    open_one = {"start": date(2026, 3, 1), "end": None}
    assert cycle.prolonged_periods([long_one, usual, open_one]) == [long_one]


def test_stats_leave_out_forgotten_logs():
    periods = periods_from(date(2026, 1, 1), date(2026, 1, 29), date(2026, 5, 1))
    assert cycle.cycle_stats(periods)["longest"] == 28


def test_extendable_period_allows_a_long_period_to_end():
    periods = [{"start": date(2026, 10, 1), "end": None}]
    assert cycle.extendable_period(periods, date(2026, 10, 8)) == periods[0]
    assert cycle.extendable_period(periods, date(2026, 10, 16)) is None
    assert cycle.extendable_period(periods, date(2026, 9, 30)) is None


def test_starts_too_close_together_are_rejected():
    original = periods_from(date(2026, 10, 1))
    with pytest.raises(ValueError, match="too close"):
        cycle.add_period(original, date(2026, 10, 8), None, TODAY)


def test_next_fertile_window_after_this_one_has_passed():
    p = cycle.predict_cycle(periods_from(date(2026, 9, 1), date(2026, 9, 29)))
    start, end, this_cycle = cycle.fertile_window_ahead(p, date(2026, 10, 1))
    assert this_cycle and start == p.fertile_start
    start, end, this_cycle = cycle.fertile_window_ahead(
        p, p.fertile_end + timedelta(days=1)
    )
    assert not this_cycle
    assert start == p.next_start + timedelta(days=p.fertile_from)
    assert end == p.next_start + timedelta(days=p.fertile_to)


def test_hormone_chart_ovulation_matches_the_prediction():
    assert cycle.schematic_ovulation_day(28) == 15


# BMI for girls under 20 ------------------------------------------------------------


def test_percentile_at_the_median_is_50():
    median = growth.GIRLS_BMI_LMS[60][1]
    assert growth.percentile(median, 180) == pytest.approx(50, abs=0.1)


def test_percentile_cut_offs_match_the_chart():
    assert growth.bmi_at_z(growth.Z_95TH, 180) == pytest.approx(28.1, abs=0.1)
    assert growth.bmi_at_z(growth.Z_85TH, 180) == pytest.approx(24.0, abs=0.1)
    assert growth.bmi_at_z(growth.Z_5TH, 180) == pytest.approx(16.3, abs=0.1)


@pytest.mark.parametrize(
    ("value", "category"),
    [
        (15.5, bmi.UNDERWEIGHT),
        (20.0, bmi.HEALTHY_WEIGHT),
        (26.0, bmi.OVERWEIGHT),
        (30.0, bmi.OBESITY),
    ],
)
def test_girl_categories_use_percentiles(value, category):
    assert growth.assess(value, 160, 180).category == category


def test_same_bmi_differs_by_age():
    assert growth.assess(24.5, 160, 180).category == bmi.OVERWEIGHT
    assert growth.assess(24.5, 160, 300).category == bmi.HEALTHY_WEIGHT


def test_adults_use_the_chosen_table():
    assert growth.assess(24, 160, 300, bmi.ASIA_PACIFIC).category == bmi.OVERWEIGHT
    assert growth.assess(24, 160, None).percentile is None


def test_girl_healthy_range_contains_the_median():
    result = growth.assess(20, 160, 180)
    assert result.healthy_low_kg < 20 * 1.6**2 < result.healthy_high_kg


def test_age_in_months():
    assert growth.age_in_months(date(2010, 5, 15), date(2026, 5, 14)) == 191
    assert growth.age_in_months(date(2010, 5, 15), date(2026, 5, 15)) == 192


def test_obesity_classes():
    assert bmi.obesity_class(29.9) is None
    assert [bmi.obesity_class(v) for v in (30, 35, 40)] == [1, 2, 3]


# Age-based targets --------------------------------------------------------------------


def test_energy_requirement_for_girls_matches_the_equation():
    # 135.3 - 30.8*15 + 1.31*(10*50 + 934*1.6) + 25 = 2,311
    assert profile.estimated_energy_requirement_girl(50, 160, 15, "moderate") == 2310


def test_calorie_target_switches_at_19():
    data = storage.new_user_data()
    data["profile"].update(height_cm=160.0, weight_kg=50.0, activity_level="moderate")
    data["profile"]["birth_date"] = date(2011, 1, 1)  # 15
    assert profile.calorie_target(data, TODAY) == 2310
    data["profile"]["birth_date"] = date(2000, 1, 1)  # 26
    assert (
        profile.calorie_target(data, TODAY)
        == round(profile.bmr_mifflin_st_jeor(50, 160, 26) * 1.55 / 10) * 10
    )


def test_caffeine_mark_depends_on_age_and_conceiving():
    assert nutrition.caffeine_limit() == 400
    assert nutrition.caffeine_limit(16) == 100
    assert nutrition.caffeine_limit(30, True) == 200
    assert nutrition.caffeine_note(150, False, 16)[1] == "warning"
    assert nutrition.caffeine_note(250, True, 30)[1] == "warning"


def test_alcohol_under_18():
    assert nutrition.alcohol_note(1, 16)[1] == "warning"
    assert nutrition.alcohol_note(1, 30)[1] == "info"


def test_protein_and_nutrients_by_age():
    assert nutrition.protein_target_g(50) == 40
    assert nutrition.protein_target_g(50, 16) == 42
    assert nutrition.protein_target_g(40, 12) == 38
    assert nutrition.daily_nutrients(30)["Iron"][0] == "18 mg"
    assert nutrition.daily_nutrients(16)["Iron"][0] == "15 mg"
    assert nutrition.daily_nutrients(12)["Iron"][0] == "8 mg"
    assert nutrition.daily_nutrients(16)["Calcium"][0] == "1,300 mg"


def test_activity_goal_by_age():
    assert activity.weekly_goal_minutes(16) == 420
    assert activity.weekly_goal_minutes(30) == 150


def test_strength_days():
    days = {
        TODAY: {"workouts": [{"type": "Strength training", "met": 3.5, "minutes": 20}]},
        TODAY - timedelta(days=2): {
            "workouts": [{"type": "Walking", "met": 3.5, "minutes": 20}]
        },
    }
    assert activity.strength_days(days, TODAY) == 1


def test_sleep_recommendation_by_age():
    assert vitals.recommended_sleep(11) == 9
    assert vitals.recommended_sleep(15) == 8
    assert vitals.recommended_sleep(30) == 7
    assert vitals.sleep_note(7.5, 7, 15)[1] == vitals.INFO
    assert vitals.sleep_note(6, 8, 30)[1] == vitals.WARNING


@pytest.mark.parametrize(
    ("systolic", "diastolic", "category"),
    [
        (85, 70, "Low"),
        (110, 55, "Low"),
        (90, 60, "Normal"),
        (150, 55, "Stage 2 hypertension"),
    ],
)
def test_low_blood_pressure(systolic, diastolic, category):
    assert vitals.bp_category(systolic, diastolic)[0] == category


def test_blood_pressure_average():
    days = {
        TODAY: {"bp_sys": 130, "bp_dia": 80},
        TODAY - timedelta(days=1): {"bp_sys": 120, "bp_dia": 70},
    }
    assert vitals.bp_average(days, TODAY) == (125, 75, 2)
    assert vitals.bp_average({}, TODAY) is None


def test_high_average_blood_pressure_is_flagged():
    data = make_data()
    for i in range(3):
        data["days"][TODAY - timedelta(days=i)] = {"bp_sys": 135, "bp_dia": 85}
    found = insights.habit_insights(data, datetime(2026, 10, 31, 9, 0))
    assert "Blood pressure averaging 135/85" in [item["title"] for item in found]


@pytest.mark.parametrize(
    ("percent", "tone"),
    [(95, vitals.GOOD), (93, vitals.WARNING), (92, vitals.DANGER)],
)
def test_oxygen_follows_nhs_advice(percent, tone):
    assert vitals.spo2_note(percent)[1] == tone


def test_fast_weight_change_is_flagged():
    data = make_data()
    data["weights"] = [
        {"date": TODAY - timedelta(days=20), "weight_kg": 60.0},
        {"date": TODAY, "weight_kg": 56.0},
    ]
    assert (
        insights.body_insights(data, TODAY)[0]["title"] == "Weight down 7% in a month"
    )
    data["weights"][1]["weight_kg"] = 59.0
    assert insights.body_insights(data, TODAY) == []


def test_mucus_sign_is_noticed():
    data = make_data(TODAY - timedelta(days=12))
    data["days"][TODAY] = {"mucus": "egg white"}
    titles = [item["title"] for item in insights.cycle_insights(data, TODAY)]
    assert "A fertile sign today" in titles


# Report and export --------------------------------------------------------------------


def test_doctor_summary_contains_the_facts_and_escapes_text():
    data = make_data(date(2026, 9, 1), date(2026, 9, 29))
    data["profile"].update(
        display_name="<b>Maria</b>",
        height_cm=160.0,
        weight_kg=55.0,
        birth_date=date(2000, 1, 1),
    )
    data["days"][TODAY] = {"bp_sys": 118, "bp_dia": 76, "symptoms": ["Cramps"]}
    text = report.doctor_summary_html(data, "maria", TODAY)
    assert "&lt;b&gt;Maria&lt;/b&gt;" in text and "<b>Maria" not in text
    assert "average 28 days" in text
    assert "118/76" in text
    assert "Cramps" in text
    assert "not a diagnosis" in text


def test_summary_works_with_no_data():
    data = storage.new_user_data()
    assert "Health summary" in report.doctor_summary_html(data, "maria", TODAY)


def test_csv_blocks_formulas(tmp_path):
    data = storage.new_user_data()
    data["days"][TODAY] = {"note": "=HYPERLINK(1)"}
    storage.export_csv(data, tmp_path / "x.csv")
    assert "'=HYPERLINK" in (tmp_path / "x.csv").read_text(encoding="utf-8-sig")
