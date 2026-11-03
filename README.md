# Bloom: BMI & Female Health Tracker

A desktop app for women's health: BMI and weight, periods and ovulation, basal body temperature, moods and symptoms, vital signs and sleep, activity, and nutrition. Each person has a private, password-protected account, and the app gives personal insights from their own logs. Built entirely in Python with CustomTkinter for COMPE 02: Programming Logic and Design.

> Bloom gives general wellness information and estimates. It is not a medical device, does not diagnose, and its fertile-window predictions are not birth control.

## Features

| Page | What you can do |
| --- | --- |
| **Log in / Sign up** | Several accounts per computer. Passwords are hashed (PBKDF2, 600,000 rounds), 5 wrong tries lock the account for 30 seconds, and a one-time recovery code resets a forgotten password. |
| **First-run setup** | Seven short steps after the first login: name, birth date, height and weight (metric or US), cycle, activity level and goals, and your reasons for using the app (tick any; tap again to untick). Everything can be changed later in Settings. |
| **Today** | A purple 3D banner with your greeting and cycle day, your cycle ring and phase, today's goals as rings, one-click quick logging, smart insights, a daily checklist with a streak, and your last 7 days. |
| **Cycle** | A calendar coloured by period, predicted period, fertile window and ovulation. Log a period's start and end, flow, cervical mucus and LH tests. Predictions learn from your last 6 cycles, with a confidence level, a hormone chart and your cycle history. |
| **Temperature (BBT)** | Log your morning temperature. The chart draws the coverline and confirms ovulation with the 3-over-6 rule; fever readings are left out. |
| **Journal** | Mood (faces), energy, stress, 14 symptoms and a note for any day; your symptom patterns by cycle phase and a 14-day mood trend. |
| **Vitals & Sleep** | Sleep hours and quality (with sleep debt), blood pressure with its ACC/AHA category, resting heart rate and blood oxygen, with 14-day charts. |
| **Activity** | Steps, workouts with MET-based calories, and the WHO goal of 150 active minutes a week (vigorous minutes count double). |
| **Nutrition** | Water with an animated glass, meals and calories against a Mifflin-St Jeor estimate, caffeine (FDA 400 mg), alcohol, and fruit and vegetables (WHO 5 a day). |
| **BMI** | Log weight, see BMI on a gauge with CDC or Asia-Pacific categories, your healthy weight range, and your weight history. |
| **Settings** | Profile, reasons, cycle settings, goals, appearance (light, dark or system), units, reduce motion, CSV export, change password, new recovery code, log out, delete account, and the sources. |

The window adapts to the screen: it opens at about 84% of the screen, cards reflow between 1, 2 and 3 columns, and below 1020 px the sidebar becomes an icon rail.

## Set up (once)

Python 3.14 on Windows (it reports Tk 8.6). On a Mac where the check below prints Tk 9.x, use Python 3.13.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -c "import sys, tkinter; print(sys.version, tkinter.TkVersion)"
```

On macOS, activate with `source .venv/bin/activate`.

## Everyday commands

| Command | What it does |
| --- | --- |
| `python main.py` | Start the app (your data is saved in `data/`) |
| `python -m tracker.ui.preview` | Open the app with a made-up demo account, already logged in; nothing touches `data/` |
| `python -m tracker.ui.preview cycle` | The same, opened on one page (`home`, `cycle`, `bbt`, `journal`, `vitals`, `activity`, `nutrition`, `bmi`, `settings`, or `login`) |
| `pytest` | Run the 161 tests |
| `ruff format .` then `ruff check .` | Format the code, then check style, naming and docstrings |

The demo account is `demo` with the password `bloom2026`. Keyboard: Ctrl+1 to Ctrl+9 open the sidebar pages, Enter submits a form, Esc closes a dialog.

## How the code is organised

```
main.py                 starts the app
tracker/                the logic: plain Python, no screens
    auth.py, storage.py, profile.py, units.py, validators.py,
    bmi.py, cycle.py, calendar_logic.py, bbt.py, daylog.py, journal.py,
    vitals.py, activity.py, nutrition.py, insights.py, demo.py
tracker/ui/             the screens and the drawing code
    app.py              the window, sidebar, page switching
    theme.py            colours, fonts, spacing, motion timings
    widgets.py          every reusable piece: cards, buttons, charts, dialogs
    anim.py             easing and animation timers
    icons.py, graphics.py, render3d.py   icons, charts and 3D drawn with Pillow and numpy
    page.py             the base class of every page
    *_page.py, auth_pages.py, onboarding.py   one file per screen
    preview.py          the demo launcher
tests/                  pytest tests, one file per area
data/                   your accounts and logs (Git ignores this folder)
```

Three rules keep it tidy, and `tests/test_architecture.py` checks the first two automatically:

1. **Logic never imports the user interface.** Modules in `tracker/` do not import customtkinter, tkinter or Pillow, so every calculation can be tested and flowcharted on its own.
2. **Every public function has a docstring** that says what it returns.
3. **Only `storage.py` touches files.** Inside the program dates are `datetime.date` objects; in the JSON files they are ISO text like `"2026-10-31"`.

## Design notes

- **Look:** purple and white, inspired by Apple's apps: Segoe UI Variable (the Windows relative of SF Pro), an 8-point spacing grid, rounded cards, a deep-purple sidebar, and colour pairs for light and dark mode with text contrast of at least 4.5:1.
- **3D:** Tkinter cannot show 3D models, so `render3d.py` ray-marches glossy spheres, a torus and cubes into images with numpy, which then float gently on screen.
- **Motion:** pages slide up, numbers count up, rings and charts grow in, toasts spring up; "Reduce motion" turns all of it off.
- **Psychology and app-maker strategies:** one question per setup step with a progress bar (people finish what they can see the end of); smart defaults such as a water goal from body weight; logging in one or two taps; goal rings and a logging streak (visible progress and small wins); insights only when there is enough data; errors next to the field that caused them; and warnings, not alarms, for health readings.
- **Speed:** pages are built card by card so the window never freezes, and visited pages are kept until data changes.

## Testing

- `pytest` runs 161 unit tests of the logic (BMI, inputs, cycles, temperature, vitals, activity, nutrition, insights, accounts, files) and the architecture rules.
- The whole app was also driven end to end by a script: demo login, every page, logging actions, dark mode, a small window, logging out, then sign-up, recovery code and the full setup, with no errors.

## Sources

- [CDC: Adult BMI categories](https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html)
- WHO Western Pacific Region (2000): Asia-Pacific BMI cut-offs
- [Office on Women's Health: Your menstrual cycle](https://www.womenshealth.gov/menstrual-cycle/your-menstrual-cycle)
- [Office on Women's Health: Trying to conceive](https://www.womenshealth.gov/pregnancy/you-get-pregnant/trying-conceive) (calendar method)
- [NHS: Fertility in the menstrual cycle](https://www.nhs.uk/conditions/periods/fertility-in-the-menstrual-cycle/)
- CDC and ACC/AHA: blood pressure categories
- [CDC: How much sleep do I need?](https://www.cdc.gov/sleep/about/index.html)
- [WHO: Physical activity fact sheet](https://www.who.int/news-room/fact-sheets/detail/physical-activity)
- [FDA: How much caffeine is too much?](https://www.fda.gov/consumers/consumer-updates/spilling-beans-how-much-caffeine-too-much)
- Compendium of Physical Activities: MET values
- Mifflin-St Jeor equation (1990)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

## Team

| Member | Role |
| --- | --- |
| | Programming |
| | |
| | |
| | |
