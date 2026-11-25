"""The game's logo and window icon, painted in the house pixel style.

STELLAR FORGE in chunky gold letters (bevelled, outlined, extruded), set over the
Forge ring - the broken teal gate the whole story turns on - with a rocket's
trail crossing it and THE LAST VOYAGER underneath.
Output: generated/ui/logo.png (art pixels x3) and generated/ui/icon.png.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pygame

from .common import GEN

sys.path.insert(0, str(GEN.parent.parent))

GOLD_TOP = np.array([255, 244, 180])
GOLD_MID = np.array([255, 206, 92])
GOLD_LOW = np.array([232, 132, 46])
DEPTH = np.array([112, 44, 26])
INK = np.array([16, 10, 22])
TEAL = [(18, 60, 70), (30, 110, 118), (70, 190, 190), (150, 255, 236), (235, 255, 250)]


def _mask(text: str, scale: int) -> np.ndarray:
    from stellar_forge.ui import pixelfont
    img = pixelfont.render(text, (255, 255, 255), scale, None, None)
    return pygame.surfarray.array_alpha(img).T > 0          # rows x cols


def _shift(m, dy, dx):
    out = np.zeros_like(m)
    h, w = m.shape
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = m[ys, xs]
    return out


def _letters(text: str, scale: int, depth: int) -> np.ndarray:
    """RGBA (rows x cols x 4) chunky title lettering."""
    m = _mask(text, scale)
    pad = depth + 2
    m = np.pad(m, pad)
    h, w = m.shape
    rgba = np.zeros((h, w, 4), np.uint8)
    body = m
    ext = np.zeros_like(m)
    for k in range(1, depth + 1):
        ext |= _shift(m, k, 0)
    solid = body | ext
    outline = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            outline |= _shift(solid, dy, dx)
    outline &= ~solid
    rows = np.where(body.any(axis=1))[0]
    top, bot = rows.min(), rows.max()
    t = ((np.arange(h) - top) / max(1, bot - top)).clip(0, 1)[:, None, None]
    grad = np.where(t < 0.5, GOLD_TOP + (GOLD_MID - GOLD_TOP) * (t / 0.5), GOLD_MID + (GOLD_LOW - GOLD_MID) *
                    ((t - 0.5) / 0.5))
    grad = np.broadcast_to(grad, (h, w, 3))
    rgba[outline] = [*INK, 255]
    rgba[ext & ~body] = [*DEPTH, 255]
    rgba[body] = np.concatenate([grad[body], np.full((body.sum(), 1), 255)], axis=1)
    edge = body & ~_shift(body, 1, 0)                         # bright top edge on every stroke
    rgba[edge] = [255, 252, 228, 255]
    shade = body & ~_shift(body, 0, -1)                       # darker right edge
    rgba[shade, :3] = (rgba[shade, :3] * 0.82).astype(np.uint8)
    return rgba


def _surface(rgba: np.ndarray) -> pygame.Surface:
    h, w = rgba.shape[:2]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(s)[:] = rgba[:, :, :3].transpose(1, 0, 2)
    pygame.surfarray.pixels_alpha(s)[:] = rgba[:, :, 3].T
    return s


def _ring(surf, cx, cy, r, thick=5):
    """The Forge ring: a segmented teal band with a bright inner rim, broken at the bottom."""
    for y in range(int(cy - r - thick - 3), int(cy + r + thick + 4)):
        for x in range(int(cx - r - thick - 3), int(cx + r + thick + 4)):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            a = math.atan2(y + 0.5 - cy, x + 0.5 - cx)
            if r - thick <= d <= r:
                seg = (math.degrees(a) + 360) % 30
                if 1.5 < seg < 28.5 and not (60 < math.degrees(a) < 120):      # the broken gap at the bottom
                    k = (d - (r - thick)) / thick
                    col = TEAL[1] if k > 0.75 else TEAL[2] if k > 0.3 else TEAL[3]
                    if (x + y) % 2 == 0 and k > 0.75:
                        col = TEAL[0]
                    surf.set_at((x, y), (*col, 255))
            elif r < d <= r + 2.5:
                surf.set_at((x, y), (*TEAL[2], 70))                             # soft outer glow
            elif r - thick - 2.5 <= d < r - thick:
                surf.set_at((x, y), (*TEAL[3], 60))


def _star(surf, x, y, n=2, col=(255, 250, 220)):
    surf.set_at((x, y), (*col, 255))
    for k in range(1, n + 1):
        a = 255 - k * 70
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            surf.set_at((x + dx, y + dy), (*col, max(60, a)))


def logo(scale: int = 3) -> pygame.Surface:
    W, H = 320, 118
    art = pygame.Surface((W, H), pygame.SRCALPHA)
    cx, cy = W // 2, 52
    _ring(art, cx, cy, 50, 6)
    # a rocket trail sweeping through the ring
    for i in range(70):
        t = i / 69
        x = int(cx - 92 + t * 184)
        y = int(cy + 30 - math.sin(t * math.pi) * 52)
        a = int(40 + 180 * t)
        art.fill((150, 230, 255, a), (x, y, 2, 1))
        if i % 3 == 0:
            art.set_at((x, y + 1), (90, 160, 220, a // 2))
    art.fill((255, 255, 255, 255), (cx + 91, cy + 29, 2, 2))
    title = _surface(_letters("STELLAR", 3, 3))
    forge = _surface(_letters("FORGE", 4, 4))
    art.blit(title, title.get_rect(midtop=(cx, 4)))
    art.blit(forge, forge.get_rect(midtop=(cx, 4 + title.get_height() - 6)))
    from stellar_forge.ui import pixelfont
    sub = pixelfont.render("THE  LAST  VOYAGER", (150, 236, 255), 1, None, (12, 18, 34))
    sy = 4 + title.get_height() - 6 + forge.get_height() + 2
    art.blit(sub, sub.get_rect(midtop=(cx, sy)))
    for dx in (-1, 1):                                                         # little star rules either side
        x0 = cx + dx * (sub.get_width() // 2 + 8)
        for k in range(18):
            art.set_at((x0 + dx * k, sy + 4), (*TEAL[2], 200 - k * 9))
        _star(art, x0 + dx * 22, sy + 4, 2, (180, 245, 255))
    for x, y, n in ((34, 18, 2), (284, 26, 2), (60, 80, 1), (262, 84, 1), (cx + 58, 8, 1)):
        _star(art, x, y, n)
    return pygame.transform.scale(art, (W * scale, H * scale))


def icon(size: int = 256) -> pygame.Surface:
    """Generate a square RGBA icon at the requested size.

    The icon is painted at 64 px and scaled up to `size`, which should be a
    power-of-two (256 is good for Windows .ico, macOS .icns and Linux desktop
    files alike).  Callers that need multiple resolutions (e.g. .ico embedding)
    can call this several times with different sizes.
    """
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    _ring(s, 32, 32, 28, 7)
    letters = _surface(_letters("SF", 2, 2))
    s.blit(letters, letters.get_rect(center=(32, 32)))
    if size != 64:
        s = pygame.transform.smoothscale(s, (size, size))
    return s


def build_all():
    os.makedirs(GEN / "ui", exist_ok=True)
    pygame.image.save(logo(3), str(GEN / "ui" / "logo.png"))          # big, for the README / store page
    pygame.image.save(logo(1), str(GEN / "ui" / "logo_1x.png"))       # one art pixel = one pixel (the game scales it)
    # Cross-platform icons: 256×256 is the standard for Windows .ico, macOS
    # .icns and Linux .desktop / freedesktop.  Additional sizes let callers
    # build multi-resolution bundles.
    for sz in (16, 32, 48, 64, 128, 256):
        pygame.image.save(icon(sz), str(GEN / "ui" / f"icon_{sz}.png"))
    # The default icon.png is 256 px: big enough for any OS/desktop/launcher.
    pygame.image.save(icon(256), str(GEN / "ui" / "icon.png"))
    return ["ui/logo.png", "ui/logo_1x.png", "ui/icon.png"]
