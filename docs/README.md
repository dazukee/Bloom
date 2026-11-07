# Documentation

The technical document, its flowcharts, and how every calculation was checked. Each flowchart follows its function's code step by step, so the presentation can point from the chart to the code.

| File | What it shows | Where in the code |
| --- | --- | --- |
| `Bloom_Technical_Document.pdf` | Objectives, requirements, program structure, the 11 flowcharts, the test case table, the real-data test, accessibility, user guide, sources | |
| `CALCULATIONS.md` | The verdict on every calculation and the test on 1,665 real cycles | |
| `flowchart_program.png` | The whole program: login, setup, pages, saving | `tracker/ui/app.py` |
| `flowchart_login.png` | Logging in, with the 5-try lockout | `auth.check_login` |
| `flowchart_recovery.png` | Resetting a password with the recovery code | `auth.reset_password_with_code` |
| `flowchart_bmi.png` | BMI, its category and the healthy range | `bmi.calculate_bmi`, `classify_bmi`, `healthy_weight_range` |
| `flowchart_inputs.png` | Turning typed text into a checked number or date | `validators.parse_number`, `parse_date` |
| `flowchart_cycle.png` | Predicting the next period, its likely range and the fertile window | `cycle.predict_cycle` |
| `flowchart_calendar.png` | The month grid and each day's colour | `calendar_logic.month_grid`, `day_status` |
| `flowchart_bbt.png` | Confirming ovulation with the 3-over-6 rule | `bbt.detect_thermal_shift` |
| `flowchart_sign.png` | Counting the next period from a known ovulation | `insights.prediction_for`, `cycle.with_ovulation_sign` |
| `flowchart_growth.png` | What a BMI means under and over 20 | `growth.assess` |
| `flowchart_insights.png` | Choosing the insights for the Today page | `insights.build_insights` |
