"""World art: per-biome terrain tiles, background strips, props, stronghold
entrances and creatures. Heights are planned against the pilot (78 art px)."""
from __future__ import annotations

from .common import (MATTE, H, Sprite, box, capsule, circle, crystal, ellipse, math, mute, np, poly, ramp_of,
                     ROOT, GEN, rock, save, smooth_union, subtract, tuft, union)

def _seed(name: str) -> int:
    import zlib
    return zlib.crc32(name.encode())


# Per-biome look: (fringe ramp, accent ramp, soil ramp, deep ramp, pebble ramps, sky colour for backdrops)
BIOME_LOOK = {
    "desert": ("sand", "orange", "sand", "rust", ("stone", "orange", "bone"), (250, 200, 140)),
    "ice": ("snow", "cyan", "snow", "coolstone", ("coolstone", "steel", "cyan"), (200, 225, 250)),
    "forest": ("lime", "amber", "soil", "soildeep", ("stone", "coolstone", "orange"), (190, 225, 245)),
    "ocean": ("sand", "rose", "sand", "soil", ("bone", "rose", "cyan"), (180, 215, 240)),
    "volcanic": ("ash", "orange", "darkstone", "ash", ("darkstone", "red", "orange"), (190, 90, 60)),
    "toxic": ("lime", "amber", "soil", "soildeep", ("stone", "orange", "teal"), (170, 200, 140)),
    "crystal": ("violet", "cyan", "darkstone", "indigo", ("indigo", "cyan", "violet"), (150, 120, 200)),
    "barren": ("regolith", "steel", "regolith", "coolstone", ("regolith", "coolstone", "steel"), (60, 60, 80)),
}


# ---------------------------------------------------------------- terrain tiles
def fringe(biome):
    top_n, acc_n = BIOME_LOOK[biome][0], BIOME_LOOK[biome][1]
    top, acc = ramp_of(top_n), ramp_of(acc_n)
    s = Sprite(80, 18, seed=_seed(biome) % 997)
    X, Y = s.wobbled(0.6, 4)
    s.paint(box(X, Y, 40, 14, 46, 4), top[:3], rim=0, mottle=0.04)
    rng = np.random.default_rng(len(biome) * 7)
    if biome in ("forest", "toxic"):
        for i in range(24):
            x = i * 3.4 + rng.uniform(-1, 1)
            tuft(s, X, Y, x, 11, rng.uniform(3, 8), top if i % 3 else H["green"], rng.uniform(-1.5, 1.5))
        for x in (13, 47, 68):
            s.stroke([(x, 10), (x, 4)], 1.0, H["green"][1])
            s.dab(x, 3.5, 1.6, acc[3])
    elif biome in ("desert", "ocean"):
        for i in range(6):   # wind ripples
            x = i * 14 + rng.uniform(0, 6)
            s.stroke([(x, 11.5), (x + 5, 10.5), (x + 10, 11.5)], 1.0, top[3], 0.9)
        for x in (18, 52, 70):
            s.dab(x, 10.5, 1.5, acc[3] if biome == "ocean" else H["stone"][2])
        if biome == "desert":
            for x in (30, 61):
                tuft(s, X, Y, x, 11, 5, H["amber"], -1, 1.0)
                tuft(s, X, Y, x + 2, 11, 6, H["amber"], 1.2, 1.0)
    elif biome == "ice":
        s.paint(box(X, Y, 40, 11, 46, 3.5, 2), top, rim=0, mottle=0.03)
        for x in (10, 34, 58, 74):
            s.paint(poly(X, Y, [(x - 2, 12), (x, 17), (x + 2, 12)]), ramp_of("ice"), rim=0)
    elif biome == "volcanic":
        for i in range(5):
            x = i * 17 + rng.uniform(0, 8)
            s.stroke([(x, 13), (x + 3, 15), (x + 7, 14)], 1.0, H["orange"][3], 1.0)
        for x in (25, 63):
            s.paint(ellipse(X, Y, x, 11, 4, 2.4), H["darkstone"], **MATTE)
    elif biome == "crystal":
        for i in range(10):
            x = i * 8 + rng.uniform(0, 4)
            crystal(s, X, Y, x, 12, rng.uniform(3, 8), 1.6, rng.uniform(-1, 1),
                    H["cyan"] if i % 3 == 0 else top, rim=0.3)
    elif biome == "barren":
        for x in (12, 44, 66):
            s.paint(subtract(ellipse(X, Y, x, 12, 6, 2.2), ellipse(s.X, s.Y, x, 11.6, 4, 1.4)), top, rim=0)
            s.flat(ellipse(s.X, s.Y, x, 11.8, 3.6, 1.1), top[0], 0.8)
    return s


def underground(biome, w=160, h=120):
    soil_n, deep_n, pebs = BIOME_LOOK[biome][2], BIOME_LOOK[biome][3], BIOME_LOOK[biome][4]
    s = Sprite(w, h, seed=_seed(biome) % 991 + 7)
    tau = 2 * math.pi
    soil, deep = ramp_of(soil_n), ramp_of(deep_n)
    # strata repeat seamlessly in BOTH directions (depth darkening is added at render time)
    wave = s.Y + 2.5 * np.sin(s.X * tau / w * 2) + 1.5 * np.sin(s.X * tau / w * 5 + 1)
    band = np.sin(wave * tau / h * 2)
    t = 0.55 + 0.07 * band + 0.03 * np.sin(s.Y * tau / h * 9 + 2 * np.sin(s.X * tau / w * 3))
    t = np.where(np.sin(wave * tau / h * 4) > 0.75, t - 0.08, t)
    idx = np.clip((t * 4).astype(int), 0, 3)
    col = np.array(soil[:4], float)[idx]
    col = np.where((np.sin(wave * tau / h * 2 + 1) > 0.8)[..., None], np.array(deep[:4], float)[idx], col)
    s._over(col, np.ones((h, w)))
    rng = np.random.default_rng(len(biome) * 13)

    def wrapped(fn):
        for dx in (-w, 0, w):
            for dy in (-h, 0, h):
                fn(dx, dy)

    for _ in range(9):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        rr = rng.uniform(1.8, 4.0)
        rmp = ramp_of(pebs[rng.integers(0, len(pebs))])

        def peb(dx, dy, x=x, y=y, rr=rr, rmp=rmp):
            d = ellipse(s.X, s.Y, x + dx, y + dy, rr * 1.3, rr)
            if (d < 1).any():
                s.paint(d, rmp, highlight=0.6, mottle=0.0, rim=1)
        wrapped(peb)
    if biome in ("forest", "toxic", "ocean"):
        for _ in range(4):   # roots
            x0 = rng.uniform(0, w)
            pts = [(x0, 0)]
            for _k in range(5):
                pts.append((pts[-1][0] + rng.uniform(-5, 5), pts[-1][1] + rng.uniform(4, 8)))
            wrapped(lambda dx, dy, pts=pts: s.stroke([(px + dx, py + dy) for px, py in pts], 1.4, deep[0], 0.9))
    if biome == "volcanic":
        for _ in range(2):   # lava veins
            x0, y0 = rng.uniform(0, w), rng.uniform(h * 0.3, h)
            pts = [(x0, y0)]
            for _k in range(4):
                pts.append((pts[-1][0] + rng.uniform(4, 9), pts[-1][1] + rng.uniform(-4, 4)))
            wrapped(lambda dx, dy, pts=pts: s.stroke([(px + dx, py + dy) for px, py in pts], 1.3, H["orange"][3]))
    fx, fy = rng.uniform(20, w - 40), rng.uniform(h * 0.45, h * 0.75)
    for k in range(5):   # a fossil
        a = k * 0.9
        s.dab(fx + math.cos(a) * (6 - k), fy + math.sin(a) * (6 - k), 1.8 - k * 0.2, H["bone"][3 - (k % 2)])
    glint = H["cyan"] if biome != "crystal" else H["violet"]
    for _ in range(3):
        x, y = rng.uniform(4, w - 4), rng.uniform(h * 0.3, h - 4)
        s.dab(x, y, 1.2, glint[4])
        s.dab(x + 1.5, y + 1, 0.8, glint[3])
    return s


def backdrop(biome):
    """Far strip, 300x80, seamless: two hill layers plus biome silhouettes."""
    s = Sprite(300, 80, seed=_seed(biome) % 977)
    sky = BIOME_LOOK[biome][5]
    tau = 2 * math.pi

    def ridge(x, a=1.0):
        return 52 + 9 * a * np.sin(x * tau / 150) + 6 * a * np.sin(x * tau / 60 + 1) + 3 * np.sin(x * tau / 37.5)
    hill = {"ocean": ("blue", "teal"), "volcanic": ("red", "darkstone"), "crystal": ("indigo", "violet"),
            "barren": ("coolstone", "regolith"), "toxic": ("teal", "green")}.get(biome, ("teal", "green"))
    s.paint(-(s.Y - (ridge(s.X + 40, 1.4) - 14)), mute(ramp_of(hill[0]), 0.40, sky), rim=0, mottle=0.03)
    s.paint(-(s.Y - ridge(s.X)), mute(ramp_of(hill[1]), 0.55, sky), rim=0, mottle=0.03)
    rng = np.random.default_rng(8)
    for _ in range(9):
        x = rng.uniform(24, 276)
        gy = float(ridge(np.array(x)))
        hh = rng.uniform(10, 22)
        if biome == "toxic":
            stem = capsule(s.X, s.Y, (x, gy + 2), (x + rng.uniform(-2, 2), gy - hh), 1.6, 1.2)
            cap = subtract(ellipse(s.X, s.Y, x, gy - hh, hh * 0.55, hh * 0.35), box(s.X, s.Y, x, gy - hh + 8, 20, 4))
            s.paint(union(stem, cap), mute(H["violet"], 0.5, sky), rim=0, mottle=0.0)
        elif biome == "crystal":
            crystal(s, s.X, s.Y, x, gy + 2, hh * 1.4, hh * 0.22, rng.uniform(-3, 3), mute(H["violet"], 0.5, sky),
                    rim=0)
        elif biome == "volcanic":
            if rng.random() < 0.3:
                s.paint(poly(s.X, s.Y, [(x - hh * 1.6, gy + 2), (x - 3, gy - hh * 1.6), (x + 3, gy - hh * 1.6),
                                        (x + hh * 1.6, gy + 2)]), mute(H["darkstone"], 0.55, sky), rim=0)
                s.dab(x, gy - hh * 1.6, 2.4, H["orange"][3], 0.8)
        elif biome == "ocean":
            s.paint(capsule(s.X, s.Y, (x, gy + 2), (x + 3, gy - hh), 1.2, 1.0), mute(H["wood"], 0.5, sky), rim=0)
            for a in (-0.9, -0.3, 0.3, 0.9):
                s.stroke([(x + 3, gy - hh), (x + 3 + math.sin(a) * 7, gy - hh + 3)], 1.5, mute(H["green"], 0.5, sky)[2])
        elif biome == "barren":
            s.paint(subtract(ellipse(s.X, s.Y, x, gy + 1, hh * 0.9, 2.6), ellipse(s.X, s.Y, x, gy, hh * 0.7, 1.6)),
                    mute(H["regolith"], 0.5, sky), rim=0)
    return s


# ---------------------------------------------------------------- props
def p_mushroom(rmp="magenta", spots="cyan", seed=3):
    s = Sprite(48, 46, seed=seed)
    X, Y = s.wobbled(0.8, 6)
    s.paint(capsule(X, Y, (22, 45), (25, 24), 5.2, 3.8), H["cream"], **MATTE)
    s.stroke([(21, 42), (23, 33)], 1.0, H["cream"][1], 0.5)
    s.paint(ellipse(X, Y, 25, 23, 17, 4.5), H["orange"][:3], rim=2)
    cap = subtract(ellipse(X, Y, 25, 18, 21, 14), box(s.X, s.Y, 25, 31, 26, 6))
    s.paint(cap, ramp_of(rmp), **MATTE)
    for (x, y, r) in ((15, 13, 2.4), (27, 9, 2.8), (35, 15, 2.0), (21, 18, 1.6), (31, 20, 1.4), (10, 20, 1.3)):
        s.dab(x, y, r, ramp_of(spots)[3], 1.0)
        s.dab(x - 0.6, y - 0.6, r * 0.45, ramp_of(spots)[4], 0.9)
    return s


def p_giant_fungus():
    s = Sprite(96, 128, seed=8)
    X, Y = s.wobbled(1.1, 8)
    s.paint(union(capsule(X, Y, (46, 127), (50, 70), 9, 6), capsule(X, Y, (50, 72), (44, 40), 6, 5)), H["cream"],
            **MATTE)
    for k in range(5):
        y = 120 - k * 14
        s.stroke([(41 + k % 2, y), (45, y - 5), (49, y - 9)], 1.0, H["cream"][1], 0.55)
    s.paint(ellipse(X, Y, 46, 42, 36, 7), H["amber"][:3], rim=2)
    s.paint(subtract(ellipse(X, Y, 46, 32, 44, 26), box(s.X, s.Y, 46, 58, 50, 10)), H["violet"], **MATTE)
    for (x, y, r) in ((24, 26, 3.6), (44, 16, 4.0), (64, 24, 3.2), (34, 36, 2.2), (57, 38, 2.4), (78, 34, 2.0),
                      (14, 38, 2.0)):
        s.dab(x, y, r, H["lime"][3], 1.0)
        s.dab(x - 0.8, y - 0.8, r * 0.4, H["lime"][4], 0.9)
    for x in (30, 52, 70):
        s.stroke([(x, 47), (x + 1, 56), (x - 1, 64)], 1.0, H["violet"][2], 0.8)
        s.dab(x - 1, 65, 1.4, H["lime"][3])
    return s


def p_pod():
    s = Sprite(34, 26, seed=4)
    X, Y = s.wobbled(0.6, 5)
    for x, y, r in ((10, 18, 7), (23, 17, 8), (16, 10, 6)):
        s.paint(circle(X, Y, x, y, r), H["lime"], **MATTE)
        s.dab(x - r * 0.3, y - r * 0.3, r * 0.3, H["yellow"][4], 0.8)
    s.paint(box(X, Y, 17, 24, 14, 2.4, 1.5), H["green"][:3], rim=0)
    return s


def p_bush(rmp="teal", berry="red", seed=17):
    s = Sprite(40, 28, seed=seed)
    X, Y = s.wobbled(1.0, 4)
    body = union(circle(X, Y, 12, 18, 9), circle(X, Y, 22, 14, 11), circle(X, Y, 31, 19, 8))
    s.paint(subtract(body, box(s.X, s.Y, 20, 31, 30, 3)), ramp_of(rmp), **MATTE)
    for (x, y) in ((10, 15), (19, 10), (27, 13), (32, 18), (15, 20), (24, 20)):
        s.dab(x, y, 1.7, ramp_of(berry)[3])
        s.dab(x - 0.5, y - 0.5, 0.7, ramp_of(berry)[4])
    return s


def p_tall_tree(leaf="green", seed=40, pine=False):
    """A tall tree drawn at full height (138 px) so its pixels match the pilot."""
    s = Sprite(90, 138, seed=seed)
    X, Y = s.wobbled(1.0, 7)
    trunk = union(capsule(X, Y, (44, 137), (45, 60), 7, 4.5), capsule(X, Y, (45, 92), (60, 74), 2.4, 1.6),
                  capsule(X, Y, (44, 100), (30, 84), 2.4, 1.6))
    s.paint(trunk, H["wood"], strokes=0.05, **MATTE)
    for k in range(6):
        s.stroke([(41, 130 - k * 12), (43, 124 - k * 12)], 1.0, H["wood"][0], 0.6)
    lv = ramp_of(leaf)
    if pine:
        for k, (y, w) in enumerate(((34, 18), (56, 26), (80, 34), (102, 38))):
            s.paint(poly(X, Y, [(45 - w, y + 18), (45, y - 16), (45 + w, y + 18)]), lv, **MATTE)
            s.paint(poly(X, Y, [(45 - w + 4, y + 18), (45 - w + 10, y + 14), (45 + w - 6, y + 18)]), H["snow"],
                    rim=0, highlight=0.4)
    else:
        blobs = [(45, 34, 26), (25, 50, 18), (66, 48, 20), (44, 58, 22), (30, 30, 14), (60, 26, 15)]
        body = blobs[0]
        d = circle(X, Y, *body)
        for b in blobs[1:]:
            d = smooth_union(d, circle(X, Y, *b), 4)
        s.paint(d, lv, **MATTE)
        rng = np.random.default_rng(seed)
        for _ in range(9):   # leaf clumps: darker dabs, like Tree1/Tree2
            x, y = rng.uniform(22, 70), rng.uniform(20, 66)
            s.dab(x, y, rng.uniform(2.5, 4.5), lv[1], 0.7)
        for (x, y) in ((40, 22), (55, 30), (30, 40)):
            s.dab(x, y, 3.2, lv[3], 0.8)
    return s


def p_coral():
    s = Sprite(40, 44, seed=21)
    rmp = H["rose"]

    def branch(x, y, ang, length, w, depth):
        if depth == 0 or length < 3:
            s.dab(x, y, w * 0.9, rmp[3])
            return
        ex, ey = x + math.cos(ang) * length, y - math.sin(ang) * length
        s.paint(capsule(s.X, s.Y, (x, y), (ex, ey), w, w * 0.8), rmp, highlight=0.4, mottle=0, rim=0.6)
        branch(ex, ey, ang + 0.5, length * 0.72, w * 0.75, depth - 1)
        branch(ex, ey, ang - 0.55, length * 0.68, w * 0.75, depth - 1)
    branch(20, 44, math.pi / 2, 14, 3.2, 4)
    return s


def p_shell():
    s = Sprite(16, 12, seed=22)
    s.paint(ellipse(s.X, s.Y, 8, 7, 7, 4.6), H["bone"], **MATTE)
    for k in range(3):
        s.stroke([(4 + k * 3, 10.5), (6 + k * 2, 4)], 1.0, H["rose"][2], 0.8)
    return s


def p_kelp():
    s = Sprite(26, 58, seed=23)
    for k, (x0, hgt) in enumerate(((7, 52), (14, 58), (20, 44))):
        pts = [(x0 + math.sin(i * 0.8 + k * 1.3) * 2.5, 58 - i * hgt / 8) for i in range(9)]
        for a, b in zip(pts, pts[1:]):
            s.paint(capsule(s.X, s.Y, a, b, 1.5, 1.3), H["green"], highlight=0.3, mottle=0, rim=0.5)
        for i in (3, 6):
            x, y = pts[i]
            side = 1 if (i + k) % 2 else -1
            s.paint(ellipse(s.X, s.Y, x + side * 3, y, 3.2, 1.4, side * 0.5), H["lime"], highlight=0.4, mottle=0, rim=0)
        s.dab(*pts[-1], 1.8, H["lime"][3])
    return s


def p_basalt_columns():
    s = Sprite(48, 74, seed=31)
    X, Y = s.wobbled(0.4, 6)
    for i, (x, h) in enumerate(((9, 44), (18, 66), (27, 56), (36, 72), (43, 38))):
        col = box(X, Y, x, 74 - h / 2, 4.2, h / 2, 1)
        s.paint(col, H["darkstone"], highlight=0.5, mottle=0.04, rim=1)
        s.paint(ellipse(X, Y, x, 74 - h + 1, 4, 1.6), H["darkstone"][2:], rim=0, highlight=0)
        s.stroke([(x - 1, 74 - h * 0.5), (x + 1, 74 - h * 0.38)], 1.0, H["orange"][3], 0.95)
    return s


def p_vent():
    s = Sprite(44, 32, seed=32)
    X, Y = s.wobbled(0.6, 5)
    s.paint(poly(X, Y, [(1, 32), (16, 8), (28, 8), (43, 32)]), H["darkstone"], **MATTE)
    s.paint(ellipse(X, Y, 22, 8, 7, 3), H["orange"], rim=0, highlight=0.6)
    s.dab(22, 8, 2.2, H["yellow"][4])
    s.stroke([(22, 10), (20, 18), (23, 26)], 1.1, H["orange"][3], 0.9)
    return s


def p_obsidian():
    s = Sprite(36, 36, seed=33)
    X, Y = s.wobbled(0.4, 5)
    for x, h, w, lean in ((10, 22, 6, -3), (21, 34, 7, 2), (30, 16, 5, 3)):
        crystal(s, X, Y, x, 36, h, w, lean, H["darkstone"])
    return s


def p_crystal_cluster(main="indigo", side="cyan", seed=12, big=False):
    hgt = 64 if big else 40
    s = Sprite(40 if not big else 56, hgt, seed=seed)
    X, Y = s.wobbled(0.5, 5)
    cx = s.w / 2
    s.paint(ellipse(X, Y, cx, hgt - 2, s.w * 0.4, 4), H["coolstone"][:3], rim=0)
    k = hgt / 40
    for (x, h, lean, r) in ((cx - 9, 22, -4, side), (cx - 1, 36, 1, main), (cx + 8, 26, 4, "violet"),
                            (cx + 14, 14, 3, side)):
        crystal(s, X, Y, x, hgt - 2, h * k, (3.5 + h * 0.08) * (1 + (k - 1) * 0.5), lean * k, ramp_of(r))
    return s


def p_geode():
    s = Sprite(36, 28, seed=34)
    X, Y = s.wobbled(0.8, 5)
    rock(s, X, Y, 18, 28, 34, 26, H["stone"])
    s.flat(ellipse(s.X, s.Y, 18, 16, 9, 7), (30, 18, 50))
    for x in (12, 16, 20, 24):
        crystal(s, X, Y, x, 22, 8 + (x % 3) * 2, 2.2, (x - 18) * 0.3, H["violet"], rim=0.3)
    return s


def p_boulder():
    s = Sprite(40, 30, seed=35)
    X, Y = s.wobbled(1.0, 6)
    rock(s, X, Y, 20, 30, 38, 28, H["regolith"])
    return s


def p_crater_rock():
    s = Sprite(32, 22, seed=36)
    X, Y = s.wobbled(0.8, 5)
    rock(s, X, Y, 16, 22, 30, 20, H["regolith"])
    for x, y, r in ((11, 13, 2.6), (20, 10, 1.8), (22, 16, 1.4)):
        s.flat(circle(s.X, s.Y, x, y, r), H["regolith"][0], 0.9)
        s.dab(x - r * 0.4, y - r * 0.4, r * 0.4, H["regolith"][3], 0.8)
    return s


def p_probe():
    s = Sprite(34, 70, seed=37)
    for a, b in (((17, 70), (17, 24)), ((17, 46), (5, 70)), ((17, 46), (29, 70))):
        s.paint(capsule(s.X, s.Y, a, b, 1.6), H["steel"], highlight=0.3, mottle=0)
    s.paint(ellipse(s.X, s.Y, 17, 18, 14, 6), H["steel"], **MATTE)
    s.stroke([(17, 12), (17, 2)], 1.0, H["steel"][1])
    s.dab(17, 2, 1.8, H["red"][3])
    return s


def p_ice_spikes():
    s = Sprite(40, 40, seed=38)
    X, Y = s.wobbled(0.4, 5)
    for x, h, lean in ((10, 24, -3), (20, 38, 1), (30, 28, 3)):
        crystal(s, X, Y, x, 40, h, 4.4, lean, ramp_of("ice"))
    return s


def p_snow_rock():
    s = Sprite(36, 24, seed=39)
    X, Y = s.wobbled(0.9, 5)
    rock(s, X, Y, 18, 24, 34, 22, H["coolstone"])
    s.paint(subtract(ellipse(X, Y, 15, 8, 13, 5), box(s.X, s.Y, 15, 14, 20, 3)), H["snow"], rim=0, highlight=0.5)
    return s


def p_dune_grass():
    s = Sprite(24, 18, seed=41)
    X, Y = s.wobbled(0.4, 4)
    for i in range(7):
        tuft(s, X, Y, 6 + i * 2, 18, 8 + (i % 3) * 3, H["amber"], (i - 3) * 1.2, 1.0)
    return s


def p_charred_tree():
    s = Sprite(50, 96, seed=42)
    X, Y = s.wobbled(0.8, 6)
    d = union(capsule(X, Y, (25, 96), (26, 30), 5, 2.5), capsule(X, Y, (26, 60), (40, 40), 2, 1.2),
              capsule(X, Y, (25, 52), (11, 36), 2, 1.2), capsule(X, Y, (26, 36), (34, 20), 1.6, 1))
    s.paint(d, H["ash"], highlight=0.5, mottle=0.04)
    for y in (80, 64, 46):
        s.stroke([(24, y), (26, y - 4)], 1.0, H["orange"][3], 0.9)
    return s


# ---------------------------------------------------------------- strongholds
def s_shrine():
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
    for (x, y, h, lean, r) in ((22, 34, 22, -5, "violet"), (30, 28, 15, -2, "indigo"), (86, 32, 20, 6, "violet"),
                               (94, 44, 13, 8, "cyan"), (56, 20, 18, 0, "violet"), (48, 24, 10, -4, "cyan"),
                               (65, 23, 12, 4, "indigo")):
        crystal(s, X, Y, x, y + 4, h, 3.5 + h * 0.16, lean, ramp_of(r))
    rng = np.random.default_rng(4)
    for _ in range(16):
        s.dab(rng.uniform(16, 96), 110 - rng.uniform(0, 6), rng.uniform(1.5, 3.2), H["green"][rng.integers(1, 3)])
    return s


def _door(s, cx, base, w, h):
    door = union(box(s.X, s.Y, cx, base - h * 0.35, w, h * 0.35, 1), ellipse(s.X, s.Y, cx, base - h * 0.7, w, w))
    s.flat(door, (14, 10, 24))
    return door


def s_temple():
    s = Sprite(116, 100, seed=51)
    X, Y = s.wobbled(0.6, 8)
    for i, (hw, y0) in enumerate(((56, 86), (46, 70), (36, 54), (26, 38))):
        s.paint(box(X, Y, 58, y0 + 6, hw, 8, 2), H["darkstone"], highlight=0.6, mottle=0.04)
        s.stroke([(58 - hw + 2, y0 - 1), (58 + hw - 2, y0 - 1)], 1.0, H["darkstone"][3], 0.6)
    _door(s, 58, 100, 9, 34)
    s.stroke([(49, 100), (49, 66)], 1.4, H["orange"][3])
    s.stroke([(67, 100), (67, 66)], 1.4, H["orange"][3])
    s.paint(circle(X, Y, 58, 22, 8), H["orange"], highlight=0.8, mottle=0)
    s.dab(58, 22, 3, H["yellow"][4])
    for x in (6, 110):
        s.stroke([(x, 100), (x, 84)], 1.6, H["orange"][3])
    return s


def s_hive():
    s = Sprite(110, 80, seed=52)
    X, Y = s.wobbled(1.2, 8)
    dome = subtract(ellipse(X, Y, 55, 80, 54, 74), box(s.X, s.Y, 55, 86, 60, 6))
    s.paint(dome, H["green"], **MATTE)
    rng = np.random.default_rng(5)
    for _ in range(12):
        x, y = rng.uniform(14, 96), rng.uniform(16, 64)
        r = rng.uniform(3, 5.5)
        s.flat(circle(s.X, s.Y, x, y, r), H["green"][0])
        s.dab(x, y, r * 0.55, H["lime"][4])
    _door(s, 55, 80, 11, 30)
    s.paint(subtract(ellipse(s.X, s.Y, 55, 59, 14, 12), ellipse(s.X, s.Y, 55, 59, 11, 9)), H["lime"], rim=0)
    return s


def s_ruin():
    s = Sprite(110, 96, seed=53)
    X, Y = s.wobbled(1.0, 8)
    arch = subtract(union(box(X, Y, 18, 60, 12, 36, 2), box(X, Y, 92, 60, 12, 36, 2), ellipse(X, Y, 55, 34, 50, 30)),
                    union(ellipse(s.X, s.Y, 55, 46, 32, 30), box(s.X, s.Y, 55, 80, 32, 22)))
    s.paint(arch, H["stone"], highlight=0.7, mottle=0.06, grain=0.03)
    s.flat(union(ellipse(s.X, s.Y, 55, 52, 26, 26), box(s.X, s.Y, 55, 82, 26, 16)), (12, 22, 40))
    rng = np.random.default_rng(6)
    for _ in range(20):
        s.dab(rng.choice([rng.uniform(8, 28), rng.uniform(82, 102)]), rng.uniform(26, 92), rng.uniform(1, 2),
              H["bone"][3])
    for x in (38, 46, 72):
        for k in range(7):
            s.dab(x + math.sin(k) * 2, 94 - k * 6, 1.6, H["green"][2 + k % 2])
    return s


def s_bunker():
    s = Sprite(120, 64, seed=54)
    X, Y = s.wobbled(0.3, 8)
    s.paint(poly(X, Y, [(0, 64), (14, 24), (106, 24), (120, 64)]), H["steel"], **MATTE)
    s.paint(box(X, Y, 34, 18, 14, 6, 2), H["steel"][:4], rim=1)
    s.flat(box(s.X, s.Y, 60, 52, 16, 14), (24, 24, 32))
    for i in range(4):
        s.paint(poly(s.X, s.Y, [(44 + i * 9, 38), (49 + i * 9, 38), (44 + i * 9, 44)]), H["yellow"], rim=0)
    s.stroke([(96, 24), (96, 4)], 1.6, H["steel"][1])
    s.dab(96, 4, 2, H["red"][3])
    return s


# ---------------------------------------------------------------- creatures
def c_crawler(body="violet", spines="cyan", seed=11):
    s = Sprite(44, 32, seed=seed)
    X, Y = s.wobbled(0.6, 5)
    b = ramp_of(body)
    for k, x in enumerate((12, 19, 26)):
        s.paint(capsule(X, Y, (x, 22), (x - 3 + k, 31), 1.7, 1.2), b[:4], rim=2)
    s.paint(smooth_union(ellipse(X, Y, 20, 19, 13, 9), circle(X, Y, 32, 15, 7.5), 4), b, **MATTE)
    s.paint(ellipse(X, Y, 19, 24, 9, 3), b[1:4], rim=0, bias=0.2)
    for (x, y, h) in ((11, 12, 7), (17, 10, 9), (23, 10, 7)):
        s.paint(poly(X, Y, [(x - 2.5, y + 3), (x, y - h), (x + 2.5, y + 3)]), ramp_of(spines), highlight=0.4, rim=0.5)
    s.flat(ellipse(s.X, s.Y, 35, 14, 2.8, 3.1), (16, 12, 30))
    s.dab(35.6, 13.2, 1.0, H["amber"][4])
    s.stroke([(37, 10), (40, 4), (39, 1)], 1.1, b[1])
    s.dab(39, 1.5, 1.8, H["amber"][3])
    return s


def c_jelly(body="cyan", seed=12):
    s = Sprite(32, 40, seed=seed)
    b = ramp_of(body)
    for i, x in enumerate((8, 13, 19, 24)):
        pts = [(x + math.sin(k * 0.9 + i) * 2, 16 + k * 4) for k in range(6)]
        for a, c in zip(pts, pts[1:]):
            s.paint(capsule(s.X, s.Y, a, c, 1.1), b[:3], rim=0, highlight=0)
    dome = subtract(ellipse(s.X, s.Y, 16, 16, 14, 13), box(s.X, s.Y, 16, 25, 18, 5))
    s.paint(dome, b, **MATTE)
    s.flat(ellipse(s.X, s.Y, 12, 13, 1.8, 2), (20, 16, 40))
    s.flat(ellipse(s.X, s.Y, 20, 13, 1.8, 2), (20, 16, 40))
    return s


def c_crab(shell="orange", seed=13):
    s = Sprite(44, 30, seed=seed)
    X, Y = s.wobbled(0.5, 5)
    b = ramp_of(shell)
    for side in (-1, 1):
        for k in range(3):
            x = 22 + side * (6 + k * 4)
            s.paint(capsule(X, Y, (x, 20), (x + side * 6, 29), 1.3), b[:3], rim=1)
        s.paint(ellipse(X, Y, 22 + side * 16, 8, 5, 4), b, **MATTE)
        s.paint(poly(X, Y, [(22 + side * 13, 10), (22 + side * 19, 2), (22 + side * 21, 9)]), b, rim=0.5)
    s.paint(ellipse(X, Y, 22, 18, 13, 8), b, **MATTE)
    for x in (18, 26):
        s.stroke([(x, 12), (x, 7)], 1.0, b[1])
        s.dab(x, 6.5, 1.6, (20, 16, 30))
    return s


def c_beetle(shell="red", seed=14):
    s = Sprite(44, 30, seed=seed)
    X, Y = s.wobbled(0.5, 5)
    b = ramp_of(shell)
    for k, x in enumerate((12, 19, 26)):
        s.paint(capsule(X, Y, (x, 20), (x - 4 + k * 3, 29), 1.3), H["darkstone"][:3], rim=1)
    s.paint(ellipse(X, Y, 19, 16, 14, 10), b, **MATTE)
    s.stroke([(19, 7), (19, 25)], 1.0, b[0], 0.8)
    s.paint(circle(X, Y, 35, 17, 6), H["darkstone"], **MATTE)
    s.dab(38, 15, 1.4, H["yellow"][4])
    s.stroke([(38, 12), (42, 5)], 1.0, H["darkstone"][1])
    return s


CREATURES = {   # biome -> (hopper, flyer); originals keep the alien
    "ocean": (lambda: c_crab("orange", 31), lambda: c_jelly("cyan", 32)),
    "volcanic": (lambda: c_beetle("red", 33), lambda: c_jelly("orange", 34)),
    "toxic": (lambda: c_crawler("lime", "violet", 35), lambda: c_jelly("magenta", 36)),
    "crystal": (lambda: c_crawler("violet", "cyan", 37), lambda: c_jelly("indigo", 38)),
    "barren": (lambda: c_crab("steel", 39), lambda: c_jelly("teal", 40)),
}

def p_ore(fuel=False):
    s = Sprite(26, 22, seed=44 + fuel)
    X, Y = s.wobbled(0.7, 5)
    rock(s, X, Y, 13, 22, 24, 14, H["stone"])
    gem = H["amber"] if fuel else H["cyan"]
    for x, h, lean in ((8, 10, -2), (13, 15, 0), (18, 9, 2)):
        crystal(s, X, Y, x, 17, h, 2.4, lean, gem, rim=0.4)
    return s


def p_medkit():
    """Chunky pixel-art Nano-Medkit pod: titanium case, glowing bio-gel window and emerald cross."""
    s = Sprite(22, 20, seed=47)
    # handle on top
    s.paint(box(s.X, s.Y, 11, 3.5, 4.5, 1.5, 0.8), H["steel"], highlight=0.4, mottle=0)
    # main rounded titanium case
    s.paint(box(s.X, s.Y, 11, 11.5, 9.0, 6.5, 2.0), H["snow"], highlight=0.6, mottle=0.02, rim=0.9)
    # side metal latches
    for sx in (3.0, 19.0):
        s.paint(box(s.X, s.Y, sx, 11.5, 1.4, 3.2, 0.5), H["steel"], highlight=0.5, mottle=0)
    # glowing cyan/mint bio-gel vial strip across the top of the case
    s.paint(box(s.X, s.Y, 11, 7.2, 5.2, 1.1, 0.5), H["cyan"], highlight=0.8, mottle=0, rim=0)
    s.dab(8.5, 7.0, 0.9, H["cyan"][4])
    # bright emerald medical cross on the front
    cross = union(box(s.X, s.Y, 11, 13.0, 4.0, 1.3, 0.3), box(s.X, s.Y, 11, 13.0, 1.3, 4.0, 0.3))
    s.paint(cross, H["green"], highlight=0.8, mottle=0, rim=0.4)
    s.dab(10.5, 12.2, 1.0, H["lime"][4])
    return s


PROPS = {   # file name -> painter
    "props/ore.png": p_ore, "props/ore_fuel.png": lambda: p_ore(True),
    "props/medkit.png": p_medkit,
    "props/toxic/giant_fungus.png": p_giant_fungus, "props/toxic/shroom1.png": p_mushroom,
    "props/toxic/shroom2.png": lambda: p_mushroom("lime", "rose", 5), "props/toxic/pod.png": p_pod,
    "props/toxic/bush.png": lambda: p_bush("teal", "red", 17),
    "props/ocean/coral.png": p_coral, "props/ocean/shell.png": p_shell, "props/ocean/kelp.png": p_kelp,
    "props/volcanic/basalt.png": p_basalt_columns, "props/volcanic/vent.png": p_vent,
    "props/volcanic/obsidian.png": p_obsidian, "props/volcanic/charred_tree.png": p_charred_tree,
    "props/crystal/cluster1.png": lambda: p_crystal_cluster("indigo", "cyan", 12),
    "props/crystal/cluster2.png": lambda: p_crystal_cluster("violet", "teal", 13, big=True),
    "props/crystal/cluster3.png": lambda: p_crystal_cluster("magenta", "cyan", 14),
    "props/crystal/geode.png": p_geode,
    "props/barren/boulder.png": p_boulder, "props/barren/crater_rock.png": p_crater_rock,
    "props/barren/antenna.png": p_probe,
    "props/forest/tall_tree1.png": lambda: p_tall_tree("green", 40),
    "props/forest/tall_tree2.png": lambda: p_tall_tree("lime", 41),
    "props/forest/bush.png": lambda: p_bush("green", "rose", 18),
    "props/forest/mushroom.png": lambda: p_mushroom("red", "bone", 6),
    "props/ice/pine.png": lambda: p_tall_tree("teal", 42, pine=True), "props/ice/spikes.png": p_ice_spikes,
    "props/ice/snow_rock.png": p_snow_rock, "props/desert/dune_grass.png": p_dune_grass,
    "props/desert/bush.png": lambda: p_bush("lime", "amber", 19),
    "strongholds/crystal.png": s_shrine, "strongholds/volcanic.png": s_temple, "strongholds/toxic.png": s_hive,
    "strongholds/ocean.png": s_ruin, "strongholds/barren.png": s_bunker,
}


def calm_copy(src: str, dst: str, sat: float = 0.5, warm=(1.04, 1.0, 0.86)):
    """A copy of an original sprite with its saturation pulled down to the house
    palette (the old desert cacti were neon green)."""
    import pygame
    img = pygame.image.load(str(ROOT / "assets" / src))
    rgb = pygame.surfarray.array3d(img).astype(np.float32)
    alpha = pygame.surfarray.array_alpha(img)
    lum = (rgb * np.array([0.3, 0.59, 0.11])).sum(axis=2, keepdims=True)
    rgb = (lum + (rgb - lum) * sat) * np.array(warm) * 0.92
    out = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    pygame.surfarray.blit_array(out, np.clip(rgb, 0, 255).astype(np.uint8))
    pygame.surfarray.pixels_alpha(out)[:] = alpha
    path = GEN / dst
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(out, str(path))


def build_all():
    out = []
    for k in range(1, 5):
        calm_copy(f"desert/cactus{k}.png", f"props/desert/cactus{k}.png")
        out.append(f"props/desert/cactus{k}.png")
    for biome in BIOME_LOOK:
        for name, fn in (("fringe", fringe), ("underground", underground), ("backdrop", backdrop)):
            save(fn(biome), f"terrain/{biome}/{name}.png")
            out.append(f"terrain/{biome}/{name}.png")
    for rel, fn in PROPS.items():
        save(fn(), rel)
        out.append(rel)
    for biome, (hop, fly) in CREATURES.items():
        save(hop(), f"creatures/{biome}_hopper.png")
        save(fly(), f"creatures/{biome}_flyer.png")
        out += [f"creatures/{biome}_hopper.png", f"creatures/{biome}_flyer.png"]
    return out
