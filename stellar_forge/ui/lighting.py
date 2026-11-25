"""Cheap 2D lighting: a darkness layer with soft light holes cut into it.

Used for planet nights, caves and derelict interiors. The darkness is
rendered at half resolution and scaled up, which keeps it smooth and fast.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pygame

from .. import config
from ..core.assets import glow

SCALE = 3


@lru_cache(maxsize=32)
def _hole(radius: int) -> pygame.Surface:
    """Alpha-only radial sprite subtracted from the darkness."""
    size = radius * 2
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - radius + 0.5) ** 2 + (yy - radius + 0.5) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 1.4
    bayer = np.array([[0, 2], [3, 1]]) / 4.0
    yy, xx = np.mgrid[0:size, 0:size]
    a = np.floor(a * 4 + bayer[yy % 2, xx % 2] * 0.9) / 4          # four dithered steps, pixel-art style
    a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[...] = a.T
    del alpha
    return surf


class Lighting:
    def __init__(self):
        self.small = pygame.Surface((config.SCREEN_W // SCALE, config.SCREEN_H // SCALE), pygame.SRCALPHA)
        self.lights: list[tuple] = []

    def add(self, x: float, y: float, radius: float, color=None, strength: float = 1.0) -> None:
        """Screen-space light. ``color`` also adds a soft coloured glow."""
        if -radius < x < config.SCREEN_W + radius and -radius < y < config.SCREEN_H + radius:
            self.lights.append((x, y, radius, color, strength))

    def apply(self, surf: pygame.Surface, darkness: float, tint=(4, 6, 18)) -> None:
        """darkness: 0 (none) .. 255 (pitch black)."""
        if darkness <= 2:
            self.lights.clear()
            return
        small = self.small
        small.fill((*tint, int(darkness)))
        for x, y, r, _c, strength in self.lights:
            rr = max(4, int(r / SCALE) // 4 * 4)
            hole = _hole(rr)
            if strength < 1:
                hole = hole.copy()
                hole.fill((255, 255, 255, int(255 * strength)), special_flags=pygame.BLEND_RGBA_MULT)
            for _ in range(2 if strength >= 1 else 1):
                small.blit(hole, (x / SCALE - rr, y / SCALE - rr), special_flags=pygame.BLEND_RGBA_SUB)
        surf.blit(pygame.transform.scale(small, surf.get_size()), (0, 0))   # chunky, like the art
        k = darkness / 255
        for x, y, r, color, strength in self.lights:
            if color:
                g = glow(int(r * 0.5) // 8 * 8 + 8, color, round(min(1.0, 0.35 * k * k * strength + 0.05), 2))
                surf.blit(g, g.get_rect(center=(x, y)), special_flags=pygame.BLEND_ADD)
        self.lights.clear()
