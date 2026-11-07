"""Reusable pieces in the app's style, from buttons to 3D art.

Cards, buttons, fields, chips, steppers, rings, charts, 3D art, toasts and
dialogs. Every screen builds from these, so spacing, colours and motion stay the same
everywhere. Colours come from theme.py tokens, never raw hex.
"""

import colorsys
import math
import threading
import tkinter as tk
from datetime import date, timedelta
from functools import lru_cache
from typing import override

import customtkinter as ctk
from customtkinter.windows.widgets.core_rendering import CTkCanvas
from PIL import Image, ImageDraw, ImageTk

from tracker import calendar_logic
from tracker.ui import anim, effects, graphics, icons, render3d, sfx, speech, theme

# tone: (strong colour, soft background)
TONES = {
    "good": ("success", "success_soft"),
    "warning": ("warning", "warning_soft"),
    "danger": ("danger", "danger_soft"),
    "info": ("primary_text", "primary_soft"),
}
TONE_ICONS = {"good": "check", "warning": "alert", "danger": "alert", "info": "info"}
TOAST_MS = 2600
LONG_TOAST_MS = 8000
long_messages = False  # "Keep messages on screen longer"
speak_messages = False  # "Read messages aloud"
speak_focus = False  # "Read what the keyboard reaches"
calendar_symbols = False  # letters on the calendar, so colour is never the only cue

# CustomTkinter 6.0's drop-down lists and scrollbars force a layout pass of the
# whole window each time they draw (update_idletasks), so a card with one took
# up to half a second longer to appear. Tk draws them at the next idle moment
# anyway, so that forced pass is switched off. (The version is pinned.)
CTkCanvas.update_idletasks = lambda self: None
FOCUS_BORDER = 2


def configure(settings: dict) -> None:
    """Copy the accessibility settings these widgets follow."""
    global long_messages, speak_messages, speak_focus, calendar_symbols
    long_messages = settings["long_messages"]
    speak_messages = settings["speak_messages"]
    speak_focus = settings["speak_focus"]
    calendar_symbols = (
        settings["calendar_symbols"]
        or settings["high_contrast"]
        or settings["color_vision"] != "none"
    )


def hue_rgb(hue: float, saturation: float, value: float) -> tuple[int, int, int]:
    """Return an (r, g, b) colour from a hue, for 3D art."""
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
    return round(r * 255), round(g * 255), round(b * 255)


def mix(first: str, second: str, share: float) -> str:
    """Blend share of the second "#rrggbb" colour into the first."""
    return anim.lerp_color(first, second, share)


def glass_color(backdrop: str) -> str:
    """Return a pill colour for a banner: its backdrop, dark enough for white text."""
    shade = mix(backdrop, "#FFFFFF", 0.1)
    for _ in range(12):
        if theme.contrast(shade, "#FFFFFF") >= theme.READABLE_RATIO:
            break
        shade = mix(shade, "#000000", 0.14)
    return shade


# Keyboard access ----------------------------------------------------------------------


def _ensure_visible(widget) -> None:
    """Scroll the page so a widget the keyboard reached is on screen."""
    node = widget
    while node is not None:
        if hasattr(node, "ensure_visible"):
            node.ensure_visible(widget)
            return
        node = node.master


def keyboard(widget, activate, name: str = "") -> None:
    """Let the keyboard reach a CustomTkinter control and use it.

    Tab moves to it, Enter or Space uses it, and a ring in the focus colour shows
    where you are. CustomTkinter's controls are canvases that skip Tab by default.

    Args:
        widget: A CTkButton, CTkFrame, CTkSwitch or similar control.
        activate: Called when Enter or Space is pressed.
        name: What the control is called, for reading aloud.
    """
    canvas = widget._canvas
    canvas.configure(takefocus=1)
    uses_border = isinstance(widget, (ctk.CTkButton, ctk.CTkFrame))
    if not uses_border:
        canvas.configure(
            highlightthickness=2,
            highlightbackground=canvas.cget("bg"),
            highlightcolor=theme.color("focus"),
        )

    def use(_event) -> str:
        activate()
        return "break"

    def focus_in(_event) -> None:
        if uses_border:
            widget.rest_border = (
                widget.cget("border_width"),
                widget.cget("border_color"),
            )
            widget.configure(
                border_width=FOCUS_BORDER, border_color=theme.pair("focus")
            )
        _ensure_visible(widget)
        if speak_focus and name:
            speech.speak(name)

    def focus_out(_event) -> None:
        if uses_border and hasattr(widget, "rest_border"):
            width, color = widget.rest_border
            widget.configure(border_width=width, border_color=color)

    for key in ("<Return>", "<space>"):
        canvas.bind(key, use, add="+")
    canvas.bind("<FocusIn>", focus_in, add="+")
    canvas.bind("<FocusOut>", focus_out, add="+")


def _busy(widget) -> None:
    """Tell the window a key was pressed (it pauses background work)."""
    note = getattr(widget.winfo_toplevel(), "note_input", None)
    if note is not None:
        note()


def _next_focus(event) -> str:
    """Move on with Tab instead of typing a tab character."""
    _busy(event.widget)
    event.widget.tk_focusNext().focus_set()
    return "break"


def _previous_focus(event) -> str:
    _busy(event.widget)
    event.widget.tk_focusPrev().focus_set()
    return "break"


def tab_moves_on(text_widget) -> None:
    """Make Tab leave a text box, so keyboard users are never trapped inside it."""
    text_widget.bind("<Tab>", _next_focus)
    text_widget.bind("<Shift-Tab>", _previous_focus)


def spoken_text(widget) -> list[str]:
    """Return what a widget and its children say, top to bottom, left to right."""
    if isinstance(widget, ArtCanvas):
        text = widget.spoken()
        return [text] if text else []
    if isinstance(widget, ctk.CTkEntry):
        return [f"Text box: {widget.get()}"] if widget.get() else ["Empty text box"]
    if isinstance(widget, ctk.CTkSegmentedButton):
        return [f"Choice, {widget.get()} is selected"]
    if isinstance(widget, ctk.CTkSwitch):
        state = "on" if widget.get() else "off"
        return [f"Switch: {widget.cget('text')}, {state}"]
    if isinstance(widget, ctk.CTkButton):
        text = widget.cget("text")
        return [f"Button: {text}"] if text else []
    if isinstance(widget, ctk.CTkLabel):
        text = widget.cget("text")
        return [text] if text else []
    found: list[str] = []
    children = [
        child
        for child in widget.winfo_children()
        if child.winfo_ismapped() and not isinstance(child, (tk.Scrollbar,))
    ]
    children.sort(key=lambda child: (child.winfo_rooty() // 12, child.winfo_rootx()))
    for child in children:
        found.extend(spoken_text(child))
    return found


def scaling(widget: tk.Misc) -> float:
    """Return CustomTkinter's widget scaling (1.0 at 100% display scaling)."""
    return ctk.ScalingTracker.get_widget_scaling(widget)


def canvas_font(widget: tk.Misc, role: str) -> tuple:
    """Return a Tk font tuple for canvas text, scaled like CTk widgets."""
    size, weight, kind = theme.TYPE_SCALE[role]
    return (theme.face(kind), -round(theme.sized(size) * scaling(widget)), weight)


def label(
    master,
    text: str,
    role: str = "body",
    color: str = "text",
    reserve: int = 0,
    **kwargs,
) -> ctk.CTkLabel:
    """Return a left-aligned text label in a type role and colour token.

    With wraplength, the text wraps at that width at most, and narrower when
    its container is narrower, so long text never pushes a card wider. `reserve`
    keeps that many pixels free for something to the label's right.
    """
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    widget = ctk.CTkLabel(
        master, text=text, font=theme.font(role), text_color=theme.pair(color), **kwargs
    )
    if "wraplength" in kwargs:
        widest = kwargs["wraplength"]
        seen = {"x": None}

        def fit(_event=None) -> None:
            # The room from the label's left edge to the container's right edge.
            room = master.winfo_width() - widget.winfo_x()
            wrap = max(80, min(widest, room / scaling(widget) - 12 - reserve))
            if room > 1 and abs(wrap - widget.cget("wraplength")) > 2:
                widget.configure(wraplength=wrap)

        def moved(_event) -> None:
            # Only a change of position matters here: reacting to a change of size
            # could make the label and its container keep resizing each other.
            if widget.winfo_x() != seen["x"]:
                seen["x"] = widget.winfo_x()
                fit()

        master.bind("<Configure>", fit, add="+")
        widget.bind("<Configure>", moved, add="+")
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
    widget = ctk.CTkButton(
        master,
        text=text,
        command=sfx.with_sound(command, "click"),
        image=image,
        compound="left",
        height=theme.control_height(height),
        width=width,
        corner_radius=theme.RADIUS_CONTROL,
        font=theme.font("headline"),
        fg_color="transparent" if fill == "transparent" else theme.pair(fill),
        hover_color=theme.pair(hover),
        text_color=theme.pair(text_color),
        text_color_disabled=theme.pair("text_muted"),
        **kwargs,
    )
    keyboard(widget, widget.invoke, f"{text}, button")
    return widget


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
    grown = theme.control_height(size)
    widget = ctk.CTkButton(
        master,
        text="",
        command=sfx.with_sound(command, "click"),
        image=icons.icon(name, 18, color),
        width=grown,
        height=grown,
        corner_radius=theme.RADIUS_CONTROL,
        fg_color="transparent" if fill == "transparent" else theme.pair(fill),
        hover_color=theme.pair(hover),
    )
    if tooltip:
        Tooltip(widget, tooltip)
    if command is not None:
        keyboard(widget, widget.invoke, f"{tooltip or name}, button")
    return widget


def small_button(master, text: str, command) -> ctk.CTkButton:
    """Return a compact button for quick choices, such as a common food."""
    widget = ctk.CTkButton(
        master,
        text=text,
        command=sfx.with_sound(command, "click"),
        width=40,
        height=theme.control_height(34),
        corner_radius=theme.RADIUS_CHIP,
        font=theme.font("footnote"),
        fg_color=theme.pair("surface_alt"),
        hover_color=theme.pair("primary_soft"),
        text_color=theme.pair("text"),
    )
    keyboard(widget, widget.invoke, f"{text}, button")
    return widget


def tile_button(
    master, text: str, icon_name: str, command, tint: bool = True, height: int = 86
) -> ctk.CTkButton:
    """Return a large square-ish button with a coloured icon above its label."""
    strong, soft = theme.TOPIC_TOKENS.get(icon_name, theme.DEFAULT_TOPIC)
    widget = ctk.CTkButton(
        master,
        text=text,
        image=icons.icon(icon_name, 26, strong if tint else "primary_text"),
        compound="top",
        width=60,  # stretches to fill its column
        height=theme.control_height(height),
        corner_radius=16,
        font=theme.font("callout"),
        fg_color=theme.pair("surface_alt"),
        hover_color=theme.pair(soft if tint else "primary_soft"),
        text_color=theme.pair("text"),
        command=sfx.with_sound(command, "click"),
    )
    keyboard(widget, widget.invoke, f"{text}, button")
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
            border_width=theme.border_width,
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
                strong, soft = theme.TOPIC_TOKENS.get(icon, theme.DEFAULT_TOPIC)
                tile = ctk.CTkLabel(
                    head,
                    text="",
                    image=icons.icon(icon, 18, strong),
                    width=34,
                    height=34,
                    corner_radius=10,
                    fg_color=theme.pair(soft),
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
        effects.add_glow(self)


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
        wraplength=230,  # long notes wrap instead of pushing the card wider
        justify="left",
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
            height=theme.control_height(),
            width=width or 60,  # stretches to fill; small so narrow cards fit
            corner_radius=10,
            border_width=theme.border_width,
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
        self.entry.bind("<FocusIn>", self._focus_in, add="+")
        self.entry.bind("<FocusOut>", lambda _e: self._border("border"), add="+")
        self._has_error = False
        self.label_text = label_text

    def _focus_in(self, _event) -> None:
        self._border("focus" if theme.high_contrast else "primary")
        _ensure_visible(self)
        if speak_focus:
            speech.speak(f"{self.label_text}, text box. {self.helper}")

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
        if speak_messages:
            speech.speak(text)

    def clear_error(self) -> None:
        """Remove the error and restore the helper text."""
        self._has_error = False
        self.entry.configure(border_color=theme.pair("border"))
        self.message.configure(text=self.helper, text_color=theme.pair("text_muted"))
        if not self.helper:
            self.message.grid_remove()

    def focus(self) -> None:
        """Put the keyboard cursor in the box."""
        try:
            self.entry.focus_set()
        except tk.TclError:
            pass  # the screen moved on before the delayed focus arrived


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
            height=theme.control_height(),
            corner_radius=10,
            image=icons.icon("eye", 18, "text_muted"),
            fg_color=theme.pair("surface_alt"),
            hover_color=theme.pair("border"),
            command=sfx.with_sound(self._toggle, "toggle"),
        )
        self.toggle.grid(row=1, column=1, padx=(6, 0))
        Tooltip(self.toggle, "Show or hide the password")
        keyboard(self.toggle, self.toggle.invoke, "Show or hide the password, button")

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
        command=sfx.with_sound(command, "toggle"),
        height=theme.control_height(height),
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
    for name, inner in control._buttons_dict.items():
        keyboard(inner, inner.invoke, f"{name}, choice")
    return control


def switch(master, text: str, value: bool, command=None) -> ctk.CTkSwitch:
    """Return an on/off switch in the app's purple."""
    widget = ctk.CTkSwitch(
        master,
        text=text,
        command=sfx.with_sound(command, "toggle"),
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
    keyboard(widget, widget.toggle, f"{text}, switch")
    return widget


def option_menu(
    master, values: list[str], value: str, command=None, width: int = 200
) -> ctk.CTkOptionMenu:
    """Return a drop-down list."""
    menu = ctk.CTkOptionMenu(
        master,
        values=values,
        command=sfx.with_sound(command, "toggle"),
        width=width,
        height=theme.control_height(),
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
    keyboard(menu, menu._open_dropdown_menu, "Drop-down list")
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
                height=theme.control_height(theme.SMALL_CONTROL_HEIGHT),
                corner_radius=theme.RADIUS_CHIP,
                font=theme.font("callout"),
                border_width=1,
                command=sfx.with_sound(
                    lambda value=option: self._toggle(value), "toggle"
                ),
            )
            keyboard(chip, chip.invoke, f"{option}, option")
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
                widget.bind("<Button-1>", lambda _e, k=key: self._click(k))
            keyboard(row, lambda k=key: self._click(k), f"{title}. {description}")
            self.rows[key] = (row, mark)
        self._restyle()

    def _click(self, key: str) -> None:
        sfx.play("toggle")
        self.choose(key)

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
        for widget, direction, name in ((minus, -1, "Less"), (plus, 1, "More")):
            widget.bind("<ButtonPress-1>", lambda _e, d=direction: self._press(d))
            widget.bind("<ButtonRelease-1>", lambda _e: self._release())
            keyboard(widget, lambda d=direction: self._nudge(d), f"{name}, button")
            for key, way in (("<Up>", 1), ("<Down>", -1)):
                widget._canvas.bind(key, lambda _e, w=way: self._nudge(w), add="+")
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

    def _nudge(self, direction: int) -> None:
        """One step from the keyboard, read aloud if that is switched on."""
        self._bump(direction)
        sfx.play("click")
        if speak_focus:
            speech.speak(self.display.cget("text"))

    def _press(self, direction: int) -> None:
        sfx.play("click")
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
                height=theme.control_height(74 if faces else 44),
                corner_radius=14,
                border_width=2,
                font=theme.font("footnote"),
                command=sfx.with_sound(lambda n=number: self.choose(n), "toggle"),
            )
            widget.grid(row=0, column=column, sticky="ew", padx=4)
            keyboard(widget, widget.invoke, f"{number}, {text}")
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
    target = min(max(value, 0.0), 1.0)
    if not page_animates(master):
        bar.set(target)
        return bar
    bar.set(0)
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
        self._redraw_job = None
        self._photos: list[ImageTk.PhotoImage] = []
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event) -> None:
        size = (event.width, event.height)
        if size == self._drawn_size or event.width < 10:
            return
        first = self._drawn_size is None
        self._drawn_size = size
        if first and self._animate_in and page_animates(self):
            anim.animate(self, theme.SLOW, self._set_progress, key=f"art-{id(self)}")
        elif first:
            self.progress = 1.0
            self.redraw()
        elif self._redraw_job is None:
            # While a page lays out, the size changes several times; draw once.
            self._redraw_job = self.after_idle(self._redraw_after_resize)

    def _redraw_after_resize(self) -> None:
        self._redraw_job = None
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

    def spoken(self) -> str:
        """Return the art in words, for reading aloud; subclasses override this."""
        return ""

    def recolour(self) -> None:
        """Follow a change of light or dark mode."""
        self.configure(bg=theme.color(self.bg_token))
        self.redraw()

    def chip(self, x: float, y: float, text: str, tags: str = "hover") -> None:
        """Show a small dark label near a point, kept inside the canvas."""
        s = self.ui_scale
        item = self.create_text(
            0,
            0,
            text=text,
            fill=theme.color("on_toast"),
            font=canvas_font(self, "footnote"),
            anchor="nw",
            tags=tags,
        )
        left, top, right, bottom = self.bbox(item)
        box_w = right - left + 18 * s
        box_h = bottom - top + 8 * s
        x0 = min(max(x - box_w / 2, 2), self.winfo_width() - box_w - 2)
        y0 = max(y - box_h - 10 * s, 2)
        self.coords(item, x0 + 9 * s, y0 + 4 * s)
        back = self.create_rectangle(
            x0,
            y0,
            x0 + box_w,
            y0 + box_h,
            fill=theme.color("toast"),
            outline="",
            tags=tags,
        )
        self.tag_raise(item, back)

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


def page_animates(widget) -> bool:
    """Return False for art on a page prepared unseen or rebuilt after a save."""
    while widget is not None:
        if hasattr(widget, "animate_art"):
            return widget.animate_art
        widget = widget.master
    return True


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

    @override
    def spoken(self) -> str:
        return f"{self.center} {self.caption}".strip()

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
        count = max(len(self.labels) - 1, 1)
        plot_w = width - pad[0] - pad[2]
        # As many labels as fit, always the first and the last, none overlapping.
        widest = max((len(text) for text in self.labels), default=1) * 7 * s + 14 * s
        step = max(1, math.ceil(widest / max(plot_w / count, 1)))
        last = len(self.labels) - 1
        for i, text in enumerate(self.labels):
            near_end = i != last and last - i < step
            if (i % step == 0 and not near_end) or i == last:
                x = pad[0] + plot_w * i / count
                anchor = "e" if i == last else "w" if i == 0 else "center"
                x = width - 2 * s if i == last else x
                self.text(x, height - 10 * s, text, "caption", anchor=anchor)

    @override
    def spoken(self) -> str:
        present = [value for value in self.values if value is not None]
        if not present:
            return ""
        fmt = self.fmt.format
        return (
            f"Line chart, {len(present)} readings. Lowest {fmt(min(present))}, "
            f"highest {fmt(max(present))}, latest {fmt(present[-1])}."
        )

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
        self.chip(x, y, f"{self.labels[best]}: {self.fmt.format(self.values[best])}")


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
        self.tops: list = []
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda _e: self.delete("hover"))

    @override
    def spoken(self) -> str:
        logged = [value for value in self.values if value]
        if not logged:
            return "Bar chart with nothing logged yet."
        average = sum(logged) / len(logged)
        return (
            f"Bar chart, {len(logged)} days logged. Average {average:.1f}, "
            f"highest {self.fmt.format(max(logged))}."
        )

    def _hover(self, event) -> None:
        self.delete("hover")
        if not self.tops:
            return
        slot = self.winfo_width() / max(len(self.tops), 1)
        index = min(int(event.x // slot), len(self.tops) - 1)
        x, y = self.tops[index]
        value = self.values[index]
        text = self.fmt.format(value) + self.unit if value else "Nothing logged"
        names = self.full_labels or self.labels
        self.chip(x, y, f"{names[index]}: {text}")

    full_labels: list[str] | None = None  # longer names for the hover label
    unit = ""  # added to the value on the hover label
    MAX_LABELLED_BARS = 8  # with more bars, only the highlighted one shows its value

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        s = self.ui_scale
        pad = (round(8 * s), round(22 * s), round(8 * s), round(24 * s))
        art, tops = graphics.bar_chart(
            width, height, self.values, self.maximum, theme.color(self.color), theme.color("surface_alt"),
            pad=pad, t=t, goal=self.goal, goal_colour=theme.color("text_muted"),
            highlight=self.highlight, highlight_colour=theme.color("primary"),
        )  # fmt: skip
        self.tops = tops
        self.image(art, 0, 0)
        for i, (x, y) in enumerate(tops):
            self.text(x, height - 10 * s, self.labels[i], "caption")
            roomy = len(tops) <= self.MAX_LABELLED_BARS or i == self.highlight
            if self.values[i] and t >= 1 and roomy:
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
    def spoken(self) -> str:
        return "Chart of a typical hormone pattern across the cycle."

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
        pad = (round(10 * s), round(24 * s), round(10 * s), round(40 * s))
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
    mark(day) returns (a letter for the day or "", whether something was logged).
    Clicking a day, or arrow keys and Enter, call on_select(day).
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
        mark=None,
        bg: str = "surface",
    ) -> None:
        super().__init__(
            master, height=self.HEADER + 6 * self.ROW, bg=bg, animate_in=False
        )
        self.mark = mark
        self.has_focus = False
        self.configure(takefocus=1)
        for key, days in (("<Left>", -1), ("<Right>", 1), ("<Up>", -7), ("<Down>", 7)):
            self.bind(key, lambda _e, d=days: self._arrow(d))
        self.bind("<FocusIn>", lambda _e: self._focus(True))
        self.bind("<FocusOut>", lambda _e: self._focus(False))
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda _e: self.delete("hover"))
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
    def spoken(self) -> str:
        return f"Calendar. Selected day {self.selected:%A, %B} {self.selected.day}."

    def _focus(self, focused: bool) -> None:
        self.has_focus = focused
        self.redraw()
        if focused:
            _ensure_visible(self)
            if speak_focus:
                speech.speak(self.spoken())

    def _arrow(self, days: int) -> str:
        self.on_select(self.selected + timedelta(days=days))
        if speak_focus:
            speech.speak(f"{self.selected:%A, %B} {self.selected.day}")
        return "break"

    def _hover(self, event) -> None:
        self.delete("hover")
        for x0, y0, x1, y1, _day in self.cells:
            if x0 <= event.x < x1 and y0 <= event.y < y1:
                self.create_rectangle(
                    x0 + 3,
                    y0 + 3,
                    x1 - 3,
                    y1 - 3,
                    outline=theme.color("border"),
                    tags="hover",
                )
                return

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
                ring = None
                if day == self.selected and self.has_focus:
                    ring = "focus"
                elif day == self.today:
                    ring = "primary"
                elif day == self.selected:
                    ring = "text_muted"
                if ring:
                    pen.ellipse(
                        box,
                        outline=graphics.rgb(theme.color(ring)),
                        width=round(2.5 * s * ss),
                    )
                bold = day in (self.today, self.selected)
                letter, logged = self.mark(day) if self.mark else ("", False)
                texts.append((cx, cy, str(day.day), text, bold, letter))
                if logged:
                    dot = 2.2 * s * ss
                    # Beside a letter there is no room below the number.
                    dx = (cx + (radius * 0.62 if letter else 0)) * ss
                    dy = (cy + radius * (0.5 if letter else 0.68)) * ss
                    pen.ellipse(
                        (dx - dot, dy - dot, dx + dot, dy + dot),
                        fill=graphics.rgb(theme.color(text)),
                    )
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
        for cx, cy, number, color, bold, letter in texts:
            lift = 5 * s if letter else 0
            self.text(cx, cy - lift, number, "headline" if bold else "body", color)
            if letter:
                self.text(cx, cy + 10 * s, letter, "caption", color)

    def _click(self, event) -> None:
        for x0, y0, x1, y1, day in self.cells:
            if x0 <= event.x < x1 and y0 <= event.y < y1:
                sfx.play("click")
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

        def step(t: float) -> None:
            self.shown = anim.lerp(start, fraction, t)
            if anim.reduce_motion:  # no wave loop is running to show the new level
                self.after_idle(self.redraw)

        anim.animate(self, theme.SLOW, step, key=f"glass-{id(self)}")

    @override
    def spoken(self) -> str:
        return f"Water glass, {min(self.fraction, 1):.0%} full."

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
        self.words = ""

    @override
    def spoken(self) -> str:
        return self.words

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


def art_for(spec: dict, size: int, default_hue: float):
    """Return the Pillow image for one object on a banner (drawn once, then cached)."""
    kind = spec["kind"]
    hue = spec.get("hue", default_hue)
    base = spec.get("base", hue_rgb(hue, 0.74, 0.96))
    glow = spec.get("glow", hue_rgb(hue, 0.24, 1.0))
    if kind == "image":
        return spec["image"]
    if kind == "sphere":
        return render3d.sphere(size, base, glow)
    if kind == "torus":
        return render3d.torus(
            size, base=hue_rgb(hue + 0.08, 0.68, 0.95), glow=render3d.PEARL
        )
    if kind == "cube":
        return render3d.cube(size, base=base, glow=glow)
    return render3d.shape(kind, size, base, glow, spec.get("accent", render3d.GOLD))


# Shades around the theme colour for banner objects: the colour itself, then two
# neighbours on the colour wheel, so a banner stays in one family of colours.
THEME_SHIFTS = (0.0, 0.07, -0.06)


def themed_specs(objects: list[dict], hue: float) -> list[dict]:
    """Return banner objects recoloured in shades of one hue (the theme colour).

    Objects with fixed colours of their own (the sun, the moon, today's flower)
    have no "hue" and stay as they are.
    """
    return [
        {**spec, "hue": hue + THEME_SHIFTS[index % len(THEME_SHIFTS)]}
        if "hue" in spec
        else spec
        for index, spec in enumerate(objects)
    ]


def prepare_art(specs_and_hues: list[tuple[dict, float]], scale: float) -> None:
    """Draw banner art ahead of time, so pages open without a pause.

    Safe on a background thread: it only makes images and touches no widget.
    """
    for spec, hue in specs_and_hues:
        art_for(spec, round(spec["size"] * scale), hue)


class Hero3D(ArtCanvas):
    """A scene of floating 3D objects, optionally on a soft gradient banner.

    objects: dicts with kind (a shape in render3d.SHAPES, "sphere", "torus", "cube",
    or "image" with a Pillow image in spec["image"]), size (px), x and y (0-1, the
    object's centre), and optional amp (px), phase (radians), hue, base, glow, accent.
    texts: (text, role, colour token, x 0-1, y 0-1, anchor) shown on top.
    hue: the banner's colour (0-1); None uses the accent theme.
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
        hue: float | None = None,
        stars: int = 16,
        themed_objects: bool = False,
    ) -> None:
        super().__init__(master, height=height, width=width, bg=bg, animate_in=False)
        self.objects = objects
        self.themed_objects = themed_objects  # objects in shades of the banner colour
        self.gradient = gradient
        self.texts = texts
        self.deep = deep
        self.radius = radius
        self.text_width = text_width  # share of the width text may use
        self.hue = hue
        self.stars = stars
        self.after_backdrop = None  # called with a colour-sampling function
        self.backdrop = None
        self.items: list[tuple[int, int, dict, float]] = []
        self.sparkles: list[tuple[int, float, float, float]] = []
        anim.loop(self, self._float, 33)

    def _banner_hue(self) -> float:
        return theme.accent_hue if self.hue is None else self.hue

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        if self.gradient:
            dark = ctk.get_appearance_mode() == "Dark"
            radius = round(self.radius * self.ui_scale)
            safe = (
                render3d.TEXT_SAFE_LUMINANCE_HIGH
                if theme.high_contrast
                else render3d.TEXT_SAFE_LUMINANCE
            )
            self.backdrop = render3d.aurora(
                width,
                height,
                self._banner_hue(),
                dark,
                radius,
                self.text_width + 0.04,
                safe,
            )
            self.image(self.backdrop, 0, 0)
            self._add_sparkles(width, height)
            if self.after_backdrop:
                self.after_backdrop(self.backdrop)
        self.items = []
        roomy = width >= 560 * self.ui_scale or not self.deep
        objects = self.objects
        if self.themed_objects:
            objects = themed_specs(objects, self._banner_hue())
        for spec in objects:
            if effects.simple_view or not roomy:
                break
            size = round(spec["size"] * self.ui_scale)
            art = art_for(spec, size, self._banner_hue())
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

    @override
    def spoken(self) -> str:
        return ". ".join(item[0] for item in self.texts)

    def _add_sparkles(self, width: int, height: int) -> None:
        """Scatter small stars on the gradient; _float makes them twinkle."""
        self.sparkles = []
        if not effects.sparkles_on or effects.simple_view:
            return
        for number in range(self.stars):  # fixed places, so a redraw doesn't jump
            x = (number * 0.381966 + 0.07) % 1 * width
            y = (number * 0.754877 + 0.11) % 1 * height
            star = self.create_oval(x, y, x, y, fill="#FFFFFF", outline="")
            self.sparkles.append((star, x, y, number * 1.7))

    def _float(self, seconds: float) -> None:
        for star, x, y, phase in self.sparkles:
            radius = max(0.0, 2.0 * math.sin(seconds * 1.4 + phase)) * self.ui_scale
            self.coords(star, x - radius, y - radius, x + radius, y + radius)
        for object_id, _shadow_id, spec, base_y in self.items:
            amp = spec.get("amp", 8) * self.ui_scale
            offset = amp * math.sin(seconds * 1.6 + spec.get("phase", 0.0))
            x, _ = self.coords(object_id) or (0, 0)
            self.coords(object_id, x, base_y + offset)


PETAL_TOKENS = ("activity", "water", "sleep", "lilac", "period", "success")


@lru_cache(maxsize=256)
def _flower_art(size: int, petals: tuple, faint: str, centre: str, t: float = 1.0):
    return graphics.flower(size, list(petals), faint, centre, t)


def flower_image(size: int, done: list[bool], t: float = 1.0):
    """Return a Pillow flower with a coloured petal for each habit that was done."""
    petals = tuple(
        theme.color(token) if earned else None
        for token, earned in zip(PETAL_TOKENS, done, strict=True)
    )
    centre = "warning" if any(done) else "border"
    return _flower_art(size, petals, theme.color("border"), theme.color(centre), t)


class FlowerView(ArtCanvas):
    """A flower that grows in, with a coloured petal for each habit done that day."""

    def __init__(
        self, master, size: int, done: list[bool], bg: str = "surface"
    ) -> None:
        super().__init__(master, height=size, width=size, bg=bg, animate_in=size > 60)
        self.done = done

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        side = min(width, height)
        if t < 1:
            art = graphics.flower(
                side,
                [
                    theme.color(token) if earned else None
                    for token, earned in zip(PETAL_TOKENS, self.done, strict=True)
                ],
                theme.color("border"),
                theme.color("warning" if any(self.done) else "border"),
                anim.ease_out_back(t),
            )
        else:
            art = flower_image(side, self.done)
        self.image(art, width / 2, height / 2, anchor="center")

    @override
    def spoken(self) -> str:
        return f"Flower with {sum(self.done)} of {len(self.done)} petals."


class CycleWheel(ArtCanvas):
    """The whole cycle as a ring of phases, with a dot on today."""

    def __init__(
        self,
        master,
        size: int,
        segments: list[tuple[float, float, str]],
        marker: float | None,
        center: str,
        caption: str,
        bg: str = "surface",
    ) -> None:
        super().__init__(master, height=size, width=size, bg=bg)
        self.segments = segments
        self.marker = marker
        self.center = center
        self.caption = caption

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        size = min(width, height)
        art = graphics.cycle_wheel(
            size,
            [(a, b, theme.color(c)) for a, b, c in self.segments],
            theme.color("surface_alt"),
            self.marker,
            theme.color("text"),
            theme.color(self.bg_token),
            round(13 * self.ui_scale),
            t,
        )
        self.image(art, width / 2, height / 2, anchor="center")
        s = self.ui_scale
        self.text(width / 2, height / 2 - 9 * s, self.center, "number_sm", "text")
        self.text(width / 2, height / 2 + 14 * s, self.caption, "caption", "text_muted")

    @override
    def spoken(self) -> str:
        return f"Cycle wheel. {self.center} {self.caption}."


class GardenScene(ArtCanvas):
    """Four weeks as a garden: a hill per week, a flower per day, this week in front.

    days: (date, list of six habits done) oldest first; the last is today.
    """

    WEEKS = 4
    WEEK_DAYS = 7
    HILLS = (0.28, 0.46, 0.64, 0.82)  # where each week's hill begins, top down
    SCALE = (0.56, 0.68, 0.82, 1.0)  # flowers further away are smaller

    def __init__(
        self, master, days: list, height: int = 300, butterflies: int = 0
    ) -> None:
        super().__init__(master, height=height, animate_in=False)
        self.days = days
        self.butterflies = butterflies
        self.heads: list[tuple[int, float, float, float]] = []
        self.flyers: list[tuple[int, float]] = []
        self.wings: list[list] = []
        self.spots: list[tuple[float, float, float, object, list[bool]]] = []
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda _e: self.delete("hover"))
        anim.loop(self, self._sway, 50)

    def _sky(self) -> tuple[str, str, list[str], bool]:
        hue = 0.41
        dark = ctk.get_appearance_mode() == "Dark"
        if theme.high_contrast:
            hill = theme.color("surface_alt")
            return theme.color("bg"), theme.color("bg"), [hill] * self.WEEKS, dark
        if dark:
            top, bottom = "#10102E", "#2F1D57"
            shades = [0.36, 0.31, 0.26, 0.21]
        else:
            top, bottom = "#BFE3FF", "#FFF0DC"
            shades = [0.86, 0.76, 0.66, 0.56]
        hills = []
        for number, value in enumerate(shades):
            r, g, b = hue_rgb(hue + number * 0.012, 0.55 if dark else 0.46, value)
            hills.append(f"#{r:02x}{g:02x}{b:02x}")
        return top, bottom, hills, dark

    @override
    def draw(self, width: int, height: int, t: float) -> None:
        top, bottom, hills, night = self._sky()
        image = graphics.garden_scene(
            width, height, top, bottom, hills, list(self.HILLS), night
        )
        pen = ImageDraw.Draw(image)
        s = self.ui_scale
        self.heads = []
        self.spots = []
        placed = []
        stem_colour = graphics.rgb(theme.color("success"))
        for index, (day, done) in enumerate(self.days[-self.WEEKS * self.WEEK_DAYS :]):
            week, column = divmod(index, self.WEEK_DAYS)
            scale = self.SCALE[week]
            gap = width / (self.WEEK_DAYS + 0.3)
            # Each row is shifted a little, so the garden doesn't look like a table.
            x = gap * (column + 0.65) + (week % 2) * gap * 0.16
            ground = height * (self.HILLS[week] + (0.14 if week < 3 else 0.13))
            count = sum(done)
            stem = (14 + count * 5.5) * scale * s
            head = round((22 + count * 4.6) * scale * s) if count else 0
            if count:
                pen.line(
                    (x, ground, x, ground - stem),
                    fill=stem_colour,
                    width=max(2, round(2.4 * scale * s)),
                )
                # A small leaf halfway up the stem.
                leaf = 5 * scale * s
                mid = ground - stem * 0.45
                pen.ellipse(
                    (x, mid - leaf / 2.4, x + leaf * 1.8, mid + leaf / 2.4),
                    fill=stem_colour,
                )
                placed.append((x, ground - stem, head, done))
            else:  # nothing that day: just a small sprout
                sprout = 7 * scale * s
                pen.line(
                    (x, ground, x, ground - sprout),
                    fill=stem_colour,
                    width=max(1, round(1.8 * s)),
                )
            self.spots.append((x, ground - stem, max(head, 16 * s), day, done))
        self.image(image, 0, 0)
        for x, y, head, done in placed:
            item = self.image(flower_image(head, done), x, y, anchor="center")
            self.heads.append((item, x, y, x * 0.02 + y * 0.03))
        today_x, today_y, today_head, _day, _done = self.spots[-1]
        self.chip(today_x, today_y - today_head / 2 + 4 * s, "Today", tags="today")
        self.flyers = []
        self.wings = []
        for number in range(self.butterflies):
            token = ("period", "warning", "water")[number % 3]
            size = round(22 * s)
            frames = [
                ImageTk.PhotoImage(graphics.butterfly(size, theme.color(token), flap))
                for flap in (1.0, 0.45)
            ]
            self.wings.append(frames)
            self.flyers.append(
                (self.create_image(-40, -40, image=frames[0]), number * 2.1)
            )

    @override
    def spoken(self) -> str:
        days = len(self.days)
        full = sum(1 for _, done in self.days if all(done))
        some = sum(1 for _, done in self.days if any(done))
        return (
            f"A garden of the last {days} days. {some} days have a flower, "
            f"{full} of them in full bloom."
        )

    def _sway(self, seconds: float) -> None:
        for item, x, y, phase in self.heads:
            self.coords(
                item, x + 1.6 * self.ui_scale * math.sin(seconds * 1.3 + phase), y
            )
        width, height = self.winfo_width(), self.winfo_height()
        for (item, phase), frames in zip(self.flyers, self.wings, strict=True):
            t = seconds * 0.22 + phase
            x = width * (0.5 + 0.44 * math.sin(t))
            y = height * (0.36 + 0.2 * math.sin(t * 2.3 + phase)) + 4 * math.sin(
                seconds * 9
            )
            self.coords(item, x, y)
            self.itemconfigure(item, image=frames[int(seconds * 7) % 2])

    def _hover(self, event) -> None:
        self.delete("hover")
        for x, y, reach, day, done in self.spots:
            if abs(event.x - x) <= reach and abs(event.y - y) <= reach + 14:
                count = sum(done)
                self.chip(
                    x,
                    y - reach / 2,
                    f"{day:%b} {day.day}: {count} of {len(done)} petals",
                )
                return


class BreathingCircle(tk.Canvas):
    """A guided 4-4-6 breath: the circle swells, holds and shrinks."""

    # (words, milliseconds, start size, end size)
    PHASES = (
        ("Breathe in", 4000, 0.45, 1.0),
        ("Hold", 4000, 1.0, 1.0),
        ("Breathe out", 6000, 1.0, 0.45),
    )

    def __init__(self, master, on_finish, size: int = 200, rounds: int = 3) -> None:
        self.size = round(size * scaling(master))
        super().__init__(
            master,
            width=self.size,
            height=self.size,
            bg=theme.color("surface"),
            highlightthickness=0,
        )
        self.on_finish = on_finish
        self.rounds = rounds
        self.running = False
        self._timer = None
        self.after(10, lambda: self._draw(0.45, "Ready"))
        self.bind("<Destroy>", self._quiet, add="+")

    def _quiet(self, _event=None) -> None:
        """Stop the spoken breaths if the exercise is closed half-way."""
        if self.running:
            self.running = False
            speech.stop()

    def _draw(self, scale: float, text: str) -> None:
        self.delete("all")
        middle = self.size / 2
        for token, share in (("primary_soft", 1.0), ("lilac", 0.82), ("primary", 0.62)):
            radius = middle * scale * share * 0.96
            self.create_oval(
                middle - radius,
                middle - radius,
                middle + radius,
                middle + radius,
                fill=theme.color(token),
                outline="",
            )
        self.create_text(
            middle,
            middle,
            text=text,
            justify="center",
            fill=theme.color("on_primary"),
            font=canvas_font(self, "caption"),
        )

    def start(self) -> None:
        """Run the breaths; pressing again does nothing until they end."""
        if not self.running:
            self.running = True
            self._phase(0, 0)

    def _phase(self, round_number: int, phase: int) -> None:
        if not self.winfo_viewable():
            # The page was left: stop, so its sounds don't follow you around.
            self.running = False
            self._draw(0.45, "Ready")
            return
        if phase == len(self.PHASES):
            round_number, phase = round_number + 1, 0
        if round_number == self.rounds:
            self.running = False
            self._draw(0.45, "Well done")
            self.on_finish()
            return
        name, duration, start, end = self.PHASES[phase]
        if phase != 1:
            sfx.play("breath")
        if speak_messages:
            speech.speak(name)
        words = f"{name}\n{round_number + 1} of {self.rounds}"
        go_on = lambda: self._phase(round_number, phase + 1)  # noqa: E731
        if anim.reduce_motion:
            # Without motion the words and the timing still guide the breath.
            self._draw(end, words)
            self._timer = self.after(duration, go_on)
            return
        anim.animate(
            self,
            duration,
            lambda t: self._draw(anim.lerp(start, end, t), words),
            ease=anim.ease_in_out_cubic,
            key=f"breath-{id(self)}",
            done=go_on,
        )


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
    sfx.play("success" if tone == "good" else "click" if tone == "info" else "warning")
    if speak_messages:
        speech.speak(text)
    old = getattr(app, "_toast", None)
    if old is not None:
        try:
            old.after_cancel(old.leave_job)
            old.destroy()
        except (tk.TclError, ValueError, AttributeError):
            pass
    pill = ctk.CTkFrame(app, fg_color=theme.pair("toast"), corner_radius=16)
    ctk.CTkLabel(
        pill, text="", image=icons.icon(TONE_ICONS[tone], 18, "on_toast")
    ).grid(row=0, column=0, padx=(16, 8), pady=10)
    # A plain CTkLabel: the pill takes its size from the text, not the other way round.
    ctk.CTkLabel(
        pill,
        text=text,
        font=theme.font("callout"),
        text_color=theme.pair("on_toast"),
        justify="left",
        wraplength=480,
    ).grid(row=0, column=1, padx=(0, 18), pady=10)
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

    pill.leave_job = pill.after(LONG_TOAST_MS if long_messages else TOAST_MS, leave)


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
        widget.bind("<Unmap>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._hide()  # never two timers at once
        self.pending = self.widget.after(450, self._show)

    def _show(self) -> None:
        self.pending = None
        if self.window is not None or not self.widget.winfo_viewable():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2 - 13
        room = self.widget.winfo_screenwidth() - 8 * len(self.text) - 24
        x = min(x, room)  # near the screen's edge, stay on screen
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
        if hasattr(app, "dress_window"):
            app.dress_window(self)
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
                icon="copy",
            ).grid(row=row + 1, column=0, sticky="w", pady=(0, 14))
            row += 2
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=row, column=0, sticky="e")
        self.cancel_button = None
        if cancel:
            self.cancel_button = button(
                actions, cancel, self.destroy, kind="plain", width=110
            )
            self.cancel_button.grid(row=0, column=0, padx=(0, 8))
        self.ok_button = button(
            actions, action, self._ok, kind="danger" if danger else "primary", width=130
        )
        self.ok_button.grid(row=0, column=1)
        self.danger = danger
        self.spoken_intro = f"{title}. {message}"
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(30, lambda: self._centre(app))

    def _centre(self, app) -> None:
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:  # not on screen yet: try again in a moment
            self.after(60, lambda: self._centre(app))
            return
        if self.field:
            self.field.focus()
        else:
            # Enter should never confirm something dangerous by accident.
            safe = self.cancel_button if self.danger else self.ok_button
            (safe or self.ok_button)._canvas.focus_set()
        if speak_messages:
            speech.speak(self.spoken_intro)

    def _copy(self, code: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(code)
        toast(self.master, "Code copied")
        self.lift()

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
hold_hidden_builds = False  # the app sets this while the user is busy


class ResponsiveGrid(ctk.CTkFrame):
    """Cards in equal columns; the column count follows the available width."""

    def __init__(
        self,
        master,
        min_column: int = 300,
        max_columns: int = 3,
        gap: int = theme.GUTTER,
        nested: bool = False,
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
        narrow = window.use_rail() if hasattr(window, "use_rail") else False
        rail = theme.RAIL_WIDTH if narrow else theme.SIDEBAR_WIDTH
        guess = window.winfo_width() / scaling(self) - rail - 2 * theme.PAGE_PAD - 16
        self.columns = self._columns_for(min(guess, theme.CONTENT_MAX_WIDTH))
        # Inside a card the window width says nothing; starting wide would force
        # the card wider than its column, so start with one column and grow.
        if nested:
            self.columns = 1
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
            if hold_hidden_builds and not _on_shown_page(self):
                # A page being prepared unseen waits while the user is busy.
                self.after(200, self._build_next)
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


def forget_styles(roots) -> None:
    """Stop CustomTkinter restyling hidden widgets that are waiting to be destroyed.

    A change of light/dark mode or text size makes CustomTkinter redraw every
    widget it knows about. Widgets that are about to go are taken off its lists,
    which saves seconds. (CustomTkinter internals: the version is pinned.)
    """
    doomed = set()
    pending = list(roots)
    while pending:
        widget = pending.pop()
        doomed.add(id(widget))
        pending.extend(widget.winfo_children())

    def keep(callback) -> bool:
        return id(getattr(callback, "__self__", None)) not in doomed

    callbacks = ctk.AppearanceModeTracker.callback_list
    callbacks[:] = [callback for callback in callbacks if keep(callback)]
    for callbacks in ctk.ScalingTracker.window_widgets_dict.values():
        callbacks[:] = [callback for callback in callbacks if keep(callback)]


def _on_shown_page(widget) -> bool:
    """Return True for a widget on the page being shown, or on no page at all."""
    page = getattr(widget.winfo_toplevel(), "page", None)
    if page is None:
        return True
    path, page_path = str(widget), str(page)
    return path == page_path or path.startswith(page_path + ".")


def still_building(widget) -> bool:
    """Return True while any of a page's cards are still to arrive."""
    pending = [widget]
    while pending:
        current = pending.pop()
        if isinstance(current, ResponsiveGrid) and current.ready < len(current.items):
            return True
        pending.extend(current.winfo_children())
    return False


class TabBar(ctk.CTkFrame):
    """Rounded tabs that wrap onto a second row when the window is narrow."""

    def __init__(self, master, tabs: list[str], current: str, command) -> None:
        super().__init__(master, fg_color="transparent")
        self.command = command
        self.buttons: dict[str, ctk.CTkButton] = {}
        self._width = 0
        for tab in tabs:
            pill = ctk.CTkButton(
                self,
                text=tab,
                width=20,
                height=theme.control_height(theme.SMALL_CONTROL_HEIGHT),
                corner_radius=theme.RADIUS_CHIP + 2,
                font=theme.font("callout"),
                command=sfx.with_sound(lambda t=tab: self.choose(t), "toggle"),
            )
            keyboard(pill, pill.invoke, f"{tab} tab")
            self.buttons[tab] = pill
        self.current = current
        self._restyle()
        self.bind("<Configure>", self._on_resize)
        self._flow(1100)

    def _restyle(self) -> None:
        for tab, pill in self.buttons.items():
            chosen = tab == self.current
            pill.configure(
                fg_color=theme.pair("primary" if chosen else "surface_alt"),
                hover_color=theme.pair("primary_hover" if chosen else "border"),
                text_color=theme.pair("on_primary" if chosen else "text"),
            )

    def choose(self, tab: str) -> None:
        """Show a tab as chosen and tell the page."""
        self.current = tab
        self._restyle()
        self.command(tab)

    def _on_resize(self, event) -> None:
        width = event.width / scaling(self)
        if abs(width - self._width) > 4:
            self._width = width
            self.after(10, lambda: self._flow(width))

    def _flow(self, width: float) -> None:
        """Lay the tabs out in as many rows as the width needs."""
        font = theme.font("callout")
        row, column, used = 0, 0, 0.0
        for tab, pill in self.buttons.items():
            need = font.measure(tab) + 44
            if column and used + need > width:
                row, column, used = row + 1, 0, 0.0
            pill.grid(row=row, column=column, padx=(0, 6), pady=(0, 6), sticky="w")
            column += 1
            used += need + 6


class DateSwitcher(ctk.CTkFrame):
    """Back and forward arrows around a date; logging past days is one click away."""

    def __init__(self, master, day: date, on_change, today: date) -> None:
        super().__init__(
            master,
            fg_color=theme.pair("surface"),
            corner_radius=12,
            border_width=theme.border_width,
            border_color=theme.pair("border"),
        )
        self.day = day
        self.today = today
        self.on_change = on_change
        self.on_glass = False
        self.back = icon_button(
            self,
            "chevron_left",
            lambda: self._move(-1),
            size=34,
            kind="ghost",
            tooltip="Previous day",
        )
        self.back.grid(row=0, column=0, padx=4, pady=4)
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

    def glass(self, backdrop: str) -> None:
        """Restyle for a banner: a dark see-through pill with white text."""
        self.on_glass = True
        pill = glass_color(backdrop)
        hover = mix(pill, "#FFFFFF", 0.12)
        self.configure(
            fg_color=pill, bg_color=backdrop, border_color=mix(pill, "#FFFFFF", 0.25)
        )
        self.text.configure(text_color="#FFFFFF", bg_color=pill, fg_color=pill)
        white = icons.icon("chevron_left", 18, "#FFFFFF")
        self.back.configure(
            fg_color=pill, bg_color=pill, hover_color=hover, image=white
        )
        self.forward.configure(fg_color=pill, bg_color=pill, hover_color=hover)
        self._show()

    def _show(self) -> None:
        if self.day == self.today:
            text = "Today"
        elif self.day == self.today - timedelta(days=1):
            text = "Yesterday"
        else:
            text = f"{self.day:%a, %b} {self.day.day}"
        self.text.configure(text=text, cursor="" if text == "Today" else "hand2")
        at_today = self.day >= self.today
        live = "#FFFFFF" if self.on_glass else "primary_text"
        faded = "#BBBBBB" if self.on_glass else "border"
        self.forward.configure(
            state="disabled" if at_today else "normal",
            # A faded arrow shows there is no "tomorrow" to log yet.
            image=icons.icon("chevron_right", 18, faded if at_today else live),
        )

    def _move(self, days: int) -> None:
        new_day = self.day + timedelta(days=days)
        if new_day > self.today or days == 0:
            return
        self.day = new_day
        self._show()
        self.on_change(new_day)
