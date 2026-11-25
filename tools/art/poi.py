"""Planet points of interest: settler camps, escape pods, Architect ruins,
material veins, and the cave dungeon's vault and sigils (docs/ART_STYLE.md)."""
from __future__ import annotations

from .common import (MATTE, H, ROOT, Sprite, box, capsule, circle, crystal, ellipse, math, np, poly, ramp_of, rock,
                     save, smooth_union, subtract, union)

# biome -> (material name, hue ramp name). The same table lives in stellar_forge/systems/materials.py.
MAT_HUE = {"forest": "amber", "desert": "yellow", "ice": "cyan", "volcanic": "orange", "crystal": "violet",
           "toxic": "lime", "ocean": "rose", "barren": "indigo"}
GLYPHS = 4


# settlers live in art/npc.py


def tent():
    s = Sprite(76, 50, seed=301)
    X, Y = s.wobbled(0.8, 6)
    s.paint(poly(X, Y, [(2, 50), (36, 4), (74, 50)]), H["teal"], **MATTE)
    s.flat(poly(s.X, s.Y, [(28, 50), (38, 20), (48, 50)]), (22, 18, 26))     # doorway
    s.stroke([(36, 4), (36, 0)], 1.2, H["wood"][1])
    s.paint(box(s.X, s.Y, 18, 34, 5, 4, 1), H["amber"], rim=0.6, mottle=0)    # patch
    s.stroke([(36, 4), (2, 50)], 1.0, H["teal"][4], 0.6)
    return s


def campfire(frame):
    s = Sprite(28, 26, seed=302)
    for a in (-1, 1):
        s.paint(capsule(s.X, s.Y, (14 - a * 10, 24), (14 + a * 9, 20), 2.0), H["wood"], rim=1)
    for k in range(5):
        a = k / 5 * math.tau
        s.paint(circle(s.X, s.Y, 14 + math.cos(a) * 11, 24 + math.sin(a) * 2, 2.4), H["stone"], rim=1, mottle=0)
    h = 18 if frame == 0 else 15
    lean = 2 if frame == 0 else -2
    flame = smooth_union(circle(s.X, s.Y, 14, 17, 5.5), poly(s.X, s.Y, [(9, 16), (14 + lean, 22 - h), (19, 16)]), 2)
    s.paint(flame, H["orange"], highlight=0.6, mottle=0, rim=0.3)
    core = smooth_union(circle(s.X, s.Y, 14, 18, 3), poly(s.X, s.Y, [(11, 18), (14 - lean * 0.5, 22 - h * 0.65),
                                                                       (17, 18)]), 1.5)
    s.paint(core, H["yellow"], highlight=0.9, mottle=0, rim=0)
    return s


def supply_crate():
    s = Sprite(30, 26, seed=303)
    s.paint(box(s.X, s.Y, 15, 14, 13, 11, 2), H["wood"], **MATTE)
    s.flat(box(s.X, s.Y, 15, 14, 13, 1.0), H["wood"][1])
    for x in (6, 24):
        s.flat(box(s.X, s.Y, x, 14, 1.0, 11), H["wood"][1])
    s.paint(box(s.X, s.Y, 15, 9, 5, 3, 1), H["teal"], rim=0.6, mottle=0)
    s.dab(15, 9, 1.2, H["cream"][4])
    return s


# ---------------------------------------------------------------- crashed escape pod
def pod(opened=False):
    s = Sprite(70, 42, seed=304)
    X, Y = s.wobbled(0.6, 7)
    body = ellipse(X, Y, 34, 26, 26, 14, rot=-0.32)
    body = subtract(body, box(s.X, s.Y, 35, 46, 40, 6))                       # half buried
    s.paint(body, H["steel"], **MATTE)
    s.paint(intersect_band(s, 34, 26), H["orange"], rim=0, mottle=0)       # one warning band, no orange rim
    if opened:
        s.flat(ellipse(s.X, s.Y, 40, 22, 7, 6, rot=-0.32), (20, 18, 26))
        s.paint(box(s.X, s.Y, 52, 12, 7, 2.2, 1), H["steel"], rim=1)          # hatch lying open
    else:
        s.paint(ellipse(s.X, s.Y, 40, 22, 7, 6, rot=-0.32), H["cyan"], highlight=0.9, mottle=0)
        s.dab(38, 20, 1.6, H["cyan"][4])
    for x, y in ((14, 30), (58, 18)):
        s.paint(circle(s.X, s.Y, x, y, 3), H["darkstone"], rim=0.5, mottle=0)  # scorch rivets
    rock(s, s.X, s.Y, 10, 42, 16, 9, H["regolith"])
    rock(s, s.X, s.Y, 62, 42, 14, 8, H["regolith"])
    return s


def intersect_band(s, cx, cy):
    """The orange stripe around the pod's waist."""
    return np.maximum(ellipse(s.X, s.Y, cx, cy, 26, 14, rot=-0.32), np.abs((s.X - cx + 12) + (s.Y - cy) * 0.35) - 2.4)


# ---------------------------------------------------------------- Architect ruin
def tablet():
    s = Sprite(40, 56, seed=305)
    X, Y = s.wobbled(0.8, 6)
    s.paint(box(X, Y, 20, 30, 15, 24, 5), H["coolstone"], **MATTE)
    s.paint(box(s.X, s.Y, 20, 54, 19, 3, 1), H["darkstone"], rim=1)
    s.flat(box(s.X, s.Y, 20, 26, 10, 14, 2), H["coolstone"][0])
    for k in range(3):
        s.flat(box(s.X, s.Y, 20, 17 + k * 9, 6, 1.0), H["cyan"][3], 0.85)
    s.stroke([(7, 10), (11, 20), (9, 30)], 1.0, H["coolstone"][0], 0.8)       # crack
    return s


def pillar(lit):
    s = Sprite(28, 66, seed=306)
    X, Y = s.wobbled(0.6, 6)
    s.paint(box(X, Y, 14, 38, 9, 26, 2), H["coolstone"], **MATTE)
    s.paint(box(s.X, s.Y, 14, 10, 12, 4, 1.5), H["coolstone"], **MATTE)
    s.paint(box(s.X, s.Y, 14, 63, 13, 3, 1), H["darkstone"], rim=1)
    s.flat(box(s.X, s.Y, 14, 30, 7, 8, 1.5), (16, 24, 34) if not lit else H["cyan"][1])
    if lit:
        s.dab(14, 4, 3.5, H["cyan"][4])
        s.dab(14, 4, 1.8, (240, 255, 255))
    return s


def glyph(k):
    """Four Architect glyphs, read from the tablet and matched on the pillars."""
    s = Sprite(12, 12, seed=310 + k)
    c = H["cyan"][4]
    if k == 0:
        s.stroke([(2, 10), (6, 2), (10, 10), (2, 10)], 1.0, c)
    elif k == 1:
        s.flat(subtract(circle(s.X, s.Y, 6, 6, 4.6), circle(s.X, s.Y, 6, 6, 2.6)), c)
        s.dab(6, 6, 1.0, c)
    elif k == 2:
        s.stroke([(2, 2), (10, 10)], 1.0, c)
        s.stroke([(10, 2), (2, 10)], 1.0, c)
    else:
        s.stroke([(2, 3), (10, 3)], 1.0, c)
        s.stroke([(6, 3), (6, 10)], 1.0, c)
        s.stroke([(3, 10), (9, 10)], 1.0, c)
    return s


def chest(opened=False):
    s = Sprite(36, 30, seed=320)
    s.paint(box(s.X, s.Y, 18, 21, 15, 8, 2), H["coolstone"], **MATTE)
    if opened:
        s.paint(box(s.X, s.Y, 18, 7, 15, 3, 1.5), H["coolstone"], rim=1)
        s.dab(18, 14, 4, H["cyan"][4], 0.7)
    else:
        s.paint(box(s.X, s.Y, 18, 11, 15, 4, 2), H["coolstone"], **MATTE)
    s.flat(box(s.X, s.Y, 18, 20, 3, 3, 1), H["cyan"][3])
    s.flat(box(s.X, s.Y, 18, 15, 15, 0.8), H["cyan"][2], 0.8)
    return s


# ---------------------------------------------------------------- materials
def vein(biome, big=True):
    w, h = (46, 36) if big else (24, 20)
    s = Sprite(w, h, seed=330 + len(biome))
    X, Y = s.wobbled(0.8, 5)
    stone = {"ice": H["coolstone"], "volcanic": H["ash"], "crystal": H["darkstone"], "barren": H["regolith"]}.get(
        biome, H["stone"])
    rmp = ramp_of(MAT_HUE[biome])
    rock(s, X, Y, w / 2, h, w * 0.92, h * 0.8, stone)
    picks = [(0.3, 0.75, -1.5), (0.52, 0.95, 0.5), (0.72, 0.7, 2.0)] if big else [(0.4, 0.8, -0.8), (0.62, 0.65, 1.2)]
    for fx, fh, lean in picks:
        crystal(s, X, Y, w * fx, h - 2, h * fh, w * 0.07 + 1, lean, rmp, rim=0.4)
    return s


def mat_icon(biome):
    s = Sprite(14, 14, seed=340 + len(biome))
    rmp = ramp_of(MAT_HUE[biome])
    if biome in ("forest",):                                                    # a heartwood log
        s.paint(capsule(s.X, s.Y, (3, 9), (11, 5), 3.0), H["wood"], highlight=0.5, mottle=0, rim=0.5)
        s.flat(circle(s.X, s.Y, 11, 5, 2.2), rmp[3])
        s.dab(11, 5, 0.8, rmp[1])
    elif biome == "ocean":                                                      # coral branch
        for a, b in (((7, 13), (7, 4)), ((7, 9), (3, 4)), ((7, 8), (11, 3))):
            s.paint(capsule(s.X, s.Y, a, b, 1.5), rmp, highlight=0.5, mottle=0, rim=0.5)
    elif biome == "barren":                                                     # iron ingot
        s.paint(poly(s.X, s.Y, [(1, 11), (4, 5), (13, 5), (10, 11)]), rmp, highlight=0.6, mottle=0, rim=0.5)
        s.flat(poly(s.X, s.Y, [(4, 5), (13, 5), (12, 7), (5, 7)]), rmp[4], 0.8)
    elif biome == "toxic":                                                      # resin drop
        s.paint(smooth_union(circle(s.X, s.Y, 7, 9, 4), poly(s.X, s.Y, [(4, 7), (7, 1), (10, 7)]), 2), rmp,
                highlight=0.7, mottle=0, rim=0.5)
    else:                                                                       # crystal cluster
        crystal(s, s.X, s.Y, 5, 13, 9, 2.4, -1, rmp, rim=0.4)
        crystal(s, s.X, s.Y, 9, 13, 11, 2.6, 1, rmp, rim=0.4)
    return s


# ---------------------------------------------------------------- the cave dungeon
def vault(opened=False):
    s = Sprite(84, 100, seed=350)
    X, Y = s.wobbled(0.8, 7)
    arch = union(box(X, Y, 42, 64, 38, 36, 3), circle(X, Y, 42, 34, 34))
    s.paint(arch, H["darkstone"], **MATTE)
    door = union(box(s.X, s.Y, 42, 72, 22, 28, 1), circle(s.X, s.Y, 42, 44, 22))
    if opened:
        s.flat(door, (14, 10, 20))
        s.dab(42, 80, 8, H["amber"][3], 0.5)
    else:
        s.paint(door, H["coolstone"], **MATTE)
        s.flat(box(s.X, s.Y, 42, 72, 0.8, 28), H["coolstone"][0])
    for k in range(3):                                                          # three sigil sockets
        s.flat(circle(s.X, s.Y, 26 + k * 16, 16, 4), (16, 14, 24))
    s.paint(box(s.X, s.Y, 42, 98, 42, 3, 1), H["darkstone"], rim=1)
    return s


def sigil():
    s = Sprite(18, 24, seed=360)
    s.paint(poly(s.X, s.Y, [(9, 1), (17, 12), (9, 23), (1, 12)]), H["amber"], highlight=0.8, mottle=0)
    s.flat(poly(s.X, s.Y, [(9, 6), (13, 12), (9, 18), (5, 12)]), H["amber"][1])
    s.dab(9, 12, 1.5, H["yellow"][4])
    return s


def cave_wall():
    s = Sprite(40, 64, seed=361)
    X, Y = s.wobbled(1.6, 6)
    s.paint(box(X, Y, 20, 32, 16, 34, 6), H["darkstone"], **MATTE)
    for y in (12, 34, 52):
        s.stroke([(8, y), (30, y + 3)], 1.0, H["darkstone"][0], 0.7)
    return s


# ---------------------------------------------------------------- map icons
def ic(seed):
    return Sprite(14, 14, seed=seed)


def ic_camp():
    s = ic(370)
    s.paint(poly(s.X, s.Y, [(1, 13), (7, 2), (13, 13)]), H["teal"], highlight=0.6, mottle=0, rim=0.6)
    s.flat(poly(s.X, s.Y, [(5, 13), (7, 8), (9, 13)]), (20, 18, 26))
    return s


def ic_pod():
    s = ic(371)
    s.paint(ellipse(s.X, s.Y, 7, 8, 6, 4, rot=-0.4), H["steel"], highlight=0.6, mottle=0, rim=0.6)
    s.dab(8, 7, 1.4, H["cyan"][4])
    return s


def ic_ruin():
    s = ic(372)
    for x in (3, 7, 11):
        s.paint(box(s.X, s.Y, x, 8, 1.4, 5 - abs(x - 7) * 0.3), H["coolstone"], highlight=0.6, mottle=0, rim=0.5)
    s.flat(box(s.X, s.Y, 7, 2.5, 6, 1), H["cyan"][3])
    return s


def ic_vault():
    s = ic(373)
    s.paint(union(box(s.X, s.Y, 7, 9, 5, 4.5), circle(s.X, s.Y, 7, 5, 5)), H["darkstone"], highlight=0.6, mottle=0)
    s.flat(union(box(s.X, s.Y, 7, 10, 2.4, 3.4), circle(s.X, s.Y, 7, 7, 2.4)), H["amber"][3])
    return s


def ic_cave():
    s = ic(374)
    s.paint(poly(s.X, s.Y, [(0, 13), (3, 4), (8, 1), (13, 6), (14, 13)]), H["stone"], highlight=0.6, mottle=0)
    s.flat(ellipse(s.X, s.Y, 7, 11, 3.5, 4), (16, 12, 20))
    return s


def ic_rocket():
    s = ic(375)
    s.paint(ellipse(s.X, s.Y, 7, 6, 3.4, 6), H["steel"], highlight=0.7, mottle=0, rim=0.6)
    s.dab(7, 5, 1.3, H["cyan"][4])
    for d in (-1, 1):
        s.paint(poly(s.X, s.Y, [(7 + d * 3, 8), (7 + d * 6, 13), (7 + d * 3, 12)]), H["red"], rim=0.4, mottle=0)
    return s


def ic_unknown():
    s = ic(376)
    s.paint(circle(s.X, s.Y, 7, 7, 5.6), H["steel"][:3], highlight=0.5, mottle=0, rim=0.5)
    s.stroke([(5, 5), (7, 4), (9, 5), (7.5, 7.5), (7, 9)], 1.0, H["cream"][4])
    s.dab(7, 11, 0.8, H["cream"][4])
    return s


def ic_skull():
    s = ic(377)
    s.paint(union(circle(s.X, s.Y, 7, 6, 5), box(s.X, s.Y, 7, 10.5, 3, 2.4)), H["bone"], highlight=0.6, mottle=0)
    for x in (5, 9):
        s.dab(x, 6.5, 1.3, (24, 18, 28))
    return s


def build_all():
    out = {"poi/tent.png": tent, "poi/campfire0.png": lambda: campfire(0), "poi/campfire1.png": lambda: campfire(1),
           "poi/supply_crate.png": supply_crate, "poi/pod.png": pod, "poi/pod_open.png": lambda: pod(True),
           "poi/tablet.png": tablet, "poi/pillar.png": lambda: pillar(False),
           "poi/pillar_lit.png": lambda: pillar(True), "poi/chest.png": chest,
           "poi/chest_open.png": lambda: chest(True), "poi/vault.png": vault,
           "poi/vault_open.png": lambda: vault(True), "poi/sigil.png": sigil, "poi/cave_wall.png": cave_wall}
    for k in range(GLYPHS):
        out[f"poi/glyph{k}.png"] = lambda k=k: glyph(k)
    for b in MAT_HUE:
        out[f"poi/vein_{b}.png"] = lambda b=b: vein(b, True)
        out[f"props/mat_{b}.png"] = lambda b=b: vein(b, False)
    for rel, fn in out.items():
        save(fn(), rel)
    icons = {"camp": ic_camp, "pod": ic_pod, "ruin": ic_ruin, "vault": ic_vault, "cave": ic_cave,
             "rocket": ic_rocket, "unknown": ic_unknown, "skull": ic_skull,
             **{f"mat_{b}": (lambda b=b: mat_icon(b)) for b in MAT_HUE}}
    ui_icons = ROOT / "assets" / "ui" / "icons"
    for name, fn in icons.items():
        fn().save(ui_icons / f"{name}.png")
    return list(out)
