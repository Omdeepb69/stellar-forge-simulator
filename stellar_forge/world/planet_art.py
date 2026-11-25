"""Pixel-art planets (see docs/ART_STYLE.md).

Planets are painted at a small native size with stepped light, a dithered
terminator, painted continents and clouds, then scaled with nearest-neighbour
so they share the chunky grain of every other sprite. Each biome has its own
look built from the shared perceptual palette (same lightness/chroma steps,
different hues).
"""
from __future__ import annotations

import math
from collections import OrderedDict

import numpy as np
import pygame

from .palette import hue_ramp

BASE_RADIUS = 32          # native radius in art pixels (64 px planets, 80 for gas giants)


def _noise(size, cell, seed):
    rng = np.random.default_rng(seed & 0xFFFFFFFF)
    g = int(size / cell) + 3
    grid = rng.random((g, g)) * 2 - 1
    t = np.arange(size) / cell
    i = t.astype(int)
    f = t - i
    f = f * f * (3 - 2 * f)
    a, b = grid[i][:, i], grid[i][:, i + 1]
    c, d = grid[i + 1][:, i], grid[i + 1][:, i + 1]
    top = a + (b - a) * f
    bot = c + (d - c) * f
    return top + (bot - top) * f[:, None]


# biome -> (base hue/chroma/light, land, highlights/specials)
LOOKS = {
    "desert": dict(base=(75, 0.55, 0.06), land=(55, 0.8, 0.0), poles=None, clouds=0.75, lake=None),
    "ice": dict(base=(220, 0.18, 0.14), land=(205, 0.5, 0.06), poles=(220, 0.1, 0.2), clouds=0.6, lake=None),
    "forest": dict(base=(255, 1.0, 0.0), land=(145, 1.0, 0.0), poles=(225, 0.2, 0.16), clouds=0.5, lake=None,
                   high=(75, 0.8, 0.0)),
    "ocean": dict(base=(245, 1.0, 0.0), land=(80, 0.6, 0.06), poles=(225, 0.2, 0.16), clouds=0.45, lake=None,
                  land_thr=0.45),
    "volcanic": dict(base=(300, 0.12, -0.12), land=(20, 0.1, -0.1), poles=None, clouds=0.85, lake=(45, 1.0, 0.04)),
    "toxic": dict(base=(125, 0.85, 0.0), land=(150, 0.7, -0.06), poles=None, clouds=0.6, lake=(105, 1.0, 0.1)),
    "crystal": dict(base=(290, 0.9, 0.0), land=(310, 0.9, 0.04), poles=None, clouds=0.8, lake=(215, 1.0, 0.06)),
    "barren": dict(base=(60, 0.06, 0.0), land=(60, 0.06, -0.06), poles=None, clouds=None, lake=None, craters=True),
}


def _ramp(spec):
    h, c, light = spec
    return np.array(hue_ramp(h, chroma=c, light=light), float)


def render_planet(seed: int, palette, gas: bool, rings: bool, liquid=None, biome: str | None = None,
                  size: int | None = None) -> pygame.Surface:
    """Paint a planet. ``biome`` picks the look; ``palette`` is a fallback."""
    size = size or (80 if gas else BASE_RADIUS * 2)
    pad = size // 2 if rings else 2
    W = size + 2 * pad
    yy, xx = np.mgrid[0:size, 0:size].astype(float) + 0.5
    r = size / 2 - 1
    nx, ny = (xx - size / 2) / r, (yy - size / 2) / r
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lam = np.clip(nx * -0.72 + ny * -0.42 + nz * 0.55, -1, 1)
    t = np.clip(0.06 + 0.94 * np.clip(lam + 0.12, 0, 1) ** 0.8 + 0.04 * _noise(size, 3, seed + 9), 0, 0.999)
    disc = np.hypot(xx - size / 2, yy - size / 2) - r
    big = 1.0 if size <= 64 else 1.5
    k = 4
    idx = np.clip((t * k).astype(int), 0, k - 1)
    if gas:
        hue = (seed % 360)
        bands = np.sin(ny * 9 + _noise(size, size / 4, seed) * 1.6) + 0.5 * np.sin(ny * 23 + 1)
        a = np.array(hue_ramp((hue + 40) % 360, chroma=0.55), float)
        b = np.array(hue_ramp(hue, chroma=0.7, light=0.04), float)
        col = np.where((bands > 0)[..., None], a[idx], b[idx])
        spot = np.hypot((nx - 0.25) / 0.22, (ny - 0.25) / 0.12) < 1
        col = np.where(spot[..., None], np.array(hue_ramp((hue + 340) % 360), float)[idx], col)
    else:
        look = LOOKS.get(biome or "", LOOKS["forest"])
        base, land = _ramp(look["base"]), _ramp(look["land"])
        n1 = _noise(size, size / (5 * big), seed) + 0.5 * _noise(size, size / (11 * big), seed + 1)
        col = base[idx]
        is_land = n1 > look.get("land_thr", 0.12)
        col = np.where(is_land[..., None], land[idx], col)
        if "high" in look:
            col = np.where((n1 > 0.55)[..., None], _ramp(look["high"])[idx], col)
        if look["lake"]:
            lake = (_noise(size, size / (7 * big), seed + 3) > 0.42) & ~is_land
            col = np.where(lake[..., None], _ramp(look["lake"])[np.clip(idx + 1, 0, 3)], col)
        if look.get("craters"):
            rng = np.random.default_rng(seed)
            for _ in range(int(6 * big)):
                cx, cy, cr = rng.uniform(4, size - 4), rng.uniform(4, size - 4), rng.uniform(2, 5) * big
                ring = np.abs(np.hypot(xx - cx, yy - cy) - cr) < 0.9
                col = np.where(ring[..., None], base[np.clip(idx - 1, 0, 3)], col)
        if look["poles"]:
            pole = np.abs(ny) > 0.8 + 0.08 * n1
            col = np.where(pole[..., None], _ramp(look["poles"])[idx], col)
        if look["clouds"] is not None:
            cn = _noise(size, size / (9 * big), seed + 5) + 0.4 * _noise(size, size / (18 * big), seed + 6)
            cr_ = np.array([(150, 165, 190), (205, 215, 232), (240, 245, 250)], float)
            clouds = (cn > look["clouds"]) & (lam > 0.05)
            col = np.where(clouds[..., None], cr_[np.clip((t * 3).astype(int), 0, 2)], col)
    night = (lam < -0.12) | ((lam < 0.05) & (((xx.astype(int) + yy.astype(int)) % 2) == 0))
    col = np.where(night[..., None], np.array([12, 10, 30], float), col)
    alpha = (disc < 0.4).astype(np.uint8) * 255
    surf = pygame.Surface((W, W), pygame.SRCALPHA)
    core = pygame.Surface((size, size), pygame.SRCALPHA)
    px = pygame.surfarray.pixels3d(core)
    px[...] = np.clip(col, 0, 255).astype(np.uint8).transpose(1, 0, 2)
    del px
    al = pygame.surfarray.pixels_alpha(core)
    al[...] = alpha.T
    del al
    if rings:
        ring_col = hue_ramp((seed * 7) % 360, chroma=0.4, light=0.06)
        back = pygame.Surface((W, W), pygame.SRCALPHA)
        front = pygame.Surface((W, W), pygame.SRCALPHA)
        c = W / 2
        for i, rr in enumerate(np.arange(size * 0.62, size * 0.9, 1.0)):
            colr = (*ring_col[1 + i % 3], 255)
            for a in np.linspace(0, math.tau, int(rr * 5)):
                x, y = c + math.cos(a) * rr, c + math.sin(a) * rr * 0.28
                (front if math.sin(a) > 0 else back).set_at((int(x), int(y)), colr)
        surf.blit(back, (0, 0))
        surf.blit(core, (pad, pad))
        surf.blit(front, (0, 0))
    else:
        surf.blit(core, (pad, pad))
    return surf


class SpriteCache:
    """Keeps native textures and a few nearest-neighbour rescales per body."""

    def __init__(self, max_scaled: int = 60):
        self.base: dict = {}
        self.scaled: OrderedDict = OrderedDict()
        self.max_scaled = max_scaled
        self.px = 0                       # pixels held by the rescales (kept under a budget)
        self.budget = 16_000_000

    def get(self, key, builder, screen_radius: float) -> pygame.Surface:
        base = self.base.get(key)
        if base is None:
            base = builder()
            self.base[key] = base
            if len(self.base) > 120:
                self.base.pop(next(iter(self.base)))
        disc = base.get_width() if base.get_width() == base.get_height() else base.get_width()
        native_r = disc / 2
        if base.get_width() > BASE_RADIUS * 2 + 20:     # ringed: disc is half the texture
            native_r = base.get_width() / 4
        if screen_radius >= native_r:
            k = max(1, round(screen_radius / native_r))   # whole-number scale: crisp pixels
        else:                                             # far away: shrink in eighths
            k = max(1 / 16, round(screen_radius / native_r * 8) / 8)
        skey = (key, k)
        surf = self.scaled.get(skey)
        if surf is None:
            w, h = base.get_size()
            surf = pygame.transform.scale(base, (max(1, int(w * k)), max(1, int(h * k))))
            self.scaled[skey] = surf
            self.px += surf.get_width() * surf.get_height()
            while self.scaled and (len(self.scaled) > self.max_scaled or self.px > self.budget):
                _k, old = self.scaled.popitem(last=False)
                self.px -= old.get_width() * old.get_height()
                if old is surf:
                    self.scaled[skey] = surf
                    self.px += surf.get_width() * surf.get_height()
                    break
        else:
            self.scaled.move_to_end(skey)
        return surf


SPRITES = SpriteCache()
