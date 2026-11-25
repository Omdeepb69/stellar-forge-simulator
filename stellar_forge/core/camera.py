"""Cameras for the zoomable space view and the side-scrolling surface view."""
from __future__ import annotations

import random

from pygame.math import Vector2

from .. import config


class SpaceCamera:
    def __init__(self, w: int = config.SCREEN_W, h: int = config.SCREEN_H):
        self.w, self.h = w, h
        self.pos = Vector2()
        self.zoom = 0.6
        self.target_zoom = 0.6
        self.min_zoom, self.max_zoom = 0.04, 2.0
        self.shake = 0.0
        self._offset = Vector2()

    def follow(self, target: Vector2, velocity: Vector2, dt: float) -> None:
        # look slightly ahead of where the ship is heading
        lead = velocity * 0.25
        desired = target + lead
        self.pos += (desired - self.pos) * min(1.0, dt * 6)
        self.zoom += (self.target_zoom - self.zoom) * min(1.0, dt * 6)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 30)
            self._offset = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)) * self.shake
        else:
            self._offset.update(0, 0)

    def snap(self, target: Vector2) -> None:
        self.pos = Vector2(target)

    def zoom_by(self, factor: float) -> None:
        self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom * factor))

    def to_screen(self, p) -> tuple[float, float]:
        return ((p[0] - self.pos.x) * self.zoom + self.w / 2 + self._offset.x,
                (p[1] - self.pos.y) * self.zoom + self.h / 2 + self._offset.y)

    def to_world(self, sx: float, sy: float) -> Vector2:
        return Vector2((sx - self.w / 2) / self.zoom + self.pos.x,
                       (sy - self.h / 2) / self.zoom + self.pos.y)

    def visible(self, p, radius: float, margin: float = 50) -> bool:
        sx, sy = self.to_screen(p)
        r = radius * self.zoom + margin
        return -r < sx < self.w + r and -r < sy < self.h + r

    @property
    def view_radius(self) -> float:
        """World-space radius that covers the screen."""
        return (self.w ** 2 + self.h ** 2) ** 0.5 / 2 / self.zoom


class SideCamera:
    """Smooth follow camera for platforming scenes (no zoom)."""

    def __init__(self, w: int = config.SCREEN_W, h: int = config.SCREEN_H):
        self.w, self.h = w, h
        self.x = 0.0
        self.y = 0.0
        self.shake = 0.0

    def follow(self, tx: float, ty: float, dt: float, snap: bool = False) -> None:
        dx = tx - self.w * 0.5
        dy = ty - self.h * 0.6
        if snap:
            self.x, self.y = dx, dy
        else:
            self.x += (dx - self.x) * min(1.0, dt * 7)
            self.y += (dy - self.y) * min(1.0, dt * 4)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 30)

    @property
    def ox(self) -> float:
        return self.x + (random.uniform(-1, 1) * self.shake if self.shake else 0)

    @property
    def oy(self) -> float:
        return self.y + (random.uniform(-1, 1) * self.shake if self.shake else 0)
