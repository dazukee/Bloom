"""Vital signs and sleep: categories and gentle notes.

Pure logic: no customtkinter, no file access. Notes are general information,
not a diagnosis.

Blood pressure categories (ACC/AHA, as listed by the CDC):
    Normal     systolic below 120 and diastolic below 80
    Elevated   systolic 120-129 and diastolic below 80
    Stage 1    systolic 130-139 or diastolic 80-89
    Stage 2    systolic 140 or higher or diastolic 90 or higher
    Severe     systolic above 180 or diastolic above 120
Sleep: the CDC recommends 7 or more hours a night for adults aged 18-60.
"""

from datetime import date, timedelta

GOOD = "good"
WARNING = "warning"
DANGER = "danger"
INFO = "info"

MIN_SLEEP_HOURS = 7.0

LIMITS = {
    "rhr": (30, 220, "bpm"),
    "bp_sys": (60, 260, "mm Hg"),
    "bp_dia": (30, 160, "mm Hg"),
    "spo2": (70, 100, "%"),
    "sleep_h": (0, 16, "h"),
}


def bp_category(systolic: int, diastolic: int) -> tuple[str, str]:
    """Return (category, tone) for a blood pressure reading.

    Checks from the highest category down, so either number can raise it.
    """
    if systolic > 180 or diastolic > 120:
        return "Severe hypertension", DANGER
    if systolic >= 140 or diastolic >= 90:
        return "Stage 2 hypertension", WARNING
    if systolic >= 130 or diastolic >= 80:
        return "Stage 1 hypertension", WARNING
    if systolic >= 120:
        return "Elevated", INFO
    return "Normal", GOOD


SEVERE_BP_ADVICE = (
    "Above 180/120 mm Hg. Rest and measure again; if it stays this high, contact "
    "a health professional now. With chest pain, shortness of breath, weakness "
    "or trouble speaking, call emergency services."
)


def rhr_note(bpm: int) -> tuple[str, str]:
    """Return (note, tone) for a resting heart rate."""
    if bpm < 60:
        return "Below 60 bpm: common in fit people; mention it if you feel dizzy", INFO
    if bpm <= 100:
        return "Within the typical adult range of 60-100 bpm", GOOD
    return "Above 100 bpm at rest: re-measure after sitting quietly", WARNING


def spo2_note(percent: int) -> tuple[str, str]:
    """Return (note, tone) for a blood oxygen reading."""
    if percent >= 95:
        return "Typical (95-100%)", GOOD
    if percent >= 92:
        return "Lower than typical: re-measure with warm, still hands", WARNING
    return "Low: contact a health professional, especially if breathless", DANGER


def sleep_note(hours: float, goal: float) -> tuple[str, str]:
    """Return (note, tone) for one night's sleep."""
    if hours >= goal:
        return "You met your sleep goal", GOOD
    if hours >= MIN_SLEEP_HOURS:
        return "7+ hours, as the CDC recommends, but under your goal", INFO
    return "Under the 7 hours the CDC recommends for adults", WARNING


def sleep_debt(days: dict, goal: float, end: date, count: int = 7) -> float:
    """Return the hours short of `goal` over the last `count` logged nights."""
    debt = 0.0
    for offset in range(count):
        log = days.get(end - timedelta(days=offset), {})
        if "sleep_h" in log:
            debt += max(0.0, goal - log["sleep_h"])
    return round(debt, 1)


def average_of(days: dict, key: str, end: date, count: int = 7) -> float | None:
    """Return the average of `key` over the last `count` days that have it."""
    values = []
    for offset in range(count):
        log = days.get(end - timedelta(days=offset), {})
        if key in log:
            values.append(log[key])
    if not values:
        return None
    return sum(values) / len(values)
