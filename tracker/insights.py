"""Smart insights for the Today screen: alerts, cycle news, habits, patterns.

Pure logic: no customtkinter, no file access.

Each insight is a dict:
    {"tone": "danger" | "warning" | "info" | "good", "icon": str,
     "title": str, "text": str, "page": str | None}
Alerts come first, then the rest by importance. Every pattern needs enough
data before it speaks, so the app never guesses from one or two days.
"""

from datetime import date, datetime, timedelta

from tracker import activity, bbt, cycle, daylog, journal, nutrition, profile, vitals

TONE_ORDER = {"danger": 0, "warning": 1, "info": 2, "good": 3}
PATTERN_WINDOW_DAYS = 120


def _insight(
    tone: str, icon: str, title: str, text: str, page: str | None = None
) -> dict:
    """Bundle one insight."""
    return {"tone": tone, "icon": icon, "title": title, "text": text, "page": page}


def _plural(count: int, word: str) -> str:
    """Return "1 day" or "3 days"."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def prediction_for(data: dict) -> cycle.CyclePrediction | None:
    """Return the cycle prediction, using the profile's usual lengths as defaults."""
    p = data["profile"]
    if not p.get("track_cycle", True):
        return None
    return cycle.predict_cycle(
        data["periods"],
        p.get("cycle_length", cycle.DEFAULT_CYCLE_LENGTH),
        p.get("period_length", cycle.DEFAULT_PERIOD_LENGTH),
    )


def phase_today(data: dict, today: date) -> str | None:
    """Return today's cycle phase, or None when it is unknown."""
    prediction = prediction_for(data)
    period_length = data["profile"].get("period_length", cycle.DEFAULT_PERIOD_LENGTH)
    return cycle.phase_on(today, data["periods"], prediction, period_length)


def current_shift(data: dict, today: date) -> bbt.ThermalShift | None:
    """Return this cycle's temperature shift, if the readings show one."""
    prediction = prediction_for(data)
    if prediction is None:
        return None
    readings = bbt.readings_between(data["days"], prediction.last_start, today)
    return bbt.detect_thermal_shift(readings)


def alert_insights(data: dict, today: date) -> list[dict]:
    """Return urgent notes about today's readings."""
    log = daylog.peek_day(data, today)
    found = []
    if "bp_sys" in log and "bp_dia" in log:
        _, tone = vitals.bp_category(log["bp_sys"], log["bp_dia"])
        if tone == vitals.DANGER:
            found.append(
                _insight(
                    "danger",
                    "heart",
                    "Very high blood pressure",
                    vitals.SEVERE_BP_ADVICE,
                    "vitals",
                )
            )
    if "bbt_c" in log and bbt.is_fever(log["bbt_c"]):
        found.append(_insight(
            "warning", "thermometer", "Temperature in the fever range",
            "38.0 °C or higher is a fever, so it is left out of your ovulation chart. "
            "Rest, drink fluids and seek care if you feel unwell.", "bbt",
        ))  # fmt: skip
    if "spo2" in log:
        _, tone = vitals.spo2_note(log["spo2"])
        if tone == vitals.DANGER:
            found.append(
                _insight(
                    "danger",
                    "heart",
                    "Low blood oxygen",
                    vitals.spo2_note(log["spo2"])[0],
                    "vitals",
                )
            )
    return found


def cycle_insights(data: dict, today: date) -> list[dict]:
    """Return notes about the period, fertile window and confirmed ovulation."""
    if not data["profile"].get("track_cycle", True):
        return []
    prediction = prediction_for(data)
    if prediction is None:
        return [_insight(
            "info", "drop", "Log your last period",
            "Two or more periods give the app enough to predict your next one.", "cycle",
        )]  # fmt: skip

    found = []
    days = cycle.days_until(prediction.next_start, today)
    if days < 0:
        found.append(_insight(
            "info", "drop", f"Period {_plural(-days, 'day')} late",
            "Late periods are common: stress, illness and travel can shift a cycle. "
            "If you might be pregnant, a home test can tell you.", "cycle",
        ))  # fmt: skip
    elif days == 0:
        found.append(
            _insight(
                "info",
                "drop",
                "Period expected today",
                "Log it when it starts so predictions keep improving.",
                "cycle",
            )
        )
    elif days <= 3:
        found.append(_insight(
            "info", "drop", f"Period expected in {_plural(days, 'day')}",
            "Cramps and tiredness are common in the days before; keep supplies handy.", "cycle",
        ))  # fmt: skip

    if prediction.fertile_start <= today <= prediction.fertile_end:
        ovulation = prediction.ovulation.strftime("%b %d")
        if profile.has_focus(data["profile"], "conceive"):
            text = f"Your best days to conceive, especially the 2 days before ovulation (around {ovulation})."
        elif profile.has_focus(data["profile"], "avoid"):
            text = "Predicted fertile days are estimates and are not birth control."
        else:
            text = (
                f"Estimated fertile window; ovulation is expected around {ovulation}."
            )
        found.append(_insight("info", "sparkle", "Fertile window", text, "cycle"))

    shift = current_shift(data, today)
    if shift is not None:
        found.append(_insight(
            "good", "thermometer", "Ovulation confirmed",
            f"Your temperature rose on {shift.first_high:%b %d}, so ovulation most likely "
            f"happened around {shift.ovulation:%b %d}.", "bbt",
        ))  # fmt: skip

    recent = cycle.cycle_lengths(cycle.period_starts(data["periods"]))[
        -cycle.CYCLES_TO_AVERAGE :
    ]
    unusual = cycle.lengths_outside_typical_range(recent)
    if len(unusual) >= 2:
        found.append(_insight(
            "warning", "drop", "Cycles outside the typical range",
            f"{len(unusual)} of your last {len(recent)} cycles were outside 24-38 days. "
            "If this continues, consider talking to a doctor.", "cycle",
        ))  # fmt: skip
    return found


def habit_insights(data: dict, now: datetime) -> list[dict]:
    """Return notes about sleep, water, activity, caffeine and logging streaks."""
    today = now.date()
    log = daylog.peek_day(data, today)
    goals = data["goals"]
    found = []

    debt = vitals.sleep_debt(data["days"], goals["sleep_h"], today)
    if debt >= 5:
        found.append(_insight(
            "warning", "moon", f"Sleep debt: {debt:g} h this week",
            "You are behind your sleep goal. A few earlier nights help you catch up.", "vitals",
        ))  # fmt: skip

    water = log.get("water_ml", 0)
    expected = nutrition.expected_water_by_now(goals["water_ml"], now)
    if now.hour >= 12 and water < expected * 0.5:
        found.append(_insight(
            "info", "cup", "Time for some water",
            f"{water} of {goals['water_ml']} ml so far; about {expected} ml is due by now.", "nutrition",
        ))  # fmt: skip

    weekly = activity.weekly_moderate_minutes(data["days"], today)
    if weekly >= activity.WHO_WEEKLY_MINUTES:
        found.append(_insight(
            "good", "activity", "150 active minutes reached",
            f"{weekly} active minutes in the last 7 days meets the WHO recommendation.", "activity",
        ))  # fmt: skip
    elif weekly >= 100:
        found.append(_insight(
            "info", "activity", f"{activity.WHO_WEEKLY_MINUTES - weekly} active minutes to go",
            f"{weekly} of the 150 minutes WHO recommends each week.", "activity",
        ))  # fmt: skip

    if log.get("caffeine_mg", 0) > nutrition.CAFFEINE_LIMIT_MG:
        found.append(
            _insight(
                "warning",
                "cup",
                "A lot of caffeine today",
                nutrition.caffeine_note(log["caffeine_mg"])[0],
                "nutrition",
            )
        )

    streak = daylog.logging_streak(data, today)
    if streak >= 3:
        found.append(_insight(
            "good", "flame", f"{streak}-day streak",
            "You have logged something every day. Small daily check-ins add up.", None,
        ))  # fmt: skip
    return found


def pattern_insights(data: dict, today: date) -> list[dict]:
    """Return personal patterns: mood by phase, sleep and mood, symptom timing."""
    found = []
    start = today - timedelta(days=PATTERN_WINDOW_DAYS)
    prediction = prediction_for(data)
    period_length = data["profile"].get("period_length", cycle.DEFAULT_PERIOD_LENGTH)

    if prediction is not None:
        luteal, other = [], []
        for day, log in data["days"].items():
            if start <= day <= today and "mood" in log:
                phase = cycle.phase_on(day, data["periods"], prediction, period_length)
                (luteal if phase == cycle.LUTEAL else other).append(log["mood"])
        if len(luteal) >= 3 and len(other) >= 3:
            luteal_avg = sum(luteal) / len(luteal)
            other_avg = sum(other) / len(other)
            if other_avg - luteal_avg >= 0.7:
                found.append(_insight(
                    "info", "smile", "Your mood dips before your period",
                    f"Mood averages {luteal_avg:.1f} in your luteal phase and {other_avg:.1f} "
                    "at other times, a common PMS pattern. Plan gentler days.", "journal",
                ))  # fmt: skip

        counts = journal.symptom_counts(data["days"], start, today)
        if counts and counts[0][1] >= 3:
            symptom, total = counts[0]
            by_phase: dict[str, int] = {}
            for day, log in data["days"].items():
                if start <= day <= today and symptom in log.get("symptoms", []):
                    phase = cycle.phase_on(
                        day, data["periods"], prediction, period_length
                    )
                    if phase:
                        by_phase[phase] = by_phase.get(phase, 0) + 1
            if by_phase:
                phase, hits = max(by_phase.items(), key=lambda item: item[1])
                if hits / total >= 0.6:
                    found.append(_insight(
                        "info", "journal", f"{symptom} clusters in your {phase} phase",
                        f"{hits} of the {total} times you logged it. Knowing when it comes "
                        "helps you plan ahead.", "journal",
                    ))  # fmt: skip

    pairs = journal.sleep_mood_pairs(data["days"], today)
    if len(pairs) >= 7:
        split = journal.split_average(pairs, vitals.MIN_SLEEP_HOURS)
        if split is not None and split[0] - split[1] >= 0.5:
            found.append(_insight(
                "good", "moon", "Sleep lifts your mood",
                f"After 7+ hours of sleep your mood averages {split[0]:.1f}, and "
                f"{split[1]:.1f} after shorter nights.", "vitals",
            ))  # fmt: skip
    return found


def build_insights(data: dict, now: datetime, limit: int = 6) -> list[dict]:
    """Return the most useful insights for now, alerts first."""
    today = now.date()
    found = alert_insights(data, today)
    found += cycle_insights(data, today)
    found += pattern_insights(data, today)
    found += habit_insights(data, now)
    found.sort(key=lambda item: TONE_ORDER[item["tone"]])  # stable: keeps topic order
    return found[:limit]


def daily_checklist(data: dict, today: date) -> list[dict]:
    """Return today's small tasks, each {"label", "done", "page"}."""
    log = daylog.peek_day(data, today)
    goals = data["goals"]
    items = []
    if data["profile"].get("track_cycle", True):
        items.append(
            {"label": "Log your temperature", "done": "bbt_c" in log, "page": "bbt"}
        )
    items.append(
        {"label": "Check in with your mood", "done": "mood" in log, "page": "journal"}
    )
    items.append({
        "label": f"Drink {goals['water_ml']:,} ml of water",
        "done": log.get("water_ml", 0) >= goals["water_ml"],
        "page": "nutrition",
    })  # fmt: skip
    items.append(
        {"label": "Log last night's sleep", "done": "sleep_h" in log, "page": "vitals"}
    )
    moved = activity.active_minutes(log.get("workouts", [])) >= goals["active_min"]
    moved = moved or log.get("steps", 0) >= goals["steps"]
    items.append({
        "label": f"Move {goals['active_min']} min or walk {goals['steps']:,} steps",
        "done": moved,
        "page": "activity",
    })  # fmt: skip
    return items
