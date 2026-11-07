"""Symptom and mood journal: a few taps a day, patterns over time."""

from datetime import timedelta
from typing import override

import customtkinter as ctk

from tracker import cycle, daylog, insights, journal
from tracker.ui import theme, widgets
from tracker.ui.page import Page

NOTE_SAVE_DELAY_MS = 800


class JournalPage(Page):
    """Mood, energy, stress, symptoms and a note for any day."""

    title = "Journal"
    subtitle = "How you feel, in a few taps. Everything saves as you go."
    banner = [
        {"kind": "smile", "size": 84, "x": 0.68, "y": 0.5, "amp": 6, "hue": 0.13, "accent": (88, 28, 135)},
    ]  # fmt: skip
    banner_hue = 0.78

    @override
    def build(self) -> None:
        if not hasattr(self, "day"):
            self.day = self.today
        widgets.DateSwitcher(self.actions, self.day, self._change_day, self.today).grid(
            row=0, column=0
        )
        self.log = daylog.peek_day(self.data, self.day)
        self.note_job = None
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._feel_card(grid), span=2)
        grid.add(lambda: self._notes_card(grid))
        grid.add(lambda: self._symptoms_card(grid), span=3)
        grid.add(lambda: self._patterns_card(grid), span=2)
        grid.add(lambda: self._trend_card(grid))

    def _feel_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "How are you feeling?", icon="smile")
        widgets.ScalePicker(
            card.body,
            journal.MOOD_LABELS,
            self.log.get("mood"),
            lambda v: self._set("mood", v, "Mood"),
            faces=True,
        ).grid(row=0, column=0, sticky="ew")
        for row, (key, title) in enumerate(
            (("energy", "Energy"), ("stress", "Stress")), start=1
        ):
            widgets.label(card.body, title, "label").grid(
                row=row * 2 - 1, column=0, sticky="w", pady=(16, 6)
            )
            widgets.ScalePicker(
                card.body,
                journal.LEVEL_LABELS,
                self.log.get(key),
                lambda v, k=key, t=title: self._set(k, v, t),
            ).grid(row=row * 2, column=0, sticky="ew")
        return card

    def _notes_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Note", "Anything worth remembering", icon="edit")
        self.note_box = ctk.CTkTextbox(
            card.body, height=150, corner_radius=12, border_width=1, wrap="word",
            fg_color=theme.pair("surface_alt"), border_color=theme.pair("border"),
            text_color=theme.pair("text"), font=theme.font("body"),
        )  # fmt: skip
        self.note_box.grid(row=0, column=0, sticky="ew")
        if self.log.get("note"):
            self.note_box.insert("1.0", self.log["note"])
        # Saved a moment after typing stops, so a note can't be lost by leaving.
        self.note_job = None
        self.note_box.bind("<KeyRelease>", self._note_typed, add="+")
        widgets.tab_moves_on(self.note_box._textbox)
        widgets.label(
            card.body, "Saves by itself as you type.", "footnote", "text_muted"
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        return card

    def _note_typed(self, _event) -> None:
        if self.note_job:
            self.after_cancel(self.note_job)
        self.note_job = self.after(NOTE_SAVE_DELAY_MS, self._save_note)

    def _symptoms_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master, "Symptoms", "Tap everything you notice", icon="journal"
        )
        widgets.ChipGrid(
            card.body,
            journal.SYMPTOMS,
            self.log.get("symptoms", []),
            multi=True,
            min_width=150,
            on_change=lambda v: self._set("symptoms", v, "Symptoms"),
        ).grid(row=0, column=0, sticky="ew")
        return card

    def _change_day(self, day) -> None:
        if self.note_job:  # the note belongs to the day being left
            self.after_cancel(self.note_job)
            self._save_note()
        self.day = day
        self.refresh()

    def _set(self, key: str, value, what: str) -> None:
        daylog.set_value(self.data, self.day, key, value)
        self.save(f"{what} saved")

    def _save_note(self) -> None:
        self.note_job = None
        text = self.note_box.get("1.0", "end").strip()
        if text != self.log.get("note", ""):
            daylog.set_value(self.data, self.day, "note", text or None)
            self.log = daylog.peek_day(self.data, self.day)
            self.save()
            self.built_version = self.app.data_version  # the box is already current

    def _patterns_card(self, master) -> widgets.Card:
        start = self.today - timedelta(days=60)
        counts = journal.symptom_counts(self.data["days"], start, self.today)
        card = widgets.Card(
            master, "Your symptom patterns", "Last 60 days", icon="sparkle"
        )
        body = card.body
        if not counts:
            widgets.label(
                body,
                "Log symptoms for a few days to see which come most often and when in your cycle.",
                "callout",
                "text_muted",
                wraplength=520,
            ).grid(row=0, column=0, sticky="w")
            return card
        prediction = insights.prediction_for(self.data)
        top = counts[0][1]
        for row, (symptom, count) in enumerate(counts[:5]):
            line = ctk.CTkFrame(body, fg_color="transparent")
            line.grid(row=row, column=0, sticky="ew", pady=4)
            line.columnconfigure(1, weight=1)
            widgets.label(line, symptom, "body", width=150).grid(
                row=0, column=0, sticky="w"
            )
            widgets.progress_bar(line, count / top, "lilac", 8).grid(
                row=0, column=1, sticky="ew", padx=12
            )
            when = self._usual_phase(symptom, start, prediction)
            widgets.label(
                line,
                f"{count} day{'s' if count != 1 else ''}{when}",
                "footnote",
                "text_muted",
                width=170,
            ).grid(row=0, column=2, sticky="e")
        return card

    def _usual_phase(self, symptom: str, start, prediction) -> str:
        if prediction is None:
            return ""
        phases: dict[str, int] = {}
        for day, log in self.data["days"].items():
            if start <= day <= self.today and symptom in log.get("symptoms", []):
                phase = cycle.phase_on(
                    day,
                    self.data["periods"],
                    prediction,
                    self.data["profile"]["period_length"],
                )
                if phase:
                    phases[phase] = phases.get(phase, 0) + 1
        if not phases:
            return ""
        phase = max(phases, key=phases.get)
        return f", mostly {cycle.PHASES[phase][0].lower()}"

    def _trend_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Mood, last 14 days", icon="smile")
        days = daylog.last_n_days(self.today, 14)
        values = [daylog.peek_day(self.data, day).get("mood") for day in days]
        if sum(1 for v in values if v) < 2:
            widgets.label(
                card.body,
                "Check in for two days to see your mood trend.",
                "callout",
                "text_muted",
                wraplength=260,
            ).grid(row=0, column=0, sticky="w")
            return card
        labels = [day.strftime("%a")[0] for day in days]
        widgets.LineChart(
            card.body, values, labels, 1, 5, "primary", height=190, fmt="{:.0f}"
        ).grid(row=0, column=0, sticky="ew")
        return card
