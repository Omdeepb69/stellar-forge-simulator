"""Procedural prop sprites (crystals, lava spires, giant mushrooms) and ore nodes."""
from __future__ import annotations

import random
from functools import lru_cache

import pygame


def _shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


@lru_cache(maxsize=64)
def procedural(kind: str, height: int, tint: tuple, variant: int) -> pygame.Surface:
    rng = random.Random(variant)
    w = int(height * 0.8)
    surf = pygame.Surface((w, height), pygame.SRCALPHA)
    if kind == "crystal":
        for _ in range(rng.randint(3, 5)):
            cx = rng.uniform(w * 0.25, w * 0.75)
            hh = rng.uniform(0.45, 1.0) * height
            ww = rng.uniform(0.1, 0.18) * w
            lean = rng.uniform(-0.25, 0.25) * hh
            pts = [(cx - ww, height), (cx - ww * 0.8 + lean * 0.8, height - hh * 0.85),
                   (cx + lean, height - hh), (cx + ww * 0.8 + lean * 0.8, height - hh * 0.85), (cx + ww, height)]
            pygame.draw.polygon(surf, (*_shade(tint, 0.75), 235), pts)
            pygame.draw.polygon(surf, (*_shade(tint, 1.3), 255),
                                [pts[1], pts[2], (cx + lean * 0.5, height - hh * 0.2), (cx - ww * 0.6, height)])
            pygame.draw.lines(surf, (255, 255, 255, 180), False, [pts[1], pts[2], pts[3]], 2)
    elif kind == "spire":
        pts = [(w * 0.15, height), (w * 0.42, height * 0.25), (w * 0.5, 0), (w * 0.58, height * 0.3), (w * 0.85, height)]
        pygame.draw.polygon(surf, tint, pts)
        for i in range(4):
            y = height * (0.35 + i * 0.16)
            pygame.draw.line(surf, (255, 120, 30), (w * (0.42 - i * 0.04), y), (w * 0.55, y + 8), 3)
    elif kind == "mushroom":
        stem_w = w * 0.16
        pygame.draw.rect(surf, (225, 215, 200), (w / 2 - stem_w / 2, height * 0.35, stem_w, height * 0.65),
                         border_radius=6)
        cap = pygame.Rect(0, 0, w, height * 0.5)
        pygame.draw.ellipse(surf, tint, cap)
        pygame.draw.rect(surf, (0, 0, 0, 0), (0, height * 0.3, w, height * 0.25))
        for _ in range(5):
            pygame.draw.circle(surf, (255, 240, 255), (rng.uniform(w * 0.2, w * 0.8), rng.uniform(height * 0.06, height * 0.22)),
                               rng.uniform(3, 7))
    return surf


@lru_cache(maxsize=16)
def ore_node(color: tuple, fuel: bool) -> pygame.Surface:
    surf = pygame.Surface((44, 40), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (90, 84, 80), [(2, 40), (8, 16), (22, 8), (36, 14), (42, 40)])
    c = (255, 200, 60) if fuel else color
    for pts in ([(12, 34), (16, 12), (22, 30)], [(20, 34), (26, 6), (32, 32)], [(28, 36), (34, 18), (38, 36)]):
        pygame.draw.polygon(surf, c, pts)
        pygame.draw.line(surf, (255, 255, 255), pts[0], pts[1], 1)
    return surf
