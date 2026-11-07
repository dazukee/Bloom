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
MIN_PATTERN_DAYS = 5  # each side of a comparison, so a few odd days prove nothing
FAST_WEIGHT_CHANGE = 0.05  # 5% of body weight
FAST_WEIGHT_WINDOW_DAYS = 30
FERTILE_MUCUS = ("egg white", "watery")


def _insight(
    tone: str, icon: str, title: str, text: str, page: str | None = None
) -> dict:
    """Bundle one insight."""
    return {"tone": tone, "icon": icon, "title": title, "text": text, "page": page}


def _plural(count: int, word: str) -> str:
    """Return "1 day" or "3 days"."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def prediction_for(data: dict) -> cycle.CyclePrediction | None:
    """Return the cycle prediction, using the profile's usual lengths as defaults.

    When this cycle's temperature or LH tests show ovulation, the next period is
    counted from it, using the person's own usual gap once past cycles show one.
    """
    p = data["profile"]
    if not p.get("track_cycle", True):
        return None
    prediction = cycle.predict_cycle(
        data["periods"],
        p.get("cycle_length", cycle.DEFAULT_CYCLE_LENGTH),
        p.get("period_length", cycle.DEFAULT_PERIOD_LENGTH),
    )
    if prediction is None:
        return None
    last_day = prediction.last_start + timedelta(days=cycle.MISSED_LOG_DAYS)
    sign = bbt.ovulation_sign(data["days"], prediction.last_start, last_day)
    if sign is None:
        return prediction
    usual_gap = bbt.usual_days_to_period(
        data["days"], cycle.period_starts(data["periods"])
    )
    return cycle.with_ovulation_sign(prediction, sign[0], sign[1], usual_gap)


def phase_today(data: dict, today: date) -> str | None:
    """Return today's cycle phase, or None when it is unknown."""
    prediction = prediction_for(data)
    period_length = data["profile"].get("period_length", cycle.DEFAULT_PERIOD_LENGTH)
    return cycle.phase_on(today, data["periods"], prediction, period_length)


def age_for(data: dict, today: date) -> int | None:
    """Return the user's age today, or None when no birth date is saved."""
    return profile.age_of(data["profile"], today)


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
    age = age_for(data, today)
    days = cycle.days_until(prediction.next_start, today)
    since_last = (today - prediction.last_start).days
    if since_last >= cycle.NO_PERIOD_ALERT_DAYS:
        found.append(_insight(
            "warning", "drop", f"No period logged for {since_last} days",
            "If you have had one, log it so predictions stay useful. If you truly have "
            "not and are not pregnant, 3 months without a period is worth raising with a doctor.",
            "cycle",
        ))  # fmt: skip
    elif days < 0:
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
        ovulation = f"{prediction.ovulation:%b} {prediction.ovulation.day}"
        known = prediction.basis != "calendar"
        when = f"around {ovulation}" + (
            f" (from your {prediction.basis})" if known else ""
        )
        if profile.has_focus(data["profile"], "conceive"):
            text = f"Your best days to conceive are the 2 days before ovulation and the day itself; it is {when}."
        elif profile.has_focus(data["profile"], "avoid"):
            text = "Predicted fertile days are estimates and are not birth control."
        else:
            text = f"Estimated fertile window; ovulation is {when}."
        found.append(_insight("info", "sparkle", "Fertile window", text, "cycle"))

    mucus = daylog.peek_day(data, today).get("mucus")
    if mucus in FERTILE_MUCUS and not cycle.is_stale(prediction, today):
        found.append(_insight(
            "info", "sparkle", "A fertile sign today",
            f"{mucus.capitalize()} mucus usually appears in the days just before ovulation.",
            "cycle",
        ))  # fmt: skip

    shift = current_shift(data, today)
    if shift is not None:
        found.append(_insight(
            "good", "thermometer", "Ovulation confirmed",
            f"Your temperature rose on {shift.first_high:%b} {shift.first_high.day}, so ovulation most likely "
            f"happened around {shift.ovulation:%b} {shift.ovulation.day}.", "bbt",
        ))  # fmt: skip

    recent = cycle.usable_lengths(cycle.period_starts(data["periods"]))[
        -cycle.CYCLES_TO_AVERAGE :
    ]
    unusual = cycle.lengths_outside_typical_range(recent, age)
    low, high = cycle.typical_range(age)
    if len(unusual) >= 2:
        found.append(_insight(
            "warning", "drop", "Cycles outside the typical range",
            f"{len(unusual)} of your last {len(recent)} cycles were outside {low}-{high} days. "
            "If this continues, consider talking to a doctor.", "cycle",
        ))  # fmt: skip
    elif len(recent) >= 3:
        spread = max(recent) - min(recent)
        allowed = cycle.allowed_variation(age)
        if spread > allowed:
            found.append(_insight(
                "info", "drop", f"Your cycles vary by {spread} days",
                f"Up to {allowed} days counts as regular at your age, so predictions will be "
                "less exact. If this is new for you, mention it to a doctor.", "cycle",
            ))  # fmt: skip

    last_periods = sorted(data["periods"], key=lambda p: p["start"])[-3:]
    long_ones = cycle.prolonged_periods(last_periods)
    if len(long_ones) >= 2:
        found.append(_insight(
            "warning", "drop", "Your periods have been long",
            f"{len(long_ones)} of your last {len(last_periods)} lasted over 8 days. "
            "Periods that long are worth mentioning to a doctor.", "cycle",
        ))  # fmt: skip
    return found


def habit_insights(data: dict, now: datetime) -> list[dict]:
    """Return notes about sleep, water, activity, caffeine and logging streaks."""
    today = now.date()
    log = daylog.peek_day(data, today)
    goals = data["goals"]
    found = []

    age = age_for(data, today)
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
    weekly_goal = activity.weekly_goal_minutes(age)
    if weekly >= weekly_goal:
        found.append(_insight(
            "good", "activity", f"{weekly_goal} active minutes reached",
            f"{weekly} active minutes in the last 7 days meets the WHO recommendation.", "activity",
        ))  # fmt: skip
    elif weekly >= weekly_goal * 2 / 3:
        found.append(_insight(
            "info", "activity", f"{weekly_goal - weekly} active minutes to go",
            f"{weekly} of the {weekly_goal} minutes WHO recommends each week.", "activity",
        ))  # fmt: skip

    conceiving = profile.has_focus(data["profile"], "conceive")
    if log.get("caffeine_mg", 0) > nutrition.caffeine_limit(age, conceiving):
        found.append(
            _insight(
                "warning",
                "cup",
                "A lot of caffeine today",
                nutrition.caffeine_note(log["caffeine_mg"], conceiving, age)[0],
                "nutrition",
            )
        )

    pressure = vitals.bp_average(data["days"], today)
    if pressure is not None and pressure[2] >= vitals.READINGS_FOR_AVERAGE:
        systolic, diastolic, count = pressure
        category, tone = vitals.bp_category(systolic, diastolic)
        if tone == vitals.WARNING:
            found.append(_insight(
                "warning", "heart", f"Blood pressure averaging {systolic}/{diastolic}",
                f"That is in the {category} range across {count} readings. An average "
                "like this is worth showing to a health professional.", "vitals",
            ))  # fmt: skip

    streak = daylog.logging_streak(data, today)
    if streak >= 3:
        found.append(_insight(
            "good", "flame", f"{streak}-day streak",
            "You have logged something every day. Small daily check-ins add up.", None,
        ))  # fmt: skip
    return found


def body_insights(data: dict, today: date) -> list[dict]:
    """Return notes about weight: a fast change is worth a conversation."""
    start = today - timedelta(days=FAST_WEIGHT_WINDOW_DAYS)
    recent = sorted(
        (e for e in data["weights"] if start <= e["date"] <= today),
        key=lambda e: e["date"],
    )
    if len(recent) < 2 or (recent[-1]["date"] - recent[0]["date"]).days < 7:
        return []
    first, last = recent[0]["weight_kg"], recent[-1]["weight_kg"]
    change = abs(last - first) / first
    if change < FAST_WEIGHT_CHANGE:
        return []
    direction = "down" if last < first else "up"
    return [_insight(
        "warning", "scale", f"Weight {direction} {change:.0%} in a month",
        "That is a fast change. If you did not plan it, it is worth mentioning to a "
        "health professional.", "bmi",
    )]  # fmt: skip


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
        if len(luteal) >= MIN_PATTERN_DAYS and len(other) >= MIN_PATTERN_DAYS:
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
        enough = vitals.recommended_sleep(age_for(data, today))
        split = journal.split_average(pairs, enough)
        if split is not None and split[0] - split[1] >= 0.5:
            found.append(_insight(
                "good", "moon", "Sleep lifts your mood",
                f"After {enough:g}+ hours of sleep your mood averages {split[0]:.1f}, and "
                f"{split[1]:.1f} after shorter nights.", "vitals",
            ))  # fmt: skip
    return found


def build_insights(data: dict, now: datetime, limit: int = 6) -> list[dict]:
    """Return the most useful insights for now, alerts first."""
    today = now.date()
    found = alert_insights(data, today)
    found += cycle_insights(data, today)
    found += body_insights(data, today)
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
        "label": f"Move {goals['active_min']} min or {goals['steps']:,} steps",
        "done": moved,
        "page": "activity",
    })  # fmt: skip
    return items
