"""Global overlays drawn above every scene: dialogue box and toasts."""
from __future__ import annotations

import pygame

from .. import config


PORTRAITS = {
    "pilot": ("player/mainCharStill.png", (110, 220, 255)),
    "vey": ("generated/portraits/vey.png", (255, 210, 120)),
    "warlord": ("finalboss/boss.png", (255, 90, 90)),
    "ai": ("generated/portraits/ai.png", (160, 255, 180)),
    "pirate": ("generated/portraits/pirate.png", (255, 190, 90)),
    "survivor": ("generated/portraits/survivor.png", (140, 255, 200)),
}
_FACES = []


def settler_portrait(game, spk: str):
    """('settler:<look>:<name>') -> (64x64 face crop, name)."""
    _, look, name = spk.split(":", 2)
    if not _FACES:
        import json
        path = game.assets.resolve("generated/poi/npc/faces.json")
        _FACES.extend(json.loads(open(path).read()) if path else [])
    look = int(look)
    full = game.assets.image(f"generated/poi/npc/{look}_idle0.png")
    x, y = _FACES[look] if look < len(_FACES) else (16, 10)
    return pygame.transform.scale(full.subsurface((x, y, 32, 32)), (64, 64)), name


NAMES = {"pilot": "You", "vey": "Commander Vey", "warlord": "The Warlord", "ai": "Ship AI (ORA)",
         "pirate": "Pirate Captain", "survivor": "Stranded Pilot"}


class Dialogue:
    """Non-blocking typewriter dialogue. ENTER advances / skips."""

    def __init__(self, game):
        self.game = game
        self.queue: list[tuple[str, str]] = []
        self.chars = 0.0
        self.timer = 0.0
        self.on_done = []

    @property
    def active(self) -> bool:
        return bool(self.queue)

    def say(self, lines, on_done=None) -> None:
        """lines: list of (speaker, text)."""
        self.queue.extend(lines)
        if on_done:
            self.on_done.append((len(self.queue), on_done))

    def advance(self) -> None:
        if not self.queue:
            return
        _spk, msg = self.queue[0]
        if self.chars < len(msg):
            self.chars = len(msg)
            return
        self._next()

    def _next(self):
        self.queue.pop(0)
        self.chars = 0
        self.timer = 0
        self.game.audio.play("ui", 0.4)
        remaining = []
        for idx, fn in self.on_done:
            idx -= 1
            if idx <= 0:
                fn()
            else:
                remaining.append((idx, fn))
        self.on_done = remaining

    def update(self, dt) -> None:
        if not self.queue:
            return
        _spk, msg = self.queue[0]
        self.chars = min(len(msg), self.chars + dt * 55)
        if self.chars >= len(msg):
            self.timer += dt
            if self.timer > 2.4 + len(msg) * 0.035:
                self._next()

    def draw(self, surf) -> None:
        """The Console dialogue box: panel, porthole portrait over the corner,
        gold nameplate, pixel-font typewriter text and a blinking ▼."""
        if not self.queue:
            return
        from . import pixelfont
        from .text import theme
        th = theme()
        spk, msg = self.queue[0]
        w, h = 820, 128
        rect = pygame.Rect((config.SCREEN_W - w) // 2 + 30, config.SCREEN_H - h - 18, w, h)
        th.panel(surf, rect)
        if spk.startswith("settler:"):           # a frontier settler: their own face and name
            img, name = settler_portrait(self.game, spk)
        else:
            sprite, _color = PORTRAITS.get(spk, PORTRAITS["ai"])
            name = NAMES.get(spk, spk)
            img = self.game.assets.image(sprite, crop=True)
            k = max(1, 64 // max(img.get_width(), img.get_height(), 1)) if max(img.get_size()) < 64 else 0
            img = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k)) if k else \
                pygame.transform.scale(img, (64, int(64 * img.get_height() / max(1, img.get_width()))))
        th.portrait(surf, img, (rect.x + 8, rect.y + 6))
        th.nameplate(surf, (rect.x + 64, rect.y - 20, pixelfont.width(name, 2) + 48, 40), name)
        shown = msg[:int(self.chars)]
        for i, line in enumerate(pixelfont.wrap(shown, w - 120, 2)[:3]):
            pixelfont.draw(surf, line, (rect.x + 66, rect.y + 32 + i * 24), 2, th.c["text"])
        if self.chars >= len(msg) and int(pygame.time.get_ticks() / 400) % 2:
            pixelfont.draw(surf, "▼", (rect.right - 30, rect.bottom - 30), 2, th.c["accent"])


class Toasts:
    def __init__(self, assets=None):
        self.assets = assets
        self.items: list[list] = []  # [text, color, time, icon]

    MAX_SHOWN = 3

    def add(self, msg: str, color=config.UI_ACCENT, duration: float = 3.5, icon: str | None = None) -> None:
        for it in self.items:                  # the same message again just stays up longer
            if it[0] == msg:
                it[2] = max(it[2], duration)
                return
        self.items.append([msg, color, duration, icon])
        self.items = self.items[-6:]

    def update(self, dt) -> None:
        for t in self.items:
            t[2] -= dt
        self.items = [t for t in self.items if t[2] > 0]

    ICONS = {(255, 230, 120): "coin", (140, 255, 230): "ore", (200, 255, 200): "fuel"}

    def draw(self, surf, in_menu: bool = False) -> None:
        """Small plaques: gold for rewards, teal for everyday pickups. In the right HUD column
        during play; along the bottom centre over menus, where they can't cover the menu's header."""
        from .text import theme
        from .hud import LAYOUT, RIGHT_W, fit
        th = theme()
        y = LAYOUT.get("right_bottom", 120) + 10          # the right column, under the location
        shown = self.items[-(1 if in_menu else self.MAX_SHOWN):]
        for msg, color, left, icon in shown:
            msg = fit(msg, RIGHT_W - 60)
            if in_menu:
                from . import pixelfont
                w = pixelfont.width(msg, 2) + 70
                r = th.plate(surf, ((config.SCREEN_W - w) // 2, config.SCREEN_H - 58, w, 40),
                             gold=tuple(color[:3]) in ((255, 230, 120), (255, 210, 90)))
                pixelfont.draw(surf, msg, r.center, 2, th.c["text"], "center")
                continue
            gold = tuple(color[:3]) in ((255, 210, 90), (255, 215, 110), (255, 220, 120), (255, 230, 120)) or \
                "Achievement" in msg or "recovered" in msg
            ic = icon or ("trophy" if "Achievement" in msg else "coin" if "cr" in msg.split()[-1:] else None)
            if ic and ic not in th.icons:
                ic = {"credits": "coin"}.get(ic)
            off = 0 if left > 0.4 else int((0.4 - left) / 0.4 * 400)
            if ic:
                th.toast(surf, (config.SCREEN_W - 12 + off, y), ic, msg, gold=gold)
            else:
                from . import pixelfont
                w = pixelfont.width(msg, 2) + 28
                r = th.plate(surf, (config.SCREEN_W - 12 - w + off, y, w, 40), gold=gold)
                pixelfont.draw(surf, msg, (r.x + 14, r.centery), 2, th.c["accent"] if gold else th.c["text"],
                               "midleft")
            y += 44


class Banner:
    """Big centred title card, e.g. 'DISCOVERED: Orkaia system'."""

    def __init__(self):
        self.title = ""
        self.sub = ""
        self.t = 0.0
        self.duration = 1.0

    def show(self, title: str, sub: str = "", duration=3.2) -> None:
        self.title, self.sub, self.t, self.duration = title, sub, duration, duration

    def update(self, dt):
        self.t = max(0.0, self.t - dt)

    def draw(self, surf):
        """A big pixel title with a dark outline, and a subtitle plate."""
        if self.t <= 0:
            return
        from . import pixelfont
        from .text import theme
        th = theme()
        k = max(0.0, min(1.0, self.t / 0.6, (self.duration - self.t) / 0.3))
        if k <= 0.02:
            return
        from .hud import CENTER_X0, CENTER_X1, LAYOUT, fit
        band = CENTER_X1 - CENTER_X0
        cx = (CENTER_X0 + CENTER_X1) // 2
        title = pixelfont.render(fit(self.title, band, 3), (255, 226, 140), 3, None, (20, 12, 8))
        subs = [pixelfont.render(ln, th.c["text"], 2, None, (8, 8, 14))
                for ln in pixelfont.wrap(self.sub, band, 2)[:2]] if self.sub else []
        y = LAYOUT.get("center_top", 70) + 6
        for img in [title] + subs:
            if k < 1:
                img = img.copy()
                img.set_alpha(int(255 * k))
            surf.blit(img, img.get_rect(midtop=(cx, y)))
            y += img.get_height() + 6
