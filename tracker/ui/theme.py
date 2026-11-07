"""Design tokens: colours, type, spacing, corner radius and motion.

Owner: Lead. Every screen takes its look from here, so the app stays
consistent. Colours are (light mode, dark mode) pairs; CustomTkinter widgets
accept the pair directly, and color() returns the one for the current mode for
drawings made with Pillow.

Style: purple + white by default, with accent themes, per-page colours, and
accessible palettes (high contrast and colour-blind safe). The bundled fonts live
in assets/fonts; every look setting is applied by apply_look().
"""

import colorsys
import tkinter.font as tkfont
from pathlib import Path

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
    "success": ("#166534", "#4ADE80"),
    "success_soft": ("#E6F6EC", "#163222"),
    "warning": ("#92400E", "#FBBF24"),
    "warning_soft": ("#FDF1E2", "#3A2A12"),
    "danger": ("#B91C1C", "#F87171"),
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
    # Soft tiles behind coloured icons, one per health topic.
    "period_soft": ("#FCE4EE", "#3D1A29"),
    "water_soft": ("#DFEBFE", "#16273F"),
    "sleep_soft": ("#E4E5FD", "#20213F"),
    "activity_soft": ("#FCE3F0", "#3A1A2E"),
    "focus": ("#1D4ED8", "#FDE047"),  # the keyboard focus ring: never the accent
    "luteal": ("#F2B04A", "#D99A32"),  # the last part of the cycle wheel
    "glass_text": ("#FFFFFF", "#FFFFFF"),
}

# Which colours an icon uses on a card's tile: icon name -> (strong, soft).
TOPIC_TOKENS = {
    "drop": ("period", "period_soft"),
    "calendar": ("period", "period_soft"),
    "thermometer": ("warning", "warning_soft"),
    "moon": ("sleep", "sleep_soft"),
    "cup": ("water", "water_soft"),
    "coffee": ("warning", "warning_soft"),
    "leaf": ("success", "success_soft"),
    "activity": ("activity", "activity_soft"),
    "steps": ("activity", "activity_soft"),
    "dumbbell": ("activity", "activity_soft"),
    "heart": ("danger", "danger_soft"),
    "flame": ("warning", "warning_soft"),
    "gauge": ("fertile", "fertile_soft"),
    "scale": ("fertile", "fertile_soft"),
    "trash": ("danger", "danger_soft"),
}
DEFAULT_TOPIC = ("primary_text", "primary_soft")


# Accent themes: each turns every purple-tinted token to a new hue, so one number
# recolours the whole app. Meaningful colours (period, danger...) never change.
BASE_HUE = 0.722  # the hue of the original Bloom purple
ACCENTS = {
    "bloom": ("Bloom Purple", BASE_HUE),
    "rose": ("Rose", 0.93),
    "coral": ("Coral", 0.03),
    "ocean": ("Ocean", 0.58),
    "lagoon": ("Lagoon", 0.5),
    "forest": ("Forest", 0.41),
}
FOLLOW_CYCLE = "cycle"  # the accent changes with the user's cycle phase
TINTED = (
    "bg surface surface_alt border title primary primary_hover primary_soft "
    "primary_soft_hover primary_text segment_on segment_on_hover sidebar "
    "sidebar_muted sidebar_hover sidebar_active sidebar_active_text sidebar_marker "
    "on_primary_muted ovulation lilac"
).split()
# Darkened in light mode until they keep 4.5:1 contrast against white.
KEEP_READABLE = (
    "primary primary_hover sidebar sidebar_hover primary_text "
    "sidebar_active_text ovulation"
).split()
# The same in dark mode, for fills that carry white text there too.
KEEP_READABLE_DARK = (
    "primary primary_hover sidebar sidebar_hover sidebar_active ovulation"
).split()

# Colour vision: Okabe-Ito colours stay distinct for most colour-blind people.
COLOR_VISION = {
    "none": ("Standard", {}),
    "red-green": (
        "Red-green safe",
        {
            "period": ("#B34700", "#FF9F5A"),
            "predicted": ("#F6D5BC", "#5A3A1E"),
            "period_soft": ("#FBE9DC", "#3A2412"),
            "fertile": ("#0072B2", "#56B4E9"),
            "fertile_soft": ("#CFE6F5", "#12324A"),
            "ovulation": ("#3D2C8D", "#B8A9FF"),
            "success": ("#00658F", "#56B4E9"),
            "success_soft": ("#D9EEF9", "#12324A"),
            "warning": ("#8A5A00", "#F0C24B"),
            "warning_soft": ("#FAEFD2", "#3A2E10"),
            "danger": ("#B34700", "#FF9F5A"),
            "danger_soft": ("#FBE9DC", "#3A2412"),
            "activity": ("#A8527F", "#E0A3C4"),
            "activity_soft": ("#F6E4EE", "#35202D"),
        },
    ),
    "blue-yellow": (
        "Blue-yellow safe",
        {
            "period": ("#C2185B", "#F48FB1"),
            "predicted": ("#F8D0DF", "#55283A"),
            "period_soft": ("#FBE3EC", "#3D1A29"),
            "fertile": ("#006B6B", "#4DD0C4"),
            "fertile_soft": ("#CFEFEC", "#10302E"),
            "ovulation": ("#1B1B1B", "#FFFFFF"),
            "success": ("#00695C", "#4DD0C4"),
            "success_soft": ("#D5F0EC", "#10302E"),
            "warning": ("#A63D00", "#FF9E66"),
            "warning_soft": ("#FBE6DA", "#3A2214"),
            "danger": ("#8E0038", "#FF8FB5"),
            "danger_soft": ("#F9DFE8", "#3B1A26"),
            "water": ("#00796B", "#4DD0C4"),
            "water_soft": ("#D5F0EC", "#10302E"),
            "sleep": ("#37474F", "#B0BEC5"),
            "sleep_soft": ("#E3E7E9", "#242C30"),
        },
    ),
}

# High contrast: pure black and white, 7:1 or more for every text colour (WCAG AAA).
HIGH_CONTRAST = {
    "bg": ("#FFFFFF", "#000000"),
    "surface": ("#FFFFFF", "#000000"),
    "surface_alt": ("#EFEFEF", "#1C1C1C"),
    "border": ("#000000", "#FFFFFF"),
    "text": ("#000000", "#FFFFFF"),
    "text_muted": ("#222222", "#E4E4E4"),
    "title": ("#000000", "#FFFFFF"),
    "primary_soft": ("#E2E2E2", "#303030"),
    "primary_soft_hover": ("#CFCFCF", "#444444"),
    "segment_on": ("#FFFFFF", "#000000"),
    "segment_on_hover": ("#F2F2F2", "#111111"),
    "sidebar": ("#000000", "#000000"),
    "sidebar_text": ("#FFFFFF", "#FFFFFF"),
    "sidebar_muted": ("#EAEAEA", "#EAEAEA"),
    "sidebar_hover": ("#333333", "#333333"),
    "sidebar_active": ("#FFFFFF", "#FFFFFF"),
    "sidebar_active_text": ("#000000", "#000000"),
    "sidebar_marker": ("#FFFFFF", "#FFFFFF"),
    "on_primary_muted": ("#FFFFFF", "#FFFFFF"),
    "toast": ("#000000", "#FFFFFF"),
    "on_toast": ("#FFFFFF", "#000000"),
    "danger_fill": ("#A80000", "#A80000"),
    "danger_fill_hover": ("#800000", "#800000"),
    "success": ("#005214", "#7CFFA0"),
    "success_soft": ("#FFFFFF", "#000000"),
    "warning": ("#663800", "#FFD166"),
    "warning_soft": ("#FFFFFF", "#000000"),
    "danger": ("#A80000", "#FFA3A3"),
    "danger_soft": ("#FFFFFF", "#000000"),
    "period": ("#A3003F", "#FF8DB8"),
    "period_soft": ("#FFFFFF", "#000000"),
    "predicted": ("#F4C2D5", "#6B2A44"),
    "fertile": ("#00507A", "#7FD4FF"),
    "fertile_soft": ("#BFE3F7", "#0F4560"),
    "water": ("#003F99", "#8FC1FF"),
    "water_soft": ("#FFFFFF", "#000000"),
    "sleep": ("#28268A", "#B5B7FF"),
    "sleep_soft": ("#FFFFFF", "#000000"),
    "activity": ("#8F0F58", "#FF9BD2"),
    "activity_soft": ("#FFFFFF", "#000000"),
    "focus": ("#0000FF", "#FFFF00"),
}
HIGH_CONTRAST_RATIO = 7.0
READABLE_RATIO = 4.5
# Tokens with text on something other than pure white need a margin to stay at 4.5.
LIGHT_MODE_RATIOS = {"primary_text": 6.5, "sidebar": 6.5}

_original = dict(PALETTE)
accent_hue = BASE_HUE
high_contrast = False
border_width = 1  # cards and fields: 2 in high contrast


def _luminance(hex_color: str) -> float:
    """Return a colour's relative luminance (the WCAG contrast formula)."""
    total = 0.0
    weights = (0.2126, 0.7152, 0.0722)
    for start, weight in zip((1, 3, 5), weights, strict=True):
        part = int(hex_color[start : start + 2], 16) / 255
        part = part / 12.92 if part <= 0.03928 else ((part + 0.055) / 1.055) ** 2.4
        total += weight * part
    return total


def contrast(first: str, second: str) -> float:
    """Return the WCAG contrast ratio between two "#rrggbb" colours."""
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _with_hue(hex_color: str, hue: float, lightness: float = 1.0) -> str:
    """Return the colour with a new hue; lightness below 1 darkens it."""
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    _, light, saturation = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(hue, light * lightness, saturation)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def _readable(
    base: str, hue: float | None = None, ratio: float = READABLE_RATIO
) -> str:
    """Return `base` in a hue, darkened until white text on it reaches `ratio`."""
    hue = accent_hue if hue is None else hue
    factor = 1.0
    shade = _with_hue(base, hue)
    while contrast(shade, "#FFFFFF") < ratio and factor > 0.05:
        factor -= 0.04
        shade = _with_hue(base, hue, factor)
    return shade


def swatch_color(key: str) -> str:
    """Return the colour that shows an accent in the Settings picker."""
    return _readable("#7C3AED", ACCENTS[key][1])


def _lightened(hex_color: str, hue: float, ratio: float) -> str:
    """Return a light tint of a hue that reaches `ratio` on black."""
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    _, light, saturation = colorsys.rgb_to_hls(r, g, b)
    shade = hex_color
    while contrast(shade, "#000000") < ratio and light < 0.97:
        light += 0.02
        r, g, b = colorsys.hls_to_rgb(hue, light, saturation)
        shade = f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"
    return shade


def apply_look(
    accent: str = "bloom", contrast_mode: bool = False, color_vision: str = "none"
) -> None:
    """Rebuild the palette: the accent, then colour vision, then high contrast."""
    global accent_hue, high_contrast, border_width
    accent_hue = ACCENTS.get(accent, ACCENTS["bloom"])[1]
    high_contrast = contrast_mode
    border_width = 2 if contrast_mode else 1
    PALETTE.clear()
    PALETTE.update(_original)
    if accent_hue != BASE_HUE:
        for token in TINTED:
            light, dark = _original[token]
            PALETTE[token] = (_with_hue(light, accent_hue), _with_hue(dark, accent_hue))
        for token in KEEP_READABLE:
            ratio = LIGHT_MODE_RATIOS.get(token, READABLE_RATIO)
            light = _readable(_original[token][0], ratio=ratio)
            PALETTE[token] = (light, PALETTE[token][1])
        for token in KEEP_READABLE_DARK:
            PALETTE[token] = (PALETTE[token][0], _readable(_original[token][1]))
    PALETTE.update(COLOR_VISION.get(color_vision, COLOR_VISION["none"])[1])
    if contrast_mode:
        PALETTE.update(HIGH_CONTRAST)
        solid = _readable("#7C3AED", ratio=HIGH_CONTRAST_RATIO)
        for token in ("primary", "primary_hover", "ovulation"):
            PALETTE[token] = (solid, solid)
        deep = _readable("#7C3AED", ratio=10.0)  # 7:1 even on the grey soft fill
        PALETTE["primary_text"] = (deep, _lightened("#A78BFA", accent_hue, 12.0))
        PALETTE["lilac"] = (solid, _lightened("#A78BFA", accent_hue, 9.0))


def set_accent(key: str) -> None:
    """Recolour the palette for a key in ACCENTS (unknown keys use Bloom Purple)."""
    apply_look(key)


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
SMALL_CONTROL_HEIGHT = 36
TARGET_GROWTH = 8  # extra pixels on every control with "Larger click targets"
big_targets = False


def control_height(size: int = CONTROL_HEIGHT) -> int:
    """Return a control's height, taller with "Larger click targets" on."""
    return size + TARGET_GROWTH if big_targets else size


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

# key: (name, display family, text family, one line about it). All but the Windows
# system choice are in assets/fonts (open licences, see the README there).
FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
FONT_CHOICES = {
    "poppins": ("Poppins", "Poppins", "Poppins", "Geometric and confident"),
    "nunito": ("Nunito", "Nunito ExtraLight", "Nunito ExtraLight", "Round and friendly"),
    "quicksand": ("Quicksand", "Quicksand Light", "Quicksand Light", "Soft and playful"),
    "outfit": ("Outfit", "Outfit Thin", "Outfit Thin", "Clean and stylish"),
    "figtree": ("Figtree", "Figtree Light", "Figtree Light", "Light and friendly"),
    "editorial": ("Editorial", "Fraunces", "DM Sans 9pt", "Elegant serif headings"),
    "atkinson": ("Atkinson Hyperlegible", "Atkinson Hyperlegible", "Atkinson Hyperlegible", "Made for low vision"),
    "lexend": ("Lexend", "Lexend", "Lexend", "Eases reading effort"),
    "opendyslexic": ("OpenDyslexic", "OpenDyslexic", "OpenDyslexic", "Designed for dyslexia"),
    "system": ("Segoe UI", "Segoe UI Variable Display", "Segoe UI Variable Text", "The original look"),
}  # fmt: skip
DEFAULT_FONT = "poppins"
# OpenDyslexic's letters are much wider and taller than most fonts at the same size.
FONT_SIZE_FACTOR = {"opendyslexic": 0.8}
_font_choice = DEFAULT_FONT
_bundled_ok = False  # True once this program has loaded assets/fonts
bold_text = False  # the "Bold text" accessibility setting
_faces: dict[str, str] = {}
_fonts: dict[str, ctk.CTkFont] = {}


def load_font_files() -> None:
    """Make the bundled fonts available to this program (no install needed)."""
    global _bundled_ok
    results = [ctk.FontManager.load_font(str(p)) for p in FONT_DIR.glob("*.ttf")]
    _bundled_ok = bool(results) and all(results)


def set_font_choice(key: str, bold: bool = False) -> None:
    """Switch every type role to a key in FONT_CHOICES, optionally all bold."""
    global _font_choice, bold_text
    _font_choice = key if key in FONT_CHOICES else DEFAULT_FONT
    bold_text = bold
    _faces.clear()
    _fonts.clear()


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
        _, display, text, _ = FONT_CHOICES[_font_choice]
        chosen = {"display": display, "text": text}.get(kind)
        candidates = {"display": DISPLAY_FACES, "text": TEXT_FACES}.get(
            kind, MONO_FACES
        )
        # Fonts loaded for this program alone are not in Tk's list of installed ones.
        if chosen and _font_choice != "system" and _bundled_ok:
            _faces[kind] = chosen
        else:
            _faces[kind] = _first_installed(
                (chosen, *candidates) if chosen else candidates
            )
    return _faces[kind]


def sized(size: int) -> int:
    """Return a font size adjusted for the chosen font."""
    return round(size * FONT_SIZE_FACTOR.get(_font_choice, 1.0))


def font(role: str) -> ctk.CTkFont:
    """Return the shared font for a type role such as "title" or "body".

    Call only after the main window exists (fonts belong to a Tk instance).
    """
    if role not in _fonts:
        size, weight, kind = TYPE_SCALE[role]
        weight = "bold" if bold_text else weight
        _fonts[role] = ctk.CTkFont(family=face(kind), size=sized(size), weight=weight)
    return _fonts[role]


def reset_fonts() -> None:
    """Forget cached fonts; needed when a new main window is created."""
    _fonts.clear()
