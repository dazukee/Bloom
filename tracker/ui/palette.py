"""Quick Find (Ctrl+K) and the keyboard shortcuts list (F1).

Quick Find lets anyone reach any page, setting or action by typing a few letters,
which is faster than hunting with a mouse and much easier without one.
"""

import customtkinter as ctk

from tracker.ui import icons, sfx, speech, theme, widgets

MAX_RESULTS = 7
SHORTCUTS = (
    ("Ctrl + K", "Quick Find: jump to any page, setting or action"),
    ("Ctrl + 1 to 0", "Open the sidebar pages in order"),
    ("Tab, Shift + Tab", "Move between controls; a ring shows where you are"),
    ("Enter or Space", "Use the control with the ring"),
    ("Arrow keys", "Move around the calendar; change a number"),
    ("F2", "Read this page aloud (Esc stops it)"),
    ("F6", "Jump between the sidebar and the page"),
    ("F11", "Full screen on or off"),
    ("Ctrl + plus or minus", "Bigger or smaller text"),
    ("Esc", "Close a dialog"),
)


class CommandPalette(ctk.CTkToplevel):
    """A search box with a list of matching commands."""

    def __init__(self, app, commands: list[tuple]) -> None:
        super().__init__(app)
        self.app = app
        self.commands = commands  # (title, words to match, icon name, action)
        self.title("Quick Find")
        self.configure(fg_color=theme.pair("surface"))
        self.resizable(False, False)
        self.transient(app)
        app.dress_window(self)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)
        body.columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(
            body,
            placeholder_text="Type to find a page, setting or action",
            height=theme.control_height(44),
            width=460,
            corner_radius=12,
            border_width=theme.border_width,
            border_color=theme.pair("primary"),
            fg_color=theme.pair("surface_alt"),
            text_color=theme.pair("text"),
            placeholder_text_color=theme.pair("text_muted"),
            font=theme.font("body"),
        )
        self.entry.grid(row=0, column=0, sticky="ew")
        self.results = ctk.CTkFrame(body, fg_color="transparent")
        self.results.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.results.columnconfigure(0, weight=1)
        self.rows: list[ctk.CTkButton] = []
        self.shown: list[tuple] = []
        self.selected = 0
        self.entry.bind("<KeyRelease>", self._typed)
        self.entry.bind("<Return>", lambda _e: self._run(self.selected))
        self.entry.bind("<Down>", lambda _e: self._move(1))
        self.entry.bind("<Up>", lambda _e: self._move(-1))
        self.bind("<Escape>", lambda _e: self.destroy())
        self._fill("")
        self.after(30, self._centre)

    def _centre(self) -> None:
        self.update_idletasks()
        x = self.app.winfo_rootx() + (self.app.winfo_width() - self.winfo_width()) // 2
        y = self.app.winfo_rooty() + self.app.winfo_height() // 7
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.lift()
        try:
            self.grab_set()
        except widgets.tk.TclError:
            self.after(60, self._centre)
            return
        self.entry.focus_set()

    def _typed(self, event) -> None:
        if event.keysym not in ("Up", "Down", "Return", "Escape"):
            self._fill(self.entry.get())

    def _fill(self, text: str) -> None:
        words = text.lower().split()
        self.shown = [
            command
            for command in self.commands
            if all(word in f"{command[0]} {command[1]}".lower() for word in words)
        ][:MAX_RESULTS]
        for row in self.rows:
            row.destroy()
        self.rows = []
        self.selected = 0
        for index, (title, _, icon_name, _action) in enumerate(self.shown):
            strong, _soft = theme.TOPIC_TOKENS.get(icon_name, theme.DEFAULT_TOPIC)
            row = ctk.CTkButton(
                self.results,
                text=title,
                image=icons.icon(icon_name, 18, strong),
                compound="left",
                anchor="w",
                height=theme.control_height(38),
                corner_radius=10,
                font=theme.font("body"),
                text_color=theme.pair("text"),
                hover_color=theme.pair("primary_soft_hover"),
                command=lambda i=index: self._run(i),
            )
            row.grid(row=index, column=0, sticky="ew", pady=1)
            self.rows.append(row)
        if not self.shown:
            empty = widgets.label(
                self.results,
                "Nothing found. Try another word.",
                "callout",
                "text_muted",
            )
            empty.grid(row=0, column=0, sticky="w", pady=8)
            self.rows.append(empty)
        self._mark()

    def _mark(self) -> None:
        for index, row in enumerate(self.rows):
            if isinstance(row, ctk.CTkButton):
                chosen = index == self.selected
                row.configure(
                    fg_color=theme.pair("primary_soft") if chosen else "transparent"
                )
        if self.shown and widgets.speak_focus:
            speech.speak(self.shown[self.selected][0])

    def _move(self, step: int) -> str:
        if self.shown:
            self.selected = (self.selected + step) % len(self.shown)
            self._mark()
        return "break"

    def _run(self, index: int) -> None:
        if index < len(self.shown):
            action = self.shown[index][3]
            sfx.play("click")
            self.destroy()
            self.app.after(30, action)


def show_shortcuts(app) -> None:
    """Show the keyboard shortcuts in a dialog."""
    dialog = widgets.Dialog(
        app,
        "Keyboard shortcuts",
        "Everything in Bloom works without a mouse.",
        "Got It",
        cancel="",
    )
    table = ctk.CTkFrame(dialog.ok_button.master.master, fg_color="transparent")
    table.grid(row=2, column=0, sticky="ew", pady=(0, 16))
    table.columnconfigure(1, weight=1)
    for row, (keys, what) in enumerate(SHORTCUTS):
        ctk.CTkLabel(
            table,
            text=keys,
            font=theme.font("label"),
            text_color=theme.pair("primary_text"),
            fg_color=theme.pair("primary_soft"),
            corner_radius=6,
            height=24,
            padx=8,
        ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
        widgets.label(table, what, "callout", wraplength=320).grid(
            row=row, column=1, sticky="w"
        )
    dialog.ok_button.master.grid(row=3, column=0, sticky="e")
    app.wait_window(dialog)


def show_login_access(app, on_change) -> None:
    """Let someone turn on bigger text or high contrast before logging in."""
    look = app.users["look"]
    dialog = widgets.Dialog(
        app,
        "Accessibility",
        "These apply here and to new accounts. More options are in Settings after you log in.",
        "Done",
        cancel="",
    )
    box = ctk.CTkFrame(dialog.ok_button.master.master, fg_color="transparent")
    box.grid(row=2, column=0, sticky="w", pady=(0, 16))
    contrast = widgets.switch(box, "High contrast", look["high_contrast"])
    contrast.grid(row=0, column=0, sticky="w", pady=4)
    larger = widgets.switch(box, "Larger text", look["text_size"] != "default")
    larger.grid(row=1, column=0, sticky="w", pady=4)
    readable = widgets.switch(
        box, "Easier-to-read font (Atkinson Hyperlegible)", look["font"] == "atkinson"
    )
    readable.grid(row=2, column=0, sticky="w", pady=4)
    dialog.ok_button.master.grid(row=3, column=0, sticky="e")
    app.wait_window(dialog)
    if not dialog.result:
        return
    look["high_contrast"] = bool(contrast.get())
    look["text_size"] = "large" if larger.get() else "default"
    if readable.get():
        look["font"] = "atkinson"
    elif look["font"] == "atkinson":
        look["font"] = theme.DEFAULT_FONT
    on_change()
