"""Symptom and mood journal: options and patterns across the cycle.

Pure logic: no customtkinter, no file access.
"""

import math
from datetime import date, timedelta

SYMPTOMS = (
    "Cramps",
    "Headache",
    "Bloating",
    "Breast tenderness",
    "Acne",
    "Fatigue",
    "Back pain",
    "Cravings",
    "Nausea",
    "Insomnia",
    "Anxiety",
    "Irritability",
    "Mood swings",
    "Dizziness",
)
MOOD_LABELS = {1: "Awful", 2: "Low", 3: "Okay", 4: "Good", 5: "Great"}
LEVEL_LABELS = {1: "Very low", 2: "Low", 3: "Medium", 4: "High", 5: "Very high"}


def symptom_counts(days: dict, start: date, end: date) -> list[tuple[str, int]]:
    """Return (symptom, days logged) from start to end, most frequent first."""
    counts: dict[str, int] = {}
    for day, log in days.items():
        if start <= day <= end:
            for symptom in log.get("symptoms", []):
                counts[symptom] = counts.get(symptom, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Return the Pearson correlation of two lists, or None if undefined."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    spread_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    spread_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if spread_x == 0 or spread_y == 0:
        return None
    return covariance / (spread_x * spread_y)


def sleep_mood_pairs(days: dict, end: date, count: int = 30) -> list[tuple[float, int]]:
    """Return (last night's sleep, today's mood) pairs from the last `count` days."""
    pairs = []
    for offset in range(count):
        log = days.get(end - timedelta(days=offset), {})
        if "sleep_h" in log and "mood" in log:
            pairs.append((log["sleep_h"], log["mood"]))
    return pairs


def split_average(
    pairs: list[tuple[float, int]], threshold: float
) -> tuple[float, float] | None:
    """Return average mood after nights at or above vs below a sleep threshold."""
    good = [mood for sleep, mood in pairs if sleep >= threshold]
    short = [mood for sleep, mood in pairs if sleep < threshold]
    if not good or not short:
        return None
    return sum(good) / len(good), sum(short) / len(short)
