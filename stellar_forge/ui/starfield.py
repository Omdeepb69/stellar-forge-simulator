"""Infinite parallax starfield built from hashed, cached tiles (never repeats)."""
from __future__ import annotations

import math
from collections import OrderedDict

import pygame

from ..world.rng import rng_of

TILE = 512
LAYERS = [  # parallax, star count, size range, brightness
    (0.04, 38, (1, 1), 120),
    (0.12, 22, (1, 2), 180),
    (0.3, 10, (1, 3), 240),
]


class Starfield:
    def __init__(self, seed: int):
        self.seed = seed
        self.cache: OrderedDict = OrderedDict()

    def _tile(self, layer: int, tx: int, ty: int) -> pygame.Surface:
        key = (layer, tx, ty)
        surf = self.cache.get(key)
        if surf is not None:
            self.cache.move_to_end(key)
            return surf
        _, count, (smin, smax), bright = LAYERS[layer]
        rng = rng_of(self.seed, "stars", layer, tx, ty)
        surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        if layer == 0 and rng.random() < 0.06:  # distant galaxy smudge
            cx, cy = rng.uniform(80, TILE - 80), rng.uniform(80, TILE - 80)
            col = rng.choice([(90, 60, 140), (60, 90, 140), (140, 80, 90)])
            for i in range(18, 0, -1):
                pygame.draw.ellipse(surf, (*col, 6), (cx - i * 4, cy - i * 1.6, i * 8, i * 3.2))
        for _ in range(count):
            x, y = rng.randrange(TILE), rng.randrange(TILE)
            b = rng.randint(bright // 2, bright)
            tint = rng.choice([(1, 1, 1), (1, 0.85, 0.7), (0.75, 0.85, 1), (1, 1, 0.8)])
            col = tuple(int(b * t) for t in tint)
            s = rng.randint(smin, smax)
            if s <= 1:
                surf.set_at((x, y), col)
            else:
                pygame.draw.circle(surf, col, (x, y), s - 0.5)
        # flatten onto black and key black out (run-length encoded): a blit then only touches the
        # stars, instead of alpha-blending a whole 512x512 tile every frame
        flat = pygame.Surface((TILE, TILE))
        flat.fill((0, 0, 0))
        flat.blit(surf, (0, 0))
        flat.set_colorkey((0, 0, 0), pygame.RLEACCEL)
        surf = flat
        self.cache[key] = surf
        if len(self.cache) > 72:
            self.cache.popitem(last=False)
        return surf

    def draw(self, surf: pygame.Surface, cam_x: float, cam_y: float) -> None:
        w, h = surf.get_size()
        for li, (par, *_rest) in enumerate(LAYERS):
            ox = cam_x * par
            oy = cam_y * par
            tx0 = math.floor((ox - w / 2) / TILE)
            ty0 = math.floor((oy - h / 2) / TILE)
            tx1 = math.floor((ox + w / 2) / TILE)
            ty1 = math.floor((oy + h / 2) / TILE)
            for ty in range(ty0, ty1 + 1):
                for tx in range(tx0, tx1 + 1):
                    sx = tx * TILE - ox + w / 2
                    sy = ty * TILE - oy + h / 2
                    surf.blit(self._tile(li, tx, ty), (sx, sy))
