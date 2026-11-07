"""Bloom: BMI & Female Health Tracker.

Logic modules (pure Python: no screens, and only storage.py touches files):
    auth.py            accounts, password hashing, login lockout, recovery codes
    storage.py         load and save the JSON files, export CSV
    profile.py         activity levels, reasons for using the app, calorie target
    units.py           kg/lb, cm/ft-in and °C/°F conversions
    validators.py      turn typed text into checked values (or a clear error)
    bmi.py             BMI, category, healthy weight range, age
    growth.py          BMI percentiles for girls under 20 (CDC growth charts)
    cycle.py           period history, predictions, phases, hormone curves
    calendar_logic.py  the month grid and each day's colour
    bbt.py             basal body temperature and the 3-over-6 rule
    daylog.py          one dictionary of logs per day
    journal.py         moods, symptoms and simple statistics
    vitals.py          blood pressure, heart rate, oxygen and sleep notes
    activity.py        workouts, MET calories and the WHO weekly goal
    nutrition.py       water, caffeine, alcohol and meals
    garden.py          the daily flower, the garden and achievements
    sound.py           sound effects made from math
    insights.py        the smart notes and daily checklist on the Today page
    report.py          the printable doctor summary
    demo.py            a realistic made-up account for demos and screenshots

The screens live in tracker/ui and call these modules.
"""
