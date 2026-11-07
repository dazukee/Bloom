"""Settings: profile, goals, look, accessibility, sound, account and about."""

import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import override

import customtkinter as ctk

from tracker import auth, profile, report, sound, storage, units, validators
from tracker.ui import anim, effects, sfx, speech, theme, widgets
from tracker.ui.page import Page

TABS = (
    "Profile",
    "Goals",
    "Appearance",
    "Accessibility",
    "Sound",
    "Preferences",
    "Account",
    "About",
)
TEXT_SIZES = {
    "Small": "small",
    "Default": "default",
    "Large": "large",
    "Extra large": "xlarge",
}
TRANSITIONS = {"Rise": "rise", "Slide": "slide", "Fade": "fade", "None": "none"}
START_PAGES = {"Today": "home", "My Garden": "garden", "Cycle": "cycle"}
READABLE_FONTS = ("atkinson", "lexend", "opendyslexic")
LOOK_DEFAULTS = (
    "appearance accent font text_size transition page_colors sparkles card_glow "
    "confetti sound_on sound_volume sound_pack sound_clicks sound_alerts "
    "sound_celebrate high_contrast bold_text color_vision calendar_symbols "
    "big_targets simple_view long_messages speak_messages speak_focus reduce_motion"
).split()
# name: (who it helps, the settings it sets)
ACCESS_PRESETS = {
    "Low vision": (
        "Extra large text, high contrast and a clearer font",
        {
            "text_size": "xlarge",
            "high_contrast": True,
            "bold_text": True,
            "font": "atkinson",
            "big_targets": True,
            "long_messages": True,
            "calendar_symbols": True,
        },
    ),
    "Dyslexia": (
        "A dyslexia-friendly font, larger text and fewer distractions",
        {
            "font": "opendyslexic",
            "text_size": "large",
            "sparkles": False,
            "long_messages": True,
        },
    ),
    "Motion sensitive": (
        "No animation, confetti or sparkles",
        {
            "reduce_motion": True,
            "confetti": False,
            "sparkles": False,
            "transition": "none",
            "simple_view": True,
        },
    ),
    "Colour blind": (
        "Red-green safe colours, with letters on the calendar",
        {"color_vision": "red-green", "calendar_symbols": True},
    ),
    "Screen reading": (
        "Reads messages and what the keyboard reaches",
        {"speak_messages": True, "speak_focus": True, "long_messages": True},
    ),
}
APPEARANCE = {"System": "system", "Light": "light", "Dark": "dark"}
SOURCES = (
    "CDC: Adult BMI categories; 2000 BMI-for-age growth charts (under 20)",
    "WHO Western Pacific Region (2000): Asia-Pacific BMI cut-offs",
    "Office on Women's Health: Your menstrual cycle; Trying to conceive (calendar method)",
    "NHS: Fertility in the menstrual cycle; oxygen readings",
    "FIGO 2018: Normal cycle length, regularity and period length",
    "ACOG Committee Opinion 651: Cycles in girls and teens",
    "Fehring et al. (2006), Marquette University: 1,665 cycles used to test predictions",
    "Sensiplan: The 3-over-6 temperature rule",
    "CDC / ACC-AHA: Blood pressure categories; American Heart Association: low blood pressure",
    "CDC: How much sleep do I need?",
    "WHO: Physical activity fact sheet",
    "FDA, ACOG and American Academy of Pediatrics: Caffeine limits",
    "US Dietary Guidelines 2025-2030: Alcohol",
    "NIH Office of Dietary Supplements: Iron, calcium and folate needs",
    "USDA FoodData Central: Food calories and protein",
    "Compendium of Physical Activities: MET values",
    "Mifflin-St Jeor equation (1990); Institute of Medicine (2005) energy equations",
    "OWASP Password Storage Cheat Sheet",
    "WCAG 2.2: Contrast and keyboard access",
    "Fonts: Poppins, Nunito, Quicksand, Outfit, Figtree, Fraunces, DM Sans, Atkinson Hyperlegible, Lexend, OpenDyslexic (SIL Open Font License)",
)


class SettingsPage(Page):
    """Everything set during onboarding can be changed here."""

    title = "Settings"
    subtitle = "Your profile, goals, look, accessibility and account."
    banner = [
        {"kind": "gear", "size": 90, "x": 0.84, "y": 0.5, "amp": 5},
        {"kind": "gear", "size": 46, "x": 0.72, "y": 0.34, "amp": 4, "phase": 1.4},
    ]

    @override
    def build(self) -> None:
        tab = getattr(self.app, "settings_tab", "Profile")
        widgets.TabBar(self.body, list(TABS), tab, self._show_tab).grid(
            row=0, column=0, sticky="ew", pady=(0, theme.GUTTER - 6)
        )
        self.holder = ctk.CTkFrame(self.body, fg_color="transparent")
        self.holder.grid(row=1, column=0, sticky="ew")
        self.holder.columnconfigure(0, weight=1)
        self._show_tab(tab, animate=False)

    def _show_tab(self, tab: str, animate: bool = True) -> None:
        self.app.settings_tab = tab
        for child in self.holder.winfo_children():
            child.destroy()
        content = widgets.ResponsiveGrid(self.holder, min_column=360, max_columns=2)
        content.grid(row=0, column=0, sticky="ew")
        getattr(self, f"_tab_{tab.lower()}")(content)
        if animate:
            anim.animate(
                content,
                theme.BASE + 60,
                lambda t: content.grid_configure(padx=(round(24 * (1 - t)), 0)),
                key="settings-tab",
            )

    # Profile ---------------------------------------------------------------------------

    def _tab_profile(self, grid) -> None:
        p = self.data["profile"]
        card = widgets.Card(
            grid, "Profile", "Used to personalise your goals and guidance", icon="user"
        )
        body = card.body
        body.columnconfigure((0, 1), weight=1, uniform="profile")
        self.name_field = widgets.Field(body, "Name", value=p["display_name"])
        self.name_field.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        born = p["birth_date"].isoformat() if p["birth_date"] else ""
        self.birth_field = widgets.Field(body, "Birth date", "YYYY-MM-DD", value=born)
        self.birth_field.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))
        self.height_unit = self.settings["height_unit"]
        height = p["height_cm"]
        if self.height_unit == "ft":
            feet, inches = units.cm_to_ft_in(height) if height else ("", "")
            self.feet_field = widgets.Field(body, "Height (feet)", value=str(feet))
            self.feet_field.grid(
                row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12)
            )
            self.inch_field = widgets.Field(
                body, "Inches", value=f"{inches:g}" if height else ""
            )
            self.inch_field.grid(
                row=1, column=1, sticky="ew", padx=(8, 0), pady=(0, 12)
            )
        else:
            self.height_field = widgets.Field(
                body, "Height", unit="cm", value=f"{height:g}" if height else ""
            )
            self.height_field.grid(
                row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12)
            )
        levels = {label: key for key, (label, _, _) in profile.ACTIVITY_LEVELS.items()}
        widgets.label(body, "Activity level", "label").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )
        self.level_menu = widgets.option_menu(
            body,
            list(levels),
            profile.ACTIVITY_LEVELS[p["activity_level"]][0],
            width=210,
        )
        self.level_menu.grid(row=3, column=0, sticky="w", pady=(0, 12))
        self.levels = levels
        self.message = widgets.label(body, "", "callout", "danger")
        self.message.grid(row=4, column=0, columnspan=2, sticky="w")
        widgets.button(body, "Save Profile", self._save_profile, icon="check").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        grid.add(card)

        reasons = widgets.Card(
            grid,
            "Why you use Bloom",
            "Tick all that apply; tap again to untick. Saves straight away.",
            icon="sparkle",
        )
        widgets.OptionList(
            reasons.body,
            profile.FOCUS_OPTIONS,
            profile.focus_list(p),
            self._save_focus,
            toggle=profile.toggle_focus,
        ).grid(row=0, column=0, sticky="ew")
        grid.add(reasons)

        cycle_card = widgets.Card(
            grid,
            "Cycle tracking",
            "Your usual lengths are used until you log enough periods",
            icon="drop",
        )
        cbody = cycle_card.body
        self.track_switch = widgets.switch(
            cbody, "Track my menstrual cycle", p["track_cycle"]
        )
        self.track_switch.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        widgets.label(cbody, "Usual cycle length", "label").grid(
            row=1, column=0, sticky="w"
        )
        self.cycle_stepper = widgets.Stepper(
            cbody,
            p["cycle_length"],
            1,
            profile.MIN_CYCLE_LENGTH,
            profile.MAX_CYCLE_LENGTH,
            unit="days",
        )
        self.cycle_stepper.grid(row=2, column=0, sticky="w", pady=(6, 12))
        widgets.label(cbody, "Period length", "label").grid(row=3, column=0, sticky="w")
        self.period_stepper = widgets.Stepper(
            cbody,
            p["period_length"],
            1,
            profile.MIN_PERIOD_LENGTH,
            profile.MAX_PERIOD_LENGTH,
            unit="days",
        )
        self.period_stepper.grid(row=4, column=0, sticky="w", pady=(6, 12))
        widgets.button(
            cbody,
            "Save Cycle Settings",
            self._save_cycle,
            kind="secondary",
            icon="check",
        ).grid(row=5, column=0, columnspan=2, sticky="w")
        grid.add(cycle_card)

    def _read_height(self) -> float:
        if self.height_unit == "ft":
            return validators.parse_feet_inches(
                self.feet_field.get(), self.inch_field.get()
            )
        return validators.parse_height(self.height_field.get())

    def _save_profile(self) -> None:
        p = self.data["profile"]
        try:
            name = validators.parse_display_name(self.name_field.get())
            birth = validators.parse_birth_date(self.birth_field.get(), self.today)
            height = round(self._read_height(), 1)
        except ValueError as error:
            self.message.configure(text=str(error))
            return
        p.update(
            display_name=name,
            birth_date=birth,
            height_cm=height,
            activity_level=self.levels[self.level_menu.get()],
        )
        self.app.save_user_data()
        self.app.enter_main("settings")
        widgets.toast(self.app, "Profile saved")

    def _save_focus(self, keys: list[str]) -> None:
        self.data["profile"]["focus"] = keys
        names = ", ".join(profile.FOCUS_OPTIONS[key][0] for key in keys)
        self.save(f"Saved: {names or 'no reasons ticked'}")

    def _save_cycle(self) -> None:
        p = self.data["profile"]
        p.update(
            track_cycle=bool(self.track_switch.get()),
            cycle_length=int(self.cycle_stepper.get()),
            period_length=int(self.period_stepper.get()),
        )
        self.app.save_user_data()
        self.app.enter_main("settings")
        widgets.toast(self.app, "Cycle settings saved")

    # Goals --------------------------------------------------------------------------------

    def _tab_goals(self, grid) -> None:
        goals = self.data["goals"]
        card = widgets.Card(
            grid,
            "Daily goals",
            "Reachable goals keep you going. Raise them as habits stick.",
            icon="flame",
        )
        body = card.body
        rows = (
            ("Steps", "steps", 500, 1000, 30000, "{:,.0f}", ""),
            ("Water", "water_ml", 250, 1000, 4000, "{:,.0f}", "ml"),
            ("Sleep", "sleep_h", 0.5, 5, 11, "{:g}", "h"),
            ("Active minutes", "active_min", 5, 10, 180, "{:g}", "min"),
        )
        self.goal_steppers = {}
        for row, (title, key, step, low, high, fmt, unit) in enumerate(rows):
            widgets.label(body, title, "body").grid(
                row=row, column=0, sticky="w", pady=6
            )
            stepper = widgets.Stepper(
                body, goals[key], step, low, high, fmt=fmt, unit=unit, value_width=108
            )
            stepper.grid(row=row, column=1, sticky="e", pady=6)
            self.goal_steppers[key] = stepper
        body.columnconfigure(0, weight=1)
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(12, 0))
        widgets.button(actions, "Save Goals", self._save_goals, icon="check").grid(
            row=0, column=0, padx=(0, 8)
        )
        widgets.button(
            actions, "Suggest a Water Goal", self._suggest_water, kind="plain"
        ).grid(row=0, column=1)
        grid.add(card)

    def _suggest_water(self) -> None:
        suggestion = profile.suggested_water_ml(profile.current_weight(self.data))
        self.goal_steppers["water_ml"].set(suggestion)
        widgets.toast(self.app, f"Suggested {suggestion:,} ml from your weight", "info")

    def _save_goals(self) -> None:
        for key, stepper in self.goal_steppers.items():
            value = stepper.get()
            self.data["goals"][key] = value if key == "sleep_h" else int(value)
        self.save("Goals saved")

    # Appearance -----------------------------------------------------------------------------

    def _tab_appearance(self, grid) -> None:
        s = self.settings
        card = widgets.Card(grid, "Theme", "Light or dark, and your colour", icon="sun")
        current = next(
            name for name, key in APPEARANCE.items() if key == s["appearance"]
        )
        widgets.segmented(
            card.body, list(APPEARANCE), current, command=self._set_appearance
        ).grid(row=0, column=0, sticky="w")
        swatches = ctk.CTkFrame(card.body, fg_color="transparent")
        swatches.grid(row=1, column=0, sticky="w", pady=(16, 8))
        for index, (key, (name, _)) in enumerate(theme.ACCENTS.items()):
            shade = theme.swatch_color(key)
            chosen = s["accent"] == key
            swatch = ctk.CTkButton(
                swatches,
                text="✓" if chosen else "",
                width=38,
                height=38,
                corner_radius=19,
                fg_color=shade,
                hover_color=shade,
                border_width=3 if chosen else 0,
                border_color=theme.pair("text"),
                font=theme.font("headline"),
                text_color="#FFFFFF",
                command=sfx.with_sound(
                    lambda k=key: self._restyle("accent", k), "toggle"
                ),
            )
            swatch.grid(row=0, column=index, padx=(0, 8))
            widgets.Tooltip(swatch, name)
            widgets.keyboard(swatch, swatch.invoke, f"{name} colour")
        row = 2
        if self.data["profile"]["track_cycle"]:
            follow = widgets.switch(
                card.body,
                "Follow my cycle",
                s["accent"] == theme.FOLLOW_CYCLE,
                command=lambda: self._restyle(
                    "accent", theme.FOLLOW_CYCLE if follow.get() else "bloom"
                ),
            )
            follow.grid(row=row, column=0, sticky="w", pady=(8, 0))
            widgets.label(
                card.body,
                "The colour changes with your phase: rose, forest, coral, then purple.",
                "footnote",
                "text_muted",
                wraplength=380,
            ).grid(row=row + 1, column=0, sticky="w", pady=(4, 0))
            row += 2
        colorful = widgets.switch(
            card.body,
            "A different colour for each page",
            s["page_colors"],
            command=lambda: self._restyle("page_colors", bool(colorful.get())),
        )
        colorful.grid(row=row, column=0, sticky="w", pady=(10, 0))
        grid.add(card)

        fonts = widgets.Card(grid, "Font", "Applies to the whole app", icon="edit")
        for row, (key, (name, display, _, about)) in enumerate(
            theme.FONT_CHOICES.items()
        ):
            if key not in READABLE_FONTS:
                self._font_row(fonts.body, row, key, name, display, about)
        grid.add(fonts)

        fx = widgets.Card(grid, "Motion and effects", icon="sparkle")
        widgets.label(fx.body, "Page transition", "label").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        current = next(n for n, v in TRANSITIONS.items() if v == s["transition"])
        widgets.segmented(
            fx.body,
            list(TRANSITIONS),
            current,
            command=lambda n: self._set_effect("transition", TRANSITIONS[n]),
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))
        switches = (
            ("Sparkles on banners", "sparkles"),
            ("Glow on the card under the mouse", "card_glow"),
            ("Confetti when you reach a goal", "confetti"),
        )
        for row, (text, key) in enumerate(switches, start=2):
            self._effect_switch(fx.body, text, key).grid(
                row=row, column=0, sticky="w", pady=4
            )
        widgets.button(
            fx.body,
            "Preview Confetti",
            lambda: effects.confetti(self.app),
            kind="plain",
        ).grid(row=5, column=0, sticky="w", pady=(10, 0))
        grid.add(fx)

    def _font_row(self, master, row, key, name, display, about) -> None:
        chosen = self.settings["font"] == key
        choice = ctk.CTkButton(
            master,
            text=f"{'✓  ' if chosen else ''}{name}",
            anchor="w",
            height=theme.control_height(),
            corner_radius=theme.RADIUS_CONTROL,
            font=ctk.CTkFont(
                family=display,
                size=round(14 * theme.FONT_SIZE_FACTOR.get(key, 1.0)),
                weight="bold",
            ),
            fg_color=theme.pair("primary_soft" if chosen else "surface_alt"),
            hover_color=theme.pair("primary_soft_hover"),
            text_color=theme.pair("primary_text" if chosen else "text"),
            command=sfx.with_sound(lambda k=key: self._restyle("font", k), "toggle"),
        )
        choice.grid(row=row, column=0, sticky="ew", pady=3)
        widgets.label(master, about, "footnote", "text_muted", wraplength=170).grid(
            row=row, column=1, sticky="w", padx=(10, 0)
        )
        widgets.keyboard(choice, choice.invoke, f"{name} font. {about}")

    def _effect_switch(self, master, text: str, key: str):
        widget = widgets.switch(
            master,
            text,
            self.settings[key],
            command=lambda: self._set_effect(key, bool(widget.get())),
        )
        return widget

    def _set_effect(self, key: str, value) -> None:
        self.settings[key] = value
        self.app.save_user_data()
        self.app.apply_settings(rebuild=key in ("sparkles", "reduce_motion"))

    def _restyle(self, key: str, value) -> None:
        """Save a look setting and rebuild the app so everything shows it."""
        self.settings[key] = value
        self.app.save_user_data()
        self.app.apply_settings(rebuild=True)

    # Accessibility --------------------------------------------------------------------------

    def _tab_accessibility(self, grid) -> None:
        s = self.settings
        quick = widgets.Card(
            grid,
            "Quick setups",
            "One click to set several options together. You can fine-tune them below.",
            icon="eye_access",
        )
        box = ctk.CTkFrame(quick.body, fg_color="transparent")
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)
        for row, (name, (about, _)) in enumerate(ACCESS_PRESETS.items()):
            widgets.button(
                box,
                name,
                lambda n=name: self._apply_preset(n),
                kind="secondary",
                width=150,
            ).grid(row=row, column=0, sticky="w", pady=3)
            widgets.label(box, about, "footnote", "text_muted", wraplength=270).grid(
                row=row, column=1, sticky="w", padx=(10, 0)
            )
        grid.add(quick)

        see = widgets.Card(grid, "Seeing", icon="eye")
        body = see.body
        widgets.label(body, "Text and control size", "label").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        current = next(n for n, v in TEXT_SIZES.items() if v == s["text_size"])
        widgets.segmented(
            body,
            list(TEXT_SIZES),
            current,
            command=lambda n: self._restyle("text_size", TEXT_SIZES[n]),
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))
        widgets.label(body, "Colour vision", "label").grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )
        visions = {info[0]: key for key, info in theme.COLOR_VISION.items()}
        current = next(n for n, v in visions.items() if v == s["color_vision"])
        widgets.segmented(
            body,
            list(visions),
            current,
            command=lambda n: self._restyle("color_vision", visions[n]),
        ).grid(row=3, column=0, sticky="w", pady=(0, 10))
        options = (
            ("High contrast", "high_contrast", "Pure black and white, thicker borders"),
            ("Bold text", "bold_text", "Every word in the heavier weight"),
            ("Letters on the calendar", "calendar_symbols", "P, E, F and O, so colour is not the only cue"),
            ("Larger click targets", "big_targets", "Taller buttons and boxes"),
        )  # fmt: skip
        self._access_switches(body, options, 4)
        grid.add(see)

        fonts = widgets.Card(
            grid,
            "Easier-to-read fonts",
            "Designed with readers in mind",
            icon="journal",
        )
        for row, key in enumerate(READABLE_FONTS):
            name, display, _, about = theme.FONT_CHOICES[key]
            self._font_row(fonts.body, row, key, name, display, about)
        grid.add(fonts)

        calm = widgets.Card(grid, "Motion and focus", icon="moon")
        options = (
            ("Reduce motion", "reduce_motion", "Turns off slides, counting numbers and floating art"),
            ("Hide decorative art", "simple_view", "Plain titles and no 3D objects, for fewer distractions"),
            ("Keep messages on screen longer", "long_messages", "About 8 seconds instead of 3"),
        )  # fmt: skip
        self._access_switches(calm.body, options, 0)
        grid.add(calm)

        hear = widgets.Card(
            grid,
            "Reading aloud",
            "Uses the voice built into your computer" if speech.available() else "Not available on this computer",
            icon="speaker",
        )  # fmt: skip
        options = (
            ("Read messages aloud", "speak_messages", "Confirmations, warnings and errors"),
            ("Read what the keyboard reaches", "speak_focus", "Says each control as you Tab to it"),
        )  # fmt: skip
        self._access_switches(hear.body, options, 0)
        actions = ctk.CTkFrame(hear.body, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="w", pady=(12, 0))
        widgets.button(
            actions, "Read This Page (F2)", self.app.read_page, kind="secondary", icon="speaker"
        ).grid(row=0, column=0, padx=(0, 8))  # fmt: skip
        widgets.button(actions, "Stop", speech.stop, kind="plain", width=70).grid(
            row=0, column=1
        )
        grid.add(hear)

        keys = widgets.Card(
            grid,
            "Using the keyboard",
            "Everything works without a mouse",
            icon="keyboard",
        )
        widgets.label(
            keys.body,
            "Tab moves between controls and a bright ring shows where you are. Enter or "
            "Space uses a control, and Ctrl+K finds anything.",
            "callout",
            "text_muted",
            wraplength=380,
        ).grid(row=0, column=0, sticky="w")
        widgets.button(
            keys.body, "See All Shortcuts (F1)", self.app.show_help, kind="secondary", icon="keyboard"
        ).grid(row=1, column=0, sticky="w", pady=(12, 0))  # fmt: skip
        grid.add(keys)

    def _access_switches(self, master, options, row: int) -> None:
        for text, key, about in options:
            widget = self._restyle_switch(master, text, key)
            widget.grid(row=row, column=0, sticky="w", pady=(6, 0))
            widgets.label(master, about, "footnote", "text_muted", wraplength=360).grid(
                row=row + 1, column=0, sticky="w", padx=(52, 0)
            )
            row += 2

    def _restyle_switch(self, master, text: str, key: str):
        widget = widgets.switch(
            master,
            text,
            self.settings[key],
            command=lambda: self._restyle(key, bool(widget.get())),
        )
        return widget

    def _apply_preset(self, name: str) -> None:
        self.settings.update(ACCESS_PRESETS[name][1])
        self.app.save_user_data()
        self.app.apply_settings(rebuild=True)
        widgets.toast(self.app, f"{name} setup applied")

    # Sound ----------------------------------------------------------------------------------

    def _tab_sound(self, grid) -> None:
        s = self.settings
        card = widgets.Card(
            grid, "Sound effects", "Made by Bloom itself, from math", icon="speaker"
        )
        body = card.body
        self._sound_switch(body, "Play sound effects", "sound_on").grid(
            row=0, column=0, sticky="w"
        )
        widgets.label(body, "Volume", "label").grid(
            row=1, column=0, sticky="w", pady=(14, 4)
        )
        volume = ctk.CTkSlider(
            body,
            from_=10,
            to=100,
            number_of_steps=9,
            progress_color=theme.pair("primary"),
            button_color=theme.pair("primary"),
            button_hover_color=theme.pair("primary_hover"),
            fg_color=theme.pair("border"),
        )
        volume.set(s["sound_volume"])
        volume.grid(row=2, column=0, sticky="ew")
        volume.bind(
            "<ButtonRelease-1>", lambda _e: self._set_volume(round(volume.get()))
        )

        def nudge(step: int) -> None:
            volume.set(volume.get() + step)
            self._set_volume(round(volume.get()))

        widgets.keyboard(
            volume, lambda: self._set_volume(round(volume.get())), "Volume"
        )
        volume._canvas.bind("<Left>", lambda _e: nudge(-10), add="+")
        volume._canvas.bind("<Right>", lambda _e: nudge(10), add="+")
        widgets.label(body, "Sound pack", "label").grid(
            row=3, column=0, sticky="w", pady=(14, 6)
        )
        packs = {info[0]: key for key, info in sound.PACKS.items()}
        current = next(n for n, v in packs.items() if v == s["sound_pack"])
        widgets.segmented(
            body, list(packs), current, command=lambda n: self._set_pack(packs[n])
        ).grid(row=4, column=0, sticky="w")
        grid.add(card)

        which = widgets.Card(grid, "Which sounds play", icon="check")
        switches = (
            ("Clicks and page changes", "sound_clicks"),
            ("Saved, warning, log in and log out", "sound_alerts"),
            ("Celebrations and breathing", "sound_celebrate"),
        )
        for row, (text, key) in enumerate(switches):
            self._sound_switch(which.body, text, key).grid(
                row=row, column=0, sticky="w", pady=4
            )
        tests = ctk.CTkFrame(which.body, fg_color="transparent")
        tests.grid(row=3, column=0, sticky="w", pady=(12, 0))
        samples = (
            ("Click", "click"),
            ("Saved", "success"),
            ("Warning", "warning"),
            ("Celebrate", "celebrate"),
        )
        for column, (text, event) in enumerate(samples):
            sample = widgets.small_button(tests, text, lambda e=event: sfx.play(e))
            sample.configure(width=78)
            sample.grid(row=0, column=column, padx=(0, 6))
        grid.add(which)

    def _sound_switch(self, master, text: str, key: str):
        widget = widgets.switch(
            master,
            text,
            self.settings[key],
            command=lambda: self._set_sound(key, bool(widget.get())),
        )
        return widget

    def _set_sound(self, key: str, value) -> None:
        self.settings[key] = value
        self.app.save_user_data()
        sfx.configure(self.settings)

    def _set_volume(self, value: int) -> None:
        self._set_sound("sound_volume", value)
        sfx.play("success")

    def _set_pack(self, key: str) -> None:
        self._set_sound("sound_pack", key)
        sfx.play("success")

    # Preferences ----------------------------------------------------------------------------

    def _tab_preferences(self, grid) -> None:
        s = self.settings
        units_card = widgets.Card(grid, "Units", icon="scale")
        body = units_card.body
        options = (
            ("Weight", "weight_unit", {"kg": "kg", "lb": "lb"}),
            ("Height", "height_unit", {"cm": "cm", "ft & in": "ft"}),
            ("Temperature", "temp_unit", {"°C": "c", "°F": "f"}),
            (
                "BMI categories",
                "bmi_standard",
                {"CDC / WHO": "cdc", "Asia-Pacific": "asia"},
            ),
        )
        body.columnconfigure(0, weight=1)
        for row, (title, key, values) in enumerate(options):
            widgets.label(body, title, "body").grid(
                row=row, column=0, sticky="w", pady=6
            )
            current = next(name for name, value in values.items() if value == s[key])
            widgets.segmented(
                body,
                list(values),
                current,
                command=lambda name, k=key, v=values: self._set(
                    k, v[name], "Units saved"
                ),
            ).grid(row=row, column=1, sticky="e", pady=6)
        grid.add(units_card)

        behaviour = widgets.Card(grid, "How Bloom behaves", icon="gear")
        bbody = behaviour.body
        widgets.label(bbody, "Open on this page", "label").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        current = next(n for n, v in START_PAGES.items() if v == s["start_page"])
        widgets.option_menu(
            bbody,
            list(START_PAGES),
            current,
            command=lambda n: self._set(
                "start_page", START_PAGES[n], "Start page saved"
            ),
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))
        rail = widgets.switch(
            bbody,
            "Always use the narrow icon sidebar",
            s["always_rail"],
            command=lambda: self._restyle("always_rail", bool(rail.get())),
        )
        rail.grid(row=2, column=0, sticky="w", pady=4)
        ask = widgets.switch(
            bbody,
            "Ask before logging out",
            s["confirm_logout"],
            command=lambda: self._set("confirm_logout", bool(ask.get()), "Saved"),
        )
        ask.grid(row=3, column=0, sticky="w", pady=4)
        widgets.button(
            bbody, "Reset Look and Sound to Default", self._reset_look, kind="plain"
        ).grid(row=4, column=0, sticky="w", pady=(12, 0))
        grid.add(behaviour)

    def _reset_look(self) -> None:
        defaults = storage.new_user_data()["settings"]
        for key in LOOK_DEFAULTS:
            self.settings[key] = defaults[key]
        self.app.save_user_data()
        self.app.apply_settings(rebuild=True)
        widgets.toast(self.app, "Look and sound reset")

    def _set(self, key: str, value, message: str) -> None:
        self.settings[key] = value
        if key == "reduce_motion":
            anim.reduce_motion = value
        self.save(message)

    def _set_appearance(self, name: str) -> None:
        self.settings["appearance"] = APPEARANCE[name]
        self.app.save_user_data()
        self.app.apply_settings(rebuild=True)
        widgets.toast(self.app, f"{name} appearance")

    # Account -----------------------------------------------------------------------------

    def _tab_account(self, grid) -> None:
        user = self.app.user
        card = widgets.Card(grid, "Account", icon="user")
        body = card.body
        widgets.label(body, f"@{user['username']}", "title3").grid(
            row=0, column=0, sticky="w"
        )
        widgets.label(
            body,
            f"Member since {user['created_on']:%B} {user['created_on'].day}, {user['created_on'].year}".replace(
                " 0", " "
            ),
            "callout",
            "text_muted",
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="w")
        widgets.button(
            actions,
            "Export My Data (CSV)",
            self._export,
            kind="secondary",
            icon="download",
        ).grid(row=0, column=0, padx=(0, 8))
        widgets.button(
            actions, "Log Out", self.app.confirm_log_out, kind="plain", icon="logout"
        ).grid(row=0, column=1)
        widgets.button(
            body,
            "Create a Doctor Summary",
            self._doctor_summary,
            kind="secondary",
            icon="report",
        ).grid(row=4, column=0, sticky="w", pady=(10, 0))
        widgets.label(
            body,
            "A one-page summary of your logs to print or show a clinician.",
            "footnote",
            "text_muted",
            wraplength=400,
        ).grid(row=5, column=0, sticky="w", pady=(4, 0))
        widgets.label(
            body,
            "To switch accounts, log out and log in as someone else.",
            "footnote",
            "text_muted",
            wraplength=400,
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))
        grid.add(card)

        password = widgets.Card(grid, "Change password", icon="lock")
        pbody = password.body
        self.current_pw = widgets.PasswordField(pbody, "Current password")
        self.current_pw.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.new_pw = widgets.PasswordField(
            pbody, "New password", helper="8+ characters with a letter and a number"
        )
        self.new_pw.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.confirm_pw = widgets.PasswordField(
            pbody, "Confirm new password", on_enter=self._change_password
        )
        self.confirm_pw.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.pw_button = widgets.button(
            pbody, "Change Password", self._change_password, icon="check"
        )
        self.pw_button.grid(row=3, column=0, sticky="w")
        grid.add(password)

        code = widgets.Card(
            grid,
            "Recovery code",
            "Lost it? Make a new one; the old code stops working.",
            icon="key",
        )
        widgets.button(
            code.body,
            "Create New Recovery Code",
            self._new_code,
            kind="secondary",
            icon="key",
        ).grid(row=0, column=0, sticky="w")
        grid.add(code)

        danger = widgets.Card(
            grid,
            "Delete account",
            "Permanently removes your account and every log on this computer.",
            icon="trash",
        )
        widgets.button(
            danger.body,
            "Delete My Account",
            self._delete_account,
            kind="danger",
            icon="trash",
        ).grid(row=0, column=0, sticky="w")
        grid.add(danger)

    def _export(self) -> None:
        default = f"bloom-{self.app.user['username']}-{self.today:%Y%m%d}.csv"
        target = filedialog.asksaveasfilename(
            parent=self.app,
            title="Export your data",
            defaultextension=".csv",
            initialfile=default,
            filetypes=[("CSV spreadsheet", "*.csv")],
        )
        if not target:
            return
        try:
            rows = storage.export_csv(self.data, Path(target))
        except OSError:  # e.g. the file is open in Excel, or the folder is read-only
            widgets.toast(self.app, "Couldn't save there. Close the file or pick another folder.", "warning")  # fmt: skip
            return
        widgets.toast(self.app, f"Exported {rows} days to {Path(target).name}")

    def _doctor_summary(self) -> None:
        default = f"bloom-summary-{self.today:%Y%m%d}.html"
        target = filedialog.asksaveasfilename(
            parent=self.app,
            title="Save your health summary",
            defaultextension=".html",
            initialfile=default,
            filetypes=[("Web page you can print", "*.html")],
        )
        if not target:
            return
        text = report.doctor_summary_html(
            self.data, self.app.user["username"], self.today
        )
        try:
            storage.write_text_file(Path(target), text)
        except OSError:
            widgets.toast(
                self.app, "Couldn't save there. Pick another folder.", "warning"
            )
            return
        webbrowser.open(Path(target).as_uri())
        widgets.toast(self.app, f"Summary saved as {Path(target).name}")

    def _change_password(self) -> None:
        for field in (self.current_pw, self.new_pw, self.confirm_pw):
            field.clear_error()
        current, new, confirm = (
            self.current_pw.get(),
            self.new_pw.get(),
            self.confirm_pw.get(),
        )
        user = self.app.user
        self.pw_button.configure(state="disabled", text="Saving…")

        def done(_result, error) -> None:
            self.pw_button.configure(state="normal", text="Change Password")
            if error is None:
                self.app.save_users()
                for field in (self.current_pw, self.new_pw, self.confirm_pw):
                    field.set("")
                widgets.toast(self.app, "Password changed")
            elif isinstance(error, auth.AuthError):
                self.current_pw.show_error(str(error))
            elif isinstance(error, ValueError):
                (self.confirm_pw if "match" in str(error) else self.new_pw).show_error(
                    str(error)
                )
            else:
                raise error

        widgets.run_in_background(
            self, lambda: auth.change_password(user, current, new, confirm), done
        )

    def _new_code(self) -> None:
        password = widgets.ask_password(
            self.app,
            "Create a new recovery code",
            "Enter your password to confirm it's you.",
            "Continue",
        )
        if password is None:
            return
        user = self.app.user

        def done(code, error) -> None:
            if error is not None:
                widgets.toast(self.app, str(error), "warning")
                return
            self.app.save_users()
            widgets.show_code(self.app, code)

        widgets.run_in_background(
            self, lambda: auth.regenerate_recovery_code(user, password), done
        )

    def _delete_account(self) -> None:
        password = widgets.ask_password(
            self.app,
            "Delete your account?",
            "This permanently deletes your account and all your logs on this computer. Enter your password to continue.",
            "Continue",
            danger=True,
        )
        if password is None:
            return
        if not widgets.confirm(
            self.app,
            "Are you sure?",
            "This cannot be undone. Consider exporting your data first.",
            "Delete Forever",
            danger=True,
        ):
            return
        users, user = self.app.users, self.app.user

        def done(_result, error) -> None:
            if error is not None:
                widgets.toast(self.app, str(error), "warning")
                return
            self.app.delete_user_files()
            self.app.save_users()
            self.app.log_out()
            widgets.toast(self.app, "Your account was deleted")

        widgets.run_in_background(
            self, lambda: auth.delete_account(users, user, password), done
        )

    # About -----------------------------------------------------------------------------------

    def _tab_about(self, grid) -> None:
        card = widgets.Card(
            grid,
            f"{theme.APP_NAME}: {theme.APP_TAGLINE}",
            "Version 2.0  ·  COMPE 02 final project",
            icon="sparkle",
        )
        body = card.body
        widgets.note(
            body,
            "Bloom gives general wellness information and estimates. It is not a medical device, does not diagnose, and its fertile-window predictions are not birth control.",
            "warning",
            420,
        ).grid(row=0, column=0, sticky="ew")
        widgets.label(body, "Keyboard shortcuts", "label").grid(
            row=1, column=0, sticky="w", pady=(16, 4)
        )
        widgets.label(
            body,
            "Ctrl+K finds anything, F1 lists every shortcut, and F2 reads the page aloud.",
            "callout",
            "text_muted",
            wraplength=420,
        ).grid(row=2, column=0, sticky="w")
        widgets.label(
            body,
            f"Data folder: {self.app.data_dir}",
            "footnote",
            "text_muted",
            wraplength=420,
        ).grid(row=3, column=0, sticky="w", pady=(12, 0))
        widgets.label(
            body,
            f"Today is {datetime.now():%A, %B} {datetime.now().day}, {datetime.now().year}.",
            "footnote",
            "text_muted",
        ).grid(row=4, column=0, sticky="w")
        grid.add(card)
        sources = widgets.Card(
            grid, "Sources", "The guidance behind the numbers", icon="info"
        )
        for row, source in enumerate(SOURCES):
            widgets.label(sources.body, f"•  {source}", "callout", wraplength=420).grid(
                row=row, column=0, sticky="w", pady=2
            )
        grid.add(sources)
