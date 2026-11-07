"""Log in, sign up, reset a password, and show a recovery code once.

Layout: a purple hero with floating 3D objects on the left and the form on
the right; on narrow windows the hero hides and the form is centred. Password
hashing is slow on purpose (600,000 rounds), so it runs on a background thread
while the button shows "Logging in…".
"""

from datetime import date, datetime
from typing import override

import customtkinter as ctk

from tracker import auth
from tracker.ui import icons, palette, sfx, theme, widgets

HERO_OBJECTS = [
    {
        "kind": "flower",
        "size": 230,
        "x": 0.48,
        "y": 0.36,
        "amp": 10,
        "base": (168, 85, 247),
        "glow": (253, 224, 255),
    },
    {"kind": "heart", "size": 74, "x": 0.15, "y": 0.2, "amp": 8, "phase": 1.6, "hue": 0.95},
    {"kind": "drop", "size": 62, "x": 0.86, "y": 0.16, "amp": 7, "phase": 3.1, "hue": 0.93},
    {"kind": "moon", "size": 62, "x": 0.84, "y": 0.6, "amp": 6, "phase": 2.2, "hue": 0.13},
    {"kind": "sphere", "size": 40, "x": 0.14, "y": 0.58, "amp": 6, "phase": 0.7, "hue": 0.55},
]  # fmt: skip
STRENGTHS = (("Weak", "danger"), ("Fair", "warning"), ("Good", "fertile"), ("Strong", "success"))  # fmt: skip
HERO_TEXTS = (
    (theme.APP_NAME, "large_title", "on_primary", 0.09, 0.80, "w"),
    ("Know your body, one day at a time.", "title3", "on_primary", 0.09, 0.865, "w"),
    (
        "Private by design: your data stays on this computer.",
        "footnote",
        "on_primary",
        0.09,
        0.92,
        "w",
    ),
)


class AuthScreen(ctk.CTkFrame):
    """The shared two-column layout; subclasses fill in build()."""

    heading = ""
    subheading = ""

    def __init__(self, app) -> None:
        super().__init__(app, fg_color=theme.pair("bg"), corner_radius=0)
        self.app = app
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=5)
        self.columnconfigure(1, weight=6)
        self.hero = widgets.Hero3D(
            self, HERO_OBJECTS, height=600, texts=HERO_TEXTS, stars=26, text_width=0.84
        )
        self.hero.grid(row=0, column=0, sticky="nsew")
        self.side = ctk.CTkFrame(self, fg_color=theme.pair("bg"), corner_radius=0)
        self.side.grid(row=0, column=1, sticky="nsew")
        self.side.rowconfigure(0, weight=1)
        self.side.columnconfigure(0, weight=1)
        # The form scrolls if a short window or large text cannot fit it.
        self.scroller = ctk.CTkScrollableFrame(
            self.side,
            fg_color=theme.pair("bg"),
            corner_radius=0,
            scrollbar_button_color=theme.pair("border"),
            scrollbar_button_hover_color=theme.pair("text_muted"),
        )
        self.scroller.grid(row=0, column=0, sticky="nsew")
        self.scroller.columnconfigure(0, weight=1)
        widgets.fast_scroll(self.scroller)
        self.card = ctk.CTkFrame(self.scroller, fg_color="transparent")
        self.card.columnconfigure(0, weight=1)
        # An empty 380-wide row fixes the form's width; its height follows the content.
        ctk.CTkFrame(self.card, width=380, height=1, fg_color="transparent").grid(
            row=99, column=0
        )
        widgets.label(self.card, self.heading, "large_title", "title").grid(
            row=0, column=0, sticky="w"
        )
        widgets.label(
            self.card, self.subheading, "body", "text_muted", wraplength=370
        ).grid(row=1, column=0, sticky="w", pady=(4, 22))
        self.build(self.card, 2)
        self.card.grid(row=0, column=0, pady=theme.PAGE_PAD)
        self.scroller.bind("<Configure>", self._centre_form, add="+")
        access = widgets.icon_button(
            self.side,
            "eye_access",
            self._open_access,
            size=36,
            kind="ghost",
            tooltip="Accessibility: larger text, high contrast",
        )
        access.place(relx=1.0, x=-14, y=14, anchor="ne")
        self.adapt(app.compact)
        self.after(20, self._centre_form)

    def _centre_form(self, _event=None) -> None:
        """Keep the form vertically centred whenever it fits."""
        try:
            room = self.scroller._parent_canvas.winfo_height()
            height = self.card.winfo_reqheight()
            scale = widgets.scaling(self)
            top = max(theme.PAGE_PAD, (room - height) / 2 / scale)
            self.card.grid_configure(pady=(top, theme.PAGE_PAD))
        except widgets.tk.TclError:
            pass

    def _open_access(self) -> None:
        palette.show_login_access(self.app, self._look_changed)

    def _look_changed(self) -> None:
        self.app.save_users()
        self.app.apply_login_look()
        self.app.restart_screen(self)

    def build(self, card, row: int) -> None:
        """Add the form to `card`, starting at grid row `row`."""

    def adapt(self, compact: bool) -> None:
        """Hide the hero on narrow windows."""
        if compact:
            self.hero.grid_remove()
            self.side.grid(row=0, column=0, columnspan=2, sticky="nsew")
        else:
            self.hero.grid()
            self.side.grid(row=0, column=1, columnspan=1, sticky="nsew")

    def error_label(self, card, row: int) -> ctk.CTkLabel:
        """Add a hidden red message line for form-level errors."""
        message = widgets.label(card, "", "callout", "danger", wraplength=370)
        message.grid(row=row, column=0, sticky="w", pady=(0, 10))
        message.grid_remove()
        return message

    def busy(self) -> bool:
        """Return True while a slow check runs (pressing Enter again does nothing)."""
        button = getattr(self, "submit_button", None)
        return button is not None and button.cget("state") == "disabled"

    @staticmethod
    def show(message: ctk.CTkLabel, text: str) -> None:
        """Show (or hide, with "") a form-level message."""
        message.configure(text=text)
        if text:
            message.grid()
        else:
            message.grid_remove()

    def links(self, card, row: int, items) -> None:
        """Add a row of text buttons, e.g. ("Create Account", command)."""
        frame = ctk.CTkFrame(card, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=(10, 0))
        for column, (text, command) in enumerate(items):
            frame.columnconfigure(column, weight=1)
            widgets.button(frame, text, command, kind="ghost", height=36).grid(
                row=0, column=column, sticky="w" if column == 0 else "e"
            )


class LoginScreen(AuthScreen):
    """Username and password."""

    heading = "Welcome back"
    subheading = "Log in to continue your daily check-in."

    @override
    def build(self, card, row: int) -> None:
        last = self.app.users.get("last_username") or ""
        first_run = not self.app.users["users"]
        if first_run:
            widgets.note(
                card,
                "New here? Create an account to get started; it takes a minute.",
                "info",
                330,
            ).grid(row=row, column=0, sticky="ew", pady=(0, 16))
            row += 1
        self.username = widgets.Field(
            card,
            "Username",
            "e.g. maria_c",
            value=last,
            on_enter=lambda: self.password.focus(),
        )
        self.username.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        self.password = widgets.PasswordField(card, "Password", on_enter=self.submit)
        self.password.grid(row=row + 1, column=0, sticky="ew", pady=(0, 14))
        self.message = self.error_label(card, row + 2)
        self.submit_button = widgets.button(
            card, "Log In", self.submit, height=theme.BIG_CONTROL_HEIGHT
        )
        self.submit_button.grid(row=row + 3, column=0, sticky="ew")
        self.links(
            card,
            row + 4,
            [
                ("Forgot Password?", self.app.show_reset),
                ("Create Account", self.app.show_register),
            ],
        )
        target = self.password if last else self.username
        self.after(120, target.focus)

    def submit(self) -> None:
        """Check the fields, then verify the password on a background thread."""
        if self.busy():
            return
        self.username.clear_error()
        self.password.clear_error()
        self.show(self.message, "")
        username, password = self.username.get(), self.password.get()
        if not username.strip():
            self.username.show_error("Enter your username.")
            return
        if not password:
            self.password.show_error("Enter your password.")
            return
        self.submit_button.configure(state="disabled", text="Logging in…")
        users = self.app.users
        widgets.run_in_background(
            self,
            lambda: auth.check_login(users, username, password, datetime.now()),
            self._done,
        )

    def _done(self, user, error) -> None:
        self.app.save_users()  # the attempt counter changed either way
        if error is None:
            self.app.log_in(user)
            return
        if not isinstance(error, auth.AuthError):
            raise error
        self.submit_button.configure(state="normal", text="Log In")
        self.show(self.message, str(error))
        self.password.set("")
        self.password.focus()


class RegisterScreen(AuthScreen):
    """Create an account, with live password rules."""

    heading = "Create your account"
    subheading = "It takes a minute, and everything stays on this computer."

    @override
    def build(self, card, row: int) -> None:
        self.username = widgets.Field(
            card,
            "Username",
            "e.g. maria_c",
            helper="3-20 letters, numbers or _",
            on_enter=lambda: self.password.focus(),
        )
        self.username.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        self.password = widgets.PasswordField(
            card, "Password", on_enter=lambda: self.confirm.focus()
        )
        self.password.grid(row=row + 1, column=0, sticky="ew", pady=(0, 12))
        self.confirm = widgets.PasswordField(
            card, "Confirm password", on_enter=self.submit
        )
        self.confirm.grid(row=row + 2, column=0, sticky="ew", pady=(0, 10))
        rules = ctk.CTkFrame(card, fg_color="transparent")
        rules.grid(row=row + 3, column=0, sticky="w", pady=(0, 14))
        self.rule_labels = []
        for index, text in enumerate(
            ("At least 8 characters", "A letter and a number", "Passwords match")
        ):
            rule = widgets.label(
                rules,
                text,
                "footnote",
                "text_muted",
                compound="left",
                image=icons.icon("check", 14, "border"),
            )
            rule.grid(row=index, column=0, sticky="w")
            self.rule_labels.append(rule)
        self.strength = widgets.progress_bar(rules, 0, "danger", 6)
        self.strength.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self.strength_text = widgets.label(rules, "", "footnote", "text_muted")
        self.strength_text.grid(row=4, column=0, sticky="w")
        for field in (self.password, self.confirm):
            field.entry.bind("<KeyRelease>", lambda _e: self._update_rules(), add="+")
        self.message = self.error_label(card, row + 4)
        self.submit_button = widgets.button(
            card, "Create Account", self.submit, height=theme.BIG_CONTROL_HEIGHT
        )
        self.submit_button.grid(row=row + 5, column=0, sticky="ew")
        self.links(card, row + 6, [("I Already Have an Account", self.app.show_login)])
        self.after(120, self.username.focus)

    def _update_rules(self) -> None:
        password, confirm = self.password.get(), self.confirm.get()
        checks = (
            len(password) >= auth.PASSWORD_MIN_LENGTH,
            any(c.isalpha() for c in password) and any(c.isdigit() for c in password),
            bool(password) and password == confirm,
        )
        for rule, passed in zip(self.rule_labels, checks, strict=True):
            rule.configure(
                text_color=theme.pair("success" if passed else "text_muted"),
                image=icons.icon("check", 14, "success" if passed else "border"),
            )
        score = auth.password_strength(password)
        name, token = STRENGTHS[score]
        self.strength.set((score + 1) / len(STRENGTHS) if password else 0)
        self.strength.configure(progress_color=theme.pair(token))
        self.strength_text.configure(text=f"Strength: {name}" if password else "")

    def submit(self) -> None:
        """Check the rules field by field, then create the account."""
        if self.busy():
            return
        for field in (self.username, self.password, self.confirm):
            field.clear_error()
        self.show(self.message, "")
        username = self.username.get().strip()
        password, confirm = self.password.get(), self.confirm.get()
        try:
            auth.check_username_rules(username)
        except ValueError as error:
            self.username.show_error(str(error))
            return
        try:
            auth.check_password_rules(password, confirm)
        except ValueError as error:
            target = self.confirm if "match" in str(error) else self.password
            target.show_error(str(error))
            return
        self.submit_button.configure(state="disabled", text="Creating account…")
        users = self.app.users
        widgets.run_in_background(
            self,
            lambda: auth.register_user(
                users, username, password, confirm, date.today()
            ),
            self._done,
        )

    def _done(self, result, error) -> None:
        if error is not None:
            if not isinstance(error, (auth.AuthError, ValueError)):
                raise error
            self.submit_button.configure(state="normal", text="Create Account")
            self.username.show_error(str(error))
            return
        user, code = result
        self.app.save_users()
        self.app.show_code(
            code, lambda: self.app.log_in(user), "Save your recovery code"
        )


class ResetScreen(AuthScreen):
    """Reset a forgotten password with the one-time recovery code."""

    heading = "Reset your password"
    subheading = "Use the recovery code you saved when you created your account."

    @override
    def build(self, card, row: int) -> None:
        last = self.app.users.get("last_username") or ""
        self.username = widgets.Field(card, "Username", "e.g. maria_c", value=last)
        self.username.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        self.code = widgets.Field(card, "Recovery code", "XXXX-XXXX-XXXX")
        self.code.grid(row=row + 1, column=0, sticky="ew", pady=(0, 12))
        self.password = widgets.PasswordField(
            card, "New password", helper="8+ characters with a letter and a number"
        )
        self.password.grid(row=row + 2, column=0, sticky="ew", pady=(0, 12))
        self.confirm = widgets.PasswordField(
            card, "Confirm new password", on_enter=self.submit
        )
        self.confirm.grid(row=row + 3, column=0, sticky="ew", pady=(0, 14))
        self.message = self.error_label(card, row + 4)
        self.submit_button = widgets.button(
            card, "Reset Password", self.submit, height=theme.BIG_CONTROL_HEIGHT
        )
        self.submit_button.grid(row=row + 5, column=0, sticky="ew")
        self.links(card, row + 6, [("Back to Log In", self.app.show_login)])
        self.after(120, (self.code if last else self.username).focus)

    def submit(self) -> None:
        """Check the new password, then verify the code on a background thread."""
        if self.busy():
            return
        for field in (self.username, self.code, self.password, self.confirm):
            field.clear_error()
        self.show(self.message, "")
        if not self.username.get().strip():
            self.username.show_error("Enter your username.")
            return
        if not self.code.get().strip():
            self.code.show_error("Enter the recovery code you saved.")
            return
        args = (
            self.username.get(),
            self.code.get(),
            self.password.get(),
            self.confirm.get(),
        )
        self.submit_button.configure(state="disabled", text="Checking…")
        users = self.app.users
        widgets.run_in_background(
            self,
            lambda: auth.reset_password_with_code(users, *args, datetime.now()),
            self._done,
        )

    def _done(self, new_code, error) -> None:
        self.app.save_users()
        if error is not None:
            if not isinstance(error, (auth.AuthError, ValueError)):
                raise error
            self.submit_button.configure(state="normal", text="Reset Password")
            if isinstance(error, ValueError):
                target = self.confirm if "match" in str(error) else self.password
                target.show_error(str(error))
            else:
                self.show(self.message, str(error))
            return

        def back_to_login() -> None:
            self.app.show_login()
            widgets.toast(self.app, "Password changed. Log in with your new password.")

        self.app.show_code(new_code, back_to_login, "Your new recovery code")


class CodeScreen(AuthScreen):
    """Shows a recovery code once; Continue unlocks after "I saved it"."""

    subheading = (
        "If you forget your password, this code resets it. It is shown only once, "
        "so save it now: write it down or keep it in a password manager."
    )

    def __init__(self, app, code: str, then, heading: str) -> None:
        self.code = code
        self.then = then
        self.heading = heading
        super().__init__(app)

    @override
    def build(self, card, row: int) -> None:
        box = ctk.CTkLabel(
            card,
            text=self.code,
            font=theme.font("mono"),
            text_color=theme.pair("primary_text"),
            fg_color=theme.pair("primary_soft"),
            corner_radius=14,
            height=72,
        )
        box.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        widgets.button(
            card, "Copy Code", self._copy, kind="secondary", icon="copy"
        ).grid(row=row + 1, column=0, sticky="w", pady=(0, 18))
        self.saved = ctk.CTkCheckBox(
            card,
            text="I saved my recovery code",
            command=sfx.with_sound(self._toggle, "toggle"),
            font=theme.font("body"),
            text_color=theme.pair("text"),
            fg_color=theme.pair("primary"),
            hover_color=theme.pair("primary_hover"),
            border_color=theme.pair("text_muted"),
            corner_radius=6,
        )
        self.saved.grid(row=row + 2, column=0, sticky="w", pady=(0, 16))
        widgets.keyboard(self.saved, self.saved.toggle, "I saved my recovery code")
        self.continue_button = widgets.button(
            card,
            "Continue",
            self.then,
            height=theme.BIG_CONTROL_HEIGHT,
            state="disabled",
        )
        self.continue_button.grid(row=row + 3, column=0, sticky="ew")

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.code)
        widgets.toast(self.app, "Code copied")

    def _toggle(self) -> None:
        self.continue_button.configure(
            state="normal" if self.saved.get() else "disabled"
        )
