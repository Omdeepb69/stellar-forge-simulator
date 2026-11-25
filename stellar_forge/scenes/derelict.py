"""Boarding a derelict: a short side-on level inside a dead ship.

Failing artificial gravity, dark corridors lit by emergency lamps, hull
breaches crackling with arcs, security drones that never got the memo,
supply crates to smash, crew terminals holding logs, and the captain's
vault at the far end.
"""
from __future__ import annotations

import math
import random

import pygame

from .. import config
from ..core.camera import SideCamera
from ..core.scene import Scene
from ..surface.creatures import Creature
from ..surface.player import Pilot
from ..systems import lore
from ..systems.items import roll_mod
from ..systems.particles import ParticleSystem
from ..ui import hud
from ..ui.floaters import Floaters
from ..ui.lighting import Lighting
from ..world.rng import rng_of

METAL, METAL_DARK, METAL_LIGHT = (72, 78, 94), (36, 40, 52), (120, 128, 146)


class Layout:
    """Piecewise corridors: flat decks with steps and the odd hull breach."""

    def __init__(self, seed: int):
        rng = rng_of(seed, "derelict-layout")
        self.segs = [(-640.0, 640.0, 0.0, False)]   # (x0, x1, floor_y, breach)
        x, y = 640.0, 0.0
        self.length = rng.uniform(5200, 7600)
        while x < self.length:
            if rng.random() < 0.18 and x > 900:
                w = rng.uniform(190, 280)
                self.segs.append((x, x + w, y + 420, True))
                x += w
                continue
            w = rng.uniform(480, 900)
            y += rng.choice([-144, -96, 0, 0, 0, 96, 144])
            y = max(-480, min(480, y))
            self.segs.append((x, x + w, y, False))
            x += w
        self.segs.append((x, x + 600, y, False))
        self.end = x + 300
        self.heights = {}
        crng = random.Random(seed + 5)
        self.ceil_off = [crng.uniform(450, 560) for _ in self.segs]

    def seg_at(self, x):
        for i, s in enumerate(self.segs):
            if s[0] <= x < s[1]:
                return i, s
        return (0, self.segs[0]) if x < self.segs[0][0] else (len(self.segs) - 1, self.segs[-1])

    def floor(self, x):
        return self.seg_at(x)[1][2]

    def ceiling(self, x):
        i, s = self.seg_at(x)
        base = s[2] if not s[3] else s[2] - 420
        return base - self.ceil_off[i]

    def breach(self, x):
        return self.seg_at(x)[1][3]


class DerelictScene(Scene):
    menu = False
    on_foot = True

    def __init__(self, game, derelict):
        super().__init__(game)
        self.derelict = derelict
        self.layout = Layout(derelict.seed)
        st = game.state
        self.looted = derelict.id in st.derelicts_looted
        self.pilot = Pilot(game, 0, self.layout.floor, 0.75, 1.0, None)
        self.pilot.ceiling = self.layout.ceiling
        self.pilot.anchor_fn = self.raycast
        self.pilot.x = -300
        self.pilot.y = self.layout.floor(-300)
        self.camera = SideCamera()
        self.camera.follow(self.pilot.x, self.pilot.y, 0, snap=True)
        self.particles = ParticleSystem(500)
        self.floaters = Floaters()
        self.lighting = Lighting()
        self.clock = 0.0
        self.bolts = []
        self.dead_t = -1.0
        self.prompt = None
        sx, sy = (int(v) for v in derelict.id.split(":")[0].split(","))
        self.danger = game.universe.danger_at(sx, sy) + 0.5
        rng = rng_of(derelict.seed, "contents")
        a = game.assets
        self.crate_img = a.sprite("generated/interiors/crate.png")
        self.vault_img = a.sprite("generated/interiors/crate.png", mult=2, tint=(255, 220, 150))
        self.term_img = a.sprite("generated/interiors/terminal.png")
        self.airlock_img = a.sprite("generated/interiors/airlock.png")
        # contents
        self.crates = []   # [x, hp, id]
        self.terminals = []
        x = 1000.0
        i = 0
        while x < self.layout.end - 500:
            if not self.layout.breach(x):
                if rng.random() < 0.55:
                    self.crates.append([x, 3.0, f"{derelict.id}:c{i}"])
                elif rng.random() < 0.3:
                    self.terminals.append([x, f"{derelict.id}:t{i}"])
            x += rng.uniform(560, 900)
            i += 1
        if not self.terminals:
            self.terminals.append([1200.0 if not self.layout.breach(1200) else 600.0, f"{derelict.id}:t0"])
        self.vault_x = self.layout.end - 150
        self.creatures: dict[str, Creature] = {}
        drone_n = 3 + int(self.danger)
        for k in range(min(8, drone_n)):
            dx = rng.uniform(900, self.layout.end - 400)
            uid = f"drone{k}"
            if not self.looted:
                c = Creature(game, uid, dx, "flyer", self.layout.floor, (255, 255, 255), self.danger,
                             sprites=("generated/interiors/drone.png", "generated/interiors/drone.png"))
                c.shoot_t = rng.uniform(1.5, 3.5)
                self.creatures[uid] = c
        self.enemy_bolts = []   # [x, y, vx, vy, life]
        self.used = set()

    @property
    def music(self) -> str:
        return "stronghold"

    def on_enter(self) -> None:
        self.game.banner.show(self.derelict.name, "Gravity failing. Air thin. Something is still awake.", 3.0)
        self.game.hint("derelict", "We're inside. Smash crates with your sword, read terminals with [E], and find "
                                   "the captain's vault at the far end. The airlock behind us is the way out.")

    def save_location(self) -> None:
        self.game.state.location = {"kind": "space", "near": self.derelict.id}

    def raycast(self, x, y, dx, dy, max_d):
        d = 30.0
        while d < max_d:
            px, py = x + dx * d, y + dy * d
            if py >= self.layout.floor(px) - 2:
                return px, self.layout.floor(px)
            if py <= self.layout.ceiling(px) + 2:
                return px, self.layout.ceiling(px)
            d += 14
        return None

    # ------------------------------------------------------------------
    def handle_event(self, e) -> None:
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            from .menus import PauseScene
            self.game.scenes.push(PauseScene(self.game))
        elif e.key == pygame.K_b:
            from .logbook import LogbookScene
            self.game.scenes.push(LogbookScene(self.game))
        elif e.key == pygame.K_e and self.dead_t < 0:
            self.interact()
        elif e.key == pygame.K_h and self.dead_t < 0:
            self.pilot.use_medkit(self.particles, self.floaters)

    def interact(self) -> None:
        p = self.pilot
        st = self.game.state
        if p.x < -200:
            self.game.audio.play("land", 0.5)
            self.game.scenes.pop(fade=True)
            return
        for tx, tid in self.terminals:
            if abs(p.x - tx) < 90 and tid not in self.used:
                self.used.add(tid)
                lid = lore.next_log(st, "crew")
                if lid:
                    lore.announce(self.game, lid)
                    _pool, title, body = lore.LOGS[lid]
                    self.game.dialogue.say([("ai", f"{title}: {body}")])
                else:
                    st.scan_data += 5
                    self.game.toasts.add("Terminal: nav data recovered (+5 data)", (140, 255, 200))
                return
        if abs(p.x - self.vault_x) < 120 and not self.looted:
            self._open_vault()

    def _open_vault(self) -> None:
        st = self.game.state
        self.looted = True
        st.mark("derelicts_looted", self.derelict.id)
        st.bump("derelicts")
        rng = random.Random(self.derelict.seed)
        mod = roll_mod(rng, min_rarity=1, luck=0.1)
        st.mods.append(mod)
        cr = int(320 * self.danger)
        st.earn(cr)
        n = rng.randint(4, 10)
        st.ore += n
        x, y = self.vault_x, self.layout.floor(self.vault_x)
        self.particles.burst(x, y - 40, 60, 300, [(255, 230, 140), (255, 255, 255), (140, 230, 255)],
                             life=(0.5, 1.3), gravity=400)
        self.game.audio.play("relic", 0.8)
        self.game.banner.show("Captain's vault", f"{mod['name']} ({mod['rarity']})  ·  +{cr} cr" +
                              f"  ·  +{n} ore", 4.0)
        self.game.save()

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.clock += dt
        st = self.game.state
        p = self.pilot
        alive = self.dead_t < 0
        keys = self.game.input.pressed()
        for x, y, vx, power in p.update(dt, keys, enabled=alive):
            self.bolts.append([x, y, vx, 0.9, power, set()])
        p.x = max(-580.0, min(self.layout.end + 300, p.x))
        self.camera.follow(p.x, p.y, dt)
        self.particles.update(dt)
        self.floaters.update(dt)
        if self.layout.breach(p.x) and p.y > self.layout.floor(p.x) - 90:
            p.hazard(30, dt)
            if random.random() < 0.5:
                self.particles.emit(p.x + random.uniform(-30, 30), p.y - 10, random.uniform(-80, 80),
                                    -random.uniform(80, 200), 0.3, 3, (140, 220, 255), glow=True)
        # sparks from breaches
        for x0, x1, fy, br in self.layout.segs:
            if br and abs((x0 + x1) / 2 - p.x) < 900 and random.random() < dt * 8:
                x = random.uniform(x0, x1)
                self.particles.emit(x, fy - 10, random.uniform(-60, 60), -random.uniform(150, 300), 0.4, 3,
                                    (170, 230, 255), glow=True, gravity=600)
        # combat
        sword = p.sword_rect()
        for c in list(self.creatures.values()):
            c.update(dt, p.x, p.y)
            c.y = max(c.y, self.layout.ceiling(c.x) + 40)
            if abs(c.x - p.x) < 700:
                c.shoot_t -= dt
                if c.shoot_t <= 0:
                    c.shoot_t = random.uniform(2.0, 3.2)
                    dx, dy = p.x - c.x, (p.y - 45) - (c.y - 20)
                    d = math.hypot(dx, dy) or 1
                    self.enemy_bolts.append([c.x, c.y - 20, dx / d * 420, dy / d * 420, 2.5])
                    self.game.audio.play("enemy_laser", 0.3)
            if alive and c.rect.colliderect(p.rect):
                p.hurt(c.damage, 1 if p.x > c.x else -1)
            if sword and c.id not in p.swing_hit and sword.colliderect(c.rect):
                p.swing_hit.add(c.id)
                self._hurt_drone(c, p.melee_damage, p.facing)
        for b in self.bolts:
            b[0] += b[2] * dt
            b[3] -= dt
            if b[1] > self.layout.floor(b[0]) or b[1] < self.layout.ceiling(b[0]):
                b[3] = 0
            for c in self.creatures.values():
                if c.id not in b[5] and c.rect.collidepoint(b[0], b[1]):
                    b[5].add(c.id)
                    if b[4] < 2:
                        b[3] = 0
                    self._hurt_drone(c, b[4] * st.weapon_mult, 1 if b[2] > 0 else -1)
                    break
            for cr in self.crates:
                if cr[1] > 0 and abs(cr[0] - b[0]) < 32 and self.layout.floor(cr[0]) - 56 < b[1]:
                    b[3] = 0
                    self._hit_crate(cr, b[4])
                    break
        self.bolts = [b for b in self.bolts if b[3] > 0]
        self.creatures = {k: v for k, v in self.creatures.items() if v.alive}
        for eb in self.enemy_bolts:
            eb[0] += eb[2] * dt
            eb[1] += eb[3] * dt
            eb[4] -= dt
            if p.rect.collidepoint(eb[0], eb[1]):
                eb[4] = 0
                p.hurt(6 + self.danger * 1.5, 1 if eb[2] > 0 else -1)
            elif eb[1] > self.layout.floor(eb[0]) or eb[1] < self.layout.ceiling(eb[0]):
                eb[4] = 0
        self.enemy_bolts = [eb for eb in self.enemy_bolts if eb[4] > 0]
        if sword:
            for cr in self.crates:
                if cr[1] > 0 and cr[2] not in p.swing_hit:
                    r = pygame.Rect(cr[0] - 32, self.layout.floor(cr[0]) - 56, 64, 56)
                    if sword.colliderect(r):
                        p.swing_hit.add(cr[2])
                        self._hit_crate(cr, 1.5)
        # prompts
        self.prompt = None
        if p.x < -200:
            self.prompt = ("[E] Cycle the airlock and return to your ship", (150, 255, 170))
        elif abs(p.x - self.vault_x) < 120:
            self.prompt = ("[E] Open the captain's vault", (255, 220, 120)) if not self.looted else \
                ("The vault is empty", (180, 180, 180))
        else:
            for tx, tid in self.terminals:
                if abs(p.x - tx) < 90 and tid not in self.used:
                    self.prompt = ("[E] Read the crew terminal", (140, 255, 200))
        if st.pilot_hp <= 0 and self.dead_t < 0:
            self.dead_t = 0.0
            self.particles.explosion(p.x, p.y - 40, 1.2)
            self.game.audio.play("explosion")
        if self.dead_t >= 0:
            self.dead_t += dt
            if self.dead_t > 1.5:
                self.game.game_over(f"The {self.derelict.name.split('the ')[-1]} became your tomb.")

    def _hurt_drone(self, c, dmg, knock):
        self.floaters.damage(c.x, c.y - 50, dmg)
        self.particles.burst(c.x, c.y - 20, 10, 160, [(255, 120, 100), (255, 255, 255)], life=(0.2, 0.5))
        self.game.audio.play("hit", 0.5)
        if c.hurt(dmg, knock):
            self.particles.explosion(c.x, c.y - 20, 0.7)
            self.game.audio.play("explosion", 0.5)
            self.game.freeze(0.04)
            self.game.state.earn(int(15 * self.danger))
            self.game.events.emit("creature_killed", kind="drone")

    def _hit_crate(self, cr, dmg):
        cr[1] -= dmg
        x, y = cr[0], self.layout.floor(cr[0])
        self.particles.burst(x, y - 30, 8, 150, [(170, 170, 180), (250, 200, 60)], life=(0.2, 0.5))
        self.game.audio.play("hit", 0.4)
        if cr[1] <= 0:
            st = self.game.state
            rng = random.Random(cr[2])
            roll = rng.random()
            if roll < 0.12:
                mod = roll_mod(rng)
                st.mods.append(mod)
                self.floaters.add(x, y - 70, mod["name"], (200, 160, 255), 17, 1.6)
            elif roll < 0.45:
                st.ore += 3
                self.floaters.add(x, y - 70, "+3 ore", (150, 240, 220))
            elif roll < 0.7:
                st.fuel = min(st.max_fuel, st.fuel + 80)
                self.floaters.add(x, y - 70, "+80 fuel", (255, 210, 90))
            elif roll < 0.85 and st.medkits < config.MAX_MEDKITS:
                st.medkits += 1
                self.floaters.add(x, y - 70, "+1 Medkit [H]", (120, 255, 160))
            else:
                cr_amt = int(40 * self.danger)
                st.earn(cr_amt)
                self.floaters.add(x, y - 70, f"+{cr_amt} cr", (255, 230, 120))
            self.particles.burst(x, y - 30, 24, 220, [(170, 170, 180), (250, 200, 60), (255, 255, 255)])
            self.game.audio.play("pickup", 0.6)

    # ------------------------------------------------------------------
    def draw(self, surf) -> None:
        cam = self.camera
        ox, oy = cam.ox, cam.oy
        surf.fill((10, 12, 18))
        self._draw_walls(surf, ox, oy)
        self._draw_floor(surf, ox, oy)
        st = self.game.state
        # airlock, terminals, crates, vault
        surf.blit(self.airlock_img, self.airlock_img.get_rect(midbottom=(-400 - ox, self.layout.floor(-400) - oy + 2)))
        for tx, tid in self.terminals:
            r = surf.blit(self.term_img, self.term_img.get_rect(midbottom=(tx - ox, self.layout.floor(tx) - oy + 2)))
            if tid not in self.used and int(self.clock * 2) % 2:
                pygame.draw.circle(surf, (140, 255, 200), (r.centerx, r.top - 8), 3)
        for x, hp, _id in self.crates:
            if hp > 0:
                surf.blit(self.crate_img, self.crate_img.get_rect(midbottom=(x - ox, self.layout.floor(x) - oy + 2)))
        vimg = self.vault_img if not self.looted else self.crate_img
        surf.blit(vimg, vimg.get_rect(midbottom=(self.vault_x - ox, self.layout.floor(self.vault_x) - oy + 2)))
        for c in self.creatures.values():
            c.draw(surf, ox, oy)
        if self.dead_t < 0:
            self.pilot.draw(surf, ox, oy)
        for bx, by, vx, _l, power, _h in self.bolts:
            sx, sy = bx - ox, by - oy
            pygame.draw.line(surf, (140, 230, 255), (sx, sy), (sx - vx * 0.02, sy), 4 if power < 2 else 9)
        for x, y, _vx, _vy, _l in self.enemy_bolts:
            pygame.draw.circle(surf, (255, 90, 80), (x - ox, y - oy), 6)
            pygame.draw.circle(surf, (255, 220, 200), (x - ox, y - oy), 3)
        self.particles.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        self._lighting(surf, ox, oy)
        self.floaters.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        # HUD
        hud.pilot_status(surf, self.game, self.pilot.jet / max(0.01, st.jetpack_capacity))
        prog = max(0.0, min(1.0, self.pilot.x / self.layout.end))
        hud.location(surf, self.derelict.name, f"to the vault: {prog * 100:.0f}%")
        if self.prompt and not self.game.dialogue.active:
            hud.prompt(surf, *self.prompt)
        if self.layout.breach(self.pilot.x) and self.pilot.y > self.layout.floor(self.pilot.x) - 60:
            hud.warning(surf, "ARCING CURRENT! GET OUT!", self.clock)

    def _draw_walls(self, surf, ox, oy) -> None:
        L = self.layout
        for i, (x0, x1, fy, br) in enumerate(L.segs):
            if x1 - ox < -50 or x0 - ox > config.SCREEN_W + 50:
                continue
            top = L.ceiling(x0) - oy
            bot = fy - oy
            r = pygame.Rect(x0 - ox, top, x1 - x0 + 1, bot - top)
            pygame.draw.rect(surf, (28, 32, 42), r)
            # panels
            for px in range(int(x0), int(x1), 120):
                pr = pygame.Rect(px - ox + 6, top + 40, 108, bot - top - 60)
                pygame.draw.rect(surf, (34, 38, 50), pr, border_radius=6)
                pygame.draw.rect(surf, (44, 50, 64), pr, 2, border_radius=6)
                if (px // 120 + i) % 5 == 0 and pr.h > 120:   # a window onto the stars
                    w = pygame.Rect(pr.x + 24, pr.y + 30, 60, 40)
                    pygame.draw.rect(surf, (4, 6, 16), w, border_radius=10)
                    rng = random.Random(px)
                    for _ in range(6):
                        surf.set_at((w.x + rng.randrange(w.w), w.y + rng.randrange(w.h)), (220, 220, 255))
                    pygame.draw.rect(surf, METAL_LIGHT, w, 2, border_radius=10)
            # pipes along the ceiling
            pygame.draw.line(surf, (60, 66, 80), (x0 - ox, top + 22), (x1 - ox, top + 22), 8)
            pygame.draw.line(surf, (90, 96, 112), (x0 - ox, top + 19), (x1 - ox, top + 19), 2)
            if br:
                for k in range(0, int(x1 - x0), 24):
                    pygame.draw.polygon(surf, (250, 200, 60), [(x0 - ox + k, bot - 420), (x0 - ox + k + 12, bot - 420),
                                                               (x0 - ox + k + 4, bot - 404), (x0 - ox + k - 8, bot - 404)])
        # ceiling slab
        for x0, x1, fy, br in L.segs:
            if x1 - ox < -50 or x0 - ox > config.SCREEN_W + 50:
                continue
            c = L.ceiling(x0) - oy
            pygame.draw.rect(surf, METAL_DARK, (x0 - ox, -10, x1 - x0 + 1, c + 10))
            pygame.draw.line(surf, METAL, (x0 - ox, c), (x1 - ox, c), 4)
            for k in range(int(x0), int(x1), 160):   # dangling cables
                sway = math.sin(self.clock * 1.5 + k) * 6
                pygame.draw.line(surf, (30, 30, 36), (k - ox, c), (k - ox + sway, c + 40 + (k % 3) * 15), 3)

    def _draw_floor(self, surf, ox, oy) -> None:
        H = config.SCREEN_H + 10
        for x0, x1, fy, br in self.layout.segs:
            if x1 - ox < -50 or x0 - ox > config.SCREEN_W + 50:
                continue
            y = fy - oy
            pygame.draw.rect(surf, METAL, (x0 - ox, y, x1 - x0 + 1, H - y))
            pygame.draw.rect(surf, METAL_DARK, (x0 - ox, y + 30, x1 - x0 + 1, H - y))
            pygame.draw.line(surf, METAL_LIGHT, (x0 - ox, y + 2), (x1 - ox, y + 2), 4)
            for k in range(int(x0) + 20, int(x1), 40):
                pygame.draw.circle(surf, METAL_DARK, (k - ox, y + 14), 3)
            if br:
                pygame.draw.rect(surf, (10, 12, 22), (x0 - ox, y - 420, x1 - x0, 420))
                for _ in range(2):
                    a = random.uniform(x0, x1)
                    pygame.draw.line(surf, (170, 230, 255), (a - ox, y - random.uniform(0, 400)),
                                     (a - ox + random.uniform(-20, 20), y), 1)

    def _lighting(self, surf, ox, oy) -> None:
        L = self.lighting
        p = self.pilot
        L.add(p.x - ox, p.y - oy - 80, 420, None, 1.0)
        L.add(p.x - ox + p.facing * 260, p.y - oy - 80, 320, None, 0.8)
        for x in range(int(ox // 420) * 420, int(ox + config.SCREEN_W + 420), 420):
            on = (x // 420) % 3 != 0 or int(self.clock * 2.5 + x) % 3
            if on:
                L.add(x - ox, self.layout.ceiling(x) - oy + 40, 280, (255, 70, 60), 0.8)
        for tx, _t in self.terminals:
            L.add(tx - ox, self.layout.floor(tx) - oy - 60, 140, (140, 255, 200), 0.8)
        L.add(self.vault_x - ox, self.layout.floor(self.vault_x) - oy - 50, 200, (255, 220, 140), 0.9)
        L.add(-240 - ox, self.layout.floor(-240) - oy - 80, 200, (120, 255, 160), 0.8)
        for b in self.bolts:
            L.add(b[0] - ox, b[1] - oy, 100, (140, 230, 255), 0.7)
        for x, y, *_r in self.enemy_bolts:
            L.add(x - ox, y - oy, 70, (255, 90, 80), 0.7)
        for x0, x1, fy, br in self.layout.segs:
            if br:
                L.add((x0 + x1) / 2 - ox, fy - oy - 60, 160, (140, 220, 255), 0.5 + 0.4 * random.random())
        L.apply(surf, 196, (2, 3, 8))
