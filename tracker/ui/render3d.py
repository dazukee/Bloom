"""Real-time 3D objects drawn with numpy: glossy spheres, a torus and cubes.

Tkinter cannot show 3D models, so each object is ray-marched: for every pixel
a ray travels into the scene until it meets the shape's surface, described by
a signed distance function (SDF). The surface normal then gives Lambert
diffuse light, a Phong highlight and a soft rim, in the app's purples.
Edges are anti-aliased from how closely each ray missed the shape.

Images are cached, so each object is drawn once per size and colour.
"""

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
