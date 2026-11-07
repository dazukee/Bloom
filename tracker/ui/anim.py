"""Smooth motion for Tkinter: easing curves and an interruptible animator.

Tkinter has no animation system, so animate() calls a step function about
60 times a second with progress from 0 to 1. Starting a new animation with the
same key cancels the old one, so animations never fight. When the user turns
on "Reduce motion" in Settings, every animation jumps to its end state.
"""

import math
import time
import tkinter as tk

from tracker.ui import theme

reduce_motion = False  # set from the user's settings
_running: dict[str, tuple[tk.Misc, str]] = {}


def ease_out_cubic(t: float) -> float:
    """Fast start, gentle stop: for things arriving."""
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Gentle start and stop: for things moving across the screen."""
    return 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t: float) -> float:
    """Overshoots slightly, then settles: a playful pop."""
    c1 = 1.4
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def spring(t: float) -> float:
    """A damped spring that settles on 1, like iOS motion."""
    if t >= 1:
        return 1.0
    return 1 - math.exp(-6.5 * t) * math.cos(9 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Return the value t of the way from a to b."""
    return a + (b - a) * t


def lerp_color(start: str, end: str, t: float) -> str:
    """Blend two "#rrggbb" colours."""
    a = [int(start[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(end[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(lerp(x, y, t)) for x, y in zip(a, b, strict=True)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def busy() -> bool:
    """Return True while an animation is playing (floating loops don't count)."""
    for key, (widget, _job) in list(_running.items()):
        try:
            alive = widget.winfo_exists()
        except tk.TclError:
            alive = False
        if not alive:
            # Its widget was closed mid-animation, so its next frame never runs.
            _running.pop(key, None)
    return bool(_running)


def cancel(key: str) -> None:
    """Stop the animation running under `key`, if any."""
    entry = _running.pop(key, None)
    if entry is not None:
        widget, after_id = entry
        try:
            widget.after_cancel(after_id)
        except tk.TclError:
            pass


def animate(
    widget: tk.Misc,
    duration_ms: int,
    step,
    ease=ease_out_cubic,
    key: str | None = None,
    done=None,
) -> None:
    """Call step(progress) each frame for duration_ms, ending with step(1.0).

    Args:
        widget: Any widget; the animation stops if it is destroyed.
        duration_ms: Length of the animation.
        step: Called with the eased progress, 0.0 to 1.0.
        ease: The easing curve.
        key: Animations sharing a key replace each other (interruptible).
        done: Called once at the end.
    """
    key = key or f"anim-{id(step)}"
    cancel(key)
    if reduce_motion or duration_ms <= 0:
        _safe(step, 1.0)
        if done:
            done()
        return
    started = time.perf_counter()

    def tick() -> None:
        _running.pop(key, None)
        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        progress = min((time.perf_counter() - started) * 1000 / duration_ms, 1.0)
        if not _safe(step, ease(progress) if progress < 1 else 1.0):
            return
        if progress < 1:
            _running[key] = (widget, widget.after(theme.FRAME_MS, tick))
        elif done:
            done()

    tick()


def _safe(step, value: float) -> bool:
    """Run one frame; return False if its widget has gone (TclError)."""
    try:
        step(value)
    except tk.TclError:
        return False
    return True


def loop(widget: tk.Misc, step, interval_ms: int = 33) -> None:
    """Call step(seconds_since_start) forever, until the widget is destroyed.

    Used for gentle floating motion. With reduce motion on, it draws one frame.
    """
    started = time.perf_counter()
    if reduce_motion:
        _safe(step, 0.0)
        return

    def tick() -> None:
        try:
            if not widget.winfo_exists():
                return
            if not widget.winfo_viewable():  # on a hidden (cached) page: just wait
                widget.after(interval_ms * 4, tick)
                return
        except tk.TclError:
            return
        if _safe(step, time.perf_counter() - started):
            widget.after(interval_ms, tick)

    tick()


def count_up(
    label, target: float, fmt: str = "{:.0f}", duration_ms: int = theme.SLOW
) -> None:
    """Animate a label's number from 0 up to target."""
    animate(
        label,
        duration_ms,
        lambda t: label.configure(text=fmt.format(target * t)),
        key=f"count-{id(label)}",
    )
