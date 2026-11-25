"""Frontier settlers: eight far-future peoples (see stellar_forge/systems/species.py,
same order), painted in every pose the camp needs.

Each look gets: idle0/idle1 (breathing), blink, walk0-3, wave0/1, talk0/1, sit0/1.
They face right; the game flips them. Output: generated/poi/npc/<look>_<pose>.png
"""
from __future__ import annotations

import math

from .common import MATTE, H, Sprite, box, capsule, circle, ellipse, poly, save, subtract, union
from pixelkit import hexc, intersect, ramp

W, HH = 64, 84
K = 1.35            # how much wider than the 48-px design space each figure is painted (chunky, like the pilot)
FOOT = 81
INK = (22, 18, 30)
GLASS = ramp(*map(hexc, ("2c5a78", "4b8db0", "79c2dc", "b4e6f2", "eafaff")))
JELLY = ramp(*map(hexc, ("6a2a6e", "a0428c", "d266a8", "f095c4", "ffd0e6")))
AXO = ramp(*map(hexc, ("8a3a52", "c25a74", "e88a9a", "f6b4bc", "ffe0e2")))
BRASS = ramp(*map(hexc, ("5a3c14", "8c6224", "bc8e36", "e0b852", "f6e08a")))
VOID = ramp(*map(hexc, ("100c1e", "1e1838", "2e2652", "463a72", "5e5290")))

POSES = {"idle0": ("idle", 0), "idle1": ("idle", 1), "blink": ("blink", 0),
         "walk0": ("walk", 0), "walk1": ("walk", 1), "walk2": ("walk", 2), "walk3": ("walk", 3),
         "wave0": ("wave", 0), "wave1": ("wave", 1), "talk0": ("talk", 0), "talk1": ("talk", 1),
         "sit0": ("sit", 0), "sit1": ("sit", 1)}


class P:
    """Pose parameters every painter reads."""

    def __init__(self, pose):
        self.kind, self.f = POSES[pose]
        k, f = self.kind, self.f
        self.breathe = f if k in ("idle", "sit") else 0
        self.walk = k == "walk"
        self.sw = (6, 2, -6, -2)[f] if self.walk else 0           # leg swing
        self.bob = (0, -1, 0, -1)[f] if self.walk else 0
        self.blink = k == "blink"
        self.talk_open = k == "talk" and f == 0
        self.talk = k == "talk"
        self.wave = k == "wave"
        self.sit = k == "sit"
        self.ph = f * math.pi / 2 + (0.0 if k != "idle" else f * 1.3)   # sway phase


def shadow(s, cx=24, w=11):
    s.flat(ellipse(s.X, s.Y, cx, FOOT - 0.5, w, 1.6), (10, 10, 20), 0.28)


def eyes(s, pts, p, r=1.0, col=INK, shine=True):
    for x, y in pts:
        if p.blink:
            s.flat(box(s.X, s.Y, x, y + 0.4, r + 0.5, 0.45), col)
        else:
            s.flat(box(s.X, s.Y, x, y, r * 0.9, r * 1.4, 0.3), col)
            if shine:
                s.dab(x + 0.3, y - 0.8, 0.45, (250, 250, 255))


def glow_eyes(s, pts, p, col, r=1.2):
    for x, y in pts:
        if p.blink:
            s.flat(box(s.X, s.Y, x, y, r + 0.4, 0.4), col, 0.7)
        else:
            s.dab(x, y, r + 0.9, col, 0.3)
            s.dab(x, y, r, col)
            s.dab(x, y, r * 0.45, (255, 255, 240))


# ---------------------------------------------------------------- 0 Lumen
def lumen(s, X, Y, p):
    lift = 3 if p.sit else 8 + p.breathe + (p.bob * 2)
    cy = 30 - lift + 8
    shadow(s, 24, 10)
    # tentacles under the collar, swaying (trailing back when drifting)
    base = cy + 15
    for k, tx in enumerate((15, 19, 23, 27, 31)):
        if p.wave and k == 4:
            pts = [(tx, base), (tx + 6, base - 6), (tx + 9, base - 15 - p.f * 3)]
        else:
            ln = 10 if p.sit else 22 - abs(k - 2) * 2
            sway = math.sin(p.ph + k * 1.1) * 2.2 - (4 if p.walk else 0)
            pts = [(tx, base), (tx + sway * 0.5, base + ln * 0.5), (tx + sway + (k - 2) * (2 if p.sit else 0.6),
                                                                    base + ln)]
        s.stroke(pts, 3.0, JELLY[1], taper=True)
        s.stroke(pts[:2], 1.0, JELLY[3], 0.6)
    s.paint(box(s.X, s.Y, 24, cy + 15, 12, 2.6, 1.2), BRASS, rim=1, mottle=0)       # collar
    for x in (15, 21, 27, 33):
        s.dab(x, cy + 15, 0.7, BRASS[4])
    # the jelly
    bell = subtract(ellipse(X, Y, 25, cy + 1, 10, 9.5), box(s.X, s.Y, 25, cy + 12, 12, 3))
    s.paint(bell, JELLY, highlight=0.7 + (0.4 if p.talk else 0), mottle=0.05, bias=0.12 if p.talk else 0)
    for k in range(3):
        s.stroke([(18 + k * 5, cy + 9), (19 + k * 5, cy + 12)], 1.0, JELLY[4], 0.7)
    eyes(s, [(27.5, cy), (31.5, cy)], p, 0.9)
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, 30, cy + 4.2, 1.4, 1.0), JELLY[0])
    # glass dome over it all
    dome = circle(X, Y, 24, cy, 14.5)
    s.paint(dome, GLASS, alpha=0.28, rim=0, mottle=0, flat=0.6)
    s.flat(subtract(dome, circle(s.X, s.Y, 24, cy, 13.4)), GLASS[3], 0.75)
    s.stroke([(15, cy - 4), (17, cy - 9), (21, cy - 12)], 1.4, (255, 255, 255), 0.75)
    s.dab(31, cy - 9, 0.9, (255, 255, 255), 0.8)


# ---------------------------------------------------------------- 1 Mossback
def mossback(s, X, Y, p):
    low = 10 if p.sit else 0
    by = 54 + p.breathe + p.bob + low
    shadow(s, 24, 15)
    if not p.sit:
        for side, d in ((-1, -p.sw * 0.6), (1, p.sw * 0.6)):
            hx = 24 + side * 7
            rmp = H["stone"][:3] if side < 0 else H["stone"][:4]
            s.paint(capsule(s.X, s.Y, (hx, by + 8), (hx + d, FOOT - 3), 4.2, 4.6), rmp, rim=1, mottle=0)
            s.paint(box(s.X, s.Y, hx + d + 1.5, FOOT - 1.5, 5, 2.2, 1.2), H["darkstone"], rim=1, mottle=0)
    else:
        s.paint(ellipse(s.X, s.Y, 33, FOOT - 3, 7, 3.5), H["stone"][:4], rim=1, mottle=0)
    # staff (behind the hand)
    staff = [(41, 34 + low), (42, FOOT)]
    s.stroke(staff, 2.2, H["wood"][1])
    s.stroke(staff, 1.0, H["wood"][3], 0.6)
    # body: a hunched boulder with moss on the shoulders
    body = ellipse(X, Y, 23, by - 4, 15.5, 15)
    s.paint(body, H["stone"], **MATTE, grain=0.05)
    moss = intersect(body, ellipse(X, Y, 21, by - 15, 16, 9))
    s.paint(moss, H["green"], rim=0.4, mottle=0.12)
    s.speckle(moss, H["lime"][3], 0.12, seed=3)
    for x, y in ((14, by - 2), (19, by + 4), (28, by + 2)):                       # cracks
        s.stroke([(x, y), (x + 2, y + 3), (x + 1, y + 5)], 0.8, H["stone"][0], 0.8)
    # sapling growing on the back
    s.stroke([(15, by - 16), (13, by - 26), (14, by - 32)], 1.4, H["wood"][1])
    for lx, ly in ((11, by - 27), (16, by - 30), (12, by - 33), (17, by - 25)):
        s.paint(ellipse(s.X, s.Y, lx, ly, 2.6, 1.6, rot=0.5), H["green"][1:], rim=0.5, mottle=0)
    # head jutting forward under a heavy brow
    hy = by - 4
    s.paint(ellipse(X, Y, 35, hy, 8.5, 7.5), H["stone"], **MATTE)
    s.paint(box(s.X, s.Y, 36, hy - 4.5, 8, 2.2, 1.5), H["stone"][:4], rim=1, mottle=0)
    glow_eyes(s, [(36.5, hy - 1), (40.5, hy - 1)], p, H["amber"][4], 1.0)
    if p.talk_open:
        s.flat(box(s.X, s.Y, 38.5, hy + 4, 3.5, 1.4, 0.5), (30, 24, 30))
    else:
        s.stroke([(35, hy + 4), (42, hy + 3.5)], 1.0, H["stone"][0])
    s.paint(ellipse(s.X, s.Y, 39, hy + 6, 4, 2.2), H["green"][:4], rim=0.5, mottle=0)      # mossy beard
    # arm holding the staff
    hand = (44 + p.f, by - 14 - p.f * 3) if p.wave else ((40, by + 1) if p.talk and p.f else (41, by + 4))
    s.paint(capsule(s.X, s.Y, (29, by + 1), hand, 4.0, 3.4), H["stone"][:4], rim=1, mottle=0)
    s.paint(circle(s.X, s.Y, hand[0] + 0.5, hand[1], 3.4), H["stone"], rim=1, mottle=0)


# ---------------------------------------------------------------- 2 Tik
def tik(s, X, Y, p):
    low = 14 if p.sit else 0
    by = 40 + p.bob + low + p.breathe * 0.5
    shadow(s, 24, 11)
    # stilt legs
    for side, d in ((-1, -p.sw), (1, p.sw)):
        hx = 24 + side * 4
        rmp = H["steel"][:3] if side < 0 else H["steel"]
        if p.sit:
            s.stroke([(hx, by + 8), (hx + 8, by + 18), (hx + 4, FOOT - 1)], 2.4, rmp[1])
        else:
            knee = (hx + d * 0.5 + 2, by + 22)
            s.stroke([(hx, by + 8), knee, (hx + d, FOOT - 2)], 2.4, rmp[1])
            s.dab(knee[0], knee[1], 1.8, rmp[-1])
        s.paint(box(s.X, s.Y, hx + (0 if p.sit else d) + 1, FOOT - 1, 3.4, 1.4, 0.7), H["darkstone"], rim=1,
                mottle=0)
    # antenna
    s.stroke([(17, by - 8), (14, by - 18), (15, by - 22)], 1.0, H["steel"][1])
    s.dab(15, by - 23, 1.6, H["red"][4] if p.f % 2 == 0 else H["yellow"][4])
    # body: a dented box with a scrap satchel
    s.paint(box(X, Y, 23, by, 12, 10, 3), H["rust"], **MATTE, grain=0.06)
    s.paint(box(s.X, s.Y, 13, by + 4, 3, 5, 1.2), H["wood"][:4], rim=1, mottle=0)       # satchel
    s.stroke([(14, by - 6), (29, by + 6)], 0.9, H["wood"][1], 0.9)
    for x, y in ((15, by - 6), (31, by - 6), (15, by + 6), (31, by + 7)):
        s.dab(x, y, 0.7, H["rust"][4])
    for k in range(3):                                                             # speaker grille
        s.flat(box(s.X, s.Y, 21, by + 3 + k * 2, 4, 0.4), H["yellow"][4] if p.talk else H["rust"][0],
               0.9 if p.talk else 0.8)
    # the big eye
    s.paint(circle(s.X, s.Y, 29, by - 2, 6.5), H["steel"], rim=1, mottle=0)
    if p.blink:
        s.paint(box(s.X, s.Y, 29, by - 2, 4.8, 4.8, 2), H["steel"][:4], rim=0.5, mottle=0)
        s.flat(box(s.X, s.Y, 29, by - 2, 4.8, 0.4), H["steel"][0])
    else:
        lens = H["cyan"] if not p.talk else H["cyan"][1:] + [(255, 255, 255)]
        s.paint(circle(s.X, s.Y, 30, by - 2, 4.4), lens, highlight=0.9, rim=0.5, mottle=0)
        s.dab(31, by - 2, 1.6, INK)
        s.dab(28.6, by - 4, 1.0, (255, 255, 255))
    # manipulator arm
    if p.wave:
        pts = [(33, by + 3), (38, by - 4), (37 + p.f * 3, by - 12)]
    elif p.talk:
        pts = [(33, by + 3), (38, by + 6), (42, by + 2 - p.f * 2)]
    else:
        pts = [(33, by + 3), (36, by + 9), (35, by + 15)]
    s.stroke(pts, 1.3, H["steel"][2])
    s.dab(pts[1][0], pts[1][1], 1.2, H["steel"][3])
    ex, ey = pts[2]
    s.stroke([(ex, ey), (ex + 2, ey - 1.5)], 1.0, H["steel"][3])
    s.stroke([(ex, ey), (ex + 2, ey + 1.5)], 1.0, H["steel"][3])


# ---------------------------------------------------------------- 3 Sporeling
def sporeling(s, X, Y, p):
    low = 4 if p.sit else 0
    by = 66 + p.bob + low
    tilt = (p.sw * 0.25) if p.walk else (0.5 * p.breathe)
    shadow(s, 24, 13)
    # root feet
    if not p.sit:
        for side, d in ((-1, -p.sw * 0.5), (1, p.sw * 0.5)):
            fx = 24 + side * 5 + d
            s.paint(ellipse(s.X, s.Y, fx + 1, FOOT - 2, 4.4, 2.6), H["bone"][:4], rim=1, mottle=0)
            s.stroke([(fx + 4, FOOT - 1), (fx + 6, FOOT)], 0.8, H["bone"][1])
    else:
        s.paint(ellipse(s.X, s.Y, 24, FOOT - 2, 10, 3), H["bone"][:4], rim=1, mottle=0)
    # stalk body
    s.paint(box(X, Y, 24, by - 6, 8, 14 - low, 5), H["cream"], **MATTE)
    s.stroke([(16.5, by - 13), (24, by - 11), (31.5, by - 14)], 2.4, H["lime"][2])   # leaf scarf
    s.paint(ellipse(s.X, s.Y, 17, by - 9, 2.4, 4, rot=0.3), H["lime"][1:4], rim=0.5, mottle=0)
    # little arms
    if p.wave:
        s.stroke([(31, by - 8), (35, by - 15), (36 + p.f * 2, by - 21)], 2.4, H["cream"][2])
    elif p.talk:
        s.stroke([(31, by - 8), (36, by - 6), (39, by - 9 - p.f)], 2.4, H["cream"][2])
    else:
        s.stroke([(31, by - 8), (33, by - 2)], 2.4, H["cream"][2])
    s.stroke([(17, by - 8), (15, by - 2)], 2.4, H["cream"][1])
    # face under the cap
    hy = by - 21
    eyes(s, [(27, hy + 2), (31, hy + 2)], p, 1.1)
    s.dab(25, hy + 5, 1.3, (240, 130, 130), 0.4)
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, 29, hy + 6, 1.3, 1.1), (90, 40, 40))
    else:
        s.stroke([(27.5, hy + 6), (30.5, hy + 6)], 0.9, H["cream"][0])
    # the cap
    cx = 24 + tilt
    cap = subtract(ellipse(X, Y, cx, hy - 5, 19, 12), box(s.X, s.Y, cx, hy + 6, 22, 5))
    s.paint(cap, H["rose"], **MATTE)
    s.flat(box(s.X, s.Y, cx, hy + 0.5, 17, 0.9, 0.5), H["rose"][0])
    for dx, dy, r in ((-8, -10, 2.4), (2, -13, 2.0), (9, -7, 2.6), (-2, -6, 1.6), (13, -2, 1.4), (-13, -3, 1.5)):
        s.paint(circle(s.X, s.Y, cx + dx, hy + dy, r), H["cream"][2:], rim=0, mottle=0)
    if p.talk:                                                                    # spores
        for k in range(5):
            a = k * 1.3 + p.f * 0.7
            s.dab(cx + math.cos(a) * 12 + 4, hy - 18 - (k % 3) * 3 - p.f * 2, 0.9, H["yellow"][4], 0.85)


# ---------------------------------------------------------------- 4 Shardkin
def shardkin(s, X, Y, p):
    lift = 2 if p.sit else 5 + p.breathe + p.bob
    by = 52 - lift + (6 if p.sit else 0)
    V = H["violet"]
    shadow(s, 24, 10)
    # crystal legs (pointed, not touching the ground)
    if not p.sit:
        for side, d in ((-1, -p.sw * 0.4), (1, p.sw * 0.4)):
            lx = 24 + side * 4
            s.paint(poly(s.X, s.Y, [(lx - 4, by + 8), (lx + 4, by + 8), (lx + d + 0.5, FOOT - 3 - lift)]),
                    V[:3] if side < 0 else V[:4], rim=1, mottle=0)
    # torso: stacked facets
    torso = poly(X, Y, [(16, by - 8), (24, by - 16), (33, by - 9), (31, by + 9), (24, by + 12), (17, by + 8)])
    s.paint(torso, V, rim=1, mottle=0, highlight=0.6)
    s.flat(poly(s.X, s.Y, [(24, by - 16), (33, by - 9), (25, by - 2)]), V[4], 0.55)
    s.stroke([(24, by - 15), (25, by + 11)], 0.8, V[1], 0.7)
    # orbiting chips
    for k in range(3):
        a = p.ph * 0.8 + k * 2.1
        s.paint(poly(s.X, s.Y, [(24 + math.cos(a) * 15 - 1.5, by - 6 + math.sin(a) * 4),
                                (24 + math.cos(a) * 15, by - 9 + math.sin(a) * 4),
                                (24 + math.cos(a) * 15 + 1.5, by - 6 + math.sin(a) * 4)]), H["cyan"][2:], rim=0,
                mottle=0)
    # floating head: a gem with a glowing core
    hy = by - 27 - (1 if p.talk and p.f else 0)
    head = poly(X, Y, [(26, hy - 10), (34, hy - 2), (27, hy + 8), (18, hy)])
    s.paint(head, V, rim=1, mottle=0, highlight=0.8)
    s.flat(poly(s.X, s.Y, [(26, hy - 10), (34, hy - 2), (27, hy - 1)]), V[4], 0.5)
    core = H["cyan"][4] if not p.blink else H["cyan"][1]
    r = 2.4 if p.talk else 1.8
    s.dab(28, hy - 1, r + 2, H["cyan"][3], 0.35)
    s.dab(28, hy - 1, r, core)
    s.dab(28.5, hy - 1.5, r * 0.4, (255, 255, 255))
    # floating hands
    if p.wave:
        hands = [(16, by - 2), (37 + p.f * 2, by - 22)]
    elif p.talk:
        hands = [(16, by - 2), (38, by - 8 - p.f * 2)]
    else:
        hands = [(15, by + 1 + p.breathe), (35, by + 1 + p.breathe)]
    for k, (hx, hy2) in enumerate(hands):
        s.paint(poly(s.X, s.Y, [(hx, hy2 - 3.5), (hx + 2.6, hy2), (hx, hy2 + 3.5), (hx - 2.6, hy2)]),
                V[1:] if k else V[:4], rim=1, mottle=0)


# ---------------------------------------------------------------- 5 Hollow
def hollow(s, X, Y, p):
    lift = 1 if p.sit else 3 + p.breathe + p.bob
    hem = FOOT - lift
    sway = math.sin(p.ph) * 1.5 - (3 if p.walk else 0)
    shadow(s, 24, 12)
    # lantern staff
    sx = 38 if not p.wave else 40
    top = 26 - (6 if p.wave else 0) + (6 if p.sit else 0)
    s.stroke([(sx, top), (sx + 1, FOOT - (8 if p.sit else 0))], 1.6, H["wood"][1])
    s.dab(sx, top - 1, 6, H["amber"][4], 0.25)
    s.paint(box(s.X, s.Y, sx, top + 1, 2.6, 3.4, 1.2), BRASS, rim=1, mottle=0)
    s.dab(sx, top + 1, 1.5, H["yellow"][4])
    # robe: widening, ragged hem
    pts = [(18, 34), (31, 34), (37 + sway, hem - 2), (34 + sway, hem), (30 + sway, hem - 2), (26 + sway, hem),
           (22 + sway, hem - 2), (17 + sway, hem), (12 + sway, hem - 2)]
    if p.sit:
        pts = [(18, 40), (31, 40), (38, hem), (11, hem)]
    s.paint(poly(X, Y, pts), VOID, **MATTE)
    s.stroke([(24, 38), (25 + sway, hem - 3)], 1.0, VOID[0], 0.7)                    # fold
    s.stroke([(20, 40), (17 + sway, hem - 6)], 0.8, VOID[3], 0.5)
    s.flat(box(s.X, s.Y, 24.5, 46 + (6 if p.sit else 0), 7, 1.0), BRASS[2])         # sash
    # hood with a starfield inside
    hy = 26 + (6 if p.sit else 0) + p.breathe * 0.5
    s.paint(ellipse(X, Y, 24, hy, 11, 12), VOID, **MATTE)
    s.paint(poly(s.X, s.Y, [(15, hy - 6), (20, hy - 15), (22, hy - 8)]), VOID[:4], rim=1, mottle=0)   # point
    opening = ellipse(s.X, s.Y, 28, hy + 1.5, 6.5, 8)
    s.flat(opening, (6, 4, 14))
    s.speckle(opening, (220, 220, 255), 0.18, seed=11)
    glow = (150, 230, 255)
    for x in (26.5, 31):
        if p.blink:
            s.flat(box(s.X, s.Y, x, hy + 1, 1.3, 0.35), glow, 0.8)
        else:
            s.dab(x, hy + 1, 1.8 if p.talk else 1.2, glow, 0.35)
            s.dab(x, hy + 1, 0.9 if not p.talk_open else 1.2, (230, 250, 255))
    # wrapped hand
    if p.wave:
        hand = (36 + p.f * 2, hy - 2)
    elif p.talk:
        hand = (35, hy + 13 - p.f * 2)
    else:
        hand = (sx - 1.5, top + 18)
    s.paint(capsule(s.X, s.Y, (30, hy + 12), hand, 3.0, 2.4), VOID[1:], rim=1, mottle=0)
    s.paint(circle(s.X, s.Y, hand[0], hand[1], 2.2), H["bone"][1:4], rim=1, mottle=0)


# ---------------------------------------------------------------- 6 Gillwright
def gillwright(s, X, Y, p):
    low = 10 if p.sit else 0
    by = 56 + p.bob + p.breathe * 0.5 + low
    T = H["teal"]
    shadow(s, 24, 13)
    # chunky boots and legs
    if p.sit:
        s.paint(box(s.X, s.Y, 21, FOOT - 4, 11, 4, 2), H["wood"], **MATTE)          # a crate seat
        s.paint(capsule(s.X, s.Y, (24, by + 8), (34, FOOT - 3), 4.4, 4.0), T[:4], rim=1, mottle=0)
        s.paint(box(s.X, s.Y, 36, FOOT - 2, 4.6, 3, 1.4), BRASS, rim=1, mottle=0)
    else:
        for side, d in ((-1, -p.sw * 0.7), (1, p.sw * 0.7)):
            lx = 24 + side * 5
            s.paint(capsule(s.X, s.Y, (lx, by + 8), (lx + d, FOOT - 5), 4.4, 4.0), T[:3] if side < 0 else T[:4],
                    rim=1, mottle=0)
            s.paint(box(s.X, s.Y, lx + d + 1.5, FOOT - 2.5, 5, 3, 1.4), BRASS[:4] if side < 0 else BRASS, rim=1,
                    mottle=0)
    # back tank
    s.paint(box(s.X, s.Y, 12, by - 6, 3.6, 8, 3), BRASS, rim=1, mottle=0)
    s.stroke([(12, by - 14), (16, by - 20), (20, by - 22)], 1.2, H["steel"][2])     # hose to the bowl
    # round diving suit
    s.paint(ellipse(X, Y, 24, by - 4, 12, 13), T, **MATTE)
    s.flat(box(s.X, s.Y, 24, by + 6, 11.5, 1.4), BRASS[1])
    s.paint(circle(s.X, s.Y, 29, by - 6, 3), BRASS, rim=1, mottle=0, highlight=0.6)  # chest valve
    s.dab(29, by - 6, 1.0, H["cyan"][3])
    # collar ring
    s.paint(box(s.X, s.Y, 25, by - 16, 9, 2.4, 1.2), BRASS, rim=1, mottle=0)
    # head in a water bowl
    hy = by - 29
    s.paint(circle(X, Y, 25, hy, 12.5), GLASS, alpha=0.5, rim=0, mottle=0, flat=0.7)          # water
    for k, side in enumerate((-1, 1)):                                                         # feathery gills
        gx = 25 + side * 8
        for j in range(3):
            s.stroke([(gx, hy - 2 + j * 3), (gx + side * 4, hy - 6 + j * 3 + math.sin(p.ph + j) * 0.8)], 1.4,
                     AXO[1] if j % 2 else H["magenta"][3])
    s.paint(ellipse(s.X, s.Y, 26, hy + 1, 8.5, 6.5), AXO, rim=1, mottle=0, highlight=0.5)
    eyes(s, [(24, hy), (32, hy)], p, 0.9)
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, 29, hy + 4, 1.6, 1.3), AXO[0])
    else:
        s.stroke([(25, hy + 3.5), (28, hy + 4.6), (32, hy + 3.5)], 0.8, AXO[0])               # the smile
    for bx, bb, r in ((32, -8, 1.2), (19, -6, 0.8), (30, -3 - p.f * 3, 0.9 if p.talk else 0.6)):
        s.flat(subtract(circle(s.X, s.Y, bx, hy + bb, r + 0.6), circle(s.X, s.Y, bx, hy + bb, r)),
               (230, 250, 255), 0.8)
    bowl = circle(s.X, s.Y, 25, hy, 12.5)
    s.flat(subtract(bowl, circle(s.X, s.Y, 25, hy, 11.4)), GLASS[3], 0.8)
    s.stroke([(16, hy - 3), (18, hy - 8), (22, hy - 11)], 1.3, (255, 255, 255), 0.8)
    # arm
    if p.wave:
        pts = [(31, by - 10), (36, by - 18), (37 + p.f * 3, by - 26)]
    elif p.talk:
        pts = [(31, by - 10), (36, by - 4), (41, by - 8 - p.f * 2)]
    else:
        pts = [(31, by - 10), (33, by - 2), (33, by + 4)]
    s.paint(capsule(s.X, s.Y, pts[0], pts[1], 3.8, 3.4), T[1:], rim=1, mottle=0)
    s.paint(capsule(s.X, s.Y, pts[1], pts[2], 3.4, 3.2), T[1:], rim=1, mottle=0)
    s.paint(circle(s.X, s.Y, pts[2][0], pts[2][1], 3.0), BRASS, rim=1, mottle=0)


# ---------------------------------------------------------------- 7 Echo
def echo(s, X, Y, p):
    low = 12 if p.sit else 0
    jy = 50 + p.bob + low
    shadow(s, 24, 13)
    # tripod legs
    feet = [(13 - p.sw * 0.4, FOOT - 1), (24 + p.sw * 0.6, FOOT), (35 - p.sw * 0.3, FOOT - 1)]
    if p.sit:
        feet = [(9, FOOT - 1), (24, FOOT), (39, FOOT - 1)]
    for k, (fx, fy) in enumerate(feet):
        knee = ((24 + fx) / 2 + (k - 1) * 4, jy + 16 - (6 if p.sit else 0))
        col = H["steel"][1] if k != 1 else H["steel"][2]
        s.stroke([(24, jy + 11), knee, (fx, fy - 1)], 2.4, col)
        s.dab(knee[0], knee[1], 1.4, BRASS[3])
        s.paint(box(s.X, s.Y, fx, fy - 1, 2.6, 1.2, 0.6), H["darkstone"], rim=1, mottle=0)
    # the jar: glass, green fluid, a glowing mind
    s.paint(box(s.X, s.Y, 24, jy + 11, 8, 2, 1), BRASS, rim=1, mottle=0)              # base
    fluid = box(s.X, s.Y, 24, jy + 2, 7, 7.5, 2)
    s.paint(fluid, H["lime"][:4], rim=0, mottle=0.1, alpha=0.8)
    s.paint(ellipse(X, Y, 24, jy + 2 + p.breathe * 0.5, 4.6, 4), H["magenta"], rim=1, mottle=0.08,
            highlight=0.6 + (0.5 if p.talk else 0))
    s.stroke([(21, jy + 1), (24, jy + 3), (27, jy + 1)], 0.6, H["magenta"][1], 0.8)
    for bx, by2 in ((20, jy + 6 - p.f), (28, jy + 3 - p.f * 2)):
        s.dab(bx, by2, 0.7, (235, 255, 220), 0.8)
    jar = box(s.X, s.Y, 24, jy, 8.5, 10, 3)
    s.paint(jar, GLASS, alpha=0.25, rim=0, mottle=0, flat=0.7)
    s.flat(subtract(jar, box(s.X, s.Y, 24, jy, 7.4, 9, 2.4)), GLASS[3], 0.8)
    s.stroke([(18, jy - 6), (18, jy + 4)], 1.0, (255, 255, 255), 0.7)
    s.paint(box(s.X, s.Y, 24, jy - 10.5, 9, 2.2, 1), BRASS, rim=1, mottle=0)           # lid + emitter
    s.dab(24, jy - 13, 1.4, H["cyan"][4])
    # manipulator
    if p.wave:
        pts = [(32, jy - 2), (37, jy - 8), (37 + p.f * 3, jy - 16)]
    elif p.talk:
        pts = [(32, jy - 2), (37, jy + 1), (41, jy - 3 - p.f * 2)]
    else:
        pts = [(32, jy - 2), (35, jy + 4), (34, jy + 9)]
    s.stroke(pts, 1.3, H["steel"][2])
    s.dab(pts[1][0], pts[1][1], 1.1, BRASS[3])
    s.dab(pts[2][0], pts[2][1], 1.4, BRASS[2])
    # hologram face projected above
    fy = jy - 28 + p.breathe * 0.5
    s.flat(poly(s.X, s.Y, [(22, jy - 14), (26, jy - 14), (34, fy + 6), (15, fy + 6)]), H["cyan"][3], 0.18)
    face = ellipse(s.X, s.Y, 25, fy, 8.5, 10)
    s.flat(face, H["cyan"][2], 0.55)
    s.flat(subtract(face, ellipse(s.X, s.Y, 25, fy, 7.5, 9)), H["cyan"][4], 0.8)
    for k in range(-9, 10, 2):                                                      # scanlines
        s.flat(intersect(face, box(s.X, s.Y, 25, fy + k + (p.f % 2), 9, 0.3)), H["cyan"][0], 0.35)
    for x in (24, 29.5):
        if p.blink:
            s.flat(box(s.X, s.Y, x, fy - 1, 1.6, 0.4), (230, 255, 255))
        else:
            s.flat(box(s.X, s.Y, x, fy - 1, 1.1, 1.6, 0.3), (230, 255, 255))
    s.flat(box(s.X, s.Y, 23.5, fy - 4.5, 2, 0.4), (230, 255, 255), 0.8)
    s.flat(box(s.X, s.Y, 29.5, fy - 4.5, 2, 0.4), (230, 255, 255), 0.8)
    if p.talk_open:
        s.flat(ellipse(s.X, s.Y, 27, fy + 5, 2.2, 1.4), (230, 255, 255))
    else:
        s.flat(box(s.X, s.Y, 27, fy + 5, 2.5, 0.4), (230, 255, 255))


from .npc_natives import NATIVE_FACES, NATIVES  # noqa: E402

PAINTERS = [lumen, mossback, tik, sporeling, shardkin, hollow, gillwright, echo] + NATIVES
# face centres in the 48-wide design space (dialogue portraits crop around these)
FACES = [(25, 30), (34, 46), (28, 38), (28, 42), (27, 26), (27, 30), (26, 28), (26, 23)] + NATIVE_FACES


def face_box(look: int) -> tuple:
    """Top-left of a 32x32 portrait crop in the widened output sprite."""
    fx, fy = FACES[look]
    x = (fx - 24) * K + W / 2
    return (int(max(0, min(W - 32, x - 16))), int(max(0, min(HH - 32, fy - 16))))


# ---------------------------------------------------------------- the caravan's pack beast
def beast(pose: str) -> Sprite:
    """A Grumblebeast: shaggy, six-legged, patient, loaded with the Gloam Caravan's wares."""
    f = int(pose[-1])
    walk = pose.startswith("walk")
    s = Sprite(112, 80, seed=777 + f)
    X, Y = s.wobbled(0.5, 7)
    FUR = H["amber"]
    by = 44 + ((0, -1, 0, -1)[f] if walk else f)
    s.flat(ellipse(s.X, s.Y, 54, 78.5, 40, 2), (10, 10, 20), 0.28)
    for k, x in enumerate((24, 46, 70)):                 # six legs (far side first)
        for side in (0, 1):
            d = ((5, 2, -5, -2)[(f + k + side * 2) % 4]) if walk else 0
            rmp = FUR[:3] if side == 0 else FUR[:4]
            lx = x + (4 if side == 0 else 0)
            s.paint(capsule(s.X, s.Y, (lx, by + 10), (lx + d, 74), 5, 4.6), rmp, rim=1, mottle=0)
            s.paint(box(s.X, s.Y, lx + d + 1, 76, 5.5, 2.6, 1.2), H["darkstone"][:4], rim=1, mottle=0)
    body = ellipse(X, Y, 50, by, 38, 20)
    s.paint(body, FUR, **MATTE)
    for k in range(26):                                   # shaggy fringe
        x = 16 + k * 2.7
        s.stroke([(x, by + 12 + math.sin(k) * 2), (x + 1, by + 20 + (k % 3))], 1.6, FUR[1])
    for x, w, h, rmp in ((34, 11, 9, H["wood"]), (54, 9, 11, H["teal"]), (72, 10, 8, H["rust"])):   # packs
        s.paint(box(X, Y, x, by - 20 + (11 - h), w, h, 2), rmp, **MATTE)
        s.flat(box(s.X, s.Y, x, by - 20 + (11 - h), w, 0.8), rmp[0])
    s.stroke([(22, by - 16), (84, by - 16)], 1.4, H["wood"][0])
    s.stroke([(80, by - 30), (82, by - 18)], 1.0, H["steel"][1])                     # lantern pole
    s.paint(box(s.X, s.Y, 80, by - 31, 2.6, 3, 1), H["amber"], rim=1, mottle=0)
    s.dab(80, by - 31, 1.4, H["yellow"][4])
    hx, hy = 94, by + 2 + (p_head := (0, 1, 0, 1)[f])
    s.paint(ellipse(X, Y, hx, hy, 11, 9), FUR, **MATTE)
    s.paint(ellipse(s.X, s.Y, hx + 7, hy + 4, 5, 3.6), H["sand"][1:], rim=1, mottle=0)          # muzzle
    for side in (-1, 1):                                   # curled horns
        s.stroke([(hx - 2 + side * 3, hy - 7), (hx - 6 + side * 4, hy - 13), (hx - 10 + side * 2, hy - 11)],
                 2.0, H["bone"][2])
    s.dab(hx + 3, hy - 2, 1.3, INK)
    s.dab(hx + 3.4, hy - 2.8, 0.45, (255, 255, 255))
    s.dab(hx + 11, hy + 3, 0.8, (60, 30, 30))
    del p_head
    return s


def tripod() -> Sprite:
    """The Survey Corps' theodolite, set up whenever the team stops."""
    s = Sprite(30, 48, seed=778)
    for a, b in (((15, 20), (5, 47)), ((15, 20), (25, 47)), ((15, 20), (16, 47))):
        s.stroke([a, b], 1.4, H["wood"][1] if b[0] != 16 else H["wood"][2])
    s.paint(box(s.X, s.Y, 15, 14, 7, 5, 1.5), H["yellow"], rim=1, mottle=0)
    s.paint(circle(s.X, s.Y, 21, 13, 3), H["steel"], rim=1, mottle=0)
    s.dab(22, 13, 1.6, H["cyan"][4])
    s.stroke([(15, 9), (15, 3)], 0.8, H["steel"][1])
    s.paint(box(s.X, s.Y, 18, 3, 3.5, 2, 0.3), H["orange"], rim=0, mottle=0)                   # pennant
    return s


def settler(look: int, pose: str) -> Sprite:
    s = Sprite(W, HH, seed=900 + look * 17 + sum(map(ord, pose)) % 7)
    s.X = (s.X - W / 2) / K + 24          # paint in the 48-wide design space, widened on the way out
    X, Y = s.wobbled(0.35, 6)
    PAINTERS[look](s, X, Y, P(pose))
    return s


# ---------------------------------------------------------------- Survey Corps ships (nose up)
def corps_fighter() -> Sprite:
    s = Sprite(36, 42, seed=781)
    X, Y = s.wobbled(0.3, 6)
    for side in (-1, 1):                                                   # swept wings
        s.paint(poly(X, Y, [(18 + side * 5, 18), (18 + side * 17, 32), (18 + side * 16, 37), (18 + side * 5, 33)]),
                H["cream"] if side > 0 else H["cream"][:4], rim=1, mottle=0)
        s.paint(poly(s.X, s.Y, [(18 + side * 12, 27), (18 + side * 16, 32), (18 + side * 16, 35),
                                (18 + side * 11, 31)]), H["orange"], rim=0.5, mottle=0)    # wingtip livery
    hull = poly(X, Y, [(18, 2), (24, 14), (25, 34), (21, 39), (15, 39), (11, 34), (12, 14)])
    s.paint(hull, H["cream"], **MATTE)
    s.paint(box(s.X, s.Y, 18, 25, 6.5, 1.6), H["orange"], rim=0.5, mottle=0)              # hull stripe
    s.paint(ellipse(s.X, s.Y, 18, 14, 3.4, 5), H["cyan"], rim=1, mottle=0, highlight=0.9)  # canopy
    for x in (15, 21):                                                     # twin engines
        s.paint(box(s.X, s.Y, x, 39, 2.2, 2.4, 0.8), H["darkstone"], rim=1, mottle=0)
    s.dab(18, 31, 1.4, H["yellow"][4])                                     # corps lamp
    return s


def corps_tender() -> Sprite:
    s = Sprite(50, 58, seed=782)
    X, Y = s.wobbled(0.3, 6)
    for side in (-1, 1):                                                   # fuel tanks
        s.paint(box(X, Y, 25 + side * 17, 32, 5, 14, 4.5), H["orange"] if side > 0 else H["orange"][:4], **MATTE)
        s.flat(box(s.X, s.Y, 25 + side * 17, 26, 5, 0.6), H["orange"][0])
        s.flat(box(s.X, s.Y, 25 + side * 17, 38, 5, 0.6), H["orange"][0])
        s.stroke([(25 + side * 9, 24), (25 + side * 13, 24)], 1.4, H["steel"][1])
        s.stroke([(25 + side * 9, 40), (25 + side * 13, 40)], 1.4, H["steel"][1])
    hull = box(X, Y, 25, 30, 10, 24, 6)
    s.paint(hull, H["cream"], **MATTE)
    s.paint(poly(s.X, s.Y, [(17, 10), (25, 2), (33, 10)]), H["cream"][1:], rim=1, mottle=0)
    s.paint(box(s.X, s.Y, 25, 32, 10, 2, 0.5), H["orange"], rim=0.5, mottle=0)
    s.paint(box(s.X, s.Y, 25, 44, 10, 1.4, 0.5), H["orange"], rim=0.5, mottle=0)
    s.paint(ellipse(s.X, s.Y, 25, 14, 5, 5), H["cyan"], rim=1, mottle=0, highlight=0.9)
    s.paint(circle(s.X, s.Y, 25, 25, 3), H["steel"], rim=1, mottle=0)               # docking clamp
    s.dab(25, 25, 1.2, H["yellow"][4])
    for x in (20, 30):
        s.paint(box(s.X, s.Y, x, 55, 3, 2.6, 0.8), H["darkstone"], rim=1, mottle=0)
    return s


def corps_lander() -> Sprite:
    """The Kestrel Survey Team's lander, parked with its ramp down."""
    s = Sprite(84, 64, seed=783)
    X, Y = s.wobbled(0.4, 7)
    for x0, x1 in ((22, 12), (62, 72)):                                     # landing legs
        s.stroke([(x0, 42), (x1, 61)], 2.2, H["steel"][1])
        s.paint(box(s.X, s.Y, x1, 62, 5, 1.6, 0.6), H["darkstone"], rim=1, mottle=0)
    hull = union(ellipse(X, Y, 42, 34, 30, 14), box(X, Y, 42, 26, 20, 12, 6))
    s.paint(hull, H["cream"], **MATTE)
    s.paint(box(s.X, s.Y, 42, 38, 29, 2.2, 0.8), H["orange"], rim=0.5, mottle=0)          # livery stripe
    s.paint(box(s.X, s.Y, 42, 44, 22, 1.4, 0.6), H["orange"][1:], rim=0, mottle=0)
    s.paint(ellipse(s.X, s.Y, 58, 24, 7, 5), H["cyan"], rim=1, mottle=0, highlight=0.9)   # cockpit
    s.flat(poly(s.X, s.Y, [(28, 44), (36, 44), (44, 62), (24, 62)]), H["steel"][2])        # ramp
    s.stroke([(28, 44), (24, 62)], 0.8, H["steel"][0])
    s.flat(box(s.X, s.Y, 32, 40, 5, 4, 1), (40, 34, 30))                                   # open hatch
    s.dab(32, 39, 1.4, H["yellow"][4], 0.8)
    s.stroke([(30, 14), (26, 4)], 1.0, H["steel"][1])                                      # dish mast
    s.paint(ellipse(s.X, s.Y, 25, 4, 5, 2.4, rot=-0.4), H["steel"], rim=1, mottle=0)
    for x in (14, 70):
        s.paint(box(s.X, s.Y, x, 32, 3, 4, 1), H["darkstone"], rim=1, mottle=0)               # thrusters
    s.dab(70, 28, 1.2, H["red"][4])
    return s


def build_all():
    import json
    from .common import GEN
    out = []
    for look in range(len(PAINTERS)):
        for pose in POSES:
            rel = f"poi/npc/{look}_{pose}.png"
            save(settler(look, pose), rel)
            out.append(rel)
    for pose in ("idle0", "idle1", "walk0", "walk1", "walk2", "walk3"):
        save(beast(pose), f"poi/npc/beast_{pose}.png")
        out.append(f"poi/npc/beast_{pose}.png")
    save(tripod(), "poi/tripod.png")
    save(corps_fighter(), "ships/corps_fighter.png")
    save(corps_tender(), "ships/corps_tender.png")
    save(corps_lander(), "poi/corps_lander.png")
    (GEN / "poi" / "npc" / "faces.json").write_text(json.dumps([face_box(k) for k in range(len(PAINTERS))]))
    return out + ["poi/tripod.png"]
