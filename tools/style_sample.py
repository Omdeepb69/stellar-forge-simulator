"""Style sample v2: matte (less shiny), multi-hue on one shared lightness/chroma
ladder, planned proportions against the pilot, and a detailed underground."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pygame  # noqa: E402
from pixelkit import (Sprite, box, capsule, circle, ellipse, hue_ramp, poly, smooth_union,  # noqa: E402
                      subtract, union, value_noise)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "sample"

# One palette, many hues, identical lightness/chroma steps (OkLCh).
H = {name: hue_ramp(h) for name, h in {
    "red": 25, "orange": 55, "amber": 75, "lime": 125, "green": 145, "teal": 185, "cyan": 215,
    "blue": 255, "indigo": 280, "violet": 305, "magenta": 335, "rose": 5}.items()}
H["soil"] = hue_ramp(60, chroma=0.45, light=-0.06)
H["soildeep"] = hue_ramp(40, chroma=0.35, light=-0.13)
H["stone"] = hue_ramp(70, chroma=0.12)
H["coolstone"] = hue_ramp(250, chroma=0.12)
H["bone"] = hue_ramp(85, chroma=0.22, light=0.08)
H["cream"] = hue_ramp(90, chroma=0.28, light=0.06)
H["skin"] = hue_ramp(190, chroma=0.75)

MATTE = dict(highlight=0.7, shine=0.0, mottle=0.06)

# Planned heights in art pixels (the pilot is 78). Bigger things are DRAWN bigger.
PROPORTIONS = {"pebble": 12, "rock": 24, "bush": 26, "crawler": 30, "mushroom": 44, "crystals": 40,
               "pilot": 78, "giant_fungus": 128, "shrine": 112}


# ----------------------------------------------------------------------------
def mushroom():
    s = Sprite(48, 46, seed=3)
    X, Y = s.wobbled(0.8, 6)
    s.paint(capsule(X, Y, (22, 45), (25, 24), 5.2, 3.8), H["cream"], **MATTE)
    s.stroke([(21, 42), (23, 33)], 1.0, H["cream"][1], 0.5)
    s.paint(ellipse(X, Y, 25, 23, 17, 4.5), H["orange"][:3], rim=2)
    cap = subtract(ellipse(X, Y, 25, 18, 21, 14), box(s.X, s.Y, 25, 31, 26, 6))
    s.paint(cap, H["magenta"], **MATTE)
    for (x, y, r) in ((15, 13, 2.4), (27, 9, 2.8), (35, 15, 2.0), (21, 18, 1.6), (31, 20, 1.4), (10, 20, 1.3)):
        s.dab(x, y, r, H["cyan"][3], 1.0)
        s.dab(x - 0.6, y - 0.6, r * 0.45, H["cyan"][4], 0.9)
    return s


def giant_fungus():
    """A tree-sized fungus: drawn tall (128 px), not scaled up."""
    s = Sprite(96, 128, seed=8)
    X, Y = s.wobbled(1.1, 8)
    trunk = union(capsule(X, Y, (46, 127), (50, 70), 9, 6), capsule(X, Y, (50, 72), (44, 40), 6, 5))
    s.paint(trunk, H["cream"], **MATTE)
    for k in range(5):
        y = 120 - k * 14
        s.stroke([(41 + k % 2, y), (45, y - 5), (49, y - 9)], 1.0, H["cream"][1], 0.55)
    s.paint(ellipse(X, Y, 46, 42, 36, 7), H["amber"][:3], rim=2)
    cap = subtract(ellipse(X, Y, 46, 32, 44, 26), box(s.X, s.Y, 46, 58, 50, 10))
    s.paint(cap, H["violet"], **MATTE)
    for (x, y, r) in ((24, 26, 3.6), (44, 16, 4.0), (64, 24, 3.2), (34, 36, 2.2), (57, 38, 2.4), (78, 34, 2.0),
                      (14, 38, 2.0)):
        s.dab(x, y, r, H["lime"][3], 1.0)
        s.dab(x - 0.8, y - 0.8, r * 0.4, H["lime"][4], 0.9)
    for x in (30, 52, 70):
        s.stroke([(x, 47), (x + 1, 56), (x - 1, 64)], 1.0, H["violet"][2], 0.8)
        s.dab(x - 1, 65, 1.4, H["lime"][3])
    return s


def basalt_rock():
    s = Sprite(40, 26, seed=5)
    X, Y = s.wobbled(1.0, 6)
    body = smooth_union(ellipse(X, Y, 17, 16, 15, 10), ellipse(X, Y, 27, 18, 11, 8), 4)
    body = subtract(body, box(s.X, s.Y, 20, 29, 30, 3))
    s.paint(body, H["coolstone"], **MATTE)
    s.stroke([(8, 20), (13, 15), (17, 17), (22, 12)], 1.1, H["orange"][3], 1.0, wobble=0.3)
    s.stroke([(24, 22), (28, 18), (33, 19)], 1.0, H["red"][3], 1.0)
    return s


def bush():
    s = Sprite(40, 28, seed=17)
    X, Y = s.wobbled(1.0, 4)
    body = union(circle(X, Y, 12, 18, 9), circle(X, Y, 22, 14, 11), circle(X, Y, 31, 19, 8))
    body = subtract(body, box(s.X, s.Y, 20, 31, 30, 3))
    s.paint(body, H["teal"], **MATTE)
    for (x, y) in ((10, 15), (19, 10), (27, 13), (32, 18), (15, 20), (24, 20)):
        s.dab(x, y, 1.7, H["red"][3])
        s.dab(x - 0.5, y - 0.5, 0.7, H["rose"][4])
    return s


def crystals():
    s = Sprite(40, 40, seed=12)
    X, Y = s.wobbled(0.5, 5)
    s.paint(ellipse(X, Y, 20, 38, 16, 4), H["coolstone"][:3], rim=0)
    for (x, h, lean, ramp_) in ((11, 22, -4, H["cyan"]), (19, 36, 1, H["indigo"]), (28, 26, 4, H["violet"]),
                                (34, 14, 3, H["cyan"])):
        w = 3.5 + h * 0.08
        pts = [(x - w, 38), (x - w * 0.7 + lean * 0.7, 38 - h * 0.8), (x + lean, 38 - h),
               (x + w * 0.7 + lean * 0.7, 38 - h * 0.8), (x + w, 38)]
        s.paint(poly(X, Y, pts), ramp_, highlight=0.6, mottle=0.03)
        s.stroke([(x - w * 0.3, 36), (x + lean * 0.6 - 0.5, 38 - h * 0.85)], 1.0, ramp_[3], 0.6)
    return s


def crawler():
    s = Sprite(44, 32, seed=11)
    X, Y = s.wobbled(0.6, 5)
    for k, x in enumerate((12, 19, 26)):
        s.paint(capsule(X, Y, (x, 22), (x - 3 + k, 31), 1.7, 1.2), H["indigo"][:4], rim=2)
    body = smooth_union(ellipse(X, Y, 20, 19, 13, 9), circle(X, Y, 32, 15, 7.5), 4)
    s.paint(body, H["violet"], **MATTE)
    s.paint(ellipse(X, Y, 19, 24, 9, 3), H["magenta"][1:4], rim=0)
    for (x, y, h) in ((11, 12, 7), (17, 10, 9), (23, 10, 7)):
        s.paint(poly(X, Y, [(x - 2.5, y + 3), (x, y - h), (x + 2.5, y + 3)]), H["cyan"], highlight=0.4, rim=0.5)
    s.flat(ellipse(s.X, s.Y, 35, 14, 2.8, 3.1), (16, 12, 30))
    s.dab(35.6, 13.2, 1.0, H["amber"][4])
    s.stroke([(37, 10), (40, 4), (39, 1)], 1.1, H["violet"][1])
    s.dab(39, 1.5, 1.8, H["amber"][3])
    return s


def shrine():
    s = Sprite(112, 112, seed=21)
    X, Y = s.wobbled(1.3, 9)
    arch = union(box(X, Y, 56, 80, 42, 32, 8), ellipse(X, Y, 56, 50, 38, 32))
    door = union(box(s.X, s.Y, 56, 94, 14, 18, 1), ellipse(s.X, s.Y, 56, 74, 14, 14))
    s.paint(subtract(arch, door), H["stone"], highlight=0.7, mottle=0.06, grain=0.04)
    s.flat(door, (14, 10, 28))
    for i in range(7):
        y = 54 + i * 8
        s.stroke([(18 + (i % 2) * 6, y), (38, y + 0.5)], 1.0, H["stone"][0], 0.45)
        s.stroke([(74, y + 0.5), (94 - (i % 2) * 6, y)], 1.0, H["stone"][0], 0.45)
    s.stroke([(46, 46), (56, 40), (66, 46)], 1.4, H["amber"][3], 0.95)
    s.dab(56, 49, 1.8, H["amber"][3])
    for (x, y, h, lean, rmp) in ((22, 34, 22, -5, H["violet"]), (30, 28, 15, -2, H["indigo"]),
                                 (86, 32, 20, 6, H["violet"]), (94, 44, 13, 8, H["cyan"]),
                                 (56, 20, 18, 0, H["violet"]), (48, 24, 10, -4, H["cyan"]),
                                 (65, 23, 12, 4, H["indigo"])):
        w = 3.5 + h * 0.16
        pts = [(x - w, y + 4), (x - w * 0.6 + lean * 0.7, y - h * 0.8), (x + lean, y - h),
               (x + w * 0.6 + lean * 0.7, y - h * 0.8), (x + w, y + 4)]
        s.paint(poly(X, Y, pts), rmp, highlight=0.5, mottle=0.03, rim=0.8)
    rng = np.random.default_rng(4)
    for _ in range(16):
        x = rng.uniform(16, 96)
        s.dab(x, 110 - rng.uniform(0, 6), rng.uniform(1.5, 3.2), H["green"][rng.integers(1, 3)], 0.95)
    return s


def vey_portrait():
    s = Sprite(44, 44, seed=51)
    X, Y = s.wobbled(0.6, 5)
    s.paint(ellipse(X, Y, 22, 44, 17, 10), H["blue"][:4], **MATTE)
    s.paint(box(X, Y, 12, 36, 4, 1.6, 0.8), H["amber"], rim=0)
    s.paint(box(X, Y, 32, 36, 4, 1.6, 0.8), H["amber"], rim=0)
    s.dab(22, 39, 1.8, H["red"][3])
    s.paint(box(X, Y, 22, 32, 4, 4), H["skin"][:4])
    head = smooth_union(ellipse(X, Y, 22, 19, 11, 13), union(
        poly(X, Y, [(12, 16), (3, 7), (14, 12)]), poly(X, Y, [(32, 16), (41, 7), (30, 12)])), 2)
    s.paint(head, H["skin"], **MATTE)
    for ex in (18, 26):
        s.flat(ellipse(s.X, s.Y, ex, 19, 2.4, 1.9), H["cream"][4])
        s.dab(ex + 0.3, 19.2, 1.0, (20, 26, 40))
    s.stroke([(15.5, 15.5), (20, 16.5)], 1.0, H["skin"][0], 0.9)
    s.stroke([(28.5, 15.5), (24, 16.5)], 1.0, H["skin"][0], 0.9)
    s.stroke([(19, 26), (25, 26)], 1.0, H["skin"][0], 0.8)
    s.stroke([(30, 9), (33, 14)], 1.0, H["skin"][1], 0.7)
    return s


def pixel_planet(size=64, seed=7):
    s = Sprite(size, size, seed=seed)
    r = size / 2 - 1.5
    cx = cy = size / 2
    nx, ny = (s.X - cx) / r, (s.Y - cy) / r
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lam = np.clip(nx * -0.75 + ny * -0.45 + nz * 0.45, -1, 1)
    d = 1.0 if size <= 64 else 1.6          # big planets get finer continents and clouds
    land_n = value_noise(size, size, size / (5 * d), seed) + 0.5 * value_noise(size, size, size / (11 * d), seed + 1)
    cloud_n = value_noise(size, size, size / (9 * d), seed + 5) + 0.4 * value_noise(size, size, size / (18 * d),
                                                                                    seed + 6)
    if size > 64:
        cloud_n -= 0.12
    t = 0.05 + 0.95 * np.clip(lam + 0.1, 0, 1) ** 0.8 + 0.04 * value_noise(size, size, 3, seed + 9)
    disc = np.hypot(s.X - cx, s.Y - cy) - r
    is_land = land_n > 0.18
    is_ice = np.abs(ny) > 0.78 + 0.08 * land_n
    col = np.zeros((size, size, 3))
    for mask, rmp in ((~is_land, H["blue"]), (is_land, H["green"]), (is_land & (land_n > 0.55), H["amber"]),
                      (is_ice, hue_ramp(230, chroma=0.25, light=0.12))):
        k = len(rmp) - 1
        idx = np.clip((t * k).astype(int), 0, k - 1)
        col = np.where(mask[..., None], np.array(rmp, float)[idx], col)
    day = lam > 0.05
    cloud_ramp = np.array([(150, 165, 190), (205, 215, 232), (240, 245, 250)], float)
    col = np.where(((cloud_n > 0.5) & day)[..., None], cloud_ramp[np.clip((t * 3).astype(int), 0, 2)], col)
    night = (lam < -0.12) | ((lam < 0.05) & (((s.X.astype(int) + s.Y.astype(int)) % 2) == 0))
    col = np.where(night[..., None], np.array(H["indigo"][0], float) * 0.45, col)
    s._over(col, np.clip(0.55 - disc, 0, 1))
    return s


# ---------------------------------------------------------------- terrain
def fringe(top=None, tuft2=None, flower=None):
    """Ground-top tile: tufts in two hues and the odd flower (cf. forest/floor.png)."""
    top, tuft2, flower = top or H["lime"], tuft2 or H["green"], flower or H["amber"]
    s = Sprite(80, 18, seed=31)
    X, Y = s.wobbled(0.6, 4)
    s.paint(box(X, Y, 40, 14, 46, 4), top[:3], rim=0, mottle=0.04)
    rng = np.random.default_rng(3)
    for i in range(24):
        x = i * 3.4 + rng.uniform(-1, 1)
        h = rng.uniform(3, 8)
        rmp = top if i % 3 else tuft2
        s.paint(capsule(X, Y, (x, 11), (x + rng.uniform(-1.5, 1.5), 11 - h), 1.4, 0.5), rmp, rim=0, mottle=0.02)
    for x in (13, 47, 68):
        s.stroke([(x, 10), (x, 4)], 1.0, tuft2[1])
        s.dab(x, 3.5, 1.6, flower[3])
    return s


def underground(w=160, h=120, seed=7):
    """Seamless soil tile: wavy strata, pebbles in several hues, roots, a fossil,
    rare ore glints. Painted, not noise-filled."""
    s = Sprite(w, h, seed=seed)
    tau = 2 * math.pi
    soil, deep = H["soil"], H["soildeep"]
    band = (s.Y + 5 * np.sin(s.X * tau / w * 2) + 3 * np.sin(s.X * tau / w * 5 + 1)) / h
    t = 0.62 - 0.35 * band + 0.04 * np.sin(s.Y * 0.45 + 2 * np.sin(s.X * tau / w * 3))
    strata = np.floor(band * 6) % 2 == 1
    t = np.where(strata, t - 0.12, t)
    idx = np.clip((t * 4).astype(int), 0, 3)
    col = np.array(soil[:4], float)[idx]
    col = np.where((band > 0.7)[..., None], np.array(deep[:4], float)[idx], col)
    s._over(col, np.ones((h, w)))
    rng = np.random.default_rng(seed)

    def wrapped(fn):
        for dx in (-w, 0, w):
            for dy in (-h, 0, h):
                fn(dx, dy)

    for _ in range(16):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        rr = rng.uniform(1.8, 4.2)
        rmp = [H["stone"], H["coolstone"], H["stone"], H["orange"], H["teal"]][rng.integers(0, 5)]

        def peb(dx, dy, x=x, y=y, rr=rr, rmp=rmp):
            d = ellipse(s.X, s.Y, x + dx, y + dy, rr * 1.3, rr)
            if (d < 1).any():
                s.paint(d, rmp, highlight=0.6, mottle=0.0, rim=1)
        wrapped(peb)
    for _ in range(4):
        x0 = rng.uniform(0, w)
        pts = [(x0, 0)]
        for _k in range(5):
            pts.append((pts[-1][0] + rng.uniform(-5, 5), pts[-1][1] + rng.uniform(4, 8)))
        wrapped(lambda dx, dy, pts=pts: s.stroke([(px + dx, py + dy) for px, py in pts], 1.4, H["soildeep"][0], 0.9))
    fx, fy = rng.uniform(20, w - 40), rng.uniform(h * 0.45, h * 0.75)
    for k in range(5):
        a = k * 0.9
        s.dab(fx + math.cos(a) * (6 - k), fy + math.sin(a) * (6 - k), 1.8 - k * 0.2, H["bone"][3 - (k % 2)])
    for _ in range(5):
        x, y = rng.uniform(4, w - 4), rng.uniform(h * 0.3, h - 4)
        s.dab(x, y, 1.2, H["cyan"][4])
        s.dab(x + 1.5, y + 1, 0.8, H["cyan"][3])
    return s


def mute(rmp, k, sky=(170, 200, 140)):
    return [tuple(int(c[i] * k + sky[i] * (1 - k)) for i in range(3)) for c in rmp]


def backdrop():
    s = Sprite(300, 80, seed=41)
    tau = 2 * math.pi

    def ridge(x):
        return 52 + 9 * np.sin(x * tau / 150) + 6 * np.sin(x * tau / 60 + 1) + 3 * np.sin(x * tau / 37.5)
    s.paint(-(s.Y - (ridge(s.X + 40) - 14)), mute(H["teal"], 0.4), rim=0, mottle=0.03)
    s.paint(-(s.Y - ridge(s.X)), mute(H["green"], 0.55), rim=0, mottle=0.03)
    rng = np.random.default_rng(8)
    for _ in range(9):
        x = rng.uniform(24, 276)
        gy = float(ridge(np.array(x)))
        hh = rng.uniform(10, 22)
        stem = capsule(s.X, s.Y, (x, gy + 2), (x + rng.uniform(-2, 2), gy - hh), 1.6, 1.2)
        cap = subtract(ellipse(s.X, s.Y, x, gy - hh, hh * 0.55, hh * 0.35), box(s.X, s.Y, x, gy - hh + 8, 20, 4))
        s.paint(union(stem, cap), mute(H["violet"], 0.5), rim=0, mottle=0.0)
    return s


ALL = {"mushroom": mushroom, "giant_fungus": giant_fungus, "basalt_rock": basalt_rock, "bush": bush,
       "crystals": crystals, "crawler": crawler, "shrine": shrine, "vey": vey_portrait, "planet": pixel_planet,
       "fringe": fringe, "underground": underground, "backdrop": backdrop}


def build():
    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    out = {}
    for name, fn in ALL.items():
        fn().save(OUT / f"{name}.png")
        out[name] = pygame.image.load(str(OUT / f"{name}.png")).convert_alpha()
    return out


if __name__ == "__main__":
    build()
    print("ok")
