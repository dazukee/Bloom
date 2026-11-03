"""Nutrition and lifestyle: water, calories, caffeine, alcohol, fruit and vegetables."""

from datetime import datetime
from typing import override

import customtkinter as ctk

from tracker import daylog, nutrition, profile, validators
from tracker.ui import theme, widgets
from tracker.ui.page import Page


class NutritionPage(Page):
    """Quick logs for drinks and meals, with daily targets."""

    title = "Nutrition"
    subtitle = "Small, steady habits. Tap to log; everything saves straight away."

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
        grid.add(lambda: self._water_card(grid))
        grid.add(lambda: self._meals_card(grid), span=2, shrink=True)
        grid.add(lambda: self._caffeine_card(grid))
        grid.add(lambda: self._lifestyle_card(grid), span=2)

    def _change_day(self, day) -> None:
        self.day = day
        self.refresh()

    # Water ------------------------------------------------------------------------------

    def _water_card(self, master) -> widgets.Card:
        goal = self.data["goals"]["water_ml"]
        card = widgets.Card(master, "Water", f"Goal {goal:,} ml", icon="cup")
        body = card.body
        body.columnconfigure(1, weight=1)
        water = self.log.get("water_ml", 0)
        self.glass = widgets.WaterGlass(body, water / goal)
        self.glass.grid(row=0, column=0, rowspan=2, padx=(0, 16))
        self.water_label = widgets.label(body, f"{water:,} ml", "number")
        self.water_label.grid(row=0, column=1, sticky="sw")
        self.water_hint = widgets.label(
            body,
            self._water_hint(water, goal),
            "footnote",
            "text_muted",
            wraplength=170,
        )
        self.water_hint.grid(row=1, column=1, sticky="nw")
        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        for column, amount in enumerate((250, 500, -250)):
            buttons.columnconfigure(column, weight=1)
            text = f"+{amount}" if amount > 0 else f"{amount}"
            widgets.button(
                buttons,
                f"{text} ml",
                lambda a=amount: self._add_water(a),
                kind="secondary" if amount > 0 else "plain",
            ).grid(row=0, column=column, sticky="ew", padx=3)
        return card

    def _water_hint(self, water: int, goal: int) -> str:
        if water >= goal:
            return "Goal reached for today."
        if self.day == self.today:
            due = nutrition.expected_water_by_now(goal, datetime.now())
            if water < due:
                return f"About {due:,} ml is due by now. A glass is {nutrition.GLASS_ML} ml."
        return f"{goal - water:,} ml to go."

    def _add_water(self, amount: int) -> None:
        goal = self.data["goals"]["water_ml"]
        total = int(daylog.add_amount(self.data, self.day, "water_ml", amount))
        self.save()
        self.glass.set_fraction(total / goal)
        self.water_label.configure(text=f"{total:,} ml")
        self.water_hint.configure(text=self._water_hint(total, goal))
        if amount > 0 and total >= goal > total - amount:
            widgets.toast(self.app, "Water goal reached. Well done!")

    # Meals and calories -------------------------------------------------------------------

    def _meals_card(self, master) -> widgets.Card:
        meals = self.log.get("meals", [])
        eaten = nutrition.kcal_eaten(meals)
        target = profile.calorie_target(self.data, self.day)
        subtitle = f"{eaten:,} kcal eaten" + (
            f" of about {target:,} kcal (Mifflin-St Jeor estimate)" if target else ""
        )
        card = widgets.Card(master, "Meals & calories", subtitle, icon="leaf")
        body = card.body
        if target:
            widgets.progress_bar(body, eaten / target, "primary", 10).grid(
                row=0, column=0, sticky="ew", pady=(0, 14)
            )
        form = ctk.CTkFrame(body, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)
        self.meal_name = widgets.Field(
            form, "Meal or snack", "e.g. Chicken adobo with rice"
        )
        self.meal_name.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.meal_kcal = widgets.Field(
            form, "Calories", "450", unit="kcal", width=90, on_enter=self._add_meal
        )
        self.meal_kcal.grid(row=0, column=1, sticky="ew")
        widgets.button(form, "Add", self._add_meal, icon="plus", width=90).grid(
            row=0, column=2, sticky="s", padx=(10, 0), pady=(0, 0)
        )
        for row, meal in enumerate(meals, start=2):
            line = ctk.CTkFrame(
                body, fg_color=theme.pair("surface_alt"), corner_radius=12
            )
            line.grid(row=row, column=0, sticky="ew", pady=(10 if row == 2 else 4, 0))
            line.columnconfigure(0, weight=1)
            widgets.label(line, meal["name"], "body").grid(
                row=0, column=0, sticky="w", padx=14, pady=10
            )
            widgets.label(line, f"{meal['kcal']} kcal", "headline").grid(
                row=0, column=1, padx=8
            )
            widgets.icon_button(
                line,
                "trash",
                lambda i=row - 2: self._remove_meal(i),
                size=32,
                kind="ghost",
                tooltip="Delete",
            ).grid(row=0, column=2, padx=(0, 6))
        return card

    def _add_meal(self) -> None:
        name = self.meal_name.get().strip()
        if not name:
            self.meal_name.show_error("Enter what you ate.")
            return
        self.meal_name.clear_error()
        try:
            kcal = validators.parse_number(
                self.meal_kcal.get(), "Calories", 1, 5000, "kcal", "450", whole=True
            )
        except ValueError as error:
            self.meal_kcal.show_error(str(error))
            return
        daylog.get_day(self.data, self.day).setdefault("meals", []).append(
            {"name": name[:60], "kcal": kcal}
        )
        self.save(f"{name[:30]} added")
        self.refresh()

    def _remove_meal(self, index: int) -> None:
        meals = list(daylog.peek_day(self.data, self.day).get("meals", []))
        del meals[index]
        daylog.set_value(self.data, self.day, "meals", meals)
        self.save("Meal deleted")
        self.refresh()

    # Caffeine ----------------------------------------------------------------------------

    def _caffeine_card(self, master) -> widgets.Card:
        total = self.log.get("caffeine_mg", 0)
        card = widgets.Card(master, "Caffeine", f"{total} mg today", icon="coffee")
        body = card.body
        widgets.progress_bar(
            body,
            total / nutrition.CAFFEINE_LIMIT_MG,
            "warning" if total > nutrition.CAFFEINE_LIMIT_MG else "primary",
            10,
        ).grid(row=0, column=0, sticky="ew")
        text, tone = nutrition.caffeine_note(
            total, profile.has_focus(self.data["profile"], "conceive")
        )
        widgets.label(
            body,
            text,
            "footnote",
            "warning" if tone == "warning" else "text_muted",
            wraplength=260,
        ).grid(row=1, column=0, sticky="w", pady=(6, 12))
        drinks = ctk.CTkFrame(body, fg_color="transparent")
        drinks.grid(row=2, column=0, sticky="ew")
        for index, (drink, mg) in enumerate(nutrition.CAFFEINE_DRINKS.items()):
            drinks.columnconfigure(index % 2, weight=1)
            widgets.button(
                drinks,
                f"{drink} +{mg}",
                lambda m=mg: self._add_caffeine(m),
                kind="secondary",
                height=36,
            ).grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
        if total:
            widgets.button(
                body,
                "Reset",
                lambda: self._add_caffeine(-total),
                kind="ghost",
                height=32,
            ).grid(row=3, column=0, sticky="e", pady=(6, 0))
        return card

    def _add_caffeine(self, amount: int) -> None:
        daylog.add_amount(self.data, self.day, "caffeine_mg", amount)
        self.save("Caffeine logged" if amount > 0 else "Caffeine reset")
        self.refresh()

    # Lifestyle -----------------------------------------------------------------------------

    def _lifestyle_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master,
            "Lifestyle",
            "WHO suggests 5 portions of fruit and vegetables a day",
            icon="sparkle",
        )
        body = card.body
        body.columnconfigure((0, 1), weight=1, uniform="life")
        produce = self.log.get("fruit_veg", 0)
        drinks = self.log.get("alcohol", 0)
        widgets.label(body, "Fruit & vegetable portions", "label").grid(
            row=0, column=0, sticky="w"
        )
        widgets.Stepper(
            body,
            produce,
            1,
            0,
            20,
            unit=f"/ {nutrition.FRUIT_VEG_GOAL}",
            on_change=lambda v: self._set("fruit_veg", int(v)),
        ).grid(row=1, column=0, sticky="w", pady=(6, 4))
        widgets.label(
            body, "One portion is about a handful (80 g).", "footnote", "text_muted"
        ).grid(row=2, column=0, sticky="w")
        widgets.label(body, "Alcoholic drinks", "label").grid(
            row=0, column=1, sticky="w"
        )
        widgets.Stepper(
            body, drinks, 1, 0, 20, on_change=lambda v: self._set("alcohol", int(v))
        ).grid(row=1, column=1, sticky="w", pady=(6, 4))
        text, tone = nutrition.alcohol_note(drinks)
        widgets.label(
            body,
            text,
            "footnote",
            "warning" if tone == "warning" else "text_muted",
            wraplength=260,
        ).grid(row=2, column=1, sticky="w")
        return card

    def _set(self, key: str, value: int) -> None:
        daylog.set_value(self.data, self.day, key, value or None)
        self.save()
