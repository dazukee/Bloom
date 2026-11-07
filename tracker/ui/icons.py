"""A small line-icon set, drawn in code with Pillow (no emoji, no image files).

Every icon is drawn on a 24 x 24 grid with one stroke width, like SF Symbols
or Lucide, at 4x size and then scaled down so the edges are smooth.
icon("home") returns a CTkImage that switches colour with light and dark mode.
"""

import math

import customtkinter as ctk
from PIL import Image, ImageDraw

from tracker.ui import theme

GRID = 24
SUPERSAMPLE = 4
STROKE = 1.9


class _Pen:
    """Draws lines and shapes in 24-grid units onto a big Pillow image."""

    def __init__(self, draw: ImageDraw.ImageDraw, scale: float, rgb: tuple) -> None:
        self.draw = draw
        self.scale = scale
        self.rgb = rgb
        self.width = max(1, round(STROKE * scale))

    def _pt(self, x: float, y: float) -> tuple[float, float]:
        return x * self.scale, y * self.scale

    def _cap(self, x: float, y: float) -> None:
        r = self.width / 2
        cx, cy = self._pt(x, y)
        self.draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=self.rgb)

    def line(self, *points: tuple[float, float], closed: bool = False) -> None:
        """Draw a polyline with round ends and joints."""
        pts = [self._pt(x, y) for x, y in points]
        if closed:
            pts.append(pts[0])
        self.draw.line(pts, fill=self.rgb, width=self.width, joint="curve")
        for x, y in points:
            self._cap(x, y)

    def circle(self, cx: float, cy: float, r: float, fill: bool = False) -> None:
        """Draw a circle outline (or a filled dot)."""
        x0, y0 = self._pt(cx - r, cy - r)
        x1, y1 = self._pt(cx + r, cy + r)
        if fill:
            self.draw.ellipse((x0, y0, x1, y1), fill=self.rgb)
        else:
            self.draw.ellipse((x0, y0, x1, y1), outline=self.rgb, width=self.width)

    def arc(self, cx: float, cy: float, r: float, start: float, end: float) -> None:
        """Draw an arc; angles in degrees, 0 = right, clockwise."""
        points = []
        steps = max(8, int(abs(end - start) / 6))
        for i in range(steps + 1):
            angle = math.radians(start + (end - start) * i / steps)
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        self.line(*points)

    def rect(
        self, x0: float, y0: float, x1: float, y1: float, radius: float = 2
    ) -> None:
        """Draw a rounded rectangle outline."""
        box = (*self._pt(x0, y0), *self._pt(x1, y1))
        self.draw.rounded_rectangle(
            box, radius=radius * self.scale, outline=self.rgb, width=self.width
        )

    def shape(self, points: list[tuple[float, float]]) -> None:
        """Draw a closed outline through many points (for curves)."""
        self.line(*points, closed=True)


def _heart_points(cx: float, cy: float, size: float) -> list[tuple[float, float]]:
    points = []
    for i in range(60):
        t = 2 * math.pi * i / 60
        x = 16 * math.sin(t) ** 3
        y = (
            13 * math.cos(t)
            - 5 * math.cos(2 * t)
            - 2 * math.cos(3 * t)
            - math.cos(4 * t)
        )
        points.append((cx + x * size / 32, cy - y * size / 32))
    return points


def _drop_points() -> list[tuple[float, float]]:
    points = [(12, 2.8)]
    for i in range(41):
        angle = math.radians(-35 + 250 * i / 40)
        points.append((12 + 6.6 * math.cos(angle), 14.6 + 6.6 * math.sin(angle)))
    return points


def _palette_points() -> list[tuple[float, float]]:
    points = []
    for step in range(32):
        angle = math.radians(step * 360 / 32 - 40)
        radius = 8.8 if not -30 < step * 360 / 32 - 40 - 90 < 30 else 8.0
        points.append((12 + radius * math.cos(angle), 12 + radius * math.sin(angle)))
    return points


def _moon_points() -> list[tuple[float, float]]:
    outer = []
    for i in range(41):
        angle = math.radians(-60 + 300 * i / 40)
        outer.append((12 + 8.5 * math.cos(angle), 12 + 8.5 * math.sin(angle)))
    inner = []
    for i in range(41):
        angle = math.radians(240 - 300 * i / 40)
        inner.append((15.8 + 6.2 * math.cos(angle), 9 + 6.2 * math.sin(angle)))
    inner_clipped = [p for p in inner if (p[0] - 12) ** 2 + (p[1] - 12) ** 2 <= 8.6**2]
    return outer + inner_clipped


def _face(pen: _Pen, mood: int) -> None:
    pen.circle(12, 12, 9)
    pen.circle(9, 10, 0.9, fill=True)
    pen.circle(15, 10, 0.9, fill=True)
    # The mouth bends down for a smile (positive) and up for a frown (negative).
    curve = {1: -2.4, 2: -1.2, 3: 0.0, 4: 1.4, 5: 2.6}[mood]
    base = 14.6 if curve > 0 else 16.2
    points = []
    for i in range(13):
        x = 8.4 + 7.2 * i / 12
        bend = 1 - ((x - 12) / 3.6) ** 2  # 0 at the corners, 1 in the middle
        points.append((x, base + curve * bend))
    pen.line(*points)


def _draw(name: str, pen: _Pen) -> None:  # noqa: C901 (one branch per icon)
    """Draw one icon by name."""
    if name == "home":
        pen.line((3.5, 11), (12, 3.8), (20.5, 11))
        pen.line((5.5, 9.5), (5.5, 20), (18.5, 20), (18.5, 9.5))
        pen.line((10, 20), (10, 14.5), (14, 14.5), (14, 20))
    elif name == "calendar":
        pen.rect(3.5, 5, 20.5, 20.5, 2.5)
        pen.line((3.5, 10), (20.5, 10))
        pen.line((8, 3), (8, 7))
        pen.line((16, 3), (16, 7))
    elif name == "drop":
        pen.shape(_drop_points())
    elif name == "thermometer":
        pen.line((10, 14.2), (10, 5.5))
        pen.arc(12, 5.5, 2, 180, 360)
        pen.line((14, 5.5), (14, 14.2))
        pen.arc(12, 17.2, 3.6, -56, 236)
        pen.circle(12, 17.2, 1.4, fill=True)
        pen.line((12, 15.5), (12, 9))
    elif name == "journal":
        pen.rect(5, 3, 19, 21, 2.5)
        pen.line((9, 8), (15, 8))
        pen.line((9, 12), (15, 12))
        pen.line((9, 16), (12.5, 16))
    elif name == "heart":
        pen.shape(_heart_points(12, 12.6, 17))
    elif name == "moon":
        pen.shape(_moon_points())
    elif name == "activity":
        pen.line(
            (2.5, 12.5),
            (6.5, 12.5),
            (9.2, 4.5),
            (14.8, 19.5),
            (17.5, 12.5),
            (21.5, 12.5),
        )
    elif name == "leaf":
        points = []
        for i in range(21):
            t = math.pi * i / 20
            points.append(
                (
                    5 + 14 * i / 20 + 3.4 * math.sin(t),
                    19 - 14 * i / 20 + 3.4 * math.sin(t),
                )
            )
        for i in range(21):
            t = math.pi * i / 20
            points.append(
                (
                    19 - 14 * i / 20 - 3.4 * math.sin(t),
                    5 + 14 * i / 20 - 3.4 * math.sin(t),
                )
            )
        pen.shape(points)
        pen.line((4, 20), (14, 10))
    elif name == "gauge":
        pen.arc(12, 15, 9, 180, 360)
        pen.line((12, 15), (16.4, 9.2))
        pen.circle(12, 15, 1.3, fill=True)
        pen.line((3, 19.5), (21, 19.5))
    elif name == "gear":
        pen.circle(12, 12, 3.2)
        pen.circle(12, 12, 7.2)
        for k in range(8):
            angle = math.radians(k * 45 + 22.5)
            pen.line(
                (12 + 7.2 * math.cos(angle), 12 + 7.2 * math.sin(angle)),
                (12 + 9.6 * math.cos(angle), 12 + 9.6 * math.sin(angle)),
            )
    elif name == "user":
        pen.circle(12, 8, 4)
        pen.arc(12, 22, 8.5, 200, 340)
    elif name == "plus":
        pen.line((12, 5), (12, 19))
        pen.line((5, 12), (19, 12))
    elif name == "minus":
        pen.line((5, 12), (19, 12))
    elif name == "check":
        pen.line((5, 12.5), (10, 17.5), (19, 7))
    elif name == "circle":
        pen.circle(12, 12, 9)
    elif name == "check_circle":
        pen.circle(12, 12, 10, fill=True)
        pen.rgb = (*pen.rgb, 0)  # see-through ink: cuts the tick out of the dot
        pen.line((7.5, 12.5), (10.8, 15.8), (16.5, 9))
    elif name == "chevron_left":
        pen.line((15, 5), (8, 12), (15, 19))
    elif name == "chevron_right":
        pen.line((9, 5), (16, 12), (9, 19))
    elif name == "close":
        pen.line((6, 6), (18, 18))
        pen.line((18, 6), (6, 18))
    elif name == "logout":
        pen.line((10, 4), (5.5, 4), (5.5, 20), (10, 20))
        pen.line((10, 12), (20, 12))
        pen.line((16, 8), (20, 12), (16, 16))
    elif name == "sparkle":
        pen.shape(
            [
                (12, 2.5),
                (14, 10),
                (21.5, 12),
                (14, 14),
                (12, 21.5),
                (10, 14),
                (2.5, 12),
                (10, 10),
            ]
        )
    elif name == "copy":
        pen.rect(8.5, 8.5, 20.5, 20.5, 2.5)
        pen.line(
            (15.5, 8.5), (15.5, 5.5), (15.5, 3.5), (3.5, 3.5), (3.5, 15.5), (8.5, 15.5)
        )
    elif name == "search":
        pen.circle(10.5, 10.5, 6.5)
        pen.line((15.5, 15.5), (20.5, 20.5))
    elif name == "speaker":
        pen.line((4, 9.5), (8, 9.5), (13, 5), (13, 19), (8, 14.5), (4, 14.5), (4, 9.5))
        pen.arc(14, 12, 3.5, -50, 50)
        pen.arc(14, 12, 6.8, -50, 50)
    elif name == "eye_access":
        pen.circle(12, 5, 2)
        pen.line((4.5, 9), (12, 10.5), (19.5, 9))
        pen.line((12, 10.5), (12, 15), (8, 21))
        pen.line((12, 15), (16, 21))
    elif name == "palette":
        pen.shape(_palette_points())
        pen.circle(8, 9, 1.1, fill=True)
        pen.circle(12.5, 6.8, 1.1, fill=True)
        pen.circle(16.8, 9.5, 1.1, fill=True)
    elif name == "flower":
        for turn in range(6):
            angle = math.radians(turn * 60 - 90)
            pen.circle(12 + 5.2 * math.cos(angle), 12 + 5.2 * math.sin(angle), 2.9)
        pen.circle(12, 12, 2.3)
    elif name == "keyboard":
        pen.rect(2.5, 6, 21.5, 18.5, 2.5)
        for row, y in enumerate((10, 13.5)):
            for column in range(5):
                pen.circle(6.2 + column * 2.9 + (row * 0.8), y, 0.5, fill=True)
        pen.line((8.5, 16), (15.5, 16))
    elif name == "report":
        pen.rect(5, 3, 19, 21, 2.5)
        pen.line((8.5, 8), (15.5, 8))
        pen.line((8.5, 12), (15.5, 12))
        pen.line((8.5, 16), (12.5, 16))
    elif name == "fullscreen":
        pen.line((4, 9), (4, 4), (9, 4))
        pen.line((15, 4), (20, 4), (20, 9))
        pen.line((20, 15), (20, 20), (15, 20))
        pen.line((9, 20), (4, 20), (4, 15))
    elif name == "cup":
        pen.line((5.5, 4), (18.5, 4), (17, 20.5), (7, 20.5), (5.5, 4))
        pen.line((6.5, 10), (17.5, 10))
    elif name == "flame":
        points = [(12, 2.5)]
        for i in range(31):
            angle = math.radians(-20 + 220 * i / 30)
            points.append((12 + 7 * math.cos(angle), 14.5 + 7 * math.sin(angle)))
        points.append((7.2, 9.5))
        points.append((9.5, 11.5))
        pen.shape(points)
    elif name == "smile":
        _face(pen, 4)
    elif name.startswith("face"):
        _face(pen, int(name[-1]))
    elif name == "eye":
        pen.arc(12, 19, 11, 220, 320)
        pen.arc(12, 5, 11, 40, 140)
        pen.circle(12, 12, 3)
    elif name == "eye_off":
        pen.arc(12, 19, 11, 220, 320)
        pen.arc(12, 5, 11, 40, 140)
        pen.line((4, 4), (20, 20))
    elif name == "trash":
        pen.line((4, 6.5), (20, 6.5))
        pen.line((9, 6.5), (9, 4), (15, 4), (15, 6.5))
        pen.line((6, 6.5), (7, 20.5), (17, 20.5), (18, 6.5))
    elif name == "edit":
        pen.line((4, 20), (5, 15.5), (16, 4.5), (19.5, 8), (8.5, 19), (4, 20))
    elif name == "download":
        pen.line((12, 3.5), (12, 15))
        pen.line((7.5, 10.5), (12, 15), (16.5, 10.5))
        pen.line((4, 16.5), (4, 20.5), (20, 20.5), (20, 16.5))
    elif name == "lock":
        pen.rect(5, 10.5, 19, 20.5, 2.5)
        pen.arc(12, 10.5, 4.2, 180, 360)
    elif name == "key":
        pen.circle(8, 15, 4)
        pen.line((11, 12), (20, 3))
        pen.line((17, 6), (19.5, 8.5))
        pen.line((14.5, 8.5), (16.5, 10.5))
    elif name == "steps":
        pen.shape([(7, 4), (10, 5), (10.5, 11), (7.5, 12), (5, 9)])
        pen.shape([(15, 9), (18, 10), (18.5, 16), (15.5, 17), (13, 14)])
        pen.line((7.5, 14.5), (9.5, 14))
        pen.line((15.5, 19.5), (17.5, 19))
    elif name == "clock":
        pen.circle(12, 12, 9)
        pen.line((12, 7), (12, 12), (15.5, 14))
    elif name == "info":
        pen.circle(12, 12, 9)
        pen.line((12, 11), (12, 16.5))
        pen.circle(12, 7.6, 1.1, fill=True)
    elif name == "alert":
        pen.line((12, 3.5), (21.5, 20), (2.5, 20), (12, 3.5))
        pen.line((12, 9.5), (12, 14))
        pen.circle(12, 17, 1.1, fill=True)
    elif name == "sun":
        pen.circle(12, 12, 4)
        for k in range(8):
            angle = math.radians(k * 45)
            pen.line(
                (12 + 6.8 * math.cos(angle), 12 + 6.8 * math.sin(angle)),
                (12 + 9.2 * math.cos(angle), 12 + 9.2 * math.sin(angle)),
            )
    elif name == "monitor":
        pen.rect(3, 4, 21, 16, 2)
        pen.line((12, 16), (12, 20))
        pen.line((8, 20), (16, 20))
    elif name == "scale":
        pen.rect(3.5, 3.5, 20.5, 20.5, 4)
        pen.arc(12, 13, 5.5, 205, 335)
        pen.line((12, 10.5), (13.6, 8.2))
    elif name == "dumbbell":
        pen.line((7, 12), (17, 12))
        pen.rect(4, 7, 7, 17, 1.2)
        pen.rect(17, 7, 20, 17, 1.2)
        pen.line((2, 10), (2, 14))
        pen.line((22, 10), (22, 14))
    elif name == "coffee":
        pen.line((4, 9), (4, 16), (6, 20), (14, 20), (16, 16), (16, 9), (4, 9))
        pen.arc(16.5, 12.5, 2.8, -90, 90)
        pen.line((8, 3), (8, 6))
        pen.line((12, 3), (12, 6))
    else:
        raise KeyError(f"No icon named {name!r}")


def render(name: str, px: int, hex_color: str) -> Image.Image:
    """Return a Pillow image of one icon, px pixels square."""
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    big = px * SUPERSAMPLE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    _draw(name, _Pen(ImageDraw.Draw(image), big / GRID, rgb))
    return image.resize((px, px), Image.LANCZOS)


_cache: dict[tuple, ctk.CTkImage] = {}


def reset_cache() -> None:
    """Forget cached icons; needed when a new main window is created."""
    _cache.clear()


def icon(name: str, size: int = 20, color: str = "text") -> ctk.CTkImage:
    """Return a CTkImage of an icon in a theme colour (light and dark versions)."""
    key = (name, size, color)
    if key not in _cache:
        light, dark = theme.pair(color) if color in theme.PALETTE else (color, color)
        _cache[key] = ctk.CTkImage(
            light_image=render(name, size * 2, light),
            dark_image=render(name, size * 2, dark),
            size=(size, size),
        )
    return _cache[key]


ALL_ICONS = (
    "home calendar drop thermometer journal heart moon activity leaf gauge gear "
    "user plus minus check chevron_left chevron_right close logout sparkle cup "
    "flame smile face1 face2 face3 face4 face5 eye eye_off trash edit download "
    "lock key steps clock info alert sun monitor scale dumbbell coffee circle "
    "check_circle copy search speaker eye_access palette flower keyboard report "
    "fullscreen"
).split()
