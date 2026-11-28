"""Cached, case-insensitive asset loading with graceful fallbacks."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pygame

from .. import config


class AssetManager:
    """Loads images once and hands out cached, transformed copies.

    Paths are resolved case-insensitively so the game behaves the same on
    Windows, macOS and Linux (the old code broke on ``Assets/`` vs ``assets/``).
    """

    def __init__(self, root: Path = config.ASSET_DIR):
        self.root = Path(root)
        self._cache: dict[tuple, pygame.Surface] = {}
        self._index = self._build_index()
        self.missing: set[str] = set()

    def _build_index(self) -> dict[str, Path]:
        index = {}
        if not self.root.exists():
            return index
        for dirpath, _dirs, files in os.walk(self.root):
            for name in files:
                full = Path(dirpath) / name
                rel = full.relative_to(self.root).as_posix().lower()
                index[rel] = full
        return index

    def resolve(self, rel_path: str) -> Path | None:
        return self._index.get(rel_path.replace("\\", "/").lower())

    def exists(self, rel_path: str) -> bool:
        return self.resolve(rel_path) is not None

    # ------------------------------------------------------------------
    def image(self, rel_path: str, size: tuple[int, int] | None = None,
              scale: float | None = None, tint: tuple[int, int, int] | None = None,
              flip_x: bool = False, crop: bool = False) -> pygame.Surface:
        key = (rel_path.lower(), size, scale, tint, flip_x, crop)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        surf = self._load_raw(rel_path)
        if crop:
            box = surf.get_bounding_rect()
            if box.width and box.height:
                surf = surf.subsurface(box).copy()
        if scale is not None:
            w, h = surf.get_size()
            surf = pygame.transform.scale(surf, (max(1, int(w * scale)), max(1, int(h * scale))))
        if size is not None:
            w, h = surf.get_size()
            shrink = size[0] < w and size[1] < h and surf.get_bitsize() >= 24
            surf = pygame.transform.smoothscale(surf, size) if shrink else pygame.transform.scale(surf, size)
        if tint is not None:
            surf = tint_surface(surf, tint)
        if flip_x:
            surf = pygame.transform.flip(surf, True, False)
        self._cache[key] = surf
        return surf

    def sprite(self, rel_path: str, mult: int = 1, flip_x: bool = False, tint=None) -> pygame.Surface:
        """A world sprite at the fixed art scale: cropped, whole-number nearest
        scaling only, so every pixel on screen is the same size."""
        from .. import config
        key = ("sprite", rel_path.lower(), mult, flip_x, tint)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        surf = self.image(rel_path, crop=True, tint=tint)
        k = max(1, int(config.ART_SCALE * mult))
        surf = pygame.transform.scale(surf, (surf.get_width() * k, surf.get_height() * k))
        if flip_x:
            surf = pygame.transform.flip(surf, True, False)
        self._cache[key] = surf
        return surf

    def frames(self, rel_paths: list[str], **kw) -> list[pygame.Surface]:
        return [self.image(p, **kw) for p in rel_paths]

    def _load_raw(self, rel_path: str) -> pygame.Surface:
        key = ("raw", rel_path.lower())
        if key in self._cache:
            return self._cache[key]
        path = self.resolve(rel_path)
        if path is None:
            if rel_path not in self.missing:
                print(f"[assets] missing: {rel_path} (using placeholder)")
                self.missing.add(rel_path)
            surf = placeholder()
        else:
            try:
                surf = pygame.image.load(str(path))
                surf = surf.convert_alpha() if pygame.display.get_surface() else surf
            except Exception as exc:
                print(f"[assets] failed to load {rel_path}: {exc}")
                surf = placeholder()
        self._cache[key] = surf
        return surf


def placeholder(size=(64, 64)) -> pygame.Surface:
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((255, 0, 255, 160))
    pygame.draw.line(surf, (0, 0, 0), (0, 0), size, 3)
    return surf


def tint_surface(surf: pygame.Surface, tint: tuple[int, int, int]) -> pygame.Surface:
    """Multiply-tint a sprite, keeping alpha. Brightens a bit so tints stay vivid."""
    out = surf.copy()
    overlay = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    overlay.fill((*tint, 255))
    out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    lift = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    lift.fill((tint[0] // 5, tint[1] // 5, tint[2] // 5, 0))
    out.blit(lift, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return out


def glow(radius: float, color: tuple[int, int, int], intensity: float = 1.0,
         additive: bool = True) -> pygame.Surface:
    """Soft radial glow sprite.

    ``additive=True`` (the default) returns premultiplied colour for
    ``BLEND_ADD`` blits, which ignore alpha; ``False`` returns a plain
    alpha-faded sprite for normal blits.  Radii are quantised to ~10% steps
    and capped so zooming never floods the cache."""
    import math
    r = max(2.0, min(900.0, float(radius)))
    q = int(round(2 ** (round(math.log2(r) * 7) / 7)))
    return _glow(q, tuple(color), round(intensity, 2), additive)


@lru_cache(maxsize=48)
def _glow(radius: int, color: tuple[int, int, int], intensity: float, additive: bool = True) -> pygame.Surface:
    import numpy as np
    radius = max(2, int(radius))
    size = radius * 2
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - radius + 0.5) ** 2 + (yy - radius + 0.5) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * intensity
    # stepped + dithered (pixel-art), in 2-px cells so it shares the sprites' grain
    cell = 2
    bayer = np.array([[0, 2], [3, 1]]) / 4.0
    yy, xx = np.mgrid[0:size, 0:size]
    by, bx = (yy // cell) % 2, (xx // cell) % 2
    a = np.floor(np.clip(a, 0, 1) * 5 + bayer[by, bx] * 0.9) / 5
    a = np.clip(a, 0, 1)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rgb = pygame.surfarray.pixels3d(surf)
    k = a if additive else np.ones_like(a)
    for i in range(3):
        rgb[..., i] = (color[i] * k).T.astype(np.uint8)
    del rgb
    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[...] = (a * 255).T.astype(np.uint8)
    del alpha
    return surf


def rot(img: pygame.Surface, angle: float, scale: float = 1.0) -> pygame.Surface:
    """Pixel-art friendly rotozoom: nearest-neighbour scale (whole numbers when
    enlarging, eighths when shrinking), then a nearest-neighbour rotation."""
    if scale != 1.0:
        k = max(1, round(scale)) if scale >= 1 else max(1 / 16, round(scale * 8) / 8)
        img = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
    if angle % 360:
        img = pygame.transform.rotate(img, angle)
    return img
