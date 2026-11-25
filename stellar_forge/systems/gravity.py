"""Gravity from the handful of bodies that matter right now.

Only the current star system (star + planets) and nearby hazards pull on
the ship, so cost is constant no matter how big the explored universe is.
"""
from __future__ import annotations

from pygame.math import Vector2

from .. import config


def acceleration(p: Vector2, t: float, sources) -> Vector2:
    acc = Vector2()
    soft2 = config.GRAVITY_SOFTENING ** 2
    for b in sources:
        if b.mu <= 0:
            continue
        d = b.pos(t) - p
        r2 = d.length_squared()
        # inside a solid body the collision code takes over; keep it finite
        r2 = max(r2, b.radius * b.radius * 0.8) + soft2 * 0.05
        acc += d * (b.mu / (r2 * r2 ** 0.5))
    return acc


def dominant_body(p: Vector2, t: float, sources):
    """The body with the strongest pull (used for velocity matching/HUD)."""
    best, best_a = None, 0.0
    for b in sources:
        if b.mu <= 0:
            continue
        r2 = max(1.0, (b.pos(t) - p).length_squared())
        a = b.mu / r2
        if a > best_a:
            best, best_a = b, a
    return best


def predict(p: Vector2, v: Vector2, t: float, sources, steps: int = 90, dt: float = 0.25):
    """Forward-simulate a ballistic path (planets keep moving on rails)."""
    pts = []
    pos, vel = Vector2(p), Vector2(v)
    solids = [b for b in sources if b.solid]
    for i in range(steps):
        tt = t + i * dt
        vel += acceleration(pos, tt, sources) * dt
        pos += vel * dt
        pts.append(Vector2(pos))
        hit = False
        for b in solids:
            if (b.pos(tt) - pos).length_squared() < b.radius ** 2:
                hit = True
                break
        if hit:
            break
    return pts
