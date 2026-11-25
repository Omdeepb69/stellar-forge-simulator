"""The Logbook: journal, planet codex, achievements and pilot stats."""
from __future__ import annotations

import zlib

import pygame

from .. import config
from ..core.scene import Scene
from ..systems.achievements import ACHIEVEMENTS, LANDABLE, RANKS, rank
from ..systems.quests import CHAPTERS
from ..ui.text import bar, panel, text, wrap
from ..world.biomes import BIOMES, LIQUIDS

TABS = ["Journal", "Codex", "Archive", "Achievements", "Stats"]
GOLD = config.UI_GOLD
CYAN = (140, 210, 255)

JOURNAL = {
    "awaken": "Woke from cryo-sleep on Aster after the crash. A distress call came from orbit.",
    "signal": "Found Haven Station under attack. Commander Vey told me about the Ancient Keys.",
    "raiders": "Drove off the raiders. Their wrecks carried charts of the old strongholds.",
    "keys": "Recovered the Sun, Frost and Verdant Keys from their desert, ice and forest vaults.",
    "return": "Brought the Keys home. The Warlord came for them through the Forge gate.",
    "boss": "Defeated the Warlord. His death shattered the Forge's core into five Shards.",
    "shards": "Broke the Remnant Wardens' blockades and recovered all five Forge Shards.",
    "forge": "Decided the Forge's fate with all five Shards in hand.",
    "free": "Heard a bell ring at the rim of the galaxy.",
    "road": "Walked the Maker Road and passed the three waystone trials.",
    "judgment": "Rang the Bell and faced the Last Smith's judgment.",
    "legend": "The galaxy never ends.",
}


class LogbookScene(Scene):
    is_overlay = True

    def __init__(self, game, state=None):
        super().__init__(game)
        self.state = state or game.state
        self.menu = True
        self.tab = 0
        self.scroll = 0
        self._planets: dict[str, pygame.Surface] = {}

    def _frame(self):
        return pygame.Rect((config.SCREEN_W - 980) // 2, 60, 980, 610)

    def _tab_rects(self):
        f = self._frame()
        return [pygame.Rect(f.x + 24 + i * 150, f.y + 62, 142, 36) for i in range(len(TABS))]

    def handle_event(self, e) -> None:
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_b):
                self.game.scenes.pop()
            elif e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_q):
                self._set_tab(self.tab - 1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB, pygame.K_e):
                self._set_tab(self.tab + 1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.scroll += 1
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.scroll = max(0, self.scroll - 1)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._tab_rects()):
                if r.collidepoint(e.pos):
                    self._set_tab(i)
        elif e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - e.y)

    def _set_tab(self, i):
        self.tab = i % len(TABS)
        self.scroll = 0
        self.game.audio.play("ui", 0.4)

    # ------------------------------------------------------------------
    def draw(self, surf) -> None:
        v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        v.fill((0, 3, 10, 190))
        surf.blit(v, (0, 0))
        st = self.state
        f = self._frame()
        panel(surf, f, color=(8, 14, 30, 245), border=GOLD)
        text(surf, "LOGBOOK", (f.x + 26, f.y + 18), 28, GOLD, bold=True)
        surf.blit(self.game.assets.image("generated/ui/icons/star.png", size=(24, 24)), (f.right - 300, f.y + 22))
        text(surf, f"{rank(st)}", (f.right - 268, f.y + 22), 20, (255, 235, 190), bold=True)
        for i, r in enumerate(self._tab_rects()):
            sel = i == self.tab
            panel(surf, r, color=(30, 60, 100, 230) if sel else (12, 20, 36, 220),
                  border=GOLD if sel else (60, 80, 120), radius=6, corners=sel)
            text(surf, TABS[i], r.center, 16, (255, 230, 160) if sel else (180, 190, 210), bold=sel, anchor="center")
        body = pygame.Rect(f.x + 24, f.y + 116, f.w - 48, f.h - 150)
        clip = surf.get_clip()
        surf.set_clip(body)
        [self._journal, self._codex, self._archive, self._achievements, self._stats][self.tab](surf, body)
        surf.set_clip(clip)
        text(surf, "<- -> tabs   Up/Down scroll   B / Esc close", (f.right - 20, f.bottom - 12), 12,
             (130, 140, 170), anchor="bottomright")

    def _journal(self, surf, r) -> None:
        st = self.state
        y = r.y + 4 - self.scroll * 40
        for i, ch in enumerate(CHAPTERS):
            done = i < st.chapter or (ch["id"] == "free" and st.forge_restored)
            current = i == min(st.chapter, len(CHAPTERS) - 1)
            hidden = not done and not current and i >= 6 and not st.boss_defeated
            if hidden:
                col, title = (90, 95, 110), "???  (a story yet to be told)"
            else:
                col = GOLD if current else ((150, 230, 170) if done else (150, 160, 185))
                title = f"{'ACT II · ' if ch['id'] == 'shards' else ''}{ch['title']}"
            mark = "✓" if done else ("▶" if current else "·")
            text(surf, f"{mark}", (r.x + 8, y), 18, col, bold=True)
            text(surf, f"Chapter {i + 1}: {title}", (r.x + 36, y), 18, col, bold=current)
            y += 26
            if hidden:
                y += 10
                continue
            desc = JOURNAL.get(ch["id"], "") if done else (ch["objective"] if current else "")
            if current and ch["id"] in ("raiders", "keys", "shards"):
                have = {"raiders": st.chapter_progress, "keys": len(st.relics), "shards": len(st.shards)}[ch["id"]]
                desc += f"  ({have}/{ch['count']})"
            for line in wrap(desc, 15, r.w - 60):
                text(surf, line, (r.x + 36, y), 15, (200, 210, 230) if not done else (165, 180, 200))
                y += 20
            y += 12

    def _planet_icon(self, biome_id: str, size: int) -> pygame.Surface:
        key = f"{biome_id}:{size}"
        img = self._planets.get(key)
        if img is None:
            from ..world.planet_art import render_planet
            b = BIOMES[biome_id]
            liquid = LIQUIDS[b.liquid]["color"] if b.liquid and b.liquid_level > 0.3 else None
            raw = render_planet(zlib.crc32(biome_id.encode()) & 0xFFFF, b.planet_palette, biome_id == "gas",
                                biome_id == "gas", liquid, biome=biome_id, size=40)
            k = max(1, size // raw.get_width())
            img = self._planets[key] = pygame.transform.scale(raw, (raw.get_width() * k, raw.get_height() * k))
        return img

    def _codex(self, surf, r) -> None:
        st = self.state
        ids = list(LANDABLE) + ["gas"]
        cols = 3
        cw, chh = r.w // cols, 150
        seen = sum(b in st.biomes_visited for b in LANDABLE)
        text(surf, f"World types walked: {seen}/{len(LANDABLE)}", (r.x + 4, r.y + 2 - self.scroll * 40), 15, CYAN,
             bold=True)
        for i, bid in enumerate(ids):
            b = BIOMES[bid]
            x = r.x + (i % cols) * cw
            y = r.y + 30 + (i // cols) * chh - self.scroll * 40
            cell = pygame.Rect(x + 4, y, cw - 12, chh - 12)
            known = bid in st.biomes_visited or (bid == "gas" and len(st.discovered_systems) > 1)
            panel(surf, cell, color=(12, 22, 40, 220), border=(90, 130, 180) if known else (50, 60, 80),
                  radius=6, corners=known)
            icon = self._planet_icon(bid, 84)
            if not known:
                icon = icon.copy()
                icon.fill((20, 20, 30, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(icon, (cell.x + 10, cell.y + 12))
            tx = cell.x + 104
            if not known:
                text(surf, "Unknown world", (tx, cell.y + 14), 16, (120, 130, 150), bold=True)
                text(surf, "Land on one to log it.", (tx, cell.y + 40), 13, (110, 120, 140))
                continue
            text(surf, b.name, (tx, cell.y + 10), 17, GOLD, bold=True)
            facts = f"{b.gravity:.2f} g" + (f" · {b.liquid}" if b.liquid else "") + (f" · {b.weather}" if b.weather else "")
            text(surf, facts, (tx, cell.y + 32), 12, CYAN)
            for j, line in enumerate(wrap(b.description, 12, cell.right - tx - 8)[:4]):
                text(surf, line, (tx, cell.y + 52 + j * 17), 12, (200, 210, 230))
            fauna = sum(1 for k in ("hopper", "flyer") if f"{bid}:{k}" in st.scanned)
            if bid != "gas":
                text(surf, f"Fauna {fauna}/2", (cell.right - 8, cell.y + 12), 11,
                     (140, 255, 200) if fauna == 2 else (150, 160, 180), anchor="topright")
            if bid in st.trophies:
                from ..systems.items import BOSSES
                surf.blit(self.game.assets.image(f"generated/ui/icons/{BOSSES[bid]['icon']}.png", size=(24, 24)),
                          (cell.x + 10, cell.bottom - 34))
            tags = []
            if b.relic:
                tags.append("Key vaults")
            if bid in ("crystal", "volcanic", "toxic", "ocean", "barren"):
                tags.append("Shard vault")
            if tags:
                text(surf, " · ".join(tags), (tx, cell.bottom - 22), 12, (255, 200, 120))

    def _archive(self, surf, r) -> None:
        from ..systems.lore import LOGS
        st = self.state
        found = [lid for lid in LOGS if lid in st.logs]
        text(surf, f"Logs recovered: {len(found)}/{len(LOGS)}", (r.x + 4, r.y + 2), 15, CYAN, bold=True)
        text(surf, "Inscriptions: strongholds, caves, beasts  ·  Crew logs: derelicts  ·  Remnant: flagships",
             (r.right - 4, r.y + 4), 12, (150, 165, 195), anchor="topright")
        if not found:
            text(surf, "No logs yet. Board derelicts, loot vaults and crack geodes.", (r.centerx, r.y + 120), 16,
                 (160, 170, 195), anchor="center")
            return
        self.scroll = min(self.scroll, len(found) - 1)
        lid = found[self.scroll]
        pool, title, body = LOGS[lid]
        # list on the left, selected log on the right
        for i, l2 in enumerate(found):
            y = r.y + 34 + i * 22
            if y > r.bottom - 20:
                break
            sel = i == self.scroll
            text(surf, ("> " if sel else "  ") + LOGS[l2][1][:34], (r.x + 4, y), 13,
                 GOLD if sel else (180, 190, 210), bold=sel)
        box = pygame.Rect(r.x + 330, r.y + 34, r.w - 334, r.h - 40)
        panel(surf, box, color=(12, 22, 40, 220), border=(90, 130, 180), radius=6)
        surf.blit(self.game.assets.image("generated/items/datapad.png", size=(36, 36)), (box.x + 14, box.y + 14))
        text(surf, title, (box.x + 60, box.y + 14), 18, GOLD, bold=True)
        text(surf, {"architect": "Architect inscription", "crew": "Crew log", "remnant": "Remnant datapad"}[pool],
             (box.x + 60, box.y + 38), 12, CYAN)
        for j, line in enumerate(wrap(body, 16, box.w - 40)):
            text(surf, line, (box.x + 20, box.y + 70 + j * 24), 16, (215, 225, 240))
        text(surf, "Up/Down to browse", (box.right - 10, box.bottom - 8), 11, (130, 140, 170), anchor="bottomright")

    def _achievements(self, surf, r) -> None:
        st = self.state
        got = len(st.achievements)
        text(surf, f"{got}/{len(ACHIEVEMENTS)} unlocked", (r.x + 4, r.y + 2 - self.scroll * 40), 15, CYAN, bold=True)
        nxt = next(((need, name) for need, name in RANKS if need > got), None)
        if nxt:
            text(surf, f"Next rank: {nxt[1]} at {nxt[0]}", (r.right - 4, r.y + 2 - self.scroll * 40), 14,
                 (190, 200, 225), anchor="topright")
        cw = r.w // 2
        for i, a in enumerate(ACHIEVEMENTS):
            x = r.x + (i % 2) * cw
            y = r.y + 30 + (i // 2) * 62 - self.scroll * 40
            if y > r.bottom or y < r.y - 62:
                continue
            unlocked = a.id in st.achievements
            cell = pygame.Rect(x + 2, y, cw - 10, 56)
            panel(surf, cell, color=(14, 26, 46, 220) if unlocked else (10, 16, 28, 200),
                  border=GOLD if unlocked else (50, 60, 80), radius=6, corners=unlocked)
            ic = "trophy" if unlocked else "locked"
            surf.blit(self.game.assets.image(f"generated/ui/icons/{ic}.png", size=(34, 34)), (cell.x + 10, cell.y + 11))
            name = a.name if unlocked or not a.secret else "???"
            desc = a.desc if unlocked or not a.secret else "A secret achievement"
            text(surf, name, (cell.x + 54, cell.y + 7), 16, GOLD if unlocked else (190, 195, 210), bold=True)
            text(surf, desc, (cell.x + 54, cell.y + 30), 13, (190, 205, 225) if unlocked else (130, 140, 160))
            if not unlocked and a.progress and not a.secret:
                have, need = a.progress(st)
                bar(surf, (cell.right - 120, cell.y + 10, 108, 10), have / need, (110, 180, 255))
                text(surf, f"{int(have)}/{int(need)}", (cell.right - 12, cell.y + 22), 11, (150, 165, 190),
                     anchor="topright")

    def _stats(self, surf, r) -> None:
        from .menus import fmt_time
        st = self.state
        s = st.stats
        rows = [
            ("star", "Pilot rank", rank(st)),
            ("planet", "Time played", fmt_time(st.play_time)),
            ("kill", "Raiders destroyed", st.kills),
            ("kill", "Remnant flagships destroyed", s.get("flagships", 0)),
            ("kill", "Creatures defeated", s.get("creatures", 0)),
            ("star", "Star systems charted", max(0, len(st.discovered_systems) - 1)),
            ("planet", "Worlds walked", len(st.landed_planets)),
            ("trophy", "Strongholds looted", len(st.looted_strongholds)),
            ("ore", "Ore collected", s.get("ore_total", 0)),
            ("credits", "Credits earned", f"{s.get('credits_earned', 0):,}"),
            ("data", "Contracts completed", st.contracts_done),
            ("star", "Furthest sector from Haven", s.get("max_distance", 0)),
            ("key", "Ancient Keys", f"{len(st.relics)}/3"),
            ("shard", "Forge Shards", f"{len(st.shards)}/5"),
            ("planet", "Derelicts looted", len(st.derelicts_looted)),
            ("trophy", "Planet bosses slain", len(st.lairs_cleared)),
            ("kill", "Creature kinds logged", len(st.scanned)),
            ("data", "Lore logs", f"{len(st.logs)}/30"),
            ("star", "Encounters resolved", s.get("events", 0)),
            ("planet", "Outposts", len(st.outposts)),
            ("star", "Difficulty", st.diff["name"]),
            ("star", "Galaxy seed", st.seed),
            ("star", "New Game+ cycle", st.ng_plus),
            ("camp", "Settlers helped", s.get("settlers", 0)),
            ("ruin", "Ruins solved", s.get("ruins", 0)),
            ("pod", "Escape pods salvaged", s.get("pods", 0)),
            ("vault", "Cave vaults opened", s.get("vaults", 0)),
        ]
        from ..systems.corps_career import rank_name
        rows += [("scanner", "Corps rank", f"{rank_name(st)} ({st.corps_merit_total} lifetime)"),
                 ("scanner", "Corps contracts done", s.get("corps_jobs", 0)),
                 ("scanner", "Corps Merit", st.corps_merit),
                 ("scanner", "Corps battles", s.get("corps_battles", 0)),
                 ("scanner", "Corps calls answered", s.get("corps_calls", 0))]
        from ..systems.species import GROUPS
        for grp in GROUPS:                                  # the roaming groups you've met
            met = st.groups.get(grp["key"], {}).get("met", 0)
            rows.append((grp["icon"], grp["name"], f"met {met}x" if met else "not yet met"))
        from ..systems.materials import MATERIALS
        rows = [(f"mat_{b}", name, st.materials.get(b, 0)) for b, (name, _c) in MATERIALS.items()] + rows
        from ..systems.items import FACTIONS, standing
        fy = r.y + 6 - self.scroll * 40
        for k, (fid, (fname, emblem, fcol)) in enumerate(FACTIONS.items()):
            x = r.x + k * (r.w // 3)
            surf.blit(self.game.assets.image(emblem, size=(34, 34)), (x + 4, fy))
            rep = st.rep.get(fid, 0)
            text(surf, fname, (x + 46, fy), 14, fcol, bold=True)
            text(surf, f"{standing(rep)}  ({rep:+.0f})", (x + 46, fy + 18), 13, (200, 210, 230))
        cw = r.w // 2
        for i, (ic, label, val) in enumerate(rows):
            x = r.x + (i % 2) * cw
            y = r.y + 52 + (i // 2) * 52 - self.scroll * 40
            cell = pygame.Rect(x + 2, y, cw - 10, 44)
            panel(surf, cell, color=(12, 22, 40, 210), border=(60, 90, 130), radius=6, corners=False)
            surf.blit(self.game.assets.image(f"generated/ui/icons/{ic}.png", size=(26, 26)), (cell.x + 10, cell.y + 9))
            text(surf, label, (cell.x + 46, cell.centery), 15, (200, 212, 232), anchor="midleft")
            text(surf, str(val), (cell.right - 14, cell.centery), 17, GOLD, bold=True, anchor="midright")
