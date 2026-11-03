"""First-run setup: seven short steps after the first login.

Psychology used here: one topic per step (less to think about at once), a
progress indicator (people finish what they can see the end of), smart
defaults (water goal from body weight), inline validation, and a friendly
finish. Every answer can be changed later in Settings.
"""

from datetime import date

import customtkinter as ctk

from tracker import bmi, cycle, profile, units, validators
from tracker.ui import anim, icons, theme, widgets

STEPS = ("welcome", "about", "body", "cycle", "lifestyle", "focus", "done")
STEP_GOALS = ("5,000", "8,000", "10,000", "12,000")

HERO = [
    {"kind": "sphere", "size": 150, "x": 0.34, "y": 0.34, "amp": 10},
    {"kind": "torus", "size": 130, "x": 0.70, "y": 0.58, "amp": 8, "phase": 1.4},
    {"kind": "cube", "size": 84, "x": 0.26, "y": 0.68, "amp": 7, "phase": 2.6},
]


class Onboarding(ctk.CTkFrame):
    """The setup wizard; finish() saves the answers and opens the app."""

    def __init__(self, app) -> None:
        super().__init__(app, fg_color=theme.pair("bg"), corner_radius=0)
        self.app = app
        self.today = date.today()
        data = app.user_data
        p, goals, settings = data["profile"], data["goals"], data["settings"]
        self.answers = {
            "display_name": p["display_name"],
            "birth_date": p["birth_date"],
            "height_cm": p["height_cm"],
            "weight_kg": p["weight_kg"],
            "us_units": settings["weight_unit"] == "lb",
            "track_cycle": p["track_cycle"],
            "last_period": None,
            "cycle_length": p["cycle_length"],
            "period_length": p["period_length"],
            "activity_level": p["activity_level"],
            "focus": profile.focus_list(p),
            "sleep_h": goals["sleep_h"],
            "steps": goals["steps"],
            "water_ml": None,
        }
        self.index = 0
        self.step_frame = None
        self.validate = None

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=4)
        self.columnconfigure(1, weight=6)
        self.hero = widgets.Hero3D(self, HERO, height=600, texts=(
            ("Let's make Bloom yours", "title", "on_primary", 0.1, 0.84, "w"),
            ("A few questions, then you're in.", "body", "on_primary", 0.1, 0.9, "w"),
        ))  # fmt: skip
        self.hero.grid(row=0, column=0, sticky="nsew")
        side = ctk.CTkFrame(self, fg_color=theme.pair("bg"), corner_radius=0)
        side.grid(row=0, column=1, sticky="nsew")
        self.side = side
        side.rowconfigure(1, weight=1)
        side.columnconfigure(0, weight=1)

        top = ctk.CTkFrame(side, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 8))
        self.dots = []
        for i in range(len(STEPS)):
            dot = ctk.CTkFrame(top, width=10, height=8, corner_radius=4)
            dot.grid(row=0, column=i, padx=3)
            self.dots.append(dot)
        self.step_text = widgets.label(top, "", "footnote", "text_muted")
        self.step_text.grid(row=0, column=len(STEPS), padx=(12, 0))

        self.holder = ctk.CTkFrame(side, fg_color="transparent")
        self.holder.grid(row=1, column=0, sticky="nsew", padx=24)

        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=40, pady=(8, 28))
        bottom.columnconfigure(0, weight=1)
        self.back_button = widgets.button(
            bottom, "Back", self.back, kind="plain", width=110, icon="chevron_left"
        )
        self.back_button.grid(row=0, column=0, sticky="w")
        self.next_button = widgets.button(
            bottom, "Continue", self.next, width=180, height=theme.BIG_CONTROL_HEIGHT
        )
        self.next_button.grid(row=0, column=1, sticky="e")
        # Enter means Continue anywhere in the window (bound on the main window,
        # because CustomTkinter does not allow bind_all).
        self._enter_binding = app.bind("<Return>", self._enter, add="+")
        self.adapt(app.compact)
        self.show_step(0, 1)

    def adapt(self, compact: bool) -> None:
        """Hide the hero on narrow windows."""
        if compact:
            self.hero.grid_remove()
            self.side.grid(row=0, column=0, columnspan=2, sticky="nsew")
        else:
            self.hero.grid()
            self.side.grid(row=0, column=1, columnspan=1, sticky="nsew")

    def _enter(self, event) -> None:
        if self.winfo_exists() and not isinstance(event.widget, ctk.CTkTextbox):
            self.next()

    # Navigation ---------------------------------------------------------------

    def show_step(self, index: int, direction: int) -> None:
        """Build a step and slide it in from the right (forward) or left (back)."""
        self.index = index
        name = STEPS[index]
        frame = ctk.CTkScrollableFrame(
            self.holder,
            fg_color="transparent",
            scrollbar_button_color=theme.pair("border"),
        )
        frame.columnconfigure(0, weight=1)
        widgets.fast_scroll(frame)
        self.validate = getattr(self, f"_step_{name}")(frame)
        old = self.step_frame
        self.step_frame = frame
        frame.place(relx=0, rely=0, relwidth=1, relheight=1, x=60 * direction)
        if old is not None:
            old.destroy()
        anim.animate(
            frame,
            theme.PAGE_IN,
            lambda t: frame.place_configure(x=60 * direction * (1 - t)),
            key="onboarding-step",
        )
        for i, dot in enumerate(self.dots):
            current = i == index
            dot.configure(
                width=26 if current else 8,
                fg_color=theme.pair("primary" if i <= index else "border"),
            )
        self.step_text.configure(text=f"Step {index + 1} of {len(STEPS)}")
        self.back_button.grid() if index > 0 else self.back_button.grid_remove()
        labels = {0: "Get Started", len(STEPS) - 1: f"Start Using {theme.APP_NAME}"}
        self.next_button.configure(text=labels.get(index, "Continue"))

    def next(self) -> None:
        """Validate this step, then move on (or finish)."""
        if self.validate is not None and not self.validate():
            return
        if self.index == len(STEPS) - 1:
            self.finish()
        else:
            self.show_step(self.index + 1, 1)

    def back(self) -> None:
        """Go to the previous step."""
        if self.index > 0:
            self.show_step(self.index - 1, -1)

    # Helpers --------------------------------------------------------------------

    def _title(self, frame, title: str, text: str) -> None:
        widgets.label(frame, title, "title", "title").grid(
            row=0, column=0, sticky="w", padx=16, pady=(8, 4)
        )
        widgets.label(frame, text, "body", "text_muted", wraplength=520).grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 22)
        )

    def _place(self, widget, row: int, pady=(0, 16)) -> None:
        widget.grid(row=row, column=0, sticky="ew", padx=16, pady=pady)

    # Steps (each returns its validate function, or None) -------------------------

    def _step_welcome(self, frame):
        self._title(
            frame,
            f"Hi, welcome to {theme.APP_NAME}",
            "A few questions help personalise predictions, goals and tips. You can change everything later in Settings.",
        )
        features = (
            (
                "drop",
                "Cycle, ovulation and temperature",
                "Predictions that learn from your own history",
            ),
            (
                "heart",
                "Vitals, sleep, activity and food",
                "Simple daily logs with gentle goals",
            ),
            (
                "sparkle",
                "Smart insights",
                "Patterns between your sleep, mood, symptoms and cycle",
            ),
            ("lock", "Private", "Saved only on this computer, behind your password"),
        )
        for row, (icon_name, title, text) in enumerate(features, start=2):
            item = ctk.CTkFrame(frame, fg_color="transparent")
            self._place(item, row, (0, 12))
            ctk.CTkLabel(
                item,
                text="",
                image=icons.icon(icon_name, 20, "primary_text"),
                width=40,
                height=40,
                corner_radius=12,
                fg_color=theme.pair("primary_soft"),
            ).grid(row=0, column=0, rowspan=2, padx=(0, 14))
            widgets.label(item, title, "headline").grid(row=0, column=1, sticky="sw")
            widgets.label(item, text, "footnote", "text_muted").grid(
                row=1, column=1, sticky="nw"
            )
        return None

    def _step_about(self, frame):
        self._title(
            frame,
            "About you",
            "Your name is only used to greet you. Your age adjusts guidance such as BMI categories.",
        )
        name = widgets.Field(
            frame,
            "What should we call you?",
            "e.g. Maria",
            value=self.answers["display_name"],
        )
        self._place(name, 2)
        birth = self.answers["birth_date"]
        born = widgets.Field(
            frame,
            "Birth date",
            "YYYY-MM-DD",
            helper="For example 2005-08-21",
            value=birth.isoformat() if birth else "",
        )
        self._place(born, 3)
        age = widgets.label(frame, "", "callout", "primary_text")
        self._place(age, 4)

        def show_age(_event=None) -> None:
            try:
                value = validators.parse_birth_date(born.get(), self.today)
                age.configure(text=f"You are {bmi.calculate_age(value, self.today)}.")
            except ValueError:
                age.configure(text="")

        born.entry.bind("<KeyRelease>", show_age, add="+")
        show_age()
        self.after(150, name.focus)

        def validate() -> bool:
            ok = True
            try:
                self.answers["display_name"] = validators.parse_display_name(name.get())
                name.clear_error()
            except ValueError as error:
                name.show_error(str(error))
                ok = False
            try:
                self.answers["birth_date"] = validators.parse_birth_date(
                    born.get(), self.today
                )
                born.clear_error()
            except ValueError as error:
                born.show_error(str(error))
                ok = False
            return ok

        return validate

    def _step_body(self, frame):
        self._title(
            frame,
            "Your body",
            "Height and weight give your BMI and a daily calorie estimate.",
        )
        us = self.answers["us_units"]
        unit_switch = widgets.segmented(
            frame,
            ["Metric (kg, cm, °C)", "US (lb, ft, °F)"],
            "US (lb, ft, °F)" if us else "Metric (kg, cm, °C)",
            command=lambda v: self._switch_units(v.startswith("US")),
        )
        self._place(unit_switch, 2, (0, 20))
        height = self.answers["height_cm"]
        weight = self.answers["weight_kg"]
        if us:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            self._place(row, 3)
            row.columnconfigure((0, 1), weight=1)
            feet, inches = units.cm_to_ft_in(height) if height else ("", "")
            feet_field = widgets.Field(row, "Height (feet)", "5", value=str(feet))
            feet_field.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            inch_field = widgets.Field(
                row, "Inches", "4", value=f"{inches:g}" if height else ""
            )
            inch_field.grid(row=0, column=1, sticky="ew", padx=(8, 0))
            weight_field = widgets.Field(
                frame,
                "Weight",
                "121",
                unit="lb",
                value=f"{units.kg_to_lb(weight):.1f}" if weight else "",
            )
        else:
            height_field = widgets.Field(
                frame, "Height", "160", unit="cm", value=f"{height:g}" if height else ""
            )
            self._place(height_field, 3)
            weight_field = widgets.Field(
                frame,
                "Weight",
                "55.5",
                unit="kg",
                value=f"{weight:g}" if weight else "",
            )
        self._place(weight_field, 4)
        preview = ctk.CTkFrame(frame, fg_color="transparent", width=1, height=1)
        self._place(preview, 5)

        def read_height() -> float:
            if us:
                return validators.parse_feet_inches(feet_field.get(), inch_field.get())
            return validators.parse_height(height_field.get())

        def show_bmi(_event=None) -> None:
            for child in preview.winfo_children():
                child.destroy()
            try:
                value = bmi.calculate_bmi(
                    validators.parse_weight(weight_field.get(), "lb" if us else "kg"),
                    read_height(),
                )
            except ValueError:
                return
            widgets.label(preview, f"BMI {value}", "headline").grid(
                row=0, column=0, padx=(0, 10)
            )
            widgets.badge(
                preview,
                bmi.classify_bmi(value),
                "good" if bmi.classify_bmi(value) == bmi.HEALTHY_WEIGHT else "info",
            ).grid(row=0, column=1)

        fields = [weight_field] + ([feet_field, inch_field] if us else [height_field])
        for field in fields:
            field.entry.bind("<KeyRelease>", show_bmi, add="+")
        show_bmi()
        self._body_fields = (read_height, weight_field, fields)

        def validate() -> bool:
            ok = True
            try:
                self.answers["height_cm"] = read_height()
                for field in fields[1:]:
                    field.clear_error()
            except ValueError as error:
                fields[1].show_error(str(error))
                ok = False
            try:
                self.answers["weight_kg"] = round(
                    validators.parse_weight(weight_field.get(), "lb" if us else "kg"), 1
                )
                weight_field.clear_error()
            except ValueError as error:
                weight_field.show_error(str(error))
                ok = False
            return ok

        return validate

    def _switch_units(self, us: bool) -> None:
        read_height, weight_field, _ = self._body_fields
        try:
            self.answers["height_cm"] = read_height()
        except ValueError:
            pass
        try:
            self.answers["weight_kg"] = validators.parse_weight(
                weight_field.get(), "lb" if self.answers["us_units"] else "kg"
            )
        except ValueError:
            pass
        self.answers["us_units"] = us
        self.show_step(self.index, 0)

    def _step_cycle(self, frame):
        self._title(
            frame,
            "Your cycle",
            "Predictions start from what you know now and improve with every period you log.",
        )
        track = widgets.switch(
            frame,
            "Track my menstrual cycle",
            self.answers["track_cycle"],
            command=lambda: self._toggle_cycle(track.get()),
        )
        self._place(track, 2, (0, 18))
        if not self.answers["track_cycle"]:
            widgets.note(
                frame,
                "Cycle and temperature pages will be hidden. You can turn tracking on later in Settings.",
                "info",
            ).grid(row=3, column=0, sticky="ew", padx=16)
            return None
        last = self.answers["last_period"]
        start = widgets.Field(
            frame,
            "When did your last period start?",
            "YYYY-MM-DD",
            helper="Optional: leave blank if you don't remember.",
            value=last.isoformat() if last else "",
        )
        self._place(start, 3)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        self._place(row, 4)
        widgets.label(row, "Usual cycle length", "label").grid(
            row=0, column=0, sticky="w"
        )
        length = widgets.Stepper(
            row,
            self.answers["cycle_length"],
            1,
            profile.MIN_CYCLE_LENGTH,
            profile.MAX_CYCLE_LENGTH,
            unit="days",
        )
        length.grid(row=1, column=0, sticky="w", pady=(6, 16))
        widgets.label(row, "Period length", "label").grid(
            row=0, column=1, sticky="w", padx=(40, 0)
        )
        period = widgets.Stepper(
            row,
            self.answers["period_length"],
            1,
            profile.MIN_PERIOD_LENGTH,
            profile.MAX_PERIOD_LENGTH,
            unit="days",
        )
        period.grid(row=1, column=1, sticky="w", padx=(40, 0), pady=(6, 16))
        widgets.label(
            frame,
            "Not sure? 28 and 5 days are common starting points.",
            "footnote",
            "text_muted",
        ).grid(row=5, column=0, sticky="w", padx=16)

        def validate() -> bool:
            try:
                self.answers["last_period"] = validators.parse_optional_date(
                    start.get(), self.today
                )
                start.clear_error()
            except ValueError as error:
                start.show_error(str(error))
                return False
            self.answers["cycle_length"] = int(length.get())
            self.answers["period_length"] = int(period.get())
            return True

        return validate

    def _toggle_cycle(self, value: int) -> None:
        self.answers["track_cycle"] = bool(value)
        self.show_step(self.index, 0)

    def _step_lifestyle(self, frame):
        self._title(
            frame,
            "Your daily rhythm",
            "Goals you can reach keep you motivated, so start realistic. You can raise them anytime.",
        )
        options = {
            key: (label, text)
            for key, (label, text, _) in profile.ACTIVITY_LEVELS.items()
        }
        activity = widgets.OptionList(
            frame,
            options,
            self.answers["activity_level"],
            lambda key: self.answers.update(activity_level=key),
        )
        self._place(activity, 2)
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        self._place(grid, 3)
        widgets.label(grid, "Sleep goal", "label").grid(row=0, column=0, sticky="w")
        sleep = widgets.Stepper(
            grid, self.answers["sleep_h"], 0.5, 5, 11, fmt="{:g}", unit="h"
        )
        sleep.grid(row=1, column=0, sticky="w", pady=(6, 14))
        widgets.label(grid, "Water goal", "label").grid(
            row=0, column=1, sticky="w", padx=(40, 0)
        )
        water_default = self.answers["water_ml"] or profile.suggested_water_ml(
            self.answers["weight_kg"]
        )
        water = widgets.Stepper(
            grid,
            water_default,
            250,
            1000,
            4000,
            fmt="{:,.0f}",
            unit="ml",
            value_width=120,
        )
        water.grid(row=1, column=1, sticky="w", padx=(40, 0), pady=(6, 14))
        widgets.label(frame, "Daily steps goal", "label").grid(
            row=4, column=0, sticky="w", padx=16, pady=(0, 6)
        )
        current = f"{self.answers['steps']:,}"
        steps = widgets.segmented(
            frame, list(STEP_GOALS), current if current in STEP_GOALS else "8,000"
        )
        self._place(steps, 5)

        def validate() -> bool:
            self.answers["sleep_h"] = sleep.get()
            self.answers["water_ml"] = int(water.get())
            self.answers["steps"] = int(steps.get().replace(",", ""))
            return True

        return validate

    def _step_focus(self, frame):
        self._title(
            frame,
            "Why are you using Bloom?",
            "Tick everything that applies; tap again to untick. Bloom puts the most relevant insights first.",
        )
        note_holder = ctk.CTkFrame(frame, fg_color="transparent", width=1, height=1)

        def chosen(keys: list[str]) -> None:
            self.answers["focus"] = keys
            for child in note_holder.winfo_children():
                child.destroy()
            if "avoid" in keys:
                widgets.note(
                    note_holder,
                    "Fertile-window predictions are estimates and are not a form of birth control.",
                    "warning",
                ).grid(row=0, column=0, sticky="ew")

        options = widgets.OptionList(
            frame,
            profile.FOCUS_OPTIONS,
            self.answers["focus"],
            chosen,
            columns=2,
            toggle=profile.toggle_focus,
        )
        self._place(options, 2)
        note_holder.grid(row=3, column=0, sticky="ew", padx=16)
        note_holder.columnconfigure(0, weight=1)
        chosen(self.answers["focus"])
        return None

    def _step_done(self, frame):
        a = self.answers
        self._title(
            frame,
            f"You're all set, {a['display_name']}",
            "Here's your starting point. Logging a little each day makes Bloom smarter.",
        )
        value = bmi.calculate_bmi(a["weight_kg"], a["height_cm"])
        weight_unit = "lb" if a["us_units"] else "kg"
        rows = [
            ("gauge", "BMI", f"{value} ({bmi.classify_bmi(value)})"),
            ("activity", "Activity", profile.ACTIVITY_LEVELS[a["activity_level"]][0]),
            ("moon", "Sleep goal", f"{a['sleep_h']:g} hours"),
            ("cup", "Water goal", f"{a['water_ml']:,} ml"),
            ("steps", "Steps goal", f"{a['steps']:,} a day"),
            ("scale", "Weight", units.format_weight(a["weight_kg"], weight_unit)),
        ]
        if a["track_cycle"]:
            rows.insert(
                1,
                (
                    "drop",
                    "Cycle",
                    f"{a['cycle_length']}-day cycle, {a['period_length']}-day period",
                ),
            )
        card = widgets.Card(frame)
        self._place(card, 2)
        for row, (icon_name, title, text) in enumerate(rows):
            ctk.CTkLabel(
                card.body, text="", image=icons.icon(icon_name, 18, "primary_text")
            ).grid(row=row, column=0, padx=(0, 12), pady=6)
            widgets.label(card.body, title, "callout", "text_muted").grid(
                row=row, column=1, sticky="w"
            )
            widgets.label(card.body, text, "headline").grid(
                row=row, column=2, sticky="e", padx=(20, 0)
            )
        card.body.columnconfigure(1, weight=1)
        celebration = widgets.Hero3D(frame, [
            {"kind": "sphere", "size": 46, "x": 0.3, "y": 0.5, "amp": 6},
            {"kind": "torus", "size": 56, "x": 0.5, "y": 0.5, "amp": 7, "phase": 1.0},
            {"kind": "cube", "size": 40, "x": 0.7, "y": 0.5, "amp": 6, "phase": 2.0},
        ], height=110, gradient=False, bg="bg")  # fmt: skip
        self._place(celebration, 3)
        return None

    # Saving ---------------------------------------------------------------------

    def finish(self) -> None:
        """Save every answer and open the main app."""
        a = self.answers
        data = self.app.user_data
        p = data["profile"]
        p.update(
            display_name=a["display_name"],
            birth_date=a["birth_date"],
            height_cm=round(a["height_cm"], 1),
            weight_kg=a["weight_kg"],
            activity_level=a["activity_level"],
            track_cycle=a["track_cycle"],
            focus=a["focus"],
            cycle_length=a["cycle_length"],
            period_length=a["period_length"],
            onboarded=True,
        )
        data["goals"].update(
            steps=a["steps"], water_ml=a["water_ml"], sleep_h=a["sleep_h"]
        )
        us = a["us_units"]
        data["settings"].update(
            weight_unit="lb" if us else "kg",
            height_unit="ft" if us else "cm",
            temp_unit="f" if us else "c",
        )
        if not any(entry["date"] == self.today for entry in data["weights"]):
            data["weights"].append({"date": self.today, "weight_kg": a["weight_kg"]})
        if a["track_cycle"] and a["last_period"] is not None:
            try:
                data["periods"] = cycle.add_period(
                    data["periods"],
                    a["last_period"],
                    None,
                    self.today,
                    a["period_length"],
                )
            except ValueError:
                pass  # already logged
        self.app.save_user_data()
        self.app.enter_main("home")
        widgets.toast(self.app, f"Welcome to {theme.APP_NAME}, {a['display_name']}")

    def destroy(self) -> None:
        """Remove the window-wide Enter key binding with the wizard."""
        self.app.unbind("<Return>", self._enter_binding)
        super().destroy()
