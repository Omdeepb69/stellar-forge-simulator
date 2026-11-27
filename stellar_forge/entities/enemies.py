"""Raider AI for space combat."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from .projectiles import Bullet
from ..core.assets import rot as _rot


class Raider:
    """Steers to keep a strafing distance, leads its shots, flees when hurt."""

    def __init__(self, game, pos, danger: float, elite: bool = False, quest: bool = False):
        self.game = game
        self.pos = Vector2(pos)
        self.vel = Vector2()
        self.angle = random.uniform(0, 360)
        self.elite = elite
        self.quest = quest
        self.max_hp = (3 + danger * 1.3) * (2.5 if elite else 1) * game.state.enemy_hp_mult
        self.hp = self.max_hp
        self.accel = 300 + danger * 18 + (90 if elite else 0)
        self.max_speed = 520 + danger * 25
        self.fire_delay = max(0.35, 1.3 - danger * 0.06) * (0.6 if elite else 1)
        self.fire_timer = random.uniform(0.5, 2.0)
        self.damage = 6 + danger * 1.5
        self.orbit_dir = random.choice([-1, 1])
        self.preferred = random.uniform(320, 480)
        self.alive = True
        self.hit_flash = 0.0
        self.aggro = False
        tint = (255, 120, 120) if elite else None
        self.sprite = game.assets.image("alien/alien_ship/alienShip.png", crop=True, tint=tint)
        self.radius = 30 if not elite else 40
        self.bounty = int((20 + danger * 8) * (3 if elite else 1))

    def update(self, dt, ship, hidden: bool, particles) -> list[Bullet]:
        to = ship.pos - self.pos
        dist = to.length() or 1
        if dist < (1100 if hidden else 3400):
            self.aggro = True
        elif dist > 6000:
            self.aggro = False
        desire = Vector2()
        if self.aggro:
            n = to / dist
            tangent = Vector2(-n.y, n.x) * self.orbit_dir
            if self.hp < self.max_hp * 0.25 and not self.elite:
                desire = -n * self.max_speed  # flee
            elif dist > self.preferred + 120:
                desire = n * self.max_speed + tangent * 120
            elif dist < self.preferred - 120:
                desire = -n * self.max_speed * 0.6 + tangent * self.max_speed * 0.6
            else:
                desire = tangent * self.max_speed * 0.8
            desire += ship.vel * 0.8
        else:
            desire = Vector2(math.cos(self.angle * 0.01), math.sin(self.angle * 0.01)) * 120
        steer = desire - self.vel
        if steer.length() > self.accel * dt:
            steer.scale_to_length(self.accel * dt)
        self.vel += steer
        self.pos += self.vel * dt
        face = to if self.aggro else self.vel
        if face.length_squared() > 1:
            target = math.degrees(math.atan2(face.x, -face.y))
            diff = (target - self.angle + 180) % 360 - 180
            self.angle += max(-260 * dt, min(260 * dt, diff))
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if steer.length_squared() > 4 and random.random() < 0.4:
            back = self.pos - Vector2(math.sin(math.radians(self.angle)), -math.cos(math.radians(self.angle))) * 24
            particles.emit(back.x, back.y, self.vel.x * 0.5, self.vel.y * 0.5, 0.25, 3, (120, 255, 140), drag=3, glow=True)

        shots = []
        self.fire_timer -= dt
        if self.aggro and dist < 1500 and self.fire_timer <= 0:
            self.fire_timer = self.fire_delay * random.uniform(0.8, 1.3)
            # lead the target
            tof = dist / config.ENEMY_BULLET_SPEED
            aim = (ship.pos + (ship.vel - self.vel) * tof * 0.8) - self.pos
            if aim.length_squared() > 1:
                aim = aim.normalize().rotate(random.uniform(-5, 5))
                count = 3 if self.elite else 1
                for i in range(count):
                    d = aim.rotate((i - (count - 1) / 2) * 8)
                    shots.append(Bullet(self.pos + d * 30, self.vel + d * config.ENEMY_BULLET_SPEED,
                                        self.damage, "enemy", (130, 255, 120), life=2.4))
                self.game.audio.play("enemy_laser", 0.35)
        return shots

    def hurt(self, dmg: float) -> bool:
        self.hp -= dmg
        self.hit_flash = 0.12
        self.aggro = True
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf, cam) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-80 < sx < cam.w + 80 and -80 < sy < cam.h + 80):
            return
        scale = (2 if self.elite else 1.5) if cam.zoom > 0.45 else 1
        img = _rot(self.sprite, -self.angle, scale)
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((180, 180, 180, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(img, img.get_rect(center=(sx, sy)))
        if self.hp < self.max_hp:
            w = 40 * scale
            pygame.draw.rect(surf, (60, 0, 0), (sx - w / 2, sy - 40 * scale, w, 4))
            pygame.draw.rect(surf, (255, 80, 80), (sx - w / 2, sy - 40 * scale, w * self.hp / self.max_hp, 4))
        if self.quest:
            pygame.draw.circle(surf, (255, 200, 60), (sx, sy), 34 * scale, 1)


class Torpedo(Bullet):
    """Slow, homing enemy round. Can be shot down."""
    __slots__ = ("turn",)

    def __init__(self, pos, vel, damage):
        super().__init__(pos, vel, damage, "enemy", (255, 150, 60), life=6.0)
        self.turn = 2.2

    def steer(self, target: Vector2, dt: float) -> None:
        want = target - self.pos
        if want.length_squared() < 1:
            return
        speed = self.vel.length() or 1
        desired = want.normalize() * speed
        self.vel += (desired - self.vel) * min(1.0, self.turn * dt)

    def draw(self, surf, cam) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-20 < sx < cam.w + 20 and -20 < sy < cam.h + 20):
            return
        r = max(3, int(7 * cam.zoom))
        pygame.draw.circle(surf, (255, 120, 40), (sx, sy), r + 2)
        pygame.draw.circle(surf, (255, 230, 150), (sx, sy), r)


class Dreadnought:
    """Remnant flagship / Shard Warden: a slow, heavily armed space boss.

    Cycles through attack patterns (broadside fans, radial bursts, homing
    torpedoes, escort launches) and gets angrier below half health.
    """

    elite = True
    quest = False
    is_boss = True

    def __init__(self, game, pos, danger: float, warden: str | None = None, name: str | None = None):
        self.game = game
        self.pos = Vector2(pos)
        self.vel = Vector2()
        self.angle = 180.0
        self.warden = warden
        self.name = name or ("Remnant Warden" if warden else "Remnant Flagship")
        self.danger = danger
        self.max_hp = (70 + danger * 16) * game.state.enemy_hp_mult
        self.hp = self.max_hp
        self.radius = 95
        self.alive = True
        self.aggro = False
        self.hit_flash = 0.0
        self.timer = 2.5
        self.pattern = 0
        self.burst_left = 0
        self.burst_t = 0.0
        self.escort_cd = 6.0
        self.damage = 7 + danger * 1.6
        self.bounty = int(500 + danger * 160)
        self.spawn_queue: list = []
        self.sprite = game.assets.image("generated/ships/dreadnought.png")
        self._rot_cache: dict = {}

    @property
    def enraged(self) -> bool:
        return self.hp < self.max_hp * 0.5

    def update(self, dt, ship, hidden: bool, particles) -> list:
        if getattr(self, "passive", False):        # crippled and silent (the Penitent, until you decide)
            self.vel *= 0.98
            self.pos += self.vel * dt
            self.hit_flash = max(0.0, self.hit_flash - dt)
            return []
        to = ship.pos - self.pos
        dist = to.length() or 1
        if dist < (1800 if hidden else 3800):
            if not self.aggro:
                self.game.audio.play("alarm", 0.7)
            self.aggro = True
        elif dist > 9000:
            self.aggro = False
        # slow drift that keeps a comfortable firing distance
        want = Vector2()
        if self.aggro:
            n = to / dist
            if dist > 900:
                want = n * 160
            elif dist < 550:
                want = -n * 140
            want += Vector2(-n.y, n.x) * 60
        self.vel += (want - self.vel) * min(1.0, 0.8 * dt)
        self.pos += self.vel * dt
        target = math.degrees(math.atan2(to.x, -to.y))
        diff = (target - self.angle + 180) % 360 - 180
        self.angle += max(-40 * dt, min(40 * dt, diff))
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if random.random() < 0.5:
            back = self.pos - Vector2(math.sin(math.radians(self.angle)), -math.cos(math.radians(self.angle))) * 90
            particles.emit(back.x, back.y, -self.vel.x * 0.2 + random.uniform(-40, 40), -self.vel.y * 0.2,
                           0.6, 7, (255, 150, 60), drag=2, glow=True)
        if self.enraged and random.random() < 0.3:
            p = self.pos + Vector2(random.uniform(-60, 60), random.uniform(-60, 60))
            particles.emit(p.x, p.y, 0, -30, 0.8, 6, (90, 90, 90), drag=1)

        shots: list = []
        if not self.aggro or dist > 2400:
            return shots
        speed_k = 1.35 if self.enraged else 1.0
        if self.burst_left > 0:
            self.burst_t -= dt
            if self.burst_t <= 0:
                self.burst_left -= 1
                self.burst_t = 0.12 / speed_k
                shots += self._fire_pattern(ship, single=True)
            return shots
        self.timer -= dt * speed_k
        if self.timer <= 0:
            self.pattern = (self.pattern + 1) % 4
            self.timer = random.uniform(1.8, 2.6)
            shots += self._fire_pattern(ship)
        self.escort_cd -= dt
        if self.escort_cd <= 0:
            self.escort_cd = 16 if not self.enraged else 11
            for k in (-1, 1):
                side = Vector2(-to.y, to.x).normalize() * k * 160
                r = Raider(self.game, self.pos + side, self.danger * 0.8)
                r.aggro = True
                self.spawn_queue.append(r)
        return shots

    def _fire_pattern(self, ship, single=False) -> list:
        aim = (ship.pos - self.pos)
        aim = aim.normalize() if aim.length_squared() > 1 else Vector2(0, 1)
        out = []
        sp = config.ENEMY_BULLET_SPEED
        if self.pattern == 0:      # broadside fan
            n = 9 if self.enraged else 7
            for i in range(n):
                d = aim.rotate((i - (n - 1) / 2) * 9)
                out.append(Bullet(self.pos + d * 80, self.vel + d * sp * 0.9, self.damage, "enemy",
                                  (130, 255, 160), life=3.0))
            self.game.audio.play("enemy_laser", 0.6)
        elif self.pattern == 1:    # radial burst
            n = 20 if self.enraged else 14
            off = random.uniform(0, 360)
            for i in range(n):
                d = Vector2(1, 0).rotate(off + i * 360 / n)
                out.append(Bullet(self.pos + d * 80, self.vel + d * sp * 0.6, self.damage * 0.8, "enemy",
                                  (200, 255, 120), life=3.5))
            self.game.audio.play("enemy_laser", 0.7)
        elif self.pattern == 2:    # homing torpedoes
            for k in (-1, 1) if not self.enraged else (-1, 0, 1):
                d = aim.rotate(60 * k) if k else aim
                out.append(Torpedo(self.pos + d * 90, self.vel + d * 260, self.damage * 1.6))
            self.game.audio.play("warp", 0.25)
        else:                      # aimed machine-gun burst
            if not single:
                self.burst_left = 10 if self.enraged else 7
                self.burst_t = 0.0
                return out
            d = aim.rotate(random.uniform(-4, 4))
            for off in (-34, 34):
                side = Vector2(-d.y, d.x) * off
                out.append(Bullet(self.pos + d * 70 + side, self.vel + d * sp * 1.15, self.damage * 0.6, "enemy",
                                  (255, 230, 120), life=2.4))
            self.game.audio.play("enemy_laser", 0.25)
        return out

    def hurt(self, dmg: float) -> bool:
        self.hp -= dmg
        self.hit_flash = 0.08
        self.aggro = True
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surf, cam) -> None:
        sx, sy = cam.to_screen(self.pos)
        if not (-200 < sx < cam.w + 200 and -200 < sy < cam.h + 200):
            return
        scale = 2 if cam.zoom > 0.45 else 1
        ang = int(self.angle) // 3 * 3
        key = (ang, scale)
        img = self._rot_cache.get(key)
        if img is None:
            if len(self._rot_cache) > 160:
                self._rot_cache.clear()
            img = _rot(self.sprite, -ang, scale)
            self._rot_cache[key] = img
        if self.hit_flash > 0:
            img = img.copy()
            img.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(img, img.get_rect(center=(sx, sy)))
        if self.aggro:
            pygame.draw.circle(surf, (255, 90, 90), (sx, sy), 110 * scale, 1)
