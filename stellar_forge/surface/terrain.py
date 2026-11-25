"""Infinite, seeded side-view terrain for a planet surface."""
from __future__ import annotations

import math
from functools import lru_cache

from .. import config
from ..world.noise import fbm, ridged
from ..world.rng import int_hash, rng_of


_TREES = ("tree", "pine", "fungus", "cactus", "basalt", "kelp", "antenna", "cluster2")
_LOGS = ("log", "broken")


def prop_role(prop) -> str:
    name = (prop.sprite or prop.kind).rsplit("/", 1)[-1].lower()
    if prop.front and "log" not in name:
        return "shrub"
    if any(k in name for k in _LOGS):
        return "log"
    if any(k in name for k in _TREES) or prop.kind in ("spire", "mushroom"):
        return "tree"
    return "shrub"


def _smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


class Terrain:
    def __init__(self, planet, seed: int):
        self.planet = planet
        self.biome = planet.biome
        self.seed = seed & 0x7FFFFFFF
        self.amp = 330 * self.biome.roughness
        rng = rng_of(seed, "layout")
        self.stronghold_x = None
        if planet.stronghold:
            side = rng.choice([-1, 1])
            self.stronghold_x = side * rng.uniform(config.STRONGHOLD_MIN_DIST, config.STRONGHOLD_MAX_DIST)
        self.liquid = self.biome.liquid if self.biome.liquid_level > 0 else None
        self.liquid_y = self.amp * (1 - 2 * self.biome.liquid_level) if self.liquid else float("inf")
        # flat pads: rocket at 0, stronghold entrance, cave mouth, boss arena
        self.pads = [(0.0, 420.0)]
        if self.stronghold_x is not None:
            self.pads.append((self.stronghold_x, 520.0))
        frng = rng_of(seed, "features")       # separate stream keeps old worlds identical
        taken = [0.0] + ([self.stronghold_x] if self.stronghold_x is not None else [])

        def free_spot(lo, hi):
            for _ in range(20):
                x = frng.choice([-1, 1]) * frng.uniform(lo, hi)
                if all(abs(x - t) > 1600 for t in taken):
                    taken.append(x)
                    return x
            return None
        self.cave_x = free_spot(1300, 4500) if getattr(planet, "cave", False) else None
        self.lair_x = free_spot(3600, 7200) if getattr(planet, "lair", False) else None
        if self.cave_x is not None:
            self.pads.append((self.cave_x, 360.0))
        if self.lair_x is not None:
            self.pads.append((self.lair_x, 1150.0))
        # points of interest: camps, pods, ruins, material veins (own rng stream)
        from ..systems import poi as poi_sys
        self.pois = []
        if self.biome.id in ("forest", "desert", "ice", "volcanic", "crystal", "toxic", "ocean", "barren"):
            used = [t for t in taken] + ([self.cave_x] if self.cave_x is not None else []) + \
                ([self.lair_x] if self.lair_x is not None else [])
            if self.lair_x is not None:
                used += [self.lair_x - 1200, self.lair_x + 1200]
            self.pois = poi_sys.generate(self, planet, rng_of(seed, "poi"), used)
            for p in self.pois:
                self.pads.append((float(p["x"]), poi_sys.PAD[p["kind"]]))
                if p.get("crate_x") is not None:
                    self.pads.append((float(p["crate_x"]), poi_sys.PAD["crate"]))
        planet._pois = self.pois
        if getattr(planet, "name", "") == "Earth-Prime":          # level ground for the homecoming town
            self.pads.append((1150.0, 560.0))
        self._pad_h = {}
        for px, _w in self.pads:
            h = self._raw(px)
            if self.liquid:
                h = min(h, self.liquid_y - 70)
            self._pad_h[px] = h
        self._cache = {}

    def _raw(self, x: float) -> float:
        s = self.seed
        y = fbm(x / 1300.0, s, 4) * self.amp
        y += fbm(x / 320.0, s + 77, 3) * self.amp * 0.16
        if self.biome.id in ("volcanic", "crystal", "ice"):
            y -= ridged(x / 1400.0, s + 5) * self.amp * 0.6
        return y

    def height(self, x: float) -> float:
        """Ground y at world x (y grows downward)."""
        key = int(x // 4)
        h = self._cache.get(key)
        if h is None:
            h = self._raw(key * 4)
            for px, w in self.pads:
                d = abs(key * 4 - px)
                if d < w + 380:
                    k = 1 - _smoothstep(w, w + 380, d)
                    h = h + (self._pad_h[px] - h) * k
            h = round(h / config.ART_SCALE) * config.ART_SCALE     # snap to the pixel grid
            if len(self._cache) > 60000:
                self._cache.clear()
            self._cache[key] = h
        return h

    def slope(self, x: float) -> float:
        return (self.height(x + 6) - self.height(x - 6)) / 12

    def in_pad(self, x: float, margin: float = 0) -> bool:
        return any(abs(x - px) < w + margin for px, w in self.pads)

    # --- chunked content ---------------------------------------------------
    def chunk_of(self, x: float) -> int:
        return math.floor(x / config.TERRAIN_CHUNK)

    # --- scenery ---------------------------------------------------------------
    def roles(self) -> dict:
        """Biome prop indices grouped by what they are: tall 'tree's, fallen 'log's, small 'shrub's."""
        r = getattr(self, "_roles", None)
        if r is None:
            r = {"tree": [], "log": [], "shrub": []}
            for i, p in enumerate(self.biome.props):
                r[prop_role(p)].append(i)
            self._roles = r
        return r

    def growth(self, x: float) -> float:
        """0..1 vegetation density: groves where it is high, clearings where it is low."""
        return max(0.0, min(1.0, 0.5 + 0.9 * fbm(x / 2600.0, self.seed + 313, 2)))

    def flat_enough(self, x: float, half: float, rise: float) -> bool:
        hs = [self.height(x + d) for d in (-half, 0, half)]
        return max(hs) - min(hs) <= rise

    def _pick(self, rng, ids):
        props = self.biome.props
        return rng.choices(ids, weights=[props[i].weight for i in ids])[0]

    @lru_cache(maxsize=256)
    def props(self, chunk: int) -> list:
        """[(x, prop_index, scale, flip)] for a chunk, sorted by x.

        Walks the chunk left to right: trees grow in groves (with shrubs at their
        feet), clearings get the odd rock or bush, fallen logs only lie on gentle
        ground, and nothing piles on top of anything else."""
        rng = rng_of(self.seed, "props", chunk)
        out = []
        if not self.biome.props:
            return out
        roles = self.roles()
        dens = self.biome.prop_density
        x = chunk * config.TERRAIN_CHUNK + rng.uniform(0, 140)
        end = (chunk + 1) * config.TERRAIN_CHUNK
        last_tree = chunk * config.TERRAIN_CHUNK - 75    # keeps trees apart across chunk edges too
        while x < end:
            g = self.growth(x)
            ok = not self.in_pad(x, 80) and self.height(x) <= self.liquid_y - 4
            if ok:
                r = rng.random()
                p_tree = 0.15 + 0.6 * g
                p_log = 0.08 + 0.06 * g
                if roles["tree"] and r < p_tree and x - last_tree > 150 and x < end - 75 and self.flat_enough(x, 30, 40):
                    idx = self._pick(rng, roles["tree"])
                    out.append((x, idx, 1.0, rng.random() < 0.5))
                    last_tree = x
                    if roles["shrub"] and rng.random() < 0.6 * g:          # undergrowth at the trunk
                        sx = x + rng.choice([-1, 1]) * rng.uniform(50, 90)
                        if not self.in_pad(sx, 60):
                            out.append((sx, self._pick(rng, roles["shrub"]), 1.0, rng.random() < 0.5))
                elif roles["log"] and r < p_tree + p_log and self.flat_enough(x, 70, 14):
                    out.append((x, self._pick(rng, roles["log"]), 1.0, rng.random() < 0.5))
                    x += 120                                                # logs need room
                elif roles["shrub"] and r < p_tree + p_log + 0.25 + 0.3 * g:
                    out.append((x, self._pick(rng, roles["shrub"]), 1.0, rng.random() < 0.5))
            # denser groves step in shorter strides
            x += rng.uniform(110, 210) * (1.6 - 0.9 * g) / max(0.4, dens)
        out.sort(key=lambda p: p[0])
        return out

    @lru_cache(maxsize=256)
    def back_props(self, chunk: int) -> list:
        """A thinner, darker row of trees behind the walkable line, for depth."""
        rng = rng_of(self.seed, "backprops", chunk)
        trees = self.roles()["tree"]
        out = []
        if not trees:
            return out
        x = chunk * config.TERRAIN_CHUNK + rng.uniform(0, 200)
        end = (chunk + 1) * config.TERRAIN_CHUNK
        while x < end:
            g = self.growth(x + 700)
            if rng.random() < 0.2 + 0.6 * g and not self.in_pad(x, 0) and self.height(x) <= self.liquid_y - 4:
                out.append((x, self._pick(rng, trees), 1.0, rng.random() < 0.5))
            x += rng.uniform(160, 300) * (1.5 - 0.7 * g)
        return out

    @lru_cache(maxsize=256)
    def ores(self, chunk: int) -> list:
        """[(id, x, kind)] mineral nodes; kind 'ore' or 'fuel'."""
        rng = rng_of(self.seed, "ore", chunk)
        out = []
        for i in range(rng.randint(0, 3)):
            x = chunk * config.TERRAIN_CHUNK + rng.uniform(40, config.TERRAIN_CHUNK - 40)
            if self.in_pad(x, 40) or self.height(x) > self.liquid_y - 4:
                continue
            kind = "fuel" if rng.random() < 0.3 else "ore"
            if kind == "ore" and self.pois and int_hash(chunk * 7 + i, self.seed + 4242) < 0.4:
                kind = "mat"           # a small vein of this world's material
            out.append((f"{self.planet.id}:{chunk}:{i}", x, kind))
        return out

    @lru_cache(maxsize=256)
    def medkits(self, chunk: int) -> list:
        """[(id, x)] rare Nano-Medkit pods resting on solid ground."""
        rng = rng_of(self.seed, "medkit", chunk)
        if rng.random() > 0.24:
            return []
        x = chunk * config.TERRAIN_CHUNK + rng.uniform(80, config.TERRAIN_CHUNK - 80)
        if self.in_pad(x, 60) or self.height(x) > self.liquid_y - 4:
            return []
        return [(f"{self.planet.id}:med:{chunk}", x)]

    @lru_cache(maxsize=256)
    def creatures(self, chunk: int) -> list:
        rng = rng_of(self.seed, "fauna", chunk)
        out = []
        for i in range(rng.choices([0, 1, 2, 3], weights=[3, 4, 2, 1])[0]):
            x = chunk * config.TERRAIN_CHUNK + rng.uniform(0, config.TERRAIN_CHUNK)
            if self.in_pad(x, 650):
                continue
            out.append((f"{chunk}:{i}", x, "flyer" if rng.random() < 0.35 else "hopper"))
        return out

    def speck(self, col: int) -> float:
        return int_hash(col, self.seed + 991)
