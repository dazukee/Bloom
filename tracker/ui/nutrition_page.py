"""Nutrition and lifestyle: water, calories, caffeine, alcohol, fruit and vegetables."""

from datetime import datetime
from typing import override

import customtkinter as ctk

from tracker import cycle, daylog, insights, nutrition, profile, validators
from tracker.ui import effects, theme, widgets
from tracker.ui.page import Page


class NutritionPage(Page):
    """Quick logs for drinks and meals, with daily targets."""

    title = "Nutrition"
    subtitle = "Small, steady habits. Tap to log; everything saves straight away."
    banner = [
        {"kind": "apple", "size": 88, "x": 0.66, "y": 0.5, "amp": 6, "hue": 0.98, "accent": (34, 197, 94)},
    ]  # fmt: skip
    banner_hue = 0.38

    @override
    def build(self) -> None:
        if not hasattr(self, "day"):
            self.day = self.today
        widgets.DateSwitcher(self.actions, self.day, self._change_day, self.today).grid(
            row=0, column=0
        )
        self.log = daylog.peek_day(self.data, self.day)
        self.age = insights.age_for(self.data, self.today)
        self.when = "today" if self.day == self.today else "this day"
        grid = widgets.ResponsiveGrid(self.body, min_column=260, max_columns=3)
        grid.grid(row=0, column=0, sticky="ew")
        grid.add(lambda: self._water_card(grid))
        grid.add(lambda: self._meals_card(grid), span=2, shrink=True)
        grid.add(lambda: self._caffeine_card(grid))
        grid.add(lambda: self._lifestyle_card(grid), span=2)
        grid.add(lambda: self._needs_card(grid), span=3)

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
            effects.celebrate(self.app)
        self.built_version = self.app.data_version  # the card already shows this

    # Meals and calories -------------------------------------------------------------------

    def _meals_card(self, master) -> widgets.Card:
        meals = self.log.get("meals", [])
        eaten = nutrition.kcal_eaten(meals)
        target = profile.calorie_target(self.data, self.day)
        method = "growth-aware estimate" if self.age and self.age < 19 else "estimate"
        subtitle = f"{eaten:,} kcal eaten" + (
            f" of about {target:,} kcal a day ({method})" if target else ""
        )
        weight = profile.current_weight(self.data)
        if weight:
            protein = nutrition.protein_eaten(meals)
            subtitle += f"  ·  {protein} of {nutrition.protein_target_g(weight, self.age)} g protein"
        card = widgets.Card(master, "Meals & calories", subtitle, icon="leaf")
        body = card.body
        if target:
            widgets.progress_bar(body, eaten / target, "primary", 10).grid(
                row=0, column=0, sticky="ew", pady=(0, 14)
            )
        form = ctk.CTkFrame(body, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(0, weight=3)
        form.columnconfigure(1, weight=2)
        self.meal_name = widgets.Field(form, "Meal", "e.g. Chicken adobo")
        self.meal_name.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.meal_kcal = widgets.Field(
            form, "Calories", "450", unit="kcal", on_enter=self._add_meal
        )
        self.meal_kcal.grid(row=0, column=1, sticky="ew")
        widgets.button(form, "Add", self._add_meal, icon="plus", width=84).grid(
            row=0, column=2, sticky="s", padx=(10, 0), pady=(0, 0)
        )
        self.meal_name.entry.bind(
            "<Return>", lambda _e: self.meal_kcal.focus(), add="+"
        )
        foods = widgets.ResponsiveGrid(
            body, min_column=158, max_columns=5, gap=6, nested=True
        )
        foods.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for food, (kcal, protein) in nutrition.COMMON_FOODS.items():
            foods.add(
                widgets.small_button(
                    foods,
                    f"{food}: {kcal}",
                    lambda f=food, k=kcal, p=protein: self._log_meal(f, k, p),
                )
            )
        for row, meal in enumerate(meals, start=3):
            line = ctk.CTkFrame(
                body, fg_color=theme.pair("surface_alt"), corner_radius=12
            )
            line.grid(row=row, column=0, sticky="ew", pady=(10 if row == 3 else 4, 0))
            line.columnconfigure(0, weight=1)
            widgets.label(line, meal["name"], "body", wraplength=340).grid(
                row=0, column=0, sticky="w", padx=14, pady=10
            )
            widgets.label(line, f"{meal['kcal']} kcal", "headline").grid(
                row=0, column=1, padx=8
            )
            widgets.icon_button(
                line,
                "trash",
                lambda i=row - 3: self._remove_meal(i),
                size=32,
                kind="ghost",
                tooltip="Delete",
            ).grid(row=0, column=2, padx=(0, 6))
        widgets.label(
            body,
            "Food values are typical servings (USDA); home-cooked dishes vary.",
            "footnote",
            "text_muted",
            wraplength=560,
        ).grid(row=len(meals) + 3, column=0, sticky="w", pady=(8, 0))
        return card

    def _log_meal(self, name: str, kcal: int, protein: int | None = None) -> None:
        meal = {"name": name[:60], "kcal": kcal}
        if protein is not None:
            meal["protein"] = protein
        daylog.get_day(self.data, self.day).setdefault("meals", []).append(meal)
        self.save(f"{name[:30]} added")
        self.refresh()

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
        self._log_meal(name, kcal)

    def _remove_meal(self, index: int) -> None:
        meals = list(daylog.peek_day(self.data, self.day).get("meals", []))
        del meals[index]
        daylog.set_value(self.data, self.day, "meals", meals)
        self.save("Meal deleted")
        self.refresh()

    # Caffeine ----------------------------------------------------------------------------

    def _caffeine_card(self, master) -> widgets.Card:
        total = self.log.get("caffeine_mg", 0)
        card = widgets.Card(
            master, "Caffeine", f"{total} mg {self.when}", icon="coffee"
        )
        body = card.body
        conceiving = profile.has_focus(self.data["profile"], "conceive")
        limit = nutrition.caffeine_limit(self.age, conceiving)
        widgets.progress_bar(
            body, total / limit, "warning" if total > limit else "primary", 10
        ).grid(row=0, column=0, sticky="ew")
        text, tone = nutrition.caffeine_note(total, conceiving, self.age)
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
            drinks.columnconfigure(index % 2, weight=1, uniform="drinks")
            widgets.small_button(
                drinks, f"{drink} +{mg}", lambda m=mg: self._add_caffeine(m)
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
        text, tone = nutrition.alcohol_note(drinks, self.age)
        self.alcohol_note = widgets.label(
            body,
            text,
            "footnote",
            "warning" if tone == "warning" else "text_muted",
            wraplength=260,
        )
        self.alcohol_note.grid(row=2, column=1, sticky="w")
        return card

    def _set(self, key: str, value: int) -> None:
        daylog.set_value(self.data, self.day, key, value or None)
        self.save()
        self.built_version = self.app.data_version  # the steppers already show this
        if key == "alcohol":
            text, tone = nutrition.alcohol_note(value, self.age)
            self.alcohol_note.configure(
                text=text,
                text_color=theme.pair("warning" if tone == "warning" else "text_muted"),
            )

    # What the body needs ----------------------------------------------------------------

    def _needs_card(self, master) -> widgets.Card:
        card = widgets.Card(
            master,
            "What your body needs each day",
            "Recommended amounts for your age, with foods that have them",
            icon="heart",
        )
        body = card.body
        needs = nutrition.daily_nutrients(self.age)
        for column, (name, (amount, foods)) in enumerate(needs.items()):
            body.columnconfigure(column, weight=1, uniform="needs")
            box = ctk.CTkFrame(
                body, fg_color=theme.pair("surface_alt"), corner_radius=14
            )
            box.grid(row=0, column=column, sticky="nsew", padx=4)
            box.columnconfigure(0, weight=1)
            widgets.label(box, name, "label", "text_muted").grid(
                row=0, column=0, sticky="w", padx=14, pady=(10, 0)
            )
            widgets.label(box, amount, "number_sm", "primary_text").grid(
                row=1, column=0, sticky="w", padx=14
            )
            widgets.label(box, foods, "footnote", "text_muted", wraplength=230).grid(
                row=2, column=0, sticky="w", padx=14, pady=(2, 12)
            )
        phase = insights.phase_today(self.data, self.today)
        if phase == cycle.MENSTRUAL:
            widgets.note(
                body,
                "On your period, iron matters most: you lose some with the blood. "
                "Vitamin C, as in calamansi or guava, helps your body absorb it.",
                "info",
                760,
            ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0), padx=4)
        elif profile.has_focus(self.data["profile"], "conceive"):
            widgets.note(
                body,
                "Trying to conceive? The CDC advises 400 mcg of folic acid every day, "
                "starting at least a month before pregnancy.",
                "info",
                760,
            ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0), padx=4)
        return card
