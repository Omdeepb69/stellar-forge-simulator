"""In-game HUD in the Console style (see docs/style/ui_planet.png):

* vitals: riveted panel, porthole portrait, liquid gauge tubes
* wallet: slim plate tucked under the vitals
* keys/shards: sockets in a plate, top-right
* objective: chapter nameplate + outlined text
* compass arrows, key-cap prompts, boss bar
"""
from __future__ import annotations

import functools
import math
import re

import pygame
from pygame.math import Vector2

from .. import config
from ..core.game_state import RELIC_BIOMES, RELIC_NAMES, SHARD_BIOMES
from . import pixelfont
from .text import text, theme

U = 2
RELIC_SPRITES = {"desert": "stronghold/desert_st/desertItem.png",
                 "ice": "stronghold/icy_st/snowyItem.png",
                 "forest": "stronghold/forest_st/forestItem.png"}
LIQUID = {"hull": (214, 64, 56), "shield": (90, 150, 255), "fuel": (246, 170, 50), "pilot": (214, 64, 56),
          "jet": (60, 170, 232)}


def icon(game, name: str, size: int = 28):
    th = theme()
    ic = th.icons.get(name) or th.icons.get({"credits": "coin", "kill": "kill", "planet": "planet"}.get(name, ""))
    if ic is None:
        return game.assets.image(f"generated/ui/icons/{name}.png", size=(size, size))
    if ic.get_width() != size:
        ic = pygame.transform.scale(ic, (size, size))
    return ic


# ---------------------------------------------------------------- screen layout
# One layout for every scene, so nothing lands on anything else (1280x720):
#   top-left column   vitals (wallet inside) + one objective card
#   top-right column  key sockets, location, an info line, then notifications
#   top centre        the planet strip map, then the banner
#   edges             compass arrows, kept clear of the HUD columns
#   bottom            prompt, warnings above it, dialogue box
M = 12
LEFT_W = 352
RIGHT_W = 296
CENTER_X0 = M + LEFT_W + 16
CENTER_X1 = config.SCREEN_W - M - RIGHT_W - 16
PROMPT_Y = config.SCREEN_H - 150
SAFE = pygame.Rect(54, 176, config.SCREEN_W - 108, config.SCREEN_H - 176 - 200)   # where edge arrows may go
LAYOUT = {"left_bottom": 150, "right_bottom": 120, "center_top": 70}
_LABELS: list = []          # edge-arrow labels drawn this frame (so they never stack)


def begin_frame() -> None:
    _LABELS.clear()
    LAYOUT["center_top"] = 70
    LAYOUT["right_bottom"] = 120


@functools.lru_cache(maxsize=4096)
def fit(msg: str, width: int, scale: int = 2) -> str:
    """Shorten ``msg`` with an ellipsis so it fits ``width`` pixels (cached: called every frame)."""
    if pixelfont.width(msg, scale) <= width:
        return msg
    lo, hi = 0, len(msg)                     # longest prefix that fits, by bisection
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if pixelfont.width(msg[:mid] + "...", scale) <= width:
            lo = mid
        else:
            hi = mid - 1
    return msg[:lo].rstrip(" ·-,") + "..."


def _vitals(surf, game, portrait, gauges, on_foot: bool = False) -> pygame.Rect:
    """Riveted panel: porthole portrait, gauge tubes, and the wallet as its bottom row."""
    begin_frame()
    th = theme()
    gh, gap = 24, 30
    h = 16 + len(gauges) * gap + 36
    p = th.panel(surf, (M, M, LEFT_W, h))
    th.portrait(surf, portrait, (p.x + 50, p.y + 12 + len(gauges) * gap // 2))
    for i, (frac, color, ic) in enumerate(gauges):
        th.gauge(surf, (p.x + 100, p.y + 12 + i * gap, LEFT_W - 116, gh), frac, color, icon=ic)
    _wallet_row(surf, game, p.x + 100, p.y + 12 + len(gauges) * gap + 14, p.right - 12, on_foot=on_foot)
    LAYOUT["left_bottom"] = p.bottom
    return p


def _wallet_row(surf, game, x, y, right, on_foot: bool = False) -> None:
    st = game.state
    th = theme()
    items = [("coin", f"{st.credits:,}", th.c["accent"]), ("ore", f"{st.ore}", th.c["text"])]
    if on_foot:
        items.append(("medkit", f"{st.medkits}", (120, 255, 160) if st.medkits else (160, 110, 110)))
    if getattr(st, "corps_merit", 0) or getattr(st, "corps_merit_total", 0):
        items.append(("scanner", f"{st.corps_merit}", (255, 190, 90)))
    for ic, val, col in items:
        r = th.counter(surf, (x, y), ic, val, col)
        x = r.right + 16
        if x > right:
            break


def ship_status(surf, game, clock: float) -> None:
    st = game.state
    low = int(clock * 4) % 2
    hull = LIQUID["hull"] if not (st.hull < st.max_hull * 0.3 and low) else (255, 150, 120)
    fuel = LIQUID["fuel"] if not (st.fuel < st.max_fuel * 0.2 and low) else (255, 230, 120)
    _vitals(surf, game, game.assets.image("rocket/rocket.png", crop=True, size=(40, 58)),
            [(st.hull / st.max_hull, hull, "hull"), (st.shield / max(1, st.max_shield), LIQUID["shield"], "shield"),
             (st.fuel / st.max_fuel, fuel, "fuel")])


def pilot_status(surf, game, jet_frac: float) -> None:
    st = game.state
    _vitals(surf, game, game.assets.image("player/mainCharStill.png", size=(56, 56)),
            [(st.pilot_hp / st.max_pilot_hp, LIQUID["pilot"], "hull"), (jet_frac, LIQUID["jet"], "fuel")],
            on_foot=True)


def wallet(surf, game, pos) -> None:
    th = theme()
    w = th.plate(surf, (pos[0], pos[1], 300, 40))
    _wallet_row(surf, game, w.x + 14, w.centery, w.right - 10)


def resources(surf, game, x, y, items=("credits", "ore", "data")) -> None:
    st = game.state
    th = theme()
    values = {"credits": f"{st.credits:,}", "ore": st.ore, "data": st.scan_data, "kill": st.kills}
    names = {"credits": "coin"}
    for name in items:
        r = th.counter(surf, (x, y + 10), names.get(name, name), values[name],
                       th.c["accent"] if name == "credits" else th.c["text"])
        x = r.right + 18


def boss_bar(surf, name: str, frac: float, enraged: bool = False) -> None:
    th = theme()
    w = CENTER_X1 - CENTER_X0
    x = CENTER_X0
    y = LAYOUT["center_top"]
    th.nameplate(surf, (x + w // 2 - 150, y, 300, 36), fit(name.upper() + (" !" if enraged else ""), 270),
                 (255, 150, 120) if enraged else th.c["accent"])
    th.gauge(surf, (x, y + 40, w, 26), frac, (230, 60, 50) if not enraged else (255, 130, 40))
    LAYOUT["center_top"] = y + 74


def relic_slots(surf, game) -> None:
    """Key (and, in Act II, Shard) sockets in a slim plate at the top of the right column."""
    st = game.state
    th = theme()
    w = 20 + 3 * 40 + (5 * 32 + 12 if st.boss_defeated else 0)
    r = th.plate(surf, (config.SCREEN_W - M - w, M, w, 48))
    x = r.x + 10
    for b in RELIC_BIOMES:
        img = th.icons.get(f"key_{b}") or th.icons["key"]
        if b not in st.relics:     # an empty socket: a dim silhouette
            img = img.copy()
            img.fill((40, 40, 52, 150), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(img, img.get_rect(center=(x + 20, r.centery)))
        x += 40
    if st.boss_defeated:
        x += 6
        for b in SHARD_BIOMES:
            img = game.assets.sprite(f"generated/items/shard_{b}.png", mult=0.5)
            if b not in st.shards:
                img = img.copy()
                img.fill((40, 40, 50, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(img, img.get_rect(center=(x + 15, r.centery)))
            x += 32
    LAYOUT["right_bottom"] = r.bottom


def location(surf, label: str, info: str | None = None) -> pygame.Rect:
    """Where you are: a nameplate in the right column, an optional small info line under it."""
    th = theme()
    label = fit(label, RIGHT_W - 40)
    w = min(RIGHT_W, max(200, th.fit(label) + 16))
    y = LAYOUT["right_bottom"] + 8
    r = th.nameplate(surf, (config.SCREEN_W - M - w, y, w, 36), label)
    bottom = r.bottom
    if info:
        t = text(surf, fit(info, RIGHT_W), (config.SCREEN_W - M - 4, r.bottom + 6), 13, th.c["dim"],
                 anchor="topright", outline=True)
        bottom = t.bottom
    LAYOUT["right_bottom"] = bottom
    return r


def objective(surf, game) -> None:
    """One card under the vitals: chapter, objective (2 lines max), then one line per side job."""
    q = game.quests
    th = theme()
    st = game.state
    x, w = M, LEFT_W
    inner = w - 24
    rows = [(fit(q.chapter["title"], inner), th.c["accent"], False)]          # (text, colour, bullet)
    for i, ln in enumerate(pixelfont.wrap(q.objective_text(), inner - 18, 2)[:2]):
        rows.append((ln, th.c["text"], i == 0))
    c = st.contract
    extra = []
    if c:
        extra.append((f"Contract: {c['desc']} {c['have']}/{c['need']}", (170, 190, 230)))
    from ..systems.poi import objective_line
    sl = objective_line(game)
    if sl:
        extra.append((sl, (120, 230, 200)))
    sp = getattr(game, "_space_scene", None)
    saga_line = sp.saga.objective_line() if sp is not None and hasattr(sp, "saga") else None
    if saga_line:
        extra.append((saga_line, (255, 220, 150)))
    from ..systems.corps_career import objective_line as corps_line
    cl = corps_line(game)
    if cl:
        extra.append((cl, (255, 190, 90)))
    rows += [(fit(msg, inner - 18), col, True) for msg, col in extra]
    y = LAYOUT["left_bottom"] + 8
    h = 12 + len(rows) * 21
    card = pygame.Surface((w, h), pygame.SRCALPHA)
    card.fill((6, 10, 22, 150))
    card.fill((255, 255, 255, 18), (0, 0, w, 2))
    surf.blit(card, (x, y))
    yy = y + 7
    for k, (msg, col, bullet) in enumerate(rows):
        if bullet:
            surf.fill(col, (x + 12, yy + 5, 6, 6))
        text(surf, msg, (x + (12 if k == 0 else 26), yy), 16, col, outline=True)
        yy += 21
    LAYOUT["left_bottom"] = y + h


def edge_arrow(surf, screen_pos, color, label: str, dist: float | None = None) -> None:
    """Pixel arrow pointing at an off-screen target, kept inside the safe area (clear of the HUD
    columns and the bottom bar). Labels never stack on each other."""
    cx, cy = SAFE.center
    dx, dy = screen_pos[0] - cx, screen_pos[1] - cy
    lbl = (fit(label, 230) + (f"  {dist / 100:.0f} km" if dist else "")) if label else ""
    if SAFE.collidepoint(screen_pos):
        x, y = int(screen_pos[0]) // 2 * 2, int(screen_pos[1]) // 2 * 2
        for k in (-1, 1):   # pixel corner brackets around the target
            for j in (-1, 1):
                surf.fill(color, (x + k * 22 - (0 if k > 0 else 8), y + j * 22 - (0 if j > 0 else 2), 10, 2))
                surf.fill(color, (x + k * 22 - (0 if k > 0 else 2), y + j * 22 - (0 if j > 0 else 8), 2, 10))
        if lbl:
            _label(surf, lbl, (x, y - 40), color)
        return
    ang = math.atan2(dy, dx)
    scale = min((SAFE.w / 2) / max(abs(dx), 1e-3), (SAFE.h / 2) / max(abs(dy), 1e-3))
    p = Vector2(cx + dx * scale, cy + dy * scale)
    # never under the HUD columns: slide down below them along the screen edge
    if p.x < M + LEFT_W + 20 and p.y < LAYOUT["left_bottom"] + 24:
        p.y = LAYOUT["left_bottom"] + 24
    if p.x > CENTER_X1 and p.y < LAYOUT["right_bottom"] + 3 * 44 + 24:
        p.y = LAYOUT["right_bottom"] + 3 * 44 + 24
    tip = Vector2(math.cos(ang), math.sin(ang))
    side = Vector2(-tip.y, tip.x)
    pts = [p + tip * 16, p - tip * 8 + side * 11, p - tip * 8 - side * 11]
    pygame.draw.polygon(surf, (8, 8, 14), [q + tip * 2 for q in pts])
    pygame.draw.polygon(surf, color, pts)
    if lbl:
        w = pixelfont.width(lbl, 2) + 12
        if p.x <= SAFE.left + 1:                       # on a side edge: label beside the arrow, inward
            _label(surf, lbl, (p.x + 22 + w / 2, p.y), color)
        elif p.x >= SAFE.right - 1:
            _label(surf, lbl, (p.x - 22 - w / 2, p.y), color)
        else:                                          # top / bottom edge: label above or below
            _label(surf, lbl, (p.x, p.y + (30 if tip.y < 0 else -30)), color)


def _label(surf, msg, center, color) -> None:
    """A small label on a dark tab; nudged down until it doesn't overlap another one."""
    w = pixelfont.width(msg, 2) + 12
    r = pygame.Rect(0, 0, w, 22)
    r.center = (int(center[0]), int(center[1]))
    r.clamp_ip(pygame.Rect(M, M, config.SCREEN_W - 2 * M, config.SCREEN_H - 2 * M))
    left_col = pygame.Rect(0, 0, M + LEFT_W + 8, LAYOUT["left_bottom"] + 6)
    right_col = pygame.Rect(CENTER_X1 + 8, 0, config.SCREEN_W, LAYOUT["right_bottom"] + 3 * 44 + 6)
    if r.colliderect(left_col):                       # step out of the HUD columns
        r.left = left_col.right
    if r.colliderect(right_col):
        r.right = right_col.left
    for _ in range(8):
        hit = next((o for o in _LABELS if o.colliderect(r)), None)
        if hit is None:
            break
        r.top = hit.bottom + 2
    _LABELS.append(r)
    tab = pygame.Surface(r.size, pygame.SRCALPHA)
    tab.fill((6, 10, 22, 170))
    surf.blit(tab, r)
    text(surf, msg, r.center, 13, color, anchor="center")


_KEY = re.compile(r"^\[([^\]]+)\]\s*(.*)$")


def prompt(surf, msg: str, color=(255, 240, 150), y=None) -> None:
    """``"[E] Enter the shrine"`` -> key cap + label on a slim plaque."""
    th = theme()
    y = y or PROMPT_Y
    msg = fit(msg, 760)
    m = _KEY.match(msg)
    if m:
        th.prompt(surf, (config.SCREEN_W // 2, y), m.group(1)[:5], m.group(2))
    else:
        w = pixelfont.width(msg, 2) + 40
        r = th.plate(surf, ((config.SCREEN_W - w) // 2, y - 22, w, 44))
        text(surf, msg, r.center, 16, color, anchor="center")


def warning(surf, msg: str, clock: float, slot: int = 0) -> None:
    """Blinking warnings sit just above the prompt line, out of the way of the top HUD."""
    if int(clock * 3) % 2 == 0:
        text(surf, msg, (config.SCREEN_W // 2, PROMPT_Y - 52 - slot * 30), 22, config.UI_DANGER, anchor="center",
             outline=True)


def relic_name(b: str) -> str:
    return RELIC_NAMES.get(b, b)


_DIM: dict = {}


MARK_NAMES = {"rocket": "Rocket", "cave": "Cave", "skull": "Lair", "key": "Stronghold", "camp": "Camp",
              "pod": "Pod", "ruin": "Ruin", "vault": "Vault", "folder": "Crate", "star": "Sigil", "unknown": "Unexplored"}


def strip_map(surf, marks, px: float, lo: float, hi: float, title: str | None = None) -> pygame.Rect:
    """A slim map plaque across the top: places along the planet line, you as a marker.
    ``marks`` is [(world_x, icon, done)]; places off the strip get an edge chevron."""
    th = theme()
    c = th.c
    r = pygame.Rect(CENTER_X0, M, CENTER_X1 - CENTER_X0, 44)   # the top-centre band, between the columns
    th.plate(surf, r)
    inner = pygame.Rect(r.x + 30, r.y, r.w - 60, r.h)
    y = r.centery + 2
    surf.fill(c["dim"], (inner.x, y, inner.w, 2))
    span = max(1.0, hi - lo)

    def sx(x):
        return int(inner.x + (x - lo) / span * inner.w) // 2 * 2
    nearest = {}                      # side -> (distance, icon) of the closest unfinished off-strip place
    for x, icon, done in marks:
        if x is not None and not done and (x < lo or x > hi):
            side = -1 if x < lo else 1
            d = abs(x - px)
            if side not in nearest or d < nearest[side][0]:
                nearest[side] = (d, icon)
    for side, (d, icon) in nearest.items():
        name = MARK_NAMES.get(icon, "Material" if icon.startswith("mat_") else icon.title())
        msg = fit(f"< {name} {d / 100:.0f} m" if side < 0 else f"{name} {d / 100:.0f} m >", r.w // 2 - 50)
        text(surf, msg, (r.x + 4 if side < 0 else r.right - 4, r.bottom + 2), 13, c["accent"],
             anchor="topleft" if side < 0 else "topright", outline=True)
    for x, icon, done in sorted(marks, key=lambda m: m[2], reverse=True):
        if x is None:
            continue
        if x < lo or x > hi:
            ex = inner.x - 14 if x < lo else inner.right + 6
            col = c["dim"] if done else c["accent"]
            for k in range(4):        # a little pixel chevron
                d = k if x > hi else 3 - k
                surf.fill(col, (ex + d * 2, y - 6 + k * 2, 2, 2))
                surf.fill(col, (ex + d * 2, y + 6 - k * 2, 2, 2))
            continue
        ic = th.icons.get(icon) or th.icons.get("unknown")
        if ic is None:
            continue
        if done:
            key = icon
            dim = _DIM.get(key)
            if dim is None:
                dim = _DIM[key] = ic.copy()
                dim.fill((90, 90, 110, 200), special_flags=pygame.BLEND_RGBA_MULT)
            ic = dim
        surf.blit(ic, ic.get_rect(center=(sx(x), y - 2)))
    m = sx(px)
    surf.fill((240, 248, 255), (m - 1, r.y + 8, 2, r.h - 16))
    for k in range(3):
        surf.fill((240, 248, 255), (m - 1 - k * 2, r.bottom - 10 + k * 2 - 4, 2 + k * 4, 2))
    if title:
        text(surf, title, (r.centerx, r.bottom + 2), 13, c["dim"], anchor="midtop", outline=True)
    LAYOUT["center_top"] = r.bottom + 26
    return r
