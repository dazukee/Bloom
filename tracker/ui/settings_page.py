"""Settings: profile, goals, preferences, account manager and about."""

from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import override

import customtkinter as ctk

from tracker import auth, profile, storage, units, validators
from tracker.ui import anim, theme, widgets
from tracker.ui.page import Page

TABS = ("Profile", "Goals", "Preferences", "Account", "About")
APPEARANCE = {"System": "system", "Light": "light", "Dark": "dark"}
SOURCES = (
    "CDC: Adult BMI categories",
    "WHO Western Pacific Region (2000): Asia-Pacific BMI cut-offs",
    "Office on Women's Health: Your menstrual cycle; Trying to conceive (calendar method)",
    "NHS: Fertility in the menstrual cycle",
    "CDC / ACC-AHA: Blood pressure categories",
    "CDC: How much sleep do I need?",
    "WHO: Physical activity fact sheet",
    "FDA: How much caffeine is too much?",
    "Compendium of Physical Activities: MET values",
    "Mifflin-St Jeor equation (1990)",
    "OWASP Password Storage Cheat Sheet",
)


class SettingsPage(Page):
    """Everything set during onboarding can be changed here."""

    title = "Settings"
    subtitle = "Your profile, goals, preferences and account."

    @override
    def build(self) -> None:
        tab = getattr(self.app, "settings_tab", "Profile")
        widgets.segmented(
            self.body, list(TABS), tab, command=self._show_tab, height=38
        ).grid(row=0, column=0, sticky="w", pady=(0, theme.GUTTER))
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
        widgets.label(cbody, "Period length", "label").grid(
            row=1, column=1, sticky="w", padx=(30, 0)
        )
        self.period_stepper = widgets.Stepper(
            cbody,
            p["period_length"],
            1,
            profile.MIN_PERIOD_LENGTH,
            profile.MAX_PERIOD_LENGTH,
            unit="days",
        )
        self.period_stepper.grid(
            row=2, column=1, sticky="w", padx=(30, 0), pady=(6, 12)
        )
        widgets.button(
            cbody,
            "Save Cycle Settings",
            self._save_cycle,
            kind="secondary",
            icon="check",
        ).grid(row=3, column=0, columnspan=2, sticky="w")
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
                body, goals[key], step, low, high, fmt=fmt, unit=unit, value_width=130
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

    # Preferences ----------------------------------------------------------------------------

    def _tab_preferences(self, grid) -> None:
        s = self.settings
        card = widgets.Card(grid, "Appearance", icon="sun")
        current = next(
            name for name, key in APPEARANCE.items() if key == s["appearance"]
        )
        widgets.segmented(
            card.body, list(APPEARANCE), current, command=self._set_appearance
        ).grid(row=0, column=0, sticky="w")
        motion = widgets.switch(
            card.body,
            "Reduce motion",
            s["reduce_motion"],
            command=lambda: self._set(
                "reduce_motion", bool(motion.get()), "Motion preference saved"
            ),
        )
        motion.grid(row=1, column=0, sticky="w", pady=(16, 0))
        widgets.label(
            card.body,
            "Turns off slides, counting numbers and floating 3D objects.",
            "footnote",
            "text_muted",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        grid.add(card)

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
            f"Member since {user['created_on']:%B %d, %Y}".replace(" 0", " "),
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
        widgets.label(
            body,
            "To switch accounts, log out and log in as someone else.",
            "footnote",
            "text_muted",
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
            "Version 1.0  ·  COMPE 02 final project",
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
            "Ctrl+1 to Ctrl+9 open the sidebar pages in order. Enter submits forms. Esc closes dialogs.",
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
            body, f"Today is {datetime.now():%A, %B %d, %Y}.", "footnote", "text_muted"
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
