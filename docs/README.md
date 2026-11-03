# Documentation

Flowcharts and the technical document go here. Each flowchart should follow the function's code step by step, so the presentation can point from the chart to the code.

| File | Algorithm | Where in the code |
| --- | --- | --- |
| `flowchart_program.png` | The whole program: login, setup, pages, saving | `tracker/ui/app.py` |
| `flowchart_login.png` | Logging in, with the 5-try lockout | `auth.check_login` |
| `flowchart_recovery.png` | Resetting a password with the recovery code | `auth.reset_password_with_code` |
| `flowchart_bmi.png` | BMI, its category and the healthy range | `bmi.calculate_bmi`, `classify_bmi`, `healthy_weight_range` |
| `flowchart_inputs.png` | Turning typed text into a checked number or date | `validators.parse_number`, `parse_date` |
| `flowchart_cycle.png` | Predicting the next period and fertile window | `cycle.predict_cycle` |
| `flowchart_calendar.png` | The month grid and each day's colour | `calendar_logic.month_grid`, `day_status` |
| `flowchart_bbt.png` | Confirming ovulation with the 3-over-6 rule | `bbt.detect_thermal_shift` |
| `flowchart_insights.png` | Choosing the insights for the Today page | `insights.build_insights` |
| Technical document | Flowcharts, test case table, user guide, sources | |
