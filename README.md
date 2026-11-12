# Bloom: BMI & Female Health Tracker

A desktop app for women's health that calculates: BMI and weight, periods and ovulation, basal body temperature, moods and symptoms, vital signs and sleep, activity, and nutrition. Each person has their own respective private, password-protected account, and the app gives personal insights from their very own logs. It is built entirely in Python with CustomTkinter for out subject, COMPE02: Programming Logic and Design.

> Bloom gives general wellness information and estimates. It is NOT a medical device. It does not diagnose, and its fertile-window predictions are not birth control.

## Features

| Page | What you can do |
| --- | --- |
| **Log in / Sign up** | Several accounts per computer. Passwords are hashed (PBKDF2, 600,000 rounds), 5 wrong tries lock the account for 30 seconds, and a one-time recovery code resets a forgotten password. A password strength meter encourages longer passwords, and larger text and high contrast are available before you log in. |
| **First-run setup** | Seven short steps after the first login: name, birth date, height and weight (metric or US), cycle, activity level and goals, and your reasons for using the app. Everything can be changed later in Settings. |
| **Today** | A banner in your theme colour with today's flower and the sun by day or the moon at night, a cycle wheel showing every phase, the likely range of your next period, goals as rings, one-click quick logging, smart insights, a daily checklist with a streak, and your last 7 days. |
| **My Garden** | A flower with one petal per healthy habit, each in its own colour; the last 4 weeks as a garden on rolling hills, with butterflies when you keep a streak; 9 achievements with progress bars; and a guided 4-4-6 breathing exercise. |
| **Cycle** | A calendar coloured by period, predicted period, fertile window and ovulation. Log a period's start and end, flow, cervical mucus and LH tests. Predictions learn from your last 6 cycles and sharpen once your temperature or an LH test shows ovulation, with a date range, a confidence level, a hormone chart and your cycle history. |
| **Temperature (BBT)** | Log your morning temperature. The chart draws the coverline and confirms ovulation with the 3-over-6 rule. Fevers are left out automatically, and you can leave out any disturbed reading (a cold, alcohol, a late night). |
| **Journal** | Mood (faces), energy, stress, 14 symptoms and a note that saves itself for any day; your symptom patterns by cycle phase and a 14-day mood trend. |
| **Vitals & Sleep** | Sleep hours and quality (with sleep debt and the recommendation for your age), blood pressure with its category and your average, resting heart rate and blood oxygen, with 14-day charts. |
| **Activity** | Steps, workouts with MET-based calories, one-tap workouts, the WHO goal for your age (vigorous minutes count double) and muscle-strengthening days. |
| **Nutrition** | Water with an animated glass, one-tap common foods (Filipino favourites included), calories and protein against targets for your age, caffeine and alcohol notes for your age, fruit and vegetables, and your daily iron, calcium and folate needs. |
| **BMI** | Log weight and see BMI on a gauge. Adults use CDC or Asia-Pacific categories; under 20, BMI is compared with girls your age on the CDC growth charts. Shows your healthy weight range and weight history. |
| **Settings** | Profile, goals, appearance (light, dark or system; 6 colour themes used on every page, one that follows your cycle, and an optional colour per page; 10 fonts; page transitions, sparkles, card glow, confetti), accessibility (below), sound effects (3 packs, volume, categories), units, start page, CSV export, a printable doctor summary, change password, new recovery code, delete account, and the sources. |

### Accessibility

A whole Settings tab, with one-click setups for low vision, dyslexia, motion sensitivity, colour blindness and screen reading:

- **Seeing:** four text sizes, high contrast (at least 7:1, tested), bold text, larger click targets, and colour-blind safe palettes with letters on the calendar so colour is never the only cue.
- **Reading:** Atkinson Hyperlegible, Lexend and OpenDyslexic fonts.
- **Motion and focus:** reduce motion (also follows the Windows setting for new accounts), hide decorative art, and messages that stay longer.
- **Reading aloud:** F2 reads the page, and Bloom can read messages and each control the keyboard reaches. Tkinter windows cannot talk to screen readers, so Bloom uses the voice built into the computer.
- **Keyboard:** everything works without a mouse. Tab moves with a visible focus ring, Enter or Space uses a control, arrows move around the calendar, Ctrl+K finds anything, F1 lists every shortcut, F6 jumps between the sidebar and the page, F11 is full screen, and Ctrl+plus or minus changes the text size.

The window adapts to the screen: it opens at about 84% of the screen, cards reflow between 1, 2 and 3 columns, and on a narrow window or with large text the sidebar becomes an icon rail.

## Set-up (once)
Here's what you need to do to set it up:
Python 3.14 on Windows (it reports Tk 8.6). On a Mac where the check below prints Tk 9.x, use Python 3.13.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -c "import sys, tkinter; print(sys.version, tkinter.TkVersion)"
```

On macOS, activate with `source .venv/bin/activate`.

AFTER this, your app is ready.

## Everyday commands

| Command | What it does |
| --- | --- |
| `python main.py` | Start the app (your data is saved in `data/`) |
| `python -m tracker.ui.preview` | Open the app with a made-up demo account, already logged in; nothing touches `data/` |
| `python -m tracker.ui.preview cycle` | The same, opened on one page (`home`, `cycle`, `bbt`, `journal`, `vitals`, `activity`, `nutrition`, `bmi`, `settings`, or `login`) |
| `pytest` | Run the 763 tests |
| `ruff format .` then `ruff check .` | Format the code, then check style, naming and docstrings |

The demo account is `demo` with the password `bloom2026`. Press F1 in the app for every keyboard shortcut.

## How the code is organised

```
main.py                 starts the app
tracker/                the logic: plain Python, no screens
    auth.py, storage.py, profile.py, units.py, validators.py,
    bmi.py, growth.py, cycle.py, calendar_logic.py, bbt.py, daylog.py,
    journal.py, vitals.py, activity.py, nutrition.py, garden.py, sound.py,
    insights.py, report.py, demo.py
tracker/ui/             the screens and the drawing code
    app.py              the window, sidebar, page switching
    theme.py            colours, fonts, spacing, motion timings
    widgets.py          every reusable piece: cards, buttons, charts, dialogs
    anim.py, effects.py easing, timers, confetti, card glow, page transitions
    sfx.py, speech.py   sound effects and reading aloud
    palette.py          Quick Find (Ctrl+K) and the keyboard shortcuts list
    icons.py, graphics.py, render3d.py   icons, charts and 3D drawn with Pillow and numpy
    page.py             the base class of every page
    *_page.py, auth_pages.py, onboarding.py   one file per screen
    preview.py          the demo launcher
assets/                 the window icon and the bundled fonts (open licences)
docs/                   the technical document, flowcharts and how calculations were checked
tests/                  pytest tests, one file per area
data/                   your accounts and logs (Git ignores this folder)
```

Three rules keep it tidy, and `tests/test_architecture.py` checks the first two automatically:

1. **Logic never imports the user interface.** Modules in `tracker/` do not import customtkinter, tkinter or Pillow, so every calculation can be tested and flowcharted on its own.
2. **Every public function has a docstring** that says what it returns.
3. **Only `storage.py` touches files.** Inside the program dates are `datetime.date` objects; in the JSON files they are ISO text like `"2026-10-31"`.

## Design notes

- **Look:** a soft gradient banner in your theme colour on every page, rounded cards whose icons are coloured by health topic, a deep sidebar with today's flower beside your name, and colour pairs for light and dark mode. Contrast is tested automatically: at least 4.5:1 everywhere, 7:1 in high contrast.
- **Brand:** the flower is the logo, the window icon and the idea behind the app: small daily habits make something grow.
- **3D:** Tkinter cannot show 3D models, so `render3d.py` ray-marches a family of glossy objects (flower, heart, drop, moon, thermometer, apple, smiling face, dumbbell, gear) into images with numpy, which then float gently on screen.
- **Motion and sound:** pages slide, rings and charts grow in, toasts spring up, confetti marks a real achievement, and every sound effect is generated from math with no audio files. All of it can be turned off.
- **Psychology and app-maker strategies:** one question per setup step with a progress bar; smart defaults such as a water goal from body weight; logging in one or two taps; a flower, rings and a streak for visible progress and small wins; insights only when there is enough data; errors next to the field that caused them; and warnings, not alarms, for health readings.
- **Speed:** pages are built card by card so the window never freezes, and 3D art is prepared on a background thread. While you read, Bloom quietly prepares the other pages (and rebuilds ones a save made out of date), so they open in about a third of a second instead of three. Any click or key pauses this background work.

## Testing

- `pytest` runs 763 tests of the logic (BMI, percentiles, inputs, cycles, signs, temperature, vitals, activity, nutrition, insights, accounts, files), the contrast of every colour theme, and the architecture rules.
- The whole app was also driven end to end by a script: sign-up, recovery code, the full setup, every page, logging actions, every theme, font and accessibility setting, Quick Find, keyboard focus, logging out, an empty account and a years-old log, with no errors.
- Cycle predictions were checked against 1,665 real cycles; see [docs/CALCULATIONS.md](docs/CALCULATIONS.md) for how every calculation was judged.

## Sources

- [CDC: Adult BMI categories](https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html)
- [CDC: Growth charts data files](https://www.cdc.gov/growthcharts/cdc-data-files.htm) (BMI-for-age, under 20)
- WHO Western Pacific Region (2000): Asia-Pacific BMI cut-offs
- [Office on Women's Health: Your menstrual cycle](https://www.womenshealth.gov/menstrual-cycle/your-menstrual-cycle)
- [Office on Women's Health: Trying to conceive](https://www.womenshealth.gov/pregnancy/you-get-pregnant/trying-conceive) (calendar method)
- [NHS: Fertility in the menstrual cycle](https://www.nhs.uk/conditions/periods/fertility-in-the-menstrual-cycle/)
- [Munro et al. (2018), FIGO menstruation terms](https://www.pure.ed.ac.uk/ws/files/75445783/Munro_et_al_2018_International_Journal_of_Gynecology_26_Obstetrics.pdf)
- [ACOG Committee Opinion 651: Menstruation in girls and adolescents](https://pubmed.ncbi.nlm.nih.gov/26595586/)
- [Fehring, Marquette University: Menstrual cycle data](https://epublications.marquette.edu/data_nfp/7) (used only to test predictions)
- CDC and ACC/AHA: blood pressure categories; American Heart Association: low blood pressure
- [NHS England: Oximeter readings](https://www.england.nhs.uk/nhs-at-home/covid-oximetry-at-home/)
- [CDC: How much sleep do I need?](https://www.cdc.gov/sleep/about/index.html)
- [WHO: Physical activity fact sheet](https://www.who.int/news-room/fact-sheets/detail/physical-activity)
- [FDA: How much caffeine is too much?](https://www.fda.gov/consumers/consumer-updates/spilling-beans-how-much-caffeine-too-much); ACOG and the American Academy of Pediatrics
- [US Dietary Guidelines 2025-2030](https://www.brewersassociation.org/government-affairs-updates/2025-2030-dietary-guidelines-for-americans-published/) (alcohol)
- [NIH Office of Dietary Supplements: Iron](https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/) and the US Dietary Reference Intakes
- USDA FoodData Central: food calories and protein
- Compendium of Physical Activities: MET values
- Mifflin-St Jeor equation (1990); Institute of Medicine (2005): Estimated Energy Requirement
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- WCAG 2.2: contrast and keyboard access

## Team

- Justin Blaire M. Ojos
- Vena Lee B. Rebaula
- Lesther Lazarte
- Hayden Tamayo
