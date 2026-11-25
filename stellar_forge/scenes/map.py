"""Galaxy map (sector view) + local system view."""
from __future__ import annotations

import pygame
from pygame.math import Vector2

from .. import config
from ..core.scene import Scene
from ..ui.text import panel, text
from ..world.universe import Universe


class MapScene(Scene):
    is_overlay = True
    menu = True

    def __init__(self, game, space):
        super().__init__(game)
        self.space = space
        self.radius = 4
        self.pan = Vector2()
        self._down = None
        self._view = None    # (origin, cell, cx, cy, area)

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_m):
            self.game.scenes.pop()
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_EQUALS, pygame.K_PLUS):
            self.radius = max(2, self.radius - 1)
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_MINUS:
            self.radius = min(9, self.radius + 1)
        elif e.type == pygame.MOUSEWHEEL:
            self.radius = max(2, min(9, self.radius - e.y))
        elif e.type == pygame.MOUSEMOTION and e.buttons[0]:
            self.pan += Vector2(e.rel)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            self._down = Vector2(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button in (1, 3) and self._down is not None:
            if Vector2(e.pos).distance_to(self._down) < 6 and self._view and self._view[4].collidepoint(e.pos):
                if e.button == 3:
                    self.game.state.waypoint = None
                    self.game.toasts.add("Waypoint cleared", (200, 220, 255), 1.5)
                else:
                    self.set_waypoint(e.pos)
            self._down = None
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_p:
            self.game.scenes.pop()
            self.space.toggle_autopilot()

    def set_waypoint(self, screen_pos) -> None:
        origin, cell, cx, cy, _area = self._view
        world = ((Vector2(screen_pos) - origin) / cell + Vector2(cx + 0.5, cy + 0.5)) * config.SECTOR_SIZE
        u, st = self.game.universe, self.game.state
        label = "Waypoint"
        sx, sy = Universe.sector_coords(world)
        sec = u.sector(sx, sy)
        if sec.has_system and (world - sec.system_center).length() < config.SECTOR_SIZE * 0.3:
            world = Vector2(sec.system_center)
            label = f"{sec.name} system" if sec.key in st.discovered_systems else "Unknown system"
        st.waypoint = [world.x, world.y, label]
        self.space.autopilot = None
        self.game.toasts.add(f"Waypoint set: {label}  ([P] autopilot)", (90, 230, 160), 2.5)
        self.game.audio.play("ui", 0.8)

    def draw(self, surf) -> None:
        veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        veil.fill((2, 4, 12, 248))
        surf.blit(veil, (0, 0))
        self._galaxy(surf, pygame.Rect(30, 60, 700, 620))
        self._system(surf, pygame.Rect(750, 60, 500, 620))
        text(surf, "GALAXY MAP", (30, 20), 26, (255, 225, 150), bold=True)
        text(surf, "click: set waypoint  ·  right-click: clear  ·  P: autopilot  ·  wheel zoom  ·  drag pan  ·  "
                   "M / Esc close", (config.SCREEN_W - 30, 28), 13, (150, 160, 190), anchor="topright")

    def _galaxy(self, surf, area: pygame.Rect) -> None:
        panel(surf, area)
        g, st = self.game, self.game.state
        u = g.universe
        ship = self.space.ship.pos
        cx, cy = Universe.sector_coords(ship)
        R = self.radius
        cell = min(area.w, area.h) / (2 * R + 1)
        origin = Vector2(area.center) + self.pan
        clip = surf.get_clip()
        surf.set_clip(area.inflate(-4, -4))

        def to_map(p):
            rel = (Vector2(p) / config.SECTOR_SIZE) - Vector2(cx + 0.5, cy + 0.5)
            return origin + rel * cell

        budget = [10]                      # new sectors generated per frame: the map fills in, never stalls

        def get(sx, sy):
            sec = u.peek(sx, sy)
            if sec is None and budget[0] > 0:
                budget[0] -= 1
                sec = u.sector(sx, sy)
            return sec
        for dy in range(-R - 1, R + 2):
            for dx in range(-R - 1, R + 2):
                sx, sy = cx + dx, cy + dy
                tl = to_map((sx * config.SECTOR_SIZE, sy * config.SECTOR_SIZE))
                pygame.draw.rect(surf, (22, 30, 52), (tl.x, tl.y, cell, cell), 1)
                if max(abs(dx), abs(dy)) > R:
                    continue
                sec = get(sx, sy)
                if sec is None:
                    continue
                known = sec.key in st.discovered_systems
                near = max(abs(dx), abs(dy)) <= 1 + st.lvl("scanner") // 2
                if sec.has_system and (known or near):
                    p = to_map(sec.system_center)
                    col = sec.star.color if known else (90, 90, 110)
                    pygame.draw.circle(surf, col, p, max(3, cell * 0.07))
                    if known and cell > 50:
                        text(surf, sec.name, (p.x, p.y + 8), 11, (190, 200, 230), anchor="midtop")
                    relic = [pl for pl in sec.planets if pl.stronghold and pl.biome_id in g.quests.missing_relics()
                             and pl.id not in st.looted_strongholds]
                    if relic and (known or near) and g.quests.cid == "keys":
                        pygame.draw.circle(surf, (255, 210, 90), p, max(6, cell * 0.12), 2)
                    if sec.stations and known:
                        pygame.draw.rect(surf, (120, 220, 255), (p.x + 6, p.y - 10, 5, 5))
                for h in sec.hazards:
                    if known or near:
                        pygame.draw.circle(surf, h.map_color(), to_map(h.pos(st.world_time)), 3)
                for w in sec.wormholes:
                    if near:
                        pygame.draw.circle(surf, (190, 110, 255), to_map(w.center), 4, 1)
                for n in sec.nebulae:
                    if near or known:
                        pygame.draw.circle(surf, n.color, to_map(n.center), max(2, n.radius / config.SECTOR_SIZE * cell), 1)
        if st.boss_defeated:  # Act II: Shard vaults are always on the map
            for (sx, sy), biome in u.shard_sites.items():
                if biome in st.shards:
                    continue
                p = to_map(((sx + 0.5) * config.SECTOR_SIZE, (sy + 0.5) * config.SECTOR_SIZE))
                r = max(7, cell * 0.12)
                pts = [(p.x, p.y - r), (p.x + r * 0.7, p.y), (p.x, p.y + r), (p.x - r * 0.7, p.y)]
                pygame.draw.polygon(surf, config.UI_VIOLET, pts, 2)
                text(surf, biome.title(), (p.x, p.y + r + 2), 11, config.UI_VIOLET, anchor="midtop")
        self._view = (origin, cell, cx, cy, area)
        from ..systems import saga as S                     # Act III waystones and the New Dawn
        if g.quests.cid in ("road", "judgment", "legend"):
            for kind in S.WAYSTONES:
                p = to_map(S.waystone_pos(u, kind))
                done = kind in S.data(st)["waystones"]
                col = (110, 120, 130) if done else S.WAY_INFO[kind][2]
                pygame.draw.circle(surf, col, p, max(6, cell * 0.1), 2)
                text(surf, kind.title(), (p.x, p.y + 10), 11, col, anchor="midtop")
        if S.data(st).get("ark") == "known":
            p = to_map(S.ark_pos(u))
            pygame.draw.rect(surf, (255, 220, 150), (p.x - 5, p.y - 5, 10, 10), 2)
            text(surf, "New Dawn?", (p.x, p.y + 8), 11, (255, 220, 150), anchor="midtop")
        t = st.world_time
        for dy in range(-R, R + 1):          # derelicts and outposts
            for dx in range(-R, R + 1):
                sec = u.peek(cx + dx, cy + dy)
                if sec is None:
                    continue
                near = max(abs(dx), abs(dy)) <= 1 + st.lvl("scanner") // 2
                for d in sec.derelicts:
                    if near or d.id in st.derelicts_looted:
                        p = to_map(d.pos(t))
                        pygame.draw.rect(surf, (170, 170, 185) if d.id not in st.derelicts_looted else (90, 90, 100),
                                         (p.x - 3, p.y - 3, 7, 7), 1)
        for pid, o in st.outposts.items():
            body = u.find_body(pid)
            if body is not None:
                p = to_map(body.pos(t))
                pygame.draw.circle(surf, (255, 220, 140), p, 5, 2)
                if cell > 40:
                    text(surf, o.get("name", ""), (p.x, p.y - 7), 10, (255, 220, 140), anchor="midbottom")
        if st.ending and not st.signal_found:
            from ..systems.quests import signal_position
            p = to_map(signal_position(u))
            pygame.draw.circle(surf, (90, 240, 220), p, 9, 2)
            text(surf, "???", (p.x, p.y - 12), 12, (90, 240, 220), anchor="midbottom")
        if st.waypoint:
            p = to_map((st.waypoint[0], st.waypoint[1]))
            pygame.draw.line(surf, (90, 230, 160), to_map(ship), p, 1)
            surf.blit(self.game.assets.image("generated/ui/icons/waypoint.png", size=(22, 22)), (p.x - 6, p.y - 20))
        sp = to_map(ship)
        fwd = self.space.ship.forward
        pygame.draw.polygon(surf, (255, 255, 255), [sp + fwd * 9, sp + fwd.rotate(140) * 7, sp + fwd.rotate(-140) * 7])
        if cell <= 50:
            home = to_map(u.sector(0, 0).system_center)
            text(surf, "Haven", (home.x, home.y - 10), 12, (255, 230, 160), anchor="midbottom")
        surf.set_clip(clip)
        text(surf, f"Sector {cx},{cy}  ·  danger {u.sector(cx, cy).danger:.1f}  ·  "
                   f"{len(st.discovered_systems)} systems charted", (area.x + 12, area.bottom - 24), 13,
             (170, 190, 220))

    def _system(self, surf, area: pygame.Rect) -> None:
        panel(surf, area)
        sys_ = self.space.system
        t = self.game.state.world_time
        if sys_ is None:
            text(surf, "Deep space", (area.centerx, area.centery), 20, (160, 170, 200), anchor="center")
            text(surf, "No star system in range", (area.centerx, area.centery + 30), 14, (120, 130, 160), anchor="center")
            return
        text(surf, f"{sys_.name} system", (area.x + 16, area.y + 12), 20, sys_.star.color, bold=True)
        text(surf, f"{sys_.star.spectral}-class star", (area.x + 16, area.y + 38), 13, (170, 180, 210))
        c = Vector2(area.centerx, area.centery - 40)
        scale = (min(area.w, area.h) / 2 - 50) / max(1, sys_.system_radius - 1500)
        center = sys_.star.pos(t)
        pygame.draw.circle(surf, sys_.star.color, c, 8)
        st = self.game.state
        y = area.bottom - 190
        listed = 0
        for p in sys_.planets:
            if p.is_moon:
                continue
            pygame.draw.circle(surf, (40, 50, 80), c, p.orbit_r * scale, 1)
            pp = c + (p.pos(t) - center) * scale
            pygame.draw.circle(surf, p.map_color(), pp, max(3, p.radius * scale * 3))
            if p.stronghold and p.id not in st.looted_strongholds:
                pygame.draw.circle(surf, (255, 210, 90), pp, 9, 1)
            if listed < 8:
                mark = " *" if p.stronghold and p.id not in st.looted_strongholds else ""
                visited = "  (visited)" if p.id in st.landed_planets else ""
                text(surf, f"{p.name}: {p.biome.name}{mark}{visited}", (area.x + 16, y + listed * 20), 13,
                     p.map_color())
                listed += 1
        for s in sys_.stations:
            sp = c + (s.pos(t) - center) * scale
            pygame.draw.rect(surf, s.color, (sp.x - 3, sp.y - 3, 6, 6))
        shp = c + (self.space.ship.pos - center) * scale
        if area.collidepoint(shp):
            pygame.draw.circle(surf, (255, 255, 255), shp, 4)
        text(surf, "* ancient signal", (area.right - 16, area.bottom - 22), 12, (255, 210, 90), anchor="topright")
