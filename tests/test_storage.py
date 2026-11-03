"""Tests for tracker/storage.py. Every test uses pytest's tmp_path."""

from datetime import date, datetime

import pytest

from tracker import auth, storage

TODAY = date(2026, 10, 31)


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    monkeypatch.setattr(auth, "PBKDF2_ITERATIONS", 1_000)


def test_t17_first_run_has_no_file(tmp_path):
    assert storage.load_users(tmp_path) == (storage.new_users(), None)


def test_t18_broken_file_moved_aside(tmp_path):
    (tmp_path / "users.json").write_text("{ not json", encoding="utf-8")
    users, warning = storage.load_users(tmp_path)
    assert users == storage.new_users()
    assert "was damaged" in warning
    assert len(list(tmp_path.glob("users.corrupt-*.json"))) == 1


def test_t31_no_plain_secrets_on_disk(tmp_path):
    users = storage.new_users()
    _, code = auth.register_user(users, "maria_c", "secret123", "secret123", TODAY)
    storage.save_users(users, tmp_path)
    text = (tmp_path / "users.json").read_text(encoding="utf-8")
    assert "secret123" not in text
    assert code not in text and auth.normalize_recovery_code(code) not in text


def test_users_round_trip_with_dates(tmp_path):
    users = storage.new_users()
    user, _ = auth.register_user(users, "maria_c", "secret123", "secret123", TODAY)
    user["locked_until"] = datetime(2026, 10, 31, 9, 0, 30)
    storage.save_users(users, tmp_path)
    loaded, warning = storage.load_users(tmp_path)
    assert warning is None
    assert loaded == users


def test_user_data_round_trip(tmp_path):
    data = storage.new_user_data()
    data["profile"]["birth_date"] = date(2004, 3, 15)
    data["periods"].append({"start": date(2026, 10, 3), "end": None})
    data["weights"].append({"date": TODAY, "weight_kg": 55.5})
    data["days"][TODAY] = {"mood": 4, "symptoms": ["Cramps"], "bbt_c": 36.45}
    storage.save_user_data("u_test", data, tmp_path)
    loaded, warning = storage.load_user_data("u_test", tmp_path)
    assert warning is None and loaded == data
    assert not list(tmp_path.glob("*.tmp"))  # the safe save left nothing behind


def test_older_file_gets_missing_keys(tmp_path):
    (tmp_path / "u_old.json").write_text(
        '{"version": 1, "profile": {"display_name": "A"}}', encoding="utf-8"
    )
    loaded, warning = storage.load_user_data("u_old", tmp_path)
    assert warning is None
    assert loaded["profile"]["display_name"] == "A"
    assert loaded["goals"]["steps"] == 8000 and loaded["days"] == {}


def test_delete_and_export(tmp_path):
    data = storage.new_user_data()
    data["days"][TODAY] = {
        "mood": 4,
        "symptoms": ["Cramps", "Fatigue"],
        "meals": [{"name": "Rice", "kcal": 300}],
    }
    storage.save_user_data("u_x", data, tmp_path)
    rows = storage.export_csv(data, tmp_path / "export.csv")
    assert rows == 1
    assert "Cramps; Fatigue" in (tmp_path / "export.csv").read_text(encoding="utf-8")
    storage.delete_user_data("u_x", tmp_path)
    storage.delete_user_data("u_x", tmp_path)  # a missing file is fine
    assert not (tmp_path / "u_x.json").exists()
