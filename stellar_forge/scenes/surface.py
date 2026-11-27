"""Infinite side-scrolling planet surface, driven entirely by biome data."""
from __future__ import annotations

import math
import random

import pygame

from .. import config
from ..core.camera import SideCamera
from ..core.scene import Scene
from ..surface.bosses import make_boss
from ..surface.creatures import Creature
from ..surface.player import Pilot
from ..surface.terrain import Terrain
from ..surface.weather import Weather
from ..systems import lore
from ..systems.items import BOSSES, roll_mod
from ..systems.particles import ParticleSystem
from ..ui import hud
from ..ui.floaters import Floaters
from ..ui.lighting import Lighting
from ..ui.text import text
from ..systems import materials as mats
from ..systems import poi as poi_sys
from ..systems.materials import MATERIALS
from ..world.biomes import LIQUIDS

STRONGHOLD_TINTS = {"desert": None, "ice": None, "forest": None}
DAY_LENGTH = 240.0            # seconds of world time for a full day/night cycle
# props that glow in the dark, per biome: prop sprite substring -> light colour
GLOWING = {"crystal": (200, 150, 255), "shroom": (220, 120, 255), "pod": (170, 255, 60), "vent": (255, 120, 40),
           "geode": (220, 160, 255), "kelp": (120, 255, 200), "coral": (255, 140, 140)}


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class SurfaceScene(Scene):
    advances_time = True
    on_foot = True     # gamepad: A jumps, X swings

    def __init__(self, game, planet):
        super().__init__(game)
        self.planet = planet
        self.biome = planet.biome
        self.terrain = Terrain(planet, planet.seed)
        liquid = None
        if self.terrain.liquid:
            liquid = (self.terrain.liquid, self.terrain.liquid_y, LIQUIDS[self.terrain.liquid])
        self.pilot = Pilot(game, 280, self.terrain.height, self.biome.gravity, self.biome.friction, liquid)
        self.camera = SideCamera()
        self.camera.follow(self.pilot.x, self.pilot.y, 0, snap=True)
        self.particles = ParticleSystem(500)
        self.weather = Weather(self.biome.weather, planet.seed)
        self.creatures: dict[str, Creature] = {}
        self.killed: set[str] = set()
        self.bolts = []           # [x, y, vx, life]
        self.clock = 0.0
        self.dead_t = -1.0
        self.prompt = None
        sx, sy = planet.sector
        self.danger = game.universe.danger_at(sx, sy)
        from ..surface.render import WorldPainter
        self.painter = WorldPainter(self)
        a = game.assets
        from ..systems.items import SHIPS
        ship_id = game.state.ship
        ship_spec = SHIPS.get(ship_id, SHIPS["voyager"])
        ship_mult = 1.5 if ship_id == "voyager" else 2.2
        self.rocket_img = a.sprite(ship_spec["sprite"], mult=ship_mult)
        self.stronghold_img = None
        if self.terrain.stronghold_x is not None:
            self.stronghold_img = a.sprite(self.biome.stronghold_sprite, mult=self.biome.stronghold_mult)
        self._liquid_layer = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        self._last_cam = (self.camera.x, self.camera.y)
        self._prop_imgs = {}
        self._back_imgs = {}
        self.floaters = Floaters()
        self.lighting = Lighting()
        self.boss = None
        self.pilot.anchor_fn = self.raycast
        self.cave_img = a.sprite("generated/interiors/cave_entrance.png")
        self.arena_pillar = a.sprite("boss_fight/pillar.png")
        self.arena_skull = a.sprite("boss_fight/skull.png")
        self.outpost_imgs = {k: a.sprite(f"generated/outposts/{k}.png") for k in ("hab", "drill", "pump", "beacon")}
        self.ore_imgs = {"ore": a.sprite("generated/props/ore.png"), "fuel": a.sprite("generated/props/ore_fuel.png")}
        self.medkit_img = a.sprite("generated/props/medkit.png")
        self._night_sky = None
        from ..surface.poi_layer import PoiLayer
        self.pois = PoiLayer(self)
        self.mat_img = None
        if self.biome.id in MATERIALS:
            self.mat_img = a.sprite(f"generated/props/mat_{self.biome.id}.png")

    # ------------------------------------------------------------------
    @property
    def music(self) -> str:
        return "boss" if self.boss is not None and self.boss.alive else "surface"

    @property
    def outpost(self) -> dict | None:
        return self.game.state.outposts.get(self.planet.id)

    @property
    def lair_cleared(self) -> bool:
        return self.planet.id in self.game.state.lairs_cleared

    def daylight(self) -> float:
        """1 = noon, 0 = midnight. Each planet has its own time zone."""
        phase = (self.game.state.world_time / DAY_LENGTH + (self.planet.seed % 997) / 997) % 1.0
        return 0.5 + 0.5 * math.cos(phase * math.tau)

    @property
    def night(self) -> bool:
        return self.daylight() < 0.3

    def raycast(self, x, y, dx, dy, max_d):
        """Grappling-hook target: ground, ceiling or the top of a tall prop."""
        t = self.terrain
        anchors = []
        for chunk in (t.chunk_of(x) - 1, t.chunk_of(x), t.chunk_of(x) + 1):
            for px, idx, scale, flip in t.props(chunk):
                prop = self.biome.props[idx]
                img = self._prop_img(idx, scale, flip, px)
                h = img.get_height()
                if h >= 170 and not prop.front:
                    gy = t.height(px)
                    w = img.get_width()
                    anchors.append(pygame.Rect(px - w * 0.3, gy - h, w * 0.6, h * 0.45))
        ceiling = getattr(t, "ceiling", None)
        step = 14
        d = 30.0
        while d < max_d:
            px, py = x + dx * d, y + dy * d
            if py >= t.height(px) - 2:
                return px, t.height(px)
            if ceiling is not None and py <= ceiling(px) + 2:
                return px, ceiling(px)
            for r in anchors:
                if r.collidepoint(px, py):
                    return px, py
            d += step
        return None

    @property
    def looted(self) -> bool:
        return self.planet.id in self.game.state.looted_strongholds

    def on_enter(self) -> None:
        st = self.game.state
        b = self.biome
        self.game.banner.show(f"{self.planet.name}", f"{b.name} world  ·  gravity {b.gravity:.2f} g  ·  {b.description}")
        if self.planet.stronghold and not self.looted:
            side = "east" if self.terrain.stronghold_x > 0 else "west"
            self.game.toasts.add(f"Ancient signal: stronghold {abs(self.terrain.stronghold_x) / 100:.0f} m {side}",
                                 (255, 210, 90), 5)
        if st.pilot_hp <= 0:
            st.pilot_hp = st.max_pilot_hp

    def save_location(self) -> None:
        self.game.state.location = {"kind": "surface", "planet": self.planet.id}

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
        elif e.key == pygame.K_o and abs(self.pilot.x) < 300 and self.dead_t < 0:
            from .outpost import OutpostScene
            self.game.scenes.push(OutpostScene(self.game, self.planet))
        elif e.key == pygame.K_q and ("boomerang" in self.game.state.weapons or "spear" in self.game.state.weapons):
            st = self.game.state
            st.foot_weapon = "boomerang" if st.foot_weapon == "sword" else "sword"
            from ..systems.items import FOOT_WEAPONS
            self.game.toasts.add(f"Equipped: {FOOT_WEAPONS[st.foot_weapon]['name']}", (200, 220, 255), 1.5)
        elif e.key == pygame.K_e and self.dead_t < 0:
            self.interact()
        elif e.key == pygame.K_h and self.dead_t < 0:
            self.pilot.use_medkit(self.particles, self.floaters)

    def interact(self) -> None:
        p = self.pilot
        st = self.game.state
        cave = getattr(self.terrain, "cave_x", None)
        if cave is not None and abs(p.x - cave) < 200 and abs(p.x) >= 120:
            from .cave import CaveScene
            self.game.audio.play("land", 0.5)
            self.game.scenes.push(CaveScene(self.game, self.planet), fade=True)
            return
        if abs(p.x) < 200:
            cost = 12 * self.biome.gravity
            st.fuel = max(0.0, st.fuel - cost)
            st.pilot_hp = st.max_pilot_hp
            self.game.audio.play("land")
            self.game.launch(self.planet)
            return
        if self.pois.interact():
            return
        sh = self.terrain.stronghold_x
        if sh is not None and abs(p.x - sh) < 230:
            if self.planet.shard and self.planet.shard not in st.shards:
                if not st.boss_defeated:
                    self.game.toasts.add("Sealed by a power far older than the Keys. Not yet...", config.UI_VIOLET, 3)
                    self.game.audio.play("deny")
                    return
                if self.game.quests.warden_alive(self.planet):
                    self.game.toasts.add("The Warden in orbit keeps the vault sealed. Destroy it first!",
                                         config.UI_DANGER, 3)
                    self.game.audio.play("deny")
                    return
            from .stronghold import StrongholdScene
            self.game.scenes.push(StrongholdScene(self.game, self.planet, looted=self.looted), fade=True)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.clock += dt
        st = self.game.state
        p = self.pilot
        keys = self.game.input.pressed()
        alive = self.dead_t < 0
        self.floaters.update(dt)
        self._update_boss(dt)
        self._hints()
        shots = p.update(dt, keys, enabled=alive)
        dust_col = self.biome.ground_top
        if getattr(p, "dust", False):
            p.dust = False
            self.particles.burst(p.x, p.y - 4, 14, 140, [dust_col, self.biome.ground], life=(0.25, 0.6),
                                 size=(2, 5), drag=3)
        elif p.on_ground and abs(p.vx) > 120 and random.random() < dt * 9:
            self.particles.emit(p.x - p.facing * 12, p.y - 3, -p.vx * 0.15, random.uniform(-60, -20), 0.35,
                                random.uniform(2, 4), dust_col, drag=3)
        for x, y, vx, power in shots:
            self.bolts.append([x, y, vx, 0.9, power, set()])
            if self.game.net is not None:
                self.game.net.send_shot("bolt", x, y, vx, 0.0, power)
        self.camera.follow(p.x, p.y, dt)
        cdx, cdy = self.camera.x - self._last_cam[0], self.camera.y - self._last_cam[1]
        self._last_cam = (self.camera.x, self.camera.y)
        self.weather.update(dt, cdx, cdy)
        self.particles.update(dt)

        # liquids & hazards
        if p.submerged:
            dmg = p.liquid[2]["damage"]
            if (p.liquid[0] == "lava" and "volcanic" in st.trophies) or \
                    (p.liquid[0] == "acid" and "ocean" in st.trophies):
                dmg = 0
            if dmg:
                p.hazard(dmg, dt)
                if random.random() < 0.3:
                    self.particles.emit(p.x, p.y - 40, random.uniform(-40, 40), -random.uniform(60, 140), 0.5, 4,
                                        (255, 150, 60) if p.liquid[0] == "lava" else (160, 255, 80))
        self._prop_hazards(dt)
        self._update_creatures(dt)
        self._update_bolts(dt)
        self._ore(dt)
        self._medkits(dt)
        self.pois.update(dt)
        if p.jetting and random.random() < 0.6:
            self.particles.emit(p.x - p.facing * 16, p.y - 24, random.uniform(-30, 30), random.uniform(80, 160),
                                0.3, 4, (255, 170, 60), glow=True)

        # prompts
        self.prompt = None
        cave = getattr(self.terrain, "cave_x", None)
        if abs(p.x) < 200:
            o = self.game.input.key_name("outpost")
            extra = f"   [{o}] Outpost" if self.outpost or st.chapter >= 3 else ""
            self.prompt = (f"[E] Board rocket and launch{extra}", (150, 255, 170))
        elif cave is not None and abs(p.x - cave) < 200:
            self.prompt = ("[E] Descend into the caves", (255, 220, 150))
        elif self.terrain.stronghold_x is not None and abs(p.x - self.terrain.stronghold_x) < 230:
            if self.looted:
                self.prompt = ("[E] Enter the stronghold (already looted)", (200, 200, 200))
            else:
                self.prompt = ("[E] Enter the ancient stronghold", (255, 210, 90))
        if self.prompt is None:
            self.prompt = self.pois.prompt()

        if st.pilot_hp <= 0 and alive:
            self.dead_t = 0.0
            self.particles.explosion(p.x, p.y - 40, 1.2)
            self.game.audio.play("explosion")
        if self.dead_t >= 0:
            self.dead_t += dt
            if self.dead_t > 1.5:
                self.game.game_over(f"You perished on {self.planet.name}.")

    def _prop_hazards(self, dt) -> None:
        p = self.pilot
        pr = p.rect
        for chunk in (self.terrain.chunk_of(p.x) - 1, self.terrain.chunk_of(p.x), self.terrain.chunk_of(p.x) + 1):
            for x, idx, scale, _flip in self.terrain.props(chunk):
                prop = self.biome.props[idx]
                if not prop.hazard:
                    continue
                img = self._prop_img(idx, scale, _flip, x)
                w = img.get_width() * 0.45
                hr = pygame.Rect(x - w / 2, self.terrain.height(x) - img.get_height() * 0.85, w,
                                 img.get_height() * 0.85)
                if pr.colliderect(hr):
                    if "vent" in (prop.sprite or "") and "volcanic" in self.game.state.trophies:
                        continue
                    if p.hurt(prop.hazard, -1 if p.x < x else 1):
                        self.game.toasts.add("Ouch!", (255, 150, 120), 1.0)

    def _update_creatures(self, dt) -> None:
        p = self.pilot
        c0 = self.terrain.chunk_of(p.x)
        for chunk in range(c0 - 2, c0 + 3):
            for uid, x, kind in self.terrain.creatures(chunk):
                if uid not in self.creatures and uid not in self.killed:
                    self.creatures[uid] = Creature(self.game, uid, x, kind, self.terrain.height,
                                                   self.biome.creature_tint, self.danger,
                                                   sprites=self.biome.creature_sprites)
        sword = p.sword_rect()
        for uid, c in list(self.creatures.items()):
            if abs(c.x - p.x) > config.TERRAIN_CHUNK * 3:
                del self.creatures[uid]
                continue
            c.update(dt, p.x, p.y)
            if self.dead_t < 0 and c.rect.colliderect(p.rect):
                p.hurt(c.damage * (1.3 if self.night else 1.0), 1 if p.x > c.x else -1)
            if sword and uid not in p.swing_hit and sword.colliderect(c.rect):
                p.swing_hit.add(uid)
                self.particles.burst(c.x, c.y - 30, 10, 180, [(180, 255, 140), (255, 255, 255)], life=(0.2, 0.5))
                self.game.audio.play("hit", 0.5)
                dmg = p.melee_damage
                self.floaters.damage(c.x, c.y - 60, dmg)
                if c.hurt(dmg, p.facing):
                    self._kill(c)
        self.creatures = {k: v for k, v in self.creatures.items() if v.alive}

    def _kill(self, c: Creature) -> None:
        self.killed.add(c.id)
        self.particles.explosion(c.x, c.y - 30, 0.6)
        self.game.audio.play("explosion", 0.4)
        self.game.freeze(0.04)
        if c.id.startswith("queen"):
            return
        reward = int(8 + self.danger * 4)
        self.game.state.earn(reward)
        self.game.events.emit("creature_killed", kind=c.kind)
        poi_sys.on_kill(self.game, self.planet)
        key = f"{self.biome.id}:{c.kind}"
        if key not in self.game.state.scanned:
            self.game.state.scanned.append(key)
            self.game.toasts.add("New creature logged in the codex", (140, 255, 200), 2.5, icon="book")
        self.game.toasts.add(f"+{reward} cr", (255, 230, 120), 1.2)
        if self.game.state.medkits < config.MAX_MEDKITS and random.random() < 0.18:
            self.game.state.medkits += 1
            self.floaters.add(c.x, c.y - 72, "+1 Medkit", (120, 255, 160), 15, 1.2)
            self.game.toasts.add("+1 Nano-Medkit [H]", (120, 255, 160), 1.6, icon="medkit")

    def _update_bolts(self, dt) -> None:
        mult = self.game.state.weapon_mult
        for b in self.bolts:
            b[0] += b[2] * dt
            b[3] -= dt
            power = b[4]
            ceiling = getattr(self.terrain, "ceiling", None)
            if b[1] > self.terrain.height(b[0]) or (ceiling and b[1] < ceiling(b[0])):
                b[3] = 0
                self.particles.burst(b[0], b[1], 5, 90, [(140, 230, 255)], life=(0.1, 0.3))
                continue
            for c in self.creatures.values():
                if c.alive and c.id not in b[5] and c.rect.collidepoint(b[0], b[1]):
                    b[5].add(c.id)
                    if power < 2:
                        b[3] = 0        # charged shots pierce
                    self.particles.burst(b[0], b[1], 6, 120, [(140, 230, 255)], life=(0.1, 0.3))
                    dmg = power * mult
                    self.floaters.damage(c.x, c.y - 60, dmg, crit=power >= 2)
                    if c.hurt(dmg, 1 if b[2] > 0 else -1):
                        self._kill(c)
                    break
            if self.boss is not None and self.boss.alive and "boss" not in b[5]:
                for r in self.boss.hitboxes():
                    if r.collidepoint(b[0], b[1]):
                        b[5].add("boss")
                        if power < 2:
                            b[3] = 0
                        self._hit_boss(power * mult * 0.8, b[0], b[1])
                        break
        self.bolts = [b for b in self.bolts if b[3] > 0]

    def _ore(self, dt) -> None:
        p = self.pilot
        st = self.game.state
        sword = p.sword_rect()
        c0 = self.terrain.chunk_of(p.x)
        for chunk in (c0 - 1, c0, c0 + 1):
            for uid, x, kind in self.terrain.ores(chunk):
                if uid in st.collected:
                    continue
                gy = self.terrain.height(x)
                r = pygame.Rect(x - 36, gy - 64, 72, 64)
                if (sword and sword.colliderect(r)) or (p.rect.colliderect(r) and self.game.input.pressed()[pygame.K_e]):
                    st.collected.append(uid)
                    if kind == "fuel":
                        st.fuel = min(st.max_fuel, st.fuel + 45)
                        self.game.toasts.add("+45 ship fuel (crystal)", (255, 210, 90), 1.5)
                    elif kind == "mat":
                        b = self.biome.id
                        n = 1 + (1 if self.night else 0) + (random.random() < 0.4)
                        mats.give(self.game, b, n, toast=False)
                        self.floaters.add(x, gy - 50, f"+{n} {mats.name(b)}", mats.color(b))
                    else:
                        n = random.randint(2, 4) + (1 if self.night else 0) + getattr(self, "ore_bonus", 0)
                        st.ore += n
                        self.game.events.emit("ore_collected", amount=n)
                        self.floaters.add(x, gy - 50, f"+{n} ore", (140, 255, 230))
                    self.game.audio.play("pickup", 0.6)
                    col = (255, 200, 60) if kind == "fuel" else \
                        mats.color(self.biome.id) if kind == "mat" else self.biome.ore_color
                    self.particles.burst(x, gy - 20, 16, 220, [col, (255, 255, 255)], life=(0.3, 0.8),
                                         gravity=600)

    def _medkits(self, dt) -> None:
        if not hasattr(self.terrain, "medkits"):
            return
        p = self.pilot
        st = self.game.state
        c0 = self.terrain.chunk_of(p.x)
        for chunk in (c0 - 1, c0, c0 + 1):
            for uid, x in self.terrain.medkits(chunk):
                if uid in st.collected:
                    continue
                gy = self.terrain.height(x)
                r = pygame.Rect(x - 36, gy - 68, 72, 68)
                if p.rect.colliderect(r):
                    if st.medkits < config.MAX_MEDKITS:
                        st.collected.append(uid)
                        st.medkits += 1
                        self.game.audio.play("pickup", 0.7)
                        self.floaters.add(x, gy - 54, "+1 Medkit [H]", (120, 255, 160), 16, 1.3)
                        self.game.toasts.add("Picked up Nano-Medkit (press [H] to heal)", (120, 255, 160), 2.0,
                                             icon="medkit")
                        self.particles.burst(x, gy - 28, 18, 200, [(110, 255, 160), (255, 255, 255)],
                                             life=(0.3, 0.8), gravity=320)
                    elif st.pilot_hp < st.max_pilot_hp - 0.5:
                        st.collected.append(uid)
                        p.apply_heal(self.particles, self.floaters)
                    else:
                        self.prompt = (f"Nano-Medkit (carrying max {config.MAX_MEDKITS})", (150, 230, 180))

    # ------------------------------------------------------------------
    # planet boss
    def _update_boss(self, dt) -> None:
        t = self.terrain
        lair = getattr(t, "lair_x", None)
        p = self.pilot
        if lair is not None and self.boss is None and not self.lair_cleared and abs(p.x - lair) < 950:
            self.boss = make_boss(self, lair)
            if self.boss:
                info = BOSSES[self.biome.id]
                self.game.banner.show(info["name"].upper(), "A legendary beast guards this land", 3.0)
                self.game.audio.play("alarm", 0.8)
                self.game.shake(10)
                self.game.hint("lair", [("ai", f"That's a {info['name']}! Watch the ground markers - every attack "
                                               "is telegraphed. Kill it for its trophy: " + info["perk"] + ".")])
        b = self.boss
        if b is None:
            return
        if not b.alive:
            return
        if abs(p.x - b.home) > 2400:      # left the arena: the beast heals and waits
            b.hp = min(b.max_hp, b.hp + b.max_hp * 0.2 * dt)
        b.update(dt)
        sword = p.sword_rect()
        if sword and "boss" not in p.swing_hit:
            for r in b.hitboxes():
                if sword.colliderect(r):
                    p.swing_hit.add("boss")
                    self._hit_boss(p.melee_damage, r.centerx, r.centery)
                    break

    def _hit_boss(self, dmg: float, x: float, y: float) -> None:
        b = self.boss
        real = dmg * b.hurt_mult
        self.floaters.damage(x, y - 40, real, crit=b.hurt_mult > 1.2)
        self.particles.burst(x, y, 12, 200, [(255, 230, 160), (255, 255, 255)], life=(0.2, 0.5))
        self.game.audio.play("hit", 0.6)
        if b.hurt(dmg):
            self._boss_defeated()

    def _boss_defeated(self) -> None:
        b = self.boss
        st = self.game.state
        info = BOSSES[self.biome.id]
        for k in range(8):
            self.particles.explosion(b.home + random.uniform(-150, 150), self.terrain.height(b.home) - random.uniform(40, 220), 1.8)
        self.game.audio.play("explosion", 1.0)
        self.game.shake(30)
        self.game.freeze(0.12)
        self.game.slowmo(1.6)
        st.mark("lairs_cleared", self.planet.id)
        st.bump("bosses")
        reward = int(700 * self.danger)
        st.earn(reward)
        mod = roll_mod(random.Random(), min_rarity=2, luck=0.15)
        st.mods.append(mod)
        new = self.biome.id not in st.trophies
        if new:
            st.trophies.append(self.biome.id)
        lore.announce(self.game, lore.next_log(st, "architect"))
        self.game.banner.show(f"{info['name']} slain!",
                              (f"Trophy: {info['trophy']} ({info['perk']})  ·  " if new else "")
                              + f"+{reward} cr  ·  {mod['name']}", 5.0)
        self.game.audio.play("relic", 0.9)
        self.game.save()

    def _hints(self) -> None:
        g = self.game
        p = self.pilot
        if p.submerged:
            g.hint("liquid", "We're submerged. Water slows us; lava and acid burn. Jump or jetpack out.")
        if self.night:
            g.hint("night", "Night is falling. Creatures hit harder in the dark, but ore glows - bonus ore per "
                            "node until dawn.")
        cave = getattr(self.terrain, "cave_x", None)
        if cave is not None and abs(p.x - cave) < 500:
            g.hint("cave", "A cave mouth! Caves are dark and dangerous, but the ore down there is rich.")

    # ------------------------------------------------------------------
    def draw(self, surf) -> None:
        cam = self.camera
        ox, oy = cam.ox, cam.oy
        surf.blit(self.painter.sky, (0, 0))
        self._draw_night_sky(surf)
        self.painter.draw_far(surf, ox, oy, self.clock, self.daylight())
        self.painter.draw_backdrop(surf, ox, oy)
        self._draw_back_props(surf, ox, oy)
        self._draw_props(surf, ox, oy, front=False)
        self._draw_structures(surf, ox, oy)
        self._draw_features(surf, ox, oy)
        self.pois.draw(surf, ox, oy)
        boss = self.boss if self.boss is not None and self.boss.alive else None
        if boss and boss.behind_ground:
            boss.draw(surf, ox, oy)
        self.painter.draw_ground(surf, ox, oy)
        self._draw_ores(surf, ox, oy)
        self._draw_medkits(surf, ox, oy)
        self._draw_props(surf, ox, oy, front=True)
        if boss and not boss.behind_ground:
            boss.draw(surf, ox, oy)
        elif boss:
            boss.draw_over(surf, ox, oy)
        for c in self.creatures.values():
            if -100 < c.x - ox < config.SCREEN_W + 100:
                c.draw(surf, ox, oy)
        if self.game.net is not None:
            self.game.net.draw_surface(surf, ox, oy, self.planet.id)
        if self.dead_t < 0:
            self.pilot.draw(surf, ox, oy)
        for bx, by, vx, _l, power, _hit in self.bolts:
            sx, sy = int(bx - ox) // 2 * 2, int(by - oy) // 2 * 2
            ln = 28 if power < 2 else 56
            th = 4 if power < 2 else 10
            d = -1 if vx > 0 else 1
            surf.fill((90, 180, 255), (min(sx, sx + d * ln), sy - th // 2, ln, th))
            surf.fill((220, 245, 255), (min(sx, sx + d * ln // 2), sy - th // 4, ln // 2, max(2, th // 2)))
        self.painter.draw_liquid(surf, ox, oy, self.clock, self._liquid_layer)
        self._apply_lighting(surf, ox, oy)
        self.pois.draw_overlay(surf, ox, oy)
        self.floaters.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        self.particles.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        self.weather.draw(surf)
        self._draw_hud(surf)

    def _prop_img(self, idx: int, scale: float, flip: bool, x: float):
        """Props are always drawn at the art scale: no random resizing."""
        prop = self.biome.props[idx]
        return self.game.assets.sprite(prop.sprite, prop.mult, flip, prop.tint)

    def _draw_props(self, surf, ox, oy, front: bool) -> None:
        t = self.terrain
        c0 = t.chunk_of(ox)
        for chunk in range(c0 - 1, c0 + 3):
            for x, idx, scale, flip in t.props(chunk):
                prop = self.biome.props[idx]
                if prop.front != front:
                    continue
                if not (-300 < x - ox < config.SCREEN_W + 300):
                    continue
                img = self._prop_img(idx, scale, flip, x)
                gy = t.height(x)
                if hasattr(t, "roles") and idx in t.roles()["log"]:           # lying things rest on the lower side, never float
                    hw = img.get_width() * 0.38
                    gy = max(gy, t.height(x - hw), t.height(x + hw))
                surf.blit(img, img.get_rect(midbottom=(x - ox, gy - oy + 4 * config.ART_SCALE)))

    def _back_img(self, idx: int, flip: bool):
        key = (idx, flip)
        img = self._back_imgs.get(key)
        if img is None:
            img = self._prop_img(idx, 1.0, flip, 0).copy()
            haze = getattr(self.painter, "far_fill", None) or self.biome.sky_bottom
            img.fill((150, 150, 165), special_flags=pygame.BLEND_RGB_MULT)
            img.fill(tuple(int(c * 0.28) for c in haze), special_flags=pygame.BLEND_RGB_ADD)
            self._back_imgs[key] = img
        return img

    def _draw_back_props(self, surf, ox, oy) -> None:
        t = self.terrain
        c0 = t.chunk_of(ox)
        names = self.biome.props
        for chunk in range(c0 - 1, c0 + 3):
            for x, idx, _s, flip in t.back_props(chunk):
                if not (-300 < x - ox < config.SCREEN_W + 300) or "antenna" in (names[idx].sprite or ""):
                    continue
                img = self._back_img(idx, flip)
                surf.blit(img, img.get_rect(midbottom=(x - ox, t.height(x) - oy + 6 * config.ART_SCALE)))

    def _draw_structures(self, surf, ox, oy) -> None:
        t = self.terrain
        # landed rocket
        rx = 0
        surf.blit(self.rocket_img, self.rocket_img.get_rect(midbottom=(rx - ox, t.height(rx) - oy + 6)))
        sh = t.stronghold_x
        if sh is not None and self.stronghold_img is not None:
            gy = t.height(sh) - oy
            if not self.looted:   # a stepped beacon of light: two flat bands, gently pulsing
                pulse = 0.5 + 0.5 * math.sin(self.clock * 2)
                for w, a in ((40, 30 + 20 * pulse), (16, 50 + 30 * pulse)):
                    beam = pygame.Surface((w, 1400), pygame.SRCALPHA)
                    beam.fill((255, 220, 120, int(a)))
                    surf.blit(beam, (sh - ox - w // 2, gy - 1400))
            surf.blit(self.stronghold_img, self.stronghold_img.get_rect(midbottom=(sh - ox, gy + 8)))

    def _draw_features(self, surf, ox, oy) -> None:
        t = self.terrain
        cave = getattr(t, "cave_x", None)
        if cave is not None and -300 < cave - ox < config.SCREEN_W + 300:
            surf.blit(self.cave_img, self.cave_img.get_rect(midbottom=(cave - ox, t.height(cave) - oy + 8)))
        lair = getattr(t, "lair_x", None)
        if lair is not None and -900 < lair - ox < config.SCREEN_W + 900:
            for d in (-1, 1):
                x = lair + d * 1080
                surf.blit(self.arena_pillar, self.arena_pillar.get_rect(midbottom=(x - ox, t.height(x) - oy + 10)))
            for k, dx in enumerate((-640, -230, 390, 720)):
                x = lair + dx
                img = pygame.transform.flip(self.arena_skull, k % 2 == 0, False)
                surf.blit(img, img.get_rect(midbottom=(x - ox, t.height(x) - oy + 8)))
        o = self.outpost
        if o:
            layout = [("hab", -330, True), ("pump", 300, o.get("pump", 0) > 0), ("drill", -560, o.get("drill", 0) > 0),
                      ("beacon", 520, o.get("beacon", False))]
            for name, x, built in layout:
                if not built:
                    continue
                img = self.outpost_imgs[name]
                r = surf.blit(img, img.get_rect(midbottom=(x - ox, t.height(x) - oy + 10)))
                if name == "drill" and int(self.clock * 6) % 2:
                    surf.fill((255, 220, 150), (r.centerx - 4, r.bottom - 14, 8, 8))
                if name == "beacon" and int(self.clock * 2) % 2:
                    surf.fill((200, 245, 255), (r.centerx - 6, r.top + 14, 12, 8))

    def _draw_night_sky(self, surf) -> None:
        dark = 1.0 - self.daylight()
        if dark < 0.3:
            return
        if self._night_sky is None:
            sky = pygame.Surface((config.SCREEN_W, config.SCREEN_H))
            sky.fill((6, 8, 22))
            rng = random.Random(self.planet.seed + 1)
            for _ in range(200):
                c = rng.randint(140, 255)
                sky.fill((c, c, min(255, c + 25)), (rng.randrange(0, config.SCREEN_W, 2),
                                                     rng.randrange(0, config.SCREEN_H * 2 // 3, 2), 2, 2))
            self._night_sky = sky
        self._night_sky.set_alpha(int(min(1.0, (dark - 0.3) / 0.5) * 200))
        surf.blit(self._night_sky, (0, 0))

    def _apply_lighting(self, surf, ox, oy) -> None:
        darkness = self.darkness()
        if darkness <= 2:
            return
        L = self.lighting
        p = self.pilot
        L.add(p.x - ox, p.y - oy - 50, 300, None, 1.0)
        L.add(p.x - ox + p.facing * 140, p.y - oy - 50, 200, None, 0.7)
        t = self.terrain
        c0 = t.chunk_of(ox)
        for chunk in range(c0 - 1, c0 + 3):
            for x, idx, scale, _f in t.props(chunk):
                spr = self.biome.props[idx].sprite or ""
                for key, colr in GLOWING.items():
                    if key in spr:
                        h = self._prop_img(idx, scale, False, x).get_height()
                        L.add(x - ox, t.height(x) - oy - h * 0.5, 120 + h * 0.4, colr, 0.8)
                        break
            for uid, x, kind in t.ores(chunk):
                if uid not in self.game.state.collected:
                    L.add(x - ox, t.height(x) - oy - 20, 110, (255, 200, 60) if kind == "fuel" else
                          mats.color(self.biome.id) if kind == "mat" else self.biome.ore_color, 0.7)
            if hasattr(t, "medkits"):
                for uid, x in t.medkits(chunk):
                    if uid not in self.game.state.collected:
                        L.add(x - ox, t.height(x) - oy - 26, 130, (100, 255, 160), 0.75)
        L.add(0 - ox, t.height(0) - oy - 120, 260, (255, 220, 150), 0.8)     # rocket floodlight
        self.pois.lights(L, ox, oy)
        for b in self.bolts:
            L.add(b[0] - ox, b[1] - oy, 90, (140, 230, 255), 0.6)
        if self.boss is not None and self.boss.alive:
            for r in self.boss.hitboxes()[:1]:
                L.add(r.centerx - ox, r.centery - oy, 260, (255, 160, 90), 0.8)
        if self.biome.liquid == "lava" and t.liquid:
            L.add(p.x - ox, t.liquid_y - oy, 500, (255, 110, 30), 0.6)
        L.apply(surf, darkness)

    def darkness(self) -> float:
        return max(0.0, (0.55 - self.daylight()) / 0.55) * 185

    def _draw_ores(self, surf, ox, oy) -> None:
        t = self.terrain
        st = self.game.state
        c0 = t.chunk_of(ox)
        for chunk in range(c0 - 1, c0 + 3):
            for uid, x, kind in t.ores(chunk):
                if uid in st.collected or not (-60 < x - ox < config.SCREEN_W + 60):
                    continue
                img = self.mat_img if kind == "mat" and self.mat_img else self.ore_imgs["fuel" if kind == "fuel" else "ore"]
                gy = t.height(x) - oy
                r = surf.blit(img, img.get_rect(midbottom=(x - ox, gy + 6)))
                if int(self.clock * 3 + x) % 5 == 0:   # a pixel glint
                    surf.fill((255, 255, 255), (r.centerx + 6, r.top + 6, 4, 4))

    def _draw_medkits(self, surf, ox, oy) -> None:
        t = self.terrain
        if not hasattr(t, "medkits"):
            return
        st = self.game.state
        c0 = t.chunk_of(ox)
        for chunk in range(c0 - 1, c0 + 3):
            for uid, x in t.medkits(chunk):
                if uid in st.collected or not (-80 < x - ox < config.SCREEN_W + 80):
                    continue
                gy = t.height(x) - oy
                bob = math.sin(self.clock * 3.2 + x * 0.01) * 5
                sx, sy = int(x - ox), int(gy - 10 + bob)
                pulse = 0.5 + 0.5 * math.sin(self.clock * 4.0 + x)
                rad = int(24 + 6 * pulse)
                aura = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(aura, (100, 255, 160, int(45 + 35 * pulse)), (rad + 2, rad + 2), rad)
                pygame.draw.circle(aura, (160, 255, 210, int(100 + 60 * pulse)), (rad + 2, rad + 2), rad, 2)
                surf.blit(aura, (sx - rad - 2, sy - self.medkit_img.get_height() // 2 - rad - 2))
                r = surf.blit(self.medkit_img, self.medkit_img.get_rect(midbottom=(sx, sy + 6)))
                if int(self.clock * 4 + x) % 4 == 0:
                    surf.fill((210, 255, 230), (r.x + 8, r.y + 4, 4, 4))

    def map_marks(self) -> list:
        t = self.terrain
        marks = [(0, "rocket", False)]
        if getattr(t, "cave_x", None) is not None:
            marks.append((t.cave_x, "cave", self.planet.id in self.game.state.caves_cleared))
        if getattr(t, "lair_x", None) is not None:
            marks.append((t.lair_x, "skull", self.lair_cleared))
        if t.stronghold_x is not None:
            marks.append((t.stronghold_x, "key", self.looted))
        return marks + self.pois.marks()

    def _draw_map(self, surf) -> None:
        p = self.pilot
        hud.strip_map(surf, self.map_marks(), p.x, p.x - 7000, p.x + 7000)

    def _draw_clock(self, surf, pos) -> None:
        d = self.daylight()
        phase = (self.game.state.world_time / DAY_LENGTH + (self.planet.seed % 997) / 997) % 1.0
        x, y = pos
        pygame.draw.circle(surf, (20, 26, 44), (x, y), 12)
        a = phase * math.tau - math.pi / 2
        if d >= 0.3:
            pygame.draw.circle(surf, (255, 220, 120), (x, y), 7)
        else:
            pygame.draw.circle(surf, (220, 225, 255), (x, y), 7)
            pygame.draw.circle(surf, (20, 26, 44), (x + 3, y - 2), 6)
        pygame.draw.circle(surf, (90, 110, 150), (x, y), 12, 1)
        pygame.draw.circle(surf, (255, 255, 255), (x + math.cos(a) * 12, y + math.sin(a) * 12), 2)

    def _draw_hud(self, surf) -> None:
        g = self.game
        p = self.pilot
        hud.pilot_status(surf, g, p.jet / max(0.01, g.state.jetpack_capacity))
        hud.relic_slots(surf, g)
        r = hud.location(surf, f"{self.planet.name} · {self.biome.name}")
        self._draw_clock(surf, (r.x - 22, r.centery))
        hud.objective(surf, g)
        self._draw_map(surf)
        if self.boss is not None and self.boss.alive:
            hud.boss_bar(surf, self.boss.name, self.boss.hp / self.boss.max_hp, self.boss.enraged)
        if self.prompt and not self.game.dialogue.active:
            hud.prompt(surf, *self.prompt)
        if self.pilot.submerged and self.pilot.liquid[2]["damage"]:
            hud.warning(surf, f"{self.pilot.liquid[0].upper()}! GET OUT!", self.clock)
        if self.game.settings.show_hints and not self.game.dialogue.active:
            k = self.game.input.key_name
            text(surf, hud.fit(f"A/D move  W jump/jet  SPACE sword  F blaster  {k('heal')} heal  "
                               "E interact  B logbook", config.SCREEN_W - 2 * 250),
                 (config.SCREEN_W // 2, config.SCREEN_H - 6), 12, (150, 160, 190), anchor="midbottom")
