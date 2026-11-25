"""Text, panels and bars for the whole game, in the house style.

Everything goes through the pixel font (ui/pixelfont.py) and the painted
Console kit (ui/pixelui.py). Older call sites still pass point sizes; they are
mapped to whole-number font scales so every glyph keeps square pixels.
"""
from __future__ import annotations

import pygame

from .. import config
from . import pixelfont

_THEME = None


def theme():
    """The game's interface theme (the painted Console kit), loaded on first use."""
    global _THEME
    if _THEME is None:
        from .pixelui import Theme
        _THEME = Theme("console")
    return _THEME


def scale_for(size: int) -> int:
    if size <= 17:
        return 2
    if size <= 27:
        return 3
    if size <= 42:
        return 4
    return 6


def font(size: int, bold: bool = False):
    """Compatibility shim: an object with .size(text) like pygame.font.Font."""
    sc = scale_for(size)

    class _F:
        @staticmethod
        def size(msg):
            return pixelfont.width(str(msg), sc), pixelfont.HEIGHT * sc
    return _F()


def text(surf, msg, pos, size=16, color=config.WHITE, bold=False, anchor="topleft", shadow=True, outline=False):
    return pixelfont.draw(surf, str(msg), pos, scale_for(size), tuple(color)[:3], anchor,
                          shadow=(10, 8, 18) if shadow and not outline else None,
                          outline=(8, 8, 14) if outline else None)


def wrap(msg: str, size: int, width: int, bold=False) -> list[str]:
    return pixelfont.wrap(msg, width, scale_for(size))


GOLDISH = {(255, 210, 120), (255, 210, 90), (200, 170, 90), (255, 214, 90), (255, 200, 110)}


def panel(surf, rect, color=None, border=None, radius=8, corners=True):
    """Big rectangles get the riveted Console panel; small ones the slim plaque.
    A gold ``border`` marks a selected / rewarding element."""
    rect = pygame.Rect(rect)
    th = theme()
    gold = border is not None and tuple(border[:3]) in GOLDISH
    if rect.h >= 200 and rect.w >= 360 and not gold:
        return th.panel(surf, rect)
    return th.plate(surf, rect, gold=gold)


def bar(surf, rect, frac, color, back=(30, 30, 40), label=None, size=13):
    """A chunky pixel bar with a highlight row (used where a liquid tube won't fit)."""
    from .pixelui import bar as pbar
    rect = pygame.Rect(rect)
    pbar(surf, rect, frac, tuple(color)[:3])
    if label:
        text(surf, label, (rect.x + 8, rect.centery), size, (240, 240, 248), anchor="midleft", outline=True)
