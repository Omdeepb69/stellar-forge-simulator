"""Bullets and pickups that float around in space."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config


class Bullet:
    __slots__ = ("pos", "vel", "damage", "owner", "color", "life", "alive")

    def __init__(self, pos, vel, damage, owner, color, life=config.BULLET_LIFETIME):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.damage = damage
        self.owner = owner
        self.color = color
        self.life = life
        self.alive = True

    def update(self, dt) -> None:
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, cam) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-20 < sx < cam.w + 20 and -20 < sy < cam.h + 20):
            return
        d = self.vel.normalize() * max(6, 22 * cam.zoom) if self.vel.length_squared() else Vector2()
        pygame.draw.line(surf, self.color, (sx, sy), (sx - d.x, sy - d.y), max(2, int(4 * cam.zoom)))
        pygame.draw.circle(surf, (255, 255, 255), (sx, sy), max(1, int(2 * cam.zoom)))


PICKUP_STYLE = {
    "fuel": ((255, 200, 60), "F"),
    "repair": ((120, 255, 140), "+"),
    "credits": ((255, 240, 120), "$"),
    "ore": ((120, 255, 230), "o"),
    "data": ((200, 160, 255), "?"),
}


class Pickup:
    def __init__(self, pos, kind: str, amount: float, vel=None):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel) if vel is not None else Vector2(random.uniform(-60, 60), random.uniform(-60, 60))
        self.kind = kind
        self.amount = amount
        self.life = 40.0
        self.alive = True
        self.phase = random.uniform(0, math.tau)

    def update(self, dt, ship_pos: Vector2) -> None:
        d = ship_pos - self.pos
        dist = d.length()
        if dist < 420 and dist > 1:  # tractor beam
            self.vel += d / dist * 1400 * dt
            self.vel *= 0.93
        else:
            self.vel *= max(0.0, 1 - 0.6 * dt)
        self.pos += self.vel * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, cam, clock) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-20 < sx < cam.w + 20 and -20 < sy < cam.h + 20):
            return
        color, _ = PICKUP_STYLE[self.kind]
        r = max(4, 9 * cam.zoom) * (1 + 0.15 * math.sin(clock * 6 + self.phase))
        pygame.draw.circle(surf, color, (sx, sy), r, 2)
        pygame.draw.circle(surf, color, (sx, sy), r * 0.45)


class Missile(Bullet):
    """Player seeker missile: accelerates and homes on the nearest enemy."""
    __slots__ = ("target", "age")

    def __init__(self, pos, vel, damage):
        super().__init__(pos, vel, damage, "player", (255, 200, 120), life=4.0)
        self.target = None
        self.age = 0.0

    def steer(self, enemies, dt: float, particles=None) -> None:
        self.age += dt
        if self.target is None or not getattr(self.target, "alive", False):
            best, bd = None, 2200 ** 2
            for e in enemies:
                d = e.pos.distance_squared_to(self.pos)
                if e.alive and d < bd:
                    best, bd = e, d
            self.target = best
        speed = min(1300.0, self.vel.length() + 900 * dt)
        if self.target is not None and self.age > 0.15:
            want = (self.target.pos - self.pos)
            if want.length_squared() > 1:
                desired = want.normalize() * speed
                self.vel += (desired - self.vel) * min(1.0, 5.0 * dt)
        if self.vel.length_squared() > 1:
            self.vel.scale_to_length(speed)
        if particles is not None and random.random() < 0.8:
            back = self.pos - self.vel.normalize() * 10
            particles.emit(back.x, back.y, -self.vel.x * 0.1, -self.vel.y * 0.1, 0.35, 3,
                           random.choice([(255, 200, 120), (200, 200, 200)]), drag=2)

    def draw(self, surf, cam) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-20 < sx < cam.w + 20 and -20 < sy < cam.h + 20) or self.vel.length_squared() < 1:
            return
        d = self.vel.normalize() * max(8, 18 * cam.zoom)
        pygame.draw.line(surf, (230, 230, 240), (sx - d.x, sy - d.y), (sx, sy), max(3, int(6 * cam.zoom)))
        pygame.draw.circle(surf, (255, 90, 70), (sx, sy), max(2, int(4 * cam.zoom)))

