import io
import wave
from datetime import date, timedelta

import pytest

from tracker import garden, sound, storage
from tracker.ui import theme

TODAY = date(2026, 11, 7)
FULL_LOG = {
    "steps": 9000,
    "water_ml": 2000,
    "sleep_h": 8.0,
    "mood": 4,
    "rhr": 70,
    "meals": [{"name": "Rice", "kcal": 300}],
}


def make_data(days):
    data = storage.new_user_data()
    data["days"] = days
    return data


def test_empty_day_has_no_petals():
    assert garden.petal_count(make_data({}), TODAY) == 0


def test_full_day_has_all_petals():
    data = make_data({TODAY: dict(FULL_LOG)})
    assert garden.petal_count(data, TODAY) == garden.TOTAL_PETALS


def test_goal_just_under_earns_no_petal():
    data = make_data({TODAY: {"water_ml": 1999}})
    assert garden.petal_count(data, TODAY) == 0


def test_garden_days_is_oldest_first():
    days = garden.garden_days(make_data({}), TODAY, 3)
    assert [day for day, _ in days] == [
        TODAY - timedelta(days=2),
        TODAY - timedelta(days=1),
        TODAY,
    ]


def test_longest_streak_survives_a_gap():
    days = {TODAY - timedelta(days=n): {"mood": 3} for n in (0, 1, 5, 6, 7)}
    assert garden.longest_streak(make_data(days)) == 3


def test_achievements_for_new_and_full_users():
    assert garden.earned_achievements(make_data({})) == set()
    earned = garden.earned_achievements(make_data({TODAY: dict(FULL_LOG)}))
    assert {"seed", "full"} <= earned
    assert "sprout" not in earned


@pytest.mark.parametrize("pack", sound.PACKS)
@pytest.mark.parametrize("event", sound.SOUNDS)
def test_every_sound_is_a_valid_wav(pack, event):
    with wave.open(io.BytesIO(sound.render(event, pack, 60))) as file:
        assert file.getframerate() == sound.SAMPLE_RATE
        assert file.getnframes() > 0


def test_every_sound_has_a_settings_switch():
    assert set(sound.SOUNDS) == set(sound.CATEGORIES)


def test_volume_never_overflows():
    assert sound.render("click", "retro", 500)  # struct.pack fails on overflow


@pytest.mark.parametrize("accent", theme.ACCENTS)
def test_accents_keep_white_text_readable(accent):
    theme.set_accent(accent)
    try:
        for token in theme.KEEP_READABLE:
            assert theme.contrast(theme.PALETTE[token][0], "#FFFFFF") >= 4.5
        for token in theme.KEEP_READABLE_DARK:
            assert theme.contrast(theme.PALETTE[token][1], "#FFFFFF") >= 4.5
    finally:
        theme.set_accent("bloom")


def test_old_data_files_get_the_new_settings(tmp_path):
    (tmp_path / "abc.json").write_text(
        '{"version": 1, "settings": {"appearance": "dark"}}', encoding="utf-8"
    )
    data, _ = storage.load_user_data("abc", tmp_path)
    assert data["settings"]["appearance"] == "dark"
    assert data["settings"]["font"] == "poppins"
