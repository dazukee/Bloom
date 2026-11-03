"""Tests for tracker/insights.py: the right insight appears for the right data."""

from datetime import date, datetime, timedelta

from tracker import insights, storage

NOW = datetime(2026, 10, 31, 15, 0)
TODAY = NOW.date()


def make_data(*period_starts):
    """Return fresh user data with 5-day periods on the given dates."""
    data = storage.new_user_data()
    for start in period_starts:
        data["periods"].append({"start": start, "end": start + timedelta(days=4)})
    return data


def titles(found):
    return [item["title"] for item in found]


def test_no_period_asks_for_one():
    assert titles(insights.cycle_insights(make_data(), TODAY)) == [
        "Log your last period"
    ]


def test_period_due_soon_and_late():
    soon = make_data(date(2026, 9, 6), date(2026, 10, 4))  # next: Nov 1
    assert "Period expected in 1 day" in titles(insights.cycle_insights(soon, TODAY))
    late = make_data(date(2026, 8, 30), date(2026, 9, 27))  # next: Oct 25
    assert "Period 6 days late" in titles(insights.cycle_insights(late, TODAY))


def test_fertile_window_message_depends_on_focus():
    data = make_data(date(2026, 9, 21), date(2026, 10, 19))  # fertile Oct 28 - Nov 4
    data["profile"]["focus"] = ["cycle", "avoid"]
    found = insights.cycle_insights(data, TODAY)
    fertile = [item for item in found if item["title"] == "Fertile window"][0]
    assert "not birth control" in fertile["text"]


def test_severe_blood_pressure_is_first():
    data = make_data(date(2026, 10, 19))
    data["days"][TODAY] = {"bp_sys": 185, "bp_dia": 100}
    found = insights.build_insights(data, NOW)
    assert found[0]["tone"] == "danger"
    assert found[0]["title"] == "Very high blood pressure"


def test_ovulation_confirmed_by_temperature():
    data = make_data(date(2026, 10, 10))
    temps = [36.3, 36.4, 36.3, 36.35, 36.4, 36.3, 36.5, 36.55, 36.6]
    for i, temp in enumerate(temps):
        data["days"][date(2026, 10, 15) + timedelta(days=i)] = {"bbt_c": temp}
    assert "Ovulation confirmed" in titles(insights.cycle_insights(data, TODAY))


def test_sleep_mood_pattern_needs_enough_days():
    data = make_data()
    for i in range(8):
        good_night = i % 2 == 0
        data["days"][TODAY - timedelta(days=i)] = {
            "sleep_h": 8.0 if good_night else 5.5,
            "mood": 5 if good_night else 3,
        }
    assert "Sleep lifts your mood" in titles(insights.pattern_insights(data, TODAY))
    sparse = make_data()
    sparse["days"][TODAY] = {"sleep_h": 8.0, "mood": 5}
    assert insights.pattern_insights(sparse, TODAY) == []


def test_water_nudge_and_streak():
    data = make_data()
    for i in range(3):
        data["days"][TODAY - timedelta(days=i)] = {"mood": 4}
    found = titles(insights.habit_insights(data, NOW))
    assert "Time for some water" in found
    assert "3-day streak" in found


def test_checklist_marks_done_items():
    data = make_data()
    data["days"][TODAY] = {"mood": 4, "water_ml": 2000, "steps": 9000}
    done = {
        item["page"]: item["done"] for item in insights.daily_checklist(data, TODAY)
    }
    assert done == {
        "bbt": False,
        "journal": True,
        "nutrition": True,
        "vitals": False,
        "activity": True,
    }


def test_tracking_off_hides_cycle_items():
    data = make_data(date(2026, 10, 19))
    data["profile"]["track_cycle"] = False
    assert insights.cycle_insights(data, TODAY) == []
    assert "bbt" not in [item["page"] for item in insights.daily_checklist(data, TODAY)]
