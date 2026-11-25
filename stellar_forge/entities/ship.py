"""The player's rocket in space."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from .projectiles import Bullet, Missile
from ..core.assets import rot as _rot


class Controls:
    __slots__ = ("thrust", "turn", "boost", "match", "fire")

    def __init__(self):
        self.thrust = False
        self.turn = 0.0
        self.boost = False
        self.match = False
        self.fire = False


class PlayerShip:
    RADIUS = 26

    def __init__(self, game, pos: Vector2, vel: Vector2 | None = None):
        self.game = game
        self.state = game.state
        self.pos = Vector2(pos)
        self.vel = Vector2(vel or (0, 0))
        self.angle = 0.0                    # degrees, 0 = nose up
        self.fire_timer = 0.0
        self.shield_timer = 0.0
        self.hit_flash = 0.0
        self.thrusting = False
        self.boosting = False
        self.invuln = 0.0
        self._flame_t = 0.0
        self.weapon_t = 0.0
        self.load_hull()

    def load_hull(self) -> None:
        """(Re)load sprites for the ship type the player is flying."""
        from ..systems.items import SHIPS
        a = self.game.assets
        spec = SHIPS.get(self.state.ship, SHIPS["voyager"])
        if self.state.ship == "voyager":
            self.sprite = a.image("rocket/rocket.png")
            self.sprite_thrust = [a.image("rocket/centreflame.png"), a.image("rocket/leftflame.png"),
                                  a.image("rocket/rightflame.png")]
        else:
            self.sprite = a.image(spec["sprite"])
            self.sprite_thrust = [self._with_flame(self.sprite, k) for k in range(3)]
        self._rot = {}

    @staticmethod
    def _with_flame(img, k: int):
        """Generated hulls get a drawn flame, matching the rocket's flicker."""
        w, h = img.get_size()
        out = pygame.Surface((w, h + 26), pygame.SRCALPHA)
        fl = [(18, 8), (14, 6), (22, 9)][k]
        cx = w / 2
        pygame.draw.polygon(out, (255, 150, 60), [(cx - fl[1], h - 8), (cx + fl[1], h - 8), (cx, h - 8 + fl[0] + 8)])
        pygame.draw.polygon(out, (255, 230, 140), [(cx - fl[1] / 2, h - 8), (cx + fl[1] / 2, h - 8),
                                                   (cx, h - 8 + fl[0])])
        out.blit(img, (0, 0))
        return out

    @property
    def forward(self) -> Vector2:
        r = math.radians(self.angle)
        return Vector2(math.sin(r), -math.cos(r))

    # ------------------------------------------------------------------
    def update(self, dt: float, ctl: Controls, gravity: Vector2, match_vel: Vector2 | None,
               particles) -> list[Bullet]:
        st = self.state
        self.angle = (self.angle + ctl.turn * config.SHIP_TURN_SPEED * st.turn_mult * dt) % 360
        acc = Vector2(gravity)
        self.thrusting = self.boosting = False
        has_fuel = st.fuel > 0
        if ctl.thrust and has_fuel:
            mult = config.SHIP_BOOST_MULT if ctl.boost else 1.0
            acc += self.forward * st.thrust * mult
            burn = config.SHIP_FUEL_BURN * (config.SHIP_BOOST_BURN if ctl.boost else 1.0)
            st.fuel = max(0.0, st.fuel - burn * dt)
            self.thrusting, self.boosting = True, ctl.boost
            self._exhaust(particles, ctl.boost)
        elif ctl.match and has_fuel and match_vel is not None:
            rel = match_vel - self.vel
            if rel.length() > 2:
                a = rel.normalize() * min(st.thrust * 1.2, rel.length() / max(dt, 1e-3))
                acc += a
                st.fuel = max(0.0, st.fuel - config.SHIP_FUEL_BURN * 0.8 * dt * min(1, a.length() / st.thrust))
                if random.random() < 0.5:
                    self._puff(particles, -a)
        self.vel += acc * dt
        if self.vel.length() > config.SHIP_MAX_SPEED:
            self.vel.scale_to_length(config.SHIP_MAX_SPEED)
        self.pos += self.vel * dt

        # shields regenerate after a short delay
        self.shield_timer -= dt
        if self.shield_timer <= 0 and st.shield < st.max_shield:
            st.shield = min(st.max_shield, st.shield + config.SHIP_SHIELD_REGEN * (1 + 0.3 * st.lvl("shield")) * dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.invuln = max(0.0, self.invuln - dt)

        bullets = []
        self.fire_timer -= dt
        weapon = st.weapon if st.weapon in st.weapons else "blaster"
        if ctl.fire and self.fire_timer <= 0:
            d = self.forward
            if weapon == "missile":
                self.fire_timer = 0.85
                for side in (-1, 1):
                    m = Missile(self.pos + d.rotate(90 * side) * 16, self.vel + d.rotate(25 * side) * 380,
                                st.blaster_damage * 3.2)
                    bullets.append(m)
                self.game.audio.play("warp", 0.18)
            else:
                self.fire_timer = st.fire_delay
                spread = [0] if st.lvl("blaster") < 3 else [-4, 4]
                if st.ship == "gunship":
                    spread = [s + o for s in spread for o in (-1.5, 1.5)]
                for off in spread:
                    r = math.radians(self.angle + off)
                    dd = Vector2(math.sin(r), -math.cos(r))
                    bullets.append(Bullet(self.pos + dd * 30, self.vel + dd * config.BULLET_SPEED,
                                          st.blaster_damage * (0.6 if st.ship == "gunship" else 1.0), "player",
                                          (140, 230, 255)))
                self.game.audio.play("laser", 0.6)
        return bullets

    def cycle_weapon(self) -> str:
        st = self.state
        from ..systems.items import WEAPONS
        order = [w for w in WEAPONS if w in st.weapons]
        i = order.index(st.weapon) if st.weapon in order else 0
        st.weapon = order[(i + 1) % len(order)]
        return WEAPONS[st.weapon]["name"]

    def _exhaust(self, particles, boost: bool) -> None:
        back = -self.forward
        base = self.pos + back * 28
        n = 3 if boost else 2
        for _ in range(n):
            spread = Vector2(back).rotate(random.uniform(-14, 14))
            v = self.vel + spread * random.uniform(180, 320) * (1.5 if boost else 1)
            col = random.choice([(255, 220, 120), (255, 150, 60), (120, 200, 255)] if boost
                                else [(255, 220, 120), (255, 150, 60)])
            particles.emit(base.x, base.y, v.x, v.y, random.uniform(0.15, 0.4), random.uniform(3, 6),
                           col, drag=2.0, glow=True)

    def _puff(self, particles, direction: Vector2) -> None:
        d = Vector2(direction)
        if d.length_squared() == 0:
            return
        d = d.normalize()
        p = self.pos - d * 20
        v = self.vel - d * 160
        particles.emit(p.x, p.y, v.x, v.y, 0.25, 3, (200, 220, 255), drag=3.0)

    def damage(self, amount: float, shake=True) -> None:
        if self.invuln > 0 or amount <= 0:
            return
        st = self.state
        amount *= st.damage_taken
        self.shield_timer = config.SHIP_SHIELD_DELAY
        absorbed = min(st.shield, amount)
        st.shield -= absorbed
        st.hull = max(0.0, st.hull - (amount - absorbed))
        self.hit_flash = 0.25
        self.game.audio.play("hit", 0.7)
        if shake:
            self.game.shake(min(18, 4 + amount * 0.4))

    # ------------------------------------------------------------------
    def draw(self, surf, cam, clock) -> None:
        sx, sy = cam.to_screen(self.pos)
        scale = 2                                    # always draw at art scale - no resizing on camera switch
        if self.thrusting:
            self._flame_t += 1
            img = self.sprite_thrust[int(self._flame_t / 3) % 3]
        else:
            img = self.sprite
        rot = _rot(img, -self.angle, scale)
        surf.blit(rot, rot.get_rect(center=(sx, sy)))
        st = self.state
        if st.shield > 1 and self.hit_flash > 0:
            r = int(40 * scale)
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (120, 200, 255, int(180 * self.hit_flash / 0.25)), (r + 2, r + 2), r, 3)
            surf.blit(ring, (sx - r - 2, sy - r - 2))
        elif self.hit_flash > 0:
            pygame.draw.circle(surf, (255, 80, 60), (sx, sy), 36 * scale, 2)
