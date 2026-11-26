"""Front-end screens: title, new game, settings, credits, pause, game over.

They all share one look: translucent navy glass panels with gold
selection, cyan secondary text, and the same animated starfield.
"""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import __version__, config
from ..core.game_state import SLOTS, GameState, slot_path
from ..core.scene import Scene
from ..ui.text import bar, panel, text

GOLD = config.UI_GOLD
CYAN = (140, 210, 255)


def fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {int(seconds % 60):02d}s"


def veil(surf, alpha=160):
    v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    v.fill((0, 2, 10, alpha))
    surf.blit(v, (0, 0))


# -----------------------------------------------------------------------------
MENU_ICONS = {"Continue": "play", "New Game": "plus", "Load Game": "folder", "Logbook": "book",
              "Settings": "gear", "Credits": "star", "Quit": "door", "New Game +": "star", "Resume": "play",
              "Save game": "folder", "Controls": "gear", "Save & quit to title": "door", "Launch": "play",
              "Random seed": "plus", "Back": "door", "Title screen": "door", "New game": "plus",
              "Continue from last save": "play"}


class Menu:
    """Keyboard/mouse menu list. Items are (label, action) or (label, action, hint).

    Console style: plain outlined text with an icon; only the selected item gets a
    gold plate and a lit lamp (see docs/style/ui_title.png)."""

    ROW = 56

    def __init__(self, items: list[tuple], y: int, game, width: int = 360, x: int | None = None, scale: int = 3):
        self.items = items
        self.index = 0
        self.y = y
        self.x = x
        self.game = game
        self.width = width
        self.scale = scale
        self.anim = [0.0] * len(items)

    def rects(self):
        x = (config.SCREEN_W - self.width) // 2 if self.x is None else self.x
        h = 12 * self.scale + 14
        return [pygame.Rect(x, self.y + i * self.ROW, self.width, h) for i in range(len(self.items))]

    def _move(self, d):
        self.index = (self.index + d) % len(self.items)
        self.game.audio.play("ui", 0.5)

    def handle(self, e) -> None:
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self._move(1)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER):
                self.game.audio.play("ui", 0.8)
                self.items[self.index][1]()
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects()):
                if r.collidepoint(e.pos) and i != self.index:
                    self.index = i
                    self.game.audio.play("ui", 0.3)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.rects()):
                if r.collidepoint(e.pos):
                    self.index = i
                    self.game.audio.play("ui", 0.8)
                    self.items[i][1]()

    def update(self, dt) -> None:
        for i in range(len(self.anim)):
            tgt = 1.0 if i == self.index else 0.0
            self.anim[i] += (tgt - self.anim[i]) * min(1, dt * 14)

    def draw(self, surf, alpha: float = 1.0) -> None:
        from ..ui.text import theme
        th = theme()
        if len(self.anim) != len(self.items):
            self.anim = [0.0] * len(self.items)
        if alpha < 0.05:
            return
        for i, (item, r) in enumerate(zip(self.items, self.rects())):
            label = item[0]
            sel = i == self.index
            nudge = int(self.anim[i] * 4) * 2
            if sel:
                th.plate(surf, r, gold=True)
                th.lamp(surf, (r.x + 20, r.centery))
            ic = th.icons.get(MENU_ICONS.get(label, ""), None)
            x = r.x + 40 + nudge
            if ic is not None:
                surf.blit(ic, ic.get_rect(midleft=(x, r.centery)))
                x += ic.get_width() + 12
            th.text(surf, label, (x, r.centery), self.scale, th.c["accent"] if sel else th.c["text"], "midleft",
                    outline=True)
        if len(self.items[self.index]) > 2 and self.items[self.index][2]:
            last = self.rects()[-1]
            th.text(surf, self.items[self.index][2], (last.x + 40, last.bottom + 12), 2, th.c["dim"], outline=True)


CONTROLS = [
    ("SPACE FLIGHT", ""),
    ("W / Up", "Thrust      SHIFT  boost (burns fuel)"),
    ("A D / Left Right", "Rotate"),
    ("S / Down", "Match speed with nearest body (brake)"),
    ("SPACE / mouse", "Fire blaster"),
    ("L", "Land on a nearby planet"),
    ("E", "Dock at station / wormhole / Stellar Forge"),
    ("M  /  TAB", "Galaxy map (click: waypoint)  /  cycle scanner target"),
    ("P  /  Q", "Autopilot to target or waypoint  /  switch weapon"),
    ("V  /  C", "Camera: close / medium / far (also wheel, + -)  /  hail the Survey Corps"),
    ("ON FOOT", ""),
    ("A D", "Walk       W jump, hold W in the air for jetpack"),
    ("SPACE / J", "Sword (mines ore, reflects boss orbs)"),
    ("F / K", "Blaster"),
    ("E", "Board rocket, enter caves, talk to settlers and groups, mine, open boards"),
    ("O", "Outpost menu (at rocket)"),
    ("H", "Use a Nano-Medkit to restore pilot health"),
    ("F hold  /  Q", "Charged piercing shot  /  swap sword and spear"),
    ("GENERAL", ""),
    ("B", "Logbook: journal, codex, achievements, stats"),
    ("Enter", "Advance dialogue     ESC pause     F11 fullscreen     F3 fps"),
    ("GAMEPAD", ""),
    ("Stick / D-pad", "Steer, walk, menus    A fire/confirm    B back    X dock/interact"),
    ("Y  LB  RB", "Land    boost    blaster      LT brake  RT thrust   View map   Guide camera"),
    ("On foot", "A jump    X sword    Y interact    RB blaster    L-stick click: Corps"),
]


def draw_controls(surf, y0=60) -> None:
    from ..ui.text import theme
    th = theme()
    w = 900
    x = (config.SCREEN_W - w) // 2
    th.panel(surf, (x, y0 - 34, w, len(CONTROLS) * 23 + 92))
    for i, (k, v) in enumerate(CONTROLS):
        y = y0 + i * 23
        if not v:
            th.text(surf, k, (x + 40, y), 2, th.c["accent"])
        else:
            th.text(surf, k, (x + 60, y), 2, (140, 220, 255))
            th.text(surf, v, (x + 300, y), 2, th.c["text"])
    th.text(surf, "press any key", (config.SCREEN_W // 2, y0 + len(CONTROLS) * 23 + 14), 2, th.c["dim"], "midtop")


class ControlsScene(Scene):
    is_overlay = True
    menu = True

    def handle_event(self, e) -> None:
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.game.scenes.pop()

    def draw(self, surf) -> None:
        veil(surf, 210)
        draw_controls(surf)


# -----------------------------------------------------------------------------
class Backdrop:
    """The animated pixel-art space vista shared by the title, credits and menus:
    painted nebula, a big pixel planet with a moon, and the Voyager flying past."""

    def __init__(self, game):
        self.game = game
        self.t = 0.0
        from ..ui.backdrop import pixel_sky
        from ..world.planet_art import render_planet
        self.sky = pixel_sky()
        planet = render_planet(11, None, False, False, biome="forest", size=150)
        self.planet = pygame.transform.scale(planet, (planet.get_width() * 4, planet.get_height() * 4))
        moon = render_planet(4, None, False, False, biome="barren", size=26)
        self.moon = pygame.transform.scale(moon, (moon.get_width() * 4, moon.get_height() * 4))
        a = game.assets
        self.rocket = [a.sprite(p) for p in ("rocket/centreflame.png", "rocket/leftflame.png",
                                             "rocket/rightflame.png")]
        self.raider = a.sprite("alien/alien_ship/alienShip.png")
        self.flyby = None
        self.next_flyby = 2.0
        self.shooting = []
        self.bolts = []
        self.twinkle = [(random.randrange(0, config.SCREEN_W, 4), random.randrange(0, config.SCREEN_H, 4),
                         random.uniform(0, 6)) for _ in range(40)]

    def update(self, dt) -> None:
        self.t += dt
        self.next_flyby -= dt
        if self.flyby is None and self.next_flyby <= 0:
            left = random.random() < 0.5
            y0 = random.uniform(240, 460)
            start = Vector2(-160 if left else config.SCREEN_W + 160, y0)
            end = Vector2(config.SCREEN_W + 200 if left else -200, y0 + random.uniform(-160, 100))
            vel = (end - start).normalize() * random.uniform(260, 330)
            self.flyby = {"pos": start, "vel": vel, "chase": random.random() < 0.5, "t": 0.0, "fire": 0.8}
        if self.flyby:
            f = self.flyby
            f["t"] += dt
            f["pos"] += f["vel"] * dt
            if f["chase"]:
                f["fire"] -= dt
                rp = f["pos"] - f["vel"].normalize() * 220
                if f["fire"] <= 0:
                    f["fire"] = random.uniform(0.4, 0.8)
                    self.bolts.append([Vector2(rp), f["vel"].normalize() * 900, 0.8])
            if not (-500 < f["pos"].x < config.SCREEN_W + 500) or f["t"] > 10:
                self.flyby = None
                self.next_flyby = random.uniform(5, 9)
        for b in self.bolts:
            b[0] += b[1] * dt
            b[2] -= dt
        self.bolts = [b for b in self.bolts if b[2] > 0]
        if random.random() < dt * 0.3:
            p = Vector2(random.uniform(200, config.SCREEN_W), random.uniform(0, 240))
            self.shooting.append([p, Vector2(-1, 0.45).normalize() * random.uniform(600, 900), 0.6])
        for sh in self.shooting:
            sh[0] += sh[1] * dt
            sh[2] -= dt
        self.shooting = [sh for sh in self.shooting if sh[2] > 0]

    def draw(self, surf) -> None:
        surf.blit(self.sky, (0, 0))
        for x, y, ph in self.twinkle:            # twinkling pixel stars
            if math.sin(self.t * 2 + ph) > 0.6:
                surf.fill((255, 250, 230), (x, y, 4, 4))
        for p, v, life in self.shooting:          # shooting stars as stepped pixel trails
            d = v.normalize()
            for k in range(6):
                q = p - d * k * 12
                c = 255 - k * 35
                surf.fill((c, c, min(255, c + 20)), (int(q.x) // 4 * 4, int(q.y) // 4 * 4, 4, 4))
        ang = self.t * 0.12
        moon_pos = (config.SCREEN_W - 200 + math.cos(ang) * 30, 130 + math.sin(ang) * 10)
        surf.blit(self.moon, self.moon.get_rect(center=moon_pos))
        surf.blit(self.planet, (config.SCREEN_W - 470, config.SCREEN_H - 300))
        for b in self.bolts:
            d = b[1].normalize()
            for k in range(4):
                q = b[0] - d * k * 8
                surf.fill((130, 255, 120), (int(q.x) // 2 * 2, int(q.y) // 2 * 2, 6, 6))
        if self.flyby:
            f = self.flyby
            heading = math.degrees(math.atan2(f["vel"].x, -f["vel"].y))
            img = pygame.transform.rotate(self.rocket[int(self.t * 12) % 3], -heading)
            surf.blit(img, img.get_rect(center=f["pos"]))
            if f["chase"]:
                rp = f["pos"] - f["vel"].normalize() * 220
                r2 = pygame.transform.rotate(self.raider, -heading)
                surf.blit(r2, r2.get_rect(center=rp))


# -----------------------------------------------------------------------------
class TitleScene(Scene):
    menu = True
    music = "title"

    def __init__(self, game):
        super().__init__(game)
        self.backdrop = Backdrop(game)
        a = game.assets
        if a.exists("generated/ui/logo_1x.png"):        # the painted logo, at a whole-number scale
            art = a.image("generated/ui/logo_1x.png")
            self.logo = pygame.transform.scale(art, (art.get_width() * 2, art.get_height() * 2))
            self.logo_has_subtitle = True
        else:
            from ..ui.backdrop import logo
            self.logo = logo("STELLAR FORGE", 9)
            self.logo_has_subtitle = False
        self.t = 0.0
        self._find_latest()
        self._build_menu()

    def _find_latest(self):
        """Continue = the most recently played slot."""
        paths = [p for p in [slot_path(i) for i in range(SLOTS)] if p.exists()]
        if config.SAVE_FILE.exists() and config.SAVE_FILE not in paths:
            paths.append(config.SAVE_FILE)
        self.latest = max(paths, key=lambda p: p.stat().st_mtime) if paths else None
        self.save = GameState.load(self.latest) if self.latest else None

    def _build_menu(self):
        items = []
        if self.save:
            items.append(("Continue", self._continue, "Resume your voyage"))
        items.append(("New Game", self._new, "Start a fresh galaxy in any of 3 slots"))
        if any(slot_path(i).exists() for i in range(SLOTS)):
            items.append(("Load Game", self._load, "Pick one of your save slots"))
        if self.save and self.save.forge_restored:
            items.append(("New Game +", self._ng_plus, "New galaxy, harder foes, keep your gear"))
        items += [("Logbook", self._logbook, "Achievements, codex and stats"),
                  ("Settings", self._settings, "Audio, display, controls and comfort"),
                  ("Controls", self._help, "Flight, surface and gamepad bindings"),
                  ("Credits", self._credits, ""),
                  ("Quit", self._quit, "")]
        self.menu = Menu(items, 262, self.game, 340, x=88)
        self.menu.ROW = 52 if len(items) <= 7 else (46 if len(items) == 8 else 43)

    def on_enter(self) -> None:
        self.game.dialogue.queue.clear()
        self.game.dialogue.on_done.clear()
        self.game.banner.t = 0.0
        self.game.toasts.items.clear()
        self.game.audio.loop("thrust", False)

    def on_resume(self) -> None:
        self._find_latest()
        idx = self.menu.index
        self._build_menu()
        self.menu.index = min(idx, len(self.menu.items) - 1)

    def _continue(self):
        if self.latest:
            self.game.select_save(self.latest)
        if not self.game.continue_game():
            self.game.toasts.add("Save file could not be read", config.UI_DANGER)

    def _new(self):
        self.game.scenes.push(SlotScene(self.game, "new"))

    def _load(self):
        self.game.scenes.push(SlotScene(self.game, "load"))

    def _ng_plus(self):
        if self.latest:
            self.game.select_save(self.latest)
        self.game.new_game_plus()

    def _logbook(self):
        from .logbook import LogbookScene
        self.game.scenes.push(LogbookScene(self.game, state=self.save or GameState()))

    def _settings(self):
        self.game.scenes.push(SettingsScene(self.game))

    def _help(self):
        self.game.scenes.push(ControlsScene(self.game))

    def _credits(self):
        self.game.scenes.push(CreditsScene(self.game))

    def _quit(self):
        self.game.running = False

    def handle_event(self, e) -> None:
        if self.t < 0.6:
            if e.type == pygame.KEYDOWN:
                self.t = 1.6  # skip the intro
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.menu.index = len(self.menu.items) - 1
            return
        self.menu.handle(e)

    def update(self, dt) -> None:
        self.t += dt
        self.backdrop.update(dt)
        self.menu.update(dt)

    def draw(self, surf) -> None:
        from ..ui.text import theme
        th = theme()
        self.backdrop.draw(surf)
        k = max(0.0, min(1.0, self.t / 1.2))
        ease = 1 - (1 - k) ** 3
        y = int(-60 + ease * (72 if self.logo_has_subtitle else 106)) // 2 * 2
        logo = self.logo
        if k < 1:
            logo = logo.copy()
            logo.set_alpha(int(255 * k))
        surf.blit(logo, logo.get_rect(midtop=(config.SCREEN_W // 2, y)))
        if not self.logo_has_subtitle:
            th.text(surf, "·  THE  LAST  VOYAGER  ·", (config.SCREEN_W // 2, y + 150), 3, (130, 220, 255), "midtop",
                    outline=True)
        m = max(0.0, min(1.0, (self.t - 0.8) / 0.5))
        if m > 0:
            self.menu.draw(surf, m)
            if self.save and self.menu.items[self.menu.index][0] in ("Continue", "New Game +", "Logbook"):
                self._save_card(surf, m)
        th.text(surf, f"v{__version__}", (config.SCREEN_W - 16, config.SCREEN_H - 14), 2, (120, 130, 160),
                "bottomright", outline=True)
        th.text(surf, "↑↓ choose   Enter select   F11 fullscreen", (16, config.SCREEN_H - 14), 2, (120, 130, 160),
                "bottomleft", outline=True)

    def _save_card(self, surf, alpha) -> None:
        """A small card beside Continue: chapter, Keys/Shards, credits, play time."""
        from ..systems.quests import CHAPTERS
        from ..ui.text import theme
        th = theme()
        st = self.save
        r0 = self.menu.rects()[self.menu.index]
        card = th.plate(surf, (r0.right + 20, r0.y - 8, 420, 104))
        ch = CHAPTERS[min(st.chapter, len(CHAPTERS) - 1)]
        th.text(surf, f"Ch.{st.chapter + 1} · {ch['title']}", (card.x + 20, card.y + 18), 2, th.c["accent"])
        x = th.counter(surf, (card.x + 20, card.y + 62), "key", f"{len(st.relics)}/3").right + 18
        if st.boss_defeated:
            x = th.counter(surf, (x, card.y + 62), "shard", f"{len(st.shards)}/5").right + 18
        th.counter(surf, (x, card.y + 62), "coin", f"{st.credits:,}", th.c["accent"])
        th.text(surf, fmt_time(st.play_time) + (f" · NG+{st.ng_plus}" if st.ng_plus else ""),
                (card.right - 20, card.y + 18), 2, th.c["dim"], "topright")


class NewGameScene(Scene):
    is_overlay = True
    menu = True

    DIFFS = ["story", "normal", "hard"]

    def __init__(self, game, overwrite: bool, slot: int | None = None):
        super().__init__(game)
        self.overwrite = overwrite
        self.slot = slot
        self.seed = str(random.randint(1, 999_999))
        self.diff = "normal"
        self.menu = Menu([("Launch", self._launch), ("Difficulty", self._cycle_diff), ("Random seed", self._reroll),
                          ("Back", self._back)], 432, game, 320)
        self.menu.ROW = 44

    def _cycle_diff(self, d=1):
        i = self.DIFFS.index(self.diff)
        self.diff = self.DIFFS[(i + d) % 3]

    def _launch(self):
        try:
            seed = int(self.seed) if self.seed else random.randint(1, 999_999)
        except ValueError:
            seed = random.randint(1, 999_999)
        if self.slot is not None:
            self.game.select_save(slot_path(self.slot))
            self.game.settings.last_slot = self.slot
        self.game.new_game(seed=seed, difficulty=self.diff)

    def _reroll(self):
        self.seed = str(random.randint(1, 999_999))

    def _back(self):
        self.game.scenes.pop()

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self._back()
                return
            if e.key == pygame.K_BACKSPACE:
                self.seed = self.seed[:-1]
                return
            if e.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.menu.index == 1:
                self._cycle_diff(1 if e.key == pygame.K_RIGHT else -1)
                self.game.audio.play("ui", 0.5)
                return
            if e.unicode and e.unicode.isdigit() and len(self.seed) < 9:
                self.seed += e.unicode
                self.game.audio.play("ui", 0.3)
                return
        self.menu.handle(e)

    def update(self, dt) -> None:
        self.menu.update(dt)

    def draw(self, surf) -> None:
        veil(surf, 210)
        from ..systems.items import DIFFICULTY
        self.menu.items[1] = (f"Difficulty: {DIFFICULTY[self.diff]['name']}", self._cycle_diff,
                              DIFFICULTY[self.diff]["desc"])
        r = pygame.Rect((config.SCREEN_W - 560) // 2, 170, 560, 470)
        panel(surf, r, color=(8, 14, 30, 240), border=GOLD)
        text(surf, "NEW VOYAGE" + (f"  ·  SLOT {self.slot + 1}" if self.slot is not None else ""),
             (r.centerx, r.y + 22), 26, GOLD, bold=True, anchor="midtop")
        text(surf, "Every seed is a different, infinite galaxy.", (r.centerx, r.y + 62), 15, (190, 205, 230),
             anchor="midtop")
        box = pygame.Rect(r.centerx - 140, r.y + 100, 280, 50)
        panel(surf, box, color=(4, 8, 20, 255), border=CYAN, radius=6)
        cursor = "_" if int(pygame.time.get_ticks() / 400) % 2 else " "
        text(surf, f"SEED  {self.seed}{cursor}", box.center, 22, (255, 255, 255), bold=True, anchor="center")
        text(surf, "type digits to choose a seed", (r.centerx, box.bottom + 8), 12, (140, 150, 180),
             anchor="midtop")
        if self.overwrite:
            text(surf, "Warning: this replaces your current save.", (r.centerx, box.bottom + 32), 14,
                 config.UI_WARN, bold=True, anchor="midtop")
        self.menu.draw(surf)


class SlotScene(Scene):
    """Three save slots: pick one to start a new game in, or to load."""
    is_overlay = True
    menu = True

    def __init__(self, game, mode: str):
        super().__init__(game)
        self.mode = mode
        self.index = min(game.settings.last_slot, SLOTS - 1)
        self.saves = [GameState.load(slot_path(i)) if slot_path(i).exists() else None for i in range(SLOTS)]

    def _rects(self):
        w = 340
        x0 = (config.SCREEN_W - (w * 3 + 40)) // 2
        return [pygame.Rect(x0 + i * (w + 20), 290, w, 260) for i in range(SLOTS)]

    def _pick(self, i):
        st = self.saves[i]
        if self.mode == "load":
            if st is None:
                self.game.audio.play("deny")
                return
            self.game.settings.last_slot = i
            self.game.select_save(slot_path(i))
            self.game.continue_game()
        else:
            self.game.scenes.pop()
            self.game.scenes.push(NewGameScene(self.game, overwrite=st is not None, slot=i))

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.game.scenes.pop()
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self.index = (self.index - 1) % SLOTS
                self.game.audio.play("ui", 0.4)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.index = (self.index + 1) % SLOTS
                self.game.audio.play("ui", 0.4)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                self._pick(self.index)
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self._rects()):
                if r.collidepoint(e.pos):
                    self.index = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._rects()):
                if r.collidepoint(e.pos):
                    self._pick(i)

    def draw(self, surf) -> None:
        from ..systems.quests import CHAPTERS
        veil(surf, 225)
        text(surf, "CHOOSE A SLOT" if self.mode == "new" else "LOAD GAME", (config.SCREEN_W // 2, 245), 30, GOLD,
             bold=True, anchor="center")
        for i, (r, st) in enumerate(zip(self._rects(), self.saves)):
            sel = i == self.index
            panel(surf, r, color=(16, 30, 56, 240) if sel else (8, 14, 30, 220), border=GOLD if sel else CYAN,
                  corners=sel)
            text(surf, f"SLOT {i + 1}", (r.x + 18, r.y + 16), 14, CYAN, bold=True)
            if st is None:
                text(surf, "Empty", (r.centerx, r.centery), 22, (150, 160, 185), anchor="center")
                text(surf, "Start a new voyage here" if self.mode == "new" else "", (r.centerx, r.centery + 30), 13,
                     (130, 140, 165), anchor="center")
                continue
            ch = CHAPTERS[min(st.chapter, len(CHAPTERS) - 1)]
            text(surf, ch["title"], (r.x + 18, r.y + 46), 20, (255, 235, 190), bold=True)
            rows = [f"Chapter {st.chapter + 1}  ·  {st.diff['name']}", f"Keys {len(st.relics)}/3  ·  "
                    f"Shards {len(st.shards)}/5", f"{st.credits:,} credits", f"{len(st.landed_planets)} worlds walked",
                    f"Played {fmt_time(st.play_time)}" + (f"  ·  NG+{st.ng_plus}" if st.ng_plus else ""),
                    f"Seed {st.seed}"]
            for j, line in enumerate(rows):
                text(surf, line, (r.x + 18, r.y + 82 + j * 26), 14, (200, 212, 232))
            if self.mode == "new":
                text(surf, "will be overwritten", (r.centerx, r.bottom - 16), 12, config.UI_WARN, anchor="midbottom")
        text(surf, "Left/Right choose  ·  Enter select  ·  Esc back", (config.SCREEN_W // 2, 570), 13,
             (140, 150, 180), anchor="midtop")


class KeybindScene(Scene):
    """Rebind any action. Enter, then press the new key."""
    is_overlay = True
    menu = True

    def __init__(self, game):
        super().__init__(game)
        self.index = 0
        self.waiting = False

    def _rows(self):
        from ..core.input import ACTIONS
        return list(ACTIONS) + [("reset", "Reset all to defaults", None), ("back", "Back", None)]

    def handle_event(self, e) -> None:
        from ..core.input import ACTION_DEFAULT
        rows = self._rows()
        if e.type != pygame.KEYDOWN:
            return
        s = self.game.settings
        if self.waiting:
            self.waiting = False
            if e.key == pygame.K_ESCAPE:
                return
            action = rows[self.index][0]
            binds = dict(s.bindings)
            old = binds.get(action, ACTION_DEFAULT[action])
            for a in ACTION_DEFAULT:   # swap with whoever had that key
                if binds.get(a, ACTION_DEFAULT[a]) == e.key and a != action:
                    binds[a] = old
            binds[action] = e.key
            s.bindings = {a: k for a, k in binds.items() if k != ACTION_DEFAULT[a]}
            self.game.input.rebuild_bindings()
            self.game.audio.play("relic", 0.4)
            return
        if e.key == pygame.K_ESCAPE:
            s.save()
            self.game.scenes.pop()
        elif e.key in (pygame.K_UP,):
            self.index = (self.index - 1) % len(rows)
        elif e.key in (pygame.K_DOWN,):
            self.index = (self.index + 1) % len(rows)
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            key = rows[self.index][0]
            if key == "back":
                s.save()
                self.game.scenes.pop()
            elif key == "reset":
                s.bindings = {}
                self.game.input.rebuild_bindings()
                self.game.toasts.add("Controls reset to defaults", config.UI_GOOD)
            else:
                self.waiting = True
                self.game.audio.play("ui", 0.6)

    def draw(self, surf) -> None:
        veil(surf, 210)
        rows = self._rows()
        f = pygame.Rect((config.SCREEN_W - 720) // 2, 40, 720, 640)
        panel(surf, f, color=(8, 14, 30, 245), border=GOLD)
        text(surf, "CONTROLS", (f.centerx, f.y + 14), 24, GOLD, bold=True, anchor="midtop")
        for i, (aid, label, _d) in enumerate(rows):
            y = f.y + 56 + i * 31
            sel = i == self.index
            r = pygame.Rect(f.x + 30, y, f.w - 60, 28)
            if sel:
                panel(surf, r, color=(24, 44, 76, 230), border=GOLD, radius=5, corners=False)
            text(surf, label, (r.x + 12, r.centery), 15, (255, 235, 190) if sel else (210, 220, 240), anchor="midleft")
            if aid not in ("reset", "back"):
                name = "press a key..." if (sel and self.waiting) else self.game.input.key_name(aid)
                text(surf, name, (r.right - 12, r.centery), 15, CYAN if not self.waiting or not sel else
                     config.UI_WARN, bold=True, anchor="midright")
        text(surf, "Up/Down choose  ·  Enter rebind  ·  Esc back", (f.centerx, f.bottom - 14), 12, (140, 150, 180),
             anchor="midbottom")


# -----------------------------------------------------------------------------
class SettingsScene(Scene):
    is_overlay = True
    menu = True

    SHAKE = [(0.0, "Off"), (0.5, "Reduced"), (1.0, "Full")]

    def __init__(self, game):
        super().__init__(game)
        self.index = 0

    def rows(self):
        s = self.game.settings
        shake = min(self.SHAKE, key=lambda x: abs(x[0] - s.shake))[1]
        return [
            ("Master volume", "slider", "master"),
            ("Music", "slider", "music"),
            ("Sound effects", "slider", "sfx"),
            ("Screen shake", shake, "shake"),
            ("Fullscreen", "On" if s.fullscreen else "Off", "fullscreen"),
            ("Control hints", "On" if s.show_hints else "Off", "show_hints"),
            ("Show FPS", "On" if s.show_fps else "Off", "show_fps"),
            ("Colour-blind signals", "On" if s.colorblind else "Off", "colorblind"),
            ("Rebind controls...", "", "keys"),
            ("Controls reference", "", "ref"),
            ("Back", "", "back"),
        ]

    def _change(self, key: str, d: int) -> None:
        s = self.game.settings
        if key in ("master", "music", "sfx"):
            setattr(s, key, round(max(0.0, min(1.0, getattr(s, key) + 0.1 * d)), 2))
        elif key == "shake":
            vals = [v for v, _ in self.SHAKE]
            i = min(range(3), key=lambda k: abs(vals[k] - s.shake))
            s.shake = vals[(i + d) % 3]
        elif key == "fullscreen":
            self.game.toggle_fullscreen()
        elif key in ("show_hints", "show_fps", "colorblind"):
            setattr(s, key, not getattr(s, key))
        elif key == "keys":
            self.game.scenes.push(KeybindScene(self.game))
            return
        elif key == "ref":
            self.game.scenes.push(ControlsScene(self.game))
            return
        elif key == "back":
            self._close()
            return
        self.game.apply_settings()
        self.game.audio.play("ui", 0.7)

    def _close(self):
        self.game.settings.save()
        self.game.scenes.pop()

    def _rects(self):
        r = self._frame()
        return [pygame.Rect(r.x + 30, r.y + 64 + i * 42, r.w - 60, 36) for i in range(len(self.rows()))]

    def _frame(self):
        return pygame.Rect((config.SCREEN_W - 620) // 2, 50, 620, 620)

    def handle_event(self, e) -> None:
        rows = self.rows()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self._close()
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(rows)
                self.game.audio.play("ui", 0.4)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(rows)
                self.game.audio.play("ui", 0.4)
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self._change(rows[self.index][2], -1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_SPACE):
                self._change(rows[self.index][2], 1)
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self._rects()):
                if r.collidepoint(e.pos):
                    self.index = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            for i, r in enumerate(self._rects()):
                if r.collidepoint(e.pos):
                    self.index = i
                    key = rows[i][2]
                    if rows[i][1] == "slider":
                        frac = (e.pos[0] - (r.right - 250)) / 230
                        if 0 <= frac <= 1.05:
                            setattr(self.game.settings, key, round(min(1.0, frac) * 10) / 10)
                            self.game.apply_settings()
                            return
                    self._change(key, 1 if e.button == 1 else -1)

    def draw(self, surf) -> None:
        veil(surf, 210)
        f = self._frame()
        panel(surf, f, color=(8, 14, 30, 240), border=GOLD)
        text(surf, "SETTINGS", (f.centerx, f.y + 22), 26, GOLD, bold=True, anchor="midtop")
        s = self.game.settings
        for i, ((label, val, key), r) in enumerate(zip(self.rows(), self._rects())):
            sel = i == self.index
            panel(surf, r, color=(24, 44, 76, 230) if sel else (10, 18, 32, 200),
                  border=GOLD if sel else (50, 70, 100), radius=6, corners=sel)
            if key in ("back", "keys", "ref"):
                text(surf, label, r.center, 17, (255, 235, 190) if sel else (210, 220, 240), bold=sel, anchor="center")
                continue
            text(surf, label, (r.x + 16, r.centery), 17, (255, 235, 190) if sel else (210, 220, 240), bold=sel,
                 anchor="midleft")
            if val == "slider":
                v = getattr(s, key)
                bar(surf, (r.right - 250, r.centery - 8, 230, 16), v, (120, 200, 255) if sel else (90, 150, 210))
                text(surf, f"{int(v * 100)}%", (r.right - 260, r.centery), 15, (200, 215, 240), anchor="midright")
            else:
                text(surf, f"<  {val}  >" if sel else val, (r.right - 20, r.centery), 17,
                     CYAN if sel else (190, 205, 230), bold=True, anchor="midright")
        text(surf, "Up/Down choose  ·  Left/Right change  ·  Esc back", (f.centerx, f.bottom - 18), 13,
             (140, 150, 180), anchor="midbottom")


# -----------------------------------------------------------------------------
def credits_lines(game) -> list[tuple[str, int, tuple]]:
    """(text, size, colour) rows used by the credits and the ending."""
    g, c, w = GOLD, CYAN, (225, 230, 245)
    return [
        ("STELLAR FORGE", 44, g), ("The Last Voyager", 22, c), ("", 30, w),
        ("ORIGINAL GAME, ART & STORY", 16, c), ("Omdeep Borkar", 24, w), ("", 24, w),
        ("PROGRAMMING", 16, c), ("Object-oriented engine, infinite galaxy,", 18, w),
        ("procedural worlds, music and Act II", 18, w), ("", 24, w),
        ("PROCEDURAL SYSTEMS", 16, c), ("Seeded sectors  ·  9 biomes  ·  numpy planet renderer", 18, w),
        ("scikit-learn planet model  ·  synthesised music & sound", 18, w), ("", 24, w),
        ("CAST", 16, c), ("The Voyager  ·  Commander Vey  ·  Ship AI", 18, w), ("The Warlord and his Remnant", 18, w),
        ("", 24, w), ("BUILT WITH", 16, c), ("Python  ·  Pygame  ·  NumPy  ·  scikit-learn  ·  OpenCV", 18, w),
        ("", 40, w), ("Thank you for playing.", 26, g), ("The galaxy never ends.", 18, c),
    ]


class CreditsScene(Scene):
    menu = True
    music = "ending"
    is_overlay = False

    def __init__(self, game):
        super().__init__(game)
        self.backdrop = Backdrop(game)
        self.y = config.SCREEN_H + 20
        self.lines = credits_lines(game)

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE) or \
                e.type == pygame.MOUSEBUTTONDOWN:
            self.game.scenes.pop()

    def update(self, dt) -> None:
        self.backdrop.update(dt)
        speed = 120 if self.game.input.pressed()[pygame.K_DOWN] else 45
        self.y -= speed * dt
        total = sum(sz + 18 for _, sz, _ in self.lines)
        if self.y < -total:
            self.y = config.SCREEN_H + 20

    def draw(self, surf) -> None:
        self.backdrop.draw(surf)
        veil(surf, 120)
        y = self.y
        for msg, size, col in self.lines:
            if msg and -60 < y < config.SCREEN_H + 60:
                text(surf, msg, (config.SCREEN_W // 2, y), size, col, bold=size >= 22, anchor="midtop")
            y += size + 18
        text(surf, "Esc back  ·  hold Down to speed up", (config.SCREEN_W - 14, config.SCREEN_H - 10), 13,
             (130, 140, 170), anchor="bottomright")


# -----------------------------------------------------------------------------
class PauseScene(Scene):
    is_overlay = True
    menu = True

    def __init__(self, game, allow_save: bool = True):
        super().__init__(game)
        items = [("Resume", self._resume), ("Logbook", self._logbook)]
        if allow_save:
            items.append(("Save game", self._save))
        items += [("Settings", self._settings), ("Controls", self._help), ("Save & quit to title", self._title)]
        self.menu = Menu(items, 250, game)

    def _resume(self):
        self.game.scenes.pop()

    def _logbook(self):
        from .logbook import LogbookScene
        self.game.scenes.push(LogbookScene(self.game))

    def _save(self):
        self.game.save()
        self.game.toasts.add("Game saved", config.UI_GOOD)

    def _settings(self):
        self.game.scenes.push(SettingsScene(self.game))

    def _help(self):
        self.game.scenes.push(ControlsScene(self.game))

    def _title(self):
        if self.game.state and self.game.state.hull > 0 and self.game.state.pilot_hp > 0:
            self.game.save()
        self.game.audio.loop("thrust", False)
        self.game.scenes.switch(TitleScene(self.game))

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self._resume()
            return
        self.menu.handle(e)

    def update(self, dt) -> None:
        self.menu.update(dt)

    def draw(self, surf) -> None:
        veil(surf, 205)
        from ..ui.text import theme
        rows = self.menu.rects()
        box = pygame.Rect(0, 0, self.menu.width + 120, rows[-1].bottom - 112 + 36)
        box.midtop = (config.SCREEN_W // 2, 112)
        theme().panel(surf, box)              # the menu sits in its own panel, clear of the game behind
        text(surf, "PAUSED", (config.SCREEN_W // 2, 170), 44, GOLD, bold=True, anchor="center")
        st = self.game.state
        if st:
            from ..systems.achievements import rank
            text(surf, f"{rank(st)}  ·  played {fmt_time(st.play_time)}  ·  Keys {len(st.relics)}/3"
                       + (f"  ·  Shards {len(st.shards)}/5" if st.boss_defeated else ""),
                 (config.SCREEN_W // 2, 210), 15, (180, 200, 230), anchor="center")
        self.menu.draw(surf)


class GameOverScene(Scene):
    menu = True
    music = "silence"

    def __init__(self, game, reason: str):
        super().__init__(game)
        self.reason = reason
        self.t = 0.0
        items = []
        if config.SAVE_FILE.exists():
            items.append(("Continue from last save", self._continue))
        items += [("New game", lambda: game.scenes.push(NewGameScene(game, overwrite=True))),
                  ("Title screen", lambda: game.scenes.switch(TitleScene(game)))]
        self.menu = Menu(items, 380, game, 420)
        self.embers = [[random.uniform(0, config.SCREEN_W), random.uniform(0, config.SCREEN_H),
                        random.uniform(10, 40), random.uniform(1, 3)] for _ in range(70)]

    def _continue(self):
        if not self.game.continue_game():
            self.game.new_game()

    def handle_event(self, e) -> None:
        if self.t > 0.8:
            self.menu.handle(e)

    def update(self, dt) -> None:
        self.t += dt
        self.menu.update(dt)
        for em in self.embers:
            em[1] -= em[2] * dt
            if em[1] < -5:
                em[1] = config.SCREEN_H + 5

    def draw(self, surf) -> None:
        surf.fill((14, 2, 6))
        for x, y, _s, r in self.embers:
            pygame.draw.circle(surf, (120, 30, 30), (x, y), r)
        k = min(1, self.t)
        text(surf, "MISSION FAILED", (config.SCREEN_W // 2, 220), 56, (int(255 * k), 70, 70), bold=True, anchor="center")
        text(surf, self.reason, (config.SCREEN_W // 2, 290), 20, (230, 200, 200), anchor="center")
        if self.t > 0.8:
            self.menu.draw(surf)
