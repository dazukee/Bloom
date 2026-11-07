"""Vital signs and sleep: categories and gentle notes.

Pure logic: no customtkinter, no file access. Notes are general information,
not a diagnosis.

Blood pressure categories (ACC/AHA, as listed by the CDC):
    Normal     systolic below 120 and diastolic below 80
    Elevated   systolic 120-129 and diastolic below 80
    Stage 1    systolic 130-139 or diastolic 80-89
    Stage 2    systolic 140 or higher or diastolic 90 or higher
    Severe     systolic above 180 or diastolic above 120
    Low        systolic below 90 or diastolic below 60 (American Heart Association)
The adult numbers apply from age 13 (AAP 2017). One reading is a snapshot:
diagnosis rests on the average of several, so bp_average() is shown as well.
Sleep: the CDC recommends 9-12 hours at 6-12 years, 8-10 at 13-17 and 7 or more
from 18. Oxygen follows NHS oximeter advice: 95+ fine, 93-94 ask for advice,
92 or less is urgent.
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
    if systolic < 90 or diastolic < 60:
        return "Low", INFO
    return "Normal", GOOD


SEVERE_BP_ADVICE = (
    "Above 180/120 mm Hg. Rest and measure again; if it stays this high, contact "
    "a health professional now. With chest pain, shortness of breath, weakness "
    "or trouble speaking, call emergency services."
)


LOW_BP_ADVICE = (
    "Often fine if you feel well. If you feel dizzy, faint or unusually tired, "
    "sit down, drink some water and mention it to a health professional."
)
ADULT_BP_FROM_AGE = 13
READINGS_FOR_AVERAGE = 3


def bp_average(days: dict, end: date, count: int = 14) -> tuple[int, int, int] | None:
    """Return (systolic, diastolic, readings) averaged over the last `count` days."""
    readings = []
    for offset in range(count):
        log = days.get(end - timedelta(days=offset), {})
        if "bp_sys" in log and "bp_dia" in log:
            readings.append((log["bp_sys"], log["bp_dia"]))
    if not readings:
        return None
    systolic = round(sum(r[0] for r in readings) / len(readings))
    diastolic = round(sum(r[1] for r in readings) / len(readings))
    return systolic, diastolic, len(readings)


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
    if percent >= 93:
        return "Lower than typical: re-measure with warm, still hands", WARNING
    return "Low: get medical advice now, urgently if you are breathless", DANGER


def recommended_sleep(age_years: int | None = None) -> float:
    """Return the fewest hours the CDC recommends a night at this age."""
    if age_years is not None and age_years < 13:
        return 9.0
    if age_years is not None and age_years < 18:
        return 8.0
    return MIN_SLEEP_HOURS


def sleep_note(
    hours: float, goal: float, age_years: int | None = None
) -> tuple[str, str]:
    """Return (note, tone) for one night's sleep."""
    enough = recommended_sleep(age_years)
    if hours >= goal:
        if hours >= enough:
            return "You met your sleep goal", GOOD
        return f"Goal met, but the CDC suggests {enough:g}+ hours at your age", INFO
    if hours >= enough:
        return f"{enough:g}+ hours, as the CDC recommends, but under your goal", INFO
    return f"Under the {enough:g} hours the CDC recommends at your age", WARNING


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
