"""Hostile alien fauna on planet surfaces."""
from __future__ import annotations

import math
import random

import pygame


_SPRITES: dict = {}
_POSES: dict = {}


def _sprite_pair(game, sprite: str, tint: tuple, size: int):
    """Creatures are drawn at the fixed art scale. Only the original alien is
    tinted per biome; painted creatures already carry their own palette."""
    tint = tint if sprite.startswith("alien/") else None
    key = (sprite, tint)
    pair = _SPRITES.get(key)
    if pair is None:
        right = game.assets.sprite(sprite, tint=tint)
        pair = _SPRITES[key] = (right, pygame.transform.flip(right, True, False))
    return pair


class Creature:
    def __init__(self, game, uid: str, x: float, kind: str, ground_fn, tint, danger: float,
                 sprites=("alien/alien.png", "alien/alien.png")):
        self.game = game
        self.id = uid
        self.kind = kind
        self.ground = ground_fn
        self.x = x
        self.y = ground_fn(x) - (290 if kind == "flyer" else 0)
        self.home_y = self.y
        self.vx = self.vy = 0.0
        self.hp = self.max_hp = ((2 if kind == "flyer" else 3) + int(danger * 0.6)) * game.state.enemy_hp_mult
        self.damage = 8 + danger * 2
        self.alive = True
        self.hop_t = random.uniform(0.5, 1.5)
        self.phase = random.uniform(0, math.tau)
        self.flash = 0.0
        self.facing = -1
        self.dive = 0.0
        sprite = sprites[0] if kind == "hopper" else sprites[1]
        self.img_r, self.img_l = _sprite_pair(game, sprite, tuple(tint), 0)
        self.size = int(max(self.img_r.get_width(), self.img_r.get_height()) * 0.8)

    @property
    def rect(self) -> pygame.Rect:
        s = self.size * 0.7
        return pygame.Rect(self.x - s / 2, self.y - s, s, s)

    def update(self, dt, px: float, py: float) -> None:
        dx = px - self.x
        near = abs(dx) < 820
        self.facing = 1 if dx > 0 else -1
        self.flash = max(0.0, self.flash - dt)
        if self.kind == "hopper":
            gy = self.ground(self.x)
            on_ground = self.y >= gy - 1
            if on_ground:
                self.vx *= max(0.0, 1 - 8 * dt)
                self.hop_t -= dt
                if self.hop_t <= 0:
                    self.hop_t = random.uniform(0.6, 1.3) if near else random.uniform(1.5, 3.0)
                    dirx = self.facing if near else random.choice([-1, 1])
                    self.vx = dirx * random.uniform(260, 440)
                    self.vy = -random.uniform(560, 820)
            self.vy += 2100 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            gy = self.ground(self.x)
            if self.y > gy:
                self.y, self.vy = gy, 0
        else:
            # Flyers behave like boss-arena minions: float, drift, fire orbs and dive
            self.phase += dt * 2.5
            self.fire_t = getattr(self, "fire_t", random.uniform(1.0, 2.5))
            if self.dive > 0:
                self.dive -= dt
                # dive toward the player
                self.y += 480 * dt
                self.x += self.facing * 190 * dt
                if self.dive <= 0:
                    self.home_y = self.y
            else:
                # drift side-to-side and bob, like boss Minion
                self.x += math.sin(self.phase * 0.7) * 60 * dt
                tx = px if near else self.x + math.sin(self.phase * 1.7) * 50
                self.x += max(-270, min(270, (tx - self.x) * 1.5)) * dt
                target_y = (py - 300 if near else self.ground(self.x) - 310)
                self.home_y += (target_y - self.home_y) * min(1, dt * 3)
                self.y = self.home_y + math.sin(self.phase * 2.3) * 30
                # fire or dive like boss minions
                self.fire_t -= dt
                if self.fire_t <= 0:
                    self.fire_t = random.uniform(1.6, 3.0)
                    if near and random.random() < 0.25:
                        self.dive = 1.2
            self.y = min(self.y, self.ground(self.x) - 10)

    def hurt(self, dmg: float, knock: float) -> bool:
        self.hp -= dmg
        self.flash = 0.15
        self.vx = knock * 480
        if self.kind == "hopper":
            self.vy = -400
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def _pose(self, img):
        """Cheap animation: hoppers stretch in the air and squash on the
        ground before a hop; flyers pulse like jellyfish."""
        if self.kind == "hopper":
            if self.y < self.ground(self.x) - 2:
                k = max(-1.0, min(1.0, -self.vy / 500))
                sx, sy = 1 - 0.1 * k, 1 + 0.14 * k
            else:
                k = max(0.0, 1 - self.hop_t / 0.35)   # crouch before hopping
                sx, sy = 1 + 0.15 * k, 1 - 0.15 * k
        else:
            sx = 1 + 0.08 * math.sin(self.phase * 2)
            sy = 1 - 0.08 * math.sin(self.phase * 2)
        key = (id(img), round(sx, 2), round(sy, 2))
        out = _POSES.get(key)
        if out is None:
            if len(_POSES) > 600:
                _POSES.clear()
            w, h = img.get_size()
            out = _POSES[key] = pygame.transform.scale(img, (max(1, int(w * sx)), max(1, int(h * sy))))
        return out

    def draw(self, surf, ox, oy) -> None:
        img = self._pose(self.img_r if self.facing > 0 else self.img_l)
        rect = img.get_rect(midbottom=(self.x - ox, self.y - oy + 4))
        surf.blit(img, rect)
        if self.flash > 0:
            f = img.copy()
            f.fill((200, 200, 200, 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(f, rect)
        if self.hp < self.max_hp:
            w = 40
            pygame.draw.rect(surf, (60, 0, 0), (rect.centerx - w / 2, rect.top - 8, w, 4))
            pygame.draw.rect(surf, (255, 90, 90), (rect.centerx - w / 2, rect.top - 8, w * self.hp / self.max_hp, 4))
