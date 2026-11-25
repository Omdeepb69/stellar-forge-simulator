"""Screen-space weather particles: snow, sandstorms, rain, ash, spores, sparkles."""
from __future__ import annotations

import math
import random

import pygame

from .. import config

STYLES = {
    "snow": dict(n=140, vx=(-30, 30), vy=(40, 110), size=(1, 3), color=(255, 255, 255)),
    "sand": dict(n=160, vx=(-520, -300), vy=(-20, 30), size=(1, 2), color=(240, 200, 140)),
    "rain": dict(n=170, vx=(-60, -40), vy=(700, 900), size=(1, 1), color=(150, 190, 255)),
    "ash": dict(n=110, vx=(-40, 20), vy=(20, 60), size=(1, 3), color=(90, 80, 80)),
    "spores": dict(n=70, vx=(-20, 20), vy=(-40, -10), size=(2, 3), color=(190, 255, 140)),
    "sparkle": dict(n=60, vx=(-10, 10), vy=(-10, 10), size=(1, 2), color=(255, 220, 255)),
}


class Weather:
    def __init__(self, kind: str | None, seed: int):
        self.kind = kind
        self.style = STYLES.get(kind or "", None)
        self.parts = []
        self.storm = 0.0
        self.storm_t = 0.0
        self.rng = random.Random(seed)
        if self.style:
            for _ in range(self.style["n"]):
                self.parts.append(self._new(randomize_y=True))

    def _new(self, randomize_y=False):
        s = self.style
        return [self.rng.uniform(0, config.SCREEN_W), self.rng.uniform(0, config.SCREEN_H) if randomize_y else -10,
                self.rng.uniform(*s["vx"]), self.rng.uniform(*s["vy"]), self.rng.uniform(*s["size"]),
                self.rng.uniform(0, math.tau)]

    def update(self, dt, cam_dx: float, cam_dy: float) -> None:
        if not self.style:
            return
        # occasional storms intensify sand / snow
        self.storm_t += dt
        self.storm = max(0.0, math.sin(self.storm_t * 0.05) * 1.6 - 0.6)
        mult = 1 + self.storm * 2
        W, H = config.SCREEN_W, config.SCREEN_H
        for p in self.parts:
            p[0] += p[2] * dt * mult - cam_dx * 0.6
            p[1] += p[3] * dt - cam_dy * 0.6
            p[5] += dt * 3
            if self.kind in ("snow", "spores"):
                p[0] += math.sin(p[5]) * 20 * dt
            if p[1] > H + 10 or p[1] < -20 or p[0] < -20 or p[0] > W + 20:
                np_ = self._new()
                if self.kind == "sand":
                    np_[0], np_[1] = W + 10, self.rng.uniform(0, H)
                elif self.kind == "spores":
                    np_[1] = H + 5
                    np_[0] = self.rng.uniform(0, W)
                else:
                    np_[0] = self.rng.uniform(-20, W + 20)
                p[:] = np_

    def draw(self, surf) -> None:
        if not self.style:
            return
        c = self.style["color"]
        if self.kind == "sand" and self.storm > 0:
            veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            veil.fill((230, 180, 120, int(70 * min(1, self.storm))))
            surf.blit(veil, (0, 0))
        for x, y, vx, vy, s, ph in self.parts:
            if self.kind == "rain":
                pygame.draw.line(surf, c, (x, y), (x + vx * 0.02, y + vy * 0.02), 1)
            elif self.kind == "sand":
                pygame.draw.line(surf, c, (x, y), (x + 8, y), 1)
            elif self.kind == "sparkle":
                if math.sin(ph) > 0.6:
                    pygame.draw.circle(surf, c, (x, y), s)
            else:
                pygame.draw.circle(surf, c, (x, y), s)
