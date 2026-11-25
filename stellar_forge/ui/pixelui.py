"""Pixel-art interface kit, derived from the original dialog boxes
(``dialog/mainCharDialogBox.png``): black panels, a thick coloured frame with
a lighter bevel, a thin grey inner line, and portraits that overlap the frame.

Everything is drawn in "UI pixels" of ``U`` screen pixels so the interface has
the same chunky grain as the sprites.
"""
from __future__ import annotations

import pygame

from . import pixelfont

U = 2   # one UI pixel = 2 screen pixels

FRAMES = {   # (frame, bevel light, bevel dark)
    "blue": ((24, 64, 150), (64, 116, 200), (10, 32, 84)),
    "green": ((14, 70, 22), (40, 120, 50), (6, 36, 10)),
    "gold": ((150, 112, 30), (220, 180, 70), (90, 62, 12)),
    "red": ((150, 34, 34), (210, 80, 70), (80, 14, 14)),
    "teal": ((18, 110, 111), (40, 170, 170), (10, 60, 62)),
    "grey": ((70, 74, 86), (110, 116, 130), (40, 42, 52)),
}
INNER = (128, 128, 128)
FILL = (0, 0, 0)
TEXT = (236, 240, 248)
DIM = (150, 156, 172)
GOLD = (255, 214, 90)


def _r(surf, color, x, y, w, h):
    if w > 0 and h > 0:
        surf.fill(color, (x, y, w, h))


def frame(surf, rect, style="blue", fill=FILL, alpha=255, inner=True):
    """A panel in the house style. ``rect`` is in screen pixels."""
    x, y, w, h = pygame.Rect(rect)
    col, light, dark = FRAMES.get(style, FRAMES["blue"])
    u = U
    if alpha < 255:
        tmp = pygame.Surface((w, h), pygame.SRCALPHA)
        tmp.fill((*fill, alpha))
        surf.blit(tmp, (x + u, y + u), (0, 0, w - 2 * u, h - 2 * u))
    else:
        _r(surf, fill, x + u, y + u, w - 2 * u, h - 2 * u)
    # thick frame with clipped (pixel-rounded) corners
    t = 3 * u
    _r(surf, col, x + u, y, w - 2 * u, t)
    _r(surf, col, x + u, y + h - t, w - 2 * u, t)
    _r(surf, col, x, y + u, t, h - 2 * u)
    _r(surf, col, x + w - t, y + u, t, h - 2 * u)
    # bevel: light on top/left, dark on bottom/right
    _r(surf, light, x + 2 * u, y + u, w - 4 * u, u)
    _r(surf, light, x + u, y + 2 * u, u, h - 4 * u)
    _r(surf, dark, x + 2 * u, y + h - 2 * u, w - 4 * u, u)
    _r(surf, dark, x + w - 2 * u, y + 2 * u, u, h - 4 * u)
    if inner and w > 10 * u and h > 10 * u:   # the thin grey hairline from the originals
        i = t + u
        _r(surf, INNER, x + i, y + i, w - 2 * i, u // 2 or 1)
        _r(surf, INNER, x + i, y + h - i - 1, w - 2 * i, u // 2 or 1)
        _r(surf, INNER, x + i, y + i, u // 2 or 1, h - 2 * i)
        _r(surf, INNER, x + w - i - 1, y + i, u // 2 or 1, h - 2 * i)
    return pygame.Rect(x, y, w, h)


def content_rect(rect) -> pygame.Rect:
    r = pygame.Rect(rect)
    pad = 6 * U
    return r.inflate(-2 * pad, -2 * pad)


def text(surf, msg, pos, scale=2, color=TEXT, anchor="topleft"):
    return pixelfont.draw(surf, msg, pos, scale, color, anchor)


def bar(surf, rect, frac, color, back=(28, 24, 40), segments=0):
    """Chunky pixel bar with a 1-UI-pixel highlight; optional segment notches."""
    x, y, w, h = pygame.Rect(rect)
    _r(surf, (10, 8, 16), x, y, w, h)
    _r(surf, back, x + U, y + U, w - 2 * U, h - 2 * U)
    fw = int((w - 2 * U) * max(0.0, min(1.0, frac)))
    if fw > 0:
        _r(surf, color, x + U, y + U, fw, h - 2 * U)
        hl = tuple(min(255, c + 60) for c in color)
        _r(surf, hl, x + U, y + U, fw, U)
        sh = tuple(int(c * 0.65) for c in color)
        _r(surf, sh, x + U, y + h - 2 * U, fw, U)
    if segments:
        step = (w - 2 * U) / segments
        for k in range(1, segments):
            _r(surf, (10, 8, 16), int(x + U + k * step), y + U, U // 2 or 1, h - 2 * U)


def button(surf, rect, label, selected=False, scale=2, style="blue"):
    frame(surf, rect, "gold" if selected else style, fill=(14, 12, 26) if selected else FILL, inner=False)
    r = pygame.Rect(rect)
    if selected:
        cx, cy = r.x + 9 * U, r.centery
        for k in range(3):   # pixel arrow
            _r(surf, GOLD, cx + k * U, cy - (2 - k) * U, U, (2 - k) * 2 * U + U)
    text(surf, label, r.center, scale, GOLD if selected else TEXT, anchor="center")


def dialog(surf, rect, portrait, name, body_lines, style="blue", name_color=GOLD):
    """The original dialog box: portrait overlapping the frame's top-left corner."""
    r = frame(surf, rect, style)
    if portrait is not None:
        p = portrait
        surf.blit(p, p.get_rect(bottomleft=(r.x - 2 * U, r.y + p.get_height() * 0.55)))
        tx = r.x + p.get_width() + 2 * U
    else:
        tx = r.x + 10 * U
    text(surf, name, (tx, r.y + 7 * U), 2, name_color)
    for i, line in enumerate(body_lines):
        text(surf, line, (tx, r.y + 20 * U + i * 11 * U), 2, TEXT)
    return r


# =============================================================================
# Painted themes (v2): parts painted by tools/ui_kit.py in the sprite style,
# assembled as nine-slices at a whole-number scale.
import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

UI_DIR = _Path(__file__).resolve().parent.parent.parent / "assets" / "ui"


class NineSlice:
    """Corners stay fixed; edges and centre are TILED (never stretched), so every
    pixel on screen keeps the same size."""

    def __init__(self, img: pygame.Surface, border: int, scale: int = U):
        self.scale = scale
        self.img = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
        self.b = border * scale
        w, h = self.img.get_size()
        b = self.b
        cut = lambda x, y, ww, hh: self.img.subsurface((x, y, ww, hh)).copy()  # noqa: E731
        if b:
            self.tl, self.tr = cut(0, 0, b, b), cut(w - b, 0, b, b)
            self.bl, self.br = cut(0, h - b, b, b), cut(w - b, h - b, b, b)
            self.t, self.bt = cut(b, 0, w - 2 * b, b), cut(b, h - b, w - 2 * b, b)
            self.l, self.r = cut(0, b, b, h - 2 * b), cut(w - b, b, b, h - 2 * b)
            self.c = cut(b, b, w - 2 * b, h - 2 * b)

    def _tile(self, surf, piece, rect):
        pw, ph = piece.get_size()
        if pw <= 0 or ph <= 0 or rect.w <= 0 or rect.h <= 0:
            return
        clip = surf.get_clip()
        surf.set_clip(rect.clip(clip) if clip else rect)
        for y in range(rect.y, rect.bottom, ph):
            for x in range(rect.x, rect.right, pw):
                surf.blit(piece, (x, y))
        surf.set_clip(clip)

    def draw(self, surf, rect):
        r = pygame.Rect(rect)
        b = self.b
        if not b:
            surf.blit(self.img, self.img.get_rect(center=r.center))
            return r
        w = max(r.w, 2 * b)
        h = max(r.h, 2 * b)
        r = pygame.Rect(r.x, r.y, w, h)
        cache = self.__dict__.setdefault("_made", {})
        img = cache.get((w, h))
        if img is None:                                # build each size once, then just blit it
            if len(cache) > 96:
                cache.clear()
            img = pygame.Surface((w, h), pygame.SRCALPHA)
            self._paint(img, pygame.Rect(0, 0, w, h))
            cache[(w, h)] = img
        surf.blit(img, r.topleft)
        return r

    def _paint(self, surf, r):
        b = self.b
        w, h = r.w, r.h
        self._tile(surf, self.c, pygame.Rect(r.x + b, r.y + b, w - 2 * b, h - 2 * b))
        self._tile(surf, self.t, pygame.Rect(r.x + b, r.y, w - 2 * b, b))
        self._tile(surf, self.bt, pygame.Rect(r.x + b, r.bottom - b, w - 2 * b, b))
        self._tile(surf, self.l, pygame.Rect(r.x, r.y + b, b, h - 2 * b))
        self._tile(surf, self.r, pygame.Rect(r.right - b, r.y + b, b, h - 2 * b))
        surf.blit(self.tl, (r.x, r.y))
        surf.blit(self.tr, (r.right - b, r.y))
        surf.blit(self.bl, (r.x, r.bottom - b))
        surf.blit(self.br, (r.right - b, r.bottom - b))


class Theme:
    def __init__(self, name: str = "console", root: _Path | None = None):
        d = (root or UI_DIR) / name
        meta = _json.loads((d / "theme.json").read_text())
        self.c = {k: tuple(v) for k, v in meta["colors"].items()}
        self.parts = {}
        for part, border in meta["borders"].items():
            img = pygame.image.load(str(d / f"{part}.png"))
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            self.parts[part] = NineSlice(img, border)
        self.icons = {}
        for p in ((root or UI_DIR) / "icons").glob("*.png"):
            img = pygame.image.load(str(p))
            img = img.convert_alpha() if pygame.display.get_surface() else img
            self.icons[p.stem] = pygame.transform.scale(img, (img.get_width() * U, img.get_height() * U))

    # ---- widgets -----------------------------------------------------------
    def panel(self, surf, rect):
        return self.parts["panel"].draw(surf, rect)

    def inner(self, rect, pad=None):
        b = self.parts["panel"].b
        return pygame.Rect(rect).inflate(-2 * (pad or b), -2 * (pad or b))

    def text(self, surf, msg, pos, scale=2, color=None, anchor="topleft", outline=False):
        return pixelfont.draw(surf, msg, pos, scale, color or self.c["text"], anchor,
                              outline=(8, 8, 14) if outline else None)

    def button(self, surf, rect, label, selected=False, right=None, right_color=None, icon=None):
        r = self.parts["button_sel" if selected else "button"].draw(surf, rect)
        x = r.x + 9 * U
        if selected:   # glowing lamp, like the device's yellow light
            pygame.draw.rect(surf, self.c["accent"], (r.x + 5 * U, r.centery - 2 * U, 3 * U, 4 * U))
            pygame.draw.rect(surf, (255, 255, 230), (r.x + 5 * U, r.centery - 2 * U, U, U))
            x += 3 * U
        if icon is not None:
            ic = self.icons[icon]
            surf.blit(ic, ic.get_rect(midleft=(x, r.centery)))
            x += ic.get_width() + 3 * U
        self.text(surf, label, (x, r.centery), 2, self.c["accent"] if selected else self.c["text"], "midleft")
        if right:
            self.text(surf, right, (r.right - 9 * U, r.centery), 2, right_color or self.c["accent"], "midright")
        return r

    def gauge(self, surf, rect, frac, liquid, icon=None, label=None):
        """A glass tube filled with coloured liquid (cf. boss_fight/testtube.png)."""
        r = pygame.Rect(rect)
        if icon:
            ic = self.icons[icon]
            surf.blit(ic, ic.get_rect(midleft=(r.x, r.centery)))
            r = pygame.Rect(r.x + ic.get_width() + 2 * U, r.y, r.w - ic.get_width() - 2 * U, r.h)
        self.parts["tube"].draw(surf, r)        # glass first, liquid inside it
        inner = pygame.Rect(r.x + 5 * U, r.y + 3 * U, r.w - 10 * U, r.h - 6 * U)
        fw = int(inner.w * max(0.0, min(1.0, frac))) // U * U
        if fw > 0:
            dark = tuple(int(c * 0.6) for c in liquid)
            light = tuple(min(255, c + 70) for c in liquid)
            surf.fill(dark, (inner.x, inner.y, fw, inner.h))
            surf.fill(liquid, (inner.x, inner.y + U, fw, inner.h - 2 * U))
            surf.fill(light, (inner.x, inner.y + U, fw, U))
            surf.fill(light, (inner.x + fw - U, inner.y + U, U, inner.h - 2 * U))   # meniscus
            t = pygame.time.get_ticks() / 1000
            for k in range(3):   # rising bubbles
                bx = inner.x + int((k * 37 + t * 22) % max(1, fw))
                if bx < inner.x + fw - 2 * U:
                    surf.fill(light, (bx // U * U, inner.y + U * (2 + k % 2), U, U))
        surf.fill((235, 245, 255), (inner.x + 2 * U, inner.y, max(0, inner.w - 6 * U), U))   # glass glint
        if label:
            self.text(surf, label, (r.right + 3 * U, r.centery), 2, self.c["dim"], "midleft")
        return r

    def portrait(self, surf, img, center):
        ring = self.parts["porthole"].img
        rr = ring.get_rect(center=center)
        disc = pygame.Surface(rr.size, pygame.SRCALPHA)
        pygame.draw.circle(disc, (*self.c["glass2"], 255), (rr.w // 2, rr.h // 2), rr.w // 2 - 4 * U)
        p = img.copy()
        mask = pygame.Surface(p.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (p.get_width() // 2, p.get_height() // 2 + 6 * U),
                           rr.w // 2 - 5 * U)
        disc.blit(p, p.get_rect(center=(rr.w // 2, rr.h // 2 - 2 * U)))
        surf.blit(disc, rr)
        surf.blit(ring, rr)
        return rr

    def tab(self, surf, rect, label, color=None):
        r = self.parts["tab"].draw(surf, rect)
        self.text(surf, label, r.center, 2, color or (30, 20, 8), "center", outline=False)
        return r

    def key(self, surf, pos, letter):
        cap = self.parts["keycap"].img
        r = cap.get_rect(midleft=pos)
        surf.blit(cap, r)
        pixelfont.draw(surf, letter, (r.centerx, r.centery - U), 2, (240, 240, 250), "center", shadow=None)
        return r

    # ---- compact widgets (v3) -------------------------------------------
    def plate(self, surf, rect, gold=False):
        return self.parts["plate_gold" if gold else "plate"].draw(surf, rect)

    def nameplate(self, surf, rect, label, color=None):
        """Light text on dark glass with a thin gold rim: always readable."""
        r = self.parts["nameplate"].draw(surf, rect)
        self.text(surf, label, (r.centerx, r.centery - U // 2), 2, color or self.c["accent"], "center")
        return r

    def fit(self, label, scale=2, pad=14):
        return pixelfont.width(label, scale) + pad * U

    def prompt(self, surf, center, key, label):
        """[E] Enter the shrine  - a slim plaque that floats over the world."""
        w = self.fit(label) + 18 * U
        r = pygame.Rect(0, 0, w, 22 * U)
        r.center = center
        self.plate(surf, r)
        self.key(surf, (r.x + 5 * U, r.centery), key)
        self.text(surf, label, (r.x + 22 * U, r.centery), 2, self.c["text"], "midleft")
        return r

    def counter(self, surf, pos, icon, value, color=None):
        ic = self.icons[icon]
        surf.blit(ic, ic.get_rect(midleft=pos))
        return self.text(surf, value, (pos[0] + ic.get_width() + 3 * U, pos[1]), 2, color or self.c["text"],
                         "midleft")

    def toast(self, surf, topright, icon, label, gold=False):
        """Reward / money message: small plaque with an icon, gold for rewards."""
        w = self.fit(label) + 14 * U
        r = pygame.Rect(0, 0, w, 20 * U)
        r.topright = topright
        self.plate(surf, r, gold)
        self.counter(surf, (r.x + 6 * U, r.centery), icon, label, self.c["accent"] if gold else self.c["text"])
        return r

    def chip(self, surf, rect, label, color=None):
        r = self.parts["chip"].draw(surf, rect)
        self.text(surf, label, r.center, 2, color or (20, 14, 6), "center")
        return r

    def iconbtn(self, surf, rect, icon, selected=False):
        r = self.parts["iconbtn_sel" if selected else "iconbtn"].draw(surf, rect)
        ic = pygame.transform.scale(self.icons[icon], (self.icons[icon].get_width() * 3 // 2,
                                                       self.icons[icon].get_height() * 3 // 2))
        surf.blit(ic, ic.get_rect(center=r.center))
        return r

    def pips(self, surf, pos, have, total, color=None):
        x, y = pos
        for i in range(total):
            on = i < have
            pygame.draw.rect(surf, (8, 10, 14), (x - U, y - U, 5 * U, 5 * U))
            pygame.draw.rect(surf, (color or self.c["accent"]) if on else self.c["glass2"], (x, y, 3 * U, 3 * U))
            if on:
                pygame.draw.rect(surf, (255, 250, 220), (x, y, U, U))
            x += 6 * U
        return x

    def divider(self, surf, x0, x1, y):
        surf.fill(self.c["glass_line"], (x0, y, x1 - x0, U // 2 or 1))

    def lamp(self, surf, center, on=True):
        x, y = center
        col = self.c["accent"] if on else self.c["glass2"]
        pygame.draw.rect(surf, (8, 10, 14), (x - 3 * U, y - 3 * U, 6 * U, 6 * U))
        pygame.draw.rect(surf, col, (x - 2 * U, y - 2 * U, 4 * U, 4 * U))
        if on:
            pygame.draw.rect(surf, (255, 255, 230), (x - 2 * U, y - 2 * U, 2 * U, U))
