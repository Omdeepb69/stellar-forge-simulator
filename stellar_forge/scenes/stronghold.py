"""Top-down stronghold: memorise the glyph sequence, pick the right doors,
dodge the sentinel orbs, claim the Key (or an ancient cache)."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from ..core.game_state import RELIC_BIOMES, SHARD_NAMES
from ..core.scene import Scene
from ..systems.particles import ParticleSystem
from ..ui import hud
from ..ui.text import panel, text
from ..world.rng import rng_of

ROOM_SETS = {
    "desert": ("stronghold/desert_st/desertRoom.png", "stronghold/desert_st/desertRoomItemTable.png",
               "stronghold/desert_st/desertRoomRock.png", "stronghold/desert_st/desertItem.png"),
    "forest": ("stronghold/forest_st/forestRoom.png", "stronghold/forest_st/forestRoomTable.png",
               "stronghold/forest_st/forestRoomRock.png", "stronghold/forest_st/forestItem.png"),
    "ice": ("stronghold/icy_st/snowyRoom.png", "stronghold/icy_st/SnowyRoomItemTable.png",
            "stronghold/icy_st/snowyRoomRock.png", "stronghold/icy_st/snowyItem.png"),
}
ARROWS = {"t": "UP", "l": "LEFT", "r": "RIGHT", "b": "DOWN"}
OPPOSITE = {"t": "b", "b": "t", "l": "r", "r": "l"}
ROOM = 660


class StrongholdScene(Scene):
    music = "stronghold"

    def __init__(self, game, planet, looted: bool):
        super().__init__(game)
        self.planet = planet
        self.biome = planet.biome_id
        self.looted = looted
        self.relic = self.biome in RELIC_BIOMES and self.biome not in game.state.relics
        st = game.state
        self.shard = planet.shard if (planet.shard and st.boss_defeated and planet.shard not in st.shards) else None
        if self.shard:
            self.looted = looted = False   # the Shard vault opens only in Act II
        rng = rng_of(planet.seed, "stronghold")
        sx, sy = planet.sector
        danger = game.universe.danger_at(sx, sy)
        length = 4 + (0 if self.relic else min(3, int(danger / 2)))
        if self.shard:
            length = 6
        self.sequence = [rng.choice("tlrb") for _ in range(length)]
        for i in range(1, length):  # avoid trivially repeating doors
            while self.sequence[i] == OPPOSITE.get(self.sequence[i - 1]) and rng.random() < 0.5:
                self.sequence[i] = rng.choice("tlrb")
        self.step = 0
        self.room_rect = pygame.Rect((config.SCREEN_W - ROOM) // 2, (config.SCREEN_H - ROOM) // 2, ROOM, ROOM)
        self.inner = self.room_rect.inflate(-150, -150)
        self.pos = Vector2(self.room_rect.centerx, self.room_rect.centery + 90)
        self.speed = 260
        self.facing = 0.0
        self.reveal_t = 0.0
        self.revealed_once = False
        self.orbs: list[list] = []
        self.complete = looted
        self.item_taken = looted
        self.exit_t = -1.0
        self.door_cool = 1.0
        self.clock = 0.0
        self.particles = ParticleSystem(300)
        self.hurt_cool = 0.0
        self.flash = 0.0

        key = self.biome if self.biome in ROOM_SETS else random.Random(planet.seed).choice(list(ROOM_SETS))
        room, table, rock, item = ROOM_SETS[key]
        tint = None if self.biome in ROOM_SETS else planet.biome.ground_top
        a = game.assets
        self.room_img = a.image(room, size=(ROOM, ROOM), tint=tint)
        self.table_img = a.image(table, size=(120, 120), tint=tint)
        self.rock_img = a.image(rock, size=(90, 90), tint=tint)
        if self.shard:
            self.item_img = a.image(f"generated/items/shard_{self.shard}.png", size=(54, 70))
        elif self.relic:
            self.item_img = a.image(item, size=(64, 64))
        else:
            self.item_img = a.image("stronghold/device.png", size=(64, 64))
        self.player_img = a.image("stronghold/mainCharTopView.png", crop=True, scale=3.0)
        self.device_img = a.image("stronghold/device.png", crop=True, scale=2.2)
        self.orb_img = a.image("finalboss/orb.png", size=(36, 36), tint=(255, 120, 120))
        self.device_pos = Vector2(self.inner.left + 50, self.inner.top + 50)
        self._spawn_orbs()

    @property
    def doors(self) -> dict[str, pygame.Rect]:
        r = self.room_rect
        d = 96
        return {
            "t": pygame.Rect(r.centerx - d / 2, r.top + 40, d, 50),
            "b": pygame.Rect(r.centerx - d / 2, r.bottom - 90, d, 50),
            "l": pygame.Rect(r.left + 40, r.centery - d / 2, 50, d),
            "r": pygame.Rect(r.right - 90, r.centery - d / 2, 50, d),
        }

    def on_enter(self) -> None:
        if self.shard:
            self.game.dialogue.say([("ai", f"The {SHARD_NAMES[self.shard]} is in here. This lock is older and "
                                           "meaner - six seals and restless sentinels. Read the terminal [E].")])
        elif self.looted:
            self.game.toasts.add("The vault is empty. Only dust remains.", (200, 200, 200))
        else:
            self.game.dialogue.say([("ai", "Ancient lock detected. Read the glyph terminal [E], then walk "
                                           "through the doors in that order. Wrong door = trap.")])

    # ------------------------------------------------------------------
    def _spawn_orbs(self) -> None:
        self.orbs = []
        if self.complete:
            return
        n = 1 + self.step + (1 if not self.relic else 0) + (1 if self.shard else 0)
        fast = 40 if self.shard else 0
        for _ in range(n):
            p = Vector2(random.uniform(self.inner.left, self.inner.right), random.uniform(self.inner.top, self.inner.centery))
            v = Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(150 + fast, 230 + fast + self.step * 20)
            self.orbs.append([p, v])

    def handle_event(self, e) -> None:
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            from .menus import PauseScene
            self.game.scenes.push(PauseScene(self.game))
        elif e.key == pygame.K_q:
            self.leave()
        elif e.key == pygame.K_e:
            if not self.complete and self.pos.distance_to(self.device_pos) < 90:
                self.reveal_t = 2.6 + len(self.sequence) * 0.35
                self.revealed_once = True
                self.game.audio.play("discover", 0.5)
        elif e.key == pygame.K_h:
            st = self.game.state
            if st.medkits <= 0:
                self.game.toasts.add("No medkits left", config.UI_WARN, 1.4)
                self.game.audio.play("deny", 0.5)
            elif st.pilot_hp >= st.max_pilot_hp - 0.5:
                self.game.toasts.add("Health is already full", (180, 220, 200), 1.3)
                self.game.audio.play("deny", 0.4)
            else:
                st.medkits -= 1
                amt = max(config.MEDKIT_HEAL, st.max_pilot_hp * 0.45)
                healed = min(st.max_pilot_hp - st.pilot_hp, amt)
                st.pilot_hp = min(st.max_pilot_hp, st.pilot_hp + amt)
                self.game.audio.play("pickup", 0.8)
                self.particles.burst(self.pos.x, self.pos.y, 24, 200,
                                     [(110, 255, 160), (180, 255, 220), (110, 230, 255)], life=(0.3, 0.8))
                self.game.toasts.add(f"+{healed:.0f} HP", (120, 255, 160), 1.4, icon="medkit")

    def leave(self) -> None:
        self.game.scenes.pop(fade=True)

    # ------------------------------------------------------------------
    def update(self, dt) -> None:
        self.clock += dt
        st = self.game.state
        keys = self.game.input.pressed()
        move = Vector2((keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
                       (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]))
        if move.length_squared() > 0:
            move = move.normalize()
            self.facing = math.degrees(math.atan2(move.x, -move.y))
        self.pos += move * self.speed * dt
        self.pos.x = max(self.inner.left - 50, min(self.inner.right + 50, self.pos.x))
        self.pos.y = max(self.inner.top - 50, min(self.inner.bottom + 50, self.pos.y))
        self.reveal_t = max(0.0, self.reveal_t - dt)
        self.door_cool = max(0.0, self.door_cool - dt)
        self.hurt_cool = max(0.0, self.hurt_cool - dt)
        self.flash = max(0.0, self.flash - dt)
        self.particles.update(dt)

        # sentinel orbs
        for orb in self.orbs:
            p, v = orb
            p += v * dt
            if p.x < self.inner.left - 40 or p.x > self.inner.right + 40:
                v.x *= -1
            if p.y < self.inner.top - 40 or p.y > self.inner.bottom + 40:
                v.y *= -1
            p.x = max(self.inner.left - 40, min(self.inner.right + 40, p.x))
            p.y = max(self.inner.top - 40, min(self.inner.bottom + 40, p.y))
            if p.distance_to(self.pos) < 38 and self.hurt_cool <= 0:
                self._hurt(12, (self.pos - p))

        # doors
        if not self.complete and self.door_cool <= 0:
            pr = pygame.Rect(self.pos.x - 20, self.pos.y - 20, 40, 40)
            for d, rect in self.doors.items():
                if pr.colliderect(rect):
                    self._through_door(d)
                    break

        # reward
        if self.complete and not self.item_taken:
            if self.pos.distance_to(Vector2(self.room_rect.center)) < 60:
                self._take_reward()
        if self.complete and self.item_taken:
            if pygame.Rect(self.pos.x - 20, self.pos.y - 20, 40, 40).colliderect(self.doors["b"]):
                self.leave()

        if st.pilot_hp <= 0:
            self.game.game_over(f"The stronghold on {self.planet.name} claimed you.")

    def _hurt(self, dmg, away: Vector2) -> None:
        st = self.game.state
        st.pilot_hp = max(0.0, st.pilot_hp - dmg)
        self.hurt_cool = 0.8
        self.flash = 0.3
        if away.length_squared() > 0:
            self.pos += away.normalize() * 40
        self.game.audio.play("hit")
        self.particles.burst(self.pos.x, self.pos.y, 10, 160, [(255, 90, 90), (255, 200, 120)])

    def _through_door(self, d: str) -> None:
        self.door_cool = 0.6
        if d == self.sequence[self.step]:
            self.step += 1
            self.game.audio.play("ui", 0.8)
            self.particles.burst(self.pos.x, self.pos.y, 18, 200, [(255, 220, 120), (255, 255, 255)])
            if self.step >= len(self.sequence):
                self.complete = True
                self.orbs = []
                self.game.audio.play("relic", 0.7)
                self.game.toasts.add("The final seal opens!", (255, 220, 120))
            else:
                self.game.toasts.add(f"Seal {self.step}/{len(self.sequence)} unlocked", (255, 220, 120), 1.5)
                self._spawn_orbs()
        else:
            self.step = 0
            self._spawn_orbs()
            self._hurt(15, Vector2())
            self.game.toasts.add("Wrong door! The seals reset.", config.UI_DANGER, 2)
            self.game.shake(10)
        # emerge from the opposite door
        r = self.room_rect
        opp = OPPOSITE[d]
        self.pos = Vector2({"t": (r.centerx, r.top + 140), "b": (r.centerx, r.bottom - 140),
                            "l": (r.left + 140, r.centery), "r": (r.right - 140, r.centery)}[opp])

    def _take_reward(self) -> None:
        st = self.game.state
        self.item_taken = True
        st.mark("looted_strongholds", self.planet.id)
        c = Vector2(self.room_rect.center)
        self.particles.burst(c.x, c.y, 50, 260, [(255, 230, 120), (255, 255, 255), (140, 230, 255)], life=(0.5, 1.4))
        if self.shard:
            self.game.events.emit("shard_collected", biome=self.shard)
        elif self.relic:
            self.game.events.emit("relic_collected", biome=self.biome)
        else:
            sx, sy = self.planet.sector
            amount = int(180 * self.game.universe.danger_at(sx, sy))
            st.earn(amount)
            st.ore += 6
            st.scan_data += 4
            self.game.banner.show("Ancient cache", f"+{amount} cr, +6 ore, +4 data")
            self.game.audio.play("relic", 0.6)
        self.game.save()

    # ------------------------------------------------------------------
    def draw(self, surf) -> None:
        surf.fill((8, 6, 12))
        surf.blit(self.room_img, self.room_rect)
        r = self.room_rect
        # seal lights
        n = len(self.sequence)
        for i in range(n):
            x = r.centerx - (n - 1) * 18 + i * 36
            lit = i < self.step or self.complete
            pygame.draw.circle(surf, (255, 220, 120) if lit else (60, 50, 40), (x, r.top + 18), 10)
            pygame.draw.circle(surf, (20, 16, 10), (x, r.top + 18), 10, 2)
        if self.complete:
            surf.blit(self.rock_img, self.rock_img.get_rect(center=(r.left + 150, r.top + 160)))
            surf.blit(self.rock_img, self.rock_img.get_rect(center=(r.right - 150, r.bottom - 170)))
            surf.blit(self.table_img, self.table_img.get_rect(center=r.center))
            if not self.item_taken:
                bob = math.sin(self.clock * 3) * 6
                surf.blit(self.item_img, self.item_img.get_rect(center=(r.centerx, r.centery - 20 + bob)))
            # exit marker
            dr = self.doors["b"]
            pygame.draw.rect(surf, (120, 255, 150), dr, 3, border_radius=6)
        else:
            surf.blit(self.device_img, self.device_img.get_rect(center=self.device_pos))
            if self.pos.distance_to(self.device_pos) < 90:
                text(surf, "[E] read glyphs", (self.device_pos.x, self.device_pos.y - 48), 14, (160, 255, 180),
                     anchor="center")
            for d, rect in self.doors.items():
                glow = 0.5 + 0.5 * math.sin(self.clock * 3 + "tlrb".index(d))
                pygame.draw.rect(surf, (int(120 + 80 * glow), 90, 255), rect, 2, border_radius=6)
        for p, _v in self.orbs:
            surf.blit(self.orb_img, self.orb_img.get_rect(center=p))
        img = pygame.transform.rotate(self.player_img, -self.facing)
        if self.flash > 0:
            img = img.copy()
            img.fill((200, 0, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(img, img.get_rect(center=self.pos))
        self.particles.draw(surf, lambda pt: pt)

        hud.pilot_status(surf, self.game, 1.0)
        hud.relic_slots(surf, self.game)
        # glyph reveal
        if self.reveal_t > 0:
            panel(surf, (config.SCREEN_W // 2 - 300, config.SCREEN_H - 120, 600, 80), border=(160, 255, 180))
            seq = "  ->  ".join(ARROWS[d] for d in self.sequence)
            text(surf, "GLYPH SEQUENCE", (config.SCREEN_W // 2, config.SCREEN_H - 104), 14, (160, 255, 180),
                 anchor="center", bold=True)
            text(surf, seq, (config.SCREEN_W // 2, config.SCREEN_H - 72), 22, (255, 255, 255), anchor="center",
                 bold=True)
        side_x = 20
        title = f"{self.planet.name} Shard vault" if self.shard else self.planet.name + " stronghold"
        text(surf, title, (side_x, 110), 18, config.UI_VIOLET if self.shard else (255, 220, 150), bold=True)
        if self.complete and not self.item_taken:
            text(surf, "Claim the treasure!", (side_x, 140), 15, (255, 230, 140))
        elif self.complete:
            text(surf, "Exit through the green door", (side_x, 140), 15, (150, 255, 170))
        else:
            text(surf, f"Seals: {self.step}/{len(self.sequence)}", (side_x, 140), 15)
            text(surf, "Remember the order!" if self.revealed_once else "Read the terminal first",
                 (side_x, 164), 14, (190, 200, 230))
        text(surf, "WASD/arrows move   E read glyphs   H heal   Q leave", (config.SCREEN_W // 2, config.SCREEN_H - 6), 12,
             (140, 140, 170), anchor="midbottom")
