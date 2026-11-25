"""The shared perceptual palette (OkLCh) used at runtime - the same maths as
tools/pixelkit.py, so runtime-painted things (planets, UI liquids) match the art."""
from __future__ import annotations

import math
from functools import lru_cache

LADDER = [(0.31, 0.105), (0.44, 0.160), (0.57, 0.195), (0.69, 0.190), (0.81, 0.125)]


def _to_rgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def lch(L, C, h):
    for _ in range(30):
        rgb = _to_rgb(L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))
        if all(-0.001 <= c <= 1.001 for c in rgb):
            break
        C *= 0.93

    def enc(c):
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(int(round(enc(c) * 255)) for c in rgb)


def _shift(h, target, k):
    return h + ((target - h + 180) % 360 - 180) * k


@lru_cache(maxsize=512)
def hue_ramp(h, levels=5, chroma=1.0, light=0.0, warm=72.0, cool=285.0):
    out = []
    ladder = LADDER[:levels]
    for i, (L, C) in enumerate(ladder):
        k = i / max(1, len(ladder) - 1)
        hh = _shift(h, cool, 0.22 * (1 - k) ** 1.5) if k < 0.5 else _shift(h, warm, 0.18 * (k - 0.5) * 2)
        out.append(lch(min(0.95, L + light), C * chroma, hh))
    return tuple(out)
