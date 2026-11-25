"""Survey Corps ships: allies that fight raiders, escort you and answer your hails."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from ..core.assets import rot as _rot
from .projectiles import Bullet

CORPS_BULLET = (255, 196, 90)
NAMES = ["KSV Plover", "KSV Tern", "KSV Heron", "KSV Swift", "KSV Petrel", "KSV Curlew", "KSV Wren", "KSV Lark",
         "KSV Avocet", "KSV Dunlin"]


class CorpsShip:
    """``role``: fighter (strafes raiders) or tender (refuels, repairs, tows).
    ``mode``: patrol (drift near an anchor), escort (stay with the player),
    service (fly to the player and help), depart (leave and vanish)."""

    def __init__(self, game, pos, role="fighter", mode="patrol", danger=1.0, name=None, art=None, tint=None,
                 hp=None, colour=None):
        self.game = game
        self.pos = Vector2(pos)
        self.vel = Vector2()
        self.angle = random.uniform(0, 360)
        self.role = role
        self.mode = mode
        self.anchor = Vector2(pos)
        self.name = name or random.choice(NAMES)
        self.max_hp = hp or ((70 if role == "fighter" else 110) + danger * 12)
        self.hp = self.max_hp
        self.accel = 520 if role == "fighter" else 380
        self.max_speed = 640 if role == "fighter" else 560
        self.damage = 1.4 + danger * 0.35
        self.fire_delay = 0.55
        self.fire_timer = random.uniform(0.2, 1.0)
        self.radius = 30 if role == "fighter" else 38
        self.orbit_dir = random.choice([-1, 1])
        self.preferred = random.uniform(300, 420)
        self.alive = True
        self.gone = False
        self.hit_flash = 0.0
        self.timer = 0.0                 # escort time left, or depart countdown
        self.service = None              # what a tender came to do
        self.offset = Vector2(random.choice([-1, 1]) * 140, 120)
        art = art or ("generated/ships/corps_fighter.png" if role == "fighter" else "generated/ships/corps_tender.png")
        self.sprite = game.assets.image(art, crop=True, tint=tint)
        self.colour = colour or (255, 190, 90)       # bullets and engine trail
        self.target = None

    # ---------------------------------------------------------------- AI
    def update(self, dt, ship, enemies, particles) -> list:
        self.hit_flash = max(0.0, self.hit_flash - dt)
        foe = None
        if self.role == "fighter" and self.mode != "depart":
            reach = 2600
            best = reach * reach
            for e in enemies:
                if not e.alive or getattr(e, "is_boss", False) and self.mode == "patrol":
                    continue
                d = e.pos.distance_squared_to(self.pos)
                if d < best:
                    best, foe = d, e
        self.target = foe
        desire = Vector2()
        if foe is not None:
            to = foe.pos - self.pos
            dist = to.length() or 1
            n = to / dist
            tangent = Vector2(-n.y, n.x) * self.orbit_dir
            if dist > self.preferred + 100:
                desire = n * self.max_speed + tangent * 140
            elif dist < self.preferred - 100:
                desire = -n * self.max_speed * 0.6 + tangent * self.max_speed * 0.6
            else:
                desire = tangent * self.max_speed * 0.8
            desire += foe.vel * 0.6
        elif self.mode == "follow":                 # a convoy: keep up with the pilot, a little behind
            want = ship.pos - ship.forward * 320 + self.offset * 0.6
            desire = (want - self.pos) * 1.8 + ship.vel
        elif self.mode == "escort":
            want = ship.pos + self.offset.rotate(-ship.angle)
            desire = (want - self.pos) * 2.5 + ship.vel
        elif self.mode == "service":
            to = ship.pos - self.pos
            dist = to.length()
            desire = to.normalize() * min(self.max_speed, dist * 1.6) + ship.vel if dist > 1 else ship.vel
        elif self.mode == "depart":
            away = (self.pos - ship.pos)
            desire = (away.normalize() if away.length_squared() > 1 else Vector2(1, 0)) * self.max_speed
            if away.length() > 4200:
                self.gone = True
        else:                                     # patrol: lazy loops round the anchor
            t = pygame.time.get_ticks() / 1000 * 0.3 + id(self) % 7
            want = self.anchor + Vector2(math.cos(t), math.sin(t)) * 500
            desire = (want - self.pos).normalize() * 260 if want != self.pos else Vector2()
        steer = desire - self.vel
        if steer.length() > self.accel * dt:
            steer.scale_to_length(self.accel * dt)
        self.vel += steer
        cap = self.max_speed * (2.2 if self.mode == "follow" else 1.6)
        if self.vel.length() > cap:
            self.vel.scale_to_length(cap)
        self.pos += self.vel * dt
        face = (foe.pos - self.pos) if foe is not None else self.vel
        if face.length_squared() > 1:
            target = math.degrees(math.atan2(face.x, -face.y))
            diff = (target - self.angle + 180) % 360 - 180
            self.angle += max(-300 * dt, min(300 * dt, diff))
        if steer.length_squared() > 4 and random.random() < 0.45:
            back = self.pos - Vector2(math.sin(math.radians(self.angle)), -math.cos(math.radians(self.angle))) * 26
            particles.emit(back.x, back.y, self.vel.x * 0.4, self.vel.y * 0.4, 0.25, 3, self.colour, drag=3,
                           glow=True)
        shots = []
        self.fire_timer -= dt
        if foe is not None and self.fire_timer <= 0:
            dist = foe.pos.distance_to(self.pos)
            if dist < 1300:
                self.fire_timer = self.fire_delay * random.uniform(0.8, 1.3)
                tof = dist / config.BULLET_SPEED
                aim = (foe.pos + (foe.vel - self.vel) * tof * 0.8) - self.pos
                if aim.length_squared() > 1:
                    aim = aim.normalize().rotate(random.uniform(-4, 4))
                    shots.append(Bullet(self.pos + aim * 30, self.vel + aim * config.BULLET_SPEED, self.damage,
                                        "ally", self.colour, life=1.6))
        return shots

    def hurt(self, dmg: float) -> bool:
        self.hp -= dmg
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf, cam) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-90 < sx < cam.w + 90 and -90 < sy < cam.h + 90):
            return
        scale = 2 if cam.zoom > 0.45 else 1
        img = _rot(self.sprite, -self.angle, scale)
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((160, 160, 160, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(img, img.get_rect(center=(sx, sy)))
        if self.hp < self.max_hp:
            w = 44 * scale / 2
            y = sy - 36 * scale
            surf.fill((40, 26, 10), (sx - w / 2, y, w, 4))
            surf.fill((255, 190, 90), (sx - w / 2, y, w * self.hp / self.max_hp, 4))
