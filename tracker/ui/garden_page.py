"""My Garden: today's flower, the last 4 weeks as a real garden, badges and breathing.

Every petal is one habit, in that habit's colour, so a glance at the flower shows
what is done and what is left. Past days grow into a garden on rolling hills.
"""

from typing import override

import customtkinter as ctk

from tracker import daylog, garden
from tracker.ui import effects, icons, theme, widgets
from tracker.ui.page import Page

BUTTERFLY_STREAK = 3  # butterflies visit once a streak gets going
BADGE_ICONS = {
    "seed": "leaf",
    "sprout": "leaf",
    "steady": "flame",
    "evergreen": "sparkle",
    "full": "flower",
    "hydrated": "cup",
    "rested": "moon",
    "writer": "journal",
    "cycle": "drop",
}


class GardenPage(Page):
    """Turns daily logging into something that grows."""

    title = "My Garden"
    banner = [
        {"kind": "flower", "size": 92, "x": 0.82, "y": 0.5, "amp": 6, "hue": 0.9},
        {"kind": "flower", "size": 52, "x": 0.93, "y": 0.34, "amp": 5, "phase": 1.1, "hue": 0.13},
        {"kind": "flower", "size": 44, "x": 0.7, "y": 0.68, "amp": 4, "phase": 2.3, "hue": 0.58},
    ]  # fmt: skip
    banner_hue = 0.41

    @override
    def subheading(self) -> str:
        count = garden.petal_count(self.data, self.today)
        streak = daylog.logging_streak(self.data, self.today)
        return f"{count} of {garden.TOTAL_PETALS} petals today  ·  {streak}-day streak"

    @override
    def build(self) -> None:
        grid = widgets.ResponsiveGrid(self.body, min_column=300, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._today_card(grid))
        grid.add(lambda: self._garden_card(grid), span=2, shrink=True)
        grid.add(lambda: self._breathe_card(grid))
        grid.add(lambda: self._badges_card(grid), span=2, shrink=True)

    def _habits(self, day) -> list[tuple[str, bool]]:
        return garden.petals(daylog.peek_day(self.data, day), self.data["goals"])

    def _today_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master, "Today's flower", "One petal for each healthy habit", icon="flower"
        )
        habits = self._habits(self.today)
        done = [earned for _, earned in habits]
        widgets.FlowerView(card.body, 160, done).grid(row=0, column=0, pady=(0, 10))
        for row, ((name, earned), token) in enumerate(
            zip(habits, widgets.PETAL_TOKENS, strict=True), start=1
        ):
            line = ctk.CTkFrame(card.body, fg_color="transparent")
            line.grid(row=row, column=0, sticky="w", pady=1)
            image = icons.icon(
                "check_circle" if earned else "circle",
                18,
                token if earned else "text_muted",
            )
            ctk.CTkLabel(line, text="", image=image, width=24).grid(row=0, column=0)
            widgets.label(
                line, name, "callout", "text" if earned else "text_muted"
            ).grid(row=0, column=1, padx=(6, 0))
        step = garden.next_petal(
            daylog.peek_day(self.data, self.today), self.data["goals"]
        )
        if step:
            widgets.label(
                card.body, f"Next petal: {step['text']}", "callout", wraplength=260
            ).grid(row=7, column=0, sticky="w", pady=(10, 4))
            widgets.button(
                card.body,
                "Do This Now",
                lambda: self.app.show_page(step["page"]),
                kind="secondary",
                icon="chevron_right",
            ).grid(row=8, column=0, sticky="ew")
        return card

    def _garden_card(self, master) -> widgets.Card:
        streak = daylog.logging_streak(self.data, self.today)
        best = garden.longest_streak(self.data)
        card = widgets.Card(
            master,
            "Your garden",
            f"The last 4 weeks, this week in front  ·  Longest streak {best} days",
            icon="leaf",
        )
        days = [
            (day, [earned for _, earned in self._habits(day)])
            for day in daylog.last_n_days(self.today, 28)
        ]
        butterflies = 2 if streak >= BUTTERFLY_STREAK else 0
        if effects.simple_view:
            butterflies = 0
        widgets.GardenScene(card.body, days, height=430, butterflies=butterflies).grid(
            row=0, column=0, sticky="ew"
        )
        return card

    def _breathe_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master,
            "Take a breath",
            "Three slow 4-4-6 breaths, about 40 seconds",
            icon="heart",
        )
        circle = widgets.BreathingCircle(card.body, self._breath_done, size=230)
        circle.grid(row=0, column=0, pady=(0, 12))
        card.body.rowconfigure(0, weight=1)
        widgets.button(
            card.body, "Start Breathing", circle.start, kind="secondary"
        ).grid(row=1, column=0, sticky="ew")
        return card

    def _breath_done(self) -> None:
        effects.celebrate(self.app)
        widgets.toast(self.app, "Nicely done. Hope you feel calmer.")

    def _badges_card(self, master) -> widgets.Card:
        progress = garden.achievement_progress(self.data)
        earned = sum(1 for have, need in progress.values() if have >= need)
        card = widgets.Card(
            master,
            "Achievements",
            f"{earned} of {len(garden.ACHIEVEMENTS)} unlocked",
            icon="sparkle",
        )
        shelf = widgets.ResponsiveGrid(
            card.body, min_column=236, max_columns=3, gap=8, nested=True
        )
        shelf.grid(row=0, column=0, sticky="ew")
        for key, (title, how, _) in garden.ACHIEVEMENTS.items():
            have, need = progress[key]
            got = have >= need
            tile = ctk.CTkFrame(
                shelf,
                fg_color=theme.pair("primary_soft" if got else "surface_alt"),
                corner_radius=theme.RADIUS_CONTROL,
            )
            tile.columnconfigure(1, weight=1)
            tone = "primary_text" if got else "text_muted"
            ctk.CTkLabel(
                tile, text="", image=icons.icon(BADGE_ICONS[key], 22, tone)
            ).grid(row=0, column=0, rowspan=3, padx=(10, 8), pady=8, sticky="n")
            widgets.label(tile, title, "headline", tone).grid(
                row=0, column=1, sticky="w", pady=(8, 0), padx=(0, 8)
            )
            widgets.label(tile, how, "footnote", "text_muted", wraplength=150).grid(
                row=1, column=1, sticky="w", padx=(0, 8)
            )
            bar = widgets.progress_bar(tile, have / need, "primary", 5)
            bar.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(4, 10))
            widgets.Tooltip(tile, f"{have} of {need}")
            shelf.add(tile)
        return card
