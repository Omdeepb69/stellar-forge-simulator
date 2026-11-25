"""pixelkit: paints sprites in the Stellar Forge house style (see docs/ART_STYLE.md).

Everything happens at native sprite resolution (no supersampling):

* Forms are signed distance fields (SDFs): negative inside, positive outside.
  They can be wobbled with smooth noise so edges look hand-painted.
* ``Sprite.paint`` pillow-shades a form from the top-left, adds brush mottling,
  quantises to a colour ramp, lays a soft dark rim in the same hue on the shadow
  side, and gives the edge about 1 px of partial alpha.
* ``Sprite.stroke`` and ``Sprite.dab`` add hand details (bark lines, cracks, shines).

The output is a small PNG that the game scales up with nearest-neighbour at
``config.ART_SCALE``, exactly like the original sprites.
"""
from __future__ import annotations

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import numpy as np  # noqa: E402
import pygame  # noqa: E402


# ----------------------------------------------------------------------------
# colour helpers
def hexc(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ramp(*cols) -> list:
    return [hexc(c) if isinstance(c, str) else tuple(c) for c in cols]


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# ---- perceptual palette (OkLCh) -------------------------------------------------
# Every hue gets the SAME lightness/chroma ladder, so a violet mushroom, a teal
# crawler and an orange crystal all sit at matching saturation and intensity.
# Ramps are hue-shifted: shadows lean cool (towards blue-violet), highlights
# lean warm (towards yellow) - the classic pixel-art ramp.
def _oklab_to_srgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    def enc(c):
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(int(round(enc(c) * 255)) for c in (r, g, bl))


def lch(L, C, h):
    """OkLCh -> sRGB, shrinking chroma until the colour fits in gamut."""
    for _ in range(30):
        a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
        l_ = L + 0.3963377774 * a + 0.2158037573 * b
        m_ = L - 0.1055613458 * a - 0.0638541728 * b
        s_ = L - 0.0894841775 * a - 1.2914855480 * b
        l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
        rgb = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
               -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
               -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
        if all(-0.001 <= c <= 1.001 for c in rgb):
            break
        C *= 0.93
    return _oklab_to_srgb(L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))


LADDER = [(0.31, 0.105), (0.44, 0.160), (0.57, 0.195), (0.69, 0.190), (0.81, 0.125)]


def _shift(h, target, k):
    d = (target - h + 180) % 360 - 180
    return h + d * k


def hue_ramp(h, levels=5, chroma=1.0, light=0.0, warm=72.0, cool=285.0):
    """A 3-5 step ramp for hue ``h`` (degrees, OkLCh) on the shared ladder."""
    out = []
    ladder = LADDER[:levels] if levels <= 5 else LADDER
    for i, (L, C) in enumerate(ladder):
        k = i / max(1, len(ladder) - 1)
        hh = _shift(h, cool, 0.22 * (1 - k) ** 1.5) if k < 0.5 else _shift(h, warm, 0.18 * (k - 0.5) * 2)
        out.append(lch(min(0.95, L + light), C * chroma, hh))
    return out


# Ramps measured from the original sprites, plus new ones built the same way:
# a dark same-hue base, saturated mids, one pale highlight.
R = {
    "pilot": ramp("#003B85", "#0B61A5", "#1874C9", "#1691C8", "#7FD3F0"),
    "alien": ramp("#001F04", "#063F0D", "#00580B", "#09981C", "#96B49A"),
    "cactus": ramp("#038A0E", "#06BC13", "#1FD72C", "#44E550", "#9DF5A2"),
    "leaf": ramp("#0C5B10", "#127016", "#1C781F", "#17931C", "#5BC85E"),
    "bark": ramp("#3B2C0C", "#59450F", "#6E5418", "#8A6C2A"),
    "stone": ramp("#4C4646", "#5D5D5D", "#787878", "#949494", "#B8B8B8"),
    "snow": ramp("#5BAA9E", "#91CDC4", "#AAECE3", "#BCF6ED", "#F3FEFC"),
    "sand": ramp("#904E17", "#B16B29", "#D38B4A", "#E69C5A", "#F6C48E"),
    "teal": ramp("#144748", "#135A5B", "#126E6F", "#179290", "#17AAAD"),
    "rust": ramp("#62311A", "#805D30", "#9A6A3A", "#B98A55"),
    "steel": ramp("#4A4C55", "#6B6E78", "#898887", "#A8A8A8", "#D0D2D6"),
    "gold": ramp("#6E5A12", "#908830", "#B0A024", "#D8C43C", "#F4E98A"),
    # new materials, built like the originals (saturated, same-hue ramps)
    "toxicgreen": ramp("#2C4A08", "#466F10", "#6A9A16", "#8CC21E", "#D2F27A"),
    "fungus": ramp("#4A1660", "#6E2390", "#9234B8", "#B455DA", "#E6B2F5"),
    "stem": ramp("#7A6A58", "#A8977F", "#CBBCA2", "#E6DAC2", "#FBF4E6"),
    "basalt": ramp("#1C1416", "#2C2125", "#3C2E33", "#52434A", "#6E5E66"),
    "lava": ramp("#9A2A06", "#D2460A", "#F57A12", "#FFB43A", "#FFE79A"),
    "crystal": ramp("#3C1C70", "#5A2EA0", "#7C48CC", "#A274EC", "#E2CCFF"),
    "aqua": ramp("#0A3E6E", "#11609E", "#1A86C8", "#3FB0E8", "#B6E6FF"),
    "coral": ramp("#7A1E2C", "#B0313E", "#D9505A", "#F07A7E", "#FFC2C0"),
    "bone": ramp("#8A8270", "#B0A890", "#D2CBB2", "#ECE6D0", "#FFFDF0"),
    "night": ramp("#0B0F24", "#141B3A", "#1E2850", "#2B3A6C", "#4A5C98"),
}


# ----------------------------------------------------------------------------
# noise
def value_noise(w, h, cell, seed):
    rng = np.random.default_rng(seed)
    gw, gh = int(w / cell) + 3, int(h / cell) + 3
    grid = rng.random((gh, gw)) * 2 - 1
    ys = np.arange(h) / cell
    xs = np.arange(w) / cell
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = ys - y0, xs - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a, b = grid[y0][:, x0], grid[y0][:, x0 + 1]
    c, d = grid[y0 + 1][:, x0], grid[y0 + 1][:, x0 + 1]
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy[:, None]


BAYER = np.array([[0, 2], [3, 1]]) / 4.0 - 0.375


# ----------------------------------------------------------------------------
class Sprite:
    def __init__(self, w: int, h: int, seed: int = 0):
        self.w, self.h, self.seed = w, h, seed
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        self.X, self.Y = xx + 0.5, yy + 0.5
        self.rgb = np.zeros((h, w, 3))
        self.a = np.zeros((h, w))
        self._n = 0

    # ---- coordinates -----------------------------------------------------
    def wobbled(self, amp=0.8, cell=5.0):
        """Coordinates bent by smooth noise: hand-painted, slightly lumpy edges."""
        self._n += 1
        nx = value_noise(self.w, self.h, cell, self.seed * 31 + self._n)
        ny = value_noise(self.w, self.h, cell, self.seed * 31 + self._n + 7)
        return self.X + nx * amp, self.Y + ny * amp

    # ---- painting ----------------------------------------------------------
    def paint(self, d, rmp, light=(-0.62, -0.78), mottle=0.07, rim=1.0, shine=0.0, pillow=None, flat=0.0,
              strokes=0.0, alpha=1.0, dither=0.0, bias=0.0, cell=6.0, highlight=0.0, grain=0.0):
        """Shade the form ``d`` with ramp ``rmp`` and composite it on top."""
        inside = np.clip(0.55 - d, 0.0, 1.0) * alpha
        if inside.max() <= 0:
            return
        depth = -d
        thick = max(2.0, float(np.percentile(depth[depth > 0], 90)) if (depth > 0).any() else 2.0)
        pillow = pillow or max(2.0, thick * 0.9)
        hgt = np.sqrt(np.clip(depth / pillow, 0, 1))
        gy, gx = np.gradient(hgt)
        lx, ly = light
        n = math.hypot(lx, ly)
        lx, ly = lx / n, ly / n
        lam = -(gx * lx + gy * ly) * pillow * 0.9
        # broad top-left to bottom-right falloff across the whole shape
        m = inside > 0.05
        cx, cy = (self.X[m].mean(), self.Y[m].mean()) if m.any() else (self.w / 2, self.h / 2)
        span = max(4.0, math.sqrt(m.sum()))
        broad = -((self.X - cx) * lx + (self.Y - cy) * ly) / span
        t = 0.48 + 0.42 * np.clip(lam, -1, 1) * (1 - flat) + 0.32 * broad + 0.12 * hgt + bias
        if mottle:   # broad, calm tone variation like a soft brush
            t += mottle * value_noise(self.w, self.h, cell, self.seed * 13 + self._n + 101)
        if grain:    # optional fine texture (stone, sand)
            t += grain * value_noise(self.w, self.h, 1.6, self.seed * 17 + self._n + 202)
        if strokes:   # directional brush strokes (bark, ridges)
            t += strokes * np.sin((self.X * 0.9 + value_noise(self.w, self.h, 4, self.seed + 9) * 3) * 1.7)
        t += BAYER[(self.Y.astype(int) % 2), (self.X.astype(int) % 2)] * dither
        k = len(rmp) - (1 if shine <= 0 and len(rmp) > 4 else 0)
        idx = np.clip((t * k).astype(int), 0, k - 1)
        if highlight:   # the big soft highlight blob of the originals (rock, cactus, pilot)
            hx, hy = cx + lx * span * 0.32 * highlight, cy + ly * span * 0.32 * highlight
            nb = value_noise(self.w, self.h, 4, self.seed + self._n + 55) * 1.2
            blob = (np.hypot((self.X - hx) / (span * 0.30), (self.Y - hy) / (span * 0.22)) * span * 0.25 + nb
                    < span * 0.25) & (depth > 1.5)
            idx = np.where(blob, np.minimum(idx + 1, k - 1 if shine <= 0 else len(rmp) - 1), idx)
        if shine > 0:   # the pale highlight only shows on the brightest bumps
            idx = np.where((t > 1.0 - shine * 0.25) & (hgt > 0.35), len(rmp) - 1, np.minimum(idx, len(rmp) - 2))
        if rim:
            edge = (depth < 1.35) & (depth > -0.6)
            shadow_side = (-(self.X - cx) * lx - (self.Y - cy) * ly) < span * 0.15
            idx = np.where(edge & (shadow_side | (rim > 1.5)), 0, idx)
        pal = np.array(rmp, float)
        col = pal[idx]
        self._over(col, inside)

    def flat(self, d, color, alpha=1.0, soft=0.55):
        inside = np.clip(soft - d, 0.0, 1.0) * alpha
        col = np.broadcast_to(np.array(color, float), (self.h, self.w, 3))
        self._over(col, inside)

    def stroke(self, pts, width, color, alpha=1.0, taper=False, wobble=0.0):
        """A painted line through ``pts``: bark, cracks, scribbles, antennae."""
        X, Y = (self.wobbled(wobble, 3.0) if wobble else (self.X, self.Y))
        d = np.full((self.h, self.w), 1e9)
        n = len(pts) - 1
        for i in range(n):
            r0 = width / 2 * (1 - (i / n) * 0.7 if taper else 1)
            r1 = width / 2 * (1 - ((i + 1) / n) * 0.7 if taper else 1)
            d = np.minimum(d, capsule(X, Y, pts[i], pts[i + 1], r0, r1))
        self.flat(d, color, alpha)

    def dab(self, x, y, r, color, alpha=1.0):
        self.flat(circle(self.X, self.Y, x, y, r), color, alpha)

    def speckle(self, d, color, density=0.06, alpha=1.0, seed=0):
        """Sparse single-pixel texture inside a form (spots, sand grains, rust)."""
        rng = np.random.default_rng(self.seed * 7 + seed)
        mask = (d < -1.0) & (rng.random(d.shape) < density)
        self._over(np.broadcast_to(np.array(color, float), (self.h, self.w, 3)), mask * alpha)

    def _over(self, col, a):
        a = a[..., None]
        out_a = a[..., 0] + self.a * (1 - a[..., 0])
        safe = np.where(out_a > 0, out_a, 1)[..., None]
        self.rgb = (col * a + self.rgb * self.a[..., None] * (1 - a)) / safe
        self.a = out_a

    # ---- output --------------------------------------------------------------
    def surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        px = pygame.surfarray.pixels3d(surf)
        px[...] = np.clip(self.rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2)
        del px
        al = pygame.surfarray.pixels_alpha(surf)
        a = np.clip(self.a, 0, 1)
        a = np.where(a < 0.12, 0, a)            # no faint halo pixels
        al[...] = (a * 255).astype(np.uint8).T
        del al
        return surf

    def save(self, path):
        path = str(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pygame.image.save(self.surface(), path)


# ----------------------------------------------------------------------------
# SDF primitives (X, Y are coordinate arrays, possibly wobbled)
def circle(X, Y, cx, cy, r):
    return np.hypot(X - cx, Y - cy) - r


def ellipse(X, Y, cx, cy, rx, ry, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    dx, dy = X - cx, Y - cy
    u, v = dx * c + dy * s, -dx * s + dy * c
    k = np.hypot(u / rx, v / ry)
    return (k - 1) * min(rx, ry)


def capsule(X, Y, a, b, ra, rb=None):
    rb = ra if rb is None else rb
    ax, ay = a
    bx, by = b
    px, py = X - ax, Y - ay
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy or 1e-9
    t = np.clip((px * vx + py * vy) / L2, 0, 1)
    dx, dy = px - vx * t, py - vy * t
    return np.hypot(dx, dy) - (ra + (rb - ra) * t)


def box(X, Y, cx, cy, hw, hh, r=0.0):
    qx = np.abs(X - cx) - hw + r
    qy = np.abs(Y - cy) - hh + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def poly(X, Y, pts):
    d = np.full(X.shape, 1e9)
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        d = np.minimum(d, capsule(X, Y, (x0, y0), (x1, y1), 0))
        cond = ((y0 > Y) != (y1 > Y)) & (X < (x1 - x0) * (Y - y0) / ((y1 - y0) or 1e-9) + x0)
        inside ^= cond
    return np.where(inside, -d, d)


def union(*ds):
    out = ds[0]
    for d in ds[1:]:
        out = np.minimum(out, d)
    return out


def smooth_union(a, b, k=3.0):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def subtract(a, b):
    return np.maximum(a, -b)


def intersect(a, b):
    return np.maximum(a, b)
