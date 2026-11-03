"""Load and save the JSON files. The only module that touches files.

Files, all inside DATA_DIR (Git ignores it, so real data never reaches GitHub):
    users.json        every account; auth.py describes one account's fields
    <user_id>.json    one user's health data, shaped like new_user_data()

Inside the program, dates are datetime.date and lockout times are
datetime.datetime. In the files they are ISO text ("2026-10-31",
"2026-10-31T14:05:00"). This module converts both ways, so no other module
ever handles date text.
"""

import copy
import csv
import json
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USERS_FILE_NAME = "users.json"
FILE_VERSION = 1


def new_users() -> dict:
    """Return an empty accounts dict, for the first run."""
    return {"version": FILE_VERSION, "users": [], "last_username": None}


def new_user_data() -> dict:
    """Return the data of a brand-new user; <user_id>.json has this shape.

    days maps a date to that day's log, e.g. {"bbt_c": 36.45, "mood": 4,
    "symptoms": ["Cramps"], "water_ml": 1500, "sleep_h": 7.5, "steps": 6000,
    "workouts": [{"type": "Walking", "minutes": 30}], ...}. See daylog.py.
    """
    return {
        "version": FILE_VERSION,
        "profile": {
            "display_name": "",
            "birth_date": None,
            "height_cm": None,
            "weight_kg": None,
            "activity_level": "light",
            "track_cycle": True,
            "focus": ["wellness"],  # any of profile.FOCUS_OPTIONS
            "cycle_length": 28,
            "period_length": 5,
            "onboarded": False,
        },
        "goals": {"steps": 8000, "water_ml": 2000, "sleep_h": 8.0, "active_min": 30},
        "settings": {
            "appearance": "system",
            "weight_unit": "kg",
            "height_unit": "cm",
            "temp_unit": "c",
            "bmi_standard": "cdc",
            "reduce_motion": False,
        },
        "periods": [],
        "weights": [],
        "days": {},
    }


def user_data_path(user_id: str, data_dir: Path = DATA_DIR) -> Path:
    """Return the path of one user's data file, e.g. data/u_3f9a1c2b.json."""
    return data_dir / f"{user_id}.json"


# Converting to and from JSON text ----------------------------------------------


def _to_json_ready(value):
    """Return a copy of value with every date and datetime turned into text."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            text_key = key.isoformat() if isinstance(key, date) else key
            result[text_key] = _to_json_ready(item)
        return result
    if isinstance(value, list):
        return [_to_json_ready(item) for item in value]
    return value


def _to_date(text: str | None) -> date | None:
    """Turn ISO date text into a date (None stays None)."""
    return None if text is None else date.fromisoformat(text)


def _to_datetime(text: str | None) -> datetime | None:
    """Turn ISO date-time text into a datetime (None stays None)."""
    return None if text is None else datetime.fromisoformat(text)


def _fill_missing(loaded: dict, defaults: dict) -> dict:
    """Return loaded with any key missing from an older file filled in."""
    for key, default_value in defaults.items():
        if key not in loaded:
            loaded[key] = copy.deepcopy(default_value)
        elif isinstance(default_value, dict) and isinstance(loaded[key], dict):
            if key != "days":
                _fill_missing(loaded[key], default_value)
    return loaded


def _users_from_json(raw: dict) -> dict:
    """Convert the text dates of a loaded users.json; KeyError if malformed."""
    users = _fill_missing(raw, new_users())
    for user in users["users"]:
        user["created_on"] = _to_date(user["created_on"])
        user["locked_until"] = _to_datetime(user.get("locked_until"))
        user.setdefault("failed_attempts", 0)
    return users


def _user_data_from_json(raw: dict) -> dict:
    """Convert the text dates of a loaded user data file."""
    data = _fill_missing(raw, new_user_data())
    data["profile"]["birth_date"] = _to_date(data["profile"]["birth_date"])
    if isinstance(data["profile"]["focus"], str):  # older files kept one reason
        data["profile"]["focus"] = [data["profile"]["focus"]]
    for period in data["periods"]:
        period["start"] = _to_date(period["start"])
        period["end"] = _to_date(period.get("end"))
    for entry in data["weights"]:
        entry["date"] = _to_date(entry["date"])
    data["days"] = {_to_date(key): log for key, log in data["days"].items()}
    return data


# Reading and writing -------------------------------------------------------------


def _write_json(path: Path, content: dict) -> None:
    """Write JSON safely: a temporary file first, then swap it in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    text = json.dumps(_to_json_ready(content), indent=2, ensure_ascii=False)
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _move_aside(path: Path) -> str:
    """Rename a damaged file and return a warning that names the copy."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.stem}.corrupt-{stamp}.json")
    path.replace(backup)
    return f"{path.name} was damaged, so it was moved to {backup.name}."


def _load(path: Path, convert, fresh) -> tuple[dict, str | None]:
    """Read a JSON file with `convert`; use `fresh()` when missing or broken."""
    if not path.exists():
        return fresh(), None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("The file is not a JSON object.")
        return convert(raw), None
    except (ValueError, KeyError, TypeError, AttributeError):
        return fresh(), _move_aside(path)


def load_users(data_dir: Path = DATA_DIR) -> tuple[dict, str | None]:
    """Read users.json and return (users, warning) (T17, T18).

    No file: (new_users(), None). A broken file is renamed to
    users.corrupt-<YYYYMMDD-HHMMSS>.json and new_users() is returned with a
    warning that names the copy.
    """
    return _load(data_dir / USERS_FILE_NAME, _users_from_json, new_users)


def save_users(users: dict, data_dir: Path = DATA_DIR) -> None:
    """Write users.json, converting dates and times to ISO text."""
    _write_json(data_dir / USERS_FILE_NAME, users)


def load_user_data(user_id: str, data_dir: Path = DATA_DIR) -> tuple[dict, str | None]:
    """Read one user's data file and return (data, warning)."""
    path = user_data_path(user_id, data_dir)
    return _load(path, _user_data_from_json, new_user_data)


def save_user_data(user_id: str, data: dict, data_dir: Path = DATA_DIR) -> None:
    """Write one user's data file, converting dates to ISO text."""
    _write_json(user_data_path(user_id, data_dir), data)


def delete_user_data(user_id: str, data_dir: Path = DATA_DIR) -> None:
    """Delete one user's data file; do nothing if it does not exist."""
    user_data_path(user_id, data_dir).unlink(missing_ok=True)


def export_csv(data: dict, path: Path) -> int:
    """Write every day's log to a CSV file for a spreadsheet; return the row count."""
    columns = [
        "date", "bbt_c", "flow", "mucus", "lh", "mood", "energy", "stress",
        "symptoms", "note", "rhr", "bp_sys", "bp_dia", "spo2", "sleep_h",
        "sleep_quality", "steps", "workout_minutes", "water_ml", "caffeine_mg",
        "alcohol", "fruit_veg", "kcal",
    ]  # fmt: skip
    rows = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for day in sorted(data["days"]):
            log = data["days"][day]
            row = [day.isoformat()]
            for column in columns[1:]:
                if column == "symptoms":
                    row.append("; ".join(log.get("symptoms", [])))
                elif column == "workout_minutes":
                    row.append(sum(w["minutes"] for w in log.get("workouts", [])))
                elif column == "kcal":
                    row.append(sum(m["kcal"] for m in log.get("meals", [])))
                else:
                    row.append(log.get(column, ""))
            writer.writerow(row)
            rows += 1
    return rows
