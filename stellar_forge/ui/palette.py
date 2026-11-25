"""Signal colours, with a colour-blind friendly alternative.

Gameplay-critical colours (enemies vs friends, compass arrows, warnings)
come from here so the Settings toggle changes them everywhere at once.
The alternative set follows the Okabe-Ito palette (safe for deuteranopia
and protanopia)."""
from __future__ import annotations

NORMAL = {
    "enemy": (255, 80, 80), "friend": (120, 255, 150), "quest": (255, 210, 90), "shard": (200, 150, 255),
    "target": (140, 220, 255), "waypoint": (90, 230, 160), "rumour": (170, 240, 120), "danger": (255, 80, 80),
    "good": (120, 255, 150), "signal": (90, 240, 220),
}
COLORBLIND = {
    "enemy": (230, 159, 0), "friend": (86, 180, 233), "quest": (240, 228, 66), "shard": (204, 121, 167),
    "target": (86, 180, 233), "waypoint": (0, 158, 115), "rumour": (240, 228, 66), "danger": (230, 159, 0),
    "good": (86, 180, 233), "signal": (0, 158, 115),
}

_active = NORMAL


def set_colorblind(on: bool) -> None:
    global _active
    _active = COLORBLIND if on else NORMAL


def col(name: str) -> tuple:
    return _active[name]
