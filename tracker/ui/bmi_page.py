"""BMI: log weight, see the category on a gauge, and the trend over time."""

from typing import override

import customtkinter as ctk

from tracker import bmi, growth, profile, units, validators
from tracker.ui import anim, theme, widgets
from tracker.ui.page import Page

SCALE_LOW = 15.0
SCALE_HIGH = 40.0
STANDARDS = {"CDC / WHO": bmi.CDC, "Asia-Pacific": bmi.ASIA_PACIFIC}


def _fraction(value: float) -> float:
    """Position of a BMI on the gauge, 0 (15) to 1 (40)."""
    return (min(max(value, SCALE_LOW), SCALE_HIGH) - SCALE_LOW) / (
        SCALE_HIGH - SCALE_LOW
    )


class BmiPage(Page):
    """Weight in, BMI out, with healthy range and history."""

    title = "BMI"
    banner = [
        {"kind": "sphere", "size": 70, "x": 0.56, "y": 0.5, "amp": 6, "hue": 0.58},
        {"kind": "torus", "size": 62, "x": 0.66, "y": 0.42, "amp": 5, "phase": 1.3, "hue": 0.5},
    ]  # fmt: skip
    banner_hue = 0.58

    def _months(self) -> int | None:
        born = self.data["profile"]["birth_date"]
        return growth.age_in_months(born, self.today) if born else None

    def _assessment(self, value: float) -> growth.BmiAssessment:
        return growth.assess(
            value,
            self.data["profile"]["height_cm"],
            self._months(),
            self.settings["bmi_standard"],
        )

    @override
    def subheading(self) -> str:
        value = self._current_bmi()
        if value is None:
            return "Add your height in Settings and log a weight to see your BMI."
        return f"Your BMI is {value} ({self._assessment(value).category.lower()})."

    def _current_bmi(self) -> float | None:
        weight = profile.current_weight(self.data)
        height = self.data["profile"]["height_cm"]
        if weight is None or height is None:
            return None
        return bmi.calculate_bmi(weight, height)

    @override
    def build(self) -> None:
        standard = self.settings["bmi_standard"]
        label = next(name for name, key in STANDARDS.items() if key == standard)
        if not growth.applies(self._months()):  # under 20, percentiles replace these
            self.standard_control = widgets.segmented(
                self.actions, list(STANDARDS), label, command=self._set_standard
            )
            self.standard_control.grid(row=0, column=0)
            self.standard_control.glass = self._glass_standard
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._log_card(grid))
        grid.add(lambda: self._gauge_card(grid), span=2, shrink=True)
        grid.add(lambda: self._history_card(grid), span=3)

    def _glass_standard(self, backdrop: str) -> None:
        """Restyle the standard switch for the banner behind it."""
        pill = widgets.glass_color(backdrop)
        self.standard_control.configure(
            bg_color=backdrop,
            fg_color=pill,
            unselected_color=pill,
            unselected_hover_color=widgets.mix(pill, "#FFFFFF", 0.1),
            selected_color=widgets.mix(pill, "#000000", 0.35),
            selected_hover_color=widgets.mix(pill, "#000000", 0.25),
            text_color="#FFFFFF",
        )

    def _set_standard(self, label: str) -> None:
        self.settings["bmi_standard"] = STANDARDS[label]
        self.save(f"Using {label} categories")
        self.refresh()

    # Logging ----------------------------------------------------------------------------

    def _log_card(self, master) -> widgets.Card:
        unit = self.settings["weight_unit"]
        card = widgets.Card(
            master,
            "Log your weight",
            "Weigh at the same time of day for fair comparisons",
            icon="scale",
        )
        body = card.body
        weight = profile.current_weight(self.data)
        shown = units.kg_to_lb(weight) if (weight and unit == "lb") else weight
        self.weight_field = widgets.Field(
            body,
            "Weight",
            "55.5",
            unit=unit,
            value=f"{shown:.1f}" if shown else "",
            on_enter=self._save_weight,
        )
        self.weight_field.grid(row=0, column=0, sticky="ew")
        height = self.data["profile"]["height_cm"]
        height_text = (
            units.format_height(height, self.settings["height_unit"])
            if height
            else "not set"
        )
        widgets.label(
            body,
            f"Height: {height_text}  (change it in Settings)",
            "footnote",
            "text_muted",
        ).grid(row=1, column=0, sticky="w", pady=(8, 14))
        widgets.button(
            body,
            "Save Weight",
            self._save_weight,
            icon="check",
            height=theme.BIG_CONTROL_HEIGHT,
        ).grid(row=2, column=0, sticky="ew")
        if growth.applies(self._months()):
            widgets.note(
                body,
                "Under 20, BMI is compared with other girls your age on the CDC growth charts, because bodies are still growing.",
                "info",
                260,
            ).grid(row=3, column=0, sticky="ew", pady=(12, 0))
        return card

    def _save_weight(self) -> None:
        if self.data["profile"]["height_cm"] is None:
            self.weight_field.show_error("Add your height in Settings first.")
            return
        try:
            weight = round(
                validators.parse_weight(
                    self.weight_field.get(), self.settings["weight_unit"]
                ),
                1,
            )
        except ValueError as error:
            self.weight_field.show_error(str(error))
            return
        entries = [e for e in self.data["weights"] if e["date"] != self.today]
        entries.append({"date": self.today, "weight_kg": weight})
        self.data["weights"] = sorted(entries, key=lambda e: e["date"])
        self.data["profile"]["weight_kg"] = weight
        value = bmi.calculate_bmi(weight, self.data["profile"]["height_cm"])
        self.save(f"Saved. BMI {value}")
        self.refresh()

    # Gauge -----------------------------------------------------------------------------------

    def _gauge_card(self, master) -> widgets.Card:
        card = widgets.Card(master, "Where you are", icon="gauge")
        body = card.body
        value = self._current_bmi()
        result = self._assessment(value) if value is not None else None
        rows = (
            result.bands
            if result
            else tuple(
                (upper, color)
                for upper, _, color in bmi.CATEGORY_TABLES[
                    self.settings["bmi_standard"]
                ]
            )
        )
        bands = []
        previous = SCALE_LOW
        for upper, color in rows:
            end = min(upper, SCALE_HIGH)
            bands.append((_fraction(previous), _fraction(end), color))
            previous = end
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        gauge = widgets.GaugeView(
            body, _fraction(value) if value else 0.0, bands, height=200
        )
        gauge.grid(row=0, column=0, rowspan=4, sticky="ew", padx=(0, 20))
        if value is None:
            widgets.label(body, "No BMI yet", "title3").grid(
                row=0, column=1, sticky="w"
            )
            return card
        category = result.category
        color = result.color
        gauge.words = f"BMI gauge. {value}, {category}."
        number = widgets.label(body, "0.0", "number_xl")
        number.grid(row=0, column=1, sticky="w")
        if widgets.page_animates(number):
            anim.count_up(number, value, "{:.1f}")
        else:
            number.configure(text=f"{value:.1f}")
        tone = (
            "good"
            if category == bmi.HEALTHY_WEIGHT
            else (
                "warning"
                if color == "warning"
                else ("info" if color == "fertile" else "danger")
            )
        )
        shown = category
        if result.percentile is not None:
            shown = f"{category}, {result.percentile:.0f}th percentile for age"
        elif bmi.obesity_class(value) and category == bmi.OBESITY:
            shown = f"{category}, class {bmi.obesity_class(value)}"
        widgets.badge(body, shown, tone).grid(row=1, column=1, sticky="w")
        low, high = result.healthy_low_kg, result.healthy_high_kg
        unit = self.settings["weight_unit"]
        text = f"A healthy range for your height is {units.format_weight(low, unit)} to {units.format_weight(high, unit)}."
        if result.percentile is not None:
            text = f"At your age and height, a healthy range is {units.format_weight(low, unit)} to {units.format_weight(high, unit)}."
        widgets.label(body, text, "callout", "text_muted", wraplength=240).grid(
            row=2, column=1, sticky="w", pady=(10, 0)
        )
        widgets.label(
            body,
            "BMI does not measure body fat or muscle; it is a starting point for a conversation with a professional.",
            "footnote",
            "text_muted",
            wraplength=240,
        ).grid(row=3, column=1, sticky="w", pady=(8, 0))
        legend = ctk.CTkFrame(body, fg_color="transparent")
        legend.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))
        for column, ((name, limit), (_, band_color)) in enumerate(
            zip(result.names, result.bands, strict=True)
        ):
            row, column = divmod(column, 2)
            ctk.CTkFrame(
                legend,
                width=10,
                height=10,
                corner_radius=5,
                fg_color=theme.pair(band_color),
            ).grid(row=row, column=column * 2, padx=(0, 5))
            widgets.label(
                legend, f"{name} {limit}".strip(), "footnote", "text_muted"
            ).grid(row=row, column=column * 2 + 1, sticky="w", padx=(0, 14))
        return card

    # History ---------------------------------------------------------------------------------

    def _history_card(self, master) -> widgets.Card:
        entries = sorted(self.data["weights"], key=lambda e: e["date"])[-14:]
        unit = self.settings["weight_unit"]
        card = widgets.Card(
            master, "Weight history", "Your last 14 weigh-ins", icon="activity"
        )
        if len(entries) < 2:
            widgets.label(
                card.body,
                "Log your weight on another day to see your trend.",
                "callout",
                "text_muted",
            ).grid(row=0, column=0, sticky="w")
            return card
        values = [
            round(units.kg_to_lb(e["weight_kg"]) if unit == "lb" else e["weight_kg"], 1)
            for e in entries
        ]
        labels = [f"{e['date']:%b} {e['date'].day}" for e in entries]
        widgets.LineChart(
            card.body,
            values,
            labels,
            min(values) - 1,
            max(values) + 1,
            "primary",
            height=210,
            fmt="{:.1f}",
        ).grid(row=0, column=0, sticky="ew")
        change = values[-1] - values[0]
        direction = "up" if change > 0 else "down"
        text = (
            f"{abs(change):.1f} {unit} {direction} since {entries[0]['date']:%b} {entries[0]['date'].day}."
            if abs(change) >= 0.1
            else "Steady since your first weigh-in here."
        )
        widgets.label(card.body, text, "callout", "text_muted").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        return card
