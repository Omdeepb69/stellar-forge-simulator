"""Shared palette and painting helpers for the art build (docs/ART_STYLE.md)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
from pixelkit import (R, Sprite, box, capsule, circle, ellipse, hue_ramp, poly, smooth_union,  # noqa: E402,F401
                      subtract, union, value_noise)

ROOT = Path(__file__).resolve().parent.parent.parent
GEN = ROOT / "assets" / "generated"

# One palette, many hues, identical lightness/chroma steps (OkLCh).
HUES = {"red": 25, "orange": 55, "amber": 75, "yellow": 95, "lime": 125, "green": 145, "teal": 185,
        "cyan": 215, "blue": 255, "indigo": 280, "violet": 305, "magenta": 335, "rose": 5}
H = {name: hue_ramp(h) for name, h in HUES.items()}
H.update({
    "soil": hue_ramp(60, chroma=0.45, light=-0.06), "soildeep": hue_ramp(40, chroma=0.35, light=-0.13),
    "stone": hue_ramp(70, chroma=0.12), "coolstone": hue_ramp(250, chroma=0.12),
    "darkstone": hue_ramp(300, chroma=0.12, light=-0.12), "bone": hue_ramp(85, chroma=0.22, light=0.08),
    "cream": hue_ramp(90, chroma=0.28, light=0.06), "skin": hue_ramp(190, chroma=0.75),
    "sand": hue_ramp(75, chroma=0.55, light=0.08), "snow": hue_ramp(220, chroma=0.18, light=0.14),
    "ice": hue_ramp(205, chroma=0.55, light=0.10), "wood": hue_ramp(55, chroma=0.55, light=-0.08),
    "steel": hue_ramp(240, chroma=0.10, light=0.02), "rust": hue_ramp(45, chroma=0.65, light=-0.04),
    "ash": hue_ramp(20, chroma=0.10, light=-0.10), "regolith": hue_ramp(60, chroma=0.06),
})
MATTE = dict(highlight=0.7, shine=0.0, mottle=0.06)


def ramp_of(name_or_hue):
    if isinstance(name_or_hue, (int, float)):
        return hue_ramp(name_or_hue)
    return H[name_or_hue]


def mute(rmp, k, sky):
    """Background version of a ramp: blended towards the sky so it recedes."""
    return [tuple(int(c[i] * k + sky[i] * (1 - k)) for i in range(3)) for c in rmp]


def crystal(s, X, Y, x, base, h, w, lean, rmp, rim=0.8):
    pts = [(x - w, base), (x - w * 0.7 + lean * 0.7, base - h * 0.8), (x + lean, base - h),
           (x + w * 0.7 + lean * 0.7, base - h * 0.8), (x + w, base)]
    s.paint(poly(X, Y, pts), rmp, highlight=0.6, mottle=0.03, rim=rim)
    s.stroke([(x - w * 0.3, base - 2), (x + lean * 0.6 - 0.5, base - h * 0.85)], 1.0, rmp[3], 0.55)


def rock(s, X, Y, cx, base, w, h, rmp, seed=0):
    body = smooth_union(ellipse(X, Y, cx - w * 0.12, base - h * 0.45, w * 0.42, h * 0.5),
                        ellipse(X, Y, cx + w * 0.18, base - h * 0.35, w * 0.32, h * 0.38), 3)
    body = subtract(body, box(s.X, s.Y, cx, base + 4, w, 4))
    s.paint(body, rmp, **MATTE)
    return body


def tuft(s, X, Y, x, base, h, rmp, lean=0.0, width=1.4):
    s.paint(capsule(X, Y, (x, base), (x + lean, base - h), width, 0.5), rmp, rim=0, mottle=0.02)


def save(s, rel):
    s.save(GEN / rel)


__all__ = ["np", "math", "R", "Sprite", "box", "capsule", "circle", "ellipse", "hue_ramp", "poly",
           "smooth_union", "subtract", "union", "value_noise", "H", "MATTE", "ramp_of", "mute", "crystal",
           "rock", "tuft", "save", "GEN", "ROOT"]
