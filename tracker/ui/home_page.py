"""Today: the user's day at a glance, and the fastest way to log.

Order follows what people check first: where they are in their cycle, how
today's goals are going, one-click logging, then personal insights. The banner
follows the real sky: sunrise colours in the morning, a moon at night.
"""

from datetime import datetime, timedelta
from typing import override

import customtkinter as ctk

from tracker import (
    activity,
    cycle,
    daylog,
    garden,
    insights,
    journal,
    profile,
    vitals,
)
from tracker.ui import effects, icons, render3d, sfx, theme, widgets
from tracker.ui.page import Page

PHASE_COLORS = {
    cycle.MENSTRUAL: "period",
    cycle.FOLLICULAR: "lilac",
    "fertile": "fertile",
    cycle.OVULATION: "ovulation",
    cycle.LUTEAL: "luteal",
}
WHEEL_LEGEND = (
    ("period", "Period"),
    ("fertile", "Fertile"),
    ("ovulation", "Ovulation"),
    ("luteal", "Luteal"),
)
# (first hour, banner hue): sunrise, daytime blue, sunset, night
SKIES = ((5, 0.05), (11, 0.57), (17, 0.92), (19, 0.68))
NIGHT_HUE = 0.68


def sky_hue(hour: int) -> float:
    """Return the banner colour for an hour of the day."""
    hue = NIGHT_HUE
    for first_hour, value in SKIES:
        if hour >= first_hour:
            hue = value
    return hue


class HomePage(Page):
    """The first page after login."""

    title = "Today"
    banner = []
    banner_height = 148

    @override
    def hero_hue(self) -> float | None:
        return sky_hue(datetime.now().hour) if effects.page_colors else None

    @override
    def hero_objects(self) -> list[dict]:
        hour = datetime.now().hour
        if 6 <= hour < 19:
            sky = {
                "kind": "sphere",
                "size": 64,
                "x": 0.92,
                "y": 0.3,
                "amp": 3,
                "base": render3d.SUN,
                "glow": (255, 244, 214),
            }
        else:
            sky = {
                "kind": "moon",
                "size": 74,
                "x": 0.92,
                "y": 0.32,
                "amp": 3,
                "base": render3d.MOON,
                "glow": (255, 255, 255),
            }
        log = daylog.peek_day(self.data, self.today)
        done = [earned for _, earned in garden.petals(log, self.data["goals"])]
        scale = widgets.scaling(self)
        flower = {
            "kind": "image",
            "image": widgets.flower_image(round(112 * scale), done),
            "size": 112,
            "x": 0.76,
            "y": 0.52,
            "amp": 4,
            "phase": 1.0,
        }
        return [sky, flower]

    @override
    def heading(self) -> str:
        hour = datetime.now().hour
        part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        name = self.data["profile"]["display_name"] or self.app.user["username"]
        return f"Good {part}, {name.split()[0]}"

    @override
    def subheading(self) -> str:
        text = self.today.strftime("%A, %B %d").replace(" 0", " ")
        if self.data["profile"]["track_cycle"]:
            day = cycle.cycle_day(self.data["periods"], self.today)
            phase = insights.phase_today(self.data, self.today)
            if day is not None and phase is not None:
                text += f"  ·  Cycle day {day}, {cycle.PHASES[phase][0].lower()} phase"
        return text

    @override
    def build(self) -> None:
        self.log = daylog.peek_day(self.data, self.today)
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        if self.data["profile"]["track_cycle"]:
            grid.add(lambda: self._cycle_card(grid), span=2)
        else:
            grid.add(lambda: self._week_card(grid), span=2)
        grid.add(lambda: self._goals_card(grid))
        grid.add(lambda: self._quick_card(grid), span=3)
        grid.add(lambda: self._insights_card(grid), span=2)
        grid.add(lambda: self._checklist_card(grid))
        if self.data["profile"]["track_cycle"]:
            grid.add(lambda: self._week_card(grid), span=3)

    # Cycle -------------------------------------------------------------------

    def _no_cycle_yet(self, body, title: str, text: str) -> None:
        body.columnconfigure(1, weight=1)
        widgets.Hero3D(
            body,
            [{"kind": "drop", "size": 96, "x": 0.5, "y": 0.45, "amp": 6, "hue": 0.93}],
            height=130,
            width=140,
            gradient=False,
        ).grid(row=0, column=0, rowspan=3)
        widgets.label(body, title, "title3").grid(row=0, column=1, sticky="w")
        widgets.label(body, text, "callout", "text_muted", wraplength=360).grid(
            row=1, column=1, sticky="w", pady=4
        )
        widgets.button(
            body, "Log a Period", lambda: self.app.show_page("cycle"), icon="plus"
        ).grid(row=2, column=1, sticky="w", pady=(8, 0))

    def _cycle_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Your cycle", icon="drop")
        body = card.body
        prediction = insights.prediction_for(self.data)
        if prediction is None:
            self._no_cycle_yet(
                body,
                "Log your period to start",
                "One period gives a first estimate; two or more make predictions personal.",
            )
            return card
        if cycle.is_stale(prediction, self.today):
            self._no_cycle_yet(
                body,
                "Log your latest period",
                f"The last one logged started on {prediction.last_start:%B} {prediction.last_start.day}, {prediction.last_start.year}, "
                "so today's dates would only be a guess.",
            )
            return card

        day = cycle.cycle_day(self.data["periods"], self.today) or 1
        phase = insights.phase_today(self.data, self.today) or cycle.FOLLICULAR
        length = max((prediction.next_start - prediction.last_start).days, 1)
        body.columnconfigure(
            0, weight=0
        )  # the wheel keeps its size; text takes the rest
        body.columnconfigure(1, weight=1)
        segments = [
            (start, end, PHASE_COLORS[part])
            for start, end, part in cycle.phase_segments(prediction)
        ]
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, rowspan=4, padx=(0, 22), sticky="n")
        wheel = widgets.CycleWheel(
            left,
            158,
            segments,
            min((day - 0.5) / length, 1.0),
            f"Day {day}",
            f"of about {length}",
        )
        wheel.grid(row=0, column=0)
        legend = ctk.CTkFrame(left, fg_color="transparent")
        legend.grid(row=1, column=0, pady=(8, 0))
        for index, (token, text) in enumerate(WHEEL_LEGEND):
            row, column = divmod(index, 2)
            ctk.CTkFrame(
                legend, width=9, height=9, corner_radius=4, fg_color=theme.pair(token)
            ).grid(row=row, column=column * 2, padx=(4, 4))
            widgets.label(legend, text, "caption", "text_muted").grid(
                row=row, column=column * 2 + 1, sticky="w", padx=(0, 6)
            )
        name, description, tip = cycle.PHASES[phase]
        widgets.label(body, f"{name} phase", "title3").grid(row=0, column=1, sticky="w")
        widgets.label(
            body, f"{description} {tip}", "callout", "text_muted", wraplength=400
        ).grid(row=1, column=1, sticky="w", pady=(2, 10))

        facts = ctk.CTkFrame(body, fg_color="transparent")
        facts.grid(row=2, column=1, sticky="w")
        days = cycle.days_until(prediction.next_start, self.today)
        if days > 0:
            period_text = f"in {days} day{'s' if days != 1 else ''}"
        elif days == 0:
            period_text = "expected today"
        else:
            period_text = f"{-days} day{'s' if days != -1 else ''} late"
        self._fact(
            facts,
            0,
            "drop",
            "Next period",
            f"{prediction.next_start:%b} {prediction.next_start.day}, {period_text}",
        )
        row = 1
        if days >= 0:
            span = f"{prediction.earliest_next:%b} {prediction.earliest_next.day} – {prediction.latest_next:%b} {prediction.latest_next.day}"
            self._fact(facts, row, "calendar", "Likely between", span)
            row += 1
        cares_about_cycle = set(profile.focus_list(self.data["profile"])) - {"wellness"}
        if (
            cares_about_cycle
            or prediction.fertile_start <= self.today <= prediction.fertile_end
        ):
            start, end, this_cycle = cycle.fertile_window_ahead(prediction, self.today)
            title = "Fertile window" if this_cycle else "Next fertile window"
            self._fact(
                facts,
                row,
                "sparkle",
                title,
                f"{start:%b} {start.day} – {end:%b} {end.day}",
            )
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=3, column=1, sticky="w", pady=(12, 0))
        widgets.button(
            actions,
            "Open Calendar",
            lambda: self.app.show_page("cycle"),
            kind="secondary",
            icon="calendar",
        ).grid(row=0, column=0, padx=(0, 8))
        confidence = f"{prediction.confidence.title()} confidence"
        if prediction.basis != "calendar":
            confidence += f", from your {prediction.basis}"
        widgets.badge(actions, confidence, "info").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        return card

    def _fact(self, master, row: int, icon_name: str, title: str, text: str) -> None:
        ctk.CTkLabel(
            master, text="", image=icons.icon(icon_name, 16, "primary_text")
        ).grid(row=row, column=0, padx=(0, 8), pady=2)
        widgets.label(master, title, "callout", "text_muted").grid(
            row=row, column=1, sticky="w", padx=(0, 10)
        )
        widgets.label(master, text, "headline").grid(row=row, column=2, sticky="w")

    # Goals ---------------------------------------------------------------------

    def _goal_values(self) -> list[tuple[str, str, float, str]]:
        goals = self.data["goals"]
        log = daylog.peek_day(self.data, self.today)
        minutes = activity.active_minutes(log.get("workouts", []))
        moved = max(minutes / goals["active_min"], log.get("steps", 0) / goals["steps"])
        moved_text = f"{log.get('steps', 0):,} steps"
        if minutes:
            moved_text += f", {minutes} min"
        return [
            ("Move", "activity", moved, moved_text),
            (
                "Water",
                "water",
                log.get("water_ml", 0) / goals["water_ml"],
                f"{log.get('water_ml', 0):,} / {goals['water_ml']:,} ml",
            ),
            (
                "Sleep",
                "sleep",
                log.get("sleep_h", 0) / goals["sleep_h"],
                f"{log.get('sleep_h', 0):g} / {goals['sleep_h']:g} h",
            ),
        ]

    def _goals_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Today's goals", icon="flame")
        body = card.body
        values = self._goal_values()
        done = sum(1 for _, _, fraction, _ in values if fraction >= 1)
        self.rings = widgets.RingView(
            body,
            150,
            [(f, c, "surface_alt") for _, c, f, _ in values],
            thickness=13,
            center=f"{done}/3",
            caption="goals met",
        )
        self.rings.grid(row=0, column=0, pady=(0, 12))
        legend = ctk.CTkFrame(body, fg_color="transparent")
        legend.grid(row=1, column=0, sticky="ew")
        legend.columnconfigure(1, weight=1)
        self.legend_values = []
        for row, (name, color, _, text) in enumerate(values):
            ctk.CTkFrame(
                legend, width=10, height=10, corner_radius=5, fg_color=theme.pair(color)
            ).grid(row=row, column=0, padx=(0, 8))
            widgets.label(legend, name, "callout", "text_muted").grid(
                row=row, column=1, sticky="w"
            )
            value_label = widgets.label(legend, text, "callout")
            value_label.grid(row=row, column=2, sticky="e", pady=2)
            self.legend_values.append(value_label)
        widgets.button(
            body, "Add a Glass of Water", self._add_water, kind="secondary", icon="cup"
        ).grid(row=2, column=0, sticky="ew", pady=(12, 0))
        return card

    def _add_water(self) -> None:
        before = self._goal_values()[1][2]
        daylog.add_amount(self.data, self.today, "water_ml", 250)
        self.save()
        values = self._goal_values()
        done = sum(1 for _, _, fraction, _ in values if fraction >= 1)
        self.rings.update_rings(
            [(f, c, "surface_alt") for _, c, f, _ in values], f"{done}/3", "goals met"
        )
        for value_label, (_, _, _, text) in zip(
            self.legend_values, values, strict=True
        ):
            value_label.configure(text=text)
        widgets.toast(
            self.app,
            "Water goal reached. Well done!"
            if values[1][2] >= 1
            else "+250 ml water logged",
        )
        if before < 1 <= values[1][2]:
            effects.celebrate(self.app)
        self._fill_insights()
        self._fill_checklist()
        self.built_version = self.app.data_version  # nothing here is out of date

    # Quick log -------------------------------------------------------------------

    def _quick_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master, "Quick log", "One click to the thing you log most", icon="plus"
        )
        tiles = [
            ("thermometer", "Temperature", "bbt"),
            ("smile", "Mood", "journal"),
            ("moon", "Sleep", "vitals"),
            ("activity", "Workout", "activity"),
            ("leaf", "Food", "nutrition"),
            ("scale", "Weight", "bmi"),
        ]
        if not self.data["profile"]["track_cycle"]:
            tiles = tiles[1:]
        shelf = widgets.ResponsiveGrid(
            card.body, min_column=112, max_columns=6, gap=8, nested=True
        )
        shelf.grid(row=0, column=0, sticky="ew")
        for icon_name, text, page in tiles:
            shelf.add(
                widgets.tile_button(
                    shelf, text, icon_name, lambda p=page: self.app.show_page(p)
                )
            )
        return card

    # Insights and checklist --------------------------------------------------------

    def _insights_card(self, master) -> widgets.Card:
        self.insights_card = widgets.Card(
            master,
            "Insights for you",
            "From your own logs and trusted health guidance",
            icon="sparkle",
        )
        self._fill_insights()
        return self.insights_card

    def _fill_insights(self) -> None:
        body = self.insights_card.body
        for child in body.winfo_children():
            child.destroy()
        found = insights.build_insights(self.data, datetime.now(), limit=5)
        if not found:
            widgets.label(
                body,
                "Log a few days of mood, sleep and your cycle, and personal patterns will appear here.",
                "callout",
                "text_muted",
                wraplength=520,
            ).grid(row=0, column=0, sticky="w")
            return
        for row, item in enumerate(found):
            strong, soft = widgets.TONES[item["tone"]]
            line = ctk.CTkFrame(
                body, fg_color=theme.pair("surface_alt"), corner_radius=14
            )
            line.grid(row=row, column=0, sticky="ew", pady=4)
            line.columnconfigure(1, weight=1)
            ctk.CTkLabel(
                line,
                text="",
                image=icons.icon(item["icon"], 18, strong),
                width=36,
                height=36,
                corner_radius=10,
                fg_color=theme.pair(soft),
            ).grid(row=0, column=0, rowspan=2, padx=12, pady=12, sticky="n")
            widgets.label(line, item["title"], "headline").grid(
                row=0, column=1, sticky="w", pady=(12, 0)
            )
            widgets.label(
                line, item["text"], "callout", "text_muted", reserve=48, wraplength=520
            ).grid(row=1, column=1, sticky="w", pady=(2, 12))
            if item["page"]:
                widgets.icon_button(
                    line,
                    "chevron_right",
                    lambda p=item["page"]: self.app.show_page(p),
                    size=32,
                    kind="ghost",
                    tooltip=f"Open: {item['title']}",
                ).grid(row=0, column=2, rowspan=2, padx=8)

    def _checklist_card(self, master) -> widgets.Card:
        self.checklist_card = widgets.Card(
            master, "Daily check-in", "A few small things", icon="check"
        )
        self._fill_checklist()
        return self.checklist_card

    def _fill_checklist(self) -> None:
        body = self.checklist_card.body
        for child in body.winfo_children():
            child.destroy()
        items = insights.daily_checklist(self.data, self.today)
        done = sum(1 for item in items if item["done"])
        self.checklist_card.subtitle_label.configure(
            text=f"{done} of {len(items)} done"
        )
        widgets.progress_bar(body, done / len(items)).grid(
            row=0, column=0, sticky="ew", pady=(0, 12)
        )
        for row, item in enumerate(items, start=1):
            mark = "check" if item["done"] else "plus"
            entry = ctk.CTkButton(
                body,
                text=item["label"],
                image=icons.icon(
                    mark, 16, "success" if item["done"] else "primary_text"
                ),
                anchor="w",
                height=theme.control_height(38),
                corner_radius=10,
                font=theme.font("callout"),
                fg_color="transparent",
                hover_color=theme.pair("surface_alt"),
                text_color=theme.pair("text_muted" if item["done"] else "text"),
                command=sfx.with_sound(
                    lambda p=item["page"]: self.app.show_page(p), "click"
                ),
            )
            entry.grid(row=row, column=0, sticky="ew")
            state = "done" if item["done"] else "not done"
            widgets.keyboard(entry, entry.invoke, f"{item['label']}, {state}")
        streak = daylog.logging_streak(self.data, self.today)
        if streak:
            line = ctk.CTkFrame(
                body, fg_color=theme.pair("primary_soft"), corner_radius=12
            )
            line.grid(row=len(items) + 1, column=0, sticky="ew", pady=(10, 0))
            ctk.CTkLabel(
                line, text="", image=icons.icon("flame", 18, "primary_text")
            ).grid(row=0, column=0, padx=(12, 8), pady=8)
            widgets.label(
                line, f"{streak}-day logging streak", "headline", "primary_text"
            ).grid(row=0, column=1, sticky="w")

    # This week ----------------------------------------------------------------------

    def _week_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Your last 7 days", icon="calendar")
        days = self.data["days"]
        sleep = vitals.average_of(days, "sleep_h", self.today)
        mood = vitals.average_of(days, "mood", self.today)
        steps = vitals.average_of(days, "steps", self.today)
        minutes = activity.weekly_moderate_minutes(days, self.today)
        goal = activity.weekly_goal_minutes(insights.age_for(self.data, self.today))
        stats = [
            (f"{sleep:.1f} h" if sleep else "–", "Average sleep"),
            (journal.MOOD_LABELS[round(mood)] if mood else "–", "Typical mood"),
            (f"{steps:,.0f}" if steps else "–", "Average steps"),
            (f"{minutes} min", f"Active (WHO goal {goal})"),
        ]
        for column, (value, caption) in enumerate(stats):
            card.body.columnconfigure(column, weight=1, uniform="week")
            widgets.stat(card.body, value, caption, "number_sm").grid(
                row=0, column=column, sticky="w"
            )
        start = self.today - timedelta(days=6)
        logged = sum(1 for day in days if start <= day <= self.today)
        widgets.label(
            card.body,
            f"You logged on {logged} of the last 7 days.",
            "footnote",
            "text_muted",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(12, 0))
        return card
