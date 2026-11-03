"""Tests for tracker/bmi.py and tracker/profile.py."""

from datetime import date

import pytest

from tracker import bmi, profile


def test_t01_basic_bmi():
    assert bmi.calculate_bmi(55, 160) == 21.5
    assert bmi.classify_bmi(21.5) == bmi.HEALTHY_WEIGHT


def test_t02_underweight():
    assert bmi.calculate_bmi(47, 160) == 18.4
    assert bmi.classify_bmi(18.4) == bmi.UNDERWEIGHT


def test_t03_bmi_boundary_uses_rounded_value():
    value = bmi.calculate_bmi(47.36, 160)  # raw 18.4999...
    assert value == 18.5
    assert bmi.classify_bmi(value) == bmi.HEALTHY_WEIGHT


def test_t04_upper_boundary():
    value = bmi.calculate_bmi(64, 160)  # raw 24.9999...
    assert value == 25.0
    assert bmi.classify_bmi(value) == bmi.OVERWEIGHT


def test_t05_healthy_range():
    assert bmi.healthy_weight_range(160) == (47.4, 63.7)


def test_t20_adult_categories_from_twenty():
    assert bmi.adult_categories_apply(17) is False
    assert bmi.adult_categories_apply(20) is True


def test_asia_pacific_cut_offs():
    assert bmi.classify_bmi(22.9, bmi.ASIA_PACIFIC) == bmi.HEALTHY_WEIGHT
    assert bmi.classify_bmi(23.0, bmi.ASIA_PACIFIC) == bmi.OVERWEIGHT
    assert bmi.classify_bmi(27.0, bmi.ASIA_PACIFIC) == bmi.OBESITY_1
    assert bmi.healthy_weight_range(160, bmi.ASIA_PACIFIC) == (47.4, 58.6)


@pytest.mark.parametrize(
    ("weight", "height"), [(19.9, 160), (300.1, 160), (55, 49), (55, 251)]
)
def test_out_of_range_raises(weight, height):
    with pytest.raises(ValueError):
        bmi.calculate_bmi(weight, height)


def test_age_around_birthday():
    assert bmi.calculate_age(date(2005, 11, 1), date(2026, 10, 31)) == 20
    assert bmi.calculate_age(date(2005, 10, 31), date(2026, 10, 31)) == 21


def test_age_for_29_february_birthday():
    born = date(2004, 2, 29)
    assert bmi.calculate_age(born, date(2027, 2, 28)) == 22
    assert bmi.calculate_age(born, date(2027, 3, 1)) == 23


def test_age_rejects_future_birth():
    with pytest.raises(ValueError):
        bmi.calculate_age(date(2027, 1, 1), date(2026, 10, 31))


def test_mifflin_st_jeor_and_calorie_target():
    # 10*60 + 6.25*165 - 5*25 - 161 = 1345.25
    assert profile.bmr_mifflin_st_jeor(60, 165, 25) == pytest.approx(1345.25)
    assert profile.daily_calorie_target(60, 165, 25, "moderate") == 2090


def test_water_suggestion_is_clamped():
    assert profile.suggested_water_ml(60) == 2000
    assert profile.suggested_water_ml(30) == 1500
    assert profile.suggested_water_ml(150) == 3500
    assert profile.suggested_water_ml(None) == 2000


def test_initials():
    assert profile.initials("Maria Santos Cruz") == "MC"
    assert profile.initials("ana") == "A"
    assert profile.initials("  ") == "?"


def test_focus_can_be_ticked_and_unticked():
    chosen = profile.toggle_focus(["wellness"], "cycle")
    assert chosen == ["wellness", "cycle"]
    assert profile.toggle_focus(chosen, "wellness") == ["cycle"]
    assert profile.toggle_focus(["cycle"], "cycle") == []


def test_conceive_and_avoid_exclude_each_other():
    assert profile.toggle_focus(["cycle", "conceive"], "avoid") == ["cycle", "avoid"]
    assert profile.toggle_focus(["avoid"], "conceive") == ["conceive"]


def test_focus_list_reads_old_single_value_files():
    assert profile.focus_list({"focus": "conceive"}) == ["conceive"]
    assert profile.focus_list({"focus": ["cycle", "unknown"]}) == ["cycle"]
    assert profile.focus_list({}) == []
    assert profile.has_focus({"focus": ["avoid"]}, "avoid")
