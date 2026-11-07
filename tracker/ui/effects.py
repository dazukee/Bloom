"""Special effects: confetti, card glow, window fade and page transitions.

All of them respect "Reduce motion" and have their own switches in Settings.
"""

import math
import random
import tkinter as tk

from tracker.ui import anim, sfx, theme

sparkles_on = True  # read by widgets.Hero3D
simple_view = False  # "Hide decorative art": read by widgets and pages
page_colors = False  # True: each page's banner in its own colour, not the theme's
_glow_on = True
_confetti_on = True
_transition = "rise"
_falling: list = []  # the confetti on screen now
GLOW_CHECK_MS = 150
CONFETTI_COLORS = ("primary", "lilac", "period", "fertile", "warning", "activity")


def configure(settings: dict) -> None:
    """Copy the effect settings from the user's preferences."""
    global sparkles_on, simple_view, page_colors, _glow_on, _confetti_on, _transition
    sparkles_on = settings["sparkles"]
    simple_view = settings["simple_view"]
    page_colors = settings["page_colors"]
    _glow_on = settings["card_glow"]
    _confetti_on = settings["confetti"]
    _transition = settings["transition"]


def add_glow(card) -> None:
    """Make a card's border light up in the accent while the mouse is over it."""
    rest, lit = theme.pair("border"), theme.pair("primary")
    state = {"inside": False, "job": None}

    def pointer_inside() -> bool:
        x = card.winfo_pointerx() - card.winfo_rootx()
        y = card.winfo_pointery() - card.winfo_rooty()
        return 0 <= x < card.winfo_width() and 0 <= y < card.winfo_height()

    def check() -> None:
        # Tk does not tell a card when the mouse leaves quickly from a child
        # widget, so while lit it checks where the mouse is.
        state["job"] = None
        try:
            if not card.winfo_exists():
                return
            if pointer_inside() and card.winfo_viewable():
                state["job"] = card.after(GLOW_CHECK_MS, check)
            else:
                state["inside"] = False
                card.configure(border_color=rest)
        except tk.TclError:
            pass

    def enter(_event) -> None:
        if _glow_on and not state["inside"]:
            state["inside"] = True
            card.configure(border_color=lit)
            state["job"] = card.after(GLOW_CHECK_MS, check)

    def destroyed(_event) -> None:
        if state["job"]:
            card.after_cancel(state["job"])

    card.bind("<Enter>", enter, add="+")
    card.bind("<Destroy>", destroyed, add="+")


def fade_in(app) -> None:
    """Fade the whole window in when the program opens."""
    try:
        if not anim.reduce_motion:
            app.attributes("-alpha", 0.0)
        anim.animate(app, 450, lambda t: app.attributes("-alpha", t), key="window-fade")
    except tk.TclError:
        pass  # a system without window transparency simply skips the fade


def page_in(app, page) -> None:
    """Bring a page in with the user's chosen transition."""
    if _transition == "slide":
        anim.animate(
            page,
            theme.PAGE_IN,
            lambda t: page.place_configure(x=60 * (1 - t)),
            ease=anim.spring,
            key="page",
        )
    elif _transition == "fade":
        anim.animate(
            app,
            theme.PAGE_IN,
            lambda t: app.attributes("-alpha", 0.72 + 0.28 * t),
            key="page-fade",
        )
    elif _transition == "rise":
        anim.animate(
            page,
            theme.PAGE_IN,
            lambda t: page.place_configure(y=26 * (1 - t)),
            key="page",
        )


def clear_confetti() -> None:
    """Remove any confetti still on screen."""
    anim.cancel("confetti")
    while _falling:
        try:
            _falling.pop()[0].destroy()
        except tk.TclError:
            pass


def confetti(app, pieces: int = 70) -> None:
    """Rain small coloured pieces over the window, then clean them up."""
    if anim.reduce_motion or not _confetti_on or simple_view:
        return
    clear_confetti()
    width, height = app.winfo_width(), app.winfo_height()
    for _ in range(pieces):
        size = random.randint(5, 11)
        piece = tk.Frame(
            app,
            width=size,
            height=random.randint(size, 16),
            bg=theme.color(random.choice(CONFETTI_COLORS)),
        )
        start_x = random.uniform(0, width)
        delay = random.uniform(-0.35, 0)
        speed = random.uniform(0.9, 1.5)
        phase = random.uniform(0, 6.3)
        _falling.append((piece, start_x, delay, speed, phase))

    def step(t: float) -> None:
        for piece, x, delay, speed, phase in _falling:
            drop = (delay + t * speed * 1.35) * height
            piece.place(x=x + 26 * math.sin(t * 9 + phase), y=drop)
            piece.lift()

    anim.animate(app, 2100, step, ease=lambda t: t, key="confetti", done=clear_confetti)


def celebrate(app) -> None:
    """Sound and confetti for a real achievement."""
    sfx.play("celebrate")
    confetti(app)
