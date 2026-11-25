"""Lightweight particle system with a hard cap (old code sorted every frame)."""
from __future__ import annotations

import math
import random



class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "drag", "gravity", "glow")

    def __init__(self, x, y, vx, vy, life, size, color, drag=0.0, gravity=0.0, glow=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size, self.color = size, color
        self.drag, self.gravity, self.glow = drag, gravity, glow


class ParticleSystem:
    def __init__(self, cap: int = 900):
        self.items: list[Particle] = []
        self.cap = cap

    def emit(self, x, y, vx, vy, life, size, color, **kw) -> None:
        if len(self.items) >= self.cap:
            self.items.pop(0)
        self.items.append(Particle(x, y, vx, vy, life, size, color, **kw))

    def burst(self, x, y, count, speed, colors, life=(0.4, 1.0), size=(2, 5), base_v=(0, 0), **kw):
        for _ in range(count):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.2, 1.0) * speed
            self.emit(x, y, base_v[0] + math.cos(a) * s, base_v[1] + math.sin(a) * s,
                      random.uniform(*life), random.uniform(*size), random.choice(colors), **kw)

    def explosion(self, x, y, scale=1.0, base_v=(0, 0)):
        self.burst(x, y, int(40 * scale), 260 * scale, [(255, 240, 180), (255, 170, 60), (255, 90, 30)],
                   life=(0.3, 0.9), size=(2, 6 * scale), base_v=base_v, drag=1.5, glow=True)
        self.burst(x, y, int(16 * scale), 90 * scale, [(90, 90, 90), (60, 60, 60)],
                   life=(0.8, 1.6), size=(4, 9 * scale), base_v=base_v, drag=0.8)

    def update(self, dt: float) -> None:
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            if p.drag:
                f = max(0.0, 1 - p.drag * dt)
                p.vx *= f
                p.vy *= f
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.items = alive

    def draw(self, surf, to_screen, zoom: float = 1.0) -> None:
        w, h = surf.get_size()
        for p in self.items:
            sx, sy = to_screen((p.x, p.y))
            if sx < -20 or sy < -20 or sx > w + 20 or sy > h + 20:
                continue
            t = p.life / p.max_life
            # square pixels on the 2-px art grid, shrinking in whole steps as they fade
            n = max(2, int(p.size * zoom * (0.4 + 0.6 * t)) // 2 * 2)
            c = tuple(int(v * (0.35 + 0.65 * t)) for v in p.color) if p.glow else p.color
            surf.fill(c, (int(sx) // 2 * 2 - n // 2, int(sy) // 2 * 2 - n // 2, n, n))

    def clear(self) -> None:
        self.items.clear()
