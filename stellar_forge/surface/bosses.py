"""Planet bosses: legendary beasts guarding rare worlds.

Each fights on its own arena (a wide flat pad on the surface) and every
attack is telegraphed: a warning marker, a wind-up or a rumble first.

  Sand Wyrm  (desert)   burrows, erupts under you, spits sand when angry
  Leviathan  (ocean)    a bigger sea-serpent cousin that sprays water orbs
  Frost Golem (ice)     slams shockwaves you must jump, hurls boulders, ice spikes
  Magma Titan (volcanic) armoured; magma eruptions expose its core
  Hive Queen (crystal)  summons drones, fires shard rings, dive-bombs then stalls
"""
from __future__ import annotations

import math
import random
from collections import deque

import pygame

from ..core.assets import glow
from ..systems.items import BOSSES


def _orb(color, r):
    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r, 0, -1):
        k = i / r
        c = tuple(min(255, int(v + (255 - v) * (1 - k) ** 2)) for v in color)
        pygame.draw.circle(surf, (*c, int(255 * (1 - k) ** 0.5)), (r, r), i)
    return surf


class Shot:
    __slots__ = ("x", "y", "vx", "vy", "r", "dmg", "img", "grav", "life")

    def __init__(self, x, y, vx, vy, r, dmg, img, grav=0.0, life=4.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.r, self.dmg, self.img, self.grav, self.life = r, dmg, img, grav, life


class Telegraph:
    """A pulsing warning marker on the ground: something is about to hit here."""
    __slots__ = ("x", "y", "t", "total", "w", "color")

    def __init__(self, x, y, t, w=70, color=(255, 120, 60)):
        self.x, self.y, self.t, self.total, self.w, self.color = x, y, t, t, w, color


class PlanetBoss:
    behind_ground = False
    base_hp = 60
    contact = 18

    def __init__(self, scene, x: float):
        self.scene = scene
        self.game = scene.game
        self.pilot = scene.pilot
        self.t_fn = scene.terrain.height
        info = BOSSES[scene.biome.id]
        self.name = info["name"]
        self.biome = scene.biome.id
        self.home = x
        self.x = x
        self.y = self.t_fn(x)
        danger = scene.danger
        self.max_hp = self.base_hp * (1 + 0.22 * danger) * self.game.state.enemy_hp_mult
        self.hp = self.max_hp
        self.dmg = 10 + danger * 2.2
        self.alive = True
        self.t = 0.0
        self.state = "intro"
        self.state_t = 1.6
        self.flash = 0.0
        self.shots: list[Shot] = []
        self.telegraphs: list[Telegraph] = []
        self.facing = -1
        self.hurt_mult = 1.0

    # ---- shared helpers ------------------------------------------------
    @property
    def enraged(self) -> bool:
        return self.hp < self.max_hp * 0.5

    def ground(self, x):
        return self.t_fn(x)

    def clamp_arena(self, x, margin=1050):
        return max(self.home - margin, min(self.home + margin, x))

    def go(self, state, t):
        self.state, self.state_t = state, t

    def hurt(self, dmg: float) -> bool:
        dmg *= self.hurt_mult
        self.hp -= dmg
        self.flash = 0.1
        if self.hp <= 0 and self.alive:
            self.alive = False
            return True
        return False

    def hitboxes(self) -> list[pygame.Rect]:
        return []

    def fire(self, x, y, vx, vy, r=13, color=(255, 200, 120), grav=0.0, dmg=None):
        key = (color, r)
        img = _ORBS.get(key)
        if img is None:
            img = _ORBS[key] = _orb(color, r)
        self.shots.append(Shot(x, y, vx, vy, r, dmg or self.dmg * 0.8, img, grav))

    def lob(self, x, y, tx, ty, time=1.1, **kw):
        """Ballistic shot that lands near (tx, ty) after ``time`` seconds."""
        g = 1300.0
        vx = (tx - x) / time
        vy = (ty - y - 0.5 * g * time * time) / time
        self.fire(x, y, vx, vy, grav=g, **kw)

    def _common(self, dt) -> None:
        self.t += dt
        self.state_t -= dt
        self.flash = max(0.0, self.flash - dt)
        p = self.pilot
        for s in self.shots:
            s.x += s.vx * dt
            s.y += s.vy * dt
            s.vy += s.grav * dt
            s.life -= dt
            if s.y > self.ground(s.x) + 4:
                s.life = 0
                self.scene.particles.burst(s.x, s.y, 8, 120, [(220, 200, 160), (255, 255, 255)], life=(0.2, 0.5))
            elif p.rect.inflate(s.r, s.r).collidepoint(s.x, s.y):
                s.life = 0
                p.hurt(s.dmg, 1 if p.x > s.x else -1)
        self.shots = [s for s in self.shots if s.life > 0]
        for tg in self.telegraphs:
            tg.t -= dt
        self.telegraphs = [tg for tg in self.telegraphs if tg.t > 0]
        if self.state != "intro":
            for r in self.hitboxes():
                if r.colliderect(p.rect):
                    p.hurt(self.contact, 1 if p.x > r.centerx else -1)
                    break

    def update(self, dt) -> None:
        self._common(dt)

    # ---- drawing ------------------------------------------------------------
    def draw_fx(self, surf, ox, oy) -> None:
        for tg in self.telegraphs:
            k = 1 - tg.t / tg.total
            pulse = 0.5 + 0.5 * math.sin(self.t * 18)
            x, y = tg.x - ox, tg.y - oy
            w = tg.w * (0.6 + 0.4 * k)
            pygame.draw.ellipse(surf, tg.color, (x - w, y - 8, w * 2, 16), 2)
            pygame.draw.line(surf, tg.color, (x, y - 12), (x, y - 40 - 40 * pulse), 2)
            pygame.draw.polygon(surf, tg.color, [(x - 8, y - 34 - 40 * pulse), (x + 8, y - 34 - 40 * pulse),
                                                 (x, y - 46 - 40 * pulse)])
        for s in self.shots:
            surf.blit(s.img, (s.x - ox - s.r, s.y - oy - s.r))

    def blit(self, surf, img, x, y, anchor="midbottom"):
        if self.flash > 0:
            img = img.copy()
            img.fill((160, 160, 160, 0), special_flags=pygame.BLEND_RGB_ADD)
        r = img.get_rect(**{anchor: (x, y)})
        surf.blit(img, r)
        return r

    def draw(self, surf, ox, oy) -> None:
        self.draw_fx(surf, ox, oy)


_ORBS: dict = {}


# ----------------------------------------------------------------------------
class Wyrm(PlanetBoss):
    behind_ground = True
    base_hp = 55
    head_sprite = "generated/bosses/wyrm_head.png"
    seg_sprite = "generated/bosses/wyrm_segment.png"
    segments = 9
    leap_v = 1650
    spit_color = (240, 200, 120)

    def __init__(self, scene, x):
        super().__init__(scene, x)
        a = self.game.assets
        self.head = a.sprite(self.head_sprite)
        self.seg = a.sprite(self.seg_sprite)
        self.hx, self.hy = x, self.ground(x) + 260
        self.vx = self.vy = 0.0
        self.trail = deque(maxlen=self.segments * 6 + 2)
        self.target_x = x
        self.spat = False
        self.go("burrow", 2.0)

    def base_y(self, x):
        return self.ground(x)

    def update(self, dt):
        self._common(dt)
        p = self.pilot
        if self.state in ("intro", "burrow"):
            tx = self.clamp_arena(p.x)
            self.hx += max(-450, min(450, (tx - self.hx) * 2)) * dt
            self.hy = self.base_y(self.hx) + 280
            if random.random() < 0.5:
                gy = self.base_y(self.hx)
                self.scene.particles.emit(self.hx + random.uniform(-40, 40), gy - 2, random.uniform(-60, 60),
                                          -random.uniform(60, 160), 0.5, random.uniform(3, 6),
                                          self.scene.biome.ground_top, drag=2, gravity=500)
            if self.state_t <= 0:
                self.target_x = self.clamp_arena(p.x)
                self.telegraphs.append(Telegraph(self.target_x, self.base_y(self.target_x), 0.9, 140))
                self.go("telegraph", 0.9)
                self.game.audio.play("land", 0.8)
        elif self.state == "telegraph":
            self.hx += (self.target_x - self.hx) * min(1, dt * 6)
            self.game.shake(3)
            if self.state_t <= 0:
                self.hx = self.target_x
                self.hy = self.base_y(self.hx) + 90
                self.vy = -self.leap_v * (1.1 if self.enraged else 1.0)
                self.vx = (p.x - self.hx) * 0.4
                self.spat = False
                self.go("leap", 4.0)
                self.game.audio.play("explosion", 0.5)
                self.scene.particles.burst(self.hx, self.base_y(self.hx), 40, 320,
                                           [self.scene.biome.ground_top, self.scene.biome.ground], life=(0.4, 1.0),
                                           gravity=700)
        elif self.state == "leap":
            self.vy += 2100 * dt
            self.hx += self.vx * dt
            self.hy += self.vy * dt
            if self.vy > 0 and not self.spat and (self.enraged or self.spits_always):
                self.spat = True
                self._spit()
            if self.vy > 0 and self.hy > self.base_y(self.hx) + 190:
                self.go("burrow", random.uniform(1.4, 2.4) * (0.7 if self.enraged else 1.0))
                self.scene.particles.burst(self.hx, self.base_y(self.hx), 24, 240,
                                           [self.scene.biome.ground_top], life=(0.3, 0.8), gravity=700)
        self.trail.append((self.hx, self.hy))
        self.facing = 1 if self.vx >= 0 else -1

    spits_always = False

    def _spit(self):
        p = self.pilot
        n = 5 if self.enraged else 3
        for k in range(n):
            spread = (k - (n - 1) / 2) * 170
            self.lob(self.hx, self.hy, p.x + spread, self.ground(p.x + spread), time=1.0, color=self.spit_color)

    def _segments(self):
        out = []
        tr = list(self.trail)
        for i in range(1, self.segments + 1):
            idx = len(tr) - 1 - i * 5
            if idx < 0:
                break
            out.append(tr[idx])
        return out

    def hitboxes(self):
        hw, hh = self.head.get_width() * 0.4, self.head.get_height() * 0.4
        boxes = [pygame.Rect(self.hx - hw, self.hy - hh, hw * 2, hh * 2)]
        sw = self.seg.get_width() * 0.35
        for sx, sy in self._segments():
            if sy < self.base_y(sx) + 10:
                boxes.append(pygame.Rect(sx - sw, sy - sw, sw * 2, sw * 2))
        return [b for b in boxes if b.centery < self.base_y(b.centerx) + 20]

    def draw(self, surf, ox, oy):
        for sx, sy in reversed(self._segments()):
            self.blit(surf, self.seg, sx - ox, sy - oy, "center")
        if self.trail:
            ang = 0.0
            if len(self.trail) > 3:
                (x0, y0), (x1, y1) = self.trail[-4], self.trail[-1]
                ang = math.degrees(math.atan2(x1 - x0, -(y1 - y0))) if (x1, y1) != (x0, y0) else 0
            img = pygame.transform.rotate(self.head, -ang + 0)
            self.blit(surf, img, self.hx - ox, self.hy - oy, "center")

    def draw_over(self, surf, ox, oy):
        """Telegraphs and shots go above the ground layer."""
        self.draw_fx(surf, ox, oy)


class Leviathan(Wyrm):
    base_hp = 70
    head_sprite = "generated/bosses/leviathan.png"
    seg_sprite = "generated/bosses/leviathan_segment.png"
    segments = 11
    leap_v = 1800
    spit_color = (120, 220, 255)
    spits_always = True

    def __init__(self, scene, x):
        super().__init__(scene, x)
        self.head = self.game.assets.sprite(self.head_sprite)
        self.seg = self.game.assets.sprite(self.seg_sprite)

    def _spit(self):
        p = self.pilot
        n = 7 if self.enraged else 4
        base = math.atan2(p.y - 60 - self.hy, p.x - self.hx)
        for k in range(n):
            a = base + (k - (n - 1) / 2) * 0.22
            self.fire(self.hx, self.hy, math.cos(a) * 650, math.sin(a) * 650 - 170, r=20,
                      color=self.spit_color, grav=500)


# ----------------------------------------------------------------------------
class Golem(PlanetBoss):
    base_hp = 75
    contact = 22

    def __init__(self, scene, x):
        super().__init__(scene, x)
        self.img = self.game.assets.sprite("generated/bosses/golem.png")
        self.img_l = pygame.transform.flip(self.img, True, False)
        self.waves = []       # [x, dir, life]
        self.spikes = []      # [x, t]
        self.attack = 0
        self.go("walk", 2.0)

    def update(self, dt):
        self._common(dt)
        p = self.pilot
        self.facing = 1 if p.x > self.x else -1
        lift = 0.0
        if self.state in ("walk", "intro"):
            speed = 165 if self.enraged else 115
            if abs(p.x - self.x) > 240:
                self.x = self.clamp_arena(self.x + self.facing * speed * dt)
            if self.state_t <= 0 and self.state == "walk":
                self.attack = (self.attack + 1) % (3 if self.enraged else 2)
                if self.attack == 0:
                    self.go("windup", 0.8)
                    self.game.audio.play("alarm", 0.4)
                elif self.attack == 1:
                    self.go("throw", 0.6)
                else:
                    for dx in (-210, 0, 210):
                        x = p.x + dx
                        self.telegraphs.append(Telegraph(x, self.ground(x), 0.9, 75, (140, 220, 255)))
                        self.spikes.append([x, 0.9])
                    self.go("walk", 2.4)
            elif self.state == "intro" and self.state_t <= 0:
                self.go("walk", 1.5)
        elif self.state == "windup":
            lift = 1 - self.state_t / 0.8
            if self.state_t <= 0:
                self.game.shake(18)
                self.game.audio.play("explosion", 0.7)
                gy = self.ground(self.x)
                self.scene.particles.burst(self.x, gy, 40, 300, [(220, 240, 255), (150, 170, 200)],
                                           life=(0.4, 1.0), gravity=600)
                for d in (-1, 1):
                    self.waves.append([self.x + d * 90, d, 1.6])
                self.go("walk", 2.2 if not self.enraged else 1.6)
        elif self.state == "throw":
            if self.state_t <= 0:
                n = 2 if self.enraged else 1
                for k in range(n):
                    self.lob(self.x, self.ground(self.x) - self.img.get_height() * 0.85, p.x + k * 130 * self.facing,
                             self.ground(p.x), time=1.0 + 0.2 * k, r=30, color=(190, 230, 255), dmg=self.dmg * 1.2)
                self.go("walk", 2.0)
        self.lift = lift
        for w in self.waves:
            w[0] += w[1] * 780 * dt
            w[2] -= dt
            if abs(w[0] - p.x) < 50 and p.y > self.ground(p.x) - 45:
                p.hurt(self.dmg, w[1])
            if random.random() < 0.7:
                self.scene.particles.emit(w[0], self.ground(w[0]) - 4, 0, -random.uniform(80, 200), 0.4, 5,
                                          (200, 235, 255), drag=2)
        self.waves = [w for w in self.waves if w[2] > 0]
        for sp in self.spikes:
            sp[1] -= dt
            if -0.6 < sp[1] <= 0 and abs(sp[0] - p.x) < 60 and p.y > self.ground(sp[0]) - 180:
                p.hurt(self.dmg * 1.1, 1 if p.x > sp[0] else -1)
        self.spikes = [sp for sp in self.spikes if sp[1] > -0.7]

    def hitboxes(self):
        gy = self.ground(self.x)
        w, h = self.img.get_width() * 0.7, self.img.get_height() * 0.95
        return [pygame.Rect(self.x - w / 2, gy - h, w, h)]

    def draw(self, surf, ox, oy):
        gy = self.ground(self.x)
        bob = (int(math.sin(self.t * 4) * 2) * 2) if self.state == "walk" else -int(getattr(self, "lift", 0) * 20) * 2
        img = self.img if self.facing > 0 else self.img_l
        self.blit(surf, img, self.x - ox, gy - oy + 10 + bob)
        for x, _d, life in self.waves:
            h = 45 + 45 * life
            gx = self.ground(x) - oy
            pygame.draw.polygon(surf, (200, 235, 255), [(x - ox - 26, gx), (x - ox, gx - h), (x - ox + 26, gx)])
            pygame.draw.polygon(surf, (255, 255, 255), [(x - ox - 8, gx), (x - ox, gx - h * 0.7), (x - ox + 8, gx)])
        for x, t in self.spikes:
            if t <= 0:
                k = min(1.0, -t / 0.15)
                gx = self.ground(x) - oy
                for dx, h in ((-27, 105), (0, 165), (27, 120)):
                    hh = h * k
                    pygame.draw.polygon(surf, (150, 210, 255), [(x - ox + dx - 12, gx), (x - ox + dx, gx - hh),
                                                                (x - ox + dx + 12, gx)])
                    pygame.draw.line(surf, (240, 250, 255), (x - ox + dx - 4, gx - 4), (x - ox + dx, gx - hh), 2)
        self.draw_fx(surf, ox, oy)


# ----------------------------------------------------------------------------
class Titan(PlanetBoss):
    base_hp = 85
    contact = 20

    def __init__(self, scene, x):
        super().__init__(scene, x)
        self.img = self.game.assets.sprite("generated/bosses/titan.png")
        self.rise = 0.0
        self.columns = []     # [x, t]
        self.exposed = 0.0
        self.attack = 0
        self.sweep = None     # [dir, t]
        self.go("intro", 2.2)

    def update(self, dt):
        self._common(dt)
        p = self.pilot
        self.rise = min(1.0, self.rise + dt / 2.0)
        self.exposed = max(0.0, self.exposed - dt)
        self.hurt_mult = 2.0 if self.exposed > 0 else 0.45
        self.facing = 1 if p.x > self.x else -1
        if self.state == "intro":
            if random.random() < 0.6:
                self.scene.particles.emit(self.x + random.uniform(-100, 100), self.ground(self.x), 0,
                                          -random.uniform(100, 300), 0.8, 6, (255, 140, 50), glow=True)
            if self.state_t <= 0:
                self.go("idle", 1.2)
        elif self.state == "idle" and self.state_t <= 0:
            if abs(p.x - self.x) < 390:
                self.sweep = [self.facing, 0.7]
                self.telegraphs.append(Telegraph(self.x + self.facing * 240, self.ground(self.x), 0.7, 210))
                self.go("idle", 2.0)
            else:
                self.attack = (self.attack + 1) % 2
                if self.attack == 0:
                    n = 5 if self.enraged else 3
                    for k in range(n):
                        tx = p.x + (k - (n - 1) / 2) * 190
                        self.lob(self.x, self.ground(self.x) - self.img.get_height() * 0.8, tx, self.ground(tx),
                                 time=1.2, r=22, color=(255, 140, 50))
                    self.game.audio.play("enemy_laser", 0.6)
                    self.go("idle", 2.2)
                else:
                    n = 4 if self.enraged else 3
                    for k in range(n):
                        x = p.x + (k - (n - 1) / 2) * 250
                        self.telegraphs.append(Telegraph(x, self.ground(x), 1.0, 75))
                        self.columns.append([x, 1.0])
                    self.go("idle", 2.8)
        for c in self.columns:
            c[1] -= dt
            if -0.8 < c[1] <= 0:
                if c[1] + dt > 0:
                    self.game.shake(8)
                    self.game.audio.play("explosion", 0.35)
                if abs(c[0] - p.x) < 66:
                    p.hurt(self.dmg * 1.2, 1 if p.x > c[0] else -1)
        done = [c for c in self.columns if c[1] <= -0.8]
        if done and not [c for c in self.columns if c[1] > -0.8]:
            self.exposed = 2.6       # the eruptions vent its core
            self.game.toasts.add("CORE EXPOSED - strike now!", (255, 220, 120), 2)
        self.columns = [c for c in self.columns if c[1] > -0.8]
        if self.sweep:
            self.sweep[1] -= dt
            if -0.3 < self.sweep[1] <= 0:
                d = self.sweep[0]
                x0 = self.x + (0 if d > 0 else -480)
                zone = pygame.Rect(x0, self.ground(self.x) - 90, 480, 90)
                if zone.colliderect(p.rect):
                    p.hurt(self.dmg * 1.3, d)
            if self.sweep[1] <= -0.3:
                self.sweep = None

    def hitboxes(self):
        gy = self.ground(self.x)
        h = self.img.get_height() * 0.95 * self.rise
        w = self.img.get_width() * 0.75
        return [pygame.Rect(self.x - w / 2, gy - h, w, h)] if self.rise > 0.3 else []

    def draw(self, surf, ox, oy):
        gy = self.ground(self.x) - oy
        img = self.img
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        visible = int(img.get_height() * self.rise)
        if visible <= 2:
            return
        part = img.subsurface((0, 0, img.get_width(), visible))
        sway = math.sin(self.t * 1.3) * 4
        r = self.blit(surf, part, self.x - ox + sway, gy + 16)
        core = (r.centerx, r.top + visible * 0.62)
        if self.exposed > 0:
            g = glow(90, (255, 200, 90), 0.9)
            surf.blit(g, g.get_rect(center=core), special_flags=pygame.BLEND_ADD)
        if self.sweep and self.sweep[1] <= 0:
            d = self.sweep[0]
            x0 = self.x - ox + (0 if d > 0 else -480)
            surf.fill((255, 140, 50), (x0, gy - 90, 480, 90))
            surf.fill((255, 230, 150), (x0 + 16, gy - 66, 448, 36))
        for x, t in self.columns:
            if t <= 0:
                h = 620 * min(1.0, -t / 0.12)
                cx = x - ox
                surf.fill((255, 110, 30), (cx - 50, gy - h, 100, h))
                surf.fill((255, 220, 120), (cx - 20, gy - h, 40, h))
        self.draw_fx(surf, ox, oy)


# ----------------------------------------------------------------------------
class Queen(PlanetBoss):
    base_hp = 60
    contact = 16

    def __init__(self, scene, x):
        super().__init__(scene, x)
        self.img = self.game.assets.sprite("generated/bosses/queen.png")
        self.y = self.ground(x) - 480
        self.attack = 0
        self.dive_to = None
        self.drones = 0
        self.go("hover", 2.0)

    def update(self, dt):
        self._common(dt)
        p = self.pilot
        gy = self.ground(self.home)
        if self.state in ("hover", "intro"):
            tx = self.home + math.sin(self.t * 0.6) * 570
            ty = gy - 480 + math.sin(self.t * 1.7) * 60
            self.x += (tx - self.x) * min(1, dt * 2)
            self.y += (ty - self.y) * min(1, dt * 2)
            if self.state_t <= 0:
                self.attack = (self.attack + 1) % 3
                if self.attack == 0:
                    n = 12 if self.enraged else 8
                    off = random.uniform(0, math.tau)
                    for k in range(n):
                        a = off + k * math.tau / n
                        self.fire(self.x, self.y, math.cos(a) * 430, math.sin(a) * 430, r=18, color=(220, 160, 255))
                    self.game.audio.play("enemy_laser", 0.6)
                    self.go("hover", 2.0)
                elif self.attack == 1:
                    self._summon()
                    self.go("hover", 2.4)
                else:
                    self.dive_to = (p.x, self.ground(p.x) - self.img.get_height() * 0.45)
                    self.telegraphs.append(Telegraph(p.x, self.ground(p.x), 0.9, 120, (220, 160, 255)))
                    self.go("aim", 0.9)
        elif self.state == "aim":
            self.x += random.uniform(-3, 3)
            if self.state_t <= 0:
                self.go("dive", 1.0)
                self.game.audio.play("warp", 0.4)
        elif self.state == "dive":
            tx, ty = self.dive_to
            self.x += (tx - self.x) * min(1, dt * 7)
            self.y += (ty - self.y) * min(1, dt * 7)
            if abs(self.y - ty) < 12 or self.state_t <= 0:
                self.game.shake(16)
                self.game.audio.play("explosion", 0.6)
                self.scene.particles.burst(self.x, self.ground(self.x), 40, 300, [(220, 170, 255), (255, 255, 255)],
                                           life=(0.3, 0.9), gravity=500)
                self.go("stunned", 1.8)
        elif self.state == "stunned":
            self.hurt_mult = 1.8
            if self.state_t <= 0:
                self.hurt_mult = 1.0
                self.go("hover", 1.5)

    def _summon(self):
        from .creatures import Creature
        sc = self.scene
        alive = [c for c in sc.creatures.values() if c.id.startswith("queen")]
        for k in range(max(0, (4 if self.enraged else 3) - len(alive))):
            self.drones += 1
            uid = f"queen-drone-{self.drones}"
            c = Creature(self.game, uid, self.x + (k - 1) * 140, "flyer", sc.terrain.height, (255, 255, 255),
                         sc.danger * 0.6, sprites=("generated/bosses/drone.png", "generated/bosses/drone.png"))
            c.y = self.y
            sc.creatures[uid] = c
        self.game.audio.play("discover", 0.4)

    def hitboxes(self):
        w, h = self.img.get_width() * 0.7, self.img.get_height() * 0.8
        return [pygame.Rect(self.x - w / 2, self.y - h / 2, w, h)]

    def draw(self, surf, ox, oy):
        wob = math.sin(self.t * 14) * 2 if self.state != "stunned" else 0
        img = self.img
        if self.state == "stunned":
            img = pygame.transform.rotate(img, math.sin(self.t * 20) * 6)
        if self.state == "aim":
            tx, ty = self.dive_to
            pygame.draw.line(surf, (220, 160, 255), (self.x - ox, self.y - oy), (tx - ox, ty - oy), 2)
        self.blit(surf, img, self.x - ox, self.y - oy + wob, "center")
        if self.state == "stunned":
            for k in range(3):
                a = self.t * 4 + k * 2.1
                pygame.draw.circle(surf, (255, 240, 140), (self.x - ox + math.cos(a) * 50, self.y - oy - 80 +
                                                           math.sin(a) * 10), 5)
        self.draw_fx(surf, ox, oy)


BOSS_CLASSES = {"desert": Wyrm, "ocean": Leviathan, "ice": Golem, "volcanic": Titan, "crystal": Queen}


def make_boss(scene, x):
    cls = BOSS_CLASSES.get(scene.biome.id)
    return cls(scene, x) if cls else None
