"""Generation of one sector of the infinite universe."""
from __future__ import annotations

import math

from pygame.math import Vector2

from .. import config
from ..entities.bodies import (Asteroid, BlackHole, Derelict, ForgeGate, Nebula, Planet, Pulsar, Star,
                               Station, Wormhole)
from . import names
from .biomes import choose_biome
from .planet_model import MODEL
from .rng import rng_of, seed_of

SPECTRAL = [  # class, weight, colour, radius range, luminosity
    ("M", 3.0, (255, 140, 90), (300, 420), 0.45),
    ("K", 2.5, (255, 190, 120), (380, 500), 0.75),
    ("G", 2.5, (255, 240, 170), (440, 560), 1.0),
    ("F", 1.5, (255, 255, 235), (480, 620), 1.5),
    ("A", 0.8, (210, 230, 255), (540, 700), 2.2),
    ("B", 0.4, (160, 190, 255), (650, 850), 3.5),
]
NEBULA_COLORS = [(120, 60, 200), (60, 120, 220), (200, 60, 120), (60, 180, 140), (220, 120, 60)]


class Sector:
    def __init__(self, universe, sx: int, sy: int):
        self.universe = universe
        self.sx, self.sy = sx, sy
        self.key = f"{sx},{sy}"
        self.origin = Vector2(sx * config.SECTOR_SIZE, sy * config.SECTOR_SIZE)
        self.star: Star | None = None
        self.system_center = self.origin + Vector2(config.SECTOR_SIZE / 2, config.SECTOR_SIZE / 2)
        self.system_radius = 0.0
        self.name = ""
        self.bodies: list = []
        self.planets: list[Planet] = []
        self.stations: list[Station] = []
        self.asteroids: list[Asteroid] = []
        self.hazards: list = []          # black holes, pulsars
        self.wormholes: list[Wormhole] = []
        self.nebulae: list[Nebula] = []
        self.danger = universe.danger_at(sx, sy)
        self.shard_planet: Planet | None = None
        self.forge: ForgeGate | None = None
        self._generate()

    # ------------------------------------------------------------------
    def _generate(self) -> None:
        u = self.universe
        rng = rng_of(u.seed, "sector", self.sx, self.sy)
        home = (self.sx, self.sy) == (0, 0)
        forced_relic = u.relic_sites.get((self.sx, self.sy))
        forced_shard = u.shard_sites.get((self.sx, self.sy))
        has_system = home or forced_relic or forced_shard or rng.random() < config.SYSTEM_CHANCE

        if has_system:
            self._make_system(rng, home, forced_relic or forced_shard, shard=bool(forced_shard))
        else:
            self.name = f"Deep Space {self.key}"
            self._make_deep_space(rng)

        if rng.random() < (0.25 if has_system else 0.55):
            c = self.origin + Vector2(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85)) * config.SECTOR_SIZE
            self.nebulae.append(Nebula(f"{self.key}:neb", c, rng.uniform(3000, 7000),
                                       rng.choice(NEBULA_COLORS), seed_of(u.seed, self.key, "neb")))
        if not home and rng.random() < (0.08 if has_system else 0.22):
            self._make_wormhole(rng)
        self.derelicts: list[Derelict] = []
        drng = rng_of(u.seed, "derelict", self.sx, self.sy)   # own stream: older seeds stay identical
        if not home and drng.random() < (0.22 if has_system else 0.35):
            did = f"{self.key}:der"
            d = Derelict(did, names.derelict_name(drng), seed_of(u.seed, did))
            ang = drng.uniform(0, math.tau)
            dist = (self.system_radius + 2500) if has_system else drng.uniform(3000, 12000)
            d.center = self.system_center + Vector2(math.cos(ang), math.sin(ang)) * dist
            self.derelicts.append(d)
            self.bodies.append(d)

    def _make_system(self, rng, home: bool, forced_relic: str | None, shard: bool = False) -> None:
        u = self.universe
        jitter = config.SECTOR_SIZE * 0.08
        self.system_center = self.system_center + Vector2(rng.uniform(-jitter, jitter),
                                                          rng.uniform(-jitter, jitter))
        if home:
            spec = SPECTRAL[2]
        else:
            spec = rng.choices(SPECTRAL, weights=[s[1] for s in SPECTRAL])[0]
        cls, _w, color, rr, lum = spec
        sname = "Haven" if home else names.star_name(rng)
        self.name = sname
        star_r = rng.uniform(*rr)
        star = Star(f"{self.key}:star", sname, star_r, mu=star_r ** 2 * 170, color=color,
                    luminosity=lum, spectral=cls)
        star.center = Vector2(self.system_center)
        self.star = star
        self.bodies.append(star)

        n_planets = rng.randint(3, 7)
        orbit = star_r + rng.uniform(1600, 2400)
        relic_index = rng.randrange(min(n_planets, 3)) if forced_relic else -1
        for i in range(n_planets):
            if i >= 3 and orbit > 14000:
                break
            uid = f"{self.key}:{i}"
            dist01 = min(1.0, (orbit - 2000) / 12000)
            size, _density = MODEL.sample(dist01, rng)
            temperature = max(0.0, min(1.0, math.sqrt(lum) * 3300 / orbit))
            biome = choose_biome(temperature, size, rng)
            if home and i == 0:
                biome, size = "forest", 0.5
            if i == relic_index:
                biome, size = forced_relic, max(0.35, min(size, 0.7))
            radius = (75 + size * 210) if biome != "gas" else rng.uniform(260, 340)
            g_surface = rng.uniform(55, 95) * (1.2 if biome == "gas" else 1.0)
            name = "Aster" if (home and i == 0) else names.planet_name(sname, i, rng)
            stronghold = False
            if biome in ("desert", "ice", "forest"):
                stronghold = rng.random() < 0.35
            elif biome not in ("gas",):
                stronghold = rng.random() < 0.15
            if i == relic_index:
                stronghold = True
            if home and i == 0:
                stronghold = False
            planet = Planet(uid, name, radius, g_surface * radius ** 2, biome,
                            seed_of(u.seed, uid), rings=(biome == "gas" and rng.random() < 0.6)
                            or rng.random() < 0.08, stronghold=stronghold, sector=(self.sx, self.sy))
            if shard and i == relic_index:
                planet.shard = biome
                self.shard_planet = planet
            omega = math.sqrt(star.mu / orbit ** 3) * config.ORBIT_TIME_SCALE
            planet.set_orbit(star, orbit, omega, rng.uniform(0, math.tau))
            self.planets.append(planet)
            self.bodies.append(planet)
            # moons
            if radius > 140 and rng.random() < 0.55:
                for m in range(rng.randint(1, 2)):
                    mid = f"{uid}m{m}"
                    mr = rng.uniform(32, 55)
                    mbiome = rng.choice(["barren", "barren", "ice", "crystal", "volcanic"])
                    moon = Planet(mid, f"{name}-{chr(97 + m)}", mr, rng.uniform(40, 60) * mr ** 2,
                                  mbiome, seed_of(u.seed, mid), is_moon=True,
                                  stronghold=rng.random() < 0.1, sector=(self.sx, self.sy))
                    mo = radius * rng.uniform(2.6, 3.6) + m * 260
                    moon.set_orbit(planet, mo, rng.uniform(0.05, 0.11) * rng.choice([-1, 1]),
                                   rng.uniform(0, math.tau))
                    planet.moons.append(moon)
                    self.planets.append(moon)
                    self.bodies.append(moon)
            gap = rng.uniform(1700, 2800) + radius * 2
            # asteroid belt in a gap
            if not home and rng.random() < 0.18:
                self._make_belt(rng, star, orbit + gap * 0.5)
                gap += 800
            orbit += gap
        self.system_radius = orbit + 1500

        # stations
        if home or rng.random() < 0.55:
            host = self.planets[0] if home else rng.choice([p for p in self.planets if not p.is_moon])
            sid = f"{self.key}:st"
            st = Station(sid, "Haven Station" if home else names.station_name(rng), seed_of(u.seed, sid))
            st.set_orbit(host, host.radius * 2.6 + 260, 0.06, rng.uniform(0, math.tau))
            self.stations.append(st)
            self.bodies.append(st)
        if home:
            outer = [p for p in self.planets if not p.is_moon]
            self._make_belt(rng, star, (outer[0].orbit_r + outer[1].orbit_r) / 2, count=50)
            self.forge = ForgeGate(f"{self.key}:forge", "The Stellar Forge")
            self.forge.set_orbit(outer[0], 1400, 0.025, 2.4)
            self.bodies.append(self.forge)
            if u.earth:   # the true ending: Earth-Prime orbits Haven again
                uid = f"{self.key}:earth"
                earth = Planet(uid, "Earth-Prime", 230, 80 * 230 ** 2, "forest", seed_of(u.seed, uid),
                               sector=(self.sx, self.sy))
                earth.lair = earth.cave = False
                eo = self.system_radius + 600
                earth.set_orbit(star, eo, math.sqrt(star.mu / eo ** 3) * config.ORBIT_TIME_SCALE, 1.0)
                self.system_radius = eo + 1500
                self.planets.append(earth)
                self.bodies.append(earth)

    def _make_belt(self, rng, star, radius, count=None) -> None:
        count = count or rng.randint(45, 80)
        omega = math.sqrt(star.mu / radius ** 3) * config.ORBIT_TIME_SCALE
        for i in range(count):
            aid = f"{self.key}:a{len(self.asteroids)}"
            if aid in self.universe.destroyed:
                continue
            a = Asteroid(aid, rng.uniform(14, 52), seed_of(self.universe.seed, aid), ore=rng.random() < 0.3)
            a.set_orbit(star, radius + rng.uniform(-650, 650), omega * rng.uniform(0.95, 1.05),
                        i / count * math.tau + rng.uniform(-0.04, 0.04))
            self.asteroids.append(a)
            self.bodies.append(a)

    def _make_deep_space(self, rng) -> None:
        roll = rng.random()
        c = self.system_center + Vector2(rng.uniform(-8000, 8000), rng.uniform(-8000, 8000))
        if roll < 0.16:
            bh = BlackHole(f"{self.key}:bh", f"Abyss {self.key}", rng.uniform(220, 320), 0)
            bh.mu = rng.uniform(2.2e8, 3.2e8)
            bh.center = c
            self.hazards.append(bh)
            self.bodies.append(bh)
            self.name = bh.name
        elif roll < 0.3:
            pul = Pulsar(f"{self.key}:pul", f"Pulsar {names.star_name(rng)}", 90, 4.5e7,
                         seed_of(self.universe.seed, self.key, "pul"))
            pul.center = c
            self.hazards.append(pul)
            self.bodies.append(pul)
            self.name = pul.name
        # drifting rocks
        if rng.random() < 0.5:
            for i in range(rng.randint(12, 30)):
                aid = f"{self.key}:a{i}"
                if aid in self.universe.destroyed:
                    continue
                a = Asteroid(aid, rng.uniform(18, 60), seed_of(self.universe.seed, aid), ore=rng.random() < 0.45)
                a.center = self.origin + Vector2(rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9)) * config.SECTOR_SIZE
                self.asteroids.append(a)
                self.bodies.append(a)

    def _make_wormhole(self, rng) -> None:
        dx = rng.randint(4, 12) * rng.choice([-1, 1])
        dy = rng.randint(-8, 8)
        wh = Wormhole(f"{self.key}:wh", "Wormhole", 180, (self.sx + dx, self.sy + dy))
        wh.center = self.origin + Vector2(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85)) * config.SECTOR_SIZE
        if self.star and (wh.center - self.star.center).length() < self.system_radius:
            wh.center = self.system_center + (wh.center - self.system_center).normalize() * (self.system_radius + 1200) \
                if (wh.center - self.system_center).length() > 1 else wh.center + Vector2(self.system_radius, 0)
        self.wormholes.append(wh)
        self.bodies.append(wh)

    # ------------------------------------------------------------------
    @property
    def has_system(self) -> bool:
        return self.star is not None

    def gravity_sources(self) -> list:
        src = []
        if self.star:
            src.append(self.star)
            src.extend(p for p in self.planets)
        src.extend(self.hazards)
        return src
