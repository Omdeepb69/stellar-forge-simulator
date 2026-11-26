"""The underground layer: endless, dark caves beneath some planets.

Caves reuse all of the surface gameplay (creatures, ore, blaster, sword,
grapple) on a terrain that also has a ceiling. They are pitch dark: your
headlamp, glowing crystals and fungi are the only light. Ore is richer,
creatures are thicker, and rare geodes hold loot and Architect logs.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

from .. import config
from ..surface.player import Pilot
from ..surface.weather import Weather
from ..systems import lore
from ..systems.items import roll_mod
from ..world.noise import fbm
from ..world.rng import int_hash, rng_of
from .surface import SurfaceScene, _mix


class CaveTerrain:
    """A finite cave: entrance rope at x=0, a rock wall behind it, three sigils
    along the way and the sealed vault at the far end. Floor and ceiling are
    noise with guaranteed headroom; the floor rises into the ceiling at both ends."""

    liquid = None
    liquid_y = float("inf")
    stronghold_x = None
    cave_x = None
    lair_x = None
    pois: list = []

    def __init__(self, planet):
        self.planet = planet
        self.biome = planet.biome
        self.seed = (planet.seed ^ 0xCA7E) & 0x7FFFFFFF
        rng = rng_of(self.seed, "dungeon")
        self.left = -560.0
        self.end = 6200.0 + rng.randrange(5) * 800.0
        self.vault_x = self.end - 320.0
        self.sigils = [round(self.end * f + rng.uniform(-260, 260)) for f in (0.27, 0.53, 0.78)]
        self.geode_spots = [round(self.end * f + rng.uniform(-150, 150)) for f in (0.4, 0.66)]   # two guaranteed
        self.pads = [(0.0, 220.0), (self.vault_x, 300.0)] + [(float(x), 140.0) for x in self.sigils]
        self._pad_h = {px: self._floor_raw(px) for px, _w in self.pads}
        self._f, self._c, self._b = {}, {}, {}

    def _floor_raw(self, x):
        return fbm(x / 1050.0, self.seed, 4) * 320 + fbm(x / 240.0, self.seed + 3, 2) * 50

    def _base(self, x):
        """Floor without the end walls (the ceiling follows this)."""
        k = int(x // 4)
        h = self._b.get(k)
        if h is None:
            wx = k * 4
            h = self._floor_raw(wx)
            for px, w in self.pads:
                d = abs(wx - px)
                if d < w + 260:
                    t = max(0.0, min(1.0, (d - w) / 260))
                    t = t * t * (3 - 2 * t)
                    h = self._pad_h[px] * (1 - t) + h * t
            if len(self._b) > 60000:
                self._b.clear()
            self._b[k] = h
        return h

    def height(self, x):
        k = int(x // 4)
        h = self._f.get(k)
        if h is None:
            wx = k * 4
            h = self._base(wx)
            over = max(0.0, wx - self.end, self.left - wx)
            if over:                                     # the floor curls up into a rock wall
                h = max(h - over * over * 0.02 - over * 1.2, self.ceiling(wx) - 4)
            h = round(h / config.ART_SCALE) * config.ART_SCALE
            if len(self._f) > 60000:
                self._f.clear()
            self._f[k] = h
        return h

    def inside(self, x, margin=0.0) -> bool:
        return self.left + margin < x < self.end - margin

    def ceiling(self, x):
        k = int(x // 4)
        c = self._c.get(k)
        if c is None:
            wx = k * 4
            gap = 470 + fbm(wx / 780.0, self.seed + 9, 3) * 250 + max(0.0, 360 - abs(wx) * 0.5)
            gap += max(0.0, 300 - abs(wx - self.vault_x) * 0.5)          # a tall vault chamber
            c = self._base(wx) - max(400.0, gap)
            if len(self._c) > 60000:
                self._c.clear()
            self._c[k] = c
        return c

    def slope(self, x):
        return (self.height(x + 6) - self.height(x - 6)) / 12

    def in_pad(self, x, margin=0):
        return any(abs(x - px) < w + margin for px, w in self.pads)

    def chunk_of(self, x):
        return math.floor(x / config.TERRAIN_CHUNK)

    def speck(self, col):
        return int_hash(col, self.seed + 991)

    @lru_cache(maxsize=256)
    def props(self, chunk):
        rng = rng_of(self.seed, "cprops", chunk)
        glowing = [i for i, p in enumerate(self.biome.props)
                   if p.sprite and any(k in p.sprite for k in ("crystal", "shroom", "geode", "pod", "kelp"))]
        pool = glowing or list(range(len(self.biome.props)))
        out = []
        for _ in range(rng.randint(2, 5)):
            x = chunk * config.TERRAIN_CHUNK + rng.uniform(0, config.TERRAIN_CHUNK)
            if self.in_pad(x, 60) or not pool or not self.inside(x, 120):
                continue
            out.append((x, rng.choice(pool), rng.uniform(0.5, 0.85), rng.random() < 0.5))
        out.sort(key=lambda p: p[0])
        return out

    @lru_cache(maxsize=256)
    def ores(self, chunk):
        rng = rng_of(self.seed, "core", chunk)
        out = []
        for i in range(rng.randint(1, 5)):
            x = chunk * config.TERRAIN_CHUNK + rng.uniform(40, config.TERRAIN_CHUNK - 40)
            if self.in_pad(x, 40) or not self.inside(x, 120):
                continue
            kind = "fuel" if rng.random() < 0.2 else "mat" if rng.random() < 0.45 else "ore"
            out.append((f"{self.planet.id}:cave:{chunk}:{i}", x, kind))
        return out

    @lru_cache(maxsize=256)
    def medkits(self, chunk):
        rng = rng_of(self.seed, "cmedkit", chunk)
        if chunk <= 0 or (chunk != 2 and rng.random() > 0.32):
            return []
        x = chunk * config.TERRAIN_CHUNK + rng.uniform(100, config.TERRAIN_CHUNK - 100)
        if not self.inside(x, 200) or self.in_pad(x, 80):
            return []
        return [(f"{self.planet.id}:cmed:{chunk}", x)]

    @lru_cache(maxsize=256)
    def geodes(self, chunk):
        rng = rng_of(self.seed, "geode", chunk)
        lo, hi = chunk * config.TERRAIN_CHUNK, (chunk + 1) * config.TERRAIN_CHUNK
        out = [(f"{self.planet.id}:geode:f{k}", x) for k, x in enumerate(self.geode_spots) if lo <= x < hi]
        x = lo + rng.uniform(100, 900)
        if chunk > 0 and rng.random() < 0.15 and self.inside(x, 200) and not self.in_pad(x, 80):
            out.append((f"{self.planet.id}:geode:{chunk}", x))
        return out

    @lru_cache(maxsize=256)
    def creatures(self, chunk):
        rng = rng_of(self.seed, "cfauna", chunk)
        out = []
        # Reduced spawn rate: fewer random creatures per chunk (was [3,3,3,1] -> [5,3,2,0])
        for i in range(rng.choices([0, 1, 2, 3], weights=[5, 3, 2, 0])[0]):
            x = chunk * config.TERRAIN_CHUNK + rng.uniform(0, config.TERRAIN_CHUNK)
            if abs(x) < 700 or not self.inside(x, 200):
                continue
            out.append((f"cave{chunk}:{i}", x, "flyer" if rng.random() < 0.4 else "hopper"))
        lo, hi = chunk * config.TERRAIN_CHUNK, (chunk + 1) * config.TERRAIN_CHUNK
        for k, sx in enumerate(self.sigils):           # every sigil has two guardians
            for j, dx in enumerate((-320, 340)):
                if lo <= sx + dx < hi:
                    out.append((f"sguard{k}:{j}", sx + dx, "hopper" if j else "flyer"))
        for j, dx in enumerate((-700, -520, -380)):      # and the vault three
            if lo <= self.vault_x + dx < hi:
                out.append((f"vguard{j}", self.vault_x + dx, "hopper" if j != 1 else "flyer"))
        return out


class CaveScene(SurfaceScene):
    ore_bonus = 2

    def __init__(self, game, planet):
        super().__init__(game, planet)
        self.terrain = CaveTerrain(planet)
        self.danger += 0.8
        self.pilot = Pilot(game, 200, self.terrain.height, self.biome.gravity, self.biome.friction, None)
        self.pilot.ceiling = self.terrain.ceiling
        self.pilot.anchor_fn = self.raycast
        self.camera.follow(self.pilot.x, self.pilot.y, 0, snap=True)
        self._last_cam = (self.camera.x, self.camera.y)
        self.weather = Weather(None, planet.seed)
        self.painter.chunks.clear()       # the cave has its own floor
        self.geode_img = game.assets.sprite("generated/props/crystal/geode.png")
        a = game.assets
        self.vault_imgs = (a.sprite("generated/poi/vault.png"), a.sprite("generated/poi/vault_open.png"))
        self.sigil_img = a.sprite("generated/poi/sigil.png")
        self.drips = []

    @property
    def music(self) -> str:
        return "stronghold"

    def on_enter(self) -> None:
        if self.cleared:
            self.game.banner.show(f"Caves of {self.planet.name}", "The vault stands open. Ore still glitters in the dark.",
                                  3.0)
        else:
            self.game.banner.show(f"Caves of {self.planet.name}",
                                  "Find the three sigils and open the vault at the far end.", 3.5)

    # ---- the dungeon goal ------------------------------------------------------
    @property
    def cleared(self) -> bool:
        return self.planet.id in self.game.state.caves_cleared

    def sigil_id(self, k) -> str:
        return f"{self.planet.id}:sigil:{k}"

    def sigils_held(self) -> int:
        st = self.game.state
        return sum(1 for k in range(3) if self.sigil_id(k) in st.collected)

    def _open_vault(self) -> None:
        from ..systems import materials as M
        g, st = self.game, self.game.state
        st.mark("caves_cleared", self.planet.id)
        st.bump("vaults")
        rng = random.Random(self.terrain.seed)
        b = self.biome.id
        if b in M.MATERIALS:
            M.give(g, b, 8)
        M.give(g, rng.choice([k for k in M.MATERIALS if k != b]), 3)
        mod = roll_mod(rng, min_rarity=2, luck=0.12)
        st.mods.append(mod)
        cr = int(260 * self.danger + 150)
        st.earn(cr)
        x = self.terrain.vault_x
        self.particles.burst(x, self.terrain.height(x) - 100, 60, 340, [(255, 220, 120), (255, 255, 255),
                                                                         (200, 160, 255)], life=(0.5, 1.4),
                             gravity=200)
        g.shake(14)
        g.freeze(0.08)
        g.audio.play("relic", 1.0)
        g.banner.show("The vault opens!", f"{mod['name']}  ·  +{cr} cr", 4.5)
        lore.announce(g, lore.next_log(st, "architect"))
        g.save()

    def darkness(self) -> float:
        return 232.0

    def daylight(self) -> float:
        return 0.0

    def _hints(self) -> None:
        self.game.hint("cave_in", "Caves are dark and treacherous - use your jetpack [W] to reach high ledges. "
                                  "Geodes glow faintly. Exit at the rope.")

    def save_location(self) -> None:
        self.game.state.location = {"kind": "surface", "planet": self.planet.id}

    def interact(self) -> None:
        p = self.pilot
        if abs(p.x) < 200:
            self.game.audio.play("land", 0.5)
            self.game.scenes.pop(fade=True)
            return
        st = self.game.state
        if abs(p.x - self.terrain.vault_x) < 240 and not self.cleared:
            n = self.sigils_held()
            if n >= 3:
                self._open_vault()
            else:
                self.game.audio.play("deny")
                self.game.toasts.add(f"Three empty sockets. Sigils found: {n}/3", (255, 210, 90), 3, icon="vault")
            return
        for chunk in (self.terrain.chunk_of(p.x) - 1, self.terrain.chunk_of(p.x), self.terrain.chunk_of(p.x) + 1):
            for gid, x in self.terrain.geodes(chunk):
                if gid not in st.collected and abs(p.x - x) < 160:
                    self._open_geode(gid, x)
                    return

    def _open_geode(self, gid, x) -> None:
        st = self.game.state
        st.collected.append(gid)
        gy = self.terrain.height(x)
        self.particles.burst(x, gy - 30, 40, 260, [(220, 160, 255), (255, 255, 255), (255, 220, 120)],
                             life=(0.4, 1.0), gravity=500)
        self.game.audio.play("relic", 0.6)
        rng = random.Random(gid)
        msgs = []
        if rng.random() < 0.55:
            mod = roll_mod(rng, luck=0.08)
            st.mods.append(mod)
            msgs.append(mod["name"])
        n = rng.randint(4, 9)
        st.ore += n
        self.game.events.emit("ore_collected", amount=n)
        msgs.append(f"+{n} ore")
        cr = int(120 * self.danger)
        st.earn(cr)
        msgs.append(f"+{cr} cr")
        self.game.banner.show("Geode cracked!", "  ·  ".join(msgs), 3.0)
        if rng.random() < 0.4:
            lore.announce(self.game, lore.next_log(st, "architect"))

    def update(self, dt: float) -> None:
        super().update(dt)
        p = self.pilot
        st = self.game.state
        self.prompt = None
        t = self.terrain
        if p.x > t.end + 40 or p.x < t.left - 40:          # the rock walls at both ends
            p.x = max(t.left - 40, min(t.end + 40, p.x))
            p.vx = 0
        for k, sx in enumerate(t.sigils):
            if self.sigil_id(k) not in st.collected and abs(p.x - sx) < 70 and abs(p.y - (t.height(sx) - 60)) < 170:
                st.collected.append(self.sigil_id(k))
                self.game.audio.play("relic", 0.6)
                self.particles.burst(sx, t.height(sx) - 70, 30, 220, [(255, 214, 90), (255, 255, 255)],
                                     life=(0.3, 0.9), gravity=200)
                n = self.sigils_held()
                self.game.toasts.add(f"Sigil {n}/3" + ("  ·  the vault will open" if n == 3 else ""),
                                     (255, 214, 90), 3, icon="vault")
        if abs(p.x) < 200:
            self.prompt = ("[E] Climb back to the surface", (150, 255, 170))
        elif abs(p.x - t.vault_x) < 240 and not self.cleared:
            self.prompt = (f"[E] Open the vault  ({self.sigils_held()}/3 sigils)", (255, 214, 90))
        else:
            for chunk in (self.terrain.chunk_of(p.x) - 1, self.terrain.chunk_of(p.x), self.terrain.chunk_of(p.x) + 1):
                for gid, x in self.terrain.geodes(chunk):
                    if gid not in st.collected and abs(p.x - x) < 160:
                        self.prompt = ("[E] Crack the geode", (220, 170, 255))
        if random.random() < dt * 3:   # dripping water from the ceiling
            x = p.x + random.uniform(-700, 700)
            self.drips.append([x, self.terrain.ceiling(x), 0.0])
        for d in self.drips:
            d[2] += 900 * dt
            d[1] += d[2] * dt
        self.drips = [d for d in self.drips if d[1] < self.terrain.height(d[0])]

    # ------------------------------------------------------------------
    def draw(self, surf) -> None:
        cam = self.camera
        ox, oy = cam.ox, cam.oy
        b = self.biome
        back = _mix(b.ground_dark, (0, 0, 0), 0.55)
        surf.fill(back)
        self._draw_backwall(surf, ox, oy)
        self._draw_props(surf, ox, oy, front=False)
        self.painter.draw_ground(surf, ox, oy)
        self._draw_ceiling(surf, ox, oy)
        self._draw_exit(surf, ox, oy)
        self._draw_vault(surf, ox, oy)
        self._draw_geodes(surf, ox, oy)
        self._draw_ores(surf, ox, oy)
        self._draw_medkits(surf, ox, oy)
        for c in self.creatures.values():
            if -100 < c.x - ox < config.SCREEN_W + 100:
                c.draw(surf, ox, oy)
        if self.dead_t < 0:
            self.pilot.draw(surf, ox, oy)
        for bx, by, vx, _l, power, _hit in self.bolts:
            sx, sy = bx - ox, by - oy
            pygame.draw.line(surf, (140, 230, 255), (sx, sy), (sx - vx * 0.02, sy), 4 if power < 2 else 9)
            pygame.draw.circle(surf, (255, 255, 255), (sx, sy), 3 if power < 2 else 7)
        for x, y, _v in self.drips:
            pygame.draw.line(surf, (150, 190, 230), (x - ox, y - oy), (x - ox, y - oy - 8), 2)
        self.particles.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        self._apply_cave_lighting(surf, ox, oy)
        self.floaters.draw(surf, lambda pt: (pt[0] - ox, pt[1] - oy))
        self._draw_hud(surf)

    def _draw_backwall(self, surf, ox, oy) -> None:
        b = self.biome
        for layer, (par, k) in enumerate(((0.25, 0.75), (0.5, 0.6))):
            colr = _mix(b.ground_dark, (0, 0, 0), k)
            pts = [(0, 0)]
            for sx in range(0, config.SCREEN_W + 41, 40):
                wx = sx + ox * par
                pts.append((sx, 120 + fbm(wx / 300.0, self.terrain.seed + layer * 7, 3) * 120 - oy * par * 0.3))
            pts.append((config.SCREEN_W + 40, 0))
            pygame.draw.polygon(surf, colr, pts)
            pts2 = [(0, config.SCREEN_H)]
            for sx in range(0, config.SCREEN_W + 41, 40):
                wx = sx + ox * par
                pts2.append((sx, config.SCREEN_H - 140 - fbm(wx / 300.0, self.terrain.seed + layer * 13, 3) * 110
                             - oy * par * 0.3))
            pts2.append((config.SCREEN_W + 40, config.SCREEN_H))
            pygame.draw.polygon(surf, colr, pts2)

    def _draw_ceiling(self, surf, ox, oy) -> None:
        b = self.biome
        t = self.terrain
        step = config.TERRAIN_STEP
        x0 = int((ox // step) * step) - step
        pts = []
        for wx in range(x0, int(ox + config.SCREEN_W + step * 2), step):
            pts.append((wx - ox, t.ceiling(wx) - oy))
        pygame.draw.polygon(surf, _mix(b.ground, b.ground_dark, 0.4), pts + [(pts[-1][0], -10), (pts[0][0], -10)])
        pygame.draw.polygon(surf, b.ground_dark, [(x, y - 50) for x, y in pts] + [(pts[-1][0], -10), (pts[0][0], -10)])
        pygame.draw.lines(surf, _mix(b.ground_top, b.ground_dark, 0.5), False, pts, 6)
        # stalactites
        for wx in range(int(ox // 60) * 60, int(ox + config.SCREEN_W + 60), 60):
            h = int_hash(wx // 60, t.seed + 17)
            if h < 0.45:
                cy = t.ceiling(wx) - oy
                ln = 20 + h * 120
                w = 8 + h * 18
                pygame.draw.polygon(surf, _mix(b.ground, b.ground_dark, 0.3),
                                    [(wx - ox - w, cy - 2), (wx - ox + w, cy - 2), (wx - ox, cy + ln)])
                pygame.draw.line(surf, _mix(b.ground_top, b.ground, 0.5), (wx - ox - w * 0.4, cy), (wx - ox, cy + ln), 2)

    def _draw_exit(self, surf, ox, oy) -> None:
        t = self.terrain
        x = 0 - ox
        top = t.ceiling(0) - oy
        gy = t.height(0) - oy
        light = pygame.Surface((120, max(1, int(gy - top) + 40)), pygame.SRCALPHA)
        for i in range(light.get_width() // 2):
            a = int(60 * (1 - i / (light.get_width() / 2)))
            pygame.draw.line(light, (255, 240, 200, a), (60 - i, 0), (60 - i, light.get_height()))
            pygame.draw.line(light, (255, 240, 200, a), (60 + i, 0), (60 + i, light.get_height()))
        surf.blit(light, (x - 60, top - 40))
        pygame.draw.line(surf, (150, 120, 90), (x, top - 40), (x, gy - 10), 3)
        for k in range(int((gy - top) // 26)):
            pygame.draw.line(surf, (190, 160, 120), (x - 6, top + k * 26), (x + 6, top + k * 26 + 4), 2)

    def _draw_vault(self, surf, ox, oy) -> None:
        t = self.terrain
        st = self.game.state
        x = t.vault_x
        if -400 < x - ox < config.SCREEN_W + 400:
            img = self.vault_imgs[1 if self.cleared else 0]
            r = img.get_rect(midbottom=(x - ox, t.height(x) - oy + 8))
            surf.blit(img, r)
            small = self._small_sigil()
            A = config.ART_SCALE
            for k in range(3):
                if self.sigil_id(k) in st.collected:
                    surf.blit(small, small.get_rect(center=(r.x + (26 + k * 16) * A, r.y + 16 * A)))
        for k, sx in enumerate(t.sigils):
            if self.sigil_id(k) in st.collected or not (-100 < sx - ox < config.SCREEN_W + 100):
                continue
            bob = int(math.sin(self.clock * 2.5 + k) * 6) // 2 * 2
            surf.blit(self.sigil_img, self.sigil_img.get_rect(center=(sx - ox, t.height(sx) - oy - 70 + bob)))

    def _small_sigil(self):
        if getattr(self, "_ssig", None) is None:
            w, h = self.sigil_img.get_size()
            self._ssig = pygame.transform.scale(self.sigil_img, (w // 2, h // 2))
        return self._ssig

    def map_marks(self) -> list:
        st = self.game.state
        marks = [(0, "cave", False), (self.terrain.vault_x, "vault", self.cleared)]
        for k, sx in enumerate(self.terrain.sigils):
            marks.append((sx, "star", self.sigil_id(k) in st.collected))
        return marks

    def _draw_map(self, surf) -> None:
        t = self.terrain
        title = "vault open" if self.cleared else f"sigils {self.sigils_held()}/3"
        from ..ui import hud
        hud.strip_map(surf, self.map_marks(), self.pilot.x, t.left, t.end, title)

    def _draw_geodes(self, surf, ox, oy) -> None:
        st = self.game.state
        c0 = self.terrain.chunk_of(ox)
        for chunk in range(c0 - 1, c0 + 3):
            for gid, x in self.terrain.geodes(chunk):
                if gid in st.collected or not (-100 < x - ox < config.SCREEN_W + 100):
                    continue
                gy = self.terrain.height(x) - oy
                bob = math.sin(self.clock * 2 + x) * 2
                surf.blit(self.geode_img, self.geode_img.get_rect(midbottom=(x - ox, gy + 8 + bob)))

    def _apply_cave_lighting(self, surf, ox, oy) -> None:
        L = self.lighting
        p = self.pilot
        L.add(p.x - ox, p.y - oy - 50, 320, (255, 230, 180), 1.0)
        L.add(p.x - ox + p.facing * 170, p.y - oy - 50, 220, None, 0.8)
        L.add(0 - ox, (self.terrain.height(0) + self.terrain.ceiling(0)) / 2 - oy, 260, (255, 240, 200), 0.9)
        t = self.terrain
        st = self.game.state
        c0 = t.chunk_of(ox)
        for chunk in range(c0 - 1, c0 + 3):
            for x, idx, scale, _f in t.props(chunk):
                h = self.biome.props[idx].height * scale
                L.add(x - ox, t.height(x) - oy - h * 0.5, 110 + h * 0.6, self.biome.ore_color, 0.75)
            for uid, x, kind in t.ores(chunk):
                if uid not in st.collected:
                    L.add(x - ox, t.height(x) - oy - 20, 120, (255, 200, 60) if kind == "fuel" else self.biome.ore_color,
                          0.8)
            for uid, x in t.medkits(chunk):
                if uid not in st.collected:
                    L.add(x - ox, t.height(x) - oy - 26, 150, (100, 255, 160), 0.85)
            for gid, x in t.geodes(chunk):
                if gid not in st.collected:
                    L.add(x - ox, t.height(x) - oy - 30, 170, (220, 160, 255), 0.9)
        for k, sx in enumerate(t.sigils):
            if self.sigil_id(k) not in st.collected:
                L.add(sx - ox, t.height(sx) - oy - 70, 220, (255, 214, 90), 1.0)
        L.add(t.vault_x - ox, t.height(t.vault_x) - oy - 120, 320, (255, 200, 120) if self.cleared else (200, 170, 255),
              0.9)
        for b in self.bolts:
            L.add(b[0] - ox, b[1] - oy, 100, (140, 230, 255), 0.7)
        for c in self.creatures.values():
            if -100 < c.x - ox < config.SCREEN_W + 100:
                L.add(c.x - ox, c.y - oy - 30, 60, (255, 90, 90), 0.35)   # glowing eyes
        L.apply(surf, self.darkness(), (2, 2, 8))
