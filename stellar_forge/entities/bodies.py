"""Celestial bodies. Positions are analytic functions of world time
("on rails"), which keeps the infinite universe deterministic and cheap:
no n-body integration, and a revisited planet is exactly where it should be.
"""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from ..core.assets import glow
from ..world.biomes import BIOMES, LIQUIDS
from ..world.planet_art import SPRITES, render_planet
from ..core.assets import rot as _rot

# ---------------------------------------------------------------- pixel sprites in space
_RAW: dict = {}
_SCALED: dict = {}


def _raw(rel: str) -> pygame.Surface:
    img = _RAW.get(rel)
    if img is None:
        from .. import config
        try:
            img = pygame.image.load(str(config.ASSET_DIR / rel))
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            img = img.subsurface(img.get_bounding_rect()).copy()
        except (pygame.error, FileNotFoundError):
            img = pygame.Surface((8, 8), pygame.SRCALPHA)
        _RAW[rel] = img
    return img


def pix(img_or_rel, diameter: float, key=None) -> pygame.Surface:
    """Scale a pixel sprite to roughly ``diameter`` px: whole-number factors when
    enlarging (crisp pixels), eighths when shrinking. Cached."""
    img = _raw(img_or_rel) if isinstance(img_or_rel, str) else img_or_rel
    native = max(img.get_width(), img.get_height())
    k = diameter / native
    k = max(1, round(k)) if k >= 1 else max(1 / 16, round(k * 8) / 8)
    ck = (key or img_or_rel if isinstance(img_or_rel, str) else id(img), k)
    out = _SCALED.get(ck)
    if out is None:
        global _SCALED_PX
        w, h = max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))
        if len(_SCALED) > 300 or _SCALED_PX + w * h > _CACHE_BUDGET:     # bounded memory, always
            _SCALED.clear()
            _SCALED_PX = 0
        out = _SCALED[ck] = pygame.transform.scale(img, (w, h))
        _SCALED_PX += w * h
    return out


_SCALED_PX = 0
_CACHE_BUDGET = 24_000_000          # pixels (~96 MB) of scaled sprites, at most
BIG = 1400                           # above this many px across, only the visible slice is scaled


def blit_pix(surf, img_or_rel, center, diameter: float, key=None, flags: int = 0, quarter: int = 0,
             flip: bool = False) -> None:
    """Draw a pixel sprite scaled to ``diameter`` at ``center``.

    Small sizes come from the bounded cache. Huge sizes (zoomed right into a nebula, a star or a
    black hole) never build a giant surface: only the part that is on screen is cut from the small
    source and scaled, so memory stays flat however close the camera gets."""
    img = _raw(img_or_rel) if isinstance(img_or_rel, str) else img_or_rel
    native = max(img.get_width(), img.get_height())
    if diameter <= BIG:
        out = pix(img, diameter, key=key or (img_or_rel if isinstance(img_or_rel, str) else None))
        if quarter:
            out = pygame.transform.rotate(out, quarter * 90)
        if flip:
            out = pygame.transform.flip(out, True, False)
        surf.blit(out, out.get_rect(center=(int(center[0]), int(center[1]))), special_flags=flags)
        return
    if quarter:
        img = pygame.transform.rotate(img, quarter * 90)
    if flip:
        img = pygame.transform.flip(img, True, False)
    k = max(1, round(diameter / native))                     # whole-number scale: square pixels
    iw, ih = img.get_size()
    left, top = center[0] - iw * k / 2, center[1] - ih * k / 2
    sw, sh = surf.get_size()
    x0, y0 = max(0.0, left), max(0.0, top)
    x1, y1 = min(sw, left + iw * k), min(sh, top + ih * k)
    if x0 >= x1 or y0 >= y1:
        return
    tx0, ty0 = int((x0 - left) // k), int((y0 - top) // k)
    tx1, ty1 = min(iw, int(-(-(x1 - left) // k))), min(ih, int(-(-(y1 - top) // k)))
    if tx1 <= tx0 or ty1 <= ty0:
        return
    part = pygame.transform.scale(img.subsurface((tx0, ty0, tx1 - tx0, ty1 - ty0)),
                                  ((tx1 - tx0) * k, (ty1 - ty0) * k))
    surf.blit(part, (int(left + tx0 * k), int(top + ty0 * k)), special_flags=flags)


def render_star(color, size: int = 40) -> pygame.Surface:
    """A pixel star: flat disc with a lighter core and three stepped corona rings."""
    pad = size
    W = size + pad * 2
    surf = pygame.Surface((W, W), pygame.SRCALPHA)
    c = W // 2
    r = size // 2
    for rr, a in ((r * 2.2, 40), (r * 1.7, 80), (r * 1.35, 140)):
        for y in range(-int(rr), int(rr) + 1):
            hw = int((rr * rr - y * y) ** 0.5)
            pygame.draw.line(surf, (*color, a), (c - hw, c + y), (c + hw, c + y))
    for rr, col in ((r, color), (r * 0.78, tuple(min(255, v + 60) for v in color)), (r * 0.5, (255, 255, 240))):
        pygame.draw.circle(surf, col, (c, c), int(rr))
    return surf


_STARS: dict = {}


class Body:
    kind = "body"
    landable = False
    dockable = False
    solid = True

    def __init__(self, uid: str, name: str, radius: float, mu: float = 0.0):
        self.id = uid
        self.name = name
        self.radius = radius
        self.mu = mu                  # G*M, px^3/s^2
        self.parent: Body | None = None
        self.center = Vector2()       # used when parent is None
        self.orbit_r = 0.0
        self.omega = 0.0
        self.phase = 0.0

    def set_orbit(self, parent: "Body", radius: float, omega: float, phase: float) -> None:
        self.parent, self.orbit_r, self.omega, self.phase = parent, radius, omega, phase

    def pos(self, t: float) -> Vector2:
        if self.parent is None:
            return Vector2(self.center)
        memo = self.__dict__.get("_pos_memo")
        if memo is not None and memo[0] == t:          # many lookups per frame, one world time
            return Vector2(memo[1])
        a = self.phase + self.omega * t
        p = self.parent.pos(t) + Vector2(math.cos(a), math.sin(a)) * self.orbit_r
        self._pos_memo = (t, Vector2(p))
        return p

    def vel(self, t: float) -> Vector2:
        if self.parent is None:
            return Vector2()
        a = self.phase + self.omega * t
        v = Vector2(-math.sin(a), math.cos(a)) * self.orbit_r * self.omega
        return self.parent.vel(t) + v

    @property
    def surface_gravity(self) -> float:
        return self.mu / (self.radius ** 2) if self.radius else 0.0

    def draw(self, surf, cam, t, clock) -> None:
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        pygame.draw.circle(surf, (200, 200, 200), (sx, sy), max(1, self.radius * cam.zoom))

    def map_color(self):
        return (200, 200, 200)


# -----------------------------------------------------------------------------
class Star(Body):
    kind = "star"

    def __init__(self, uid, name, radius, mu, color, luminosity, spectral):
        super().__init__(uid, name, radius, mu)
        self.color = color
        self.luminosity = luminosity
        self.spectral = spectral

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 1.5:
            surf.fill(self.color, (int(sx) - 2, int(sy) - 2, 4, 4))
            return
        base = _STARS.get(self.color)
        if base is None:
            base = _STARS[self.color] = render_star(self.color)
        blit_pix(surf, base, (sx, sy), r * 2 * base.get_width() / 40, key=("star", self.color))

    def map_color(self):
        return self.color


class Planet(Body):
    kind = "planet"

    def __init__(self, uid, name, radius, mu, biome: str, seed: int, rings=False,
                 stronghold=False, is_moon=False, sector=(0, 0)):
        super().__init__(uid, name, radius, mu)
        self.biome_id = biome
        self.biome = BIOMES[biome]
        self.seed = seed
        self.rings = rings
        self.stronghold = stronghold
        self.is_moon = is_moon
        self.sector = sector
        self.landable = self.biome.landable
        self.moons: list[Planet] = []
        self.ancient_signal = stronghold
        self.shard: str | None = None     # Act II: this world's vault holds a Forge Shard
        self.lair = False                 # a planet boss lives here
        self.cave = False                 # an entrance to the underground layer
        if self.landable and not is_moon:
            frng = random.Random(seed ^ 0x5EED)
            from ..systems.items import BOSSES
            self.lair = biome in BOSSES and frng.random() < 0.16
            self.cave = biome not in ("ocean",) and frng.random() < 0.4

    def _build(self):
        liquid = LIQUIDS[self.biome.liquid]["color"] if self.biome.liquid and self.biome.liquid_level > 0.3 else None
        return render_planet(self.seed, self.biome.planet_palette, self.biome_id == "gas", self.rings, liquid,
                             biome=self.biome_id, size=48 if self.is_moon else None)

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 2.5:
            pygame.draw.circle(surf, self.biome.planet_palette[1], (sx, sy), max(1.5, r))
            return
        sprite = SPRITES.get(self.id, self._build, r)
        surf.blit(sprite, (sx - sprite.get_width() / 2, sy - sprite.get_height() / 2))

    def map_color(self):
        return self.biome.planet_palette[1]


class Station(Body):
    kind = "station"
    dockable = True

    def __init__(self, uid, name, seed):
        super().__init__(uid, name, 70, 0.0)
        self.seed = seed
        rng = random.Random(seed)
        self.color = rng.choice([(120, 200, 255), (255, 200, 120), (180, 255, 180), (255, 150, 200)])
        self.arms = rng.randint(3, 6)
        self.spin = rng.uniform(0.2, 0.5) * rng.choice([-1, 1])

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 3:
            surf.fill(self.color, (int(sx) - 2, int(sy) - 2, 4, 4))
            return
        blit_pix(surf, "generated/space/station.png", (sx, sy), r * 2.4,
                 quarter=int(clock * self.spin * 20) % 4)          # quarter turns keep pixels square
        if int(clock * 2) % 2 == 0:
            surf.fill((255, 90, 80), (int(sx) - 2, int(sy - r * 1.1), 4, 4))

    def map_color(self):
        return self.color


class BlackHole(Body):
    kind = "blackhole"

    def __init__(self, uid, name, radius, mu):
        super().__init__(uid, name, radius, mu)

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 2:
            surf.fill((255, 140, 60), (int(sx) - 2, int(sy) - 2, 4, 4))
            return
        blit_pix(surf, "generated/space/blackhole.png", (sx, sy), r * 5.3,
                 flip=bool(int(clock * 3) % 2))                   # the disc flickers as it spins

    def map_color(self):
        return (255, 140, 60)


class Pulsar(Body):
    kind = "pulsar"

    def __init__(self, uid, name, radius, mu, seed):
        super().__init__(uid, name, radius, mu)
        self.rot_speed = random.Random(seed).uniform(0.25, 0.5)
        self.beam_len = 9000
        self.beam_width = 0.07  # radians

    def beam_angle(self, clock):
        return clock * self.rot_speed

    def in_beam(self, point: Vector2, t, clock) -> bool:
        d = point - self.pos(t)
        if d.length() > self.beam_len or d.length() < self.radius:
            return False
        a = math.atan2(d.y, d.x)
        base = self.beam_angle(clock)
        for off in (0, math.pi):
            diff = (a - base - off + math.pi) % math.tau - math.pi
            if abs(diff) < self.beam_width:
                return True
        return False

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = max(2, self.radius * cam.zoom)
        base = self.beam_angle(clock)
        L = self.beam_len * cam.zoom
        beam = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for off in (0, math.pi):                 # two flat bands: a wide pale one and a bright core
            a = base + off
            for w, col in ((self.beam_width, (150, 200, 255, 50)), (self.beam_width * 0.35, (220, 240, 255, 90))):
                pts = [(sx, sy), (sx + math.cos(a - w) * L, sy + math.sin(a - w) * L),
                       (sx + math.cos(a + w) * L, sy + math.sin(a + w) * L)]
                pygame.draw.polygon(beam, col, pts)
        surf.blit(beam, (0, 0))
        blit_pix(surf, "generated/space/pulsar.png", (sx, sy), r * 2.6)

    def map_color(self):
        return (150, 200, 255)


class Wormhole(Body):
    kind = "wormhole"
    solid = False

    def __init__(self, uid, name, radius, exit_sector):
        super().__init__(uid, name, radius, 0.0)
        self.exit_sector = exit_sector

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 3:
            surf.fill((190, 110, 255), (int(sx) - 2, int(sy) - 2, 4, 4))
            return
        blit_pix(surf, "generated/space/wormhole.png", (sx, sy), r * 2.2,
                 quarter=int(clock * 2) % 4)                        # spins in quarter turns

    def map_color(self):
        return (190, 110, 255)


def gate_piece(img, k: int):
    """One fragment of the Forge ring texture (for the shattered/breaking views)."""
    w, h = img.get_size()
    pw, ph = w // 3, h // 3
    return ((k % 3) * pw, ((k // 3) % 3) * ph, pw, ph)


class ForgeGate(Body):
    """The Stellar Forge itself: a broken ring near Haven with five sockets."""
    kind = "forge"
    solid = False
    lit = 0                 # shards slotted (set by the space scene each frame)
    restored = False
    destroyed = False
    _sprite = None
    _cache: dict = {}

    def __init__(self, uid, name):
        super().__init__(uid, name, 150, 0.0)

    @classmethod
    def sprite(cls):
        if cls._sprite is None:
            from .. import config
            try:
                cls._sprite = pygame.image.load(str(config.ASSET_DIR / "generated" / "ships" / "forge_gate.png"))
                if pygame.display.get_surface() is not None:
                    cls._sprite = cls._sprite.convert_alpha()
            except (pygame.error, FileNotFoundError):
                cls._sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        return cls._sprite

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if self.destroyed:   # the player chose to shatter it: drifting wreckage
            if r < 4:
                pygame.draw.circle(surf, (120, 110, 100), (sx, sy), 2)
                return
            spr = self.sprite()
            for k in range(6):
                a = k * 1.05 + clock * 0.05
                d = r * (0.9 + 0.25 * k)
                piece = spr.subsurface(gate_piece(spr, k))
                img = _rot(piece, clock * (5 + k * 3), max(0.05, r / 120))
                img.set_alpha(170)
                surf.blit(img, img.get_rect(center=(sx + math.cos(a) * d, sy + math.sin(a) * d)))
            return
        col = (255, 200, 110) if not self.restored else (140, 230, 255)
        g = glow(int(max(8, r * (2.6 if self.restored else 1.8))) // 4 * 4, col, 0.7 if self.restored else 0.35)
        surf.blit(g, (sx - g.get_width() / 2, sy - g.get_height() / 2), special_flags=pygame.BLEND_ADD)
        if r < 4:
            pygame.draw.circle(surf, col, (sx, sy), 3)
            return
        size = max(8, int(r * 2.1) // 2 * 2)
        spin = int((clock * (14 if self.restored else 2)) % 360) // 2 * 2
        key = (size, spin)
        img = self._cache.get(key)
        if img is None:
            if len(self._cache) > 200:
                self._cache.clear()
            img = _rot(self.sprite(), spin, size / self.sprite().get_width())
            self._cache[key] = img
        surf.blit(img, img.get_rect(center=(sx, sy)))
        # shard sockets
        from ..core.game_state import SHARD_BIOMES, SHARD_COLORS
        for k, b in enumerate(SHARD_BIOMES):
            a = math.radians(-90 + k * 72 - spin)
            px, py = sx + math.cos(a) * r * 0.5, sy + math.sin(a) * r * 0.5
            if k < self.lit or self.restored:
                pygame.draw.circle(surf, SHARD_COLORS[b], (px, py), max(2, r * 0.07))
                pygame.draw.circle(surf, (255, 255, 255), (px, py), max(1, r * 0.03))

    def map_color(self):
        return (255, 200, 110)


class Derelict(Body):
    """A dead ship drifting in deep space. Fly close and press [E] to board."""
    kind = "derelict"
    solid = False
    _sprite = None

    def __init__(self, uid, name, seed):
        super().__init__(uid, name, 120, 0.0)
        self.seed = seed
        self.spin = random.Random(seed).uniform(-4, 4)
        self._cache = {}

    @classmethod
    def sprite(cls):
        if cls._sprite is None:
            from .. import config
            try:
                img = pygame.image.load(str(config.ASSET_DIR / "generated" / "space" / "derelict.png"))
                cls._sprite = img.convert_alpha() if pygame.display.get_surface() else img
            except (pygame.error, FileNotFoundError):
                cls._sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        return cls._sprite

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 3:
            pygame.draw.circle(surf, (150, 150, 160), (sx, sy), 2)
            return
        scale = round(max(0.1, r * 2.2 / self.sprite().get_width()), 2)
        ang = int((clock * self.spin) % 360) // 3 * 3
        img = self._cache.get((scale, ang))
        if img is None:
            if len(self._cache) > 80:
                self._cache.clear()
            img = self._cache[(scale, ang)] = _rot(self.sprite(), ang, scale)
        surf.blit(img, img.get_rect(center=(sx, sy)))
        if int(clock * 1.5) % 2:
            pygame.draw.circle(surf, (255, 90, 70), (sx + r * 0.3, sy - r * 0.2), max(1, 3 * cam.zoom))

    def map_color(self):
        return (170, 170, 180)


_NEB: dict = {}


def _nebula_blob(color):
    """A soft nebula puff painted at 32x32 with three stepped, dithered bands."""
    img = _NEB.get(color)
    if img is None:
        img = pygame.Surface((32, 32))
        img.fill((0, 0, 0))
        for y in range(32):
            for x in range(32):
                d = math.hypot(x - 15.5, y - 15.5) / 16
                step = 3 - int(d * 3 + ((x + y) % 2) * 0.35)
                if step > 0:
                    k = step * 0.09
                    img.set_at((x, y), tuple(int(c * k) for c in color))
        _NEB[color] = img
    return img


class Nebula:
    """Not a Body: a soft region that hides you from raiders and slows you."""
    kind = "nebula"

    def __init__(self, uid, center: Vector2, radius: float, color, seed):
        self.id = uid
        self.center = Vector2(center)
        self.radius = radius
        self.color = color
        rng = random.Random(seed)
        self.blobs = [(Vector2(rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6)) * radius,
                       rng.uniform(0.35, 0.7) * radius) for _ in range(9)]

    def contains(self, p: Vector2) -> bool:
        return (p - self.center).length_squared() < self.radius ** 2

    TEXELS = 64                     # composite texels per nebula radius

    def _composite(self) -> pygame.Surface:
        """All nine puffs added together once, at a coarse pixel size, so a frame draws one image."""
        comp = getattr(self, "_comp", None)
        if comp is None:
            texel = self.radius / self.TEXELS
            size = int(2.8 * self.TEXELS)
            comp = pygame.Surface((size, size))
            comp.fill((0, 0, 0))
            blob = _nebula_blob(self.color)
            for off, r in self.blobs:
                d = max(2, int(2 * r / texel))
                img = pygame.transform.scale(blob, (d, d))
                c = (size / 2 + off.x / texel, size / 2 + off.y / texel)
                comp.blit(img, img.get_rect(center=(int(c[0]), int(c[1]))), special_flags=pygame.BLEND_ADD)
            self._comp = comp
        return comp

    def draw(self, surf, cam, clock):
        comp = self._composite()
        diameter = comp.get_width() * (self.radius / self.TEXELS) * cam.zoom
        if diameter < 8:
            return
        sx, sy = cam.to_screen(self.center)
        half = diameter / 2
        if sx + half < 0 or sy + half < 0 or sx - half > cam.w or sy - half > cam.h:
            return
        blit_pix(surf, comp, (sx, sy), diameter, key=("nebc", self.id), flags=pygame.BLEND_ADD)


class Asteroid(Body):
    kind = "asteroid"

    def __init__(self, uid, radius, seed, ore: bool):
        super().__init__(uid, "Asteroid", radius, 0.0)
        rng = random.Random(seed)
        self.ore = ore
        self.hp = 2 + radius / 18
        n = rng.randint(7, 11)
        self.shape = [(math.cos(i / n * math.tau) * rng.uniform(0.7, 1.15),
                       math.sin(i / n * math.tau) * rng.uniform(0.7, 1.15)) for i in range(n)]
        self.spin = rng.uniform(-1, 1)
        shade = rng.randint(90, 140)
        self.color = (shade, shade - 8, shade - 16)
        self.variant = rng.randrange(4)

    def draw(self, surf, cam, t, clock):
        p = self.pos(t)
        sx, sy = cam.to_screen(p)
        r = self.radius * cam.zoom
        if r < 1.5:
            surf.fill(self.color, (int(sx), int(sy), 2, 2))
            return
        art = f"generated/space/asteroid_ore{self.variant % 2}.png" if self.ore else \
            f"generated/space/asteroid{self.variant % 4}.png"
        blit_pix(surf, art, (sx, sy), r * 2.3, quarter=int(clock * self.spin * 2) % 4)
