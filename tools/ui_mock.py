"""Console-theme mock screens for approval: planet HUD, space HUD, station,
title, and a strip of small messages (prompts, money, rewards).

    python tools/ui_mock.py [out_dir]
"""
from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import pygame  # noqa: E402
import style_sample  # noqa: E402
import ui_kit  # noqa: E402
from pixelkit import hue_ramp, value_noise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
W, H = 1280, 720
WORLD = 2          # world sprites: whole-number scale
U = 2


def load(p):
    return pygame.image.load(str(A / p)).convert_alpha()


def crop(img):
    return img.subsurface(img.get_bounding_rect()).copy()


def sc(img, k):
    img = crop(img)
    return pygame.transform.scale(img, (round(img.get_width() * k), round(img.get_height() * k)))


# ---------------------------------------------------------------- backgrounds
def pixel_sky(seed=3, low=(320, 180)):
    """Space backdrop painted at 320x180 and scaled x4: stepped nebula bands,
    ordered dithering between steps, pixel stars. Same grain as the sprites."""
    w, h = low
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    n = value_noise(w, h, 40, seed) + 0.5 * value_noise(w, h, 17, seed + 1) + 0.25 * value_noise(w, h, 7, seed + 2)
    band = np.exp(-((yy - h * 0.42 - (xx - w * 0.5) * 0.28) / (h * 0.30)) ** 2)
    v = np.clip((n * 0.5 + 0.5) * band, 0, 1)
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    steps = np.floor(v * 5 + bayer[(yy % 4).astype(int), (xx % 4).astype(int)] * 0.9).clip(0, 4).astype(int)
    pal = np.array([(5, 7, 20), (16, 14, 44), (38, 22, 70), (72, 34, 96), (120, 60, 120)], float)
    teal = np.array([(5, 7, 20), (8, 22, 42), (12, 40, 64), (20, 70, 92), (40, 110, 120)], float)
    mix_ = (value_noise(w, h, 60, seed + 4) > 0.1)[..., None]
    img = np.where(mix_, teal[steps], pal[steps])
    surf = pygame.surfarray.make_surface(img.astype(np.uint8).transpose(1, 0, 2))
    for _ in range(220):
        x, y = rng.integers(0, w), rng.integers(0, h)
        b = rng.choice([(150, 160, 210), (210, 220, 255), (255, 236, 190)])
        surf.set_at((int(x), int(y)), tuple(int(c) for c in b))
    for _ in range(10):
        x, y = int(rng.integers(2, w - 2)), int(rng.integers(2, h - 2))
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            surf.set_at((x + dx, y + dy), (255, 250, 230) if (dx, dy) == (0, 0) else (150, 170, 230))
    return pygame.transform.scale(surf, (w * 4, h * 4))


def planet_world(new):
    s = pygame.Surface((W, H))
    top, bot = (92, 128, 70), (200, 222, 140)
    for y in range(0, H, 4):
        k = min(1.0, (y // 32) * 32 / (H * 0.72))
        s.fill(tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)), (0, y, W, 4))
    for r_, c_ in ((36, (232, 244, 196)), (28, (246, 255, 220)), (20, (255, 255, 242))):
        for yy in range(-r_, r_ + 1, 4):
            hw = int((r_ * r_ - yy * yy) ** 0.5) // 4 * 4
            s.fill(c_, (960 - hw, 130 + yy, hw * 2, 4))
    ground = 520
    bd = sc(new["backdrop"], 3)
    for x in range(-140, W + bd.get_width(), bd.get_width()):   # bottom edge tucked behind the grass
        s.blit(bd, (x, ground + 24 - bd.get_height()))
    ug = pygame.transform.scale(new["underground"], (160 * WORLD, 120 * WORLD))
    for x in range(0, W, ug.get_width()):
        for y in range(ground + 12, H, ug.get_height()):
            s.blit(ug, (x, y))
    fr = sc(new["fringe"], WORLD)
    for x in range(0, W + fr.get_width(), fr.get_width()):
        s.blit(fr, (x, ground - 6))
    feet = ground + 14

    def place(img, x):
        im = sc(img, WORLD)
        s.blit(im, im.get_rect(midbottom=(x, feet)))
    place(new["giant_fungus"], 110)
    place(new["bush"], 290)
    place(new["mushroom"], 380)
    place(load("player/mainCharStill.png"), 560)
    place(new["crawler"], 700)
    place(new["crystals"], 810)
    place(new["basalt_rock"], 900)
    place(new["shrine"], 1120)
    return s


def space_world(new, sky):
    s = sky.copy()
    s.blit(sc(new["planet"], 6), (680, 120))
    rk = sc(load("rocket/rocket.png"), WORLD)
    s.blit(pygame.transform.rotate(rk, 35), (430, 290))
    return s


# ---------------------------------------------------------------- HUD pieces
def vitals(th, s, pos=(12, 12)):
    x, y = pos
    pr = th.panel(s, (x, y, 380, 108))
    th.portrait(s, sc(load("player/mainCharStill.png"), 0.8), (pr.x + 52, pr.centery))
    th.gauge(s, (pr.x + 100, pr.y + 22, 260, 28), 0.78, (214, 64, 56), icon="hull")
    th.gauge(s, (pr.x + 100, pr.y + 58, 260, 28), 0.5, (60, 170, 232), icon="fuel")
    w = th.plate(s, (pr.x + 96, pr.bottom - 4, 270, 40))      # wallet tucked under the panel
    th.counter(s, (w.x + 14, w.centery), "coin", "1,240", th.c["accent"])
    th.counter(s, (w.x + 140, w.centery), "ore", "18")
    return pr


def screen_planet(th, new):
    s = planet_world(new)
    c = th.c
    vitals(th, s)
    th.nameplate(s, (W - 312, 14, 298, 40), "Daceae II · Toxic")
    th.text(s, "▶ Find the shrine's three seals  1/3", (W - 16, 66), 2, c["accent"], "topright", outline=True)
    th.toast(s, (W - 14, 98), "coin", "+120 cr", gold=True)
    th.toast(s, (W - 14, 142), "ore", "+3 ore")
    th.text(s, "← Rocket  12m", (16, 420), 2, (170, 255, 190), outline=True)
    th.text(s, "Shrine  40m →", (W - 16, 420), 2, c["accent"], "topright", outline=True)
    th.prompt(s, (1120, 330), "E", "Enter the shrine")
    d = th.panel(s, (180, H - 140, 820, 124))
    th.portrait(s, sc(new["vey"], 2), (d.x + 10, d.y + 10))
    th.nameplate(s, (d.x + 70, d.y - 20, 226, 40), "Commander Vey")
    th.text(s, "The shrine's door answers to three seals. The spores", (d.x + 70, d.y + 36), 2, c["text"])
    th.text(s, "hide them - look under the giant fungi, Voyager.", (d.x + 70, d.y + 62), 2, c["text"])
    th.text(s, "▼", (d.right - 30, d.bottom - 32), 2, c["accent"])
    return s


def screen_space(th, new, sky):
    s = space_world(new, sky)
    c = th.c
    p = th.panel(s, (12, H - 172, 360, 160))
    th.gauge(s, (p.x + 22, p.y + 22, 316, 30), 0.82, (214, 64, 56), icon="hull")
    th.gauge(s, (p.x + 22, p.y + 62, 316, 30), 0.6, (90, 150, 255), icon="shield")
    th.gauge(s, (p.x + 22, p.y + 102, 316, 30), 0.35, (246, 170, 50), icon="fuel")
    ring = th.parts["porthole"].img
    big = pygame.transform.scale(ring, (ring.get_width() * 2, ring.get_height() * 2))
    rc = big.get_rect(bottomright=(W - 14, H - 14))
    pygame.draw.circle(s, c["glass"], rc.center, rc.w // 2 - 14)
    for dx, dy, col in ((20, -30, (120, 200, 255)), (-40, 10, (255, 120, 90)), (35, 30, (255, 214, 90))):
        s.fill(col, (rc.centerx + dx, rc.centery + dy, 6, 6))
    s.fill((240, 240, 250), (rc.centerx - 2, rc.centery - 2, 4, 4))
    s.blit(big, rc)
    th.nameplate(s, (14, 14, 318, 40), "Ch.4 · The Three Keys")
    th.text(s, "Recover the Ancient Keys  1/3", (18, 64), 2, c["text"], outline=True)
    th.nameplate(s, (W - 312, 14, 298, 40), "Haven System")
    th.text(s, "speed 214", (W - 16, 64), 2, c["dim"], "topright", outline=True)
    th.prompt(s, (W // 2, H - 150), "L", "Land on Daceae II")
    return s


# ---------------------------------------------------------------- station v2
def screen_station(th, new, sky):
    """List + detail layout: tabs as icon buttons on the left, items in the middle,
    a detail card on the right; only one frame, everything else lives on the glass."""
    s = space_world(new, sky)
    veil = pygame.Surface((W, H), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 160))
    s.blit(veil, (0, 0))
    c = th.c
    f = th.panel(s, (60, 46, 1160, 628))
    g = th.inner(f, 18 * U)
    # header
    th.iconbtn(s, (g.x, g.y, 64, 64), "star", True)
    th.text(s, "HAVEN STATION", (g.x + 80, g.y + 4), 4, c["accent"])
    th.text(s, "Haven Coalition  ·  Friendly", (g.x + 82, g.y + 44), 2, c["dim"])
    wal = th.plate(s, (g.right - 230, g.y + 6, 230, 46))
    th.counter(s, (wal.x + 16, wal.centery), "coin", "1,240", c["accent"])
    th.counter(s, (wal.x + 130, wal.centery), "ore", "18")
    th.divider(s, g.x, g.right, g.y + 78)
    # tabs
    tabs = [("wrench", "Services"), ("engine", "Upgrades"), ("ship", "Hangar"), ("scroll", "Contracts")]
    for i, (ic, label) in enumerate(tabs):
        y = g.y + 96 + i * 112
        th.iconbtn(s, (g.x, y, 68, 68), ic, i == 1)
        th.text(s, label, (g.x + 34, y + 74), 2, c["accent"] if i == 1 else c["dim"], "midtop")
    # item list
    lx, lw = g.x + 112, 560
    th.text(s, "UPGRADES", (lx, g.y + 96), 2, c["dim"])
    items = [("engine", "Ion Engine", 2, "640"), ("fuel", "Fuel Tank", 1, "320"), ("hull", "Hull Plating", 3, "900"),
             ("shield", "Shield Emitter", 0, "140"), ("blaster", "Pulse Blaster", 2, "560"),
             ("scanner", "Deep Scanner", 5, ""), ("suit", "Exo Suit", 1, "320")]
    for i, (ic, name, lvl, price) in enumerate(items):
        y = g.y + 124 + i * 58
        row = pygame.Rect(lx, y, lw, 52)
        if i == 0:
            th.plate(s, row, gold=True)
            th.lamp(s, (row.x + 16, row.centery))
        th.counter(s, (row.x + 34, row.centery), ic, name, c["accent"] if i == 0 else c["text"])
        th.pips(s, (row.x + 270, row.centery - 3), lvl, 5, (120, 230, 255))
        if price:
            th.counter(s, (row.right - 130, row.centery), "coin", f"{price} cr",
                       c["accent"] if int(price) <= 1240 else c["bad"])
        else:
            th.text(s, "MAX", (row.right - 24, row.centery), 2, c["good"], "midright")
        if i:
            th.divider(s, row.x + 10, row.right - 10, y - 4)
    # detail card
    dx = lx + lw + 30
    card = pygame.Rect(dx, g.y + 96, g.right - dx, 420)
    th.plate(s, card)
    icon = pygame.transform.scale(th.icons["engine"], (56, 56))
    s.blit(icon, icon.get_rect(midtop=(card.centerx, card.y + 24)))
    th.text(s, "Ion Engine", (card.centerx, card.y + 100), 3, c["accent"], "midtop")
    th.pips(s, (card.centerx - 28, card.y + 140), 2, 5, (120, 230, 255))
    th.text(s, "Level 2 of 5", (card.centerx, card.y + 160), 2, c["dim"], "midtop")
    for j, line in enumerate(["More thrust: reach planets", "faster and escape gravity", "wells with fuel to spare."]):
        th.text(s, line, (card.x + 24, card.y + 204 + j * 26), 2, c["text"])
    th.text(s, "Thrust", (card.x + 24, card.y + 300), 2, c["dim"])
    th.text(s, "230 → 271", (card.right - 24, card.y + 300), 2, c["good"], "topright")
    buy = th.prompt(s, (card.centerx, card.bottom - 40), "E", "Buy  640 cr")
    del buy
    # footer hints
    fx = g.x
    for key, label in (("←", "Tabs"), ("↑", "Select"), ("E", "Buy"), ("X", "Sell"), ("Q", "Undock")):
        r = th.key(s, (fx, g.bottom - 14), key)
        t = th.text(s, label, (r.right + 8, g.bottom - 14), 2, c["dim"], "midleft")
        fx = t.right + 26
    return s


# ---------------------------------------------------------------- title v2
def logo(text, scale=10):
    from stellar_forge.ui import pixelfont
    base = pixelfont.render(text, (255, 255, 255), scale, None, None)
    w, h = base.get_size()
    out = pygame.Surface((w + 4 * scale, h + 6 * scale), pygame.SRCALPHA)
    dark = pixelfont.render(text, (40, 16, 10), scale, None, None)
    for dx in (-1, 0, 1):          # chunky dark outline
        for dy in (-1, 0, 1):
            out.blit(dark, (2 * scale + dx * scale, 2 * scale + dy * scale))
    for d in range(1, 3):          # extruded depth
        out.blit(pixelfont.render(text, (120, 46, 20), scale, None, None), (2 * scale, 2 * scale + d * scale))
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    bands = [(255, 240, 180), (255, 206, 96), (240, 150, 52)]
    rows = 8
    for i in range(rows):          # flat bands, one per glyph row
        grad.fill(bands[min(len(bands) - 1, int(i * len(bands) / rows))], (0, i * scale, w, scale))
    grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(grad, (2 * scale, 2 * scale))
    return out


def screen_title(th, new, sky):
    s = sky.copy()
    c = th.c
    big_planet = sc(style_sample.pixel_planet(150, seed=11).surface(), 4)   # same x4 grain as the sky
    s.blit(big_planet, (W - 470, H - 300))
    moon = sc(style_sample.pixel_planet(26, seed=4).surface(), 4)
    s.blit(moon, (W - 200, 120))
    rk = sc(load("rocket/centreflame.png"), WORLD)
    s.blit(pygame.transform.rotate(rk, -28), (W - 420, 250))
    lg = logo("STELLAR FORGE", 9)
    s.blit(lg, lg.get_rect(midtop=(W // 2, 46)))
    th.text(s, "·  THE  LAST  VOYAGER  ·", (W // 2, 196), 3, (130, 220, 255), "midtop", outline=True)
    items = [("play", "Continue"), ("plus", "New Game"), ("folder", "Load Game"), ("book", "Logbook"),
             ("gear", "Settings"), ("star", "Credits"), ("door", "Quit")]
    y0 = 272
    for i, (ic, label) in enumerate(items):
        y = y0 + i * 58
        sel = i == 0
        if sel:
            th.plate(s, (88, y - 4, 330, 50), gold=True)
            th.lamp(s, (108, y + 21))
        icon = th.icons[ic]
        s.blit(icon, icon.get_rect(midleft=(128, y + 21)))
        th.text(s, label, (166, y + 21), 3, c["accent"] if sel else c["text"], "midleft", outline=True)
    card = th.plate(s, (436, y0 - 6, 380, 96))        # describes the selected "Continue"
    th.text(s, "Ch.4 · The Three Keys", (card.x + 20, card.y + 18), 2, c["accent"])
    th.counter(s, (card.x + 20, card.y + 54), "key", "1/3")
    th.counter(s, (card.x + 106, card.y + 54), "coin", "1,240")
    th.text(s, "2h 14m", (card.right - 20, card.y + 54), 2, c["dim"], "midright")
    th.text(s, "v3.0", (W - 16, H - 16), 2, (110, 120, 150), "bottomright", outline=True)
    return s


def screen_messages(th, new):
    """Every small widget on one strip, at real size, over the world."""
    s = planet_world(new)
    th.prompt(s, (220, 120), "E", "Enter the shrine")
    th.prompt(s, (220, 180), "E", "Mine ore")
    th.prompt(s, (220, 240), "L", "Land on Daceae II")
    th.toast(s, (W - 20, 90), "coin", "+120 cr", gold=True)
    th.toast(s, (W - 20, 134), "ore", "+3 ore")
    th.toast(s, (W - 20, 178), "key", "Sun Key recovered!", gold=True)
    th.toast(s, (W - 20, 222), "fuel", "+45 fuel")
    th.nameplate(s, (520, 100, 260, 40), "Commander Vey")
    th.nameplate(s, (520, 160, 298, 40), "Daceae II · Toxic")
    w = th.plate(s, (520, 220, 270, 40))
    th.counter(s, (w.x + 14, w.centery), "coin", "1,240", th.c["accent"])
    th.counter(s, (w.x + 140, w.centery), "ore", "18")
    for i, ic in enumerate(sorted(th.icons)):
        th.iconbtn(s, (40 + i * 56, 300, 48, 48), ic, i == 0)
    return s


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "style"
    out.mkdir(parents=True, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))
    new = style_sample.build()
    ui_kit.build()
    from stellar_forge.ui.pixelui import Theme
    th = Theme("console")
    sky = pixel_sky()
    for old in out.glob("ui_*.png"):
        old.unlink()
    shots = {"planet": screen_planet(th, new), "space": screen_space(th, new, sky),
             "station": screen_station(th, new, sky), "title": screen_title(th, new, sky),
             "messages": screen_messages(th, new)}
    for name, img in shots.items():
        pygame.image.save(img, str(out / f"ui_{name}.png"))
    print("written to", out, list(shots))
    return math, random, hue_ramp   # keep tools imported for experiments


if __name__ == "__main__":
    main()
