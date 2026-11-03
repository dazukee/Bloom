"""Tests for tracker/validators.py and tracker/units.py."""

from datetime import date

import pytest

from tracker import units, validators

TODAY = date(2026, 10, 31)


def test_t06_weight_not_a_number():
    with pytest.raises(ValueError, match=r"Weight must be a number, e\.g\. 55\.5\."):
        validators.parse_weight("abc")


@pytest.mark.parametrize("text", ["0", "-160", ""])
def test_t07_bad_heights(text):
    with pytest.raises(ValueError):
        validators.parse_height(text)


def test_t08_height_in_metres_gets_a_hint():
    with pytest.raises(ValueError) as error:
        validators.parse_height("1.6")
    assert str(error.value).endswith("Did you enter metres? Type 160 for 1.60 m.")


def test_t15_future_date_rejected():
    with pytest.raises(ValueError, match="cannot be in the future"):
        validators.parse_date("2026-11-01", TODAY)


@pytest.mark.parametrize("text", ["nan", "inf", "-inf"])
def test_nan_and_inf_are_not_weights(text):
    with pytest.raises(ValueError, match="must be a number"):
        validators.parse_weight(text)


@pytest.mark.parametrize("text", ["2026-02-30", "20261031", "31/10/2026", "2026-1-5"])
def test_bad_date_formats(text):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        validators.parse_date(text, TODAY)


def test_good_values():
    assert validators.parse_weight(" 55.5 ") == 55.5
    assert validators.parse_height("160") == 160
    assert validators.parse_date("2026-10-31", TODAY) == TODAY
    assert validators.parse_optional_date("  ", TODAY) is None
    assert validators.parse_display_name("  Maria ") == "Maria"


def test_pounds_and_feet():
    assert validators.parse_weight("121", "lb") == pytest.approx(54.88, abs=0.01)
    assert validators.parse_feet_inches("5", "3") == 160.0
    assert validators.parse_feet_inches("5", "") == 152.4


def test_temperature_units():
    assert validators.parse_temperature("36.45") == 36.45
    assert validators.parse_temperature("97.7", "f") == 36.5
    with pytest.raises(ValueError, match="between 34 and 42"):
        validators.parse_temperature("43")


def test_birth_date_age_range():
    with pytest.raises(ValueError, match="Age must be between"):
        validators.parse_birth_date("2020-01-01", TODAY)


def test_whole_numbers():
    assert validators.parse_number("72", "Heart rate", 30, 220, whole=True) == 72
    with pytest.raises(ValueError, match="whole number"):
        validators.parse_number("72.5", "Heart rate", 30, 220, whole=True)


def test_time_format():
    assert validators.parse_time("6:05") == "06:05"
    with pytest.raises(ValueError):
        validators.parse_time("25:00")


def test_unit_conversions():
    assert units.cm_to_ft_in(160) == (5, 3.0)
    assert units.ft_in_to_cm(5, 3) == pytest.approx(160.02)
    assert units.c_to_f(37) == pytest.approx(98.6)
    assert units.format_weight(55.5, "kg") == "55.5 kg"
    assert units.format_height(160, "ft") == "5 ft 3 in"
    assert units.format_temp(36.45, "c") == "36.45 °C"
