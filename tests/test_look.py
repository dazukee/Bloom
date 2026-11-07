"""Checks that every theme stays readable: contrast is tested, not assumed."""

import pytest

from tracker.ui import render3d, theme

# (text token, background token): pairs the screens really use.
TEXT_PAIRS = [
    ("text", "surface"),
    ("text", "bg"),
    ("text", "surface_alt"),
    ("text_muted", "surface"),
    ("text_muted", "bg"),
    ("text_muted", "surface_alt"),
    ("title", "bg"),
    ("primary_text", "surface"),
    ("primary_text", "primary_soft"),
    ("on_primary", "primary"),
    ("on_primary", "danger_fill"),
    ("sidebar_text", "sidebar"),
    ("sidebar_muted", "sidebar"),
    ("sidebar_active_text", "sidebar_active"),
    ("on_toast", "toast"),
    ("success", "success_soft"),
    ("warning", "warning_soft"),
    ("danger", "danger_soft"),
]
ACCENTS = list(theme.ACCENTS)
VISIONS = list(theme.COLOR_VISION)


@pytest.fixture(autouse=True)
def restore_palette():
    yield
    theme.apply_look()


def ratio(text: str, back: str, mode: int) -> float:
    return theme.contrast(theme.PALETTE[text][mode], theme.PALETTE[back][mode])


@pytest.mark.parametrize("accent", ACCENTS)
@pytest.mark.parametrize("mode", [0, 1], ids=["light", "dark"])
@pytest.mark.parametrize(("text", "back"), TEXT_PAIRS)
def test_text_is_readable_in_every_accent(accent, mode, text, back):
    theme.apply_look(accent)
    assert ratio(text, back, mode) >= 4.5, (accent, mode, text, back)


@pytest.mark.parametrize("accent", ACCENTS)
@pytest.mark.parametrize("mode", [0, 1], ids=["light", "dark"])
@pytest.mark.parametrize(("text", "back"), TEXT_PAIRS)
def test_high_contrast_reaches_7_to_1(accent, mode, text, back):
    theme.apply_look(accent, True)
    assert ratio(text, back, mode) >= 7.0, (accent, mode, text, back)


@pytest.mark.parametrize("vision", VISIONS)
@pytest.mark.parametrize("mode", [0, 1], ids=["light", "dark"])
@pytest.mark.parametrize(
    ("text", "back"),
    [
        ("success", "success_soft"),
        ("warning", "warning_soft"),
        ("danger", "danger_soft"),
        ("success", "surface"),
        ("warning", "surface"),
        ("danger", "surface"),
    ],
)
def test_colour_vision_palettes_stay_readable(vision, mode, text, back):
    theme.apply_look("bloom", False, vision)
    assert ratio(text, back, mode) >= 4.5, (vision, mode, text, back)


def test_period_and_fertile_differ_for_red_green_vision():
    theme.apply_look("bloom", False, "red-green")
    period, fertile = theme.PALETTE["period"][0], theme.PALETTE["fertile"][0]
    r1, b1 = int(period[1:3], 16), int(period[5:7], 16)
    r2, b2 = int(fertile[1:3], 16), int(fertile[5:7], 16)
    assert r1 > b1 and b2 > r2  # one warm, one cool: safe when red and green merge


@pytest.mark.parametrize("hue", [0.722, 0.93, 0.03, 0.58, 0.5, 0.41, 0.97, 0.87, 0.05])
@pytest.mark.parametrize("dark", [False, True])
def test_banner_keeps_white_text_readable(hue, dark):
    image = render3d.aurora(300, 90, hue, dark, 0, 0.6).convert("RGB")
    brightest = 0.0
    for x in range(0, 180, 6):
        for y in range(0, 90, 6):
            r, g, b = image.getpixel((x, y))
            colour = f"#{r:02x}{g:02x}{b:02x}"
            brightest = max(brightest, theme._luminance(colour))
    assert (1.05) / (brightest + 0.05) >= 4.4


@pytest.mark.parametrize("hue", [0.722, 0.93, 0.41, 0.97])
def test_high_contrast_banner_reaches_7_to_1(hue):
    image = render3d.aurora(
        300, 90, hue, False, 0, 0.6, render3d.TEXT_SAFE_LUMINANCE_HIGH
    ).convert("RGB")
    brightest = 0.0
    for x in range(0, 180, 6):
        for y in range(0, 90, 6):
            r, g, b = image.getpixel((x, y))
            brightest = max(brightest, theme._luminance(f"#{r:02x}{g:02x}{b:02x}"))
    assert 1.05 / (brightest + 0.05) >= 6.9
