"""Activity: steps, workouts with calories, and the weekly WHO goal."""

from datetime import timedelta
from typing import override

import customtkinter as ctk

from tracker import activity, daylog, insights, profile, validators
from tracker.ui import icons, theme, widgets
from tracker.ui.page import Page

QUICK_WORKOUTS = (
    ("Brisk walking", 30),
    ("Yoga", 20),
    ("Dancing", 20),
    ("Running", 20),
    ("Strength training", 20),
    ("Cycling", 30),
)


class ActivityPage(Page):
    """Steps and workouts for any day, and the last 7 days against WHO's 150 minutes."""

    title = "Activity"
    subtitle = "Every active minute counts. Vigorous minutes count double toward the weekly goal."
    banner = [
        {"kind": "dumbbell", "size": 104, "x": 0.66, "y": 0.5, "amp": 6, "hue": 0.87},
    ]
    banner_hue = 0.87

    @override
    def build(self) -> None:
        if not hasattr(self, "day"):
            self.day = self.today
        widgets.DateSwitcher(self.actions, self.day, self._change_day, self.today).grid(
            row=0, column=0
        )
        self.log = daylog.peek_day(self.data, self.day)
        self.weight = profile.current_weight(self.data)
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._steps_card(grid))
        grid.add(lambda: self._workout_card(grid), span=2, shrink=True)
        grid.add(lambda: self._week_card(grid), span=3)

    def _change_day(self, day) -> None:
        self.day = day
        self.refresh()

    # Steps -------------------------------------------------------------------------------

    def _steps_card(self, master) -> widgets.Card:
        goal = self.data["goals"]["steps"]
        steps = self.log.get("steps", 0)
        card = widgets.Card(master, "Steps", f"Goal {goal:,}", icon="steps")
        body = card.body
        ring = widgets.RingView(
            body,
            150,
            [(steps / goal, "activity", "surface_alt")],
            thickness=14,
            center=f"{steps:,}",
            caption=f"{min(steps / goal, 9.99):.0%} of goal",
        )
        ring.grid(row=0, column=0, pady=(0, 12))
        self.steps_field = widgets.Field(
            body,
            "Steps today" if self.day == self.today else "Steps",
            "e.g. 6500",
            value=str(steps or ""),
            on_enter=self._save_steps,
        )
        self.steps_field.grid(row=1, column=0, sticky="ew")
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        row.columnconfigure((0, 1), weight=1)
        widgets.button(row, "Save", self._save_steps, icon="check").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        widgets.button(
            row, "+1,000", lambda: self._add_steps(1000), kind="secondary"
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        return card

    def _save_steps(self) -> None:
        try:
            steps = validators.parse_number(
                self.steps_field.get(), "Steps", 0, 100_000, example="6500", whole=True
            )
        except ValueError as error:
            self.steps_field.show_error(str(error))
            return
        daylog.set_value(self.data, self.day, "steps", steps or None)
        self.save("Steps saved")
        self.refresh()

    def _add_steps(self, amount: int) -> None:
        daylog.add_amount(self.data, self.day, "steps", amount)
        self.save(f"+{amount:,} steps")
        self.refresh()

    # Workouts ------------------------------------------------------------------------------

    def _workout_card(self, master) -> widgets.Card:
        workouts = self.log.get("workouts", [])
        kcal = activity.day_kcal(workouts, self.weight)
        minutes = activity.active_minutes(workouts)
        card = widgets.Card(
            master,
            "Workouts",
            f"{minutes} active min  ·  about {kcal} kcal",
            icon="dumbbell",
        )
        body = card.body
        form = ctk.CTkFrame(body, fg_color="transparent")
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure(0, weight=2)
        form.columnconfigure(1, weight=1)
        widgets.label(form, "Type", "label").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.kind = widgets.option_menu(
            form, list(activity.WORKOUTS), "Brisk walking", width=96
        )
        self.kind.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.minutes = widgets.Field(form, "Minutes", "30", on_enter=self._add_workout)
        self.minutes.grid(row=0, column=1, rowspan=2, sticky="ew")
        # On its own row, so both boxes keep room even with extra-large text.
        widgets.button(form, "Add", self._add_workout, icon="plus", width=84).grid(
            row=2, column=1, sticky="e", pady=(10, 0)
        )
        if not workouts:
            widgets.label(
                body,
                "No workouts logged for this day. Tap one to add it:",
                "callout",
                "text_muted",
                wraplength=520,
            ).grid(row=1, column=0, sticky="w", pady=(16, 6))
            quick = widgets.ResponsiveGrid(
                body, min_column=170, max_columns=3, gap=6, nested=True
            )
            quick.grid(row=2, column=0, sticky="ew")
            for kind, length in QUICK_WORKOUTS:
                quick.add(
                    widgets.small_button(
                        quick,
                        f"{kind}, {length} min",
                        lambda k=kind, m=length: self._log_workout(k, m),
                    )
                )
        for row, workout in enumerate(workouts, start=1):
            level = activity.intensity(workout["met"])
            line = ctk.CTkFrame(
                body, fg_color=theme.pair("surface_alt"), corner_radius=12
            )
            line.grid(row=row, column=0, sticky="ew", pady=(10 if row == 1 else 4, 0))
            line.columnconfigure(1, weight=1)
            ctk.CTkLabel(
                line, text="", image=icons.icon("activity", 18, "activity")
            ).grid(row=0, column=0, padx=12, pady=10)
            widgets.label(
                line, f"{workout['type']}  ·  {workout['minutes']} min", "headline"
            ).grid(row=0, column=1, sticky="w")
            widgets.badge(
                line, level.title(), "good" if level == "vigorous" else "info"
            ).grid(row=0, column=2, padx=8)
            if level == "light":
                widgets.Tooltip(
                    line,
                    "Light activity is good for you, but WHO's minutes count moderate and vigorous activity.",
                )
            if self.weight:
                widgets.label(
                    line,
                    f"{activity.workout_kcal(workout['met'], self.weight, workout['minutes'])} kcal",
                    "callout",
                    "text_muted",
                ).grid(row=0, column=3, padx=8)
            widgets.icon_button(
                line,
                "trash",
                lambda i=row - 1: self._remove_workout(i),
                size=32,
                kind="ghost",
                tooltip="Delete",
            ).grid(row=0, column=4, padx=(0, 6))
        widgets.label(
            body,
            "Calories are estimates from typical MET values.",
            "footnote",
            "text_muted",
            wraplength=520,
        ).grid(row=len(workouts) + 3, column=0, sticky="w", pady=(10, 0))
        return card

    def _add_workout(self) -> None:
        try:
            minutes = validators.parse_number(
                self.minutes.get(), "Minutes", 1, 600, "min", "30", whole=True
            )
        except ValueError as error:
            self.minutes.show_error(str(error))
            return
        self._log_workout(self.kind.get(), minutes)

    def _log_workout(self, kind: str, minutes: int) -> None:
        log = daylog.get_day(self.data, self.day)
        log.setdefault("workouts", []).append(
            {"type": kind, "minutes": minutes, "met": activity.WORKOUTS[kind]}
        )
        self.save(f"{kind} added")
        self.refresh()

    def _remove_workout(self, index: int) -> None:
        workouts = list(daylog.peek_day(self.data, self.day).get("workouts", []))
        del workouts[index]
        daylog.set_value(self.data, self.day, "workouts", workouts)
        self.save("Workout deleted")
        self.refresh()

    # The week --------------------------------------------------------------------------------

    def _week_card(self, master) -> widgets.Card:
        weekly = activity.weekly_moderate_minutes(self.data["days"], self.day)
        age = insights.age_for(self.data, self.today)
        goal = activity.weekly_goal_minutes(age)
        advice = (
            "WHO recommends an average of 60 active minutes a day at your age"
            if goal != activity.WHO_WEEKLY_MINUTES
            else "WHO recommends at least 150 moderate minutes a week"
        )
        card = widgets.Card(master, "Last 7 days", advice, icon="calendar")
        body = card.body
        body.columnconfigure(1, weight=1)
        number = widgets.stat(
            body, f"{weekly}", f"of {goal} minutes", "number", "primary_text"
        )
        number.grid(row=0, column=0, sticky="w", padx=(0, 24))
        bar_box = ctk.CTkFrame(body, fg_color="transparent")
        bar_box.grid(row=0, column=1, sticky="ew")
        bar_box.columnconfigure(0, weight=1)
        widgets.progress_bar(bar_box, weekly / goal, "activity", 12).grid(
            row=0, column=0, sticky="ew"
        )
        message = (
            "Goal reached. Great work!"
            if weekly >= goal
            else f"{goal - weekly} minutes to go this week."
        )
        widgets.label(bar_box, message, "callout", "text_muted").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        strength = activity.strength_days(self.data["days"], self.day)
        widgets.label(
            bar_box,
            f"Muscle-strengthening days: {strength} of the {activity.WHO_STRENGTH_DAYS} a week WHO suggests.",
            "footnote",
            "text_muted",
            wraplength=520,
        ).grid(row=2, column=0, sticky="w", pady=(2, 0))
        days = [self.day - timedelta(days=offset) for offset in range(6, -1, -1)]
        values = [
            activity.moderate_minutes(daylog.peek_day(self.data, d).get("workouts", []))
            for d in days
        ]
        labels = [d.strftime("%a") for d in days]
        chart = widgets.BarChart(
            body,
            values,
            labels,
            max(60, max(values)),
            "activity",
            height=170,
            highlight=6,
        )
        chart.unit = " min"
        chart.full_labels = [f"{d:%a, %b} {d.day}" for d in days]
        chart.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        return card
