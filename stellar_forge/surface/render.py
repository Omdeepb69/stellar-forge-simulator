"""Planet-surface painting in the house style (docs/ART_STYLE.md).

* Sky: flat bands (no smooth gradient), a stepped pixel sun in the star's colour,
  sometimes a pixel planet or moon hanging overhead.
* Backdrop: the biome's painted strip, parallax, anchored so its bottom edge is
  always tucked behind the grass.
* Ground: the biome's painted underground tile, masked by the terrain, with the
  fringe tile riding the surface. Rendered once per terrain chunk and cached.
* Liquids: flat colour with a bright top row and stepped waves.
"""
from __future__ import annotations

import math
import random
from collections import OrderedDict

import pygame

from .. import config
from ..world.biomes import LIQUIDS
from ..world.rng import int_hash

ART = config.ART_SCALE
CHUNK_DEPTH = 1100      # px of ground below the highest point of a chunk


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def build_sky(scene) -> pygame.Surface:
    b = scene.biome
    W, H = config.SCREEN_W, config.SCREEN_H
    sky = pygame.Surface((W, H))
    band = 16 * ART
    for y in range(0, H, band):            # flat bands, pixel-art style
        k = min(1.0, (y + band / 2) / (H * 0.78))
        sky.fill(_mix(b.sky_top, b.sky_bottom, k), (0, y, W, band))
    rng = random.Random(scene.planet.seed)
    if sum(b.sky_top) < 200:
        for _ in range(140):
            c = rng.randint(130, 255)
            x, y = rng.randrange(0, W, ART), rng.randrange(0, H // 2, ART)
            sky.fill((c, c, min(255, c + 20)), (x, y, ART, ART))
    sun_col = (255, 240, 200)
    sec = scene.game.universe.sector(*scene.planet.sector)
    if sec.star:
        sun_col = sec.star.color
    sx, sy = rng.randrange(240, W - 240), rng.randrange(80, 170)
    for r, k in ((40, 0.25), (32, 0.55), (24, 0.85)):         # stepped halo + disc
        col = _mix(b.sky_top, _mix(sun_col, (255, 255, 255), 0.4), k)
        for yy in range(-r, r + 1, ART * 2):
            hw = int((r * r - yy * yy) ** 0.5) // (ART * 2) * ART * 2
            sky.fill(col, (sx - hw, sy + yy, hw * 2, ART * 2))
    if scene.planet.is_moon or rng.random() < 0.4:
        from ..world.planet_art import render_planet
        biome = rng.choice(["barren", "ice", "volcanic", "crystal", "ocean"])
        img = render_planet(scene.planet.seed + 3, None, False, False, biome=biome, size=24)
        img = pygame.transform.scale(img, (img.get_width() * ART * 2, img.get_height() * ART * 2))
        img.set_alpha(200)
        sky.blit(img, (rng.randrange(60, W - 220), rng.randrange(40, 160)))
    return sky


def build_ridges(scene, near_col=None) -> list:
    """Two tileable mountain silhouettes in hazy biome colours: [(surface, parallax, lift)].
    The nearer one sits just behind the painted backdrop, the far one peeks over it."""
    b = scene.biome
    rng = random.Random(scene.planet.seed + 17)
    W = config.SCREEN_W * 2
    base = near_col or b.mountains
    out = []
    step = ART * 2
    for k, (haze, par, hgt, lift) in enumerate(((0.62, 0.04, 190, 130), (0.42, 0.09, 120, 130))):
        col = _mix(base, b.sky_bottom, haze)
        rim = _mix(col, (255, 255, 255), 0.18)
        shade = _mix(col, b.sky_top, 0.25)
        H = hgt + 140
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        waves = [(c, rng.uniform(0, math.tau), a) for c, a in ((2, 0.35), (3, 0.25), (5, 0.18), (9, 0.12),
                                                                 (17, 0.07), (31, 0.03))]
        peaks = (b.id in ("ice", "barren", "volcanic", "crystal"))
        def raw(x):
            v = sum(a * math.sin(c * x / W * math.tau + ph) for c, ph, a in waves)
            if peaks:
                v = 1 - abs(v) * 1.6                      # sharper, ridged peaks
            return H - 140 - (v * 0.5 + 0.5) * hgt
        for x in range(0, W, step):
            top = int(raw(x)) // step * step
            downhill = raw(x + 1) - raw(x - 1) > 0.25     # the face turned away from the sun
            surf.fill(col, (x, top, step, H - top))
            if downhill:                                   # a shadowed band under the crest
                depth = step * (4 + int(int_hash(x, 7) * 3))
                surf.fill(shade, (x, top, step, depth))
            else:
                surf.fill(rim, (x, top, step, step))
        out.append((surf, par, lift))
    return out


def build_clouds(scene) -> list:
    """A few chunky pixel clouds: [(surface, x, y, drift speed)]."""
    b = scene.biome
    rng = random.Random(scene.planet.seed + 29)
    light = _mix(b.sky_top, (255, 255, 255), 0.72)
    dark = _mix(b.sky_top, (255, 255, 255), 0.42)
    out = []
    g = ART * 2
    for _ in range(rng.randint(3, 6)):
        w, h = rng.randrange(120, 260, g), rng.randrange(36, 64, g)
        surf = pygame.Surface((w, h + g * 2), pygame.SRCALPHA)
        puffs = [(rng.uniform(0.15, 0.85) * w, rng.uniform(0.5, 0.75) * h, rng.uniform(0.25, 0.42) * h * 1.6)
                 for _ in range(rng.randint(3, 6))]
        for yy in range(0, h + g * 2, g):
            for xx in range(0, w, g):
                inside = any((xx - px) ** 2 / (r * r * 1.6) + (yy - py) ** 2 / (r * r * 0.5) < 1 for px, py, r in puffs)
                if inside:
                    surf.fill(light if yy < h * 0.62 else dark, (xx, yy, g, g))
        out.append((surf, rng.uniform(0, config.SCREEN_W + 600), rng.randrange(40, 240, g), rng.uniform(4, 12)))
    return out


class WorldPainter:
    def __init__(self, scene):
        self.scene = scene
        a = scene.game.assets
        b = scene.biome
        self.fringe = a.sprite(b.fringe) if b.fringe and a.exists(b.fringe) else None
        self.soil = a.sprite(b.soil) if b.soil and a.exists(b.soil) else None
        base = self.soil.get_at((4, self.soil.get_height() - 4))[:3] if self.soil else b.ground_dark
        self.soil_fill = tuple(int(c * 0.45) for c in base)
        self.far = None
        if b.far_bg and a.exists(b.far_bg):
            raw = a.image(b.far_bg, crop=True)
            self.far = pygame.transform.scale(raw, (raw.get_width() * 3, raw.get_height() * 3))
            self.far_fill = self.far.get_at((self.far.get_width() // 2, self.far.get_height() - 2))[:3]
        self.sky = build_sky(scene)
        self.chunks: OrderedDict = OrderedDict()
        self.ridges = build_ridges(scene, getattr(self, "far_fill", None)) if b.landable else []
        self.clouds = build_clouds(scene) if sum(b.sky_top) >= 200 else []

    # ---- backdrop -------------------------------------------------------------
    def horizon(self, ox, oy) -> float:
        t = self.scene.terrain
        return min(t.height(ox + config.SCREEN_W * 0.5 + dx) for dx in (-400, 0, 400)) - oy

    def draw_far(self, surf, ox, oy, clock: float, daylight: float):
        """Distant mountain ranges and drifting clouds: fill the sky above the backdrop."""
        horizon = self.horizon(ox, oy)
        fh = self.far.get_height() if self.far is not None else 0
        backdrop_top = int(horizon + 40 * ART) // ART * ART - fh
        for k, (img, par, lift) in enumerate(self.ridges):
            w, h = img.get_size()
            top = backdrop_top + lift - h
            x0 = -int((ox * par) % w)
            for i in range(config.SCREEN_W // w + 2):
                surf.blit(img, (x0 + i * w, top))
            if top + h < config.SCREEN_H:
                surf.fill(img.get_at((0, h - 1))[:3], (0, top + h, config.SCREEN_W, config.SCREEN_H - top - h))
        if self.clouds and daylight > 0.15:
            span = config.SCREEN_W + 600
            # Anchor vertical cloud parallax around the resting camera height (-0.6 * SCREEN_H)
            # so clouds sit in the upper sky at ground level and move with the background
            # when jumping, jetpacking, or climbing hills instead of sticking to the camera.
            sky_dy = -(oy + config.SCREEN_H * 0.6) * 0.5
            for img, x, y, speed in self.clouds:
                cx = (x + clock * speed - ox * 0.16) % span - 300
                cy = y + sky_dy
                img.set_alpha(int(255 * min(1.0, (daylight - 0.15) / 0.35)))
                surf.blit(img, (int(cx) // ART * ART, int(cy) // ART * ART))

    def draw_backdrop(self, surf, ox, oy):
        if self.far is None:
            return
        horizon = self.horizon(ox, oy)
        fw, fh = self.far.get_size()
        bottom = int(horizon + 40 * ART) // ART * ART          # tucked below the grass line
        top = bottom - fh
        x0 = -int((ox * 0.25) % fw)
        for i in range(config.SCREEN_W // fw + 2):
            surf.blit(self.far, (x0 + i * fw, top))
        if bottom < config.SCREEN_H:
            surf.fill(self.far_fill, (0, bottom, config.SCREEN_W, config.SCREEN_H - bottom))

    # ---- ground ---------------------------------------------------------------
    def _chunk(self, c):
        hit = self.chunks.get(c)
        if hit is not None:
            self.chunks.move_to_end(c)
            return hit
        t = self.scene.terrain
        cw = config.TERRAIN_CHUNK
        x0 = c * cw
        step = 2 * ART
        heights = [t.height(x0 + i) for i in range(0, cw + step, step)]
        top = int(min(heights)) - 24 * ART
        surf = pygame.Surface((cw, CHUNK_DEPTH), pygame.SRCALPHA)
        # underground tile in world-space so chunks join seamlessly
        if self.soil:
            tw, th = self.soil.get_size()
            sx0 = -(x0 % tw)
            sy0 = -(top % th)
            for yy in range(sy0, CHUNK_DEPTH, th):
                for xx in range(sx0, cw, tw):
                    surf.blit(self.soil, (xx, yy))
        else:
            surf.fill(self.scene.biome.ground)
        # cut away the sky above the terrain
        for i, h in enumerate(heights[:-1]):
            x = i * step
            cut = int(h) - top
            if cut > 0:
                surf.fill((0, 0, 0, 0), (x, 0, step, cut))
        # depth: three flat darker steps below the surface (pixel-art banding, no gradient)
        shade = pygame.Surface((step, CHUNK_DEPTH), pygame.SRCALPHA)
        shade.fill((8, 6, 14, 60))
        for i, h in enumerate(heights[:-1]):
            x = i * step
            gy = int(h) - top
            for d0 in (150 * ART, 290 * ART, 420 * ART):
                surf.blit(shade, (x, gy + d0))
        # fringe riding the surface
        if self.fringe:
            fw, fh = self.fringe.get_size()
            for i, h in enumerate(heights[:-1]):
                x = i * step
                src_x = (x0 + x) % fw
                y = int(h) - top - 6 * ART
                surf.blit(self.fringe, (x, y), (src_x, 0, step, fh))
        self.chunks[c] = (surf, top)
        if len(self.chunks) > 10:
            self.chunks.popitem(last=False)
        return surf, top

    def draw_ground(self, surf, ox, oy):
        c0 = self.scene.terrain.chunk_of(ox)
        cw = config.TERRAIN_CHUNK
        for c in range(c0, c0 + config.SCREEN_W // cw + 2):
            img, top = self._chunk(c)
            sx, sy = c * cw - ox, top - oy
            surf.blit(img, (sx, sy))
            below = sy + CHUNK_DEPTH
            if below < config.SCREEN_H:
                surf.fill(self.soil_fill, (sx, below, cw, config.SCREEN_H - below))

    # ---- liquids ----------------------------------------------------------------
    def draw_liquid(self, surf, ox, oy, clock, layer):
        t = self.scene.terrain
        if not t.liquid:
            return
        ly = t.liquid_y - oy
        if ly > config.SCREEN_H:
            return
        r, g, b, a = LIQUIDS[t.liquid]["color"]
        body = (r, g, b, max(150, a))
        hi = (min(255, r + 80), min(255, g + 80), min(255, b + 80), 230)
        layer.fill((0, 0, 0, 0))
        step = 4 * ART
        x0 = int(ox // step * step)
        H = config.SCREEN_H
        for wx in range(x0, int(ox + config.SCREEN_W + step), step):
            gy = t.height(wx) - oy
            if gy > ly:
                wave = (int(math.sin(wx * 0.012 + clock * 2.2) * 2) * ART)
                top = int(ly + wave)
                layer.fill(body, (wx - ox, top, step, min(gy, H) - top + 2))
                layer.fill(hi, (wx - ox, top, step, ART))
                if (wx // step + int(clock * 3)) % 7 == 0:
                    layer.fill(hi, (wx - ox + ART, top + 3 * ART, ART * 2, ART))
        surf.blit(layer, (0, 0))
