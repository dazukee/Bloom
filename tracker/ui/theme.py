"""Design tokens: colours, type, spacing, corner radius and motion.

Owner: Lead. Every screen takes its look from here, so the app stays
consistent. Colours are (light mode, dark mode) pairs; CustomTkinter widgets
accept the pair directly, and color() returns the one for the current mode for
drawings made with Pillow.

Style: purple + white, Apple-inspired. The display and text faces fall back
from Apple's SF Pro to Windows 11's Segoe UI Variable, its closest relative.
"""

import tkinter.font as tkfont

import customtkinter as ctk

APP_NAME = "Bloom"
APP_TAGLINE = "BMI & Female Health Tracker"

# Colours ---------------------------------------------------------------------
# Body text pairs keep at least 4.5:1 contrast; white on PRIMARY is 5.7:1.
PALETTE = {
    # Neutrals are tinted lavender, so even "white" and "black" areas feel purple.
    "bg": ("#F3EEFC", "#0F0A1A"),
    "surface": ("#FFFFFF", "#1A1328"),
    "surface_alt": ("#F3EFFA", "#241C33"),
    "border": ("#E4D9F7", "#33274A"),
    "text": ("#1C1A22", "#F2F0F7"),
    "text_muted": ("#5F5B70", "#A9A0C0"),
    "title": ("#2E1065", "#F3EEFF"),  # page titles: deep purple, 14:1 on bg
    "primary": ("#7C3AED", "#7C3AED"),
    "primary_hover": ("#6D28D9", "#6D28D9"),
    "primary_soft": ("#EADDFE", "#34245A"),
    "primary_soft_hover": ("#DDCBFC", "#402D6B"),
    "primary_text": ("#5B21B6", "#C4B5FD"),
    "segment_on": ("#FFFFFF", "#4A3577"),
    "segment_on_hover": ("#FBFAFF", "#553D88"),
    # The sidebar is a deep purple panel with a white pill on the current page.
    "sidebar": ("#4C1D95", "#2A1453"),
    "sidebar_text": ("#FFFFFF", "#F3EEFF"),
    "sidebar_muted": ("#D4C2FB", "#C4B2EE"),
    "sidebar_hover": ("#5B28AE", "#3A1F6E"),
    "sidebar_active": ("#FFFFFF", "#7C3AED"),
    "sidebar_active_text": ("#4C1D95", "#FFFFFF"),
    "sidebar_marker": ("#FFFFFF", "#C4B5FD"),
    "on_primary_muted": ("#EDE4FF", "#E4D8FF"),  # second line of text on purple
    "danger_fill": ("#DC2626", "#B91C1C"),
    "danger_fill_hover": ("#B91C1C", "#991B1B"),
    "toast": ("#1C1A22", "#F2F0F7"),
    "on_toast": ("#FFFFFF", "#1C1A22"),
    "on_primary": ("#FFFFFF", "#FFFFFF"),
    "success": ("#15803D", "#4ADE80"),
    "success_soft": ("#E6F6EC", "#163222"),
    "warning": ("#B45309", "#FBBF24"),
    "warning_soft": ("#FDF1E2", "#3A2A12"),
    "danger": ("#DC2626", "#F87171"),
    "danger_soft": ("#FDE8E8", "#3B1A1D"),
    "danger_hover": ("#B91C1C", "#DC2626"),
    # Cycle colours follow Apple Health: pink period, blue fertile window.
    "period": ("#E5397A", "#F0568F"),
    "predicted": ("#F9C9DB", "#5A2A3E"),
    "fertile": ("#3B9FE6", "#4FB4F0"),
    "fertile_soft": ("#DDEFFC", "#173246"),
    "ovulation": ("#7C3AED", "#7C3AED"),
    # Extra series colours for charts and rings.
    "water": ("#3B82F6", "#60A5FA"),
    "sleep": ("#6366F1", "#818CF8"),
    "activity": ("#EC4899", "#F472B6"),
    "lilac": ("#C4B5FD", "#8B5CF6"),
}


def color(name: str) -> str:
    """Return the hex colour for `name` in the current appearance mode."""
    light, dark = PALETTE[name]
    return dark if ctk.get_appearance_mode() == "Dark" else light


def pair(name: str) -> tuple[str, str]:
    """Return the (light, dark) colour pair for CustomTkinter widgets."""
    return PALETTE[name]


# Spacing, radius and sizes ---------------------------------------------------
# One 8-point rhythm: one gutter between cards, one padding inside them.
GUTTER = 16
PAD = 20
PAGE_PAD = 28
RADIUS_CARD = 18
RADIUS_CONTROL = 12
RADIUS_CHIP = 16
CONTROL_HEIGHT = 40
BIG_CONTROL_HEIGHT = 46
SIDEBAR_WIDTH = 232
RAIL_WIDTH = 72
CONTENT_MAX_WIDTH = 1240
COMPACT_BELOW = 1020  # window width (px) where the sidebar becomes an icon rail

# Motion (milliseconds); exits run faster than entrances.
FAST = 120
BASE = 220
PAGE_IN = 320
SLOW = 600
FRAME_MS = 15  # about 60 frames per second

# Typography ------------------------------------------------------------------
DISPLAY_FACES = (
    "SF Pro Display",
    "Segoe UI Variable Display",
    "Segoe UI",
    "Helvetica Neue",
    "Helvetica",
)
TEXT_FACES = (
    "SF Pro Text",
    "Segoe UI Variable Text",
    "Segoe UI",
    "Helvetica Neue",
    "Helvetica",
)
MONO_FACES = ("SF Mono", "Cascadia Mono", "Consolas", "Menlo", "Courier New")

# role: (size, weight, face). Body text is 14 px; nothing smaller than 11 px.
TYPE_SCALE = {
    "large_title": (30, "bold", "display"),
    "title": (22, "bold", "display"),
    "title3": (18, "bold", "display"),
    "headline": (15, "bold", "text"),
    "body": (14, "normal", "text"),
    "callout": (13, "normal", "text"),
    "footnote": (12, "normal", "text"),
    "label": (12, "bold", "text"),
    "caption": (11, "normal", "text"),
    "number_xl": (40, "bold", "display"),
    "number": (28, "bold", "display"),
    "number_sm": (20, "bold", "display"),
    "mono": (22, "bold", "mono"),
}

_faces: dict[str, str] = {}
_fonts: dict[str, ctk.CTkFont] = {}


def _first_installed(candidates: tuple[str, ...]) -> str:
    """Return the first font family in `candidates` that this computer has."""
    installed = set(tkfont.families())
    for family in candidates:
        if family in installed:
            return family
    return "TkDefaultFont"


def face(kind: str) -> str:
    """Return the family name for "display", "text" or "mono" text."""
    if kind not in _faces:
        candidates = {"display": DISPLAY_FACES, "text": TEXT_FACES}.get(
            kind, MONO_FACES
        )
        _faces[kind] = _first_installed(candidates)
    return _faces[kind]


def font(role: str) -> ctk.CTkFont:
    """Return the shared font for a type role such as "title" or "body".

    Call only after the main window exists (fonts belong to a Tk instance).
    """
    if role not in _fonts:
        size, weight, kind = TYPE_SCALE[role]
        _fonts[role] = ctk.CTkFont(family=face(kind), size=size, weight=weight)
    return _fonts[role]


def reset_fonts() -> None:
    """Forget cached fonts; needed when a new main window is created."""
    _fonts.clear()
