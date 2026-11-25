"""Outposts: claim a world, build on it, and let it work while you're away.

Production runs on world time, so a drill keeps digging while you are
light-years away. Warp beacons link outposts (and Haven) into a fast-travel
network.
"""
from __future__ import annotations

import pygame

from .. import config
from ..core.scene import Scene
from ..ui.text import panel, text

CLAIM_COST = 400
DRILL_COST = [300, 650, 1100]
PUMP_COST = [250, 550, 950]
BEACON_COST = 900
WARP_FUEL = 40
GOLD = config.UI_GOLD


def produce(state, planet_id: str) -> tuple[int, int]:
    """Ore and fuel produced since the last visit (collected into the outpost)."""
    o = state.outposts.get(planet_id)
    if not o:
        return 0, 0
    dt = max(0.0, state.world_time - o.get("t", state.world_time))
    o["t"] = state.world_time
    d, pmp = o.get("drill", 0), o.get("pump", 0)
    o["ore"] = min(30 * d, o.get("ore", 0) + dt * d / 35)
    o["fuel"] = min(250 * pmp, o.get("fuel", 0) + dt * pmp * 1.2)
    return int(o["ore"]), int(o["fuel"])


def beacons(state) -> list[str]:
    return [pid for pid, o in state.outposts.items() if o.get("beacon")]


def warp_to(game, planet_id: str) -> None:
    st = game.state
    body = game.universe.find_body(planet_id)
    if body is None:
        return
    st.fuel = max(0.0, st.fuel - WARP_FUEL)
    game.audio.play("warp", 0.9)
    game.banner.show("Beacon jump", f"Arrived at {body.name}", 3.0)
    game.launch(body)


class WarpScene(Scene):
    """Pick a beacon to jump to (used by outposts and stations)."""
    is_overlay = True
    menu = True

    def __init__(self, game, exclude: str | None = None):
        super().__init__(game)
        st = game.state
        self.targets = [pid for pid in beacons(st) if pid != exclude]
        self.index = 0

    def handle_event(self, e) -> None:
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE or not self.targets:
            self.game.scenes.pop()
        elif e.key in (pygame.K_UP, pygame.K_w):
            self.index = (self.index - 1) % len(self.targets)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + 1) % len(self.targets)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            if self.game.state.fuel < WARP_FUEL:
                self.game.toasts.add(f"Beacon jumps need {WARP_FUEL} fuel", config.UI_DANGER)
                self.game.audio.play("deny")
                return
            pid = self.targets[self.index]
            self.game.scenes.pop()
            warp_to(self.game, pid)

    def draw(self, surf) -> None:
        v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        v.fill((0, 3, 12, 180))
        surf.blit(v, (0, 0))
        r = pygame.Rect((config.SCREEN_W - 560) // 2, 150, 560, 120 + max(1, len(self.targets)) * 50)
        panel(surf, r, color=(8, 14, 30, 240), border=(120, 220, 255))
        text(surf, "WARP NETWORK", (r.centerx, r.y + 18), 24, (140, 230, 255), bold=True, anchor="midtop")
        if not self.targets:
            text(surf, "No other beacons yet. Build one at an outpost.", (r.centerx, r.y + 80), 16,
                 (190, 200, 225), anchor="midtop")
            return
        st = self.game.state
        for i, pid in enumerate(self.targets):
            o = st.outposts[pid]
            rr = pygame.Rect(r.x + 24, r.y + 64 + i * 50, r.w - 48, 42)
            sel = i == self.index
            panel(surf, rr, color=(24, 44, 76, 230) if sel else (10, 18, 32, 200),
                  border=GOLD if sel else (50, 70, 100), radius=6, corners=sel)
            text(surf, f"{o.get('name', pid)}  ({o.get('biome', '?')})", (rr.x + 14, rr.centery), 17,
                 (255, 235, 190) if sel else (210, 220, 240), bold=sel, anchor="midleft")
            text(surf, f"{WARP_FUEL} fuel", (rr.right - 14, rr.centery), 15, (255, 210, 90), anchor="midright")
        text(surf, "Enter jump  ·  Esc cancel", (r.centerx, r.bottom - 12), 12, (140, 150, 180), anchor="midbottom")


class OutpostScene(Scene):
    is_overlay = True
    menu = True

    def __init__(self, game, planet):
        super().__init__(game)
        self.planet = planet
        self.index = 0
        ore, fuel = produce(game.state, planet.id)
        self.collected_msg = ""
        if ore or fuel:
            self._collect()

    @property
    def o(self):
        return self.game.state.outposts.get(self.planet.id)

    def _collect(self):
        st = self.game.state
        o = self.o
        ore, fuel = int(o.get("ore", 0)), int(o.get("fuel", 0))
        st.ore += ore
        if ore:
            self.game.events.emit("ore_collected", amount=ore)
        take = min(fuel, st.max_fuel - st.fuel)
        st.fuel += take
        o["ore"] = o.get("ore", 0) - ore
        o["fuel"] = o.get("fuel", 0) - take
        if ore or take:
            self.collected_msg = f"Collected {ore} ore and {int(take)} fuel"
            self.game.audio.play("pickup")

    def rows(self):
        o = self.o
        if not o:
            return [("Claim this world", f"Plant the Voyager's flag on {self.planet.name}", CLAIM_COST, self._claim),
                    ("Close", "", None, self._close)]
        out = []
        d, p = o.get("drill", 0), o.get("pump", 0)
        out.append((f"Mining drill  Lv {d}" + (" (MAX)" if d >= 3 else f" -> {d + 1}"),
                    f"Digs {d / 35 * 60:.1f} ore/min, stores up to {30 * d}" if d else "Digs ore while you're away",
                    None if d >= 3 else DRILL_COST[d], self._drill))
        out.append((f"Fuel pump  Lv {p}" + (" (MAX)" if p >= 3 else f" -> {p + 1}"),
                    f"Refines {p * 1.2 * 60:.0f} fuel/min, stores up to {250 * p}" if p else "Refines ship fuel",
                    None if p >= 3 else PUMP_COST[p], self._pump))
        if o.get("beacon"):
            out.append(("Warp network", f"Jump to another beacon ({WARP_FUEL} fuel)", None, self._warp))
        else:
            out.append(("Warp beacon", "Join the fast-travel network", BEACON_COST, self._beacon))
        out.append(("Close", "", None, self._close))
        return out

    def _pay(self, cost) -> bool:
        if self.game.state.spend(cost):
            self.game.audio.play("relic", 0.5)
            return True
        self.game.toasts.add("Not enough credits", config.UI_DANGER)
        self.game.audio.play("deny")
        return False

    def _claim(self):
        if self._pay(CLAIM_COST):
            st = self.game.state
            st.outposts[self.planet.id] = {"t": st.world_time, "drill": 0, "pump": 0, "beacon": False,
                                          "name": self.planet.name, "biome": self.planet.biome.name}
            self.game.banner.show(f"Outpost founded on {self.planet.name}", "Build drills, pumps and a warp beacon")
            self.game.save()

    def _drill(self):
        o = self.o
        if o["drill"] < 3 and self._pay(DRILL_COST[o["drill"]]):
            produce(self.game.state, self.planet.id)
            o["drill"] += 1

    def _pump(self):
        o = self.o
        if o["pump"] < 3 and self._pay(PUMP_COST[o["pump"]]):
            produce(self.game.state, self.planet.id)
            o["pump"] += 1

    def _beacon(self):
        if self._pay(BEACON_COST):
            self.o["beacon"] = True
            self.game.toasts.add("Warp beacon online", (140, 230, 255))

    def _warp(self):
        self.game.scenes.pop()
        self.game.scenes.push(WarpScene(self.game, exclude=self.planet.id))

    def _close(self):
        self.game.save()
        self.game.scenes.pop()

    def handle_event(self, e) -> None:
        rows = self.rows()
        if e.type != pygame.KEYDOWN:
            return
        if e.key in (pygame.K_ESCAPE, pygame.K_o):
            self._close()
        elif e.key in (pygame.K_UP, pygame.K_w):
            self.index = (self.index - 1) % len(rows)
            self.game.audio.play("ui", 0.4)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + 1) % len(rows)
            self.game.audio.play("ui", 0.4)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            rows[min(self.index, len(rows) - 1)][3]()

    def draw(self, surf) -> None:
        v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        v.fill((0, 3, 12, 170))
        surf.blit(v, (0, 0))
        st = self.game.state
        rows = self.rows()
        self.index = min(self.index, len(rows) - 1)
        r = pygame.Rect((config.SCREEN_W - 700) // 2, 120, 700, 150 + len(rows) * 58)
        panel(surf, r, color=(8, 14, 30, 240), border=GOLD)
        hab = self.game.assets.image("generated/outposts/hab.png", scale=0.6)
        surf.blit(hab, (r.x + 22, r.y + 16))
        text(surf, f"OUTPOST · {self.planet.name}", (r.x + 120, r.y + 20), 24, GOLD, bold=True)
        sub = self.collected_msg or (f"{self.planet.biome.name} world" if self.o else "Unclaimed world")
        text(surf, sub, (r.x + 120, r.y + 54), 15, (150, 255, 190) if self.collected_msg else (180, 195, 225))
        if self.o:
            text(surf, f"Stored: {int(self.o.get('ore', 0))} ore · {int(self.o.get('fuel', 0))} fuel",
                 (r.right - 24, r.y + 24), 14, (200, 215, 240), anchor="topright")
        text(surf, f"{st.credits:,} cr", (r.right - 24, r.y + 50), 16, (255, 230, 140), bold=True, anchor="topright")
        for i, (label, detail, cost, _fn) in enumerate(rows):
            rr = pygame.Rect(r.x + 24, r.y + 92 + i * 58, r.w - 48, 50)
            sel = i == self.index
            panel(surf, rr, color=(24, 44, 76, 230) if sel else (10, 18, 32, 210),
                  border=GOLD if sel else (50, 70, 100), radius=6, corners=sel)
            text(surf, label, (rr.x + 14, rr.y + 7), 17, (255, 240, 200) if sel else (220, 230, 245), bold=True)
            if detail:
                text(surf, detail, (rr.x + 14, rr.y + 29), 13, (170, 190, 220))
            if cost:
                text(surf, f"{cost} cr", (rr.right - 14, rr.centery), 17,
                     config.UI_GOOD if st.credits >= cost else config.UI_DANGER, bold=True, anchor="midright")
        text(surf, "Up/Down select  ·  Enter build  ·  Esc close", (r.centerx, r.bottom - 12), 12,
             (130, 140, 170), anchor="midbottom")
