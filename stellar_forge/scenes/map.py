"""Galaxy map (sector astrogation console) + local system orrery inspector."""
from __future__ import annotations

import pygame
from pygame.math import Vector2

from .. import config
from ..core.scene import Scene
from ..ui.text import panel, text, theme
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
        self._hover_sec = None
        self._clear_btn: pygame.Rect | None = None
        self._center_btn: pygame.Rect | None = None

    def _clear_waypoint(self) -> None:
        if self.game.state.waypoint is None:
            return
        self.game.state.waypoint = None
        self.space.autopilot = None
        self.game.toasts.add("Waypoint cleared", (200, 220, 255), 1.5)
        self.game.audio.play("ui", 0.6)

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_m):
            self.game.scenes.pop()
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_EQUALS, pygame.K_PLUS):
            self.radius = max(2, self.radius - 1)
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_MINUS:
            self.radius = min(9, self.radius + 1)
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_h, pygame.K_HOME):
            self.pan = Vector2()
            self.game.audio.play("ui", 0.5)
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_x, pygame.K_BACKSPACE, pygame.K_DELETE):
            self._clear_waypoint()
        elif e.type == pygame.MOUSEWHEEL:
            self.radius = max(2, min(9, self.radius - e.y))
        elif e.type == pygame.MOUSEMOTION:
            if e.buttons[0]:
                self.pan += Vector2(e.rel)
            self._update_hover(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            self._down = Vector2(e.pos)
        elif e.type == pygame.MOUSEBUTTONUP and e.button in (1, 3) and self._down is not None:
            if Vector2(e.pos).distance_to(self._down) < 6:
                if e.button == 1 and self._clear_btn and self._clear_btn.collidepoint(e.pos):
                    self._clear_waypoint()
                elif e.button == 1 and self._center_btn and self._center_btn.collidepoint(e.pos):
                    self.pan = Vector2()
                    self.game.audio.play("ui", 0.5)
                elif self._view and self._view[4].collidepoint(e.pos):
                    if e.button == 3:
                        self._clear_waypoint()
                    else:
                        self.set_waypoint(e.pos)
            self._down = None
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_p:
            self.game.scenes.pop()
            self.space.toggle_autopilot()

    def _update_hover(self, screen_pos) -> None:
        if not self._view or not self._view[4].collidepoint(screen_pos):
            self._hover_sec = None
            return
        origin, cell, cx, cy, _area = self._view
        world = ((Vector2(screen_pos) - origin) / cell + Vector2(cx + 0.5, cy + 0.5)) * config.SECTOR_SIZE
        self._hover_sec = Universe.sector_coords(world)

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
        veil.fill((3, 6, 16, 248))
        surf.blit(veil, (0, 0))
        th = theme()
        header = pygame.Rect(30, 12, config.SCREEN_W - 60, 46)
        th.plate(surf, header)
        th.lamp(surf, (header.x + 18, header.centery), (110, 220, 255))
        text(surf, "GALAXY MAP", (header.x + 36, header.centery), 20, (255, 225, 150), bold=True, anchor="midleft")
        span = 2 * self.radius + 1
        text(surf, f"{span}x{span}", (header.x + 240, header.centery), 13, (110, 220, 255),
             bold=True, anchor="midleft")

        # Action buttons on the right side of the header bar
        rx = header.right - 10
        if self.game.state.waypoint:
            self._clear_btn = pygame.Rect(rx - 156, header.y + 7, 156, 32)
            th.plate(surf, self._clear_btn, gold=True)
            text(surf, "Clear Waypoint", self._clear_btn.center, 12, (255, 225, 140), bold=True, anchor="center")
            rx = self._clear_btn.x - 10
        else:
            self._clear_btn = None

        self._center_btn = pygame.Rect(rx - 110, header.y + 7, 110, 32)
        th.plate(surf, self._center_btn)
        text(surf, "Center [H]", self._center_btn.center, 12, (190, 215, 245), anchor="center")

        hint_x = self._center_btn.x - 16
        text(surf, "Click: waypoint · Wheel: zoom · Drag: pan · P: autopilot · Esc: close",
             (hint_x, header.centery), 11, (150, 168, 198), anchor="midright")

        self._galaxy(surf, pygame.Rect(30, 68, 700, 622))
        self._system(surf, pygame.Rect(748, 68, 502, 622))

    def _galaxy(self, surf, area: pygame.Rect) -> None:
        panel(surf, area)
        g, st = self.game, self.game.state
        u = g.universe
        ship = self.space.ship.pos
        cx, cy = Universe.sector_coords(ship)
        R = self.radius
        map_rect = pygame.Rect(area.x + 12, area.y + 12, area.w - 24, area.h - 90)
        cell = min(map_rect.w, map_rect.h) / (2 * R + 1)
        origin = Vector2(map_rect.center) + self.pan
        clip = surf.get_clip()
        surf.set_clip(map_rect)

        def to_map(p):
            rel = (Vector2(p) / config.SECTOR_SIZE) - Vector2(cx + 0.5, cy + 0.5)
            return origin + rel * cell

        # Subtle scanner-range ring centered on current sector
        scan_r = (1.5 + st.lvl("scanner") // 2) * cell
        ship_sec_center = to_map(((cx + 0.5) * config.SECTOR_SIZE, (cy + 0.5) * config.SECTOR_SIZE))
        pygame.draw.circle(surf, (25, 60, 88), ship_sec_center, max(8, int(scan_r)), 1)

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
                is_cur = (sx == cx and sy == cy)
                is_hov = (self._hover_sec == (sx, sy))
                grid_col = (44, 72, 110) if is_cur else ((28, 42, 70) if (sx == 0 or sy == 0) else (18, 26, 46))
                pygame.draw.rect(surf, grid_col, (tl.x, tl.y, cell, cell), 1)
                if is_hov:
                    hl = pygame.Surface((max(1, int(cell)), max(1, int(cell))), pygame.SRCALPHA)
                    hl.fill((110, 220, 255, 22))
                    surf.blit(hl, (tl.x, tl.y))
                    pygame.draw.rect(surf, (110, 220, 255), (tl.x, tl.y, cell, cell), 1)
                if max(abs(dx), abs(dy)) > R:
                    continue
                sec = get(sx, sy)
                if sec is None:
                    continue
                known = sec.key in st.discovered_systems
                near = max(abs(dx), abs(dy)) <= 1 + st.lvl("scanner") // 2
                for n in sec.nebulae:
                    if near or known:
                        np_ = to_map(n.center)
                        nr = max(4, int(n.radius / config.SECTOR_SIZE * cell))
                        ns = pygame.Surface((nr * 2, nr * 2), pygame.SRCALPHA)
                        pygame.draw.circle(ns, (*n.color[:3], 32), (nr, nr), nr)
                        pygame.draw.circle(ns, (*n.color[:3], 95), (nr, nr), nr, 1)
                        surf.blit(ns, (np_.x - nr, np_.y - nr))
                if sec.has_system and (known or near):
                    p = to_map(sec.system_center)
                    col = sec.star.color if known else (95, 105, 130)
                    sr = max(3, int(cell * 0.075))
                    glow_r = sr * 2 + 2
                    gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*col[:3], 55 if known else 28), (glow_r, glow_r), glow_r)
                    surf.blit(gs, (p.x - glow_r, p.y - glow_r))
                    pygame.draw.circle(surf, col, p, sr)
                    if known and cell > 54:
                        text(surf, sec.name, (p.x, p.y + sr + 5), 11, (205, 218, 242), anchor="midtop")
                    relic = [pl for pl in sec.planets if pl.stronghold and pl.biome_id in g.quests.missing_relics()
                             and pl.id not in st.looted_strongholds]
                    if relic and (known or near) and g.quests.cid == "keys":
                        pygame.draw.circle(surf, (255, 210, 90), p, max(7, int(cell * 0.14)), 2)
                    if sec.stations and known:
                        pygame.draw.rect(surf, (110, 225, 255), (p.x + sr + 3, p.y - sr - 4, 6, 6))
                for h in sec.hazards:
                    if known or near:
                        pygame.draw.circle(surf, h.map_color(), to_map(h.pos(st.world_time)), 3)
                for w in sec.wormholes:
                    if near:
                        pygame.draw.circle(surf, (190, 110, 255), to_map(w.center), 5, 1)

        if st.boss_defeated:  # Act II: Shard vaults are always on the map
            for (sx, sy), biome in u.shard_sites.items():
                if biome in st.shards:
                    continue
                p = to_map(((sx + 0.5) * config.SECTOR_SIZE, (sy + 0.5) * config.SECTOR_SIZE))
                r = max(7, cell * 0.12)
                pts = [(p.x, p.y - r), (p.x + r * 0.7, p.y), (p.x, p.y + r), (p.x - r * 0.7, p.y)]
                pygame.draw.polygon(surf, config.UI_VIOLET, pts, 2)
                text(surf, biome.title(), (p.x, p.y + r + 2), 11, config.UI_VIOLET, anchor="midtop")

        self._view = (origin, cell, cx, cy, map_rect)
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
                if cell > 44:
                    text(surf, o.get("name", ""), (p.x, p.y - 7), 10, (255, 220, 140), anchor="midbottom")
        if st.ending and not st.signal_found:
            from ..systems.quests import signal_position
            p = to_map(signal_position(u))
            pygame.draw.circle(surf, (90, 240, 220), p, 9, 2)
            text(surf, "???", (p.x, p.y - 12), 12, (90, 240, 220), anchor="midbottom")
        if st.waypoint:
            wp_world = Vector2(st.waypoint[0], st.waypoint[1])
            p = to_map(wp_world)
            pygame.draw.line(surf, (80, 225, 165), to_map(ship), p, 2)
            surf.blit(self.game.assets.image("generated/ui/icons/waypoint.png", size=(22, 22)), (p.x - 6, p.y - 20))
            dist_sec = wp_world.distance_to(ship) / config.SECTOR_SIZE
            text(surf, f"{st.waypoint[2]} ({dist_sec:.1f} sec)", (p.x, p.y + 10), 11, (120, 245, 185), anchor="midtop")
        sp = to_map(ship)
        fwd = self.space.ship.forward
        pygame.draw.polygon(surf, (255, 255, 255), [sp + fwd * 9, sp + fwd.rotate(140) * 7, sp + fwd.rotate(-140) * 7])
        if g.net is not None:
            for peer in g.net.peers.values():
                pp = to_map((peer.rx, peer.ry))
                pygame.draw.circle(surf, peer.color, (int(pp.x), int(pp.y)), 5)
                text(surf, peer.name, (pp.x, pp.y - 8), 11, peer.color, bold=True, anchor="midbottom")
        if cell <= 54:
            home = to_map(u.sector(0, 0).system_center)
            text(surf, "Haven", (home.x, home.y - 10), 12, (255, 230, 160), anchor="midbottom")
        surf.set_clip(clip)

        # Bottom status & legend bar inside the galaxy panel (generous spacing, fixed columns)
        bar_rect = pygame.Rect(area.x + 12, area.bottom - 72, area.w - 24, 58)
        theme().plate(surf, bar_rect)
        if self._hover_sec is not None:
            hx, hy = self._hover_sec
            hsec = u.peek(hx, hy)
            if hsec and hsec.has_system and hsec.key in st.discovered_systems:
                info = f"Cursor ({hx},{hy}) · {hsec.name} · Danger {hsec.danger:.1f} · {len(hsec.planets)} worlds"
            elif hsec:
                info = f"Cursor ({hx},{hy}) · {'Uncharted system' if hsec.has_system else 'Deep space'} · Danger {hsec.danger:.1f}"
            else:
                info = f"Cursor ({hx},{hy}) · Unscanned sector"
        else:
            info = (f"Sector ({cx},{cy}) · Danger {u.sector(cx, cy).danger:.1f} · "
                    f"{len(st.discovered_systems)} systems charted")
        text(surf, info, (bar_rect.x + 14, bar_rect.y + 16), 12, (205, 222, 248), anchor="midleft")
        legend = [((255, 220, 140), "Star"), ((110, 225, 255), "Station"), ((255, 210, 90), "Signal"),
                  ((255, 190, 110), "Outpost"), (config.UI_VIOLET, "Shard"), ((90, 230, 160), "Waypoint")]
        col_w = (bar_rect.w - 24) // len(legend)
        ly = bar_rect.y + 40
        for idx, (col, lbl) in enumerate(legend):
            lx = bar_rect.x + 16 + idx * col_w
            pygame.draw.circle(surf, col, (lx + 4, ly), 4)
            text(surf, lbl, (lx + 14, ly), 11, (165, 180, 210), anchor="midleft")

    def _system(self, surf, area: pygame.Rect) -> None:
        panel(surf, area)
        th = theme()
        sys_ = self.space.system
        t = self.game.state.world_time
        if sys_ is None:
            text(surf, "DEEP SPACE", (area.centerx, area.centery - 10), 22, (170, 185, 215), bold=True, anchor="center")
            text(surf, "No star system within sensor range", (area.centerx, area.centery + 20), 14,
                 (130, 145, 175), anchor="center")
            return

        # System header plate with clean internal padding
        hdr = pygame.Rect(area.x + 16, area.y + 16, area.w - 32, 64)
        th.plate(surf, hdr)
        text(surf, f"{sys_.name} System", (hdr.x + 16, hdr.y + 18), 18, sys_.star.color, bold=True, anchor="midleft")
        planets = [p for p in sys_.planets if not p.is_moon]
        text(surf, f"{sys_.star.spectral}-class star  ·  {len(planets)} worlds",
             (hdr.x + 16, hdr.y + 44), 12, (175, 190, 220), anchor="midleft")
        d_col = config.UI_DANGER if sys_.danger >= 3 else (config.UI_WARN if sys_.danger >= 2 else config.UI_GOOD)
        text(surf, f"Danger {sys_.danger:.1f}", (hdr.right - 16, hdr.centery), 13, d_col, bold=True, anchor="midright")

        # Orrery view
        orrery_h = 248
        c = Vector2(area.centerx, area.y + 84 + orrery_h * 0.5)
        scale = (min(area.w - 64, orrery_h - 32) / 2) / max(1, sys_.system_radius - 1500)
        center = sys_.star.pos(t)
        gs = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*sys_.star.color[:3], 60), (20, 20), 18)
        surf.blit(gs, (c.x - 20, c.y - 20))
        pygame.draw.circle(surf, sys_.star.color, c, 8)

        st = self.game.state
        for idx, p in enumerate(planets, 1):
            pygame.draw.circle(surf, (36, 48, 76), c, max(4, int(p.orbit_r * scale)), 1)
            pp = c + (p.pos(t) - center) * scale
            pr = max(4, int(p.radius * scale * 3))
            pygame.draw.circle(surf, p.map_color(), pp, pr)
            if p.stronghold and p.id not in st.looted_strongholds:
                pygame.draw.circle(surf, (255, 210, 90), pp, pr + 4, 1)
            text(surf, str(idx), (pp.x, pp.y - pr - 5), 10, (185, 200, 225), anchor="midbottom")
        for s in sys_.stations:
            sp = c + (s.pos(t) - center) * scale
            pygame.draw.rect(surf, (110, 225, 255), (sp.x - 3, sp.y - 3, 7, 7))
        shp = c + (self.space.ship.pos - center) * scale
        if area.collidepoint(shp):
            fwd = self.space.ship.forward
            pygame.draw.polygon(surf, (255, 255, 255),
                                [shp + fwd * 7, shp + fwd.rotate(140) * 5, shp + fwd.rotate(-140) * 5])

        # Planet list cards with generous row height (32px) and padding
        list_y = area.y + 346
        for idx, p in enumerate(planets[:7], 1):
            row = pygame.Rect(area.x + 16, list_y + (idx - 1) * 37, area.w - 32, 32)
            sig = p.stronghold and p.id not in st.looted_strongholds
            th.plate(surf, row, gold=sig)
            pygame.draw.circle(surf, p.map_color(), (row.x + 16, row.centery), 5)
            text(surf, f"{idx}. {p.name} · {p.biome.name}", (row.x + 30, row.centery), 12,
                 (225, 235, 250), anchor="midleft")
            badges = []
            if p.id in st.outposts:
                badges.append(("OUTPOST", (255, 210, 120)))
            if sig:
                badges.append(("SIGNAL", (255, 215, 90)))
            if p.id in st.landed_planets:
                badges.append(("LANDED", (120, 255, 160)))
            bx = row.right - 14
            for btxt, bcol in badges:
                text(surf, btxt, (bx, row.centery), 11, bcol, bold=True, anchor="midright")
                bx -= len(btxt) * 8 + 14
