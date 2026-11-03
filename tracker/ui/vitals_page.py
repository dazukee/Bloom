"""Vitals and sleep: heart rate, blood pressure, oxygen and last night's sleep."""

from typing import override

import customtkinter as ctk

from tracker import daylog, validators, vitals
from tracker.ui import widgets
from tracker.ui.page import Page

SLEEP_QUALITY = {1: "Poor", 2: "Fair", 3: "Okay", 4: "Good", 5: "Great"}


class VitalsPage(Page):
    """Log core vital signs and sleep, with plain-language categories."""

    title = "Vitals & Sleep"
    subtitle = "Measure while seated and rested. Categories are general guidance, not a diagnosis."

    @override
    def build(self) -> None:
        if not hasattr(self, "day"):
            self.day = self.today
        widgets.DateSwitcher(self.actions, self.day, self._change_day, self.today).grid(
            row=0, column=0
        )
        self.log = daylog.peek_day(self.data, self.day)
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._sleep_card(grid))
        grid.add(lambda: self._pressure_card(grid))
        grid.add(lambda: self._heart_card(grid))
        grid.add(lambda: self._sleep_chart(grid), span=2)
        grid.add(lambda: self._heart_chart(grid))

    def _change_day(self, day) -> None:
        self.day = day
        self.refresh()

    # Sleep ----------------------------------------------------------------------------

    def _sleep_card(self, master) -> widgets.Card:
        goal = self.data["goals"]["sleep_h"]
        card = widgets.Card(
            master, "Last night's sleep", f"Goal {goal:g} h", icon="moon"
        )
        body = card.body
        hours = self.log.get("sleep_h", goal)
        self.sleep = widgets.Stepper(
            body, hours, 0.5, 0, 16, fmt="{:g}", unit="h", role="number"
        )
        self.sleep.grid(row=0, column=0, pady=(0, 12))
        widgets.label(body, "Quality", "label").grid(
            row=1, column=0, sticky="w", pady=(0, 6)
        )
        self.quality = widgets.ScalePicker(
            body, SLEEP_QUALITY, self.log.get("sleep_quality")
        )
        self.quality.grid(row=2, column=0, sticky="ew")
        widgets.button(body, "Save Sleep", self._save_sleep, icon="check").grid(
            row=3, column=0, sticky="ew", pady=(14, 0)
        )
        if "sleep_h" in self.log:
            text, tone = vitals.sleep_note(self.log["sleep_h"], goal)
            widgets.badge(body, text, tone).grid(
                row=4, column=0, sticky="w", pady=(10, 0)
            )
        debt = vitals.sleep_debt(self.data["days"], goal, self.day)
        if debt:
            widgets.label(
                body, f"Sleep debt this week: {debt:g} h", "footnote", "text_muted"
            ).grid(row=5, column=0, sticky="w", pady=(6, 0))
        return card

    def _save_sleep(self) -> None:
        daylog.set_value(self.data, self.day, "sleep_h", self.sleep.get())
        daylog.set_value(self.data, self.day, "sleep_quality", self.quality.value)
        self.save("Sleep saved")
        self.refresh()

    # Blood pressure ---------------------------------------------------------------------

    def _pressure_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master, "Blood pressure", "mm Hg, top over bottom number", icon="heart"
        )
        body = card.body
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew")
        row.columnconfigure((0, 1), weight=1)
        self.systolic = widgets.Field(
            row, "Systolic (top)", "120", value=str(self.log.get("bp_sys", ""))
        )
        self.systolic.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.diastolic = widgets.Field(
            row,
            "Diastolic (bottom)",
            "80",
            value=str(self.log.get("bp_dia", "")),
            on_enter=self._save_pressure,
        )
        self.diastolic.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        widgets.button(
            body, "Save Blood Pressure", self._save_pressure, icon="check"
        ).grid(row=1, column=0, sticky="ew", pady=(14, 0))
        if "bp_sys" in self.log and "bp_dia" in self.log:
            category, tone = vitals.bp_category(self.log["bp_sys"], self.log["bp_dia"])
            widgets.badge(
                body, f"{self.log['bp_sys']}/{self.log['bp_dia']}: {category}", tone
            ).grid(row=2, column=0, sticky="w", pady=(10, 0))
            if tone == vitals.DANGER:
                widgets.note(body, vitals.SEVERE_BP_ADVICE, "danger", 250).grid(
                    row=3, column=0, sticky="ew", pady=(10, 0)
                )
        return card

    def _save_pressure(self) -> None:
        low, high, unit = vitals.LIMITS["bp_sys"]
        try:
            systolic = validators.parse_number(
                self.systolic.get(), "Systolic", low, high, unit, "120", whole=True
            )
            self.systolic.clear_error()
        except ValueError as error:
            self.systolic.show_error(str(error))
            return
        low, high, unit = vitals.LIMITS["bp_dia"]
        try:
            diastolic = validators.parse_number(
                self.diastolic.get(), "Diastolic", low, high, unit, "80", whole=True
            )
        except ValueError as error:
            self.diastolic.show_error(str(error))
            return
        if diastolic >= systolic:
            self.diastolic.show_error(
                "The bottom number must be lower than the top number."
            )
            return
        daylog.set_value(self.data, self.day, "bp_sys", systolic)
        daylog.set_value(self.data, self.day, "bp_dia", diastolic)
        category, tone = vitals.bp_category(systolic, diastolic)
        self.save(
            f"Saved: {category}",
            "warning" if tone in (vitals.WARNING, vitals.DANGER) else "good",
        )
        self.refresh()

    # Heart rate and oxygen -----------------------------------------------------------------

    def _heart_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master,
            "Heart rate & oxygen",
            "Resting, after 5 quiet minutes",
            icon="activity",
        )
        body = card.body
        self.rhr = widgets.Field(
            body,
            "Resting heart rate",
            "72",
            unit="bpm",
            value=str(self.log.get("rhr", "")),
        )
        self.rhr.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.spo2 = widgets.Field(
            body,
            "Blood oxygen (SpO2)",
            "98",
            unit="%",
            value=str(self.log.get("spo2", "")),
            on_enter=self._save_heart,
        )
        self.spo2.grid(row=1, column=0, sticky="ew")
        widgets.button(body, "Save", self._save_heart, icon="check").grid(
            row=2, column=0, sticky="ew", pady=(14, 0)
        )
        badges = ctk.CTkFrame(body, fg_color="transparent", width=1, height=1)
        badges.grid(row=3, column=0, sticky="w", pady=(10, 0))
        if "rhr" in self.log:
            text, tone = vitals.rhr_note(self.log["rhr"])
            widgets.label(badges, text, "footnote", "text_muted", wraplength=250).grid(
                row=0, column=0, sticky="w"
            )
        if "spo2" in self.log:
            text, tone = vitals.spo2_note(self.log["spo2"])
            widgets.badge(badges, f"SpO2 {self.log['spo2']}%: {text}", tone).grid(
                row=1, column=0, sticky="w", pady=(6, 0)
            )
        return card

    def _save_heart(self) -> None:
        values = {}
        for field, key, label, example in (
            (self.rhr, "rhr", "Heart rate", "72"),
            (self.spo2, "spo2", "Blood oxygen", "98"),
        ):
            if not field.get().strip():
                field.clear_error()
                values[key] = None
                continue
            low, high, unit = vitals.LIMITS[key]
            try:
                values[key] = validators.parse_number(
                    field.get(), label, low, high, unit, example, whole=True
                )
                field.clear_error()
            except ValueError as error:
                field.show_error(str(error))
                return
        for key, value in values.items():
            daylog.set_value(self.data, self.day, key, value)
        self.save("Saved")
        self.refresh()

    # Trends -------------------------------------------------------------------------------

    def _sleep_chart(self, master) -> widgets.Card:
        goal = self.data["goals"]["sleep_h"]
        days = daylog.last_n_days(self.day, 14)
        values = [daylog.peek_day(self.data, d).get("sleep_h", 0) for d in days]
        logged = [v for v in values if v]
        average = (
            f"Average {sum(logged) / len(logged):.1f} h"
            if logged
            else "No nights logged yet"
        )
        card = widgets.Card(
            master,
            "Sleep, last 14 nights",
            f"{average}  ·  line = your {goal:g} h goal",
            icon="moon",
        )
        labels = [d.strftime("%a")[0] for d in days]
        widgets.BarChart(
            card.body,
            values,
            labels,
            max(10, max(values, default=0)),
            "sleep",
            height=190,
            goal=goal,
            highlight=len(days) - 1,
            fmt="{:g}",
        ).grid(row=0, column=0, sticky="ew")
        return card

    def _heart_chart(self, master) -> widgets.Card:
        days = daylog.last_n_days(self.day, 14)
        values = [daylog.peek_day(self.data, d).get("rhr") for d in days]
        card = widgets.Card(
            master, "Resting heart rate", "Last 14 days, bpm", icon="heart"
        )
        present = [v for v in values if v]
        if len(present) < 2:
            widgets.label(
                card.body,
                "Log your resting heart rate on two days to see the trend.",
                "callout",
                "text_muted",
                wraplength=260,
            ).grid(row=0, column=0, sticky="w")
            return card
        labels = [d.strftime("%a")[0] for d in days]
        widgets.LineChart(
            card.body,
            values,
            labels,
            min(present) - 5,
            max(present) + 5,
            "activity",
            height=190,
            fmt="{:.0f}",
        ).grid(row=0, column=0, sticky="ew")
        return card
