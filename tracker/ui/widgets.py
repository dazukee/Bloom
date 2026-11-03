"""Reusable pieces in the app's style, from buttons to 3D art.

Cards, buttons, fields, chips, steppers, rings, charts, 3D art, toasts and
dialogs. Every screen builds from these, so spacing, colours and motion stay the same
everywhere. Colours come from theme.py tokens, never raw hex.
"""

import math
import threading
import tkinter as tk
from datetime import date, timedelta
from typing import override

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from tracker import calendar_logic
from tracker.ui import anim, graphics, icons, render3d, theme

# tone: (strong colour, soft background)
TONES = {
    "good": ("success", "success_soft"),
    "warning": ("warning", "warning_soft"),
    "danger": ("danger", "danger_soft"),
    "info": ("primary_text", "primary_soft"),
}
TONE_ICONS = {"good": "check", "warning": "alert", "danger": "alert", "info": "info"}


def scaling(widget: tk.Misc) -> float:
    """Return CustomTkinter's widget scaling (1.0 at 100% display scaling)."""
    return ctk.ScalingTracker.get_widget_scaling(widget)


def canvas_font(widget: tk.Misc, role: str) -> tuple:
    """Return a Tk font tuple for canvas text, scaled like CTk widgets."""
    size, weight, kind = theme.TYPE_SCALE[role]
    return (theme.face(kind), -round(size * scaling(widget)), weight)


def label(
    master, text: str, role: str = "body", color: str = "text", **kwargs
) -> ctk.CTkLabel:
    """Return a left-aligned text label in a type role and colour token.

    With wraplength, the text wraps at that width at most, and narrower when
    its container is narrower, so long text never pushes a card wider.
    """
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    widget = ctk.CTkLabel(
        master, text=text, font=theme.font(role), text_color=theme.pair(color), **kwargs
    )
    if "wraplength" in kwargs:
        widest = kwargs["wraplength"]

        def fit(event) -> None:
            # The room from the label's left edge to the container's right edge.
            available = (event.width - widget.winfo_x()) / scaling(widget) - 8
            wrap = max(80, min(widest, available))
            if abs(wrap - widget.cget("wraplength")) > 2:
                widget.configure(wraplength=wrap)

        master.bind("<Configure>", fit, add="+")
    return widget


# Buttons ----------------------------------------------------------------------

BUTTON_STYLES = {
    "primary": ("primary", "primary_hover", "on_primary"),
    "secondary": ("primary_soft", "primary_soft_hover", "primary_text"),
    "plain": ("surface_alt", "border", "text"),
    "ghost": ("transparent", "surface_alt", "primary_text"),
    "danger": ("danger_fill", "danger_fill_hover", "on_primary"),
}


def button(
    master,
    text: str,
    command=None,
    kind: str = "primary",
    icon: str | None = None,
    height: int = theme.CONTROL_HEIGHT,
    width: int = 0,
    **kwargs,
) -> ctk.CTkButton:
    """Return a button: primary, secondary, plain, ghost or danger."""
    fill, hover, text_color = BUTTON_STYLES[kind]
    image = icons.icon(icon, 18, text_color) if icon else None
    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        image=image,
        compound="left",
        height=height,
        width=width,
        corner_radius=theme.RADIUS_CONTROL,
        font=theme.font("headline"),
        fg_color="transparent" if fill == "transparent" else theme.pair(fill),
        hover_color=theme.pair(hover),
        text_color=theme.pair(text_color),
        text_color_disabled=theme.pair("text_muted"),
        **kwargs,
    )


def icon_button(
    master,
    name: str,
    command=None,
    size: int = 36,
    kind: str = "plain",
    tooltip: str = "",
) -> ctk.CTkButton:
    """Return a square button showing only an icon, with a hover tooltip."""
    fill, hover, color = BUTTON_STYLES[kind]
    widget = ctk.CTkButton(
        master,
        text="",
        command=command,
        image=icons.icon(name, 18, color),
        width=size,
        height=size,
        corner_radius=theme.RADIUS_CONTROL,
        fg_color="transparent" if fill == "transparent" else theme.pair(fill),
        hover_color=theme.pair(hover),
    )
    if tooltip:
        Tooltip(widget, tooltip)
    return widget


# Cards and text -------------------------------------------------------------------


class Card(ctk.CTkFrame):
    """A rounded white panel with an optional icon, title, subtitle and action.

    Put content in card.body (one column that stretches).
    """

    def __init__(
        self,
        master,
        title: str | None = None,
        subtitle: str | None = None,
        icon: str | None = None,
        action=None,
        pad: int = theme.PAD,
        bg: str = "surface",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.pair(bg),
            corner_radius=theme.RADIUS_CARD,
            border_width=1,
            border_color=theme.pair("border"),
            **kwargs,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.subtitle_label = None
        if title:
            head = ctk.CTkFrame(self, fg_color="transparent")
            head.grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, 0))
            head.columnconfigure(1, weight=1)
            if icon:
                tile = ctk.CTkLabel(
                    head,
                    text="",
                    image=icons.icon(icon, 18, "on_primary"),
                    width=34,
                    height=34,
                    corner_radius=10,
                    fg_color=theme.pair("primary"),
                )
                tile.grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="w")
            label(head, title, "headline").grid(row=0, column=1, sticky="w")
            if subtitle:
                self.subtitle_label = label(
                    head, subtitle, "footnote", "text_muted", wraplength=600
                )
                self.subtitle_label.grid(row=1, column=1, sticky="w")
            if action is not None:
                action(head).grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 0))
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(
            row=1, column=0, sticky="nsew", padx=pad, pady=(14 if title else pad, pad)
        )
        self.body.columnconfigure(0, weight=1)


def badge(master, text: str, tone: str = "info") -> ctk.CTkLabel:
    """Return a small rounded status label; the text carries the meaning, not just colour."""
    strong, soft = TONES[tone]
    return ctk.CTkLabel(
        master,
        text=text,
        font=theme.font("label"),
        text_color=theme.pair(strong),
        fg_color=theme.pair(soft),
        corner_radius=8,
        height=24,
        padx=10,
    )


def stat(
    master, value: str, caption: str, role: str = "number", color: str = "text"
) -> ctk.CTkFrame:
    """Return a big number with a grey caption under it (a KPI without a tile)."""
    frame = ctk.CTkFrame(master, fg_color="transparent")
    value_label = label(frame, value, role, color)
    value_label.grid(row=0, column=0, sticky="w")
    label(frame, caption, "footnote", "text_muted").grid(row=1, column=0, sticky="w")
    frame.value_label = value_label
    return frame


def note(master, text: str, tone: str = "info", wrap: int = 520) -> ctk.CTkFrame:
    """Return a soft tinted message with an icon (an inline banner)."""
    strong, soft = TONES[tone]
    frame = ctk.CTkFrame(master, fg_color=theme.pair(soft), corner_radius=12)
    frame.columnconfigure(1, weight=1)
    ctk.CTkLabel(frame, text="", image=icons.icon(TONE_ICONS[tone], 18, strong)).grid(
        row=0, column=0, padx=(12, 8), pady=10, sticky="n"
    )
    label(frame, text, "callout", strong, wraplength=wrap).grid(
        row=0, column=1, sticky="w", padx=(0, 12), pady=10
    )
    return frame


# Inputs ---------------------------------------------------------------------------


class Field(ctk.CTkFrame):
    """A labelled text box with helper text and an inline error under it."""

    def __init__(
        self,
        master,
        label_text: str,
        placeholder: str = "",
        helper: str = "",
        value: str = "",
        unit: str = "",
        show: str = "",
        width: int = 0,
        on_enter=None,
        bg: str = "surface",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self.helper = helper
        label(self, label_text, "label", "text").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            show=show,
            height=theme.CONTROL_HEIGHT,
            width=width or 60,  # stretches to fill; small so narrow cards fit
            corner_radius=10,
            border_width=1,
            border_color=theme.pair("border"),
            fg_color=theme.pair("surface_alt"),
            text_color=theme.pair("text"),
            placeholder_text_color=theme.pair("text_muted"),
            font=theme.font("body"),
        )
        self.entry.grid(row=1, column=0, sticky="ew")
        if value:
            self.entry.insert(0, value)
        if unit:
            label(self, unit, "callout", "text_muted").grid(
                row=1, column=1, padx=(8, 0)
            )
        self.message = label(self, helper, "footnote", "text_muted", wraplength=360)
        self.message.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        if not helper:
            self.message.grid_remove()
        if on_enter:
            self.entry.bind("<Return>", lambda _event: on_enter())
        self.entry.bind("<FocusIn>", lambda _e: self._border("primary"), add="+")
        self.entry.bind("<FocusOut>", lambda _e: self._border("border"), add="+")
        self._has_error = False

    def _border(self, token: str) -> None:
        if not self._has_error:
            self.entry.configure(border_color=theme.pair(token))

    def get(self) -> str:
        """Return the typed text."""
        return self.entry.get()

    def set(self, text: str) -> None:
        """Replace the typed text."""
        self.entry.delete(0, "end")
        if text:
            self.entry.insert(0, text)

    def show_error(self, text: str) -> None:
        """Show an error under the box and outline it in red."""
        self._has_error = True
        self.entry.configure(border_color=theme.pair("danger"))
        self.message.configure(text=text, text_color=theme.pair("danger"))
        self.message.grid()

    def clear_error(self) -> None:
        """Remove the error and restore the helper text."""
        self._has_error = False
        self.entry.configure(border_color=theme.pair("border"))
        self.message.configure(text=self.helper, text_color=theme.pair("text_muted"))
        if not self.helper:
            self.message.grid_remove()

    def focus(self) -> None:
        """Put the keyboard cursor in the box."""
        self.entry.focus_set()


class PasswordField(Field):
    """A Field with a show/hide eye button."""

    def __init__(
        self, master, label_text: str, on_enter=None, helper: str = ""
    ) -> None:
        super().__init__(
            master, label_text, "", helper=helper, show="•", on_enter=on_enter
        )
        self._visible = False
        self.toggle = ctk.CTkButton(
            self,
            text="",
            width=40,
            height=theme.CONTROL_HEIGHT,
            corner_radius=10,
            image=icons.icon("eye", 18, "text_muted"),
            fg_color=theme.pair("surface_alt"),
            hover_color=theme.pair("border"),
            command=self._toggle,
        )
        self.toggle.grid(row=1, column=1, padx=(6, 0))
        Tooltip(self.toggle, "Show or hide the password")

    def _toggle(self) -> None:
        self._visible = not self._visible
        self.entry.configure(show="" if self._visible else "•")
        name = "eye_off" if self._visible else "eye"
        self.toggle.configure(image=icons.icon(name, 18, "text_muted"))


def segmented(
    master, values: list[str], value: str, command=None, height: int = 36
) -> ctk.CTkSegmentedButton:
    """Return an iOS-style segmented control: a white pill on a lavender track."""
    control = ctk.CTkSegmentedButton(
        master,
        values=values,
        command=command,
        height=height,
        corner_radius=10,
        font=theme.font("callout"),
        fg_color=theme.pair("primary_soft"),
        selected_color=theme.pair("segment_on"),
        selected_hover_color=theme.pair("segment_on_hover"),
        unselected_color=theme.pair("primary_soft"),
        unselected_hover_color=theme.pair("primary_soft_hover"),
        text_color=theme.pair("text"),
    )
    control.set(value)
    return control


def switch(master, text: str, value: bool, command=None) -> ctk.CTkSwitch:
    """Return an on/off switch in the app's purple."""
    widget = ctk.CTkSwitch(
        master,
        text=text,
        command=command,
        font=theme.font("body"),
        text_color=theme.pair("text"),
        progress_color=theme.pair("primary"),
        button_color=("#FFFFFF", "#F2F0F7"),
        button_hover_color=("#F4F0FF", "#FFFFFF"),
        fg_color=theme.pair("border"),
        switch_width=44,
        switch_height=24,
    )
    if value:
        widget.select()
    return widget


def option_menu(
    master, values: list[str], value: str, command=None, width: int = 200
) -> ctk.CTkOptionMenu:
    """Return a drop-down list."""
    menu = ctk.CTkOptionMenu(
        master,
        values=values,
        command=command,
        width=width,
        height=theme.CONTROL_HEIGHT,
        corner_radius=10,
        font=theme.font("body"),
        dropdown_font=theme.font("body"),
        fg_color=theme.pair("surface_alt"),
        button_color=theme.pair("surface_alt"),
        button_hover_color=theme.pair("border"),
        text_color=theme.pair("text"),
        dropdown_fg_color=theme.pair("surface"),
        dropdown_hover_color=theme.pair("primary_soft"),
        dropdown_text_color=theme.pair("text"),
    )
    menu.set(value)
    return menu


class ChipGrid(ctk.CTkFrame):
    """Selectable chips in equal columns that reflow with the width.

    multi=True allows several (symptoms); multi=False picks one.
    """

    def __init__(
        self,
        master,
        options,
        selected=(),
        multi: bool = True,
        on_change=None,
        min_width: int = 140,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.options = list(options)
        self.multi = multi
        self.on_change = on_change
        self.min_width = min_width
        self.selected = set(selected)
        self._columns = 0
        self._pending = None
        self.buttons = {}
        for option in self.options:
            chip = ctk.CTkButton(
                self,
                text=option,
                width=40,  # small base width: chips stretch to fill their column
                height=36,
                corner_radius=theme.RADIUS_CHIP,
                font=theme.font("callout"),
                border_width=1,
                command=lambda value=option: self._toggle(value),
            )
            self.buttons[option] = chip
            self._style(option)
        # Columns must fit the longest label plus the check mark, or the chips
        # would ask for more width than they have and the layout would bounce.
        longest = max(theme.font("callout").measure(option) for option in self.options)
        self.min_width = max(min_width, longest + 54)
        self.bind("<Configure>", self._reflow)
        self._place(1)

    def _style(self, option: str) -> None:
        chosen = option in self.selected
        self.buttons[option].configure(
            fg_color=theme.pair("primary_soft" if chosen else "surface_alt"),
            hover_color=theme.pair("primary_soft_hover" if chosen else "border"),
            text_color=theme.pair("primary_text" if chosen else "text"),
            border_color=theme.pair("primary" if chosen else "surface_alt"),
            image=icons.icon("check", 14, "primary_text") if chosen else None,
        )

    def _toggle(self, option: str) -> None:
        if self.multi:
            self.selected ^= {option}
        elif option in self.selected:
            self.selected = set()  # clicking the chosen one again clears it
        else:
            self.selected = {option}
        for name in self.options:
            self._style(name)
        if self.on_change:
            self.on_change(self.value())

    def value(self):
        """Return the chosen options (a list), or the one choice (multi=False)."""
        ordered = [option for option in self.options if option in self.selected]
        if self.multi:
            return ordered
        return ordered[0] if ordered else None

    def _reflow(self, event) -> None:
        width = event.width / scaling(self)
        columns = max(1, int((width + 8) // (self.min_width + 8)))
        if columns != self._columns:
            # Re-grid on a short timer, never inside the resize itself, so a
            # layout change cannot trigger itself again.
            if self._pending:
                self.after_cancel(self._pending)
            self._pending = self.after(25, lambda: self._place(columns))

    def _place(self, columns: int) -> None:
        self._pending = None
        if columns == self._columns:
            return
        self._columns = columns

        for index in range(12):
            self.columnconfigure(index, weight=0, uniform="")
        for index in range(columns):
            self.columnconfigure(index, weight=1, uniform="chips")
        for i, option in enumerate(self.options):
            self.buttons[option].grid(
                row=i // columns, column=i % columns, sticky="ew", padx=4, pady=4
            )


class OptionList(ctk.CTkFrame):
    """Large rows with a title and description (like radio cards).

    Normally one row is chosen and value is its key. With toggle (a function
    (chosen_keys, clicked_key) -> new_keys), value is a list and clicking a
    chosen row again unticks it.
    """

    def __init__(
        self,
        master,
        options: dict,
        value,
        on_change=None,
        columns: int = 1,
        toggle=None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.value = value
        self.on_change = on_change
        self.toggle = toggle
        self.rows = {}
        for index in range(columns):
            self.columnconfigure(index, weight=1, uniform="options")
        for i, (key, (title, description)) in enumerate(options.items()):
            row = ctk.CTkFrame(self, corner_radius=14, border_width=2, cursor="hand2")
            row.grid(row=i // columns, column=i % columns, sticky="ew", padx=4, pady=4)
            row.columnconfigure(0, weight=1)
            title_label = label(row, title, "headline")
            title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
            text_label = label(row, description, "footnote", "text_muted")
            text_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
            mark = ctk.CTkLabel(row, text="", width=22)
            mark.grid(row=0, column=1, rowspan=2, padx=14)
            for widget in (row, title_label, text_label, mark):
                widget.bind("<Button-1>", lambda _e, k=key: self.choose(k))
            self.rows[key] = (row, mark)
        self._restyle()

    def choose(self, key: str) -> None:
        """Select an option (or tick / untick it in a multi-choice list)."""
        self.value = self.toggle(self.value, key) if self.toggle else key
        self._restyle()
        if self.on_change:
            self.on_change(self.value)

    def _restyle(self) -> None:
        for key, (row, mark) in self.rows.items():
            chosen = key in self.value if self.toggle else key == self.value
            row.configure(
                fg_color=theme.pair("primary_soft" if chosen else "surface_alt"),
                border_color=theme.pair("primary" if chosen else "surface_alt"),
            )
            if chosen:
                image = icons.icon("check_circle", 20, "primary")
            elif self.toggle:  # an empty box says "you can tick more than one"
                image = icons.icon("circle", 20, "text_muted")
            else:
                image = None
            mark.configure(image=image)


class Stepper(ctk.CTkFrame):
    """A number with minus and plus buttons; hold a button to repeat."""

    def __init__(
        self,
        master,
        value: float,
        step: float,
        low: float,
        high: float,
        fmt: str = "{:g}",
        unit: str = "",
        on_change=None,
        role: str = "number_sm",
        value_width: int = 96,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.value = value
        self.step = step
        self.low = low
        self.high = high
        self.fmt = fmt
        self.unit = unit
        self.on_change = on_change
        self._repeat = None
        minus = icon_button(self, "minus", size=38)
        minus.grid(row=0, column=0)
        self.display = label(
            self, "", role, anchor="center", justify="center", width=value_width
        )
        self.display.grid(row=0, column=1, padx=8)
        plus = icon_button(self, "plus", size=38)
        plus.grid(row=0, column=2)
        for widget, direction in ((minus, -1), (plus, 1)):
            widget.bind("<ButtonPress-1>", lambda _e, d=direction: self._press(d))
            widget.bind("<ButtonRelease-1>", lambda _e: self._release())
        self._show()

    def _show(self) -> None:
        text = self.fmt.format(self.value)
        self.display.configure(text=f"{text} {self.unit}".strip())

    def _bump(self, direction: int) -> bool:
        new = round(self.value + direction * self.step, 2)
        if not self.low <= new <= self.high:
            return False
        self.value = new
        self._show()
        if self.on_change:
            self.on_change(self.value)
        return True

    def _press(self, direction: int) -> None:
        self._bump(direction)
        self._repeat = self.after(420, lambda: self._hold(direction))

    def _hold(self, direction: int) -> None:
        if self._bump(direction):
            self._repeat = self.after(70, lambda: self._hold(direction))

    def _release(self) -> None:
        if self._repeat:
            self.after_cancel(self._repeat)
            self._repeat = None

    def get(self) -> float:
        """Return the current value."""
        return self.value

    def set(self, value: float) -> None:
        """Show a new value."""
        self.value = value
        self._show()


class ScalePicker(ctk.CTkFrame):
    """Five big choices for a 1-5 scale, with faces for mood."""

    def __init__(
        self,
        master,
        labels: dict[int, str],
        value: int | None = None,
        on_change=None,
        faces: bool = False,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.value = value
        self.on_change = on_change
        self.faces = faces
        self.buttons = {}
        for column, (number, text) in enumerate(labels.items()):
            self.columnconfigure(column, weight=1, uniform="scale")
            widget = ctk.CTkButton(
                self,
                text=text,
                compound="top",
                width=40,  # stretches to fill its column
                height=74 if faces else 44,
                corner_radius=14,
                border_width=2,
                font=theme.font("footnote"),
                command=lambda n=number: self.choose(n),
            )
            widget.grid(row=0, column=column, sticky="ew", padx=4)
            self.buttons[number] = widget
        self.labels = labels
        self.compact = False
        self.caption = label(self, "", "footnote", "text_muted")
        self.bind("<Configure>", self._fit, add="+")
        self._restyle()

    def _fit(self, event) -> None:
        """In a narrow card, show numbers (or just faces) and name the choice below."""
        room = event.width / scaling(self) / len(self.buttons) - 8 - 28
        widest = max(theme.font("footnote").measure(t) for t in self.labels.values())
        compact = widest > room
        if compact == self.compact:
            return
        self.compact = compact
        for number, widget in self.buttons.items():
            short = "" if self.faces else str(number)
            widget.configure(text=short if compact else self.labels[number])
        if compact:
            self.caption.grid(
                row=1,
                column=0,
                columnspan=len(self.buttons),
                sticky="w",
                padx=4,
                pady=(6, 0),
            )
        else:
            self.caption.grid_remove()
        self._restyle()

    def choose(self, number: int) -> None:
        """Select a value (clicking the chosen one again clears it)."""
        self.value = None if number == self.value else number
        self._restyle()
        if self.on_change:
            self.on_change(self.value)

    def _restyle(self) -> None:
        for number, widget in self.buttons.items():
            chosen = number == self.value
            color = "primary_text" if chosen else "text_muted"
            widget.configure(
                fg_color=theme.pair("primary_soft" if chosen else "surface_alt"),
                hover_color=theme.pair("primary_soft_hover" if chosen else "border"),
                border_color=theme.pair("primary" if chosen else "surface_alt"),
                text_color=theme.pair("primary_text" if chosen else "text"),
                image=icons.icon(f"face{number}", 30, color) if self.faces else None,
            )
        names = list(self.labels.values())
        self.caption.configure(
            text=self.labels[self.value]
            if self.value
            else f"1 = {names[0]}  ·  {len(names)} = {names[-1]}"
        )


def progress_bar(
    master, value: float, color: str = "primary", height: int = 10
) -> ctk.CTkProgressBar:
    """Return a rounded progress bar that fills smoothly to `value` (0-1)."""
    bar = ctk.CTkProgressBar(
        master,
        height=height,
        corner_radius=height // 2,
        progress_color=theme.pair(color),
        fg_color=theme.pair("surface_alt"),
    )
    bar.set(0)
    target = min(max(value, 0.0), 1.0)
    anim.animate(bar, theme.SLOW, lambda t: bar.set(target * t), key=f"bar-{id(bar)}")
    return bar


# Canvas art: rings, charts, 3D ----------------------------------------------------


class ArtCanvas(tk.Canvas):
    """A Tk canvas that redraws Pillow art on resize and animates in once."""

    def __init__(
        self,
        master,
        height: int,
        width: int | None = None,
        bg: str = "surface",
        animate_in: bool = True,
    ) -> None:
        self.ui_scale = scaling(master)
        self.bg_token = bg
        super().__init__(
            master,
            height=round(height * self.ui_scale),
            width=round((width or 40) * self.ui_scale),
            bg=theme.color(bg),
            highlightthickness=0,
            bd=0,
        )
        self.progress = 0.0 if animate_in else 1.0
        self._animate_in = animate_in
        self._drawn_size = None
        self._photos: list[ImageTk.PhotoImage] = []
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event) -> None:
        size = (event.width, event.height)
        if size == self._drawn_size or event.width < 10:
            return
        first = self._drawn_size is None
        self._drawn_size = size
        if first and self._animate_in:
            anim.animate(self, theme.SLOW, self._set_progress, key=f"art-{id(self)}")
        else:
            self.redraw()

    def _set_progress(self, t: float) -> None:
        self.progress = t
        self.redraw()

    def redraw(self) -> None:
        """Clear and draw again at the current size and progress."""
        width, height = self.winfo_width(), self.winfo_height()
        if width < 10:
            return
        self.delete("all")
        self._photos = []
        # Draw animation frames at 2x supersampling (fast) and the final frame at 3x.
        graphics.SS = 3 if self.progress >= 1 else 2
        self.draw(width, height, self.progress)
        graphics.SS = 3

    def draw(self, width: int, height: int, t: float) -> None:
        """Draw the art; subclasses override this."""

    def image(
        self, pil_image, x: float, y: float, anchor: str = "nw", tags: str = ""
    ) -> int:
        """Show a Pillow image on the canvas and keep it alive."""
        photo = ImageTk.PhotoImage(pil_image)
        self._photos.append(photo)
        return self.create_image(x, y, image=photo, anchor=anchor, tags=tags)

    def text(
        self,
        x: float,
        y: float,
        text: str,
        role: str = "footnote",
        color: str = "text_muted",
        anchor: str = "center",
        **kwargs,
    ) -> int:
        """Draw crisp text in a type role and colour token."""
        return self.create_text(
            x,
            y,
            text=text,
            font=canvas_font(self, role),
            fill=theme.color(color),
            anchor=anchor,
            **kwargs,
        )


class RingView(ArtCanvas):
    """Concentric progress rings with a big number in the middle."""

    def __init__(
        self,
        master,
        size: int,
        specs: list[tuple[float, str, str]],
        thickness: int = 14,
        center: str = "",
        caption: str = "",
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=size, width=size, bg=bg)
        self.specs = specs
        self.thickness = thickness
        self.center = center
        self.caption = caption

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        size = min(width, height)
        resolved = [
            (f, theme.color(c), theme.color(track)) for f, c, track in self.specs
        ]
        art = graphics.rings(
            size,
            resolved,
            round(self.thickness * self.ui_scale),
            round(4 * self.ui_scale),
            t,
        )
        self.image(art, width / 2, height / 2, anchor="center")
        if self.center:
            offset = 9 * self.ui_scale if self.caption else 0
            self.text(width / 2, height / 2 - offset, self.center, "number_sm", "text")
        if self.caption:
            self.text(
                width / 2,
                height / 2 + 14 * self.ui_scale,
                self.caption,
                "caption",
                "text_muted",
            )

    def update_rings(self, specs, center: str = "", caption: str = "") -> None:
        """Animate to new values."""
        self.specs = specs
        self.center = center
        self.caption = caption
        anim.animate(self, theme.BASE + 120, self._set_progress, key=f"art-{id(self)}")


class LineChart(ArtCanvas):
    """A line chart with x labels, min/max labels and a hover tooltip."""

    def __init__(
        self,
        master,
        values: list[float | None],
        labels: list[str],
        low: float,
        high: float,
        color: str = "primary",
        height: int = 200,
        fmt: str = "{:.1f}",
        reference: float | None = None,
        reference_text: str = "",
        shade_from: int | None = None,
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=height, bg=bg)
        self.values = values
        self.labels = labels
        self.low = low
        self.high = high
        self.color = color
        self.fmt = fmt
        self.reference = reference
        self.reference_text = reference_text
        self.shade_from = shade_from
        self.points: list = []
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda _e: self.delete("hover"))

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        s = self.ui_scale
        pad = (round(40 * s), round(14 * s), round(12 * s), round(26 * s))
        art, self.points = graphics.line_chart(
            width,
            height,
            self.values,
            self.low,
            self.high,
            theme.color(self.color),
            theme.color("surface_alt"),
            pad=pad,
            t=t,
            reference=self.reference,
            reference_colour=theme.color("text_muted"),
            shade_from=self.shade_from,
            shade_colour=theme.color("lilac"),
        )
        self.image(art, 0, 0)
        self.text(
            pad[0] - 8 * s, pad[1], self.fmt.format(self.high), "caption", anchor="e"
        )
        self.text(
            pad[0] - 8 * s,
            height - pad[3],
            self.fmt.format(self.low),
            "caption",
            anchor="e",
        )
        if self.reference is not None and self.reference_text:
            span = self.high - self.low
            y = pad[1] + (height - pad[1] - pad[3]) * (
                1 - (self.reference - self.low) / span
            )
            self.text(
                width - pad[2], y - 9 * s, self.reference_text, "caption", anchor="e"
            )
        step = max(1, len(self.labels) // 8)
        count = max(len(self.labels) - 1, 1)
        for i, text in enumerate(self.labels):
            if i % step == 0 or i == len(self.labels) - 1:
                x = pad[0] + (width - pad[0] - pad[2]) * i / count
                self.text(x, height - 10 * s, text, "caption")

    def _hover(self, event) -> None:
        self.delete("hover")
        best = None
        for index, point in enumerate(self.points):
            if point is not None and (
                best is None
                or abs(point[0] - event.x) < abs(self.points[best][0] - event.x)
            ):
                best = index
        if best is None or abs(self.points[best][0] - event.x) > 40 * self.ui_scale:
            return
        x, y = self.points[best]
        s = self.ui_scale
        self.create_line(
            x,
            4,
            x,
            self.winfo_height() - 22 * s,
            fill=theme.color("border"),
            tags="hover",
        )
        text = f"{self.labels[best]}: {self.fmt.format(self.values[best])}"
        box_w = (len(text) * 7 + 18) * s
        left = min(max(x - box_w / 2, 2), self.winfo_width() - box_w - 2)
        top = max(y - 40 * s, 2)
        self.create_rectangle(
            left,
            top,
            left + box_w,
            top + 26 * s,
            fill=theme.color("toast"),
            outline="",
            tags="hover",
        )
        self.create_text(
            left + box_w / 2,
            top + 13 * s,
            text=text,
            fill=theme.color("on_toast"),
            font=canvas_font(self, "footnote"),
            tags="hover",
        )


class BarChart(ArtCanvas):
    """Rounded bars with day labels and the value of the highlighted bar."""

    def __init__(
        self,
        master,
        values: list[float],
        labels: list[str],
        maximum: float,
        color: str = "primary",
        height: int = 170,
        goal: float | None = None,
        highlight: int | None = None,
        fmt: str = "{:g}",
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=height, bg=bg)
        self.values = values
        self.labels = labels
        self.maximum = maximum
        self.color = color
        self.goal = goal
        self.highlight = highlight
        self.fmt = fmt

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        s = self.ui_scale
        pad = (round(8 * s), round(22 * s), round(8 * s), round(24 * s))
        art, tops = graphics.bar_chart(
            width, height, self.values, self.maximum, theme.color(self.color), theme.color("surface_alt"),
            pad=pad, t=t, goal=self.goal, goal_colour=theme.color("text_muted"),
            highlight=self.highlight, highlight_colour=theme.color("primary"),
        )  # fmt: skip
        self.image(art, 0, 0)
        for i, (x, y) in enumerate(tops):
            self.text(x, height - 10 * s, self.labels[i], "caption")
            if self.values[i] and t >= 1:
                self.text(
                    x, y - 9 * s, self.fmt.format(self.values[i]), "caption", "text"
                )


class HormoneChart(ArtCanvas):
    """The schematic hormone curves for one cycle, with a "today" marker."""

    SERIES = (
        ("Estrogen", "activity"),
        ("Progesterone", "primary"),
        ("LH", "fertile"),
        ("FSH", "warning"),
    )

    def __init__(
        self,
        master,
        cycle_length: int,
        today_day: int | None,
        levels_fn,
        phase_bands: list,
        height: int = 210,
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=height, bg=bg)
        self.cycle_length = cycle_length
        self.today_day = today_day
        self.levels_fn = levels_fn
        self.phase_bands = phase_bands

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        s = self.ui_scale
        points = 120
        series = []
        for name, color in self.SERIES:
            values = []
            for i in range(points + 1):
                day = 1 + (self.cycle_length - 1) * i / points
                values.append(self.levels_fn(day, self.cycle_length)[name])
            series.append((values, theme.color(color)))
        marker = None
        if self.today_day is not None:
            marker = min(max((self.today_day - 1) / (self.cycle_length - 1), 0), 1)
        bands = [(a, b, theme.color(c)) for a, b, c in self.phase_bands]
        pad = (round(10 * s), round(14 * s), round(10 * s), round(40 * s))
        art = graphics.multi_line(
            width,
            height,
            series,
            theme.color("surface_alt"),
            pad=pad,
            t=t,
            marker=marker,
            marker_colour=theme.color("text"),
            bands=bands,
        )
        self.image(art, 0, 0)
        x = pad[0]
        for name, color in self.SERIES:
            self.create_oval(
                x,
                height - 14 * s,
                x + 9 * s,
                height - 5 * s,
                fill=theme.color(color),
                outline="",
            )
            item = self.text(
                x + 14 * s, height - 10 * s, name, "caption", "text", anchor="w"
            )
            x = self.bbox(item)[2] + 16 * s
        if marker is not None:
            mx = pad[0] + (width - pad[0] - pad[2]) * marker
            self.text(mx, pad[1] - 6 * s, "Today", "caption", "text", anchor="s")


class CalendarView(ArtCanvas):
    """A month calendar drawn on one canvas: smooth circles, fast to redraw.

    style(day) returns (fill colour token or None, text colour token).
    Clicking a day calls on_select(day).
    """

    ROW = 46
    HEADER = 30

    def __init__(
        self,
        master,
        year: int,
        month: int,
        style,
        today,
        selected,
        on_select,
        bg: str = "surface",
    ) -> None:
        super().__init__(
            master, height=self.HEADER + 6 * self.ROW, bg=bg, animate_in=False
        )
        self.year = year
        self.month = month
        self.style = style
        self.today = today
        self.selected = selected
        self.on_select = on_select
        self.cells: list[tuple[float, float, float, float, object]] = []
        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._click)

    def show(self, year: int, month: int, selected) -> None:
        """Change the month or the selected day and redraw."""
        self.year, self.month, self.selected = year, month, selected
        self.redraw()

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        s = self.ui_scale
        header = self.HEADER * s
        row_h = self.ROW * s
        cell_w = width / 7
        radius = min(cell_w, row_h) * 0.42
        weeks = calendar_logic.month_grid(self.year, self.month)
        ss = graphics.SS
        image = Image.new("RGBA", (width * ss, height * ss), (0, 0, 0, 0))
        pen = ImageDraw.Draw(image)
        self.cells = []
        texts = []
        for row, week in enumerate(weeks):
            for column, day in enumerate(week):
                if day is None:
                    continue
                cx = (column + 0.5) * cell_w
                cy = header + (row + 0.5) * row_h
                fill, text = self.style(day)
                box = [
                    (cx - radius) * ss,
                    (cy - radius) * ss,
                    (cx + radius) * ss,
                    (cy + radius) * ss,
                ]
                if fill:
                    pen.ellipse(box, fill=graphics.rgb(theme.color(fill)))
                ring = (
                    "primary"
                    if day == self.today
                    else ("text_muted" if day == self.selected else None)
                )
                if ring:
                    pen.ellipse(
                        box,
                        outline=graphics.rgb(theme.color(ring)),
                        width=round(2.5 * s * ss),
                    )
                bold = day in (self.today, self.selected)
                texts.append((cx, cy, str(day.day), text, bold))
                self.cells.append(
                    (
                        cx - cell_w / 2,
                        cy - row_h / 2,
                        cx + cell_w / 2,
                        cy + row_h / 2,
                        day,
                    )
                )
        self.image(image.resize((width, height), Image.LANCZOS), 0, 0)
        for column, name in enumerate(calendar_logic.weekday_names()):
            self.text(
                (column + 0.5) * cell_w, header / 2, name, "footnote", "text_muted"
            )
        for cx, cy, number, color, bold in texts:
            self.text(cx, cy, number, "headline" if bold else "body", color)

    def _click(self, event) -> None:
        for x0, y0, x1, y1, day in self.cells:
            if x0 <= event.x < x1 and y0 <= event.y < y1:
                self.on_select(day)
                return


class WaterGlass(ArtCanvas):
    """A glass that fills smoothly and keeps a gentle wave moving."""

    def __init__(
        self,
        master,
        fraction: float,
        size: tuple[int, int] = (92, 128),
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=size[1], width=size[0], bg=bg)
        self.fraction = fraction
        self.shown = 0.0
        self.phase = 0.0
        anim.loop(self, self._wave, 50)

    def _wave(self, seconds: float) -> None:
        self.phase = seconds * 2.2
        if self.winfo_width() > 10:
            self.redraw()

    def set_fraction(self, fraction: float) -> None:
        """Fill (or empty) smoothly to a new level."""
        start = self.shown
        self.fraction = fraction
        anim.animate(
            self,
            theme.SLOW,
            lambda t: setattr(self, "shown", anim.lerp(start, fraction, t)),
            key=f"glass-{id(self)}",
        )

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        if self.progress >= 1 and self.shown == 0 and self.fraction:
            self.set_fraction(self.fraction)
        art = graphics.water_glass(
            width,
            height,
            self.shown,
            theme.color("water"),
            theme.color("text_muted"),
            self.phase,
        )
        self.image(art, 0, 0)


class GaugeView(ArtCanvas):
    """A half-circle gauge whose needle sweeps to the value."""

    def __init__(
        self,
        master,
        fraction: float,
        bands: list[tuple[float, float, str]],
        height: int = 150,
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=height, bg=bg)
        self.fraction = fraction
        self.bands = bands

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        bands = [(a, b, theme.color(c)) for a, b, c in self.bands]
        art = graphics.gauge(
            width,
            height,
            self.fraction,
            bands,
            theme.color("surface_alt"),
            theme.color("text"),
            anim.ease_out_back(t) if t < 1 else 1.0,
        )
        self.image(art, 0, 0)


class Hero3D(ArtCanvas):
    """A scene of floating 3D objects, optionally on the purple gradient.

    objects: dicts with kind ("sphere", "torus", "cube"), size (px), x and y
    (0-1, the object's centre), and optional amp (px) and phase (radians).
    texts: (text, role, colour token, x 0-1, y 0-1, anchor) shown on top.
    """

    def __init__(
        self,
        master,
        objects: list[dict],
        height: int,
        width: int | None = None,
        gradient: bool = True,
        texts=(),
        bg: str = "surface",
        deep: bool = False,
        radius: int = 0,
        text_width: float = 0.8,
    ) -> None:
        super().__init__(master, height=height, width=width, bg=bg, animate_in=False)
        self.objects = objects
        self.gradient = gradient
        self.texts = texts
        self.deep = deep  # darker gradient behind white text (see render3d)
        self.radius = radius
        self.text_width = text_width  # share of the width text may use
        self.items: list[tuple[int, int, dict, float]] = []
        anim.loop(self, self._float, 33)

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        if self.gradient:
            dark = ctk.get_appearance_mode() == "Dark"
            radius = round(self.radius * self.ui_scale)
            backdrop = render3d.gradient(width, height, dark, self.deep, radius)
            self.image(backdrop, 0, 0)
        self.items = []
        for spec in self.objects:
            size = round(spec["size"] * self.ui_scale)
            kind = spec["kind"]
            if kind == "sphere":
                art = render3d.sphere(
                    size,
                    spec.get("base", render3d.PURPLE),
                    spec.get("glow", render3d.LILAC),
                )
            elif kind == "torus":
                art = render3d.torus(size)
            else:
                art = render3d.cube(size)
            cx, cy = spec["x"] * width, spec["y"] * height
            shadow = render3d.shadow(size, max(12, size // 4))
            shadow_id = self.image(shadow, cx, cy + size * 0.62, anchor="center")
            object_id = self.image(art, cx, cy, anchor="center")
            self.items.append((object_id, shadow_id, spec, cy))
        for text, role, color, x, y, anchor in self.texts:
            self.text(
                x * width,
                y * height,
                text,
                role,
                color,
                anchor=anchor,
                width=width * self.text_width,
            )

    def _float(self, seconds: float) -> None:
        for object_id, _shadow_id, spec, base_y in self.items:
            amp = spec.get("amp", 8) * self.ui_scale
            offset = amp * math.sin(seconds * 1.6 + spec.get("phase", 0.0))
            x, _ = self.coords(object_id) or (0, 0)
            self.coords(object_id, x, base_y + offset)


# Feedback: toasts, dialogs, tooltips ------------------------------------------------


def fast_scroll(scrollable: ctk.CTkScrollableFrame) -> None:
    """Make a CTkScrollableFrame's scrollbar redraw lazily (a big speed-up).

    CustomTkinter 6.0's scrollbar forces a full layout pass (update_idletasks)
    every time the content grows, which made each page take over a second to
    open. Here the scrollbar redraws at most once per idle moment instead.
    This touches CustomTkinter internals, so the version is pinned in
    requirements.txt.
    """
    bar = scrollable._scrollbar
    bar._canvas.update_idletasks = lambda: None
    bar.pending_draw = False

    def set_lazily(start, end) -> None:
        bar._start_value, bar._end_value = float(start), float(end)
        if not bar.pending_draw:
            bar.pending_draw = True
            bar.after_idle(draw)

    def draw() -> None:
        bar.pending_draw = False
        try:
            bar._draw()
        except tk.TclError:
            pass  # the page was closed

    scrollable._parent_canvas.configure(yscrollcommand=set_lazily)


def run_in_background(widget, work, on_done) -> None:
    """Run slow work (password hashing) without freezing the window.

    `work` runs on a background thread; on_done(result, error) is then called
    back on the main thread. Tkinter is not thread-safe, so `work` must not
    touch any widget.
    """
    outcome: dict = {}

    def worker() -> None:
        try:
            outcome["result"] = work()
        except Exception as error:  # handed back to the screen to show
            outcome["error"] = error

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def check() -> None:
        if thread.is_alive():
            widget.after(30, check)
        else:
            on_done(outcome.get("result"), outcome.get("error"))

    widget.after(30, check)


def toast(app, text: str, tone: str = "good") -> None:
    """Slide a short message up from the bottom of the window, then away."""
    old = getattr(app, "_toast", None)
    if old is not None:
        try:
            old.destroy()
        except tk.TclError:
            pass
    pill = ctk.CTkFrame(app, fg_color=theme.pair("toast"), corner_radius=16)
    ctk.CTkLabel(
        pill, text="", image=icons.icon(TONE_ICONS[tone], 18, "on_toast")
    ).grid(row=0, column=0, padx=(16, 8), pady=10)
    label(pill, text, "callout", "on_toast").grid(
        row=0, column=1, padx=(0, 18), pady=10
    )
    app._toast = pill
    pill.place(relx=0.5, rely=1.0, anchor="s", y=80)
    anim.animate(
        pill,
        360,
        lambda t: pill.place_configure(y=anim.lerp(80, -28, t)),
        ease=anim.ease_out_back,
        key="toast",
    )

    def leave() -> None:
        try:
            if pill.winfo_exists():
                anim.animate(
                    pill,
                    220,
                    lambda t: pill.place_configure(y=anim.lerp(-28, 80, t)),
                    ease=anim.ease_in_out_cubic,
                    key="toast",
                    done=pill.destroy,
                )
        except tk.TclError:
            pass

    pill.after(2600, leave)


class Tooltip:
    """A small label that appears after hovering over a widget."""

    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window = None
        self.pending = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._hide()  # never two timers at once
        self.pending = self.widget.after(450, self._show)

    def _show(self) -> None:
        self.pending = None
        if self.window is not None or not self.widget.winfo_viewable():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2 - 13
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.window,
            text=self.text,
            bg=theme.color("toast"),
            fg=theme.color("on_toast"),
            font=canvas_font(self.widget, "footnote"),
            padx=10,
            pady=4,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self.pending:
            self.widget.after_cancel(self.pending)
            self.pending = None
        if self.window is not None:
            self.window.destroy()
            self.window = None


class Dialog(ctk.CTkToplevel):
    """A small modal window: a title, a message, optional fields and buttons."""

    def __init__(
        self,
        app,
        title: str,
        message: str,
        action: str,
        danger: bool = False,
        password: bool = False,
        code: str | None = None,
        cancel: str = "Cancel",
    ) -> None:
        super().__init__(app)
        self.result = None
        self.title(title)
        self.configure(fg_color=theme.pair("surface"))
        self.resizable(False, False)
        self.transient(app)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=26, pady=24)
        body.columnconfigure(0, weight=1)
        label(body, title, "title3").grid(row=0, column=0, sticky="w")
        label(body, message, "body", "text_muted", wraplength=360).grid(
            row=1, column=0, sticky="w", pady=(6, 14)
        )
        self.field = None
        row = 2
        if password:
            self.field = PasswordField(body, "Password", on_enter=self._ok)
            self.field.grid(row=row, column=0, sticky="ew", pady=(0, 14))
            row += 1
        if code:
            code_box = ctk.CTkLabel(
                body,
                text=code,
                font=theme.font("mono"),
                text_color=theme.pair("primary_text"),
                fg_color=theme.pair("primary_soft"),
                corner_radius=12,
                height=58,
            )
            code_box.grid(row=row, column=0, sticky="ew", pady=(0, 8))
            button(
                body,
                "Copy Code",
                lambda: self._copy(code),
                kind="secondary",
                icon="download",
            ).grid(row=row + 1, column=0, sticky="w", pady=(0, 14))
            row += 2
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=row, column=0, sticky="e")
        if cancel:
            button(actions, cancel, self.destroy, kind="plain", width=110).grid(
                row=0, column=0, padx=(0, 8)
            )
        button(
            actions, action, self._ok, kind="danger" if danger else "primary", width=130
        ).grid(row=0, column=1)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(30, lambda: self._centre(app))

    def _centre(self, app) -> None:
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.lift()
        self.grab_set()
        if self.field:
            self.field.focus()

    def _copy(self, code: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(code)
        toast(self.master, "Code copied")

    def _ok(self) -> None:
        self.result = self.field.get() if self.field else True
        self.destroy()


def confirm(app, title: str, message: str, action: str, danger: bool = False) -> bool:
    """Ask a yes/no question in a modal dialog; True when confirmed."""
    dialog = Dialog(app, title, message, action, danger=danger)
    app.wait_window(dialog)
    return bool(dialog.result)


def ask_password(
    app, title: str, message: str, action: str, danger: bool = False
) -> str | None:
    """Ask for the password in a modal dialog; None when cancelled."""
    dialog = Dialog(app, title, message, action, danger=danger, password=True)
    app.wait_window(dialog)
    return dialog.result if isinstance(dialog.result, str) else None


def show_code(app, code: str) -> None:
    """Show a new recovery code once, with a copy button."""
    dialog = Dialog(
        app,
        "Your new recovery code",
        "Write it down or store it in a password manager. It is shown only once and "
        "replaces your old code.",
        "I Saved It",
        code=code,
        cancel="",
    )
    app.wait_window(dialog)


# Layout -------------------------------------------------------------------------------


progressive_build = False  # Page sets this while a page is first opening


class ResponsiveGrid(ctk.CTkFrame):
    """Cards in equal columns; the column count follows the available width."""

    def __init__(
        self,
        master,
        min_column: int = 300,
        max_columns: int = 3,
        gap: int = theme.GUTTER,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.min_column = min_column
        self.max_columns = max_columns
        self.gap = gap
        self.items: list[list] = []  # [card or card-making function, span, shrink]
        self.ready = 0  # how many items are built and shown
        self.progressive = progressive_build
        self._streaming = False
        # Guess the width from the window, so cards are laid out once in the
        # right columns instead of once in one column and again in three.
        window = self.winfo_toplevel()
        rail = (
            theme.RAIL_WIDTH
            if getattr(window, "compact", False)
            else theme.SIDEBAR_WIDTH
        )
        guess = window.winfo_width() / scaling(self) - rail - 2 * theme.PAGE_PAD - 16
        self.columns = self._columns_for(min(guess, theme.CONTENT_MAX_WIDTH))
        self._pending = None
        self.bind("<Configure>", self._on_configure)

    def _columns_for(self, width: float) -> int:
        """Return how many columns fit in `width` (logical pixels)."""
        fit = int((width + self.gap) // (self.min_column + self.gap))
        return max(1, min(self.max_columns, fit))

    def add(self, card, span: int = 1, shrink: bool = False) -> None:
        """Add a card spanning columns; `card` may be a widget or a function.

        A function (e.g. lambda: self._week_card(grid)) builds the card later.
        While a page is first opening (progressive_build is True) such cards
        are built one per idle moment, so the page appears at once and its
        cards arrive in sequence instead of freezing the window.
        shrink=True lets a wide card narrow to fill the rest of a row instead
        of leaving a hole and wrapping (e.g. a chart next to a form).
        """
        self.items.append([card, span, shrink])
        if self.progressive:
            if not self._streaming:
                self._streaming = True
                self.after(1, self._build_next)
            return
        if not isinstance(card, tk.Misc):
            self.items[-1][0] = card()
        self.ready = len(self.items)
        self._layout(self.columns)

    def _build_next(self) -> None:
        """Build and show the next waiting card, then schedule the one after."""
        try:
            if not self.winfo_exists() or self.ready >= len(self.items):
                self._streaming = False
                return
            entry = self.items[self.ready]
            if not isinstance(entry[0], tk.Misc):
                entry[0] = entry[0]()
            self.ready += 1
            self._layout(self.columns)
        except tk.TclError:
            return  # the page was closed while cards were arriving
        # Via an idle callback, so Tk paints the card before building the next.
        self.after(1, lambda: self.after_idle(self._build_next))

    def _on_configure(self, event) -> None:
        columns = self._columns_for(event.width / scaling(self))
        if columns != self.columns:
            # Deferred, so a re-layout never runs inside the resize that caused it.
            if self._pending:
                self.after_cancel(self._pending)
            self._pending = self.after(25, lambda: self._relayout(columns))

    def _relayout(self, columns: int) -> None:
        self._pending = None
        if columns != self.columns:
            self._layout(columns)

    def _layout(self, columns: int) -> None:
        self.columns = columns
        for index in range(self.max_columns):
            weight = 1 if index < columns else 0
            self.columnconfigure(
                index, weight=weight, uniform="cards" if weight else ""
            )
        row, column = 0, 0
        for widget, span, shrink in self.items[: self.ready]:
            span = min(span, columns)
            if column + span > columns:
                if shrink and column > 0:
                    span = columns - column
                else:
                    row, column = row + 1, 0
            widget.grid(
                row=row,
                column=column,
                columnspan=span,
                sticky="nsew",
                padx=(
                    0 if column == 0 else self.gap / 2,
                    0 if column + span == columns else self.gap / 2,
                ),
                pady=(0, self.gap),
            )
            column += span
            if column >= columns:
                row, column = row + 1, 0


class DateSwitcher(ctk.CTkFrame):
    """Back and forward arrows around a date; logging past days is one click away."""

    def __init__(self, master, day: date, on_change, today: date) -> None:
        super().__init__(
            master,
            fg_color=theme.pair("surface"),
            corner_radius=12,
            border_width=1,
            border_color=theme.pair("border"),
        )
        self.day = day
        self.today = today
        self.on_change = on_change
        icon_button(
            self,
            "chevron_left",
            lambda: self._move(-1),
            size=34,
            kind="ghost",
            tooltip="Previous day",
        ).grid(row=0, column=0, padx=4, pady=4)
        self.text = label(
            self, "", "headline", anchor="center", justify="center", width=150
        )
        self.text.grid(row=0, column=1)
        # Clicking the date jumps back to today.
        self.text.bind("<Button-1>", lambda _e: self._move((today - self.day).days))
        self.forward = icon_button(
            self,
            "chevron_right",
            lambda: self._move(1),
            size=34,
            kind="ghost",
            tooltip="Next day",
        )
        self.forward.grid(row=0, column=2, padx=4, pady=4)
        self._show()

    def _show(self) -> None:
        if self.day == self.today:
            text = "Today"
        elif self.day == self.today - timedelta(days=1):
            text = "Yesterday"
        else:
            text = self.day.strftime("%a, %b %d")
        self.text.configure(text=text, cursor="" if text == "Today" else "hand2")
        at_today = self.day >= self.today
        self.forward.configure(
            state="disabled" if at_today else "normal",
            # A faded arrow shows there is no "tomorrow" to log yet.
            image=icons.icon(
                "chevron_right", 18, "border" if at_today else "primary_text"
            ),
        )

    def _move(self, days: int) -> None:
        new_day = self.day + timedelta(days=days)
        if new_day > self.today or days == 0:
            return
        self.day = new_day
        self._show()
        self.on_change(new_day)
