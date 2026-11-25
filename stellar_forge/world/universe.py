"""The infinite universe: sectors are generated on demand from the world
seed, kept in a small LRU cache, and rebuilt identically when revisited.
"""
from __future__ import annotations

import math
from collections import OrderedDict

from pygame.math import Vector2

from .. import config
from .rng import rng_of
from .sector import Sector


class Universe:
    CACHE_SIZE = 600              # big enough for the zoomed-out galaxy map (19x19) plus the flight area

    def __init__(self, seed: int, destroyed: list | None = None, danger_bonus: float = 0.0, earth: bool = False):
        self.seed = seed
        self.earth = earth            # True once the Forge has rebuilt Earth-Prime
        self.destroyed = set(destroyed or [])
        self.danger_bonus = danger_bonus
        self._cache: OrderedDict[tuple, Sector] = OrderedDict()
        self.relic_sites = self._place_relic_sites()
        self.shard_sites = self._place_shard_sites()

    def rebuild_home(self) -> None:
        """Regenerate Haven (e.g. after Earth-Prime is reborn)."""
        self._cache.pop((0, 0), None)

    def danger_at(self, sx: int, sy: int) -> float:
        """How hostile a sector is: grows with distance from home (and New Game+)."""
        return 1.0 + 0.45 * math.hypot(sx, sy) + self.danger_bonus

    def _place_relic_sites(self) -> dict:
        """Guarantee every campaign is winnable: each Key has a home within
        two sectors of the start (more strongholds exist everywhere else)."""
        rng = rng_of(self.seed, "relic-sites")
        ring = [(x, y) for x in range(-2, 3) for y in range(-2, 3)
                if (x, y) != (0, 0) and max(abs(x), abs(y)) >= 1]
        rng.shuffle(ring)
        # make the first Key reachable early: keep one site in ring 1
        ring.sort(key=lambda c: max(abs(c[0]), abs(c[1])) + rng.random() * 1.5)
        return {ring[0]: "forest", ring[1]: "desert", ring[2]: "ice"}

    def _place_shard_sites(self) -> dict:
        """Act II: one vault per Forge Shard, three to five sectors out."""
        from ..core.game_state import SHARD_BIOMES
        rng = rng_of(self.seed, "shard-sites")
        ring = [(x, y) for x in range(-5, 6) for y in range(-5, 6)
                if 3 <= max(abs(x), abs(y)) <= 5 and (x, y) not in self.relic_sites]
        rng.shuffle(ring)
        sites, used_dirs = {}, []
        for c in ring:  # spread them around the compass so the hunt is a tour
            ang = math.atan2(c[1], c[0])
            if all(abs((ang - a + math.pi) % math.tau - math.pi) > 0.9 for a in used_dirs):
                sites[c] = SHARD_BIOMES[len(sites)]
                used_dirs.append(ang)
                if len(sites) == len(SHARD_BIOMES):
                    break
        for c in ring:  # fallback if the angular spread could not fit all five
            if len(sites) == len(SHARD_BIOMES):
                break
            if c not in sites:
                sites[c] = SHARD_BIOMES[len(sites)]
        return sites

    def shard_planet(self, biome: str):
        for site, b in self.shard_sites.items():
            if b == biome:
                return self.sector(*site).shard_planet
        return None

    # ------------------------------------------------------------------
    @staticmethod
    def sector_coords(p) -> tuple[int, int]:
        return (math.floor(p[0] / config.SECTOR_SIZE), math.floor(p[1] / config.SECTOR_SIZE))

    def sector(self, sx: int, sy: int) -> Sector:
        key = (sx, sy)
        sec = self._cache.get(key)
        if sec is None:
            sec = Sector(self, sx, sy)
            self._cache[key] = sec
            if len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(key)
        return sec

    def peek(self, sx: int, sy: int) -> Sector | None:
        """The sector if it has already been generated, without generating it."""
        return self._cache.get((sx, sy))

    def active_sectors(self, p, radius: int = config.SECTOR_LOAD_RADIUS) -> list[Sector]:
        cx, cy = self.sector_coords(p)
        return [self.sector(cx + dx, cy + dy)
                for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)]

    def current_system(self, p) -> Sector | None:
        """The star system whose gravity well ``p`` is in, if any."""
        best, best_d = None, float("inf")
        for sec in self.active_sectors(p):
            if not sec.has_system:
                continue
            d = (Vector2(p) - sec.system_center).length()
            if d < sec.system_radius + 4000 and d < best_d:
                best, best_d = sec, d
        return best

    def find_body(self, uid: str):
        """Look up any body by id ("sx,sy:..."), generating its sector."""
        try:
            sx, sy = (int(v) for v in uid.split(":")[0].split(","))
        except ValueError:
            return None
        sec = self.sector(sx, sy)
        for b in sec.bodies:
            if b.id == uid:
                return b
        return None

    def mark_destroyed(self, uid: str) -> None:
        self.destroyed.add(uid)

    def nearest_stronghold(self, p, biomes, exclude, max_radius: int = 3):
        """Search outward for an unlooted stronghold on a planet of ``biomes``."""
        cx, cy = self.sector_coords(p)
        best, best_d = None, float("inf")
        for r in range(max_radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    sec = self.sector(cx + dx, cy + dy)
                    for pl in sec.planets:
                        if pl.stronghold and pl.biome_id in biomes and pl.id not in exclude:
                            d = (pl.center if pl.parent is None else sec.system_center).distance_to(p)
                            if d < best_d:
                                best, best_d = pl, d
            if best is not None and r >= 1:
                break
        return best
