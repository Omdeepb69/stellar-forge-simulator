"""The true ending: the five Shards return, the Forge wakes, Earth-Prime is reborn."""
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
from .menus import credits_lines, fmt_time
from ..core.assets import rot as _rot

CENTER = Vector2(config.SCREEN_W / 2, config.SCREEN_H / 2 - 20)
SHARD_START, SHARD_GAP = 2.0, 1.1
IGNITE = SHARD_START + SHARD_GAP * 5 + 1.2
BIRTH = IGNITE + 1.6
LINES_AT = BIRTH + 5.0
CREDITS_AT = LINES_AT + 11.0

LINES = {
    "rebuild": [("The Forge remembers what it was made for.", (255, 220, 150)),
                ("Not to break worlds - to make them.", (200, 225, 255)),
                ("Earth-Prime, reborn.", (140, 230, 255))],
    "destroy": [("Some power is too great for any hand.", (255, 220, 150)),
                ("The Forge is gone. No tyrant will ever wield it again.", (200, 225, 255)),
                ("The galaxy is free.", (140, 230, 255))],
}


class EndingScene(Scene):
    music = "ending"
    menu = True

    def __init__(self, game, ending: str = "rebuild"):
        super().__init__(game)
        self.ending = ending
        self.t = 0.0
        self.stars = Starfield(77)
        self.particles = ParticleSystem(900)
        self.gate = game.assets.image("generated/ships/forge_gate.png")
        self.shard_imgs = {b: game.assets.image(f"generated/items/shard_{b}.png", size=(42, 54)) for b in SHARD_BIOMES}
        self.arrived = 0
        self.flash = 0.0
        self.ignited = False
        from ..world.planet_art import render_planet
        self.earth = render_planet(2024, None, False, False, biome="forest", size=96)
        self.done = False
        self.credits_y = config.SCREEN_H + 40
        self.lines = self._credit_rows()

    def _credit_rows(self):
        st = self.game.state
        rows = [("THE END", 52, config.UI_GOLD), ("", 20, (0, 0, 0)),
                ("YOUR VOYAGE", 16, (140, 210, 255)),
                (f"Time played  {fmt_time(st.play_time)}", 18, (225, 230, 245)),
                (f"Raiders destroyed  {st.kills}", 18, (225, 230, 245)),
                (f"Systems charted  {max(0, len(st.discovered_systems) - 1)}", 18, (225, 230, 245)),
                (f"Worlds walked  {len(st.landed_planets)}", 18, (225, 230, 245)),
                (f"Achievements  {len(st.achievements)}", 18, (225, 230, 245)), ("", 40, (0, 0, 0))]
        return rows + credits_lines(self.game) + [("", 40, (0, 0, 0)),
                                                   ("New Game+ is now unlocked.", 18, (200, 150, 255)),
                                                   ("Press Enter to return to the stars", 16, (150, 160, 190))]

    def _socket(self, k: int, spin: float) -> Vector2:
        a = math.radians(-90 + k * 72 - spin)
        return CENTER + Vector2(math.cos(a), math.sin(a)) * 130

    def handle_event(self, e) -> None:
        if e.type != pygame.KEYDOWN or e.key not in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            return
        if self.t < CREDITS_AT:
            self.t = max(self.t, CREDITS_AT)
            self.arrived = 5
            self.ignited = True
        elif not self.done:
            self.done = True
            self.game.finish_ending(self.ending)

    def update(self, dt) -> None:
        self.t += dt
        self.particles.update(dt)
        self.flash = max(0.0, self.flash - dt * 1.5)
        spin = self._spin()
        while self.arrived < 5 and self.t >= SHARD_START + SHARD_GAP * (self.arrived + 1):
            p = self._socket(self.arrived, spin)
            col = SHARD_COLORS[SHARD_BIOMES[self.arrived]]
            self.particles.burst(p.x, p.y, 40, 220, [col, (255, 255, 255)], life=(0.4, 1.0))
            self.game.audio.play("relic", 0.8)
            self.arrived += 1
        if not self.ignited and self.t >= IGNITE:
            self.ignited = True
            self.flash = 1.0
            self.game.audio.play("warp", 1.0)
            for _ in range(160):
                v = Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(100, 600)
                self.particles.emit(CENTER.x, CENTER.y, v.x, v.y, random.uniform(0.8, 2.0), random.uniform(3, 7),
                                    random.choice([(255, 220, 150), (140, 230, 255), (255, 255, 255)]), drag=1.2,
                                    glow=True)
        if self.ending == "destroy":
            if self.t > BIRTH and not getattr(self, "shattered", False):
                self.shattered = True
                self.flash = 1.0
                self.game.audio.play("explosion", 1.0)
                self.particles.explosion(CENTER.x, CENTER.y, 4.0)
                for _ in range(200):
                    v = Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(150, 900)
                    self.particles.emit(CENTER.x, CENTER.y, v.x, v.y, random.uniform(1.0, 2.5), random.uniform(3, 8),
                                        random.choice([(255, 200, 120), (255, 255, 255), (160, 150, 140)]), drag=0.8)
        elif self.t > BIRTH and random.random() < 0.6:
            a = random.uniform(0, math.tau)
            r = random.uniform(260, 420)
            p = CENTER + Vector2(math.cos(a), math.sin(a)) * r
            v = (CENTER - p) * 0.9
            self.particles.emit(p.x, p.y, v.x, v.y, 1.0, random.uniform(2, 4),
                                random.choice([(120, 200, 255), (160, 255, 190), (255, 240, 200)]), glow=True)
        if self.t >= CREDITS_AT:
            self.credits_y -= 42 * dt
            total = sum(sz + 18 for _, sz, _ in self.lines)
            self.credits_y = max(self.credits_y, config.SCREEN_H * 0.5 - total)

    def _spin(self) -> float:
        if self.t < IGNITE:
            return self.t * 3
        return IGNITE * 3 + (self.t - IGNITE) ** 1.6 * 30

    def draw(self, surf) -> None:
        surf.fill((2, 3, 10))
        self.stars.draw(surf, self.t * 20, self.t * 6)
        spin = self._spin()
        fade_gate = 1.0 if self.t < BIRTH else (0.0 if self.ending == "destroy" else max(0.0, 1 - (self.t - BIRTH) / 2.5))
        # birth of the new world
        if self.t > BIRTH and self.ending == "destroy":
            k = self.t - BIRTH
            for i in range(3):
                r = (k * 420 - i * 90)
                if 0 < r < 1400:
                    pygame.draw.circle(surf, (255, 200, 140), CENTER, r, max(1, int(6 - k * 2)))
            for j in range(10):
                a = j * 0.63
                d = 60 + k * (120 + j * 25)
                piece = self.gate.subsurface(gate_piece(self.gate, j))
                img = _rot(piece, k * (40 + j * 11), 1.0)
                img.set_alpha(int(max(0, 255 - k * 50)))
                surf.blit(img, img.get_rect(center=CENTER + Vector2(math.cos(a), math.sin(a)) * d))
        elif self.t > BIRTH:
            k = min(1.0, (self.t - BIRTH) / 4.0)
            ease = 1 - (1 - k) ** 3
            size = int(20 + ease * 360)
            g = glow(max(8, int(size * 0.9)) // 4 * 4, (90, 170, 255), 0.6 * ease)
            surf.blit(g, g.get_rect(center=CENTER), special_flags=pygame.BLEND_ADD)
            k = max(1 / 8, round(size / self.earth.get_width() * 8) / 8) if size < self.earth.get_width() else \
                max(1, round(size / self.earth.get_width()))
            img = pygame.transform.scale(self.earth, (int(self.earth.get_width() * k), int(self.earth.get_height() * k)))
            surf.blit(img, img.get_rect(center=CENTER))
        if fade_gate > 0:
            power = 0.25 + 0.15 * self.arrived + (0.6 if self.ignited else 0)
            g = glow(int(160 + 120 * power) // 4 * 4, (255, 190, 100), min(1.0, power))
            surf.blit(g, g.get_rect(center=CENTER), special_flags=pygame.BLEND_ADD)
            gate = _rot(self.gate, spin, 1.25)
            if fade_gate < 1:
                gate.set_alpha(int(255 * fade_gate))
            surf.blit(gate, gate.get_rect(center=CENTER))
            for k, b in enumerate(SHARD_BIOMES):
                target = self._socket(k, spin)
                arrive_t = SHARD_START + SHARD_GAP * (k + 1)
                if self.t < arrive_t - SHARD_GAP:
                    continue
                img = self.shard_imgs[b]
                if self.t < arrive_t:
                    f = 1 - (arrive_t - self.t) / SHARD_GAP
                    f = f * f * (3 - 2 * f)
                    start = CENTER + Vector2(0, -520).rotate(k * 72 + 20)
                    pos = start.lerp(target, f)
                else:
                    pos = target
                if fade_gate < 1:
                    img = img.copy()
                    img.set_alpha(int(255 * fade_gate))
                surf.blit(img, img.get_rect(center=pos))
        self.particles.draw(surf, lambda p: p)
        if self.t < SHARD_START + 1.5:
            k = min(1.0, self.t / 1.0) * min(1.0, (SHARD_START + 1.5 - self.t) / 0.6)
            text(surf, "The five Shards answer the Forge's call...", (config.SCREEN_W // 2, config.SCREEN_H - 90),
                 22, tuple(int(c * k) for c in (230, 220, 255)), anchor="center")
        if LINES_AT <= self.t < CREDITS_AT + 1:
            for i, (msg, col) in enumerate(LINES[self.ending]):
                lt = self.t - (LINES_AT + i * 3.0)
                if lt <= 0:
                    continue
                k = min(1.0, lt / 1.0) * max(0.0, min(1.0, (CREDITS_AT + 1 - self.t) / 1.0))
                text(surf, msg, (config.SCREEN_W // 2, config.SCREEN_H - 150 + i * 36), 24 if i < 2 else 30,
                     tuple(int(c * k) for c in col), bold=(i == 2), anchor="center")
        if self.t >= CREDITS_AT:
            shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            shade.fill((0, 0, 8, int(min(150, (self.t - CREDITS_AT) * 80))))
            surf.blit(shade, (0, 0))
            y = self.credits_y
            for msg, size, col in self.lines:
                if msg and -60 < y < config.SCREEN_H + 60:
                    text(surf, msg, (config.SCREEN_W // 2, y), size, col, bold=size >= 22, anchor="midtop")
                y += size + 18
        if self.flash > 0:
            fl = pygame.Surface(surf.get_size())
            fl.fill((255, 255, 255))
            fl.set_alpha(int(255 * self.flash))
            surf.blit(fl, (0, 0))
        if self.t < CREDITS_AT:
            text(surf, "Enter: skip", (config.SCREEN_W - 14, config.SCREEN_H - 10), 12, (90, 100, 130),
                 anchor="bottomright")
