"""Floating combat text: damage numbers and pickups that pop and fade."""
from __future__ import annotations

import random

from .text import text


class Floaters:
    def __init__(self, cap: int = 60):
        self.items: list[list] = []   # [x, y, vy, text, colour, life, max_life, size]
        self.cap = cap

    def add(self, x: float, y: float, msg, color=(255, 255, 255), size: int = 16, life: float = 0.8) -> None:
        self.items.append([x + random.uniform(-8, 8), y, -110.0, str(msg), color, life, life, size])
        if len(self.items) > self.cap:
            self.items.pop(0)

    def damage(self, x, y, amount: float, crit: bool = False) -> None:
        n = f"{amount:.0f}" if amount >= 1 else f"{amount:.1f}"
        self.add(x, y, n + ("!" if crit else ""), (255, 235, 120) if crit else (255, 255, 255), 20 if crit else 15)

    def update(self, dt: float) -> None:
        for f in self.items:
            f[1] += f[2] * dt
            f[2] *= 0.92
            f[5] -= dt
        self.items = [f for f in self.items if f[5] > 0]

    def draw(self, surf, to_screen) -> None:
        for x, y, _vy, msg, col, life, max_life, size in self.items:
            k = min(1.0, life / (max_life * 0.4))
            pop = 1.0 + 0.35 * max(0.0, (life / max_life) - 0.8) / 0.2
            sx, sy = to_screen((x, y))
            text(surf, msg, (sx, sy), int(size * pop), tuple(int(c * k) for c in col), bold=True, anchor="center")
