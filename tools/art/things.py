"""Bosses, ships, space objects, outposts, interiors, items, portraits, faction
emblems and icons - all painted in the house style at planned sizes."""
from __future__ import annotations

import shutil

from .common import (GEN, MATTE, H, R, ROOT, Sprite, box, capsule, circle, crystal, ellipse, math, np, poly,
                     ramp_of, rock, save, smooth_union, subtract, union)


# ---------------------------------------------------------------- bosses
def wyrm_head():
    s = Sprite(60, 56, seed=61)
    X, Y = s.wobbled(0.8, 6)
    s.paint(poly(X, Y, [(6, 50), (2, 28), (14, 8), (30, 2), (46, 8), (58, 28), (54, 50)]), H["sand"], **MATTE)
    for k in range(3):
        s.stroke([(12 + k * 14, 16 - k), (18 + k * 14, 12 - k)], 1.2, H["sand"][0], 0.8)
    s.flat(ellipse(s.X, s.Y, 30, 42, 14, 10), (60, 20, 24))
    for i in range(6):
        x = 19 + i * 4.4
        s.paint(poly(s.X, s.Y, [(x - 1.6, 34), (x, 41), (x + 1.6, 34)]), H["bone"], rim=0, highlight=0)
    for side in (-1, 1):
        s.paint(poly(X, Y, [(30 + side * 14, 46), (30 + side * 20, 55), (30 + side * 6, 52)]), H["bone"], rim=0.5)
    for x in (19, 41):
        s.paint(circle(X, Y, x, 22, 3.6), H["red"], highlight=0.6, mottle=0)
        s.dab(x - 1, 21, 1.1, H["yellow"][4])
    return s


def wyrm_segment():
    s = Sprite(44, 44, seed=62)
    X, Y = s.wobbled(0.6, 5)
    s.paint(circle(X, Y, 22, 22, 19), H["sand"], **MATTE)
    s.stroke([(8, 22), (22, 18), (36, 22)], 1.2, H["sand"][0], 0.7)
    for a in (2.3, 3.1, 3.9):
        x, y = 22 + math.cos(a) * 18, 22 + math.sin(a) * 18
        s.paint(poly(s.X, s.Y, [(x - 2, y + 1), (x + math.cos(a) * 7, y + math.sin(a) * 7), (x + 2, y - 1)]),
                H["bone"], rim=0.4)
    return s


def golem():
    s = Sprite(92, 112, seed=63)
    X, Y = s.wobbled(0.9, 7)
    for side in (-1, 1):
        s.paint(box(X, Y, 46 + side * 18, 100, 10, 13, 4), H["coolstone"], **MATTE)
        s.paint(ellipse(X, Y, 46 + side * 38, 62, 12, 26), H["coolstone"], **MATTE)
        s.paint(circle(X, Y, 46 + side * 40, 88, 10), H["coolstone"], **MATTE)
    s.paint(smooth_union(ellipse(X, Y, 46, 60, 30, 32), ellipse(X, Y, 46, 30, 22, 16), 6), H["coolstone"], **MATTE)
    for x, h, lean in ((30, 22, -4), (46, 30, 0), (62, 22, 4)):
        crystal(s, X, Y, x, 24, h, 6, lean, ramp_of("ice"))
    s.flat(box(s.X, s.Y, 46, 40, 13, 5, 2), (20, 30, 50))
    for x in (40, 52):
        s.dab(x, 40, 2.2, H["cyan"][4])
    crystal(s, X, Y, 46, 76, 12, 5, 0, ramp_of("ice"), rim=0.4)
    return s


def titan():
    s = Sprite(110, 116, seed=64)
    X, Y = s.wobbled(1.0, 8)
    for side in (-1, 1):
        s.paint(ellipse(X, Y, 55 + side * 40, 50, 15, 22), H["darkstone"], **MATTE)
    s.paint(smooth_union(poly(X, Y, [(14, 116), (20, 56), (40, 30), (70, 30), (90, 56), (96, 116)]),
                         ellipse(X, Y, 55, 22, 20, 20), 6), H["darkstone"], **MATTE)
    rng = np.random.default_rng(3)
    for _ in range(9):
        x, y = rng.uniform(26, 84), rng.uniform(50, 110)
        pts = [(x, y)]
        for _k in range(3):
            pts.append((pts[-1][0] + rng.uniform(-6, 6), pts[-1][1] + rng.uniform(4, 8)))
        s.stroke(pts, 1.4, H["orange"][3])
    for x in (47, 63):
        s.paint(ellipse(X, Y, x, 20, 4, 3), H["orange"], highlight=0.6, mottle=0)
    s.paint(circle(X, Y, 55, 66, 8), H["orange"], highlight=0.8, mottle=0)
    s.dab(55, 66, 3.4, H["yellow"][4])
    return s


def queen():
    s = Sprite(92, 84, seed=65)
    X, Y = s.wobbled(0.7, 6)
    for side in (-1, 1):
        s.paint(ellipse(X, Y, 46 + side * 26, 20, 20, 14), H["cyan"][2:], rim=0, highlight=0.4)
    s.paint(ellipse(X, Y, 46, 56, 18, 24), H["violet"], **MATTE)
    for k in range(3):
        s.stroke([(30, 50 + k * 9), (46, 53 + k * 9), (62, 50 + k * 9)], 1.2, H["violet"][1], 0.8)
    s.paint(circle(X, Y, 46, 26, 13), H["violet"], **MATTE)
    for x, h in ((38, 12), (46, 18), (54, 12)):
        crystal(s, X, Y, x, 16, h, 3, (x - 46) * 0.3, H["amber"], rim=0.4)
    for x in (41, 51):
        s.flat(ellipse(s.X, s.Y, x, 27, 3, 2.4), (30, 10, 40))
        s.dab(x, 27, 1.2, H["magenta"][4])
    return s


def drone():
    s = Sprite(24, 26, seed=66)
    crystal(s, s.X, s.Y, 12, 25, 22, 7, 0, H["violet"])
    s.dab(12, 13, 2, H["magenta"][4])
    return s


def leviathan_head():
    s = Sprite(84, 60, seed=67)
    X, Y = s.wobbled(0.8, 6)
    s.paint(poly(X, Y, [(2, 44), (14, 16), (46, 6), (76, 18), (82, 36), (66, 54), (24, 58)]), H["teal"], **MATTE)
    s.paint(poly(X, Y, [(44, 42), (82, 36), (66, 54), (40, 56)]), H["bone"], rim=0.5)
    for i in range(6):
        x = 48 + i * 5
        s.paint(poly(s.X, s.Y, [(x, 41 - i), (x + 2, 47 - i), (x + 4, 40 - i)]), H["bone"][2:], rim=0)
    s.paint(circle(X, Y, 62, 22, 4.4), H["amber"], highlight=0.6, mottle=0)
    s.dab(63, 22, 1.8, (20, 16, 30))
    for k in range(3):
        s.paint(poly(X, Y, [(20 + k * 12, 16 - k), (26 + k * 12, 2 + k), (32 + k * 12, 13 - k)]), H["teal"][:4],
                rim=1)
    s.stroke([(46, 6), (52, -1)], 1.0, H["teal"][1])
    s.dab(52, 1, 2.2, H["cyan"][4])
    return s


def leviathan_segment():
    s = Sprite(40, 40, seed=68)
    X, Y = s.wobbled(0.6, 5)
    s.paint(circle(X, Y, 20, 20, 17), H["teal"], **MATTE)
    s.paint(ellipse(X, Y, 20, 29, 12, 5), H["bone"], rim=0)
    return s


# ---------------------------------------------------------------- ships & space
def ship(hull, trim, glass, wing, body, length, seed, fins=2, cannons=False, stripes=False):
    """Top-down hull, nose up, in the painterly style of rocket/rocket.png."""
    s = Sprite(48, 70, seed=seed)
    X, Y = s.wobbled(0.5, 5)
    cx, top, bot = 24, 35 - length / 2, 35 + length / 2
    for side in (-1, 1):
        s.paint(poly(X, Y, [(cx + side * body * 0.35, bot - length * 0.45), (cx + side * wing, bot - 4),
                            (cx + side * wing * 0.8, bot + 2), (cx + side * body * 0.35, bot - 3)]), trim, **MATTE)
        if cannons:
            s.paint(box(X, Y, cx + side * (body * 0.5 + 3), top + length * 0.38, 1.8, length * 0.3, 0.8),
                    H["steel"], highlight=0.4, mottle=0)
    s.paint(poly(X, Y, [(cx, top), (cx + body * 0.5, top + length * 0.3), (cx + body * 0.5, bot - 5),
                        (cx + body * 0.35, bot), (cx - body * 0.35, bot), (cx - body * 0.5, bot - 5),
                        (cx - body * 0.5, top + length * 0.3)]), hull, **MATTE)
    s.paint(ellipse(X, Y, cx, top + length * 0.3, 3.6, 5), glass, highlight=0.8, mottle=0)
    if stripes:
        for y in (top + length * 0.55, top + length * 0.68):
            s.flat(box(s.X, s.Y, cx, y, body * 0.38, 1.4), H["yellow"][3])
    else:
        s.flat(box(s.X, s.Y, cx, top + length * 0.58, body * 0.32, 1.2), trim[3])
    for k in range(fins):
        ex = cx + (k - (fins - 1) / 2) * 7
        s.paint(box(X, Y, ex, bot, 2.6, 2.4, 1), H["steel"][:3], rim=1)
    rng = np.random.default_rng(seed)
    for _ in range(6):   # wear and rust spots, like the rocket
        s.dab(cx + rng.uniform(-body * 0.4, body * 0.4), rng.uniform(top + 10, bot - 6), rng.uniform(0.6, 1.2),
              H["rust"][rng.integers(0, 3)], 0.7)
    return s


def dreadnought():
    s = Sprite(90, 104, seed=71)
    X, Y = s.wobbled(0.6, 6)
    hull = R["teal"]
    s.paint(poly(X, Y, [(45, 2), (70, 40), (88, 88), (64, 80), (45, 102), (26, 80), (2, 88), (20, 40)]), hull,
            **MATTE)
    for y in (36, 56, 74):
        s.paint(box(X, Y, 45, y, 9, 2.4, 1), R["gold"], rim=0)
    s.paint(ellipse(X, Y, 45, 22, 8, 7), H["cyan"], highlight=0.7, mottle=0)
    for x in (18, 72):
        s.paint(circle(X, Y, x, 70, 6), hull[:3], rim=1)
        s.paint(capsule(s.X, s.Y, (x, 70), (x, 58), 1.6), R["gold"], rim=0)
    for x in (34, 45, 56):
        s.dab(x, 100, 2.2, H["orange"][3])
    return s


def forge_gate():
    s = Sprite(132, 132, seed=72)
    c = 66
    for k in range(12):
        a0, a1 = k / 12 * math.tau + 0.07, (k + 1) / 12 * math.tau - 0.07
        pts = [(c + math.cos(a) * r, c + math.sin(a) * r) for a, r in ((a0, 46), (a0, 62), (a1, 62), (a1, 46))]
        s.paint(poly(s.X, s.Y, pts), H["stone"] if k % 3 else H["amber"], **MATTE)
        m = (a0 + a1) / 2
        s.dab(c + math.cos(m) * 54, c + math.sin(m) * 54, 2.2, H["amber"][4])
    for k in range(5):
        a = -math.pi / 2 + k / 5 * math.tau
        x, y = c + math.cos(a) * 34, c + math.sin(a) * 34
        s.paint(subtract(circle(s.X, s.Y, x, y, 7), circle(s.X, s.Y, x, y, 5)), H["amber"], rim=0)
        s.flat(circle(s.X, s.Y, x, y, 5), (30, 20, 34))
    s.paint(circle(s.X, s.Y, c, c, 16), H["orange"], highlight=0.8, mottle=0)
    s.dab(c, c, 6, H["yellow"][4])
    return s


def derelict():
    s = Sprite(140, 70, seed=73)
    X, Y = s.wobbled(0.8, 8)
    s.paint(poly(X, Y, [(0, 36), (18, 14), (78, 10), (98, 18), (92, 34), (102, 56), (70, 64), (14, 60)]),
            H["steel"], **MATTE)
    for x in range(104, 136, 8):   # exposed ribs
        s.paint(subtract(ellipse(s.X, s.Y, x - 18, 36, 26, 24), ellipse(s.X, s.Y, x - 18, 36, 23, 21)),
                H["steel"][:3], rim=0)
    for x, y in ((26, 30), (40, 28), (54, 27)):
        s.flat(box(s.X, s.Y, x, y, 4, 2.4), (20, 22, 30))
        s.dab(x - 1.5, y - 0.5, 0.9, H["cyan"][4])
    s.paint(box(X, Y, 44, 46, 26, 3, 1), H["rust"], rim=0)
    rng = np.random.default_rng(2)
    for _ in range(14):
        s.dab(rng.uniform(8, 96), rng.uniform(16, 60), rng.uniform(0.8, 2), H["rust"][rng.integers(0, 3)], 0.8)
    return s


def beacon():
    s = Sprite(24, 34, seed=74)
    s.paint(poly(s.X, s.Y, [(6, 34), (12, 12), (18, 34)]), H["steel"], **MATTE)
    s.paint(circle(s.X, s.Y, 12, 8, 6), H["red"], highlight=0.7, mottle=0)
    s.dab(10, 6, 1.6, H["rose"][4])
    return s


def cargo_pod():
    s = Sprite(30, 22, seed=75)
    X, Y = s.wobbled(0.3, 5)
    s.paint(box(X, Y, 15, 11, 13, 8, 3), H["steel"], **MATTE)
    s.flat(box(s.X, s.Y, 15, 11, 3.4, 8), H["yellow"][3])
    s.dab(6, 7, 1.2, H["green"][4])
    return s


def comet():
    s = Sprite(30, 30, seed=76)
    X, Y = s.wobbled(1.0, 5)
    rock(s, X, Y, 15, 28, 28, 26, ramp_of("ice"))
    return s


def station():
    s = Sprite(64, 64, seed=77)
    c = 32
    s.paint(subtract(circle(s.X, s.Y, c, c, 28), circle(s.X, s.Y, c, c, 21)), H["steel"], **MATTE)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        s.paint(capsule(s.X, s.Y, (c, c), (c + math.cos(a) * 22, c + math.sin(a) * 22), 2.2), H["steel"][:4], rim=1)
        s.paint(box(s.X, s.Y, c + math.cos(a) * 27, c + math.sin(a) * 27, 5, 5, 1.5), H["coolstone"], **MATTE)
        s.dab(c + math.cos(a) * 27, c + math.sin(a) * 27, 1.4, H["cyan"][4])
    s.paint(circle(s.X, s.Y, c, c, 10), H["steel"], **MATTE)
    s.paint(circle(s.X, s.Y, c, c, 5), H["amber"], highlight=0.7, mottle=0)
    for a in range(0, 360, 30):
        s.dab(c + math.cos(math.radians(a)) * 24.5, c + math.sin(math.radians(a)) * 24.5, 0.9, H["yellow"][4], 0.9)
    return s


def asteroid(seed, ore=False):
    s = Sprite(28, 28, seed=seed)
    X, Y = s.wobbled(1.6, 4)
    rmp = [H["stone"], H["regolith"], H["coolstone"], H["darkstone"]][seed % 4]
    s.paint(smooth_union(circle(X, Y, 13, 14, 10), circle(X, Y, 17, 11, 7), 3), rmp, **MATTE)
    rng = np.random.default_rng(seed)
    for _ in range(3):
        x, y, r = rng.uniform(7, 21), rng.uniform(7, 21), rng.uniform(1.2, 2.4)
        s.flat(circle(s.X, s.Y, x, y, r), rmp[0], 0.8)
    if ore:
        for x, y in ((10, 12), (16, 17), (18, 10)):
            crystal(s, s.X, s.Y, x, y + 2, 5, 1.6, 0.5, H["cyan"], rim=0.3)
    return s


def blackhole():
    s = Sprite(80, 80, seed=78)
    c = 40
    d = np.hypot(s.X - c, (s.Y - c) * 2.6)
    disc = (d > 18) & (d < 38)
    rmp = np.array(H["orange"], float)
    band = np.clip(((38 - d) / 20 * 4).astype(int), 0, 4)
    col = rmp[band]
    s._over(col, disc.astype(float) * 0.95)
    s.flat(circle(s.X, s.Y, c, c, 15), (2, 0, 6))
    s.flat(subtract(circle(s.X, s.Y, c, c, 16.5), circle(s.X, s.Y, c, c, 15)), H["amber"][4])
    front = disc & (s.Y > c)
    s._over(col, front.astype(float))
    return s


def wormhole():
    s = Sprite(56, 56, seed=79)
    c = 28
    ang = np.arctan2(s.Y - c, s.X - c)
    d = np.hypot(s.X - c, s.Y - c)
    swirl = np.sin(ang * 3 + d * 0.45)
    rmp = np.array(H["violet"], float)
    idx = np.clip(((swirl * 0.5 + 0.5) * 3 + (1 - d / 26) * 2).astype(int), 0, 4)
    s._over(rmp[idx], ((d < 26) & (d > 5)).astype(float))
    s.flat(circle(s.X, s.Y, c, c, 5.5), (20, 4, 36))
    return s


def pulsar():
    s = Sprite(24, 24, seed=80)
    s.paint(circle(s.X, s.Y, 12, 12, 9), H["cyan"], highlight=0.8, mottle=0)
    s.dab(12, 12, 3.5, (240, 250, 255))
    return s


# ---------------------------------------------------------------- outposts & interiors
def hab():
    s = Sprite(70, 46, seed=81)
    s.paint(subtract(ellipse(s.X, s.Y, 35, 40, 30, 32), box(s.X, s.Y, 35, 48, 40, 8)), ramp_of("ice"), **MATTE)
    for x in (22, 35, 48):
        s.stroke([(x, 12), (x + (x - 35) * 0.3, 40)], 1.0, ramp_of("ice")[1], 0.6)
    s.paint(box(s.X, s.Y, 35, 43, 34, 3, 1), H["steel"], rim=1)
    s.paint(box(s.X, s.Y, 35, 34, 6, 6, 1), H["steel"][:3], rim=1)
    s.flat(box(s.X, s.Y, 35, 31, 4, 2.4), H["amber"][4])
    return s


def drill():
    s = Sprite(50, 72, seed=82)
    for side in (-1, 1):
        s.paint(capsule(s.X, s.Y, (25 + side * 18, 72), (25 + side * 4, 10), 1.8), H["steel"], highlight=0.4,
                mottle=0)
    for y in (30, 48, 62):
        s.paint(capsule(s.X, s.Y, (25 - (72 - y) * 0.22, y), (25 + (72 - y) * 0.22, y), 1.2), H["steel"][:3],
                mottle=0)
    s.paint(box(s.X, s.Y, 25, 8, 8, 4, 1.5), H["yellow"], highlight=0.5, mottle=0)
    s.paint(capsule(s.X, s.Y, (25, 12), (25, 66), 1.6), H["darkstone"], mottle=0)
    s.paint(poly(s.X, s.Y, [(21, 64), (29, 64), (25, 72)]), H["steel"], rim=0.5)
    s.dab(25, 3, 1.8, H["red"][3])
    return s


def pump():
    s = Sprite(54, 48, seed=83)
    s.paint(box(s.X, s.Y, 27, 45, 26, 3, 1), H["steel"], rim=1)
    s.paint(box(s.X, s.Y, 20, 26, 14, 17, 7), H["orange"], **MATTE)
    s.paint(box(s.X, s.Y, 42, 24, 6, 2, 1), H["steel"], rim=1)
    s.paint(box(s.X, s.Y, 47, 33, 2, 10, 1), H["steel"], rim=1)
    s.flat(box(s.X, s.Y, 20, 28, 7, 1.6), H["green"][3])
    return s


def beacon_pylon():
    s = Sprite(40, 72, seed=84)
    s.paint(poly(s.X, s.Y, [(10, 72), (16, 18), (24, 18), (30, 72)]), H["coolstone"], **MATTE)
    s.paint(subtract(ellipse(s.X, s.Y, 20, 10, 18, 6), ellipse(s.X, s.Y, 20, 10, 14, 4)), H["cyan"], highlight=0.5,
            mottle=0)
    s.dab(20, 10, 3, H["cyan"][4])
    return s


def cave_entrance():
    s = Sprite(100, 76, seed=85)
    X, Y = s.wobbled(1.4, 8)
    s.paint(subtract(poly(X, Y, [(0, 76), (6, 36), (26, 10), (56, 4), (86, 16), (100, 46), (100, 76)]),
                     box(s.X, s.Y, 50, 80, 60, 4)), H["stone"], **MATTE)
    hole = union(ellipse(s.X, s.Y, 50, 52, 22, 26), box(s.X, s.Y, 50, 70, 22, 8))
    s.flat(hole, (16, 12, 20))
    for x in (34, 44, 58, 66):
        s.paint(poly(s.X, s.Y, [(x - 3, 30), (x + 3, 30), (x, 38 + x % 7)]), H["stone"][:3], rim=0)
    s.dab(50, 70, 1.6, H["amber"][4])
    return s


def crate():
    s = Sprite(32, 28, seed=86)
    s.paint(box(s.X, s.Y, 16, 15, 14, 12, 2), H["steel"], **MATTE)
    s.flat(box(s.X, s.Y, 16, 15, 3.6, 12), H["yellow"][3])
    s.flat(box(s.X, s.Y, 16, 15, 14, 0.6), H["steel"][0])
    s.dab(26, 23, 1.2, H["green"][4])
    return s


def terminal():
    s = Sprite(24, 40, seed=87)
    s.paint(box(s.X, s.Y, 12, 30, 7, 10, 1), H["steel"][:4], rim=1)
    s.paint(box(s.X, s.Y, 12, 11, 11, 9, 2), H["steel"], **MATTE)
    s.flat(box(s.X, s.Y, 12, 11, 8, 6, 1), (14, 34, 30))
    for k in range(3):
        s.flat(box(s.X, s.Y, 9 + k, 8 + k * 3, 4 - k, 0.5), H["green"][4])
    return s


def sec_drone():
    s = Sprite(28, 24, seed=88)
    s.paint(ellipse(s.X, s.Y, 14, 13, 12, 7), H["steel"], **MATTE)
    s.paint(box(s.X, s.Y, 14, 13, 13, 1.6, 0.8), H["steel"][:3], rim=0)
    s.flat(circle(s.X, s.Y, 14, 13, 3.6), (30, 10, 14))
    s.dab(14, 13, 2, H["red"][4])
    s.stroke([(14, 6), (14, 1)], 1.0, H["steel"][1])
    return s


def airlock():
    s = Sprite(60, 80, seed=89)
    s.paint(box(s.X, s.Y, 30, 40, 29, 39, 4), H["steel"], **MATTE)
    s.flat(box(s.X, s.Y, 30, 44, 21, 33, 3), (26, 28, 38))
    s.flat(box(s.X, s.Y, 30, 13, 21, 2.4), H["yellow"][3])
    for i in range(5):
        s.paint(poly(s.X, s.Y, [(11 + i * 9, 11), (15 + i * 9, 11), (11 + i * 9, 15)]), H["darkstone"][:2], rim=0)
    s.dab(48, 46, 2, H["green"][4])
    return s


def datapad():
    s = Sprite(16, 18, seed=90)
    s.paint(box(s.X, s.Y, 8, 9, 6.6, 8, 1.5), H["steel"], **MATTE)
    s.flat(box(s.X, s.Y, 8, 8, 4.6, 5, 1), (16, 40, 34))
    for k in range(2):
        s.flat(box(s.X, s.Y, 7.5, 6.5 + k * 3, 3 - k, 0.5), H["green"][4])
    return s


# ---------------------------------------------------------------- items, portraits, emblems
SHARD_HUE = {"crystal": "violet", "volcanic": "orange", "toxic": "lime", "ocean": "cyan", "barren": "steel"}


def shard(biome):
    s = Sprite(22, 30, seed=91)
    r = ramp_of(SHARD_HUE[biome])
    s.paint(poly(s.X, s.Y, [(11, 1), (20, 12), (15, 29), (7, 29), (2, 12)]), r, highlight=0.8, mottle=0)
    s.stroke([(11, 2), (11, 15), (8, 28)], 1.0, r[4], 0.7)
    s.dab(11, 15, 1.6, (255, 255, 250))
    return s


def portrait_vey():
    s = Sprite(44, 44, seed=51)
    X, Y = s.wobbled(0.6, 5)
    s.paint(ellipse(X, Y, 22, 44, 17, 10), H["blue"][:4], **MATTE)
    for x in (12, 32):
        s.paint(box(X, Y, x, 36, 4, 1.6, 0.8), H["amber"], rim=0)
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


def portrait_ai():
    s = Sprite(44, 44, seed=52)
    s.paint(circle(s.X, s.Y, 22, 22, 17), H["steel"], **MATTE)
    s.flat(circle(s.X, s.Y, 22, 22, 12), (12, 20, 26))
    s.paint(circle(s.X, s.Y, 22, 22, 8), H["green"], highlight=0.8, mottle=0)
    s.dab(22, 22, 3.4, H["lime"][4])
    s.dab(20, 20, 1.2, (250, 255, 240))
    for k in range(8):
        a = k / 8 * math.tau
        s.stroke([(22 + math.cos(a) * 14, 22 + math.sin(a) * 14), (22 + math.cos(a) * 16.5, 22 + math.sin(a) * 16.5)],
                 1.0, H["steel"][4], 0.8)
    return s


def portrait_pirate():
    s = Sprite(44, 44, seed=53)
    X, Y = s.wobbled(0.6, 5)
    s.paint(ellipse(X, Y, 22, 44, 17, 10), H["wood"], **MATTE)
    s.paint(box(X, Y, 22, 37, 9, 2, 1), H["red"], rim=0)
    head = smooth_union(ellipse(X, Y, 22, 20, 11, 13), poly(X, Y, [(12, 18), (4, 8), (15, 13)]), 2)
    s.paint(head, H["amber"], **MATTE)
    s.flat(ellipse(s.X, s.Y, 26, 20, 2.4, 2), H["cream"][4])
    s.dab(26.4, 20.2, 1.0, (20, 16, 20))
    s.flat(box(s.X, s.Y, 17, 19.5, 3.4, 2.6, 1), (24, 16, 12))
    s.stroke([(10, 15), (33, 13)], 1.0, (24, 16, 12))
    s.stroke([(24, 25), (28, 30)], 1.0, H["red"][2], 0.8)
    s.stroke([(18, 28), (25, 27)], 1.0, H["amber"][0])
    return s


def portrait_survivor():
    s = Sprite(44, 44, seed=54)
    X, Y = s.wobbled(0.6, 5)
    s.paint(ellipse(X, Y, 22, 44, 17, 10), H["orange"][:4], **MATTE)
    s.paint(circle(X, Y, 22, 20, 14), H["steel"], **MATTE)
    s.paint(ellipse(X, Y, 22, 22, 9, 8), H["cream"], **MATTE)
    for x in (19, 25):
        s.dab(x, 21, 1.2, (24, 20, 30))
    s.stroke([(19, 26), (25, 26)], 1.0, H["cream"][0], 0.8)
    s.stroke([(30, 8), (33, 14)], 1.0, H["steel"][0])
    return s


def emblem(kind):
    s = Sprite(24, 24, seed=55)
    if kind == "haven":
        s.paint(poly(s.X, s.Y, [(12, 1), (22, 5), (20, 16), (12, 23), (4, 16), (2, 5)]), H["blue"], **MATTE)
        pts = [(12 + math.cos(-math.pi / 2 + k * math.pi / 5) * (5.5 if k % 2 == 0 else 2.3),
                12 + math.sin(-math.pi / 2 + k * math.pi / 5) * (5.5 if k % 2 == 0 else 2.3)) for k in range(10)]
        s.paint(poly(s.X, s.Y, pts), H["amber"], rim=0, highlight=0.5)
    elif kind == "traders":
        s.paint(circle(s.X, s.Y, 12, 12, 10.5), H["amber"], **MATTE)
        s.stroke([(12, 6), (12, 18)], 1.2, H["amber"][0])
        s.stroke([(6, 9), (18, 9)], 1.2, H["amber"][0])
    else:
        s.paint(poly(s.X, s.Y, [(12, 22), (3, 10), (6, 2), (12, 8), (18, 2), (21, 10)]), H["green"], **MATTE)
        s.dab(12, 13, 2.4, H["lime"][4])
    return s


# ---------------------------------------------------------------- icons
def _ic(seed):
    return Sprite(14, 14, seed=seed)


def ic_trophy():
    s = _ic(101)
    s.paint(poly(s.X, s.Y, [(3, 2), (11, 2), (10, 7), (7, 9), (4, 7)]), R["gold"], highlight=0.6, mottle=0)
    s.paint(box(s.X, s.Y, 7, 10.5, 1, 1.6), R["gold"][:3], rim=0)
    s.paint(box(s.X, s.Y, 7, 12.5, 3.5, 1.2, 0.5), R["gold"][:3], rim=0)
    return s


def ic_locked():
    s = _ic(102)
    s.paint(subtract(ellipse(s.X, s.Y, 7, 6, 4, 4.6), ellipse(s.X, s.Y, 7, 6, 2.2, 2.8)), H["steel"], rim=0)
    s.paint(box(s.X, s.Y, 7, 9.5, 5, 3.8, 1), H["steel"], highlight=0.5, mottle=0)
    s.dab(7, 9.5, 1, (24, 24, 30))
    return s


def ic_kill():
    s = _ic(103)
    s.paint(ellipse(s.X, s.Y, 7, 6, 5.5, 5), H["bone"], highlight=0.5, mottle=0)
    s.paint(box(s.X, s.Y, 7, 11, 3, 2, 0.8), H["bone"][:4], rim=0)
    for x in (5, 9):
        s.dab(x, 6.4, 1.4, (24, 16, 24))
    return s


def ic_planet():
    s = _ic(104)
    s.paint(circle(s.X, s.Y, 7, 7, 5), H["green"], highlight=0.6, mottle=0)
    s.stroke([(1, 9), (7, 6.5), (13, 4)], 1.0, H["amber"][3], 0.95)
    return s


def ic_shard():
    s = _ic(105)
    s.paint(poly(s.X, s.Y, [(7, 1), (12, 6), (9, 13), (5, 13), (2, 6)]), H["violet"], highlight=0.7, mottle=0)
    return s


def ic_waypoint():
    s = _ic(106)
    s.stroke([(4, 13), (4, 2)], 1.4, H["steel"][3])
    s.paint(poly(s.X, s.Y, [(5, 2), (13, 4.5), (5, 7)]), H["green"], highlight=0.5, mottle=0, rim=0.5)
    return s


def ic_autopilot():
    s = _ic(107)
    s.paint(subtract(circle(s.X, s.Y, 7, 7, 6.2), circle(s.X, s.Y, 7, 7, 4.8)), H["cyan"], rim=0)
    s.paint(poly(s.X, s.Y, [(7, 2.5), (10, 10), (7, 8.5), (4, 10)]), R["gold"], rim=0)
    return s


def ic_rarity(hue):
    s = _ic(108)
    s.paint(poly(s.X, s.Y, [(7, 1), (13, 7), (7, 13), (1, 7)]), ramp_of(hue), highlight=0.7, mottle=0)
    return s


def ic_missile():
    s = _ic(109)
    for x in (4, 9):
        s.paint(box(s.X, s.Y, x, 8, 1.8, 4.6, 1.5), H["steel"], highlight=0.5, mottle=0)
        s.paint(poly(s.X, s.Y, [(x - 1.8, 3.5), (x, 0.5), (x + 1.8, 3.5)]), H["red"], rim=0)
        s.dab(x, 13, 1, H["orange"][4])
    return s


def ic_grapple():
    s = _ic(110)
    s.stroke([(2, 13), (8, 6)], 1.0, H["steel"][2])
    s.paint(poly(s.X, s.Y, [(9, 1.5), (12.5, 5), (9, 8.5), (5.5, 5)]), H["steel"], highlight=0.6, mottle=0)
    return s


def ic_trophy_biome(hue):
    s = _ic(111)
    s.paint(circle(s.X, s.Y, 7, 7, 6), ramp_of(hue), highlight=0.7, mottle=0)
    s.dab(7, 7, 2.2, ramp_of(hue)[4])
    return s


def ic_key_colored(hue):
    """A Key icon in one of the three Key colours (Sun / Frost / Verdant)."""
    s = Sprite(16, 16, seed=112)
    r = ramp_of(hue)
    s.paint(subtract(circle(s.X, s.Y, 5, 5, 4.4), circle(s.X, s.Y, 5, 5, 1.8)), r, highlight=0.6, mottle=0)
    s.paint(union(box(s.X, s.Y, 10, 10, 5, 1.4, 0.5), box(s.X, s.Y, 13, 12.2, 1.1, 1.8),
                  box(s.X, s.Y, 10.6, 12, 0.9, 1.4)), r, highlight=0.4, mottle=0, rim=0.5)
    s.dab(4, 4, 1.1, r[4])
    return s


def ic_medkit():
    """Crisp pixel-art green medical cross badge for HUD and shop rows."""
    s = _ic(113)
    s.paint(box(s.X, s.Y, 7, 7, 5.8, 5.2, 1.5), H["snow"], highlight=0.5, mottle=0)
    cross = union(box(s.X, s.Y, 7, 7, 3.8, 1.3, 0.2), box(s.X, s.Y, 7, 7, 1.3, 3.8, 0.2))
    s.paint(cross, H["green"], highlight=0.8, mottle=0, rim=0)
    s.dab(6.5, 6.2, 0.9, H["lime"][4])
    return s


def build_all():
    out = []
    bosses = {"bosses/wyrm_head.png": wyrm_head, "bosses/wyrm_segment.png": wyrm_segment, "bosses/golem.png": golem,
              "bosses/titan.png": titan, "bosses/queen.png": queen, "bosses/drone.png": drone,
              "bosses/leviathan.png": leviathan_head, "bosses/leviathan_segment.png": leviathan_segment}
    things = {
        "ships/scout.png": lambda: ship(H["steel"], H["cyan"], H["cyan"], 15, 12, 56, 1, fins=1),
        "ships/gunship.png": lambda: ship(H["coolstone"], H["red"], H["amber"], 21, 18, 52, 2, cannons=True),
        "ships/hauler.png": lambda: ship(H["amber"], H["steel"], H["cyan"], 19, 22, 54, 3, fins=3, stripes=True),
        "ships/dreadnought.png": dreadnought, "ships/forge_gate.png": forge_gate,
        "space/derelict.png": derelict, "space/beacon.png": beacon, "space/cargo_pod.png": cargo_pod,
        "space/comet.png": comet, "space/station.png": station, "space/blackhole.png": blackhole,
        "space/wormhole.png": wormhole, "space/pulsar.png": pulsar,
        **{f"space/asteroid{i}.png": (lambda i=i: asteroid(i)) for i in range(4)},
        **{f"space/asteroid_ore{i}.png": (lambda i=i: asteroid(i + 10, True)) for i in range(2)}, "outposts/hab.png": hab, "outposts/drill.png": drill, "outposts/pump.png": pump,
        "outposts/beacon.png": beacon_pylon, "interiors/cave_entrance.png": cave_entrance,
        "interiors/crate.png": crate, "interiors/terminal.png": terminal, "interiors/drone.png": sec_drone,
        "interiors/airlock.png": airlock, "items/datapad.png": datapad,
        "portraits/vey.png": portrait_vey, "portraits/ai.png": portrait_ai, "portraits/pirate.png": portrait_pirate,
        "portraits/survivor.png": portrait_survivor,
        "factions/haven.png": lambda: emblem("haven"), "factions/traders.png": lambda: emblem("traders"),
        "factions/remnant.png": lambda: emblem("remnant"),
    }
    for b in SHARD_HUE:
        things[f"items/shard_{b}.png"] = lambda b=b: shard(b)
    icons = {"trophy": ic_trophy, "locked": ic_locked, "kill": ic_kill, "planet": ic_planet, "shard": ic_shard,
             "waypoint": ic_waypoint, "autopilot": ic_autopilot, "w_missile": ic_missile, "grapple": ic_grapple,
             "rarity_common": lambda: ic_rarity("steel"), "rarity_rare": lambda: ic_rarity("blue"),
             "rarity_epic": lambda: ic_rarity("violet"), "rarity_legendary": lambda: ic_rarity("amber"),
             "t_wyrm": lambda: ic_trophy_biome("amber"), "t_golem": lambda: ic_trophy_biome("cyan"),
             "t_titan": lambda: ic_trophy_biome("orange"), "t_queen": lambda: ic_trophy_biome("violet"),
             "t_leviathan": lambda: ic_trophy_biome("teal"),
             "key_desert": lambda: ic_key_colored("amber"), "key_ice": lambda: ic_key_colored("cyan"),
             "key_forest": lambda: ic_key_colored("green"), "medkit": ic_medkit}
    for rel, fn in {**bosses, **things}.items():
        save(fn(), rel)
        out.append(rel)
    ui_icons = ROOT / "assets" / "ui" / "icons"
    for name, fn in icons.items():
        fn().save(ui_icons / f"{name}.png")
    # legacy icon names used around the code base -> the theme icons
    alias = {"credits": "coin", "w_blaster": "blaster", "star": "star", "data": "data", "ore": "ore", "fuel": "fuel",
             "hull": "hull", "shield": "shield", "key": "key", "cargo": "scroll", "scan": "scanner"}
    legacy = GEN / "ui" / "icons"
    legacy.mkdir(parents=True, exist_ok=True)
    for p in ui_icons.glob("*.png"):
        shutil.copy(p, legacy / p.name)
    for old, new in alias.items():
        if (ui_icons / f"{new}.png").exists():
            shutil.copy(ui_icons / f"{new}.png", legacy / f"{old}.png")
    return out
