"""Basal body temperature: log a reading and see the ovulation shift."""

from datetime import datetime, timedelta
from typing import override

import customtkinter as ctk

from tracker import bbt, cycle, daylog, insights, units, validators
from tracker.ui import theme, widgets
from tracker.ui.page import Page

TIPS = (
    "Measure right after waking, before you sit up, talk or drink.",
    "Use the same thermometer at about the same time every day.",
    "Aim for at least 3 hours of unbroken sleep first.",
    "A fever, alcohol, travel or a late night can raise a reading; add a note in the Journal.",
)


class BbtPage(Page):
    """Log temperature and confirm ovulation with the 3-over-6 rule."""

    title = "Temperature"
    subtitle = "Your resting temperature rises slightly after ovulation. Logging every morning confirms when it happened."
    banner = [
        {"kind": "thermometer", "size": 92, "x": 0.66, "y": 0.5, "amp": 5, "hue": 0.08, "accent": (239, 68, 68)},
    ]  # fmt: skip
    banner_hue = 0.03

    @override
    def build(self) -> None:
        if not hasattr(self, "day"):
            self.day = self.today
        widgets.DateSwitcher(self.actions, self.day, self._change_day, self.today).grid(
            row=0, column=0
        )
        self.unit = self.settings["temp_unit"]
        self.prediction = insights.prediction_for(self.data)
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._log_card(grid))
        grid.add(lambda: self._chart_card(grid), span=2, shrink=True)
        grid.add(lambda: self._status_card(grid))
        grid.add(lambda: self._tips_card(grid), span=2)

    def _change_day(self, day) -> None:
        self.day = day
        self.refresh()

    # Logging -----------------------------------------------------------------------

    def _last_reading(self) -> float:
        for offset in range(0, 30):
            log = daylog.peek_day(self.data, self.day - timedelta(days=offset))
            if "bbt_c" in log:
                return log["bbt_c"]
        return 36.4

    def _log_card(self, master) -> widgets.Card:
        log = daylog.peek_day(self.data, self.day)
        logged = "bbt_c" in log
        card = widgets.Card(
            master,
            "Log temperature",
            "Logged" if logged else "Use the − and + buttons; hold to move faster",
            icon="thermometer",
        )
        body = card.body
        start_c = log.get("bbt_c", self._last_reading())
        symbol = "°F" if self.unit == "f" else "°C"
        low, high = (93.2, 107.6) if self.unit == "f" else (34.0, 42.0)
        self.stepper = widgets.Stepper(
            body, round(units.temp_in_unit(start_c, self.unit), 2), units.temp_step(self.unit), low, high,
            fmt="{:.2f}", unit=symbol, role="number", value_width=150,
        )  # fmt: skip
        self.stepper.grid(row=0, column=0, pady=(4, 14))
        self.time_field = widgets.Field(
            body,
            "Time measured",
            "HH:MM",
            value=log.get("bbt_time", datetime.now().strftime("%H:%M")),
        )
        self.time_field.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        widgets.button(
            body,
            "Update Reading" if logged else "Save Reading",
            self._save,
            icon="check",
            height=theme.BIG_CONTROL_HEIGHT,
        ).grid(row=2, column=0, sticky="ew")
        if logged:
            widgets.button(
                body, "Delete Reading", self._delete, kind="plain", icon="trash"
            ).grid(row=3, column=0, sticky="ew", pady=(8, 0))
            disturbed = widgets.switch(
                body,
                "Leave this reading out",
                bool(log.get("bbt_skip")),
                command=lambda: self._set_skip(bool(disturbed.get())),
            )
            disturbed.grid(row=4, column=0, sticky="w", pady=(12, 0))
            widgets.label(
                body,
                "For a cold, alcohol, a late night or a poor sleep: a day like that can look like a rise.",
                "footnote",
                "text_muted",
                wraplength=250,
            ).grid(row=5, column=0, sticky="w", pady=(2, 0))
            if bbt.is_fever(log["bbt_c"]):
                widgets.note(
                    body,
                    "38.0 °C (100.4 °F) or higher is a fever, so this reading is left out of the ovulation chart.",
                    "warning",
                    260,
                ).grid(row=6, column=0, sticky="ew", pady=(10, 0))
            late = bbt.unusual_time_note(self.data["days"], self.day)
            if late:
                widgets.note(body, late, "info", 260).grid(
                    row=7, column=0, sticky="ew", pady=(10, 0)
                )
        return card

    def _set_skip(self, value: bool) -> None:
        daylog.set_value(self.data, self.day, "bbt_skip", True if value else None)
        self.save("Left out of your chart" if value else "Back in your chart")
        self.refresh()

    def _save(self) -> None:
        try:
            temp_c = validators.parse_temperature(str(self.stepper.get()), self.unit)
        except ValueError as error:  # the stepper's limits normally prevent this
            widgets.toast(self.app, str(error), "warning")
            return
        try:
            time_text = validators.parse_time(self.time_field.get())
        except ValueError as error:
            self.time_field.show_error(str(error))
            return
        daylog.set_value(self.data, self.day, "bbt_c", temp_c)
        daylog.set_value(self.data, self.day, "bbt_time", time_text)
        tone = "warning" if bbt.is_fever(temp_c) else "good"
        message = (
            "Fever-range reading saved"
            if tone == "warning"
            else f"{units.format_temp(temp_c, self.unit)} saved"
        )
        self.save(message, tone)
        self.refresh()

    def _delete(self) -> None:
        daylog.set_value(self.data, self.day, "bbt_c", None)
        daylog.set_value(self.data, self.day, "bbt_time", None)
        daylog.set_value(self.data, self.day, "bbt_skip", None)
        self.save("Reading deleted")
        self.refresh()

    # Chart --------------------------------------------------------------------------

    def _cycle_range(self):
        """Return (start, end) of the cycle being charted."""
        if self.prediction is not None:
            starts = [
                s for s in cycle.period_starts(self.data["periods"]) if s <= self.day
            ]
            if starts:
                return starts[-1], min(
                    self.day,
                    starts[-1] + timedelta(days=self.prediction.average_length + 6),
                )
        return self.day - timedelta(days=27), self.day

    def _chart_card(self, master) -> widgets.Card:
        start, end = self._cycle_range()
        days = (end - start).days + 1
        readings = bbt.readings_between(self.data["days"], start, end)
        shift = bbt.detect_thermal_shift(readings)
        card = widgets.Card(
            master,
            "This cycle",
            f"{start:%b} {start.day} to {end:%b} {end.day}  ·  {len(readings)} readings",
            icon="activity",
        )
        if len(readings) < 2:
            widgets.label(
                card.body,
                "Two or more readings draw your chart. Log every morning to see the pattern.",
                "callout",
                "text_muted",
                wraplength=480,
            ).grid(row=0, column=0, sticky="w")
            widgets.Hero3D(
                card.body,
                [
                    {
                        "kind": "thermometer",
                        "size": 90,
                        "x": 0.5,
                        "y": 0.5,
                        "amp": 5,
                        "hue": 0.08,
                        "accent": (239, 68, 68),
                    }
                ],
                height=120,
                gradient=False,
            ).grid(row=1, column=0, sticky="ew")
            return card
        by_day = dict(readings)
        values = []
        for offset in range(days):
            temp = by_day.get(start + timedelta(days=offset))
            values.append(
                None if temp is None else round(units.temp_in_unit(temp, self.unit), 2)
            )
        present = [v for v in values if v is not None]
        margin = 0.3 if self.unit == "f" else 0.15
        low, high = min(present) - margin, max(present) + margin
        reference = None
        shade_from = None
        if shift is not None:
            reference = round(units.temp_in_unit(shift.coverline_c, self.unit), 2)
            shade_from = (shift.first_high - start).days
        labels = [f"D{i + 1}" for i in range(days)]
        chart = widgets.LineChart(
            card.body,
            values,
            labels,
            low,
            high,
            "primary",
            height=230,
            fmt="{:.2f}",
            reference=reference,
            reference_text="coverline" if reference else "",
            shade_from=shade_from,
        )
        chart.grid(row=0, column=0, sticky="ew")
        return card

    # Status and tips -------------------------------------------------------------------

    def _status_card(self, master) -> widgets.Card:
        start, end = self._cycle_range()
        readings = bbt.readings_between(self.data["days"], start, end)
        shift = bbt.detect_thermal_shift(readings)
        card = widgets.Card(master, "Ovulation check", icon="sparkle")
        body = card.body
        if shift is not None:
            widgets.badge(body, "Thermal shift found", "good").grid(
                row=0, column=0, sticky="w"
            )
            text = (
                f"Your temperature rose on {shift.first_high:%b} {shift.first_high.day} and stayed above the coverline "
                f"of {units.format_temp(shift.coverline_c, self.unit)}. Ovulation most likely "
                f"happened around {shift.ovulation:%b} {shift.ovulation.day}."
            )
            widgets.label(body, text, "callout", wraplength=280).grid(
                row=1, column=0, sticky="w", pady=(10, 0)
            )
            return card
        have = bbt.baseline_progress(readings)
        widgets.label(body, "No shift yet", "title3").grid(row=0, column=0, sticky="w")
        if have < bbt.BASELINE_READINGS:
            text = f"{have} of the 6 baseline readings logged this cycle."
        else:
            text = (
                "Watching for 3 readings in a row above the coverline, the last 0.2 °C "
                "higher (or a 4th reading above it)."
            )
        widgets.label(body, text, "callout", "text_muted", wraplength=280).grid(
            row=1, column=0, sticky="w", pady=(4, 10)
        )
        widgets.progress_bar(body, have / bbt.BASELINE_READINGS).grid(
            row=2, column=0, sticky="ew"
        )
        return card

    def _tips_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master,
            "How to get a reliable reading",
            "The 3-over-6 rule only works with steady mornings",
            icon="info",
        )
        for row, tip in enumerate(TIPS):
            line = ctk.CTkFrame(card.body, fg_color="transparent")
            line.grid(row=row, column=0, sticky="ew", pady=3)
            ctk.CTkFrame(
                line, width=6, height=6, corner_radius=3, fg_color=theme.pair("primary")
            ).grid(row=0, column=0, padx=(2, 12))
            widgets.label(line, tip, "callout", wraplength=560).grid(
                row=0, column=1, sticky="w"
            )
        widgets.label(
            card.body,
            "The rule confirms ovulation after it happens; it does not predict it, and it is not birth control on its own.",
            "footnote", "text_muted", wraplength=580,
        ).grid(row=len(TIPS), column=0, sticky="w", pady=(10, 0))  # fmt: skip
        return card
