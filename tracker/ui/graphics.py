"""Anti-aliased rings, gauges and charts, drawn with Pillow.

Tkinter's canvas draws jagged curves on Windows, so smooth shapes are drawn
here at 3x size and scaled down. Labels and numbers stay as real Tk text on
top, so they remain crisp. Every function takes a `t` from 0 to 1 so screens
can animate a chart growing in.
"""

import math

from PIL import Image, ImageDraw

SS = 3  # supersampling factor


def rgb(hex_color: str, alpha: int = 255) -> tuple:
    """Turn "#rrggbb" into an (r, g, b, a) tuple."""
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5)) + (alpha,)


def _canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def _finish(image: Image.Image, width: int, height: int) -> Image.Image:
    return image.resize((width, height), Image.LANCZOS)


def _arc(draw, cx, cy, radius, start, end, colour, width) -> None:
    """Draw an arc with round ends (angles in degrees, 0 = top, clockwise)."""
    if end - start <= 0.01:
        return
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.arc(box, start - 90, end - 90, fill=colour, width=width)
    # Pillow grows the stroke inwards, so the round caps sit on its centre line.
    middle = radius - width / 2
    cap = width / 2
    for angle in (start, end):
        rad = math.radians(angle - 90)
        x = cx + middle * math.cos(rad)
        y = cy + middle * math.sin(rad)
        draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=colour)


def rings(
    size: int,
    specs: list[tuple[float, str, str]],
    thickness: int,
    gap: int = 4,
    t: float = 1.0,
) -> Image.Image:
    """Concentric progress rings, Apple Activity style.

    Args:
        size: Width and height in pixels.
        specs: (fraction 0-1+, colour hex, track colour hex), outermost first.
        thickness: Ring width in pixels.
        gap: Space between rings.
        t: Animation progress 0-1.
    """
    image, draw = _canvas(size, size)
    centre = size * SS / 2
    width = thickness * SS
    for index, (fraction, colour, track) in enumerate(specs):
        radius = centre - index * (thickness + gap) * SS
        box = (centre - radius, centre - radius, centre + radius, centre + radius)
        draw.ellipse(box, outline=rgb(track), width=width)
        sweep = min(max(fraction, 0.0), 1.0) * 360 * t
        if sweep > 0:
            _arc(draw, centre, centre, radius, 0, sweep, rgb(colour), width)
    return _finish(image, size, size)


def gauge(
    width: int,
    height: int,
    value_fraction: float,
    bands: list[tuple[float, float, str]],
    track: str,
    needle: str,
    t: float = 1.0,
) -> Image.Image:
    """A half-circle gauge with coloured bands and a needle.

    Args:
        width: Image width (the gauge fills it).
        height: Image height (about half the width).
        value_fraction: Where the needle points, 0 (left) to 1 (right).
        bands: (start 0-1, end 0-1, colour hex) segments along the arc.
        track: Colour behind the bands.
        needle: Needle colour.
        t: Animation progress 0-1 (the needle sweeps in).
    """
    image, draw = _canvas(width, height)
    cx = width * SS / 2
    cy = height * SS - 14 * SS
    radius = min(cx - 10 * SS, cy - 4 * SS)
    thick = int(radius * 0.2)
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.arc(box, 180, 360, fill=rgb(track), width=thick)
    for start, end, colour in bands:
        a0 = 180 + 180 * start + 0.8
        a1 = 180 + 180 * end - 0.8
        draw.arc(box, a0, a1, fill=rgb(colour), width=thick)
    angle = math.radians(180 + 180 * min(max(value_fraction, 0), 1) * t)
    length = radius - thick * 0.6
    tip = (cx + length * math.cos(angle), cy + length * math.sin(angle))
    draw.line((cx, cy, *tip), fill=rgb(needle), width=int(5 * SS))
    hub = 9 * SS
    draw.ellipse((cx - hub, cy - hub, cx + hub, cy + hub), fill=rgb(needle))
    return _finish(image, width, height)


def line_chart(
    width: int,
    height: int,
    values: list[float | None],
    low: float,
    high: float,
    colour: str,
    grid: str,
    pad: tuple[int, int, int, int] = (12, 12, 12, 24),
    t: float = 1.0,
    reference: float | None = None,
    reference_colour: str = "#999999",
    shade_from: int | None = None,
    shade_colour: str | None = None,
    area: bool = True,
) -> tuple[Image.Image, list[tuple[float, float] | None]]:
    """A line chart with dots; gaps (None) break the line.

    Returns the image and each value's (x, y) pixel position (None for gaps),
    so the screen can place labels and hover tooltips.
    """
    image, draw = _canvas(width, height)
    left, top, right, bottom = (p * SS for p in pad)
    plot_w = width * SS - left - right
    plot_h = height * SS - top - bottom
    span = max(high - low, 1e-9)
    count = max(len(values) - 1, 1)

    for k in range(4):
        y = top + plot_h * k / 3
        draw.line((left, y, left + plot_w, y), fill=rgb(grid), width=SS)
    if shade_from is not None and shade_colour:
        x0 = left + plot_w * shade_from / count
        draw.rectangle(
            (x0, top, left + plot_w, top + plot_h), fill=rgb(shade_colour, 70)
        )

    positions: list[tuple[float, float] | None] = []
    for index, value in enumerate(values):
        if value is None:
            positions.append(None)
            continue
        x = left + plot_w * index / count
        eased = low + (value - low) * t
        y = top + plot_h * (1 - (eased - low) / span)
        positions.append((x, y))

    if reference is not None:
        y = top + plot_h * (1 - (reference - low) / span)
        dash = 8 * SS
        x = left
        while x < left + plot_w:
            draw.line(
                (x, y, min(x + dash, left + plot_w), y),
                fill=rgb(reference_colour),
                width=2 * SS,
            )
            x += dash * 1.8

    segment: list[tuple[float, float]] = []
    segments = []
    for point in positions:
        if point is None:
            if segment:
                segments.append(segment)
            segment = []
        else:
            segment.append(point)
    if segment:
        segments.append(segment)

    for seg in segments:
        if area and len(seg) > 1:
            polygon = seg + [(seg[-1][0], top + plot_h), (seg[0][0], top + plot_h)]
            draw.polygon(polygon, fill=rgb(colour, 38))
        if len(seg) > 1:
            draw.line(seg, fill=rgb(colour), width=3 * SS, joint="curve")
    for point in positions:
        if point is not None:
            x, y = point
            r = 4.5 * SS
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(colour))
            r2 = 2 * SS
            draw.ellipse((x - r2, y - r2, x + r2, y + r2), fill=(255, 255, 255, 255))

    scaled = [None if p is None else (p[0] / SS, p[1] / SS) for p in positions]
    return _finish(image, width, height), scaled


def bar_chart(
    width: int,
    height: int,
    values: list[float],
    maximum: float,
    colour: str,
    track: str,
    pad: tuple[int, int, int, int] = (8, 10, 8, 22),
    t: float = 1.0,
    goal: float | None = None,
    goal_colour: str = "#999999",
    highlight: int | None = None,
    highlight_colour: str | None = None,
) -> tuple[Image.Image, list[tuple[float, float]]]:
    """Rounded vertical bars on faint tracks; returns bar-top centres for labels."""
    image, draw = _canvas(width, height)
    left, top, right, bottom = (p * SS for p in pad)
    plot_w = width * SS - left - right
    plot_h = height * SS - top - bottom
    count = max(len(values), 1)
    slot = plot_w / count
    bar_w = min(slot * 0.56, 26 * SS)
    tops = []
    for index, value in enumerate(values):
        cx = left + slot * (index + 0.5)
        x0, x1 = cx - bar_w / 2, cx + bar_w / 2
        draw.rounded_rectangle(
            (x0, top, x1, top + plot_h), radius=bar_w / 2, fill=rgb(track)
        )
        fraction = min(max(value / maximum, 0), 1) * t if maximum else 0
        bar_h = max(plot_h * fraction, 0)
        fill = highlight_colour if (highlight == index and highlight_colour) else colour
        if bar_h > 0:
            y0 = top + plot_h - bar_h
            draw.rounded_rectangle(
                (x0, y0, x1, top + plot_h),
                radius=min(bar_w / 2, bar_h / 2),
                fill=rgb(fill),
            )
        tops.append((cx / SS, (top + plot_h - bar_h) / SS))
    if goal is not None and maximum:
        y = top + plot_h * (1 - min(goal / maximum, 1))
        draw.line((left, y, left + plot_w, y), fill=rgb(goal_colour), width=2 * SS)
    return _finish(image, width, height), tops


def multi_line(
    width: int,
    height: int,
    series: list[tuple[list[float], str]],
    grid: str,
    pad: tuple[int, int, int, int] = (10, 10, 10, 22),
    t: float = 1.0,
    marker: float | None = None,
    marker_colour: str = "#7C3AED",
    bands: list[tuple[float, float, str]] | None = None,
) -> Image.Image:
    """Several smooth lines on a 0-1 scale (the hormone chart).

    Args:
        width: Image width.
        height: Image height.
        series: (values 0-1, colour hex) per line, evenly spaced along x.
        grid: Grid line colour.
        pad: Padding (left, top, right, bottom).
        t: Animation progress; lines draw from left to right.
        marker: Position 0-1 of a "today" line, or None.
        marker_colour: Colour of the today line.
        bands: (start 0-1, end 0-1, colour hex) background phase bands.
    """
    image, draw = _canvas(width, height)
    left, top, right, bottom = (p * SS for p in pad)
    plot_w = width * SS - left - right
    plot_h = height * SS - top - bottom
    for start, end, colour in bands or []:
        draw.rectangle(
            (
                left + plot_w * start,
                top + plot_h + 6 * SS,
                left + plot_w * end,
                top + plot_h + 12 * SS,
            ),
            fill=rgb(colour),
        )
    for k in range(3):
        y = top + plot_h * k / 2
        draw.line((left, y, left + plot_w, y), fill=rgb(grid), width=SS)
    for values, colour in series:
        count = len(values) - 1
        shown = max(2, int(len(values) * t))
        points = [
            (left + plot_w * i / count, top + plot_h * (1 - v))
            for i, v in enumerate(values[:shown])
        ]
        draw.line(points, fill=rgb(colour), width=3 * SS, joint="curve")
    if marker is not None:
        x = left + plot_w * marker
        draw.line((x, top, x, top + plot_h), fill=rgb(marker_colour), width=2 * SS)
        r = 5 * SS
        draw.ellipse(
            (x - r, top - r / 2, x + r, top + r * 1.5), fill=rgb(marker_colour)
        )
    return _finish(image, width, height)


def water_glass(
    width: int, height: int, fraction: float, water: str, glass: str, phase: float = 0.0
) -> Image.Image:
    """A glass filling with water; `phase` moves the gentle wave."""
    image, draw = _canvas(width, height)
    w, h = width * SS, height * SS
    top_l, top_r = (w * 0.16, h * 0.06), (w * 0.84, h * 0.06)
    bot_l, bot_r = (w * 0.26, h * 0.94), (w * 0.74, h * 0.94)
    level = min(max(fraction, 0.0), 1.0)
    if level > 0:
        surface_y = bot_l[1] - (bot_l[1] - top_l[1]) * level * 0.92

        def edge_x(y: float, side: int) -> float:
            share = (y - top_l[1]) / (bot_l[1] - top_l[1])
            if side < 0:
                return top_l[0] + (bot_l[0] - top_l[0]) * share
            return top_r[0] + (bot_r[0] - top_r[0]) * share

        wave = []
        x_left, x_right = edge_x(surface_y, -1), edge_x(surface_y, 1)
        for i in range(25):
            x = x_left + (x_right - x_left) * i / 24
            y = surface_y + math.sin(i / 24 * 2 * math.pi * 1.5 + phase) * 2.5 * SS
            wave.append((x, y))
        polygon = wave + [bot_r, bot_l]
        draw.polygon(polygon, fill=rgb(water, 210))
    draw.line(
        [top_l, bot_l, bot_r, top_r], fill=rgb(glass), width=4 * SS, joint="curve"
    )
    return _finish(image, width, height)
