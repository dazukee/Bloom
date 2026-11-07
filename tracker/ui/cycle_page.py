"""Cycle: calendar, day logging, predictions, hormones and history."""

from datetime import date
from typing import override

import customtkinter as ctk

from tracker import calendar_logic, cycle, daylog, insights, profile
from tracker.ui import theme, widgets
from tracker.ui.page import Page

STATUS_STYLE = {
    # status: (fill token or None, text token)
    calendar_logic.STATUS_PERIOD: ("period", "on_primary"),
    calendar_logic.STATUS_PREDICTED: ("predicted", "text"),
    calendar_logic.STATUS_OVULATION: ("ovulation", "on_primary"),
    calendar_logic.STATUS_FERTILE: ("fertile_soft", "text"),
    calendar_logic.STATUS_NONE: (None, "text"),
}
LEGEND = (
    ("period", "Period"),
    ("predicted", "Predicted period"),
    ("fertile_soft", "Fertile window"),
    ("ovulation", "Ovulation"),
)
# Letters on the calendar for people who cannot tell the colours apart.
LETTERS = {
    "period": "P",
    "predicted": "E",
    "fertile_soft": "F",
    "ovulation": "O",
}
STATUS_LETTERS = {
    calendar_logic.STATUS_PERIOD: "P",
    calendar_logic.STATUS_PREDICTED: "E",
    calendar_logic.STATUS_FERTILE: "F",
    calendar_logic.STATUS_OVULATION: "O",
    calendar_logic.STATUS_NONE: "",
}
FLOWS = ("Spotting", "Light", "Medium", "Heavy")
MUCUS = ("Dry", "Sticky", "Creamy", "Watery", "Egg white")
LH = ("Negative", "Positive")


class CyclePage(Page):
    """Log periods and see where you are in your cycle."""

    title = "Cycle"
    banner = [
        {"kind": "drop", "size": 88, "x": 0.82, "y": 0.5, "amp": 6, "hue": 0.95},
        {"kind": "sphere", "size": 42, "x": 0.93, "y": 0.34, "amp": 5, "phase": 1.2, "hue": 0.85},
        {"kind": "moon", "size": 52, "x": 0.7, "y": 0.66, "amp": 4, "phase": 2.4, "hue": 0.1},
    ]  # fmt: skip
    banner_hue = 0.93

    @override
    def subheading(self) -> str:
        prediction = insights.prediction_for(self.data)
        if prediction is None:
            return "Log your periods and Bloom will predict the next one."
        if cycle.is_stale(prediction, self.today):
            return "Log your latest period to bring predictions up to date."
        return (
            f"Average {prediction.average_length}-day cycle  ·  next period around "
            f"{prediction.next_start:%B} {prediction.next_start.day}".replace(" 0", " ")
        )

    @override
    def build(self) -> None:
        if not hasattr(self, "selected"):
            self.selected = self.today
            self.month = (self.today.year, self.today.month)
        self.prediction = insights.prediction_for(self.data)
        self.period_length = self.data["profile"]["period_length"]
        self.age = insights.age_for(self.data, self.today)
        # What the calendar colours: a late period moves up to today, and after a
        # very long gap nothing is projected at all.
        self.shown_prediction = self.prediction
        if self.prediction is not None:
            if cycle.is_stale(self.prediction, self.today):
                self.shown_prediction = None
            else:
                self.shown_prediction = cycle.rolled_forward(
                    self.prediction, self.today
                )
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._calendar_card(grid), span=2)
        grid.add(lambda: self._day_card(grid))
        grid.add(lambda: self._prediction_card(grid))
        grid.add(lambda: self._hormone_card(grid), span=2)
        grid.add(lambda: self._history_card(grid), span=3)

    def _day_card(self, master) -> widgets.Card:
        self.day_card = widgets.Card(master, "Selected day", icon="edit")
        self._fill_day()
        return self.day_card

    # Calendar ----------------------------------------------------------------------

    def _calendar_card(self, master) -> widgets.Card:
        def header(head):
            nav = ctk.CTkFrame(head, fg_color="transparent")
            widgets.icon_button(
                nav,
                "chevron_left",
                lambda: self._move_month(-1),
                size=34,
                kind="ghost",
                tooltip="Previous month",
            ).grid(row=0, column=0)
            self.month_label = widgets.label(
                nav, "", "headline", anchor="center", width=150
            )
            self.month_label.grid(row=0, column=1)
            widgets.icon_button(
                nav,
                "chevron_right",
                lambda: self._move_month(1),
                size=34,
                kind="ghost",
                tooltip="Next month",
            ).grid(row=0, column=2)
            widgets.button(
                nav, "Today", self._go_today, kind="plain", height=34, width=70
            ).grid(row=0, column=3, padx=(8, 0))
            return nav

        card = widgets.Card(master, "Calendar", icon="calendar", action=header)
        year, month = self.month
        self.calendar = widgets.CalendarView(
            card.body,
            year,
            month,
            self._day_style,
            self.today,
            self.selected,
            self._select,
            mark=self._day_mark,
        )
        self.calendar.grid(row=0, column=0, sticky="ew")
        legend = ctk.CTkFrame(card.body, fg_color="transparent")
        legend.grid(row=1, column=0, sticky="w", pady=(14, 0))
        for column, (token, text) in enumerate(LEGEND):
            ctk.CTkFrame(
                legend, width=12, height=12, corner_radius=6, fg_color=theme.pair(token)
            ).grid(row=0, column=column * 2, padx=(0, 6))
            shown = f"{text} ({LETTERS[token]})" if widgets.calendar_symbols else text
            widgets.label(legend, shown, "footnote", "text_muted").grid(
                row=0, column=column * 2 + 1, padx=(0, 16)
            )
        widgets.label(
            card.body,
            "The ring marks today and a dot means something is logged. Predictions are estimates.",
            "footnote",
            "text_muted",
            wraplength=560,
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._draw_month()
        return card

    def _status(self, day: date) -> str:
        return calendar_logic.day_status(
            day, self.data["periods"], self.shown_prediction, self.period_length
        )

    def _day_style(self, day: date) -> tuple[str | None, str]:
        """Return (fill colour, text colour) for one calendar day."""
        fill, text = STATUS_STYLE[self._status(day)]
        if fill is None and day == self.selected:
            return "surface_alt", text
        return fill, text

    def _day_mark(self, day: date) -> tuple[str, bool]:
        """Return (a letter when symbols are on, whether anything was logged)."""
        letter = STATUS_LETTERS[self._status(day)] if widgets.calendar_symbols else ""
        return letter, daylog.logged_any(self.data, day)

    def _draw_month(self) -> None:
        year, month = self.month
        self.month_label.configure(text=date(year, month, 1).strftime("%B %Y"))
        if hasattr(self, "calendar"):
            self.calendar.show(year, month, self.selected)

    def _move_month(self, step: int) -> None:
        year, month = self.month
        move = calendar_logic.next_month if step > 0 else calendar_logic.previous_month
        self.month = move(year, month)
        self._draw_month()

    def _go_today(self) -> None:
        self.month = (self.today.year, self.today.month)
        self._select(self.today)

    def _select(self, day: date) -> None:
        self.selected = day
        self.month = (day.year, day.month)  # arrow keys can cross into a new month
        self._draw_month()
        self._fill_day()

    # The selected day ---------------------------------------------------------------

    def _covering_period(self, day: date) -> dict | None:
        for period in self.data["periods"]:
            if period["start"] <= day <= cycle.period_end(period, self.period_length):
                return period
        return None

    def _fill_day(self) -> None:
        body = self.day_card.body
        for child in body.winfo_children():
            child.destroy()
        day = self.selected
        widgets.label(
            body, day.strftime("%A, %B %d").replace(" 0", " "), "title3"
        ).grid(row=0, column=0, sticky="w")
        status = self._status(day)
        parts = []
        number = cycle.cycle_day(self.data["periods"], day)
        if number:
            parts.append(f"Cycle day {number}")
        names = {
            calendar_logic.STATUS_PERIOD: "Period",
            calendar_logic.STATUS_PREDICTED: "Predicted period",
            calendar_logic.STATUS_FERTILE: "Fertile window (estimate)",
            calendar_logic.STATUS_OVULATION: "Likely ovulation (estimate)",
        }
        if status in names:
            parts.append(names[status])
        widgets.label(
            body,
            "  ·  ".join(parts) or "No cycle data for this day",
            "callout",
            "text_muted",
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))
        if day > self.today:
            widgets.note(
                body, "You can log this day once it arrives.", "info", 260
            ).grid(row=2, column=0, sticky="ew")
            return

        covering = self._covering_period(day)
        row = 2
        if covering is None:
            widgets.button(
                body, "Period Started This Day", self._start_period, icon="drop"
            ).grid(row=row, column=0, sticky="ew")
            row += 1
            longer = cycle.extendable_period(self.data["periods"], day)
            if longer is not None and day > cycle.period_end(
                longer, self.period_length
            ):
                # The period ran longer than expected, or its end was logged too soon.
                widgets.button(
                    body,
                    f"Period From {longer['start']:%b} {longer['start'].day} Ended This Day",
                    self._end_period,
                    kind="secondary",
                    icon="check",
                ).grid(row=row, column=0, sticky="ew", pady=(8, 0))
                row += 1
        else:
            end = covering.get("end")
            span = (
                f"{covering['start']:%b} {covering['start'].day} – {end:%b} {end.day}"
                if end
                else f"Since {covering['start']:%b} {covering['start'].day}"
            )
            widgets.label(body, f"Period: {span}", "headline", "period").grid(
                row=row, column=0, sticky="w"
            )
            row += 1
            if end != day and day > covering["start"]:
                widgets.button(
                    body,
                    "Period Ended This Day",
                    self._end_period,
                    kind="secondary",
                    icon="check",
                ).grid(row=row, column=0, sticky="ew", pady=(8, 0))
                row += 1
            widgets.button(
                body,
                "Remove This Period",
                self._remove_period,
                kind="plain",
                icon="trash",
            ).grid(row=row, column=0, sticky="ew", pady=(8, 0))
            row += 1
        log = daylog.peek_day(self.data, day)
        sections = [("Flow", "flow", FLOWS)] if covering else []
        sections += [
            ("Cervical mucus", "mucus", MUCUS),
            ("Ovulation (LH) test", "lh", LH),
        ]
        for title, key, options in sections:
            widgets.label(body, title, "label").grid(
                row=row, column=0, sticky="w", pady=(16, 4)
            )
            current = log.get(key)
            chosen = [o for o in options if o.lower() == current]
            chips = widgets.ChipGrid(
                body,
                options,
                chosen,
                multi=False,
                min_width=88,
                on_change=lambda value, k=key: self._set(k, value),
            )
            chips.grid(row=row + 1, column=0, sticky="ew")
            row += 2

    def _set(self, key: str, value) -> None:
        daylog.set_value(
            self.data, self.selected, key, value.lower() if value else None
        )
        self.save("Saved")
        self._draw_month()

    def _start_period(self) -> None:
        try:
            self.data["periods"] = cycle.add_period(
                self.data["periods"],
                self.selected,
                None,
                self.today,
                self.period_length,
            )
        except ValueError as error:
            widgets.toast(self.app, str(error), "warning")
            return
        self.save("Period logged. Predictions updated.")
        self.refresh()

    def _end_period(self) -> None:
        covering = self._covering_period(self.selected)
        if covering is None:
            covering = cycle.extendable_period(self.data["periods"], self.selected)
        try:
            self.data["periods"] = cycle.set_period_end(
                self.data["periods"], covering["start"], self.selected, self.today
            )
        except ValueError as error:
            widgets.toast(self.app, str(error), "warning")
            return
        self.save("Period end saved")
        self.refresh()

    def _remove_period(self) -> None:
        if not widgets.confirm(
            self.app,
            "Remove this period?",
            "Its predictions will be recalculated. Day notes such as flow are kept.",
            "Remove",
            danger=True,
        ):
            return
        covering = self._covering_period(self.selected)
        self.data["periods"] = cycle.remove_period(
            self.data["periods"], covering["start"]
        )
        self.save("Period removed")
        self.refresh()

    # Prediction ------------------------------------------------------------------------

    def _prediction_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Next period", icon="drop")
        body = card.body
        p = self.prediction
        if p is None:
            widgets.Hero3D(
                body,
                [
                    {
                        "kind": "drop",
                        "size": 84,
                        "x": 0.5,
                        "y": 0.5,
                        "amp": 6,
                        "hue": 0.93,
                    }
                ],
                height=110,
                gradient=False,
            ).grid(row=0, column=0, sticky="ew")
            widgets.label(
                body,
                "Select the first day of your last period in the calendar, then choose Period Started This Day.",
                "callout",
                "text_muted",
                wraplength=280,
            ).grid(row=1, column=0, sticky="w")
            return card
        if cycle.is_stale(p, self.today):
            widgets.label(body, "It has been a while", "title3").grid(
                row=0, column=0, sticky="w"
            )
            widgets.label(
                body,
                f"The last period logged started on {p.last_start:%B} {p.last_start.day}, {p.last_start.year}. "
                "Select the day your latest one started, then choose Period Started This Day.",
                "callout",
                "text_muted",
                wraplength=280,
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))
            return card
        days = cycle.days_until(p.next_start, self.today)
        if days > 0:
            big, caption = str(days), "days to go" if days != 1 else "day to go"
        elif days == 0:
            big, caption = "Today", "the most likely day"
        else:
            big, caption = str(-days), "days late" if days != -1 else "day late"
        number = widgets.stat(body, big, caption, "number_xl", "primary_text")
        number.grid(row=0, column=0, sticky="w", pady=(0, 12))
        start, end, this_cycle = cycle.fertile_window_ahead(p, self.today)
        rows = [
            ("Most likely", f"{p.next_start:%b} {p.next_start.day}"),
            (
                "Likely between",
                f"{p.earliest_next:%b} {p.earliest_next.day} – {p.latest_next:%b} {p.latest_next.day}",
            ),
            (
                "Fertile window" if this_cycle else "Next fertile window",
                f"{start:%b} {start.day} – {end:%b} {end.day}",
            ),
            (
                "Ovulation" if this_cycle else "Last ovulation",
                f"around {p.ovulation:%b} {p.ovulation.day}",
            ),
        ]
        for row, (title, text) in enumerate(rows, start=1):
            widgets.label(body, title, "callout", "text_muted").grid(
                row=row, column=0, sticky="w", pady=2
            )
            widgets.label(body, text, "headline").grid(
                row=row, column=1, sticky="e", pady=2
            )
        body.columnconfigure(1, weight=1)
        shift = insights.current_shift(self.data, self.today)
        badges = ctk.CTkFrame(body, fg_color="transparent")
        badges.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 6))
        widgets.badge(badges, f"{p.confidence.title()} confidence", "info").grid(
            row=0, column=0, sticky="w"
        )
        if shift is not None:
            widgets.badge(badges, "Ovulation confirmed by temperature", "good").grid(
                row=1, column=0, sticky="w", pady=(4, 0)
            )
        if p.basis != "calendar":
            why = f"Counted from this cycle's ovulation, shown by your {p.basis}."
        elif p.uses_default_length:
            why = f"Using your usual {p.average_length}-day cycle until you log a second period."
        else:
            stats = cycle.cycle_stats(self.data["periods"])
            why = f"Based on your last {min(stats['count'], cycle.CYCLES_TO_AVERAGE)} cycles; they vary by {stats['spread']} days."
        widgets.label(body, why, "footnote", "text_muted", wraplength=290).grid(
            row=6, column=0, columnspan=2, sticky="w"
        )
        if profile.has_focus(self.data["profile"], "avoid"):
            widgets.note(
                body,
                "Predictions are estimates and are not birth control.",
                "warning",
                260,
            ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        return card

    # Hormones --------------------------------------------------------------------------

    def _hormone_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master,
            "Hormones across your cycle",
            "A typical pattern scaled to your cycle length, not a measurement",
            icon="activity",
        )
        length = (
            self.prediction.average_length
            if self.prediction
            else self.data["profile"]["cycle_length"]
        )
        today_day = cycle.cycle_day(self.data["periods"], self.today)
        if today_day is not None and today_day > length:
            today_day = None
        ovulation = cycle.schematic_ovulation_day(length)
        span = max(length - 1, 1)
        # Phase edges as fractions of the chart width; min() and max() keep them
        # in order even for a very short cycle with a long period.
        period_end = min((self.period_length - 1) / span, 1)
        fertile = min(max((ovulation - 2.5) / span, period_end), 1)
        luteal = min(max((ovulation - 0.5) / span, fertile), 1)
        bands = [
            (0, period_end, "period"),
            (period_end, fertile, "lilac"),
            (fertile, luteal, "ovulation"),
            (luteal, 1, "luteal"),
        ]
        chart = widgets.HormoneChart(
            card.body, length, today_day, cycle.hormone_levels, bands
        )
        chart.grid(row=0, column=0, sticky="ew")
        phase = insights.phase_today(self.data, self.today)
        if phase:
            name, description, tip = cycle.PHASES[phase]
            box = ctk.CTkFrame(
                card.body, fg_color=theme.pair("surface_alt"), corner_radius=14
            )
            box.grid(row=1, column=0, sticky="ew", pady=(12, 0))
            box.columnconfigure(0, weight=1)
            widgets.label(box, f"Today: {name} phase", "headline").grid(
                row=0, column=0, sticky="w", padx=14, pady=(12, 2)
            )
            widgets.label(
                box, f"{description} {tip}", "callout", "text_muted", wraplength=640
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))
        return card

    # History ---------------------------------------------------------------------------

    def _history_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Cycle history", icon="clock")
        body = card.body
        periods = sorted(self.data["periods"], key=lambda p: p["start"])
        if not periods:
            widgets.label(
                body, "Your logged periods will appear here.", "callout", "text_muted"
            ).grid(row=0, column=0, sticky="w")
            return card
        stats = cycle.cycle_stats(periods)
        if stats:
            strip = ctk.CTkFrame(body, fg_color="transparent")
            strip.grid(row=0, column=0, sticky="ew", pady=(0, 14))
            values = [
                (f"{stats['average']} days", "Average cycle"),
                (f"{stats['shortest']} days", "Shortest"),
                (f"{stats['longest']} days", "Longest"),
                (str(stats["count"]), "Cycles logged"),
            ]
            for column, (value, caption) in enumerate(values):
                strip.columnconfigure(column, weight=1, uniform="stats")
                widgets.stat(strip, value, caption, "number_sm").grid(
                    row=0, column=column, sticky="w"
                )
        starts = [p["start"] for p in periods]
        table = ctk.CTkFrame(body, fg_color="transparent")
        table.grid(row=1, column=0, sticky="ew")
        table.columnconfigure(0, weight=1)
        for header, column in (("Period", 0), ("Length", 1), ("Cycle", 2)):
            widgets.label(table, header, "label", "text_muted").grid(
                row=0,
                column=column,
                sticky="w" if column == 0 else "e",
                padx=(0, 0 if column == 0 else 24),
                pady=(0, 6),
            )
        newest_first = list(enumerate(periods))[::-1][:8]
        for row, (index, period) in enumerate(newest_first, start=1):
            end = period.get("end")
            span = (
                f"{period['start']:%b} {period['start'].day}, {period['start'].year}"
                + (f" – {end:%b} {end.day}" if end else "")
            )
            length = f"{(end - period['start']).days + 1} days" if end else "-"
            if index + 1 < len(starts):
                days = (starts[index + 1] - period["start"]).days
                unusual = cycle.lengths_outside_typical_range([days], self.age)
                low, high = cycle.typical_range(self.age)
                outside = f"  (outside {low}-{high})" if unusual else ""
                cycle_text = f"{days} days{outside}"
            else:
                cycle_text = "Current"
            widgets.label(table, span, "body").grid(
                row=row, column=0, sticky="w", pady=4
            )
            widgets.label(table, length, "body", "text_muted").grid(
                row=row, column=1, sticky="e", padx=(0, 24)
            )
            widgets.label(
                table,
                cycle_text,
                "body",
                "warning" if "outside" in cycle_text else "text",
            ).grid(row=row, column=2, sticky="e", padx=(0, 24))
        widgets.label(
            body,
            "Long or unusual cycles are worth raising with a doctor: a period over 8 days, "
            "or 3 months with none.",
            "footnote",
            "text_muted",
            wraplength=700,
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))
        lengths = cycle.usable_lengths(starts)[-cycle.CYCLES_TO_AVERAGE :]
        if len(cycle.lengths_outside_typical_range(lengths, self.age)) >= 2:
            low, high = cycle.typical_range(self.age)
            widgets.note(
                body,
                f"Several recent cycles were outside the typical {low}-{high} days. If this continues, consider talking to a doctor.",
                "warning",
            ).grid(row=2, column=0, sticky="ew", pady=(12, 0))
        return card
