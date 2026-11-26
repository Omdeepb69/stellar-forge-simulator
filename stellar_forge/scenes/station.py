"""Docked-at-station screen, Console style (see docs/style/ui_station.png).

Layout: icon tabs on the left, the item list in the middle (no boxes: rows live
on the glass, the selected row gets a gold plate and a lamp), and a detail card
on the right with the description, stat change and an [E] action.
Prices follow your standing with the station's faction.
"""
from __future__ import annotations

import random

import pygame

from .. import config
from ..systems import materials as M
from ..core.game_state import UPGRADES
from ..core.scene import Scene
from ..systems.items import FACTIONS, FOOT_WEAPONS, MOD_SLOTS, RARITY, SHIPS, WEAPONS, mod_value, price_mult, standing
from ..ui import pixelfont
from ..ui.text import theme

TABS = [("wrench", "Services"), ("engine", "Upgrades"), ("ship", "Hangar"), ("blaster", "Armory"),
        ("scroll", "Contracts")]
UPGRADE_ICONS = {"engine": "engine", "tank": "fuel", "hull": "hull", "shield": "shield", "blaster": "blaster",
                 "scanner": "scanner", "suit": "suit"}
VISIBLE = 7


def station_faction(station) -> str:
    if station.id == "0,0:st":
        return "haven"
    return "haven" if random.Random(station.seed).random() < 0.6 else "traders"


class Row:
    __slots__ = ("label", "detail", "cost", "action", "alt", "icon", "pips", "stat", "verb", "color", "mats")

    def __init__(self, label, detail="", cost=None, action=None, alt=None, icon=None, pips=None, stat=None,
                 verb="Buy", color=None, mats=None):
        self.label, self.detail, self.cost, self.action, self.alt = label, detail, cost, action, alt
        self.icon, self.pips, self.stat, self.verb, self.color = icon, pips, stat, verb, color
        self.mats = mats or {}


class StationScene(Scene):
    is_overlay = True
    menu = True

    def __init__(self, game, station):
        super().__init__(game)
        self.station = station
        self.tab = 0
        self.index = 0
        self.scroll = 0
        self.home = station.id == "0,0:st"
        self.faction = station_faction(station)
        self.offers = game.quests.offers(station.id)
        self.refused = game.state.rep.get(self.faction, 0) <= -40
        if self.refused:
            game.toasts.add(f"{FACTIONS[self.faction][0]} won't trade with you.", config.UI_DANGER, 4)

    @property
    def free(self) -> bool:
        return self.home and self.game.state.chapter >= 2

    @property
    def mult(self) -> float:
        return 1.0 if self.free else price_mult(self.game.state.rep.get(self.faction, 0))

    # ---- rows -----------------------------------------------------------------
    def rows(self) -> list[Row]:
        st = self.game.state
        if self.refused and self.tab:
            return [Row("Service refused", "This faction will not deal with you.", verb="")]
        return [self._services, self._upgrades, self._hangar, self._armory, self._contracts][self.tab](st)

    def _services(self, st):
        fuel_need, hull_need = st.max_fuel - st.fuel, st.max_hull - st.hull
        fcost = 0 if self.free else int(fuel_need * config.FUEL_PRICE * self.mult + 0.999)
        hcost = 0 if self.free else int(hull_need * config.REPAIR_PRICE * self.mult + 0.999)
        med_full = st.medkits >= config.MAX_MEDKITS
        mcost = 0 if self.free else int(config.MEDKIT_PRICE * self.mult + 0.999)
        rows = []
        if not self.refused:
            rows += [Row("Refuel", f"Top up {fuel_need:.0f} units of fuel.", fcost, self._refuel, icon="fuel",
                         stat=("Fuel", f"{st.fuel:.0f} → {st.max_fuel:.0f}"), verb="Refuel"),
                     Row("Repair hull", f"Patch {hull_need:.0f} points of hull damage.", hcost, self._repair,
                         icon="hull", stat=("Hull", f"{st.hull:.0f} → {st.max_hull:.0f}"), verb="Repair"),
                     Row("Buy Nano-Medkit", "Restores pilot HP on foot when you press [H].",
                         None if med_full else mcost, None if med_full else self._buy_medkit, icon="medkit",
                         stat=("Carried", f"{st.medkits}/{config.MAX_MEDKITS}"), verb="" if med_full else "Buy"),
                     Row(f"Sell ore  ×{st.ore}", "Miners' guild buys raw ore at a fixed rate.",
                         -st.ore * config.ORE_VALUE if st.ore else None, self._sell_ore, icon="ore", verb="Sell"),
                     Row(f"Sell scan data  ×{st.scan_data}", "Cartographers pay for fresh system scans.",
                         -st.scan_data * 15 if st.scan_data else None, self._sell_data, icon="data", verb="Sell")]
            from .outpost import beacons
            if beacons(st):
                rows.append(Row("Warp network", "Jump to one of your outpost beacons.", None, self._warp,
                                icon="autopilot", verb="Open"))
        if st.corps_banned:
            from ..systems import corps as C
            lic_cost = C.LICENCE_FEE + st.corps_fine
            rows.append(Row("Buy Survey Corps licence",
                            "Reinstate your revoked Survey Corps calling privileges.",
                            lic_cost, self._buy_corps_licence, icon="scanner",
                            stat=("Status", f"BANNED ({st.corps_strikes}/{C.MAX_STRIKES})"), verb="Buy"))
        rows.append(Row("Undock", "Back to the stars.", None, self._undock, icon="ship", verb="Undock"))
        return rows

    def _upgrades(self, st):
        out = []
        for key, (name, desc) in UPGRADES.items():
            lvl = st.lvl(key)
            maxed = lvl >= config.UPGRADE_MAX_LEVEL
            out.append(Row(name, desc + ".", None if maxed else int(st.upgrade_cost(key) * self.mult),
                           (lambda k=key: self._upgrade(k)) if not maxed else None, icon=UPGRADE_ICONS[key],
                           pips=(lvl, config.UPGRADE_MAX_LEVEL), verb="" if maxed else "Upgrade",
                           stat=("Level", f"{lvl} → {lvl + 1}" if not maxed else "MAX"),
                           mats=None if maxed else st.upgrade_mats(key)))
        return out

    def _hangar(self, st):
        out = []
        for sid, spec in SHIPS.items():
            if sid == st.ship:
                out.append(Row(spec["name"], spec["desc"], None, None, icon="ship", verb="", stat=("Status", "flying")))
            elif sid in st.ships_owned:
                out.append(Row(spec["name"], spec["desc"], None, lambda s=sid: self._switch(s), icon="ship",
                               verb="Fly", stat=("Status", "owned")))
            else:
                out.append(Row(spec["name"], spec["desc"], int(spec["price"] * self.mult),
                               lambda s=sid: self._buy_ship(s), icon="ship",
                               stat=("Hull / Thrust", f"×{spec['hull']:.1f} / ×{spec['thrust']:.1f}")))
        for m in sorted(st.mods, key=lambda m: -RARITY[m["rarity"]][0]):
            on = m["id"] in st.equipped
            out.append(Row(m["name"], f"{m['rarity'].title()} mod: {m['label']}. X sells it for {mod_value(m)} cr.",
                           None, lambda mm=m: self._toggle_mod(mm), lambda mm=m: self._sell_mod(mm),
                           icon=f"rarity_{m['rarity']}", verb="Unequip" if on else "Equip",
                           stat=("Mod slots", f"{len(st.equipped)}/{MOD_SLOTS}"),
                           color=RARITY[m["rarity"]][1] if not on else None))
        return out

    def _armory(self, st):
        out = []
        for wid, w in WEAPONS.items():
            owned = wid in st.weapons
            out.append(Row(w["name"], w["desc"], None if owned else int(w["price"] * self.mult),
                           None if owned else (lambda k=wid: self._buy_weapon(k)),
                           icon="blaster" if wid == "blaster" else "w_missile", verb="" if owned else "Buy",
                           stat=("Status", "owned" if owned else "for sale")))
        sp = FOOT_WEAPONS["spear"]
        owned = "spear" in st.weapons
        out.append(Row(sp["name"], sp["desc"] + " Swap on foot with Q.", None if owned else int(800 * self.mult),
                       None if owned else (lambda: self._buy_weapon("spear")), icon="blaster",
                       verb="" if owned else "Buy", stat=("Status", "owned" if owned else "for sale")))
        return out

    def _contracts(self, st):
        c = st.contract
        if c:
            return [Row(f"Active: {c['title']}", f"{c['desc']}  ({c['have']}/{c['need']})", None, None, icon="scroll",
                        verb="", stat=("Reward", f"{c['reward']} cr")),
                    Row("Abandon contract", "No penalty, but no pay either.", None, self._abandon, icon="door",
                        verb="Abandon")]
        return [Row(o["title"], o["desc"] + ".", -o["reward"], lambda o=o: self._accept(o), icon="scroll",
                    verb="Accept", stat=("Reward", f"{o['reward']} cr")) for o in self.offers]

    # ---- actions ----------------------------------------------------------------
    def _pay(self, cost: int) -> bool:
        if cost <= 0 or self.game.state.spend(cost):
            return True
        self.game.toasts.add("Not enough credits", config.UI_DANGER, 1.5)
        self.game.audio.play("deny")
        return False

    def _refuel(self):
        st = self.game.state
        need = st.max_fuel - st.fuel
        if need < 1:
            return
        unit = 0 if self.free else config.FUEL_PRICE * self.mult
        cost = int(need * unit + 0.999)
        if cost > st.credits and unit:
            st.fuel += st.credits / unit
            st.credits = 0
        elif self._pay(cost):
            st.fuel = st.max_fuel
        self.game.audio.play("pickup")

    def _repair(self):
        st = self.game.state
        need = st.max_hull - st.hull
        if need < 1:
            return
        unit = 0 if self.free else config.REPAIR_PRICE * self.mult
        cost = int(need * unit + 0.999)
        if cost > st.credits and unit:
            st.hull += st.credits / unit
            st.credits = 0
        elif self._pay(cost):
            st.hull = st.max_hull
        self.game.audio.play("pickup")

    def _buy_medkit(self):
        st = self.game.state
        if st.medkits >= config.MAX_MEDKITS:
            return
        cost = 0 if self.free else int(config.MEDKIT_PRICE * self.mult + 0.999)
        if self._pay(cost):
            st.medkits += 1
            self.game.audio.play("pickup")

    def _buy_corps_licence(self):
        from ..systems import corps as C
        st = self.game.state
        if not st.corps_banned:
            return
        cost = C.LICENCE_FEE + st.corps_fine
        if self._pay(cost):
            st.corps_banned = False
            st.corps_strikes = 0
            st.corps_fine = 0
            self.game.toasts.add("Survey Corps licence reinstated!", (120, 255, 160), 3, icon="scanner")
            self.game.audio.play("relic", 0.6)

    def _sell_ore(self):
        st = self.game.state
        if st.ore:
            st.earn(st.ore * config.ORE_VALUE)
            st.ore = 0
            self.game.audio.play("pickup")

    def _sell_data(self):
        st = self.game.state
        if st.scan_data:
            st.earn(st.scan_data * 15)
            st.scan_data = 0
            self.game.audio.play("pickup")

    def _warp(self):
        from .outpost import WarpScene
        self.game.state.shield = self.game.state.max_shield
        self.game.scenes.pop()
        self.game.scenes.push(WarpScene(self.game))

    def _upgrade(self, key):
        st = self.game.state
        need = st.upgrade_mats(key)
        if not M.has(st, need):
            self.game.audio.play("deny")
            self.game.toasts.add(f"Needs {M.describe(need)} - found on other worlds", config.UI_WARN, 3)
            return
        if self._pay(int(st.upgrade_cost(key) * self.mult)):
            M.take(st, need)
            before_hull, before_shield = st.max_hull, st.max_shield
            st.upgrades[key] += 1
            if key == "hull":
                st.hull += st.max_hull - before_hull
            if key == "shield":
                st.shield += st.max_shield - before_shield
            self.game.audio.play("relic", 0.5)
            self.game.toasts.add(f"{UPGRADES[key][0]} Lv {st.upgrades[key]}", config.UI_GOOD, icon="star")

    def _apply_hull(self):
        st = self.game.state
        st.hull = min(st.hull, st.max_hull)
        st.fuel = min(st.fuel, st.max_fuel)
        st.shield = min(st.shield, st.max_shield)
        if self.game.space is not None:
            self.game.space.ship.load_hull()

    def _buy_ship(self, sid):
        if self._pay(int(SHIPS[sid]["price"] * self.mult)):
            self.game.state.ships_owned.append(sid)
            self._switch(sid)
            self.game.banner.show(f"New ship: {SHIPS[sid]['name']}", SHIPS[sid]["desc"])

    def _switch(self, sid):
        st = self.game.state
        frac = st.hull / st.max_hull
        st.ship = sid
        st.hull = st.max_hull * frac
        self._apply_hull()
        self.game.audio.play("relic", 0.5)

    def _toggle_mod(self, m):
        st = self.game.state
        if m["id"] in st.equipped:
            st.equipped.remove(m["id"])
        elif len(st.equipped) >= MOD_SLOTS:
            self.game.toasts.add(f"All {MOD_SLOTS} mod slots are full", config.UI_WARN)
            self.game.audio.play("deny")
            return
        else:
            st.equipped.append(m["id"])
        self._apply_hull()
        self.game.audio.play("ui", 0.8)

    def _sell_mod(self, m):
        st = self.game.state
        if m["id"] in st.equipped:
            st.equipped.remove(m["id"])
        st.mods = [x for x in st.mods if x["id"] != m["id"]]
        st.earn(mod_value(m))
        self._apply_hull()
        self.game.audio.play("pickup")

    def _buy_weapon(self, wid):
        cost = 800 if wid == "spear" else WEAPONS[wid]["price"]
        if self._pay(int(cost * self.mult)):
            st = self.game.state
            st.weapons.append(wid)
            if wid == "spear":
                st.foot_weapon = "spear"
            else:
                st.weapon = wid
            self.game.toasts.add("Installed. Press Q to switch weapons.", config.UI_GOOD, icon="blaster")
            self.game.audio.play("relic", 0.6)

    def _accept(self, offer):
        self.game.quests.accept(dict(offer, faction=self.faction))
        self.game.audio.play("ui")

    def _abandon(self):
        self.game.state.contract = None
        self.offers = self.game.quests.offers(self.station.id)

    def _undock(self):
        st = self.game.state
        st.shield = st.max_shield
        self.game.save()
        self.game.scenes.pop()

    # ---- input ----------------------------------------------------------------
    def _set_tab(self, i):
        self.tab = i % len(TABS)
        self.index = self.scroll = 0
        self.game.audio.play("ui", 0.4)

    def _activate(self, row: Row | None):
        if row is not None and row.action:
            row.action()

    def handle_event(self, e) -> None:
        rows = self.rows()
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_q):
                self._undock()
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self._set_tab(self.tab - 1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                self._set_tab(self.tab + 1)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(rows)
                self.game.audio.play("ui", 0.3)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(rows)
                self.game.audio.play("ui", 0.3)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                self._activate(rows[min(self.index, len(rows) - 1)])
            elif e.key in (pygame.K_x, pygame.K_BACKSPACE, pygame.K_DELETE):
                alt = rows[min(self.index, len(rows) - 1)].alt
                if alt:
                    alt()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            for i, r in enumerate(self._tab_rects()):
                if r.collidepoint(e.pos):
                    self._set_tab(i)
                    return
            for i, r in self._row_rects(len(rows)):
                if r.collidepoint(e.pos):
                    self.index = i
                    if e.button == 1:
                        self._activate(rows[i])
                    elif rows[i].alt:
                        rows[i].alt()
        elif e.type == pygame.MOUSEMOTION:
            for i, r in self._row_rects(len(rows)):
                if r.collidepoint(e.pos):
                    self.index = i
        elif e.type == pygame.MOUSEWHEEL:
            self.index = max(0, min(len(rows) - 1, self.index - e.y))

    # ---- layout ----------------------------------------------------------------
    def _frame(self):
        return pygame.Rect(60, 46, 1160, 628)

    def _inner(self):
        return theme().inner(self._frame(), 36)

    def _tab_rects(self):
        g = self._inner()
        return [pygame.Rect(g.x + 4, g.y + 96 + i * 84, 52, 52) for i in range(len(TABS))]

    def _row_rects(self, n):
        g = self._inner()
        if self.index < self.scroll:
            self.scroll = self.index
        elif self.index >= self.scroll + VISIBLE:
            self.scroll = self.index - VISIBLE + 1
        self.scroll = max(0, min(self.scroll, max(0, n - VISIBLE)))
        return [(i, pygame.Rect(g.x + 112, g.y + 124 + (i - self.scroll) * 58, 560, 52))
                for i in range(self.scroll, min(n, self.scroll + VISIBLE))]

    # ---- drawing ----------------------------------------------------------------
    def draw(self, surf) -> None:
        th = theme()
        c = th.c
        st = self.game.state
        veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 160))
        surf.blit(veil, (0, 0))
        f = th.panel(surf, self._frame())
        g = self._inner()
        # header
        fname, emblem, fcol = FACTIONS[self.faction]
        th.iconbtn(surf, (g.x, g.y, 64, 64), "star", True)
        em = self.game.assets.sprite(emblem)
        surf.blit(em, em.get_rect(center=(g.x + 32, g.y + 32)))
        th.text(surf, self.station.name.upper(), (g.x + 80, g.y + 4), 4, c["accent"])
        rep = st.rep.get(self.faction, 0)
        th.text(surf, f"{fname}  ·  {standing(rep)}" + ("  ·  refuel & repair free" if self.free else ""),
                (g.x + 82, g.y + 44), 2, c["good"] if self.free else c["dim"])
        wal = th.plate(surf, (g.right - 240, g.y + 6, 240, 46))
        th.counter(surf, (wal.x + 16, wal.centery), "coin", f"{st.credits:,}", c["accent"])
        th.counter(surf, (wal.x + 140, wal.centery), "ore", str(st.ore))
        th.divider(surf, g.x, g.right, g.y + 78)
        # tabs
        for i, ((ic, label), r) in enumerate(zip(TABS, self._tab_rects())):
            sel = i == self.tab
            th.iconbtn(surf, r, ic, sel)
            if sel:
                th.text(surf, label, (r.centerx, r.bottom + 4), 2, c["accent"], "midtop")
        # list
        rows = self.rows()
        self.index = min(self.index, len(rows) - 1)
        th.text(surf, TABS[self.tab][1].upper(), (g.x + 112, g.y + 96), 2, c["dim"])
        for i, r in self._row_rects(len(rows)):
            row = rows[i]
            sel = i == self.index
            if sel:
                th.plate(surf, r, gold=True)
                th.lamp(surf, (r.x + 16, r.centery))
            elif i > self.scroll:
                th.divider(surf, r.x + 10, r.right - 10, r.y - 4)
            col = row.color or (c["accent"] if sel else c["text"])
            label = row.label if pixelfont.width(row.label, 2) < 300 else row.label[:24] + "…"
            th.counter(surf, (r.x + 34, r.centery), row.icon or "star", label, col)
            if row.pips:
                th.pips(surf, (r.x + 330, r.centery - 3), row.pips[0], row.pips[1], (120, 230, 255))
            if row.cost is not None:
                if row.cost > 0:
                    th.counter(surf, (r.right - 140, r.centery), "coin", f"{row.cost:,}",
                               c["accent"] if st.credits >= row.cost else c["bad"])
                elif row.cost < 0:
                    th.text(surf, f"+{-row.cost:,} cr", (r.right - 18, r.centery), 2, c["good"], "midright")
                else:
                    th.text(surf, "FREE", (r.right - 18, r.centery), 2, c["good"], "midright")
            elif row.pips and row.pips[0] >= row.pips[1]:
                th.text(surf, "MAX", (r.right - 18, r.centery), 2, c["good"], "midright")
        if len(rows) > VISIBLE:
            th.text(surf, f"{self.scroll + 1}-{min(len(rows), self.scroll + VISIBLE)} of {len(rows)}",
                    (g.x + 672, g.y + 96), 2, c["dim"], "topright")
        # detail card
        row = rows[self.index] if rows else None
        dx = g.x + 702
        card = th.plate(surf, (dx, g.y + 96, g.right - dx, 430))
        if row:
            ic = th.icons.get(row.icon or "star")
            if ic:
                big = pygame.transform.scale(ic, (ic.get_width() * 2, ic.get_height() * 2))
                surf.blit(big, big.get_rect(midtop=(card.centerx, card.y + 24)))
            name_lines = pixelfont.wrap(row.label, card.w - 40, 3)
            for j, ln in enumerate(name_lines[:2]):
                th.text(surf, ln, (card.centerx, card.y + 100 + j * 30), 3, row.color or c["accent"], "midtop")
            y = card.y + 104 + len(name_lines[:2]) * 30
            if row.pips:
                th.pips(surf, (card.centerx - row.pips[1] * 6, y + 2), row.pips[0], row.pips[1], (120, 230, 255))
                y += 26
            for j, ln in enumerate(pixelfont.wrap(row.detail, card.w - 44, 2)[:5]):
                th.text(surf, ln, (card.x + 22, y + 8 + j * 24), 2, c["text"])
            if row.mats:
                my = card.bottom - 178
                th.text(surf, "Materials", (card.x + 22, my - 26), 2, c["dim"])
                mx = card.x + 22
                for b, n in row.mats.items():
                    have = st.materials.get(b, 0)
                    r2 = th.counter(surf, (mx, my + 12), f"mat_{b}", f"{have}/{n}",
                                    c["good"] if have >= n else c["bad"])
                    mx = (r2.right if hasattr(r2, "right") else mx + 120) + 20
            if row.stat:
                th.text(surf, row.stat[0], (card.x + 22, card.bottom - 106), 2, c["dim"])
                th.text(surf, row.stat[1], (card.right - 22, card.bottom - 106), 2, c["good"], "topright")
            if row.verb and row.action:
                label = row.verb + (f"  {row.cost:,} cr" if row.cost and row.cost > 0 else "")
                th.prompt(surf, (card.centerx, card.bottom - 40), "E", label)
            if row.alt:
                th.text(surf, "X  sell", (card.right - 22, card.bottom - 74), 2, c["dim"], "topright")
        # footer
        fx = g.x
        for key, label in (("←", "Tabs"), ("↑", "Select"), ("E", "Use"), ("Q", "Undock")):
            r = th.key(surf, (fx + 112, g.bottom + 2), key)
            t = th.text(surf, label, (r.right + 8, g.bottom + 2), 2, c["dim"], "midleft")
            fx = t.right + 26
        del f
