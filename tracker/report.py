"""A one-page health summary to print or show a doctor.

Pure logic: no customtkinter, no file access. It returns HTML text; storage.py
saves it and the screen opens it in the browser, where it can be printed.
"""

import html
from datetime import date, timedelta

from tracker import (
    activity,
    bmi,
    cycle,
    growth,
    insights,
    journal,
    profile,
    units,
    vitals,
)

STYLE = """
body { font-family: Georgia, 'Times New Roman', serif; color: #1c1a22; margin: 32px auto;
       max-width: 720px; line-height: 1.45; }
h1 { font-size: 24px; margin: 0; color: #4c1d95; }
h2 { font-size: 16px; margin: 22px 0 6px; border-bottom: 1px solid #c4b5fd; padding-bottom: 3px; }
p { margin: 4px 0; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 4px 8px 4px 0; border-bottom: 1px solid #eee; }
.muted { color: #5f5b70; font-size: 13px; }
@media print { body { margin: 0; } }
"""


def _row(label: str, value: str) -> str:
    return f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"


def _body_rows(data: dict, today: date) -> list[str]:
    p = data["profile"]
    settings = data["settings"]
    rows = []
    age = profile.age_of(p, today)
    if age is not None:
        rows.append(_row("Age", f"{age} years"))
    if p["height_cm"]:
        rows.append(
            _row("Height", units.format_height(p["height_cm"], settings["height_unit"]))
        )
    weight = profile.current_weight(data)
    if weight:
        rows.append(
            _row("Weight", units.format_weight(weight, settings["weight_unit"]))
        )
    if weight and p["height_cm"]:
        value = bmi.calculate_bmi(weight, p["height_cm"])
        months = (
            growth.age_in_months(p["birth_date"], today) if p["birth_date"] else None
        )
        result = growth.assess(value, p["height_cm"], months, settings["bmi_standard"])
        text = f"{value} ({result.category})"
        if result.percentile is not None:
            text += f", {result.percentile:.0f}th percentile for age"
        rows.append(_row("BMI", text))
    return rows


def _cycle_rows(data: dict, today: date) -> list[str]:
    periods = sorted(data["periods"], key=lambda period: period["start"])
    if not periods:
        return [_row("Periods logged", "None")]
    rows = [
        _row(
            "Last period started",
            f"{periods[-1]['start']:%B} {periods[-1]['start'].day}, {periods[-1]['start'].year}",
        ),
        _row("Periods logged", str(len(periods))),
    ]
    stats = cycle.cycle_stats(periods)
    if stats:
        rows.append(
            _row(
                "Cycle length",
                f"average {stats['average']} days, {stats['shortest']} to "
                f"{stats['longest']} days over {stats['count']} cycles",
            )
        )
    average = cycle.average_period_length(periods, 0)
    if average:
        rows.append(_row("Period length", f"average {average} days"))
    long_ones = cycle.prolonged_periods(periods[-cycle.CYCLES_TO_AVERAGE :])
    if long_ones:
        rows.append(_row("Periods over 8 days", f"{len(long_ones)} of the last 6"))
    prediction = insights.prediction_for(data)
    if prediction is not None and not cycle.is_stale(prediction, today):
        rows.append(
            _row(
                "Next period (estimate)",
                f"around {prediction.next_start:%B} {prediction.next_start.day}, {prediction.next_start.year}",
            )
        )
    return rows


def _vitals_rows(data: dict, today: date) -> list[str]:
    days = data["days"]
    rows = []
    pressure = vitals.bp_average(days, today, 30)
    if pressure:
        systolic, diastolic, count = pressure
        category, _ = vitals.bp_category(systolic, diastolic)
        rows.append(
            _row(
                "Blood pressure",
                f"average {systolic}/{diastolic} mm Hg from {count} readings ({category})",
            )
        )
    for label, key, fmt in (
        ("Resting heart rate", "rhr", "{:.0f} bpm"),
        ("Blood oxygen", "spo2", "{:.0f}%"),
        ("Sleep", "sleep_h", "{:.1f} hours a night"),
        ("Steps", "steps", "{:,.0f} a day"),
    ):
        average = vitals.average_of(days, key, today, 30)
        if average is not None:
            rows.append(_row(label, "average " + fmt.format(average)))
    weekly = activity.weekly_moderate_minutes(days, today)
    rows.append(_row("Active minutes", f"{weekly} in the last 7 days"))
    return rows


def _symptom_rows(data: dict, today: date) -> list[str]:
    start = today - timedelta(days=90)
    counts = journal.symptom_counts(data["days"], start, today)
    return [_row(symptom, f"{count} days") for symptom, count in counts[:8]]


def doctor_summary_html(data: dict, username: str, today: date) -> str:
    """Return a printable summary of the user's logs as a complete HTML page."""
    name = data["profile"]["display_name"] or username
    sections = [
        ("About", _body_rows(data, today)),
        ("Menstrual cycle", _cycle_rows(data, today)),
        ("Averages, last 30 days", _vitals_rows(data, today)),
        ("Symptoms logged, last 90 days", _symptom_rows(data, today)),
    ]
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>Health summary: {html.escape(name)}</title>",
        f"<style>{STYLE}</style></head><body>",
        f"<h1>Health summary: {html.escape(name)}</h1>",
        f"<p class='muted'>Made with Bloom on {today:%B} {today.day}, {today.year} from the user's own "
        "logs. Readings were taken at home and have not been checked by a clinician.</p>",
    ]
    for title, rows in sections:
        if rows:
            parts.append(f"<h2>{html.escape(title)}</h2><table>{''.join(rows)}</table>")
    parts.append(
        "<p class='muted' style='margin-top:20px'>Predictions are estimates, and "
        "this summary is not a diagnosis.</p></body></html>"
    )
    return "".join(parts)
