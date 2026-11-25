"""Painted pixel-art backdrops for the front end: the nebula sky and the logo."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pygame

from . import pixelfont


def _noise(w, h, cell, seed):
    rng = np.random.default_rng(seed)
    gw, gh = int(w / cell) + 3, int(h / cell) + 3
    grid = rng.random((gh, gw)) * 2 - 1
    ys, xs = np.arange(h) / cell, np.arange(w) / cell
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = ys - y0, xs - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = grid[y0][:, x0], grid[y0][:, x0 + 1]
    c, d = grid[y0 + 1][:, x0], grid[y0 + 1][:, x0 + 1]
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy[:, None]


@lru_cache(maxsize=4)
def pixel_sky(seed: int = 3, w: int = 320, h: int = 180, scale: int = 4) -> pygame.Surface:
    """A nebula painted at 320x180 and scaled x4: stepped bands with ordered
    dithering between steps and pixel stars - the sprites' own grain."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    n = _noise(w, h, 40, seed) + 0.5 * _noise(w, h, 17, seed + 1) + 0.25 * _noise(w, h, 7, seed + 2)
    band = np.exp(-((yy - h * 0.42 - (xx - w * 0.5) * 0.28) / (h * 0.30)) ** 2)
    v = np.clip((n * 0.5 + 0.5) * band, 0, 1)
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    steps = np.floor(v * 5 + bayer[(yy % 4).astype(int), (xx % 4).astype(int)] * 0.9).clip(0, 4).astype(int)
    violet = np.array([(5, 7, 20), (16, 14, 44), (38, 22, 70), (72, 34, 96), (120, 60, 120)], float)
    teal = np.array([(5, 7, 20), (8, 22, 42), (12, 40, 64), (20, 70, 92), (40, 110, 120)], float)
    mix = (_noise(w, h, 60, seed + 4) > 0.1)[..., None]
    img = np.where(mix, teal[steps], violet[steps])
    surf = pygame.surfarray.make_surface(img.astype(np.uint8).transpose(1, 0, 2))
    for _ in range(220):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        surf.set_at((x, y), [(150, 160, 210), (210, 220, 255), (255, 236, 190)][int(rng.integers(0, 3))])
    for _ in range(10):
        x, y = int(rng.integers(2, w - 2)), int(rng.integers(2, h - 2))
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            surf.set_at((x + dx, y + dy), (255, 250, 230) if (dx, dy) == (0, 0) else (150, 170, 230))
    return pygame.transform.scale(surf, (w * scale, h * scale))


@lru_cache(maxsize=8)
def logo(text: str = "STELLAR FORGE", scale: int = 9) -> pygame.Surface:
    """Gold pixel-font logo: flat colour bands, dark outline, extruded depth."""
    base = pixelfont.render(text, (255, 255, 255), scale, None, None)
    w, h = base.get_size()
    out = pygame.Surface((w + 4 * scale, h + 6 * scale), pygame.SRCALPHA)
    dark = pixelfont.render(text, (40, 16, 10), scale, None, None)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            out.blit(dark, (2 * scale + dx * scale, 2 * scale + dy * scale))
    depth = pixelfont.render(text, (120, 46, 20), scale, None, None)
    for d in (1, 2):
        out.blit(depth, (2 * scale, 2 * scale + d * scale))
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    bands = [(255, 240, 180), (255, 206, 96), (240, 150, 52)]
    for i in range(8):
        grad.fill(bands[min(2, int(i * 3 / 8))], (0, i * scale, w, scale))
    grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(grad, (2 * scale, 2 * scale))
    return out
