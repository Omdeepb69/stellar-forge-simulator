"""Act II intro: the Forge's core shatters and the Remnant rise (skippable)."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from ..core.assets import glow
from ..core.game_state import SHARD_BIOMES, SHARD_COLORS
from ..core.scene import Scene
from ..entities.bodies import gate_piece
from ..systems.particles import ParticleSystem
from ..ui.starfield import Starfield
from ..ui.text import text
from ..core.assets import rot as _rot

CENTER = Vector2(config.SCREEN_W / 2, config.SCREEN_H / 2 - 10)
BREAK, SCATTER, CARD, END = 3.0, 6.5, 10.5, 15.0
CAPTIONS = [
    (0.4, BREAK, "As the Warlord fell, the Forge screamed."),
    (BREAK + 0.4, SCATTER, "Its heart broke into five Shards, flung across the stars..."),
    (SCATTER + 0.3, CARD, "...and what was left of his fleet woke to claim them."),
]


class ActTwoScene(Scene):
    music = "stronghold"
    menu = True

    def __init__(self, game, on_done):
        super().__init__(game)
        self.on_done = on_done
        self.t = 0.0
        self.finished = False
        self.stars = Starfield(4242)
        self.particles = ParticleSystem(700)
        a = game.assets
        self.gate = a.image("generated/ships/forge_gate.png")
        self.shards = {b: a.image(f"generated/items/shard_{b}.png", size=(34, 44)) for b in SHARD_BIOMES}
        self.ship = a.image("generated/ships/dreadnought.png", scale=0.35, tint=(90, 90, 110))
        rng = random.Random(7)
        self.targets = [CENTER + Vector2(1, 0).rotate(-90 + k * 72 + rng.uniform(-15, 15)) * rng.uniform(250, 330)
                        for k in range(5)]
        self.dirs = [Vector2(1, 0).rotate(-90 + k * 72) for k in range(5)]
        self.boomed = False
        self.flash = 0.0
        self.shake = 0.0
        self.card_sound = False

    def on_enter(self) -> None:
        self.game.dialogue.queue.clear()
        self.game.dialogue.on_done.clear()
        self.game.banner.t = 0.0
        self.game.toasts.items.clear()

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            if self.t < CARD:
                self.t = CARD
                self.boomed = True
            else:
                self._finish()

    def _finish(self):
        if not self.finished:
            self.finished = True
            self.on_done()

    def update(self, dt) -> None:
        self.t += dt
        self.particles.update(dt)
        self.flash = max(0.0, self.flash - dt * 1.4)
        self.shake = max(0.0, self.shake - dt * 20)
        if self.t < BREAK:
            if random.random() < dt * (2 + self.t * 3):
                self.shake = 6 + self.t * 3
                self.game.audio.play("hit", 0.3)
                p = CENTER + Vector2(random.uniform(-110, 110), random.uniform(-110, 110))
                self.particles.burst(p.x, p.y, 10, 160, [(255, 90, 60), (255, 200, 120)], life=(0.2, 0.6))
        elif not self.boomed:
            self.boomed = True
            self.flash = 1.0
            self.shake = 26
            self.game.audio.play("explosion", 1.0)
            self.game.audio.play("warp", 0.6)
            self.particles.explosion(CENTER.x, CENTER.y, 3.0)
            for _ in range(140):
                v = Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(120, 700)
                self.particles.emit(CENTER.x, CENTER.y, v.x, v.y, random.uniform(0.6, 1.6), random.uniform(3, 7),
                                    random.choice([(255, 180, 90), (255, 240, 200), (150, 140, 130)]), drag=1.5)
        if BREAK < self.t < SCATTER:
            for k, b in enumerate(SHARD_BIOMES):
                p = self._shard_pos(k)
                if random.random() < 0.8:
                    self.particles.emit(p.x, p.y, random.uniform(-20, 20), random.uniform(-20, 20), 0.6,
                                        random.uniform(2, 4), SHARD_COLORS[b], drag=2, glow=True)
        if self.t >= CARD and not self.card_sound:
            self.card_sound = True
            self.game.audio.play("discover", 1.0)
        if self.t >= END:
            self._finish()

    def _shard_pos(self, k: int) -> Vector2:
        f = max(0.0, min(1.0, (self.t - BREAK) / (SCATTER - BREAK)))
        ease = 1 - (1 - f) ** 3
        start = CENTER + self.dirs[k] * 20
        # curve out, then settle on its distant world
        mid = CENTER + self.dirs[k].rotate(35) * 420
        a = start.lerp(mid, ease)
        b = mid.lerp(self.targets[k], ease)
        return a.lerp(b, ease)

    def draw(self, surf) -> None:
        surf.fill((3, 3, 10))
        off = Vector2(random.uniform(-1, 1), random.uniform(-1, 1)) * self.shake
        self.stars.draw(surf, self.t * 15, self.t * 4)
        if self.t < BREAK + 0.6:
            heat = min(1.0, self.t / BREAK)
            g = glow(int(150 + 120 * heat) // 4 * 4, (255, int(190 - 120 * heat), 90), 0.5 + 0.5 * heat)
            surf.blit(g, g.get_rect(center=CENTER + off), special_flags=pygame.BLEND_ADD)
            gate = _rot(self.gate, self.t * 25 * heat, 1.2)
            if self.t > BREAK:
                gate.set_alpha(int(255 * max(0, 1 - (self.t - BREAK) / 0.6)))
            surf.blit(gate, gate.get_rect(center=CENTER + off))
        elif self.t < CARD + 1:
            # the broken ring drifting apart
            for k in range(6):
                d = Vector2(1, 0).rotate(k * 60 + 15) * (60 + (self.t - BREAK) * 25)
                piece = _rot(self.gate.subsurface(gate_piece(self.gate, k)),
                                                  self.t * (20 + k * 7), 0.9)
                piece.set_alpha(150)
                surf.blit(piece, piece.get_rect(center=CENTER + d + off))
        if self.t > BREAK:
            for k, b in enumerate(SHARD_BIOMES):
                p = self._shard_pos(k) + off
                col = SHARD_COLORS[b]
                g = glow(40, col, 0.8)
                surf.blit(g, g.get_rect(center=p), special_flags=pygame.BLEND_ADD)
                surf.blit(self.shards[b], self.shards[b].get_rect(center=p))
                if self.t > SCATTER:  # Remnant ships converge on each Shard
                    k2 = min(1.0, (self.t - SCATTER) / 2.5)
                    for side in (-1, 1):
                        sp = p + self.dirs[k].rotate(side * 50) * (140 - 80 * k2)
                        ang = math.degrees(math.atan2(p.x - sp.x, -(p.y - sp.y)))
                        img = _rot(self.ship, -ang, 1.0)
                        img.set_alpha(int(220 * k2))
                        surf.blit(img, img.get_rect(center=sp))
        self.particles.draw(surf, lambda pt: (pt[0] + off.x, pt[1] + off.y))
        for t0, t1, msg in CAPTIONS:
            if t0 <= self.t < t1:
                k = min(1.0, (self.t - t0) / 0.6, (t1 - self.t) / 0.5)
                text(surf, msg, (config.SCREEN_W // 2, config.SCREEN_H - 80), 22,
                     tuple(int(c * max(0, k)) for c in (225, 225, 245)), anchor="center")
        if self.t >= CARD:
            k = min(1.0, (self.t - CARD) / 1.0) * min(1.0, max(0.0, (END - self.t) / 0.8))
            shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            shade.fill((0, 0, 6, int(170 * k)))
            surf.blit(shade, (0, 0))
            gold = tuple(int(c * k) for c in config.UI_GOLD)
            cyan = tuple(int(c * k) for c in (140, 210, 255))
            text(surf, "ACT II", (config.SCREEN_W // 2, 280), 72, gold, bold=True, anchor="center")
            text(surf, "THE  SHATTERED  FORGE", (config.SCREEN_W // 2, 350), 28, cyan, bold=True, anchor="center")
            w = int(300 * k)
            pygame.draw.line(surf, gold, (config.SCREEN_W // 2 - w, 385), (config.SCREEN_W // 2 + w, 385), 2)
        if self.flash > 0:
            fl = pygame.Surface(surf.get_size())
            fl.fill((255, 240, 220))
            fl.set_alpha(int(255 * self.flash))
            surf.blit(fl, (0, 0))
        text(surf, "Enter: skip", (config.SCREEN_W - 14, config.SCREEN_H - 10), 12, (90, 100, 130),
             anchor="bottomright")


class BellScene(Scene):
    """Act III teaser: at the rim of the galaxy, the Makers' bell rings."""
    music = "ending"
    menu = True
    LINES = [(1.5, "At the rim of everything charted, a structure older than the stars."),
             (5.0, "You touch it, and it rings once."),
             (8.5, "Far beyond, something that remembers making worlds turns towards the sound.")]
    CARD = 12.5
    END = 18.0

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        self.stars = Starfield(9090)
        self.particles = ParticleSystem(500)
        self.rung = False
        self.done = False

    def on_enter(self) -> None:
        self.game.dialogue.queue.clear()
        from ..systems import lore
        st = self.game.state
        if "a10" not in st.logs:
            st.logs.append("a10")
        if "r8" not in st.logs:
            st.logs.append("r8")
        lore.announce(self.game, None)

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            if self.t < self.CARD:
                self.t = self.CARD
            else:
                self._finish()

    def _finish(self):
        if not self.done:
            self.done = True
            self.game.save()
            self.game.scenes.pop(fade=True)
            self.game.quests.start_act_three()        # the Makers' road opens

    def update(self, dt) -> None:
        self.t += dt
        self.particles.update(dt)
        if self.t > 5.0 and not self.rung:
            self.rung = True
            self.game.audio.play("relic", 1.0)
            self.game.audio.play("warp", 0.6)
        if random.random() < 0.5:
            a = random.uniform(0, math.tau)
            p = CENTER + Vector2(math.cos(a), math.sin(a)) * random.uniform(300, 600)
            v = (CENTER - p) * 0.4
            self.particles.emit(p.x, p.y, v.x, v.y, 1.2, random.uniform(2, 4), (120, 255, 230), glow=True)
        if self.t >= self.END:
            self._finish()

    def draw(self, surf) -> None:
        surf.fill((2, 6, 10))
        self.stars.draw(surf, self.t * 8, self.t * 3)
        k = min(1.0, self.t / 3)
        g = glow(int(220 + 60 * math.sin(self.t)) // 4 * 4, (90, 240, 220), 0.5 * k)
        surf.blit(g, g.get_rect(center=CENTER), special_flags=pygame.BLEND_ADD)
        w, h = 300, 380
        sx, sy = CENTER
        pts = [(sx - w * 0.2, sy - h * 0.5), (sx + w * 0.2, sy - h * 0.5), (sx + w * 0.35, sy + h * 0.1),
               (sx + w * 0.5, sy + h * 0.45), (sx - w * 0.5, sy + h * 0.45), (sx - w * 0.35, sy + h * 0.1)]
        pygame.draw.polygon(surf, (24, 60, 70), pts)
        pygame.draw.polygon(surf, (120, 255, 230), pts, 3)
        for i in range(5):
            y = sy - h * 0.3 + i * h * 0.14
            pygame.draw.line(surf, (70, 160, 150), (sx - w * (0.22 + i * 0.05), y), (sx + w * (0.22 + i * 0.05), y), 2)
        if self.rung:
            for i in range(4):
                r = (self.t - 5.0) * 300 - i * 120
                if 0 < r < 1300:
                    pygame.draw.circle(surf, (120, 255, 230), CENTER, r, 2)
        self.particles.draw(surf, lambda pt: pt)
        for i, (t0, msg) in enumerate(self.LINES):
            if t0 <= self.t < self.CARD:
                a = min(1.0, (self.t - t0) / 1.0, (self.CARD - self.t) / 0.6)
                text(surf, msg, (config.SCREEN_W // 2, config.SCREEN_H - 130 + i * 30), 19,
                     tuple(int(c * max(0, a)) for c in (210, 240, 235)), anchor="center")
        if self.t >= self.CARD:
            a = min(1.0, (self.t - self.CARD) / 1.0) * min(1.0, max(0.0, (self.END - self.t) / 0.8))
            shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            shade.fill((0, 0, 6, int(170 * a)))
            surf.blit(shade, (0, 0))
            text(surf, "ACT III", (config.SCREEN_W // 2, 280), 72, tuple(int(c * a) for c in (120, 255, 230)),
                 bold=True, anchor="center")
            text(surf, "THE  MAKERS", (config.SCREEN_W // 2, 350), 28, tuple(int(c * a) for c in config.UI_GOLD),
                 bold=True, anchor="center")
            text(surf, "the road to the ones who made the Forge", (config.SCREEN_W // 2, 395), 16,
                 tuple(int(c * a) for c in (170, 190, 210)), anchor="center")
        text(surf, "Enter: skip", (config.SCREEN_W - 14, config.SCREEN_H - 10), 12, (90, 100, 130),
             anchor="bottomright")


class CaptionScene(Scene):
    """Lines of story over a starfield, one after another, then a title card. Enter skips ahead."""
    music = "ending"
    menu = True

    def __init__(self, game, captions, title: str, subtitle: str = "", on_done=None, per_line: float = 4.2):
        super().__init__(game)
        self.captions = captions              # [(text, colour)]
        self.title, self.subtitle = title, subtitle
        self.on_done = on_done
        self.per = per_line
        self.t = 0.0
        self.stars = Starfield(5150)
        self.card = 1.0 + len(captions) * per_line
        self.end = self.card + 5.0
        self.done = False

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            if self.t < self.card:
                nxt = 1.0 + (int((self.t - 1.0) // self.per) + 1) * self.per     # next line
                self.t = min(self.card, max(self.t, nxt))
            else:
                self._finish()

    def _finish(self) -> None:
        if not self.done:
            self.done = True
            self.game.scenes.pop(fade=True)
            if self.on_done:
                self.on_done()

    def update(self, dt) -> None:
        self.t += dt
        if self.t >= self.end:
            self._finish()

    def draw(self, surf) -> None:
        from ..ui import pixelfont
        surf.fill((2, 6, 10))
        self.stars.draw(surf, self.t * 6, self.t * 2)
        g = glow(240, (90, 240, 220), 0.35)
        surf.blit(g, g.get_rect(center=CENTER), special_flags=pygame.BLEND_ADD)
        if self.t < self.card:
            k = int(max(0.0, self.t - 1.0) // self.per)
            if 0 <= k < len(self.captions):
                msg, col = self.captions[k]
                local = self.t - 1.0 - k * self.per
                a = max(0.0, min(1.0, local / 0.8, (self.per - local) / 0.6))
                for i, ln in enumerate(pixelfont.wrap(msg, 900, 2)[:4]):
                    text(surf, ln, (config.SCREEN_W // 2, config.SCREEN_H // 2 - 20 + i * 28), 19,
                         tuple(int(c * a) for c in col), anchor="center")
        else:
            a = min(1.0, (self.t - self.card) / 1.0) * min(1.0, max(0.0, (self.end - self.t) / 0.8))
            text(surf, self.title, (config.SCREEN_W // 2, 300), 44, tuple(int(c * a) for c in config.UI_GOLD),
                 bold=True, anchor="center")
            if self.subtitle:
                text(surf, self.subtitle, (config.SCREEN_W // 2, 352), 16,
                     tuple(int(c * a) for c in (170, 190, 210)), anchor="center")
        text(surf, "Enter: next", (config.SCREEN_W - 14, config.SCREEN_H - 10), 12, (90, 100, 130),
             anchor="bottomright")
