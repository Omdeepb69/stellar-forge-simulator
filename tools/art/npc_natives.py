"""Native peoples: two for every kind of world, painted in the same 48-wide design
space and pose set as the travellers in npc.py (which widens them on the way out).

Order matches stellar_forge/systems/species.py (indices 8..23).
"""
from __future__ import annotations

import math

import numpy as np

from .common import MATTE, H, box, capsule, circle, ellipse, poly, subtract
from pixelkit import hexc, intersect, ramp

FOOT = 81
INK = (22, 18, 30)
FLESH_PINK = ramp(*map(hexc, ("7a3248", "b04e66", "d8788a", "f0a4ae", "ffd4d6")))
CACTUS = ramp(*map(hexc, ("2a4a2c", "3e6a3a", "5a8a48", "7eaa5c", "a8c87a")))
FUR_GREY = ramp(*map(hexc, ("3a3436", "564c4c", "766a66", "988a82", "baaea2")))
LAVA = ramp(*map(hexc, ("7a1e0c", "c2400e", "ec7a1c", "fcb840", "fff0a0")))
SLIME = ramp(*map(hexc, ("2c5a1e", "4a8a28", "74b83a", "a6dc5a", "dcf8a0")))
TOAD = ramp(*map(hexc, ("2c3a1c", "45562a", "62743a", "84944e", "aab46a")))
NAVY = ramp(*map(hexc, ("161a2e", "232a46", "343e62", "4a5680", "64729a")))
CELL = ramp(*map(hexc, ("12204a", "1e3670", "2c5498", "4a7cc0", "86b2e4")))


# ---------------------------------------------------------------- helpers
def shadow(s, cx=24, w=13):
    s.flat(ellipse(s.X, s.Y, cx, FOOT - 0.5, w, 1.6), (10, 10, 20), 0.28)


def eyes(s, pts, p, r=1.1, col=INK):
    for x, y in pts:
        if p.blink:
            s.flat(box(s.X, s.Y, x, y + 0.4, r + 0.5, 0.45), col)
        else:
            s.flat(box(s.X, s.Y, x, y, r * 0.9, r * 1.4, 0.3), col)
            s.dab(x + 0.3, y - 0.8, 0.45, (250, 250, 255))


def mouth(s, x, y, p, col, w=1.6):
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, x, y, w, 1.2), col)
    else:
        s.stroke([(x - w, y), (x + w, y - 0.3)], 0.9, col)


def legs(s, p, hip_y, rmp, foot=None, spread=5, width=3.8, length=None, foot_w=4.6):
    """Two stout legs with a walk swing; ``foot`` paints boots/paws in that ramp."""
    if p.sit:
        return
    for side, d in ((-1, -p.sw * 0.7), (1, p.sw * 0.7)):
        hx = 24 + side * spread
        r = rmp[:3] if side < 0 else rmp[:4]
        end = FOOT - 2 - (2 if (p.walk and ((side > 0 and p.f == 1) or (side < 0 and p.f == 3))) else 0)
        s.paint(capsule(s.X, s.Y, (hx, hip_y), (hx + d, end), width, width * 0.9), r, rim=1, mottle=0)
        if foot is not None:
            s.paint(box(s.X, s.Y, hx + d + 1.4, end + 0.6, foot_w, 2.2, 1.2), foot[:3] if side < 0 else foot[:4],
                    rim=1, mottle=0)


def hand_at(p, sh, reach=11):
    x, y = sh
    if p.wave:
        return (x + 6 + p.f * 3, y - reach - 2)
    if p.talk:
        return (x + reach - 1, y + 1 - p.f * 3)
    if p.sit:
        return (x + 7, y + 7)
    if p.walk:
        return (x + (-3, -1, 3, 1)[p.f], y + reach)
    return (x + 2, y + reach + p.breathe * 0.4)


def arm(s, p, sh, rmp, hand_rmp=None, width=3.4, reach=11, back=False):
    hand = hand_at(p, sh, reach) if not back else (sh[0] - 2, sh[1] + reach)
    r = rmp[:3] if back else rmp[:4]
    s.paint(capsule(s.X, s.Y, sh, hand, width, width * 0.85), r, rim=1, mottle=0)
    s.paint(circle(s.X, s.Y, hand[0], hand[1], width * 0.8), (hand_rmp or rmp)[:4], rim=1, mottle=0)
    return hand


def seat(s):
    s.paint(box(s.X, s.Y, 22, FOOT - 4, 12, 4, 2), H["wood"], **MATTE)
    s.flat(box(s.X, s.Y, 22, FOOT - 4, 12, 0.6), H["wood"][0])


# ---------------------------------------------------------------- forest
def barkling(s, X, Y, p):
    low = 8 if p.sit else 0
    by = 52 + p.bob + low
    shadow(s)
    if p.sit:
        seat(s)
    legs(s, p, by + 12, H["wood"], spread=6, width=4.4)
    if not p.sit:                                          # root toes
        for side in (-1, 1):
            fx = 24 + side * 6 + (p.sw * 0.7 * side)
            s.stroke([(fx - 3, FOOT - 1), (fx + 4, FOOT - 1)], 2.0, H["wood"][1])
    arm(s, p, (17, by - 6), H["wood"], back=True, width=2.8)
    body = box(X, Y, 24, by, 11, 14, 4)
    s.paint(body, H["wood"], **MATTE, strokes=0.12)
    for x in (18, 23, 29):
        s.stroke([(x, by - 10), (x + 1, by + 2), (x - 0.5, by + 12)], 0.8, H["wood"][0], 0.7)
    s.paint(ellipse(s.X, s.Y, 25, by - 13, 11, 3), H["wood"][2:], rim=0.5, mottle=0)      # cut top rings
    s.stroke([(19, by - 13), (31, by - 13)], 0.6, H["wood"][1], 0.6)
    for dx, dy, r in ((-8, -19, 6), (0, -23, 7), (8, -19, 6), (-3, -16, 5), (6, -15, 5)):   # leafy crown
        s.paint(circle(X, Y, 24 + dx, by + dy - p.breathe * 0.5, r), H["green"], rim=1, mottle=0.1)
    s.dab(19, by - 22, 1.2, H["rose"][4])
    s.dab(29, by - 24, 1.2, H["yellow"][4])
    hy = by - 4
    for x in (26, 31):                                      # knothole eyes with a green glint
        s.flat(ellipse(s.X, s.Y, x, hy, 2.4, 3.0 if not p.blink else 0.6), (30, 20, 16))
        if not p.blink:
            s.dab(x + 0.4, hy - 0.4, 1.3, H["lime"][4])
            s.dab(x + 0.8, hy - 1.0, 0.5, (255, 255, 230))
    mouth(s, 29, hy + 5, p, (40, 26, 20), 2.0)
    arm(s, p, (32, by - 6), H["wood"], H["green"], width=2.8)


def mothkin(s, X, Y, p):
    low = 8 if p.sit else 0
    by = 54 + p.bob + low
    shadow(s)
    if p.sit:
        seat(s)
    flap = (0, 2, 0, 2)[p.f] if p.walk else p.breathe
    for side, k in ((-1, 0.7), (1, 1.0)):                   # folded wings behind
        wx = 24 + side * 3
        wing = poly(X, Y, [(wx, by - 16), (wx + side * 14 - flap * side, by - 22), (wx + side * 16, by + 2),
                           (wx + side * 5, by + 10)])
        s.paint(wing, H["amber"] if side > 0 else H["amber"][:4], rim=1, mottle=0.06)
        s.paint(circle(s.X, s.Y, wx + side * 10, by - 6, 3), H["cream"][2:], rim=0, mottle=0)
        s.dab(wx + side * 10, by - 6, 1.4, INK)
    legs(s, p, by + 10, H["darkstone"], spread=4, width=2.6)
    s.paint(ellipse(X, Y, 24, by, 10, 13), H["cream"], **MATTE)
    s.speckle(ellipse(s.X, s.Y, 24, by, 10, 13), H["cream"][1], 0.2, seed=4)
    s.paint(ellipse(s.X, s.Y, 25, by - 9, 9, 4), H["bone"][2:], rim=0, mottle=0)      # fluffy ruff
    hy = by - 17
    s.paint(ellipse(X, Y, 25, hy, 9, 8), H["cream"], **MATTE)
    for side in (-1, 1):                                    # feathery antennae
        base, tip = (24 + side * 3, hy - 7), (24 + side * 9 + 3, hy - 16)
        s.stroke([base, tip], 1.0, H["amber"][1])
        for k in range(1, 4):
            t = k / 4
            x, y = base[0] + (tip[0] - base[0]) * t, base[1] + (tip[1] - base[1]) * t
            s.stroke([(x, y), (x + 2, y + 1.5)], 0.7, H["amber"][2])
    for x in (25.5, 31):                                    # big glossy eyes
        if p.blink:
            s.flat(box(s.X, s.Y, x, hy, 2.6, 0.5), INK)
        else:
            s.paint(ellipse(s.X, s.Y, x, hy, 2.8, 3.4), ramp(*map(hexc, ("0c0a14", "1c1828", "2e2a40", "4a4664"))),
                    rim=0, mottle=0, highlight=0.6)
            s.dab(x + 0.8, hy - 1.4, 0.8, (255, 255, 255))
    mouth(s, 29, hy + 5, p, (90, 60, 50), 1.2)
    arm(s, p, (31, by - 4), H["cream"], width=2.6, reach=10)


# ---------------------------------------------------------------- desert
def dunestrider(s, X, Y, p):
    low = 9 if p.sit else 0
    by = 56 + p.bob + low
    shadow(s, 24, 15)
    if p.sit:
        seat(s)
    legs(s, p, by + 6, H["sand"], foot=H["wood"], spread=6, width=4.2)
    arm(s, p, (18, by - 6), H["sand"], back=True)
    shell = ellipse(X, Y, 22, by - 4, 15, 13)
    s.paint(shell, H["sand"], **MATTE)
    for k in range(4):                                     # armadillo bands
        s.stroke([(10 + k * 6, by - 14 + k), (12 + k * 6, by + 6)], 1.0, H["sand"][0], 0.7)
    s.paint(box(s.X, s.Y, 23, by + 6, 13, 3, 1.5), H["red"][1:4], rim=1, mottle=0)        # sash
    hy = by - 10
    s.paint(ellipse(X, Y, 34, hy + 2, 8, 6.5), H["sand"][1:], **MATTE)                     # snout head
    s.paint(ellipse(s.X, s.Y, 41, hy + 4, 2.6, 2), H["rose"][:4], rim=1, mottle=0)        # nose
    s.paint(ellipse(s.X, s.Y, 31, hy - 4, 3, 3.5, rot=-0.4), H["sand"][:4], rim=1, mottle=0)   # ear
    s.stroke([(28, hy - 1), (39, hy - 1)], 1.6, (50, 40, 46))                               # goggle strap
    s.paint(circle(s.X, s.Y, 36, hy - 1, 2.6), H["cyan"], rim=1, mottle=0, highlight=0.8)
    if p.blink:
        s.flat(box(s.X, s.Y, 36, hy - 1, 2, 2), H["cyan"][1])
    mouth(s, 37, hy + 6, p, (70, 40, 36), 1.4)
    s.paint(box(s.X, s.Y, 28, hy + 7, 6, 2.6, 1), H["red"], rim=1, mottle=0)               # scarf
    arm(s, p, (31, by - 4), H["sand"], width=3.2)


def cactling(s, X, Y, p):
    low = 7 if p.sit else 0
    by = 56 + p.bob + low
    shadow(s, 24, 13)
    if p.sit:
        s.paint(box(s.X, s.Y, 24, FOOT - 4, 11, 4, 1.5), H["rust"], **MATTE)    # sits in a clay pot
    legs(s, p, by + 10, CACTUS, spread=5, width=3.6)
    body = ellipse(X, Y, 24, by - 2, 12, 15)
    s.paint(body, CACTUS, **MATTE)
    for x in (17, 21, 25, 29):
        s.stroke([(x, by - 15), (x + 0.5, by + 10)], 0.8, CACTUS[0], 0.6)
    for k in range(14):                                     # spines
        a = k * 2.4
        x, y = 24 + math.cos(a) * 10.5, by - 2 + math.sin(a) * 13
        s.flat(box(s.X, s.Y, x, y, 0.5, 0.5), H["cream"][4])
    for side in (-1, 1):                                    # cactus arms
        if side > 0 and (p.wave or p.talk):
            hx, hy2 = (38 + p.f * 2, by - 18) if p.wave else (38, by - 6 - p.f * 2)
            s.paint(capsule(s.X, s.Y, (33, by - 2), (hx, hy2), 3.2), CACTUS, rim=1, mottle=0)
        else:
            x0 = 24 + side * 11
            s.paint(capsule(s.X, s.Y, (x0, by), (x0 + side * 4, by), 3.2), CACTUS[:4], rim=1, mottle=0)
            s.paint(capsule(s.X, s.Y, (x0 + side * 4, by), (x0 + side * 4, by - 8 - p.breathe), 3.0), CACTUS[:4],
                    rim=1, mottle=0)
    for k in range(5):                                      # flower
        a = k / 5 * math.tau + p.breathe * 0.2
        s.paint(circle(s.X, s.Y, 24 + math.cos(a) * 3.2, by - 18 + math.sin(a) * 2.4, 2.4), H["rose"][1:], rim=1,
                mottle=0)
    s.dab(24, by - 18, 1.6, H["yellow"][4])
    hy = by - 6
    eyes(s, [(26, hy), (31, hy)], p)
    s.dab(23.5, hy + 3, 1.3, (240, 130, 130), 0.4)
    mouth(s, 28.5, hy + 4, p, (40, 60, 30), 1.6)


# ---------------------------------------------------------------- ice
def frostmane(s, X, Y, p):
    low = 8 if p.sit else 0
    by = 52 + p.bob + low
    shadow(s, 24, 16)
    if p.sit:
        seat(s)
    legs(s, p, by + 14, H["snow"], foot=H["ice"], spread=7, width=5.2, foot_w=5)
    arm(s, p, (13, by - 6), H["snow"], back=True, width=4.6, reach=14)
    body = ellipse(X, Y, 23, by, 16, 19)
    s.paint(body, H["snow"], **MATTE)
    for k in range(18):                                     # shaggy fur tufts
        a = k / 18 * math.tau
        x, y = 23 + math.cos(a) * 14.5, by + math.sin(a) * 17.5
        if math.sin(a) > -0.3:                                  # tufts on the sides and belly only
            s.stroke([(x, y), (x + math.cos(a) * 2.6, y + math.sin(a) * 2.8 + 1.2)], 2.0, H["snow"][3])
    hy = by - 7
    s.paint(ellipse(s.X, s.Y, 30, hy, 7, 6), H["ice"][:4], rim=1, mottle=0)                # blue face
    eyes(s, [(28.5, hy - 1.5), (33, hy - 1.5)], p, 0.9)
    s.stroke([(27, hy - 4.5), (30, hy - 4)], 1.0, H["snow"][4])                              # bushy brows
    s.stroke([(32, hy - 4), (35, hy - 4.5)], 1.0, H["snow"][4])
    mouth(s, 31, hy + 3, p, (40, 50, 80), 1.8)
    for x in (28.5, 33.5):                                   # little tusks
        s.paint(poly(s.X, s.Y, [(x - 1, hy + 3.5), (x + 1, hy + 3.5), (x, hy + 6.5)]), H["bone"][2:], rim=0, mottle=0)
    arm(s, p, (33, by - 4), H["snow"], width=4.6, reach=13)


def tuxar(s, X, Y, p):
    low = 3 if p.sit else 0
    by = 62 + p.bob + low
    shadow(s, 24, 13)
    if p.sit:
        seat(s)
    if not p.sit:
        for side, d in ((-1, -p.sw * 0.5), (1, p.sw * 0.5)):               # orange feet
            s.paint(ellipse(s.X, s.Y, 25 + side * 5 + d, FOOT - 1.5, 5, 2.2), H["orange"][:4], rim=1, mottle=0)
    body = ellipse(X, Y, 24, by - 4, 12.5, 17)
    s.paint(body, NAVY, **MATTE)
    s.paint(ellipse(X, Y, 27, by, 8, 12), H["snow"], rim=0, mottle=0.04)                  # belly
    flip = 0
    if p.wave:
        flip = -12 - p.f * 3
    elif p.talk:
        flip = -6 + p.f * 2
    s.paint(ellipse(s.X, s.Y, 30, by - 4 + flip * 0.3, 3, 8.5, rot=0.4 + flip * 0.06), NAVY[1:], rim=1,
            mottle=0)                                                                       # flipper
    hy = by - 17
    s.paint(box(s.X, s.Y, 25, hy + 7, 10, 2.6, 1.2), H["red"], rim=1, mottle=0)           # knitted scarf
    s.stroke([(17, hy + 8), (14, hy + 16 + p.breathe)], 2.4, H["red"][2])
    for k in range(4):
        s.flat(box(s.X, s.Y, 19 + k * 4, hy + 7, 0.4, 2.4), H["red"][1])
    s.paint(subtract(ellipse(X, Y, 24, hy - 4, 10, 7), box(s.X, s.Y, 24, hy + 1, 12, 3)), H["teal"], **MATTE)  # beanie
    s.paint(circle(s.X, s.Y, 23, hy - 11, 2.4), H["cream"][2:], rim=0.5, mottle=0)
    s.paint(ellipse(s.X, s.Y, 29, hy + 1, 5, 4), H["snow"][1:], rim=0, mottle=0)          # face patch
    eyes(s, [(28, hy), (32, hy)], p, 0.9)
    beak = [(32, hy + 2), (37 + (1 if p.talk_open else 0), hy + 3.5), (32, hy + 5)]
    s.paint(poly(s.X, s.Y, beak), H["orange"], rim=1, mottle=0)
    if p.talk_open:
        s.flat(box(s.X, s.Y, 34, hy + 3.6, 2, 0.4), H["orange"][0])


# ---------------------------------------------------------------- volcanic
def emberkin(s, X, Y, p):
    low = 7 if p.sit else 0
    by = 56 + p.bob + low
    shadow(s, 24, 14)
    if p.sit:
        seat(s)
    legs(s, p, by + 8, H["darkstone"], spread=6, width=4.4)
    arm(s, p, (14, by - 4), H["darkstone"], LAVA, back=True, width=3.8)
    body = box(X, Y, 23, by - 2, 12, 12, 5)
    s.paint(body, H["darkstone"], **MATTE, grain=0.05)
    for pts in ([(15, by - 10), (19, by - 4), (17, by + 3)], [(27, by - 12), (25, by - 3), (30, by + 4)],
                [(21, by + 2), (23, by + 8)]):                  # glowing cracks
        s.stroke(pts, 1.4, LAVA[3])
        s.stroke(pts, 0.6, LAVA[4])
    hy = by - 22
    flick = (0, 1.5, -1, 0.5)[p.f % 4] + p.breathe
    flame = poly(X, Y, [(14, hy + 9), (16, hy - 2), (19 + flick, hy - 15), (22, hy - 6), (25, hy - 19 + flick),
                        (29, hy - 6), (33 - flick, hy - 12), (35, hy + 2), (34, hy + 9)])
    s.paint(flame, LAVA, highlight=0.9, rim=0.3, mottle=0)
    s.paint(ellipse(s.X, s.Y, 25, hy + 3, 7.5, 6), LAVA[2:], rim=0, mottle=0)
    for x in (24, 29.5):                                    # dark coal eyes
        if p.blink:
            s.flat(box(s.X, s.Y, x, hy + 2, 1.5, 0.5), (50, 14, 8))
        else:
            s.flat(ellipse(s.X, s.Y, x, hy + 2, 1.3, 1.8), (50, 14, 8))
    mouth(s, 27, hy + 6.5, p, (110, 30, 10), 1.6)
    arm(s, p, (32, by - 4), H["darkstone"], LAVA, width=3.8)


def salamandrite(s, X, Y, p):
    low = 8 if p.sit else 0
    by = 54 + p.bob + low
    R = H["red"]
    shadow(s, 22, 16)
    if p.sit:
        seat(s)
    tail = [(14, by + 6), (7, by + 14), (3 + math.sin(p.ph) * 2, FOOT - 4), (8, FOOT - 1)]
    s.stroke(tail, 4.6, R[1], taper=True)
    s.stroke(tail[:3], 1.6, R[3], 0.5, taper=True)
    legs(s, p, by + 10, R, foot=H["darkstone"], spread=5, width=3.8)
    arm(s, p, (17, by - 4), R, back=True, width=3.0)
    s.paint(ellipse(X, Y, 23, by, 10.5, 13), R, **MATTE)
    s.paint(box(X, Y, 25, by - 2, 8, 8, 3), H["steel"], rim=1, mottle=0, highlight=0.5)   # heat plate
    for y in (by - 6, by - 1, by + 4):
        s.flat(box(s.X, s.Y, 25, y, 7, 0.4), H["steel"][1])
    hy = by - 17
    for k in range(4):                                       # frill
        a = -1.9 + k * 0.45
        s.paint(poly(s.X, s.Y, [(24, hy), (24 + math.cos(a) * 12, hy + math.sin(a) * 11),
                                (24 + math.cos(a + 0.3) * 10, hy + math.sin(a + 0.3) * 9)]), H["orange"], rim=1,
                mottle=0)
    s.paint(ellipse(X, Y, 29, hy + 1, 10, 7), R, **MATTE)
    for x in (30, 35):
        if p.blink:
            s.flat(box(s.X, s.Y, x, hy - 1, 1.5, 0.5), INK)
        else:
            s.dab(x, hy - 1, 1.8, H["yellow"][4])
            s.flat(box(s.X, s.Y, x + 0.4, hy - 1, 0.5, 1.4), INK)
    mouth(s, 34, hy + 4, p, R[0], 2.4)
    arm(s, p, (31, by - 4), R, width=3.0)


# ---------------------------------------------------------------- crystal
def geodite(s, X, Y, p):
    low = 2 if p.sit else 0
    by = 66 + p.bob + low
    shadow(s, 24, 15)
    if not p.sit:
        for side, d in ((-1, -p.sw * 0.5), (1, p.sw * 0.5)):
            s.paint(ellipse(s.X, s.Y, 24 + side * 7 + d, FOOT - 2, 5.5, 3), H["coolstone"][:4], rim=1, mottle=0)
    arm(s, p, (12, by - 8), H["coolstone"], back=True, width=3.0, reach=9)
    shell = ellipse(X, Y, 23, by - 8, 15.5, 16)
    s.paint(shell, H["coolstone"], **MATTE, grain=0.06)
    open_ = ellipse(X, Y, 28, by - 8, 9, 11)                    # the split, full of crystals
    s.flat(open_, H["violet"][0])
    for dx, dy, h in ((-5, 7, 10), (-1, 8, 14), (3, 7, 11), (6, 8, 8), (-3, -6, -7), (3, -7, -9)):
        x0, y0 = 28 + dx, by - 8 + dy
        s.paint(intersect(open_, poly(s.X, s.Y, [(x0 - 2, y0), (x0, y0 - h), (x0 + 2, y0)])), H["violet"][1:],
                rim=0, mottle=0, highlight=0.6)
    s.flat(subtract(open_, ellipse(s.X, s.Y, 28, by - 8, 8, 10)), H["coolstone"][0])
    hy = by - 9
    for x in (26, 31):                                       # eyes peeking out of the geode
        if p.blink:
            s.flat(box(s.X, s.Y, x, hy, 1.6, 0.5), (255, 240, 255))
        else:
            s.dab(x, hy, 2.0, (255, 245, 255))
            s.dab(x + 0.6, hy, 1.1, INK)
    mouth(s, 28.5, hy + 5, p, H["violet"][4], 1.4)
    arm(s, p, (35, by - 8), H["coolstone"], width=3.0, reach=9)


def facet_snail(s, X, Y, p):
    glide = (0, 1, 0, -1)[p.f] if p.walk else 0
    by = 70
    shadow(s, 24, 17)
    foot = box(X, Y, 25 + glide, by + 6, 17, 4.5, 4)                 # soft body
    s.paint(foot, FLESH_PINK, **MATTE)
    s.flat(box(s.X, s.Y, 25 + glide, by + 9.5, 16, 0.8), FLESH_PINK[4], 0.5)                 # slime sheen
    hx = 38 + glide
    s.paint(capsule(s.X, s.Y, (34 + glide, by + 4), (hx, by - 8 - p.breathe), 4.2), FLESH_PINK, rim=1, mottle=0)
    for k, dx in enumerate((-2, 3)):                            # eyestalks
        tip = (hx + dx + (2 if p.wave and k else 0), by - 20 - (p.f * 2 if p.wave and k else 0) - p.breathe)
        s.stroke([(hx + dx * 0.4, by - 10), tip], 1.4, FLESH_PINK[2])
        if p.blink:
            s.flat(box(s.X, s.Y, tip[0], tip[1], 1.6, 0.5), FLESH_PINK[0])
        else:
            s.dab(tip[0], tip[1], 2.0, FLESH_PINK[3])
            s.dab(tip[0] + 0.5, tip[1], 1.0, INK)
    mouth(s, hx + 2, by - 5, p, FLESH_PINK[0], 1.2)
    sy = by - 14 + (2 if p.sit else 0)                          # the crystal shell
    shell = ellipse(X, Y, 21 + glide, sy, 13, 12)
    s.paint(shell, H["cyan"], rim=1, mottle=0.05, highlight=0.7)
    for k in range(3):
        s.stroke([(21 + glide, sy), (21 + glide + math.cos(k * 2.1) * (10 - k * 3), sy + math.sin(k * 2.1) * (9 - k * 3))],
                 1.0, H["cyan"][1], 0.6)
    for dx, h in ((-8, 9), (-3, 13), (3, 10), (8, 7)):
        x0 = 21 + glide + dx
        s.paint(poly(s.X, s.Y, [(x0 - 2.4, sy - 8), (x0, sy - 8 - h), (x0 + 2.4, sy - 8)]), H["violet"][1:], rim=1,
                mottle=0, highlight=0.7)


# ---------------------------------------------------------------- toxic
def blobbin(s, X, Y, p):
    squish = (0, 1.5, 0, 1.5)[p.f] if p.walk else p.breathe * 0.8
    by = 72 + (2 if p.sit else 0)
    shadow(s, 24, 17)
    body = smooth_blob(X, Y, by, squish, p)
    s.paint(body, SLIME, alpha=0.85, rim=1, mottle=0.05, highlight=0.8)
    s.paint(ellipse(s.X, s.Y, 20, by + 3, 3.2, 3), H["steel"], rim=1, mottle=0, alpha=0.7)  # a swallowed bolt
    s.flat(box(s.X, s.Y, 20, by + 3, 1.6, 0.5), H["steel"][0], 0.7)
    for bx, bb, r in ((28, 6, 1.4), (16, -2, 1.0), (24, 9 - p.f * 2, 0.9)):
        s.flat(subtract(circle(s.X, s.Y, bx, by + bb, r + 0.6), circle(s.X, s.Y, bx, by + bb, r)),
               SLIME[4], 0.8)
    hy = by - 15 + squish
    eyes(s, [(25, hy), (31, hy)], p, 1.4)
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, 28, hy + 5, 2.6, 1.8), SLIME[0])
    else:
        s.stroke([(24.5, hy + 4), (28, hy + 5.6), (31.5, hy + 4)], 1.0, SLIME[0])
    if p.wave or p.talk:                                        # a pseudopod waves
        tip = (40 + p.f * 2, by - 16) if p.wave else (40, by - 4 - p.f * 2)
        s.paint(capsule(s.X, s.Y, (34, by - 2), tip, 3.4, 2.4), SLIME, alpha=0.9, rim=1, mottle=0)


def smooth_blob(X, Y, by, squish, p):
    base = ellipse(X, Y, 24, by - 6 + squish * 0.5, 17 + squish, 17 - squish)
    top = circle(X, Y, 27, by - 16 + squish, 9)
    return np.minimum(base, top)


def toadwarden(s, X, Y, p):
    low = 6 if p.sit else 0
    by = 58 + p.bob + low
    shadow(s, 24, 16)
    if p.sit:
        seat(s)
    s.stroke([(41, 40 + low), (42, FOOT)], 2.2, H["wood"][1])                    # walking stick
    legs(s, p, by + 8, TOAD, spread=7, width=4.4)
    if not p.sit:
        for side in (-1, 1):
            s.paint(ellipse(s.X, s.Y, 25 + side * 7 + p.sw * 0.7 * side, FOOT - 1.5, 5, 2), TOAD[1:], rim=1,
                    mottle=0)
    body = ellipse(X, Y, 23, by - 4, 15, 14)
    s.paint(body, TOAD, **MATTE)
    s.paint(ellipse(s.X, s.Y, 27, by, 9, 8), H["sand"][2:], rim=0, mottle=0)                 # pale belly
    s.paint(box(X, Y, 21, by - 6, 11, 7, 3), H["rust"][:4], rim=1, mottle=0)                # vest
    s.dab(27, by - 8, 1, H["amber"][4])
    s.dab(27, by - 4, 1, H["amber"][4])
    hy = by - 18
    s.paint(ellipse(X, Y, 26, hy + 2, 12, 7.5), TOAD, **MATTE)
    for x in (22, 30):                                          # bulging eyes on top
        s.paint(circle(s.X, s.Y, x, hy - 4, 3.4), TOAD[1:], rim=1, mottle=0)
        if p.blink:
            s.flat(box(s.X, s.Y, x, hy - 4, 2.2, 0.5), TOAD[0])
        else:
            s.dab(x, hy - 4, 2.2, H["yellow"][3])
            s.flat(box(s.X, s.Y, x + 0.5, hy - 4, 1.6, 0.6), INK)
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, 29, hy + 5, 6, 1.8), (70, 30, 40))
    else:
        s.stroke([(18, hy + 4), (28, hy + 5.5), (37, hy + 3.5)], 1.0, TOAD[0])
    s.paint(subtract(ellipse(X, Y, 26, hy - 9, 12, 5), box(s.X, s.Y, 26, hy - 4, 14, 2)), H["rose"], rim=1,
            mottle=0)                                                                         # toadstool hat
    s.dab(21, hy - 11, 1.2, H["cream"][4])
    s.dab(30, hy - 12, 1.4, H["cream"][4])
    hand = arm(s, p, (33, by - 6), TOAD, width=3.4) if p.wave or p.talk else None
    if hand is None:
        s.paint(capsule(s.X, s.Y, (33, by - 6), (40, 46 + low), 3.4), TOAD[:4], rim=1, mottle=0)
        s.paint(circle(s.X, s.Y, 41, 46 + low, 2.8), TOAD, rim=1, mottle=0)


# ---------------------------------------------------------------- ocean
def crabbit(s, X, Y, p):
    low = 6 if p.sit else 0
    by = 62 + p.bob + low
    R = H["red"]
    shadow(s, 24, 17)
    for k, x in enumerate((12, 17, 30, 35)):                      # four spindly legs
        d = (p.sw * 0.5 if k % 2 else -p.sw * 0.5)
        knee = (x + (-3 if x < 24 else 3), by + 2)
        s.stroke([(x, by - 2), knee, (x + d + (-2 if x < 24 else 2), FOOT - 1)], 2.4, R[1] if k % 2 else R[2])
    shell = ellipse(X, Y, 24, by - 8, 16, 10)
    s.paint(shell, R, **MATTE)
    s.speckle(shell, R[4], 0.06, seed=2)
    s.paint(ellipse(s.X, s.Y, 24, by - 3, 13, 4), H["cream"][2:], rim=0, mottle=0)            # pale underside
    hy = by - 18
    for k, dx in enumerate((-3, 4)):                              # eyestalks
        tip = (26 + dx, hy - 4 - p.breathe)
        s.stroke([(26 + dx * 0.5, hy + 4), tip], 1.6, R[2])
        if p.blink:
            s.flat(box(s.X, s.Y, tip[0], tip[1], 1.8, 0.5), INK)
        else:
            s.dab(tip[0], tip[1], 2.2, H["cream"][4])
            s.dab(tip[0] + 0.6, tip[1], 1.2, INK)
    mouth(s, 30, by - 9, p, R[0], 2.0)
    s.paint(ellipse(s.X, s.Y, 10, by - 10, 4, 3), R[:4], rim=1, mottle=0)                    # small claw
    if p.wave:
        cx, cy = 40 + p.f, by - 26 - p.f * 2
    elif p.talk:
        cx, cy = 42, by - 16 + p.f * 2
    else:
        cx, cy = 40, by - 14 + p.breathe
    s.stroke([(36, by - 8), (cx - 2, cy + 6)], 3.0, R[2])
    claw = subtract(ellipse(s.X, s.Y, cx, cy, 6.5, 5.5), poly(s.X, s.Y, [(cx + 1, cy), (cx + 8, cy - 4 + (2 if p.talk_open else 0)),
                                                                     (cx + 8, cy + 2)]))
    s.paint(claw, R, rim=1, mottle=0, highlight=0.6)                                          # the big claw


def octavian(s, X, Y, p):
    low = 6 if p.sit else 0
    by = 52 + low + p.breathe * 0.5
    V = H["magenta"]
    shadow(s, 24, 15)
    if p.sit:
        seat(s)
    for k in range(5):                                            # tentacle legs, curling at the tips
        x0 = 16 + k * 4
        sway = math.sin(p.ph + k * 1.3) * 2 + (p.sw * 0.3 * (1 if k % 2 else -1))
        end = (x0 + sway + (k - 2) * 2, FOOT - 3 - (low if p.sit else 0) * 0.3)
        curl = (end[0] + (2 if k >= 2 else -2), end[1] + 2)
        s.stroke([(x0, by + 10), (x0 + sway * 0.5, by + 18), end, curl], 3.2, V[1] if k % 2 else V[2],
                 taper=True)
    s.paint(box(X, Y, 24, by + 4, 11, 9, 3), H["teal"], **MATTE)                         # little coat
    s.flat(box(s.X, s.Y, 28, by + 4, 0.5, 8), H["teal"][0])
    for y in (by, by + 5):
        s.dab(29.5, y, 0.9, BRASS_DAB)
    hy = by - 10
    s.paint(ellipse(X, Y, 24, hy, 13, 12), V, **MATTE)                                    # the big head
    s.speckle(ellipse(s.X, s.Y, 24, hy, 13, 12), V[4], 0.05, seed=9)
    eyes(s, [(26, hy + 2), (32, hy + 2)], p, 1.2)
    s.flat(subtract(circle(s.X, s.Y, 32, hy + 2, 3.2), circle(s.X, s.Y, 32, hy + 2, 2.5)), (230, 200, 90))  # monocle
    s.stroke([(34.5, hy + 3), (35, hy + 9)], 0.5, (230, 200, 90))
    mouth(s, 29, hy + 7, p, V[0], 1.4)
    tip = hand_at(p, (33, by + 2), 10)                             # a tentacle used as an arm
    s.stroke([(32, by + 2), ((32 + tip[0]) / 2 + 2, (by + 2 + tip[1]) / 2), tip], 2.6, V[2], taper=True)


BRASS_DAB = (230, 190, 80)


# ---------------------------------------------------------------- barren
def moonmole(s, X, Y, p):
    low = 7 if p.sit else 0
    by = 56 + p.bob + low
    shadow(s, 24, 15)
    if p.sit:
        seat(s)
    legs(s, p, by + 8, FUR_GREY, spread=6, width=4.2)
    body = ellipse(X, Y, 23, by - 4, 14, 15)
    s.paint(body, FUR_GREY, **MATTE)
    s.speckle(body, FUR_GREY[3], 0.12, seed=7)
    s.paint(box(X, Y, 23, by + 2, 12, 4, 2), H["amber"][:4], rim=1, mottle=0)             # tool belt
    s.paint(box(s.X, s.Y, 15, by + 3, 2, 3, 0.8), H["steel"], rim=1, mottle=0)
    hy = by - 14
    s.paint(ellipse(X, Y, 28, hy + 2, 10, 8), FUR_GREY, **MATTE)
    s.paint(ellipse(s.X, s.Y, 36, hy + 4, 3, 2.4), H["rose"], rim=1, mottle=0, highlight=0.7)   # pink nose
    for x in (29, 33):                                             # tiny squinty eyes
        s.flat(box(s.X, s.Y, x, hy + 1, 1.2, 0.5 if p.blink else 0.8, 0.3), INK)
    mouth(s, 33, hy + 7, p, (60, 40, 40), 1.4)
    s.paint(subtract(ellipse(X, Y, 26, hy - 5, 11, 7), box(s.X, s.Y, 26, hy + 1, 13, 3)), H["yellow"], **MATTE)  # helmet
    s.paint(box(s.X, s.Y, 35, hy - 6, 2.4, 2.4, 1), H["steel"], rim=1, mottle=0)
    s.dab(37, hy - 6, 2.2, H["yellow"][4])
    s.flat(poly(s.X, s.Y, [(37, hy - 8), (47, hy - 12), (47, hy)]), H["yellow"][4], 0.25)    # headlamp beam
    hand = hand_at(p, (33, by - 4), 10)
    s.paint(capsule(s.X, s.Y, (32, by - 4), hand, 3.8), FUR_GREY[1:], rim=1, mottle=0)
    for k in range(3):                                              # big digging claws
        s.stroke([(hand[0] + 1, hand[1] - 1 + k * 1.5), (hand[0] + 4.5, hand[1] + k * 1.6)], 1.0, H["bone"][3])


def dishhead(s, X, Y, p):
    low = 10 if p.sit else 0
    by = 54 + p.bob + low
    shadow(s, 24, 15)
    if p.sit:
        seat(s)
    legs(s, p, by + 10, H["steel"], foot=H["darkstone"], spread=5, width=3.4)
    for side in (-1, 1):                                            # solar panel wings
        x0 = 24 + side * 11
        tilt = (2 if (p.wave and side > 0) else 0) * (p.f + 1)
        panel = poly(s.X, s.Y, [(x0, by - 10), (x0 + side * 11, by - 14 - tilt), (x0 + side * 11, by + 2 - tilt),
                                (x0, by + 4)])
        s.paint(panel, CELL if side > 0 else CELL[:4], rim=1, mottle=0)
        for k in range(1, 3):
            s.stroke([(x0 + side * k * 3.7, by - 11 - tilt * k / 3), (x0 + side * k * 3.7, by + 3 - tilt * k / 3)],
                     0.6, CELL[0], 0.8)
    s.paint(box(X, Y, 24, by - 3, 10, 10, 2.5), H["steel"], **MATTE)
    s.flat(box(s.X, s.Y, 24, by - 3, 6, 4, 1), (30, 34, 44))                               # status screen
    for k in range(3):
        s.flat(box(s.X, s.Y, 21 + k * 3, by - 3 - (k == 1) * (1 + p.f), 0.8, 1.6), H["lime"][4] if p.talk else
               H["lime"][2])
    hy = by - 20
    s.stroke([(24, by - 13), (26, hy + 4)], 1.6, H["steel"][1])
    dish = subtract(ellipse(X, Y, 27, hy, 10, 8, rot=-0.5), ellipse(s.X, s.Y, 30, hy - 2, 8.5, 6.5, rot=-0.5))
    s.paint(ellipse(X, Y, 27, hy, 10, 8, rot=-0.5), H["steel"][1:], rim=1, mottle=0)
    s.paint(dish, H["steel"], rim=1, mottle=0)
    s.stroke([(29, hy - 1), (36, hy - 9)], 0.9, H["steel"][3])                             # feed horn
    s.dab(36, hy - 9, 1.2, H["steel"][4])
    blink_col = H["red"][4] if not p.blink else H["red"][1]
    s.dab(27, hy + 1, 2.4, blink_col, 0.35)
    s.dab(27, hy + 1, 1.4, blink_col)


NATIVES = [barkling, mothkin, dunestrider, cactling, frostmane, tuxar, emberkin, salamandrite,
           geodite, facet_snail, blobbin, toadwarden, crabbit, octavian, moonmole, dishhead]
# face centres in design space, for the dialogue portrait crop
NATIVE_FACES = [(28, 46), (27, 37), (33, 44), (27, 48), (28, 43), (28, 40), (25, 33), (29, 37),
                (27, 56), (38, 58), (27, 54), (26, 40), (27, 48), (26, 42), (30, 40), (27, 33)]
