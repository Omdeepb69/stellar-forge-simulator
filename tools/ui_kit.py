"""Paints the interface parts for each UI theme with pixelkit (same style as the
sprites): panels, buttons, gauge tubes, portrait porthole, name tab, key caps
and icons. Output: assets/ui/<theme>/*.png plus theme.json (colours, borders).

Themes are derived from original assets:
  console - teal machinery + gold lamp (stronghold/device.png, boss_fight/pillar.png)
  hull    - riveted rusty metal + amber screens (rocket/rocket.png)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from pixelkit import R, Sprite, box, circle, ellipse, hue_ramp, poly, subtract, union  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

THEMES = {
    "console": dict(
        frame=R["teal"], trim=R["gold"], plate=hue_ramp(190, chroma=0.55, light=0.04),
        glass=(6, 24, 28), glass2=(10, 34, 38), glass_line=(34, 104, 104),
        text=(220, 250, 240), accent=(255, 214, 90), dim=(110, 172, 166), good=(140, 255, 170),
        bad=(255, 110, 90), rust=False),
    "hull": dict(
        frame=R["steel"], trim=R["rust"], plate=hue_ramp(60, chroma=0.18, light=0.02),
        glass=(22, 13, 6), glass2=(32, 20, 9), glass_line=(110, 70, 26),
        text=(255, 220, 150), accent=(255, 160, 60), dim=(176, 134, 86), good=(170, 240, 120),
        bad=(255, 100, 80), rust=True),
}


def _rivet(s, x, y, rmp):
    s.paint(circle(s.X, s.Y, x, y, 1.7), rmp, highlight=0.8, mottle=0, rim=1)


def _rust(s, cx, cy, rmp, seed):
    rng = np.random.default_rng(seed)
    for _ in range(4):
        s.dab(cx + rng.uniform(-3, 3), cy + rng.uniform(-3, 3), rng.uniform(0.7, 1.4), rmp[rng.integers(0, 2)], 0.9)


def panel(t):
    """40x40 panel, 13-px border: bevelled frame ring, rivets, recessed glass."""
    s = Sprite(40, 40, seed=1)
    outer = box(s.X, s.Y, 20, 20, 19.5, 19.5, 6)
    inner = box(s.X, s.Y, 20, 20, 11, 11, 3)
    s.paint(subtract(outer, inner), t["frame"], highlight=0, mottle=0, rim=1, pillow=4)
    lip = subtract(box(s.X, s.Y, 20, 20, 11.5, 11.5, 3), inner)
    s.flat(lip, t["trim"][1], 0.9)
    s.flat(inner, t["glass"])
    s.flat(box(s.X, s.Y, 20, 9.4, 9, 0.5), t["glass_line"])
    for (x, y) in ((4.5, 4.5), (35.5, 4.5), (4.5, 35.5), (35.5, 35.5)):
        _rivet(s, x, y, t["trim"])
        if t["rust"]:
            _rust(s, x + 1.5, y + 1.5, R["rust"], int(x * 7 + y))
    return s, 13


def button(t, selected=False):
    """32x16 plaque, 6-px border. Selected: gold rim + lamp."""
    s = Sprite(32, 16, seed=2)
    outer = box(s.X, s.Y, 16, 8, 15.5, 7.5, 4)
    rim = t["trim"] if selected else t["frame"]
    s.paint(outer, rim, highlight=0, mottle=0, rim=1, pillow=3)
    face = box(s.X, s.Y, 16, 8, 12.5, 4.6, 2)
    s.flat(face, t["glass2"] if not selected else tuple(min(255, c + 14) for c in t["glass2"]))
    s.flat(box(s.X, s.Y, 16, 3.9, 11.5, 0.5), t["glass_line"])
    return s, 6


def tube(t):
    """32x14 gauge tube, 7-px border: metal caps, glass walls, empty interior."""
    s = Sprite(32, 14, seed=3)
    glass = box(s.X, s.Y, 16, 7, 14, 5.5, 5)
    s.flat(glass, (10, 12, 20), 0.85)
    s.flat(subtract(glass, box(s.X, s.Y, 16, 7, 12.8, 4.3, 4)), t["glass_line"], 0.95)
    s.flat(box(s.X, s.Y, 16, 2.6, 11, 0.5), (230, 240, 255), 0.35)
    for cx in (2.5, 29.5):
        s.paint(box(s.X, s.Y, cx, 7, 2.5, 6.5, 1.2), t["frame"], highlight=0.5, mottle=0, rim=1, pillow=2)
    return s, 6


def porthole(t):
    s = Sprite(44, 44, seed=4)
    ring = subtract(circle(s.X, s.Y, 22, 22, 21.5), circle(s.X, s.Y, 22, 22, 16))
    s.paint(ring, t["frame"], highlight=0.6, mottle=0, rim=1, pillow=4)
    s.flat(subtract(circle(s.X, s.Y, 22, 22, 16.6), circle(s.X, s.Y, 22, 22, 16)), t["trim"][1])
    for a in range(0, 360, 60):
        _rivet(s, 22 + math.cos(math.radians(a)) * 19, 22 + math.sin(math.radians(a)) * 19, t["trim"])
    return s, 0


def tab(t):
    s = Sprite(24, 12, seed=5)
    s.paint(box(s.X, s.Y, 12, 6, 11.5, 5.5, 3), t["trim"], highlight=0.4, mottle=0, rim=1, pillow=2.5)
    return s, 5


def keycap(t):
    s = Sprite(14, 14, seed=6)
    s.paint(box(s.X, s.Y, 7, 7, 6.5, 6.5, 2), R["steel"] if not t["rust"] else R["stone"], highlight=0.6, mottle=0,
            rim=1, pillow=3)
    s.flat(box(s.X, s.Y, 7, 6.2, 4.6, 4.2, 1.5), (34, 36, 46))
    return s, 5


def plate(t, rim_ramp=None):
    """24x16 slim plaque, 6-px border, for small widgets (prompts, wallet, toasts).
    A thin painted rim around dark glass: light enough for tiny sizes."""
    s = Sprite(24, 16, seed=7)
    outer = box(s.X, s.Y, 12, 8, 11.5, 7.5, 4)
    glass = box(s.X, s.Y, 12, 8, 9.2, 5.2, 2.5)
    s.paint(subtract(outer, glass), rim_ramp or t["frame"], highlight=0, mottle=0, rim=1, pillow=2)
    s.flat(glass, t["glass"])
    s.flat(box(s.X, s.Y, 12, 3.4, 8, 0.5), t["glass_line"])
    return s, 6


def nameplate(t):
    """Speaker/location tag: dark glass with a thin gold rim and two bolts, so
    light text stays readable (the old solid-gold tab was not)."""
    s = Sprite(24, 14, seed=8)
    outer = box(s.X, s.Y, 12, 7, 11.5, 6.5, 2)
    glass = box(s.X, s.Y, 12, 7, 9.6, 4.6, 1)
    s.paint(subtract(outer, glass), t["trim"], highlight=0, mottle=0, rim=1, pillow=1.5)
    s.flat(glass, (14, 12, 10))
    for x in (2.6, 21.4):
        s.dab(x, 7, 0.9, t["trim"][-1])
    return s, 6


def chip(t):
    s = Sprite(12, 10, seed=9)
    s.paint(box(s.X, s.Y, 6, 5, 5.5, 4.5, 2.5), t["plate"][:3], highlight=0, mottle=0, rim=1, pillow=2)
    return s, 4


def iconbtn(t, selected=False):
    s = Sprite(22, 22, seed=10)
    outer = box(s.X, s.Y, 11, 11, 10.5, 10.5, 4)
    face = box(s.X, s.Y, 11, 11, 7.5, 7.5, 2.5)
    s.paint(subtract(outer, face), t["trim"] if selected else t["frame"], highlight=0, mottle=0, rim=1, pillow=2.5)
    s.flat(face, tuple(min(255, c + 16) for c in t["glass2"]) if selected else t["glass"])
    s.flat(box(s.X, s.Y, 11, 4.4, 6.5, 0.5), t["glass_line"])
    return s, 9


# ---------------------------------------------------------------- icons (shared)
def icon_coin():
    s = Sprite(14, 14, seed=11)
    s.paint(circle(s.X, s.Y, 7, 7, 6.2), R["gold"], highlight=0.7, mottle=0)
    s.stroke([(7, 4), (7, 10)], 1.4, R["gold"][0], 0.9)
    return s


def icon_ore():
    """A chunky crystal shard: one clear silhouette that reads at 14 px."""
    s = Sprite(14, 14, seed=12)
    s.paint(poly(s.X, s.Y, [(3, 13), (1.5, 7), (5.5, 1), (11, 3), (12.5, 9), (9, 13)]), hue_ramp(200),
            highlight=0.8, mottle=0)
    s.stroke([(5.5, 2), (6.5, 7), (3, 12)], 1.0, hue_ramp(200)[4], 0.8)
    s.stroke([(6.5, 7), (12, 8.5)], 1.0, hue_ramp(200)[1], 0.8)
    return s


def _icon(seed):
    return Sprite(14, 14, seed=seed)


def icon_data():
    s = _icon(20)
    s.paint(box(s.X, s.Y, 7, 7, 5, 5, 1.2), hue_ramp(150), highlight=0.5, mottle=0)
    s.flat(box(s.X, s.Y, 7, 7, 2.6, 2.6, 0.6), hue_ramp(150)[4])
    for k in range(3):
        for (x, y, w, h) in ((1, 4 + k * 3, 1, 0.5), (13, 4 + k * 3, 1, 0.5), (4 + k * 3, 1, 0.5, 1),
                             (4 + k * 3, 13, 0.5, 1)):
            s.flat(box(s.X, s.Y, x, y, w, h), R["steel"][3])
    return s


def icon_engine():
    s = _icon(21)
    s.paint(poly(s.X, s.Y, [(4, 2), (10, 2), (12, 9), (2, 9)]), R["steel"], highlight=0.5, mottle=0)
    s.paint(poly(s.X, s.Y, [(4, 9), (10, 9), (7, 13.5)]), hue_ramp(55), highlight=0.5, mottle=0, rim=0)
    s.dab(7, 10.5, 1.2, (255, 240, 170))
    return s


def icon_blaster():
    s = _icon(22)
    s.paint(box(s.X, s.Y, 6, 6, 5, 2.4, 1), R["steel"], highlight=0.5, mottle=0)
    s.paint(box(s.X, s.Y, 4.5, 10, 1.8, 2.8, 0.8), hue_ramp(25), highlight=0.3, mottle=0)
    s.flat(box(s.X, s.Y, 12, 6, 1.6, 1.2), hue_ramp(215)[4])
    return s


def icon_scanner():
    s = _icon(23)
    s.paint(circle(s.X, s.Y, 7, 7, 6.3), hue_ramp(150)[:3], highlight=0, mottle=0)
    s.flat(subtract(circle(s.X, s.Y, 7, 7, 4.2), circle(s.X, s.Y, 7, 7, 3.4)), hue_ramp(150)[4], 0.8)
    s.stroke([(7, 7), (11.5, 3.5)], 1.2, hue_ramp(150)[4])
    s.dab(9, 9.5, 0.9, hue_ramp(25)[4])
    return s


def icon_suit():
    s = _icon(24)
    s.paint(circle(s.X, s.Y, 7, 6.5, 5.2), R["pilot"], highlight=0.6, mottle=0)
    s.flat(ellipse(s.X, s.Y, 8, 6, 2.6, 2), (130, 230, 250))
    s.paint(box(s.X, s.Y, 7, 12.5, 4.5, 1.4, 1), R["pilot"][:3], highlight=0, mottle=0)
    return s


def icon_wrench():
    s = _icon(25)
    s.paint(capsule_(s, (3, 11), (9.5, 4.5), 1.3), R["steel"], highlight=0.5, mottle=0)
    s.paint(subtract(circle(s.X, s.Y, 10.5, 3.5, 2.8), circle(s.X, s.Y, 11.8, 2.2, 1.6)), R["steel"],
            highlight=0.5, mottle=0)
    return s


def icon_ship():
    s = _icon(26)
    s.paint(poly(s.X, s.Y, [(7, 1), (10, 7), (10, 11), (4, 11), (4, 7)]), R["steel"], highlight=0.6, mottle=0)
    s.paint(poly(s.X, s.Y, [(4, 7), (1, 12), (4, 11)]), hue_ramp(25), mottle=0)
    s.paint(poly(s.X, s.Y, [(10, 7), (13, 12), (10, 11)]), hue_ramp(25), mottle=0)
    s.dab(7, 5.5, 1.3, hue_ramp(215)[3])
    return s


def icon_scroll():
    s = _icon(27)
    s.paint(box(s.X, s.Y, 7, 7, 4.5, 5.8, 0.8), R["sand"][2:], highlight=0.3, mottle=0)
    for y in (4.5, 7, 9.5):
        s.flat(box(s.X, s.Y, 7, y, 2.8, 0.45), R["sand"][0])
    s.dab(10, 11, 1.6, hue_ramp(25)[2])
    return s


def icon_star():
    s = _icon(28)
    pts = [(7 + math.cos(-math.pi / 2 + k * math.pi / 5) * (6.3 if k % 2 == 0 else 2.7),
            7.4 + math.sin(-math.pi / 2 + k * math.pi / 5) * (6.3 if k % 2 == 0 else 2.7)) for k in range(10)]
    s.paint(poly(s.X, s.Y, pts), R["gold"], highlight=0.6, mottle=0)
    return s


def icon_gear():
    s = _icon(29)
    teeth = [box(s.X, s.Y, 7 + math.cos(a) * 5, 7 + math.sin(a) * 5, 1.4, 1.4)
             for a in [k * math.pi / 4 for k in range(8)]]
    s.paint(subtract(union(circle(s.X, s.Y, 7, 7, 4.6), *teeth), circle(s.X, s.Y, 7, 7, 1.8)), R["steel"],
            highlight=0.5, mottle=0)
    return s


def icon_play():
    s = _icon(30)
    s.paint(poly(s.X, s.Y, [(3, 2), (12, 7), (3, 12)]), hue_ramp(145), highlight=0.5, mottle=0)
    return s


def icon_plus():
    s = _icon(31)
    s.paint(union(box(s.X, s.Y, 7, 7, 1.8, 5.5, 0.6), box(s.X, s.Y, 7, 7, 5.5, 1.8, 0.6)), R["gold"],
            highlight=0.5, mottle=0)
    return s


def icon_folder():
    s = _icon(32)
    s.paint(union(box(s.X, s.Y, 7, 8, 6, 4.5, 1), box(s.X, s.Y, 4.5, 3.5, 3, 1.5, 0.6)), R["sand"][1:],
            highlight=0.4, mottle=0)
    return s


def icon_door():
    s = _icon(33)
    s.paint(box(s.X, s.Y, 7, 7.5, 4.2, 6, 1), hue_ramp(25), highlight=0.4, mottle=0)
    s.dab(9, 8, 0.8, R["gold"][3])
    return s


def icon_book():
    s = _icon(34)
    s.paint(box(s.X, s.Y, 7, 7, 5.5, 6, 1), hue_ramp(255), highlight=0.4, mottle=0)
    s.flat(box(s.X, s.Y, 7, 7, 0.5, 5.5), hue_ramp(255)[0])
    s.flat(box(s.X, s.Y, 9.5, 4, 1.6, 0.45), hue_ramp(255)[4])
    return s


def capsule_(s, a, b, r):
    from pixelkit import capsule
    return capsule(s.X, s.Y, a, b, r)


def icon_fuel():
    s = Sprite(14, 14, seed=13)
    s.paint(box(s.X, s.Y, 7, 8, 4.6, 5.4, 1.6), hue_ramp(60), highlight=0.6, mottle=0)
    s.flat(box(s.X, s.Y, 7, 2, 2.2, 1.2), R["steel"][1])
    s.stroke([(8, 5), (6, 8), (8, 8), (6, 11)], 1.1, (255, 240, 170), 0.95)
    return s


def icon_hull():
    s = Sprite(14, 14, seed=14)
    s.paint(poly(s.X, s.Y, [(1.5, 2.5), (12.5, 2.5), (12.5, 8), (7, 13), (1.5, 8)]), hue_ramp(25), highlight=0.6,
            mottle=0)
    s.flat(box(s.X, s.Y, 7, 6.5, 1.1, 3.2), (255, 235, 225))
    s.flat(box(s.X, s.Y, 7, 6.5, 3.2, 1.1), (255, 235, 225))
    return s


def icon_shield():
    s = Sprite(14, 14, seed=15)
    s.paint(poly(s.X, s.Y, [(7, 1), (13, 3.5), (12, 9), (7, 13.5), (2, 9), (1, 3.5)]), hue_ramp(250),
            highlight=0.7, mottle=0)
    return s


def icon_key():
    s = Sprite(14, 14, seed=16)
    s.paint(subtract(circle(s.X, s.Y, 4.5, 4.5, 3.8), circle(s.X, s.Y, 4.5, 4.5, 1.6)), R["gold"], highlight=0.6,
            mottle=0)
    s.paint(union(box(s.X, s.Y, 9, 9, 4.5, 1.2, 0.5), box(s.X, s.Y, 11.5, 10.8, 1, 1.6)),
            R["gold"], highlight=0.4, mottle=0, rim=0.5)
    return s


ICONS = {"coin": icon_coin, "ore": icon_ore, "fuel": icon_fuel, "hull": icon_hull, "shield": icon_shield,
         "key": icon_key, "data": icon_data, "engine": icon_engine, "blaster": icon_blaster,
         "scanner": icon_scanner, "suit": icon_suit, "wrench": icon_wrench, "ship": icon_ship,
         "scroll": icon_scroll, "star": icon_star, "gear": icon_gear, "play": icon_play, "plus": icon_plus,
         "folder": icon_folder, "door": icon_door, "book": icon_book}


def build(out_root=None):
    out_root = Path(out_root or ROOT / "assets" / "ui")
    for name, t in THEMES.items():
        d = out_root / name
        meta = {"borders": {}, "colors": {k: list(v) for k, v in t.items() if isinstance(v, tuple)}}
        for part, fn in (("panel", panel), ("button", button), ("button_sel", lambda t: button(t, True)),
                         ("tube", tube), ("porthole", porthole), ("tab", tab), ("keycap", keycap),
                         ("plate", plate), ("plate_gold", lambda t: plate(t, t["trim"])),
                         ("nameplate", nameplate), ("chip", chip), ("iconbtn", iconbtn),
                         ("iconbtn_sel", lambda t: iconbtn(t, True))):
            spr, border = fn(t)
            spr.save(d / f"{part}.png")
            meta["borders"][part] = border
        (d / "theme.json").write_text(json.dumps(meta, indent=1))
    for name, fn in ICONS.items():
        fn().save(out_root / "icons" / f"{name}.png")
    return out_root


if __name__ == "__main__":
    print(build())
