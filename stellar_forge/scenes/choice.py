"""A story choice: portrait, a few lines of text and 2-4 options."""
from __future__ import annotations

import pygame

from .. import config
from ..core.scene import Scene
from ..ui.overlay import NAMES, PORTRAITS
from ..ui.text import panel, text, wrap
from .menus import Menu


class ChoiceScene(Scene):
    is_overlay = True
    menu = True

    def __init__(self, game, speaker: str, title: str, body: str, options, can_cancel: bool = False):
        """options: list of (label, callback) or (label, callback, hint). A callback
        may return another ``(title, body, options)`` tuple to continue the conversation."""
        super().__init__(game)
        self.speaker = speaker
        self.title = title
        self.body = body
        self.can_cancel = can_cancel
        self.t = 0.0
        self._set(options)

    def _set(self, options):
        wrapped = [(o[0], (lambda fn=o[1]: self._pick(fn)), o[2] if len(o) > 2 else "") for o in options]
        self.menu = Menu(wrapped, 0, self.game, 520)

    def _pick(self, fn):
        nxt = fn() if fn else None
        if isinstance(nxt, tuple):
            self.title, self.body, opts = nxt
            self.t = 0.0
            self._set(opts)
            return
        if self.game.scenes.top is self:
            self.game.scenes.pop()

    def handle_event(self, e) -> None:
        if self.t < 0.25:
            return
        if self.can_cancel and e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.scenes.pop()
            return
        self.menu.handle(e)

    def update(self, dt) -> None:
        self.t += dt
        self.menu.update(dt)

    def draw(self, surf) -> None:
        v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        v.fill((0, 3, 12, int(min(170, self.t * 900))))
        surf.blit(v, (0, 0))
        if self.speaker.startswith("settler:"):
            from ..ui.overlay import settler_portrait
            face, who = settler_portrait(self.game, self.speaker)
            sprite, color = None, (170, 220, 200)
        else:
            sprite, color = PORTRAITS.get(self.speaker, PORTRAITS["ai"])
            who = NAMES.get(self.speaker, self.speaker)
        lines = wrap(self.body, 17, 560)
        h = 176 + len(lines) * 24 + len(self.menu.items) * Menu.ROW       # room for the hint line
        r = pygame.Rect((config.SCREEN_W - 760) // 2, (config.SCREEN_H - h) // 2, 760, h)
        panel(surf, r, color=(8, 14, 30, 240), border=color)
        pr = pygame.Rect(r.x + 20, r.y + 20, 120, 120)
        pygame.draw.rect(surf, (20, 26, 44), pr, border_radius=8)
        img = self.game.assets.image(sprite, size=(110, 110)) if sprite else \
            pygame.transform.scale(face, (96, 96))
        surf.blit(img, img.get_rect(center=pr.center))
        text(surf, who, (pr.centerx, pr.bottom + 6), 13, color, bold=True, anchor="midtop")
        text(surf, self.title, (r.x + 160, r.y + 20), 24, config.UI_GOLD, bold=True)
        for i, line in enumerate(lines):
            text(surf, line, (r.x + 160, r.y + 60 + i * 24), 17, (220, 230, 245))
        self.menu.x = r.x + 160
        self.menu.width = r.w - 190
        self.menu.y = max(r.y + 160, r.y + 76 + len(lines) * 24)
        self.menu.draw(surf)
