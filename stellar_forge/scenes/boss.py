"""Final battle against the Warlord, in three phases:

1. The Swarm  - floating aliens rain orbs on you.
2. The Gun    - the Warlord hovers and fires patterns; swing your sword at
                his orbs to reflect them back (that's the only real damage).
3. The Duel   - he lands with a blade: dodge the telegraphed swings and
                strike during his recovery. Jump his shockwaves.
"""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from ..core.camera import SideCamera
from ..core.scene import Scene
from ..surface.player import Pilot
from ..systems.particles import ParticleSystem
from ..ui import hud
from ..ui.floaters import Floaters
from ..ui.text import bar, panel, text

CRITICAL = 3.0                       # seconds between the killing blow and the Warlord's final blast
FLOOR = config.SCREEN_H - 80        # the original arena: an 80 px metal floor along the bottom
LEFT, RIGHT = 50, config.SCREEN_W - 50


class _StillCamera(SideCamera):
    """The arena never moves and never shakes (as in the original fight)."""

    @property
    def ox(self) -> float:
        return 0.0

    @property
    def oy(self) -> float:
        return 0.0


def _energy_orb(color, r=19):
    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r, 0, -1):
        k = i / r
        a = int(255 * (1 - k) ** 0.6)
        c = tuple(min(255, int(v + (255 - v) * (1 - k) ** 2)) for v in color)
        pygame.draw.circle(surf, (*c, a), (r, r), i)
    return surf


class Orb:
    __slots__ = ("pos", "vel", "owner", "r", "alive", "img")

    def __init__(self, pos, vel, owner, r, img):
        self.pos, self.vel, self.owner, self.r, self.img = Vector2(pos), Vector2(vel), owner, r, img
        self.alive = True


class Minion:
    def __init__(self, scene, x, y):
        self.scene = scene
        self.pos = Vector2(x, y)
        self.base = Vector2(x, y)
        self.hp = 3
        self.alive = True
        self.t = random.uniform(0, 6)
        self.fire = random.uniform(1.0, 2.5)
        self.dive = 0.0
        self.flash = 0.0

    def update(self, dt, player: Pilot):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.dive > 0:
            self.dive -= dt
            d = Vector2(player.x, player.y - 40) - self.pos
            if d.length() > 1:
                self.pos += d.normalize() * 480 * dt
            if self.dive <= 0:
                self.base.x = self.pos.x
        else:
            self.base.x += math.sin(self.t * 0.7) * 60 * dt
            self.base.x = max(LEFT + 40, min(RIGHT - 40, self.base.x))
            target = Vector2(self.base.x + math.sin(self.t * 1.7) * 50, self.base.y + math.sin(self.t * 2.3) * 30)
            self.pos += (target - self.pos) * min(1.0, dt * 3)
            self.fire -= dt
            if self.fire <= 0:
                self.fire = random.uniform(1.6, 3.0)
                if random.random() < 0.25:
                    self.dive = 1.2
                else:
                    aim = Vector2(player.x, player.y - 40) - self.pos
                    if aim.length() > 1:
                        self.scene.orbs.append(Orb(self.pos, aim.normalize() * 330, "minion", 11, self.scene.img_orb_small))


class BossScene(Scene):
    music = "boss"
    on_foot = True     # gamepad: A jumps, X swings

    def __init__(self, game):
        super().__init__(game)
        a = game.assets
        self.camera = _StillCamera()
        self.camera.x = self.camera.y = 0
        st = game.state
        st.pilot_hp = st.max_pilot_hp
        self.pilot = Pilot(game, 200, lambda x: FLOOR, big=False)
        self.particles = ParticleSystem(700)
        self.floaters = Floaters()
        self.orbs: list[Orb] = []
        self.bolts: list[list] = []
        self.minions: list[Minion] = []
        self.phase = 0
        self.phase_t = 0.0
        self.clock = 0.0
        self.waves: list[list] = []      # shockwaves [x, dir, life, origin]
        self.impacts: list[list] = []    # landing flashes [x, age]
        self.cracks: list[list] = []     # floor cracks [x, age, seed]
        self.victory_t = -1.0
        self.dead_t = -1.0
        # boss
        self.boss_pos = Vector2(config.SCREEN_W / 2, 200)
        self.boss_hp = 0
        self.boss_max = 1
        self.boss_state = "idle"
        self.boss_t = 0.0
        self.boss_face = -1
        self.boss_flash = 0.0
        self.boss_vy = 0.0
        self.pattern_t = 2.0
        self.swing_hit = False

        # the original arena: background.png over the whole screen, two pillars, skulls and test tubes
        self.img_bg = pygame.transform.scale(a.image("boss_fight/background.png"), (config.SCREEN_W, config.SCREEN_H))
        self.img_pillar = pygame.transform.scale(a.image("boss_fight/pillar.png"), (120, 300))
        self.img_skull = pygame.transform.scale(a.image("boss_fight/skull.png"), (40, 40))
        self.img_tube = pygame.transform.scale(a.image("boss_fight/testtube.png"), (30, 50))
        self.img_alien = a.image("alien/alien.png", size=(80, 80))
        self.img_alien_l = a.image("alien/alien.png", size=(80, 80), flip_x=True)
        self.img_orb_small = a.image("alien/orb.png", size=(26, 26))
        self.img_orb_big = _energy_orb((255, 70, 60))
        self.img_orb_reflect = _energy_orb((90, 200, 255))
        self.img_gun = a.image("finalboss/bossGun.png", size=(200, 200))
        self.img_idle = a.image("finalboss/boss.png", size=(200, 200))
        self.img_windup = [a.image(f"finalboss/boss_sword/bossSword{i}.png", size=(200, 200)) for i in range(1, 5)]
        self.img_swing = [a.image(f"finalboss/boss_swing/bossSwordSwing{i}.png", size=(200, 200)) for i in range(1, 5)]
        rng = random.Random(4)
        self.pillars = [(100, FLOOR - 250), (config.SCREEN_W - 220, FLOOR - 250)]
        self.props = [(self.img_skull, (rng.randint(150, config.SCREEN_W - 150), FLOOR - 50)) for _ in range(4)] + \
                     [(self.img_tube, (rng.randint(150, config.SCREEN_W - 150), FLOOR - 60)) for _ in range(3)]
        self.start_phase(1)

    # ------------------------------------------------------------------
    def start_phase(self, n: int) -> None:
        self.phase = n
        self.phase_t = 0.0
        self.orbs = [o for o in self.orbs if o.owner == "reflect"]
        titles = {1: ("Phase I: The Swarm", "Cut down his minions"),
                  2: ("Phase II: The Warlord's Gun", "Swing your sword INTO his red orbs to reflect them!"),
                  3: ("Phase III: The Blade", "Dodge his telegraphed swings, strike while he recovers. Jump the shockwaves!")}
        self.game.banner.show(*titles[n], duration=4)
        self.game.audio.play("alarm", 0.6)
        ng = self.game.state.ng_plus if self.game.state else 0
        hp_k = 1 + 0.4 * ng          # New Game+: the Warlord returns, stronger every cycle
        if n == 1:
            count = 6 + 2 * min(ng, 3)
            self.minions = [Minion(self, 160 + (i % 8) * 140, 170 + (i % 2) * 90 + (i // 8) * 70)
                            for i in range(count)]
            line = "MY CHILDREN WILL PICK YOUR BONES CLEAN." if not ng else \
                "YOU BURNED ME ONCE, VOYAGER. THE FORGE REMEMBERS ME TOO."
            self.game.dialogue.say([("warlord", line)])
        elif n == 2:
            self.boss_hp = self.boss_max = round(7 * hp_k)
            self.boss_pos = Vector2(config.SCREEN_W / 2, -120)
            self.boss_state = "gun"
            self.game.dialogue.say([("warlord", "ENOUGH. I WILL DO THIS MYSELF.")])
        elif n == 3:
            self.boss_hp = self.boss_max = round(12 * hp_k)
            self.boss_state = "fall"
            self.boss_vy = 0
            self.minions = []
            self.game.dialogue.say([("warlord", "STEEL, THEN. LIKE THE OLD DAYS."),
                                    ("pilot", "Come on, then.")])

    def handle_event(self, e) -> None:
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            from .menus import PauseScene
            self.game.scenes.push(PauseScene(self.game, allow_save=False))
        elif e.key == pygame.K_h and self.dead_t < 0 and (self.victory_t < 0 or self.victory_t < CRITICAL):
            self.pilot.use_medkit(self.particles, self.floaters)

    # ------------------------------------------------------------------
    def update(self, dt) -> None:
        self.clock += dt
        self.phase_t += dt
        st = self.game.state
        p = self.pilot
        keys = self.game.input.pressed()
        winning = self.victory_t >= 0
        alive = self.dead_t < 0 and (not winning or self.victory_t < CRITICAL)   # you can run while he goes critical
        if winning:
            st.pilot_hp = max(st.pilot_hp, 1)                  # nothing kills you after the killing blow
        for x, y, vx, *_power in p.update(dt, keys, enabled=alive):
            self.bolts.append([x, y, vx, 1.2])
        p.x = max(LEFT, min(RIGHT, p.x))
        self.particles.update(dt)
        self.floaters.update(dt)
        self.boss_flash = max(0.0, self.boss_flash - dt)

        if not winning:                                        # once he's beaten, the fight stops
            for m in self.minions:
                m.update(dt, p)
            self._update_boss(dt)
            self._update_orbs(dt)
            self._update_bolts(dt)
            self._update_waves(dt)
            self._melee()

        if self.phase == 1 and not self.minions and self.phase_t > 1:
            self.start_phase(2)
        elif self.phase == 2 and self.boss_hp <= 0:
            self.particles.explosion(self.boss_pos.x, self.boss_pos.y, 2)
            self.game.audio.play("explosion")
            self.start_phase(3)
        elif self.phase == 3 and self.boss_hp <= 0 and self.victory_t < 0:
            self.victory_t = 0.0
            self.orbs.clear()
            self.waves.clear()
            self.minions.clear()
            self.blasted = False
            self.game.audio.play("alarm", 0.8)
            self.game.dialogue.say([("warlord", "IMPOSSIBLE... THE FORGE... WAS MINE..."),
                                    ("ai", "He's going critical - get clear, Voyager!")])

        if self.victory_t >= 0:
            self.victory_t += dt
            if self.victory_t < CRITICAL and random.random() < dt * 5:      # cracking apart, small pops
                self.particles.burst(self.boss_pos.x + random.uniform(-70, 70), self.boss_pos.y + random.uniform(-80, 40),
                                     10, 160, [(255, 210, 120), (255, 120, 60)], life=(0.2, 0.5))
            if self.victory_t >= CRITICAL and not self.blasted:              # ...then the big one
                self.blasted = True
                for i in range(7):
                    self.particles.explosion(self.boss_pos.x + random.uniform(-80, 80),
                                             self.boss_pos.y + random.uniform(-90, 40), 2.4)
                self.game.audio.play("explosion")
                d = p.x - self.boss_pos.x
                if abs(d) < 240:                                             # too close: thrown back, never killed
                    p.vx = (1 if d >= 0 else -1) * 700
                    p.vy = -500
                    st.pilot_hp = max(1, st.pilot_hp - 20)
            if self.victory_t > CRITICAL + 6 or (self.victory_t > CRITICAL + 2 and keys[pygame.K_RETURN]
                                                   and not self.game.dialogue.active):
                self.victory_t = -99
                st.earn(2000 * (1 + st.ng_plus))
                self.game.return_to_space_after_boss()
        if st.pilot_hp <= 0 and self.dead_t < 0 and self.victory_t < 0:
            self.dead_t = 0.0
            self.particles.explosion(p.x, p.y - 40, 1.3)
            self.game.audio.play("explosion")
        if self.dead_t >= 0:
            self.dead_t += dt
            if self.dead_t > 1.6:
                self.game.game_over("The Warlord prevails... for now.")

    def _update_boss(self, dt) -> None:
        p = self.pilot
        if self.phase == 2:
            target_y = 190
            self.boss_pos.y += (target_y - self.boss_pos.y) * min(1, dt * 2)
            self.boss_pos.x = config.SCREEN_W / 2 + math.sin(self.clock * 0.6) * 380
            self.boss_face = 1 if p.x > self.boss_pos.x else -1
            self.pattern_t -= dt
            enraged = self.boss_hp <= 3
            if self.pattern_t <= 0:
                self.pattern_t = 1.5 if enraged else 2.1
                self._fire_pattern(enraged)
            if self.phase_t > 4 and len(self.minions) < 2 and random.random() < dt * 0.25:
                self.minions.append(Minion(self, random.choice([150, config.SCREEN_W - 150]), 150))
        elif self.phase == 3:
            self._duel(dt)

    def _fire_pattern(self, enraged: bool) -> None:
        origin = self.boss_pos + Vector2(self.boss_face * 70, 30)
        aim = Vector2(self.pilot.x, self.pilot.y - 40) - origin
        aim = aim.normalize() if aim.length() > 1 else Vector2(0, 1)
        choice = random.choice(["aimed", "aimed", "fan", "ring"] + (["rain"] if enraged else []))
        speed = 300 if not enraged else 360
        if choice == "aimed":
            for i in range(3 if enraged else 2):
                self.orbs.append(Orb(origin + aim * i * 40, aim * speed, "boss", 16, self.img_orb_big))
        elif choice == "fan":
            for a in (-24, -12, 0, 12, 24):
                self.orbs.append(Orb(origin, aim.rotate(a) * speed * 0.9, "boss", 16, self.img_orb_big))
        elif choice == "ring":
            for a in range(0, 360, 30):
                d = Vector2(1, 0).rotate(a + self.clock * 40)
                self.orbs.append(Orb(origin, d * speed * 0.7, "boss", 16, self.img_orb_big))
        else:
            for i in range(8):
                x = random.uniform(LEFT, RIGHT)
                self.orbs.append(Orb((x, -20 - i * 60), (0, speed), "boss", 16, self.img_orb_big))
        self.game.audio.play("enemy_laser", 0.6)

    def _duel(self, dt) -> None:
        p = self.pilot
        enraged = self.boss_hp <= self.boss_max * 0.4
        speed_mult = 1.35 if enraged else 1.0
        ground_y = FLOOR - 90
        self.boss_t += dt
        s = self.boss_state
        if s == "fall":
            self.boss_vy += 1600 * dt
            self.boss_pos.y += self.boss_vy * dt
            if self.boss_pos.y >= ground_y:
                self.boss_pos.y = ground_y
                self._land_impact()
                self._set("walk")
        elif s == "walk":
            self.boss_face = 1 if p.x > self.boss_pos.x else -1
            self.boss_pos.x += self.boss_face * 150 * speed_mult * dt
            dist = abs(p.x - self.boss_pos.x)
            if dist < 170:
                self._set("windup")
            elif self.boss_t > (2.2 if enraged else 3.2):
                self._set("leap")
                self.boss_vy = -900
                self._leap_vx = (p.x - self.boss_pos.x) / 1.1
        elif s == "windup":
            if self.boss_t > 0.6 / speed_mult:
                self._set("swing")
                self.swing_hit = False
                self.game.audio.play("swing")
        elif s == "swing":
            reach = pygame.Rect(0, 0, 220, 170)
            if self.boss_face > 0:
                reach.midleft = (self.boss_pos.x, self.boss_pos.y + 10)
            else:
                reach.midright = (self.boss_pos.x, self.boss_pos.y + 10)
            if not self.swing_hit and reach.colliderect(p.rect):
                self.swing_hit = True
                p.hurt(22, self.boss_face)
            if self.boss_t > 0.35:
                self._set("recover")
        elif s == "recover":
            if self.boss_t > (0.7 if enraged else 1.0):
                self._set("walk")
        elif s == "leap":
            self.boss_vy += 1600 * dt
            self.boss_pos.y += self.boss_vy * dt
            self.boss_pos.x += self._leap_vx * dt
            self.boss_pos.x = max(LEFT + 60, min(RIGHT - 60, self.boss_pos.x))
            if self.boss_pos.y >= ground_y and self.boss_vy > 0:
                self.boss_pos.y = ground_y
                self._land_impact()
                self._set("recover")
        if s in ("walk", "windup", "recover"):
            self.boss_pos.x = max(LEFT + 60, min(RIGHT - 60, self.boss_pos.x))
        # body contact
        body = pygame.Rect(0, 0, 110, 150)
        body.center = self.boss_pos
        if body.colliderect(p.rect) and s not in ("recover",):
            p.hurt(10, 1 if p.x > self.boss_pos.x else -1)

    def hitbox(self) -> pygame.Rect:
        """Where the player's sword, bolts and reflected orbs count as a hit: the Warlord's whole body
        (his sprite is 200x200), not just its middle."""
        r = pygame.Rect(0, 0, 300, 280) if self.phase == 2 else pygame.Rect(0, 0, 190, 200)   # flying: bigger
        r.center = (int(self.boss_pos.x), int(self.boss_pos.y))
        return r

    def _set(self, s: str) -> None:
        self.boss_state = s
        self.boss_t = 0.0

    def _land_impact(self) -> None:
        self.game.audio.play("land")
        x = self.boss_pos.x
        self.particles.burst(x, FLOOR - 4, 34, 300, [(150, 130, 120), (110, 100, 100), (70, 64, 70)],
                             life=(0.5, 1.2), gravity=520, size=(3, 7))                     # dust cloud
        self.particles.burst(x, FLOOR - 10, 18, 420, [(255, 220, 140), (255, 150, 60)], life=(0.2, 0.6),
                             gravity=700)                                                     # sparks
        self.impacts.append([x, 0.0])
        self.cracks.append([x, 0.0, random.Random(int(x)).random()])
        for d in (-1, 1):
            self.waves.append([x, d, 2.2, x])                # [x, dir, life, origin]

    def _update_waves(self, dt) -> None:
        p = self.pilot
        for w in self.waves:
            w[0] += w[1] * 430 * dt
            w[2] -= dt
            if abs(w[0] - p.x) < 30 and p.y > FLOOR - 34:
                p.hurt(14, w[1])
            if random.random() < 0.8:                        # embers off the crest, dust kicked up behind
                self.particles.emit(w[0], FLOOR - random.uniform(10, 40), -w[1] * random.uniform(20, 90),
                                    -random.uniform(80, 220), random.uniform(0.3, 0.7), random.uniform(2, 4),
                                    random.choice([(255, 210, 120), (255, 150, 60), (255, 240, 200)]), glow=True,
                                    gravity=420)
            if random.random() < 0.5:
                self.particles.emit(w[0] - w[1] * 26, FLOOR - 6, -w[1] * random.uniform(10, 50),
                                    -random.uniform(20, 70), random.uniform(0.4, 0.9), random.uniform(3, 6),
                                    (96, 90, 96), drag=2)
        self.waves = [w for w in self.waves if w[2] > 0 and LEFT - 40 < w[0] < RIGHT + 40]
        for im in self.impacts:
            im[1] += dt
        self.impacts = [im for im in self.impacts if im[1] < 0.6]
        for c in self.cracks:
            c[1] += dt
        self.cracks = [c for c in self.cracks if c[1] < 3.0]

    def _update_orbs(self, dt) -> None:
        p = self.pilot
        pr = p.rect
        sword = p.sword_rect()
        for o in self.orbs:
            o.pos += o.vel * dt
            if o.owner == "reflect":
                to = self.boss_pos - o.pos                     # reflected orbs home in on the Warlord
                if to.length() > 1:
                    o.vel = o.vel.lerp(to.normalize() * 700, min(1.0, dt * 6))
                if self.phase == 2 and self.hitbox().inflate(40, 40).collidepoint(o.pos):
                    o.alive = False
                    self._damage_boss(1)
                continue
            if sword and o.owner == "boss" and sword.collidepoint(o.pos):
                to = (self.boss_pos - o.pos)
                o.vel = to.normalize() * 650 if to.length() > 1 else Vector2(0, -650)
                o.owner = "reflect"
                o.img = self.img_orb_reflect
                self.game.audio.play("hit", 0.8)
                self.particles.burst(o.pos.x, o.pos.y, 12, 200, [(140, 220, 255), (255, 255, 255)])
                continue
            if sword and o.owner == "minion" and sword.collidepoint(o.pos):
                o.alive = False
                continue
            if pr.collidepoint(o.pos):
                o.alive = False
                p.hurt(12 if o.owner == "boss" else 8, 1 if o.vel.x > 0 else -1)
            if o.pos.y > FLOOR + 10:
                o.alive = False
                self.particles.burst(o.pos.x, FLOOR, 6, 100, [(255, 140, 140)], life=(0.2, 0.4))
        self.orbs = [o for o in self.orbs if o.alive and -200 < o.pos.x < config.SCREEN_W + 200 and o.pos.y > -800]

    def _update_bolts(self, dt) -> None:
        for b in self.bolts:
            b[0] += b[2] * dt
            b[3] -= dt
            for m in self.minions:
                if m.pos.distance_to((b[0], b[1])) < 40:
                    b[3] = 0
                    self._hurt_minion(m, 1)
                    break
            else:
                if self.phase >= 2 and self.hitbox().collidepoint(b[0], b[1]):
                    b[3] = 0
                    vulnerable = self.phase == 3 and self.boss_state == "recover"
                    self._damage_boss(0.5 if vulnerable else 0.25 if self.phase == 2 else 0.15)
        self.bolts = [b for b in self.bolts if b[3] > 0 and LEFT - 50 < b[0] < RIGHT + 50]
        self.minions = [m for m in self.minions if m.alive]

    def _melee(self) -> None:
        p = self.pilot
        sword = p.sword_rect()
        if not sword:
            return
        for m in self.minions:
            if id(m) not in p.swing_hit and sword.collidepoint(m.pos):
                p.swing_hit.add(id(m))
                self._hurt_minion(m, 2)
        if self.phase == 3 and "boss" not in p.swing_hit:
            if sword.colliderect(self.hitbox()):
                p.swing_hit.add("boss")
                if self.boss_state == "recover":
                    self._damage_boss(1)
                else:
                    self.particles.burst(sword.centerx, sword.centery, 8, 150, [(255, 255, 200)], life=(0.1, 0.3))
                    self.game.audio.play("deny", 0.5)

    def _hurt_minion(self, m: Minion, dmg) -> None:
        m.hp -= dmg
        m.flash = 0.15
        self.game.audio.play("hit", 0.5)
        if m.hp <= 0:
            m.alive = False
            self.particles.explosion(m.pos.x, m.pos.y, 0.8)
            self.game.audio.play("explosion", 0.5)

    def _damage_boss(self, dmg) -> None:
        self.boss_hp = max(0.0, self.boss_hp - dmg)
        self.boss_flash = 0.15
        self.particles.burst(self.boss_pos.x, self.boss_pos.y, 14, 220, [(255, 120, 120), (255, 255, 255)])
        self.game.audio.play("hit")

    # ------------------------------------------------------------------
    def draw(self, surf) -> None:
        ox = self.camera.ox
        oy = self.camera.oy
        # --- the original arena ---
        surf.blit(self.img_bg, (0, 0))
        pygame.draw.rect(surf, (30, 30, 35), (0, FLOOR, config.SCREEN_W, config.SCREEN_H - FLOOR))   # dark metal
        for x in range(0, config.SCREEN_W, 100):
            pygame.draw.line(surf, (60, 60, 70), (x, FLOOR), (x, config.SCREEN_H), 2)
        for x, y in self.pillars:
            surf.blit(self.img_pillar, (x, y))
        for img, pos in self.props:
            surf.blit(img, pos)
        self._draw_impact_fx(surf)
        # boss
        if self.phase >= 2 and self.victory_t < CRITICAL:
            img = self._boss_img()
            if self.boss_face > 0:
                img = pygame.transform.flip(img, True, False)
            critical = self.victory_t >= 0 and int(self.clock * (6 + self.victory_t * 6)) % 2   # flashing faster
            if self.boss_flash > 0 or critical or (self.boss_state == "windup" and int(self.clock * 16) % 2):
                img = img.copy()
                img.fill((150, 60, 60, 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(img, img.get_rect(center=(self.boss_pos.x - ox, self.boss_pos.y - oy)))
            if self.boss_state == "recover" and self.victory_t < 0:
                text(surf, "OPEN!", (self.boss_pos.x - ox, self.boss_pos.y - 120 - oy), 16, (255, 255, 120),
                     bold=True, anchor="center")
        for m in self.minions:
            img = self.img_alien if self.pilot.x > m.pos.x else self.img_alien_l
            if m.flash > 0:
                img = img.copy()
                img.fill((200, 200, 200, 0), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(img, img.get_rect(center=(m.pos.x - ox, m.pos.y - oy)))
        if self.dead_t < 0:
            self.pilot.draw(surf, ox, oy)
        for o in self.orbs:
            surf.blit(o.img, o.img.get_rect(center=(o.pos.x - ox, o.pos.y - oy)))
        for bx, by, vx, _ in self.bolts:
            pygame.draw.line(surf, (140, 230, 255), (bx - ox, by - oy), (bx - vx * 0.02 - ox, by - oy), 4)
        self.particles.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        self.floaters.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))

        hud.pilot_status(surf, self.game, self.pilot.jet / max(0.01, self.game.state.jetpack_capacity))
        if self.phase >= 2 and self.victory_t < 0:
            w = 520
            panel(surf, ((config.SCREEN_W - w) // 2 - 10, 14, w + 20, 44), border=(255, 90, 90))
            text(surf, "THE WARLORD", (config.SCREEN_W // 2, 20), 14, (255, 140, 140), bold=True, anchor="midtop")
            bar(surf, ((config.SCREEN_W - w) // 2, 36, w, 16), self.boss_hp / self.boss_max, (220, 50, 60))
        elif self.phase == 1:
            text(surf, f"Minions: {len(self.minions)}", (config.SCREEN_W // 2, 24), 20, (255, 200, 200),
                 bold=True, anchor="midtop")
        if 0 <= self.victory_t < CRITICAL:                     # the countdown: get clear!
            left = CRITICAL - self.victory_t
            if int(self.clock * 4) % 2 == 0:
                text(surf, "HE'S GOING CRITICAL - GET CLEAR!", (config.SCREEN_W // 2, 150), 26, (255, 150, 90),
                     bold=True, anchor="center", outline=True)
            text(surf, f"{left:.1f}", (config.SCREEN_W // 2, 192), 26, (255, 230, 150), bold=True, anchor="center",
                 outline=True)
        elif self.victory_t >= CRITICAL:
            k = min(1, (self.victory_t - CRITICAL) / 1.5)
            text(surf, "VICTORY", (config.SCREEN_W // 2, 260), 64, tuple(int(c * k) for c in (255, 230, 150)),
                 bold=True, anchor="center")
            if self.victory_t > CRITICAL + 2:
                text(surf, "+2000 credits  ·  press Enter", (config.SCREEN_W // 2, 320), 18, (220, 220, 255),
                     anchor="center")
        text(surf, "A/D move  W jump/jetpack  SPACE sword (reflects orbs!)  F blaster  H heal",
             (config.SCREEN_W // 2, config.SCREEN_H - 6), 12, (160, 150, 190), anchor="midbottom")

    def _draw_impact_fx(self, surf) -> None:
        """The Warlord's landing: floor cracks, a ground flash, and two waves of fire racing outwards."""
        P = 4                                                   # chunky pixel size, like the art
        for x0, age, seed in self.cracks:                       # cracks in the metal floor, glowing then cooling
            k = max(0.0, 1 - age / 3.0)
            hot = (int(255 * k + 40 * (1 - k)), int(150 * k + 36 * (1 - k)), int(60 * k + 40 * (1 - k)))
            rng = random.Random(int(seed * 1e6))
            for d in (-1, 1):
                x, y = x0, FLOOR
                for _ in range(7):
                    x += d * rng.randint(2, 5) * P
                    y += rng.choice((0, P, P))
                    surf.fill(hot, (int(x) // P * P, int(y) // P * P, P * 2, P))
        for x0, age in self.impacts:                            # a flat flash spreading along the ground
            k = age / 0.6
            w = int(60 + 380 * k) // P * P
            a = int(200 * (1 - k))
            glow = pygame.Surface((w, 24), pygame.SRCALPHA)
            for i, (h, col) in enumerate(((24, (255, 140, 60)), (14, (255, 200, 120)), (6, (255, 245, 210)))):
                glow.fill((*col, a // (3 - i)), (0, 24 - h, w, h))
            surf.blit(glow, (int(x0 - w / 2), FLOOR - 24))
        for x, d, life, origin in self.waves:
            fade = min(1.0, life / 0.6)
            trail = int(abs(x - origin))                        # a burnt glowing streak behind the wave
            if trail > 0:
                streak = pygame.Surface((trail, P * 3), pygame.SRCALPHA)
                for i in range(0, trail, P):
                    t = i / max(1, trail)                       # 0 at the origin, 1 at the wave
                    xi = i if d > 0 else trail - i - P
                    streak.fill((255, int(110 + 100 * t), 60, int(210 * t * fade)), (xi, P, P, P * 2))
                    streak.fill((255, 230, 170, int(150 * t * t * fade)), (xi, P * 2, P, P))
                surf.blit(streak, (min(origin, x), FLOOR - P * 3))
            size = 0.65 + 0.35 * fade
            haze = pygame.Surface((P * 20, P * 28), pygame.SRCALPHA)    # heat haze: a soft stepped dome
            for row in range(28):
                half = int(10 * (1 - (1 - row / 27) ** 2) ** 0.5 + 0.5)   # wider towards the floor
                haze.fill((255, 150, 70, int((18 + row * 1.6) * fade)), ((10 - half) * P, row * P, half * 2 * P, P))
            surf.blit(haze, haze.get_rect(midbottom=(int(x - d * P * 4), FLOOR)))
            # the crest: stepped pixel columns curling forward, white-hot at the front, embers trailing back
            cols = [(88, (255, 252, 236)), (80, (255, 236, 170)), (72, (255, 210, 120)), (62, (255, 180, 80)),
                    (52, (255, 150, 60)), (42, (240, 118, 52)), (33, (215, 92, 50)), (25, (185, 72, 48)),
                    (18, (150, 58, 46)), (12, (118, 46, 44)), (7, (90, 40, 42))]
            for i, (h, col) in enumerate(cols):
                h = int(h * size) // P * P
                cx = int(x - d * i * P) // P * P
                surf.fill(col, (cx, FLOOR - h, P, h))
                if i < 4:                                       # the top curls over in the direction of travel
                    surf.fill(col, (cx + d * P * (2 - i // 2), FLOOR - h - P, P * (2 - i // 2), P))
            tip = FLOOR - int(96 * size) // P * P
            surf.fill((255, 255, 255), (int(x) // P * P + d * P * 2, tip, P, P))          # sparks riding the tip
            surf.fill((255, 240, 200), (int(x) // P * P + d * P * 3, tip + P * 3, P, P))

    def _boss_img(self):
        if self.phase == 2:
            return self.img_gun
        s = self.boss_state
        if s == "windup":
            return self.img_windup[min(3, int(self.boss_t / 0.15))]
        if s == "swing":
            return self.img_swing[min(3, int(self.boss_t / 0.09))]
        return self.img_idle
