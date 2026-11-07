"""Real-time 3D objects drawn with numpy: spheres, a torus, a flower, a heart and more.

Tkinter cannot show 3D models, so each object is ray-marched: for every pixel
a ray travels into the scene until it meets the shape's surface, described by
a signed distance function (SDF). The surface normal then gives Lambert
diffuse light, a Phong highlight and a soft rim, in the app's purples.
Edges are anti-aliased from how closely each ray missed the shape.

Images are cached, so each object is drawn once per size and colour.
"""

import colorsys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LIGHT = np.array([-0.55, -0.65, 0.55])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
VIEW = np.array([0.0, 0.0, 1.0])
HALF = (LIGHT + VIEW) / np.linalg.norm(LIGHT + VIEW)

PURPLE = (124, 58, 237)
LILAC = (196, 181, 253)
ORCHID = (217, 70, 239)
PEARL = (245, 240, 255)
GOLD = (251, 191, 36)
LEAF = (34, 197, 94)
SUN = (255, 183, 77)
MOON = (226, 232, 255)
FACE = (46, 16, 101)
TEXT_SAFE_LUMINANCE = 0.17  # white text keeps at least 4.5:1 on anything darker
TEXT_SAFE_LUMINANCE_HIGH = 0.09  # and at least 7:1 on anything darker than this


def _rotation(ax: float, ay: float, az: float = 0.0) -> np.ndarray:
    """Return a 3x3 rotation matrix (radians around x, then y, then z)."""
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz @ ry @ rx


def _sdf_torus(p: np.ndarray, major: float, minor: float) -> np.ndarray:
    """Distance from points p (N x 3) to a torus lying in the xz plane."""
    ring = np.sqrt(p[:, 0] ** 2 + p[:, 2] ** 2) - major
    return np.sqrt(ring**2 + p[:, 1] ** 2) - minor


def _sdf_round_box(p: np.ndarray, half: float, radius: float) -> np.ndarray:
    """Distance from points p (N x 3) to a cube with rounded edges."""
    q = np.abs(p) - (half - radius)
    outside = np.linalg.norm(np.maximum(q, 0.0), axis=1)
    inside = np.minimum(np.max(q, axis=1), 0.0)
    return outside + inside - radius


def _shade(
    normals: np.ndarray, base: tuple, glow: tuple, y: np.ndarray, gloss: float
) -> np.ndarray:
    """Return RGB colours (N x 3, 0-255) for surface normals."""
    base_rgb = np.array(base, dtype=float)
    glow_rgb = np.array(glow, dtype=float)
    diffuse = np.clip(normals @ LIGHT, 0, 1)
    specular = np.clip(normals @ HALF, 0, 1) ** 48
    facing = np.clip(normals[:, 2], 0, 1)
    rim = (1 - facing) ** 2.5
    # A vertical blend from the glow colour (top) to the base colour (bottom).
    blend = np.clip((y + 1) / 2, 0, 1)[:, None]
    tint = glow_rgb * (1 - blend) * 0.55 + base_rgb * (0.45 + blend * 0.55)
    colour = tint * (0.38 + 0.72 * diffuse[:, None])
    colour += rim[:, None] * glow_rgb * 0.45
    colour += specular[:, None] * 255 * gloss
    return np.clip(colour, 0, 255)


def _march(size: int, sdf, rotation: np.ndarray, extent: float) -> tuple:
    """Ray-march an orthographic view; return (hit mask, points, alpha, coords)."""
    axis = np.linspace(-extent, extent, size)
    xs, ys = np.meshgrid(axis, axis)
    count = size * size
    # The camera sits at +z looking down -z, the side the light comes from.
    origins = np.stack([xs.ravel(), ys.ravel(), np.full(count, 2.5)], axis=1)
    direction = np.array([0.0, 0.0, -1.0])
    inverse = rotation.T
    travelled = np.zeros(count)
    closest = np.full(count, np.inf)
    closest_at = np.zeros(count)  # how far each ray had gone at its closest pass
    alive = np.ones(count, dtype=bool)
    for _ in range(64):
        idx = np.nonzero(alive)[0]
        if idx.size == 0:
            break
        points = (origins[idx] + travelled[idx, None] * direction) @ inverse.T
        distance = sdf(points)
        nearer = distance < closest[idx]
        closest[idx[nearer]] = distance[nearer]
        closest_at[idx[nearer]] = travelled[idx[nearer]]
        travelled[idx] += distance
        done = (distance < 1e-3) | (travelled[idx] > 5.0)
        alive[idx[done]] = False
    pixel = 2 * extent / size
    hit = closest < 1e-3
    alpha = np.clip(1.0 - closest / (1.2 * pixel), 0, 1)
    alpha[hit] = 1.0
    # Edge pixels that just missed are shaded where the ray passed closest.
    surface_points = origins + closest_at[:, None] * direction
    return hit | (alpha > 0), surface_points, alpha, ys.ravel()


def _normals(points: np.ndarray, sdf, rotation: np.ndarray) -> np.ndarray:
    """Estimate surface normals (in view space) by central differences."""
    inverse = rotation.T
    local = points @ inverse.T
    eps = 1e-3
    gradient = np.zeros_like(local)
    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = eps
        gradient[:, axis] = sdf(local + offset) - sdf(local - offset)
    gradient = gradient @ rotation.T  # back into view space
    length = np.linalg.norm(gradient, axis=1, keepdims=True)
    return gradient / np.maximum(length, 1e-9)


def _image(
    size: int, mask: np.ndarray, colours: np.ndarray, alpha: np.ndarray
) -> Image.Image:
    """Pack colours and alpha into an RGBA Pillow image."""
    rgba = np.zeros((size * size, 4), dtype=np.uint8)
    rgba[mask, :3] = colours.astype(np.uint8)
    rgba[:, 3] = (alpha * 255).astype(np.uint8)
    return Image.fromarray(rgba.reshape(size, size, 4), "RGBA")


@lru_cache(maxsize=64)
def sphere(
    size: int, base: tuple = PURPLE, glow: tuple = LILAC, gloss: float = 0.75
) -> Image.Image:
    """Return a glossy sphere. A sphere's surface is solved exactly, no marching."""
    axis = np.linspace(-1.02, 1.02, size)
    xs, ys = np.meshgrid(axis, axis)
    radius = np.sqrt(xs**2 + ys**2)
    pixel = 2.04 / size
    alpha = np.clip((1.0 - radius) / pixel + 0.5, 0, 1).ravel()
    inside = radius.ravel() < 1.0 + pixel
    x = xs.ravel()[inside]
    y = ys.ravel()[inside]
    z = np.sqrt(np.clip(1 - x**2 - y**2, 0, 1))
    normals = np.stack([x, y, z], axis=1)
    colours = _shade(normals, base, glow, y, gloss)
    return _image(size, inside, colours, alpha)


@lru_cache(maxsize=32)
def torus(
    size: int,
    tilt: float = 1.05,
    turn: float = 0.35,
    base: tuple = ORCHID,
    glow: tuple = PEARL,
) -> Image.Image:
    """Return a glossy ring (torus), tilted towards the viewer."""
    rotation = _rotation(tilt, turn, 0.25)

    def sdf(p: np.ndarray) -> np.ndarray:
        return _sdf_torus(p, 0.66, 0.27)

    mask, points, alpha, ys = _march(size, sdf, rotation, 1.0)
    normals = _normals(points[mask], sdf, rotation)
    colours = _shade(normals, base, glow, ys[mask], 0.6)
    return _image(size, mask, colours, alpha)


@lru_cache(maxsize=32)
def cube(
    size: int,
    ax: float = 0.62,
    ay: float = 0.78,
    base: tuple = PURPLE,
    glow: tuple = LILAC,
) -> Image.Image:
    """Return a cube with softly rounded edges, turned to show three faces."""
    rotation = _rotation(ax, ay, 0.0)

    def sdf(p: np.ndarray) -> np.ndarray:
        return _sdf_round_box(p, 0.56, 0.1)

    mask, points, alpha, ys = _march(size, sdf, rotation, 1.0)
    normals = _normals(points[mask], sdf, rotation)
    colours = _shade(normals, base, glow, ys[mask], 0.35)
    return _image(size, mask, colours, alpha)


@lru_cache(maxsize=32)
def shadow(width: int, height: int, strength: int = 70) -> Image.Image:
    """Return a soft elliptical shadow to place under a floating object."""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad_x, pad_y = width * 0.18, height * 0.25
    draw.ellipse(
        (pad_x, pad_y, width - pad_x, height - pad_y), fill=(40, 10, 80, strength)
    )
    return image.filter(ImageFilter.GaussianBlur(radius=max(2, height / 5)))


@lru_cache(maxsize=16)
def gradient(
    width: int, height: int, dark: bool, deep: bool = False, radius: int = 0
) -> Image.Image:
    """Return a soft purple backdrop with light glows, like the hero art.

    deep=True is darker on the left so white text stays readable (4.5:1 or
    more); radius > 0 rounds the corners (they become see-through).
    """
    xs = np.linspace(0, 1, width)[None, :]
    ys = np.linspace(0, 1, height)[:, None]
    if dark and deep:
        top, bottom = np.array([88, 28, 180]), np.array([42, 16, 92])
    elif dark:
        top, bottom = np.array([72, 32, 150]), np.array([30, 12, 64])
    elif deep:
        top, bottom = np.array([109, 40, 217]), np.array([76, 29, 149])
    else:
        top, bottom = np.array([167, 120, 250]), np.array([109, 40, 217])
    mix = np.clip(0.65 * ys + 0.35 * xs, 0, 1)[..., None]
    rgb = top * (1 - mix) + bottom * mix
    glows = ((0.85, 0.8, 0.5, 0.22),)
    if not deep:
        glows = ((0.2, 0.15, 0.55, 0.35), *glows)
    for cx, cy, size, strength in glows:
        glow = np.exp(-(((xs - cx) ** 2 + (ys - cy) ** 2) / (size**2)))[..., None]
        rgb = rgb + glow * strength * (np.array([255, 235, 255]) - rgb)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    if radius:
        # Draw the rounded mask 3x larger and shrink it, for smooth corners.
        mask = Image.new("L", (width * 3, height * 3), 0)
        box = (0, 0, width * 3 - 1, height * 3 - 1)
        ImageDraw.Draw(mask).rounded_rectangle(box, radius * 3, fill=255)
        image.putalpha(mask.resize((width, height), Image.LANCZOS))
    return image


# Meaningful shapes -----------------------------------------------------------------
# Each builds a signed distance function from simple solids, the same way as the
# torus and cube. `parts` says which solid a point belongs to, for its colour.


def _sdf_sphere(p: np.ndarray, centre: tuple, radius: float) -> np.ndarray:
    return np.linalg.norm(p - np.array(centre), axis=1) - radius


def _sdf_ellipsoid(p: np.ndarray, centre: tuple, radii: tuple) -> np.ndarray:
    """An approximate distance to an ellipsoid (good enough for marching)."""
    q = p - np.array(centre)
    r = np.array(radii)
    k0 = np.linalg.norm(q / r, axis=1)
    k1 = np.linalg.norm(q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def _sdf_capsule(p: np.ndarray, a: tuple, b: tuple, radius: float) -> np.ndarray:
    """Distance to a rounded stick from a to b."""
    a, b = np.array(a), np.array(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - radius


def _sdf_round_cone(
    p: np.ndarray, a: tuple, b: tuple, r_a: float, r_b: float
) -> np.ndarray:
    """Distance to a smooth cone with round ends (Inigo Quilez's formula)."""
    a, b = np.array(a), np.array(b)
    ba = b - a
    l2 = ba @ ba
    rr = r_a - r_b
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = pa @ ba
    z = y - l2
    side = pa * l2 - y[:, None] * ba
    x2 = np.sum(side * side, axis=1)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    near_b = np.sign(z) * a2 * z2 > k
    near_a = np.sign(y) * a2 * y2 < k
    middle = (np.sqrt(x2 * a2 * il2) + y * rr) * il2 - r_a
    return np.where(
        near_b,
        np.sqrt(x2 + z2) * il2 - r_b,
        np.where(near_a, np.sqrt(x2 + y2) * il2 - r_a, middle),
    )


def _smooth_union(a: np.ndarray, b: np.ndarray, k: float = 0.08) -> np.ndarray:
    """Blend two shapes where they meet, like soft clay."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _flower_petals(p: np.ndarray, count: int = 6) -> np.ndarray:
    """Rounded petals around the z axis, cupped upwards like a real flower."""
    angle = np.arctan2(p[:, 1], p[:, 0])
    step = 2 * np.pi / count
    # Fold every point into one petal's slice: all petals are then one petal.
    folded = (angle + step / 2) % step - step / 2
    radius = np.hypot(p[:, 0], p[:, 1])
    cup = p[:, 2] - 0.42 * (radius - 0.3) ** 2
    local = np.stack([radius * np.cos(folded), radius * np.sin(folded), cup], axis=1)
    return _sdf_ellipsoid(local, (0.56, 0, 0.0), (0.44, 0.3, 0.11))


def _sdf_flower(p: np.ndarray) -> np.ndarray:
    return _smooth_union(_flower_petals(p), _sdf_sphere(p, (0, 0, 0.14), 0.25), 0.03)


def _sdf_heart(p: np.ndarray) -> np.ndarray:
    left = _sdf_round_cone(p, (-0.3, -0.3, 0), (0, 0.62, 0), 0.42, 0.04)
    right = _sdf_round_cone(p, (0.3, -0.3, 0), (0, 0.62, 0), 0.42, 0.04)
    return _smooth_union(left, right, 0.12)


def _sdf_drop(p: np.ndarray) -> np.ndarray:
    return _sdf_round_cone(p, (0, 0.3, 0), (0, -0.74, 0), 0.54, 0.02)


def _sdf_moon(p: np.ndarray) -> np.ndarray:
    outer = _sdf_sphere(p, (0, 0, 0), 0.74)
    # A soft-edged tube cut straight through gives a clean crescent outline.
    bite = np.hypot(p[:, 0] - 0.36, p[:, 1] + 0.14) - 0.6
    k = 0.06
    h = np.clip(0.5 - 0.5 * (outer + bite) / k, 0, 1)
    return outer * (1 - h) - bite * h + k * h * (1 - h)


def _sdf_dumbbell(p: np.ndarray) -> np.ndarray:
    bar = _sdf_capsule(p, (-0.62, 0, 0), (0.62, 0, 0), 0.085)
    left = _sdf_ellipsoid(p, (-0.62, 0, 0), (0.2, 0.42, 0.42))
    right = _sdf_ellipsoid(p, (0.62, 0, 0), (0.2, 0.42, 0.42))
    return _smooth_union(_smooth_union(left, right, 0.01), bar, 0.05)


def _sdf_thermometer(p: np.ndarray) -> np.ndarray:
    tube = _sdf_capsule(p, (0, 0.28, 0), (0, -0.74, 0), 0.15)
    bulb = _sdf_sphere(p, (0, 0.52, 0), 0.31)
    return _smooth_union(tube, bulb, 0.08)


def _apple_body(p: np.ndarray) -> np.ndarray:
    left = _sdf_sphere(p, (-0.2, 0.14, 0), 0.5)
    right = _sdf_sphere(p, (0.2, 0.14, 0), 0.5)
    return _smooth_union(left, right, 0.3)


def _apple_leaf(p: np.ndarray) -> np.ndarray:
    stem = _sdf_capsule(p, (0, -0.28, 0), (0.05, -0.58, 0), 0.035)
    leaf = _sdf_ellipsoid(p, (0.27, -0.56, 0), (0.25, 0.1, 0.05))
    return np.minimum(stem, leaf)


def _sdf_apple(p: np.ndarray) -> np.ndarray:
    return np.minimum(_apple_body(p), _apple_leaf(p))


def _sdf_smile(p: np.ndarray) -> np.ndarray:
    return _sdf_sphere(p, (0, 0, 0), 0.78)


def _sdf_gear(p: np.ndarray) -> np.ndarray:
    ring = _sdf_torus(p[:, [0, 2, 1]], 0.46, 0.17)
    angle = np.arctan2(p[:, 1], p[:, 0])
    step = 2 * np.pi / 8
    folded = (angle + step / 2) % step - step / 2
    radius = np.hypot(p[:, 0], p[:, 1])
    local = np.stack(
        [radius * np.cos(folded), radius * np.sin(folded), p[:, 2]], axis=1
    )
    q = np.abs(local - np.array((0.68, 0, 0))) - np.array((0.13, 0.08, 0.1))
    tooth = np.linalg.norm(np.maximum(q, 0.0), axis=1) - 0.04
    return _smooth_union(ring, tooth, 0.04)


# name: (distance function, extra colour rule or None, tilt x, tilt y, gloss)
SHAPES = {
    "flower": (_sdf_flower, "centre", 0.45, 0.3, 0.55),
    "heart": (_sdf_heart, None, 0.12, 0.35, 0.85),
    "drop": (_sdf_drop, None, 0.08, 0.3, 0.9),
    "moon": (_sdf_moon, None, 0.05, 0.3, 0.4),
    "dumbbell": (_sdf_dumbbell, None, 0.45, 0.6, 0.7),
    "thermometer": (_sdf_thermometer, "bulb", 0.1, 0.35, 0.85),
    "apple": (_sdf_apple, "leaf", 0.12, 0.25, 0.85),
    "smile": (_sdf_smile, "face", 0.05, 0.22, 0.7),
    "gear": (_sdf_gear, None, 0.5, 0.45, 0.65),
}


def _accent_points(rule: str, local: np.ndarray) -> np.ndarray:
    """Return which surface points take the shape's second colour."""
    if rule == "centre":  # the flower's golden heart
        return np.linalg.norm(local[:, :2], axis=1) < 0.26
    if rule == "bulb":  # the thermometer's bulb
        return local[:, 1] > 0.28
    if rule == "leaf":  # the apple's stem and leaf
        return _apple_leaf(local) < _apple_body(local)
    x, y = local[:, 0], local[:, 1]  # a smiling face
    eyes = np.minimum(np.hypot(x + 0.26, y + 0.2), np.hypot(x - 0.26, y + 0.2)) < 0.095
    smile = (np.abs(np.hypot(x, y + 0.08) - 0.42) < 0.05) & (y > 0.08)
    return eyes | smile


@lru_cache(maxsize=128)
def shape(
    name: str,
    size: int,
    base: tuple = PURPLE,
    glow: tuple = LILAC,
    accent: tuple = GOLD,
) -> Image.Image:
    """Return a glossy 3D shape from SHAPES, drawn once per size and colour."""
    sdf, rule, ax, ay, gloss = SHAPES[name]
    rotation = _rotation(ax, ay, 0.0)
    mask, points, alpha, ys = _march(size, sdf, rotation, 1.08)
    hit_points = points[mask]
    normals = _normals(hit_points, sdf, rotation)
    colours = _shade(normals, base, glow, ys[mask], gloss)
    if rule:
        inner = _accent_points(rule, hit_points @ rotation)
        if inner.any():
            colours[inner] = _shade(
                normals[inner], accent, (255, 245, 214), ys[mask][inner], gloss
            )
    return _image(size, mask, colours, alpha)


def logo(size: int) -> Image.Image:
    """Return Bloom's mark: the glossy flower in its own colours."""
    return shape("flower", size, (168, 85, 247), (253, 224, 255), GOLD)


# Aurora banners ----------------------------------------------------------------------


def _hue_rgb(hue: float, saturation: float, value: float) -> np.ndarray:
    return np.array(colorsys.hsv_to_rgb(hue % 1.0, saturation, value)) * 255


@lru_cache(maxsize=24)
def aurora(
    width: int,
    height: int,
    hue: float,
    dark: bool,
    radius: int = 0,
    text_share: float = 0.62,
    safe_luminance: float = TEXT_SAFE_LUMINANCE,
) -> Image.Image:
    """Return a soft gradient mesh in one hue, with white-text-safe contrast.

    Coloured glows drift across a deep base, like the sky at dusk. The picture is
    then darkened just enough that the left part, where text sits, stays below
    safe_luminance: white text keeps 4.5:1 in every colour theme.
    """
    xs = np.linspace(0, 1, width)[None, :]
    ys = np.linspace(0, 1, height)[:, None]
    deep = _hue_rgb(hue, 0.82, 0.34 if dark else 0.48)
    rgb = np.zeros((height, width, 3)) + deep
    glows = (
        (0.08, 0.05, 0.42, _hue_rgb(hue + 0.03, 0.72, 0.72), 0.75),
        (0.62, 1.05, 0.5, _hue_rgb(hue - 0.07, 0.68, 0.92), 0.9),
        (0.98, 0.1, 0.42, _hue_rgb(hue + 0.09, 0.45, 1.0), 0.85),
        (0.36, 0.5, 0.24, _hue_rgb(hue + 0.14, 0.6, 0.7), 0.35),
    )
    aspect = width / max(height, 1) * 0.42
    for cx, cy, size, colour, strength in glows:
        distance = ((xs - cx) * aspect) ** 2 + (ys - cy) ** 2
        glow = np.exp(-distance / (size**2))[..., None] * strength
        rgb = rgb + glow * (colour - rgb)
    # Keep the text side readable: scale until its brightest pixel is safe.
    linear = rgb / 255
    linear = np.where(
        linear <= 0.03928, linear / 12.92, ((linear + 0.055) / 1.055) ** 2.4
    )
    luminance = linear @ np.array((0.2126, 0.7152, 0.0722))
    text_side = luminance[:, : max(1, int(width * text_share))]
    brightest = float(text_side.max())
    if brightest > safe_luminance:
        # Gamma of about 2.2: luminance scales with value ** 2.2.
        rgb = rgb * (safe_luminance / brightest) ** (1 / 2.2)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    if radius:
        mask = Image.new("L", (width * 3, height * 3), 0)
        box = (0, 0, width * 3 - 1, height * 3 - 1)
        ImageDraw.Draw(mask).rounded_rectangle(box, radius * 3, fill=255)
        image.putalpha(mask.resize((width, height), Image.LANCZOS))
    return image


def sample(image: Image.Image, x: float, y: float) -> str:
    """Return the "#rrggbb" colour of an image at x, y (kept inside the image)."""
    px = min(max(int(x), 0), image.width - 1)
    py = min(max(int(y), 0), image.height - 1)
    r, g, b = image.convert("RGB").getpixel((px, py))
    return f"#{r:02x}{g:02x}{b:02x}"
