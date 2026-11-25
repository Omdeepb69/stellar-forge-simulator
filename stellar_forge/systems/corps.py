"""The Survey Corps in space.

* Patrols: Corps fighters now and then cross your path and attack any raiders.
* Battles: rarely, a Corps wing is caught by a raider pack. Join in - every
  raider you down there earns Corps Merit, and winning earns more.
* The hailing channel [C]: call a tender for fuel, repairs or a tow to the
  nearest station, or an escort wing - paid with Merit or credits.

Merit is a second currency (``GameState.corps_merit``). Contact is made by
meeting the Kestrel Survey Team on a planet, or by helping in a battle.
"""
from __future__ import annotations

import random

from pygame.math import Vector2

from ..entities.allies import NAMES, CorpsShip
from . import corps_career as career

HAIL_COOLDOWN = 45.0
PENALTY_FEE = 150
MAX_STRIKES = 3
LICENCE_FEE = 400
SERVICES = {
    # key: (label, merit cost, credit cost, what it does)
    "fuel": ("Emergency refuel", 12, 160, "a tender fills your tank"),
    "repair": ("Field repair", 18, 220, "a tender patches the hull and recharges shields"),
    "tow": ("Rescue tow", 25, 320, "a tender hauls you to the nearest station"),
    "escort": ("Escort wing", 30, 380, "fighters fly with you for three minutes"),
    "strike": ("Strike wing", 45, 600, "four fighters for ninety seconds of hard fighting"),
}
STRIKE_RANK = 3


def price(state, key) -> tuple[int, int]:
    """(Merit, credits) for a service at your rank."""
    _label, merit, cr, _what = SERVICES[key]
    if career.rank(state) >= 1:
        merit, cr = int(round(merit * 0.8)), int(round(cr * 0.8))
    return merit, cr


def free_refuel(game) -> bool:
    st = game.state
    return career.rank(st) >= 4 and st.corps_free_day != int(st.world_time // career.DAY)


def has_contact(state) -> bool:
    return state.groups.get("survey", {}).get("met", 0) > 0 or state.corps_merit_total > 0 or \
        state.stats.get("corps_battles", 0) > 0


def emergency_reason(scene, state) -> str | None:
    """Return a short reason if the pilot is in a genuine emergency, else None."""
    if state.fuel <= state.max_fuel * 0.25:
        return "low fuel"
    if state.hull <= state.max_hull * 0.35:
        return "hull critical"
    ship_pos = scene.ship.pos
    nearby = [e for e in scene.enemies if e.alive and e.pos.distance_to(ship_pos) < 3500]
    if len(nearby) >= 3 or any(getattr(e, "is_boss", False) or getattr(e, "captain", False) for e in nearby):
        return "heavy hostiles"
    return None


class CorpsWing:
    def __init__(self, scene):
        self.scene = scene
        self.game = scene.game
        self.ships: list[CorpsShip] = []
        self.patrol_timer = random.uniform(70, 140)
        self.battle_timer = random.uniform(150, 260)
        self.battle = None               # {"pos", "raiders": [...], "allies": [...], "joined": bool}
        self.hail_cd = 0.0

    # ---------------------------------------------------------------- spawning
    def _danger(self) -> float:
        return self.scene.sector_danger()

    def _ring(self, lo=2400, hi=3200) -> Vector2:
        return self.scene.ship.pos + Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(lo, hi)

    def spawn_patrol(self) -> None:
        pos = self._ring(2200, 2800)
        names = random.sample(NAMES, 2)
        for k in range(random.choice([1, 2])):
            s = CorpsShip(self.game, pos + Vector2(k * 90, 0), "fighter", "patrol", self._danger(), names[k])
            s.anchor = self.scene.ship.pos + (pos - self.scene.ship.pos) * 0.5
            self.ships.append(s)

    def start_battle(self, pos: Vector2 | None = None) -> dict:
        from ..entities.enemies import Raider
        pos = Vector2(pos) if pos is not None else self._ring(2600, 3300)
        danger = max(1.0, self._danger())
        allies = []
        for k, name in enumerate(random.sample(NAMES, random.choice([2, 3]))):
            s = CorpsShip(self.game, pos + Vector2(k * 120 - 120, 60), "fighter", "patrol", danger, name)
            s.anchor = Vector2(pos)
            s.hp = s.max_hp * random.uniform(0.55, 0.9)            # they've been at it a while
            allies.append(s)
        raiders = []
        for k in range(random.randint(3, 5)):
            r = Raider(self.game, pos + Vector2(1, 0).rotate(k * 72) * random.uniform(380, 520), danger,
                       elite=danger > 2.5 and k == 0)
            r.aggro = True
            r.corps_battle = True
            raiders.append(r)
        self.ships += allies
        self.scene.enemies += raiders
        self.battle = {"pos": Vector2(pos), "allies": allies, "raiders": raiders, "joined": False, "t": 0.0}
        self.game.toasts.add("Corps distress call: Survey Corps wing under attack!", (255, 190, 90), 4,
                             icon="scanner")
        self.game.audio.play("alarm", 0.5)
        return self.battle

    # ---------------------------------------------------------------- per frame
    def update(self, dt) -> list:
        sc = self.scene
        ship = sc.ship
        self.hail_cd = max(0.0, self.hail_cd - dt)
        shots = []
        for s in self.ships:
            shots += s.update(dt, ship, sc.enemies, sc.particles)
            if s.role == "fighter" and s.mode == "escort":
                s.timer -= dt
                if s.timer <= 0:
                    s.mode = "depart"
            if s.mode == "service" and s.pos.distance_to(ship.pos) < 150:
                self._deliver(s)
        for s in self.ships:
            if not s.alive:
                sc.particles.explosion(s.pos.x, s.pos.y, 1.2)
                self.game.audio.play("explosion", 0.6)
                self.game.toasts.add(f"{s.name} lost!", (255, 140, 100), 3)
        self.ships = [s for s in self.ships if s.alive and not s.gone and
                      s.pos.distance_to(ship.pos) < 14000]
        self._update_battle(dt)
        self._maybe_spawn(dt)
        return shots

    def _maybe_spawn(self, dt) -> None:
        sc = self.scene
        q = self.game.quests
        self._captain()                     # a contract target shows up whatever the story is doing
        if q.cid in ("awaken", "signal", "raiders", "boss") or sc.in_nebula:
            return
        self.patrol_timer -= dt
        self.battle_timer -= dt
        if self.patrol_timer <= 0:
            self.patrol_timer = random.uniform(90, 170) * (0.6 if career.rank(self.game.state) >= 4 else 1)
            if not any(s.mode == "patrol" for s in self.ships):
                self.spawn_patrol()
        if self.battle_timer <= 0:
            self.battle_timer = random.uniform(200, 340)
            if self.battle is None and random.random() < 0.6 and len(sc.enemies) < 3:
                self.start_battle()

    def _captain(self) -> None:
        """A raider captain on a Corps contract shows up when you reach their sector."""
        from ..entities.enemies import Raider
        from ..world.universe import Universe
        job = self.game.state.corps_job
        sc = self.scene
        if not job or job["kind"] != "captain" or any(getattr(e, "captain", False) for e in sc.enemies):
            return
        if list(Universe.sector_coords(sc.ship.pos)) != list(job["sector"]):
            return
        pos = self._ring(2400, 2900)
        danger = max(1.5, self._danger())
        boss = Raider(self.game, pos, danger + 1.0, elite=True, quest=True)
        boss.max_hp *= 3
        boss.hp = boss.max_hp
        boss.captain = True
        boss.name = f"Captain {job['name']}"
        boss.bounty *= 2
        sc.enemies.append(boss)
        for k in range(2):
            sc.enemies.append(Raider(self.game, pos + Vector2(120, 0).rotate(k * 180 + 90), danger))
        self.game.toasts.add(f"{boss.name}'s ship detected - with escorts!", (255, 120, 90), 4, icon="skull")
        self.game.audio.play("alarm", 0.6)

    def captain(self):
        return next((e for e in self.scene.enemies if getattr(e, "captain", False)), None)

    def _update_battle(self, dt) -> None:
        b = self.battle
        if b is None:
            return
        st = self.game.state
        b["t"] += dt
        ship = self.scene.ship
        if ship.pos.distance_to(b["pos"]) > 9000:          # you left (or warped away): no win, no loss
            self.battle = None
            for s in b["allies"]:
                s.mode = "depart"
            return
        if ship.pos.distance_to(b["pos"]) < 1800:
            b["joined"] = True
        b["raiders"] = [r for r in b["raiders"] if r.alive and r in self.scene.enemies]
        allies = [s for s in b["allies"] if s.alive and s in self.ships]
        if not b["raiders"]:
            self.battle = None
            st.bump("corps_battles")
            if allies and b["joined"]:
                merit, cr = 20 + 5 * len(allies), 120 + 40 * len(allies)
                st.earn(cr)
                career.earn(self.game, merit)
                self.game.banner.show("The Corps salutes you", f"+{merit} Corps Merit  ·  +{cr} cr", 3.5)
                self.game.audio.play("relic", 0.7)
                self.game.dialogue.say([(f"settler:6:{allies[0].name}", random.choice(THANKS))])
            for s in allies:
                s.mode, s.timer = "depart", 0
            return
        if not allies:
            self.battle = None
            if b["joined"]:
                self.game.toasts.add("The Corps wing was lost...", (255, 140, 100), 3)
            for r in b["raiders"]:
                r.corps_battle = False

    def on_kill(self, e, by_player: bool) -> None:
        """A raider died: Merit if it was part of a Corps fight you joined."""
        if getattr(e, "captain", False):
            career.progress(self.game, "captain")
        if getattr(e, "corps_battle", False) and by_player:
            if self.battle is not None:
                self.battle["joined"] = True
            career.earn(self.game, 6)
            self.scene.floaters.add(e.pos.x, e.pos.y - 50, "+6 Merit", (255, 190, 90))
        elif by_player and any(s.target is e for s in self.ships):
            career.earn(self.game, 2)                  # assisting a patrol

    def target_for(self, enemy, ship):
        """Raiders shoot whatever is closest: you, or a Corps ship."""
        best, bd = ship, enemy.pos.distance_squared_to(ship.pos)
        if getattr(enemy, "is_boss", False):
            return ship
        for s in self.ships:
            keen = getattr(enemy, "corps_battle", False) or getattr(enemy, "prefer_allies", False)
            d = enemy.pos.distance_squared_to(s.pos) * (0.5 if keen else 1.3)
            if d < bd:
                best, bd = s, d
        return best

    def hit(self, bullet) -> bool:
        for s in self.ships:
            if s.pos.distance_squared_to(bullet.pos) < s.radius ** 2:
                s.hurt(bullet.damage)
                self.scene.particles.burst(bullet.pos.x, bullet.pos.y, 8, 140, [(255, 200, 120), (255, 255, 255)])
                return True
        return False

    def draw(self, surf, cam) -> None:
        for s in self.ships:
            s.draw(surf, cam)

    # ---------------------------------------------------------------- the hailing channel
    def hail(self) -> None:
        from ..scenes.choice import ChoiceScene
        g, st = self.game, self.game.state
        if not has_contact(st):
            g.toasts.add("No Corps contact yet - meet the Kestrel Survey Team, or help a Corps ship in a fight",
                         (255, 190, 90), 4, icon="scanner")
            g.audio.play("deny")
            return
        if st.corps_banned:
            g.audio.play("deny")
            body = ("Channel locked. Your Survey Corps calling licence has been revoked.\n"
                    "Dock at any station to purchase a new Survey Corps licence.")
            g.scenes.push(ChoiceScene(g, "settler:7:Corps Dispatch", "Survey Corps — Banned", body,
                                      [("Close channel", None)], can_cancel=True))
            return
        if st.corps_fine > 0:
            body = (f"You have an unpaid {st.corps_fine} cr false-alarm penalty "
                    f"({st.corps_strikes}/{MAX_STRIKES} strikes).\n"
                    "Settle your penalty before requesting Survey Corps support.")
            opts = [(f"Pay penalty ({st.corps_fine} cr)", self._settle_fine,
                     "Clear your penalty and restore Corps support"),
                    ("Close channel", None)]
            g.scenes.push(ChoiceScene(g, "settler:7:Corps Dispatch", "Survey Corps — Unpaid Penalty", body,
                                      opts, can_cancel=True))
            return
        opts = []
        reason = emergency_reason(self.scene, st)
        if reason:
            opts.append((f"Emergency SOS  -  free ({reason})", self.emergency_sos,
                         "Dispatch an immediate Corps rescue wing at no charge"))
        else:
            opts.append(("Emergency SOS  -  call wing", self.emergency_sos,
                         f"Free in real emergencies; false alarm = {PENALTY_FEE} cr penalty"))
        busy = self.hail_cd > 0
        for key, (label, _m, _c, what) in SERVICES.items():
            if key == "strike" and career.rank(st) < STRIKE_RANK:
                continue
            merit, cr = price(st, key)
            if busy:
                opts.append((f"{label}  -  ready in {self.hail_cd:.0f} s", None, what))
            elif key == "fuel" and free_refuel(g):
                opts.append((f"{label}  -  free (Commander)", self._buy(key, "free"), what))
            elif st.corps_merit >= merit:                       # Merit first; credits when you're short
                opts.append((f"{label}  -  {merit} Merit", self._buy(key, "merit"), what))
            else:
                opts.append((f"{label}  -  {cr} cr", self._buy(key, "credits"), f"{what} ({merit} Merit)"))
        opts.insert(1, ("Corps contracts" + ("  (active)" if st.corps_job else ""),
                        lambda: career.menu(g), "bounties, captain hunts, charting runs"))
        opts.append(("Close channel", None))
        body = (f"Survey Corps, Sector Nine. Go ahead, {career.rank_name(st)}. "
                f"You hold {st.corps_merit} Merit and {st.credits:,} cr.")
        g.scenes.push(ChoiceScene(g, "settler:7:Corps Dispatch", "Survey Corps channel", body, opts, can_cancel=True))

    def emergency_sos(self) -> None:
        """Answer a distress call for free in real emergencies, or issue a penalty."""
        g, st = self.game, self.game.state
        if st.corps_banned:
            g.toasts.add("Corps licence revoked — buy a licence at a station.", (255, 90, 90), 3.5, icon="skull")
            g.audio.play("deny")
            return
        if st.corps_fine > 0:
            g.toasts.add(f"Unpaid penalty ({st.corps_fine} cr) — pay it before calling the Corps.", (255, 160, 80), 3.5)
            g.audio.play("deny")
            return
        reason = emergency_reason(self.scene, st)
        if not reason:
            self._false_alarm()
            return
        st.bump("corps_calls")
        names = random.sample(NAMES, 2)
        for k in range(2):
            s = CorpsShip(g, self._ring(1500, 1900), "fighter", "escort", self._danger(), names[k])
            s.timer = 120.0
            s.offset = Vector2((-160, 160)[k], 120)
            self.ships.append(s)
        if reason == "low fuel":
            t = CorpsShip(g, self._ring(1700, 2100), "tender", "service", self._danger(), "KST Mule")
            t.service = "fuel"
            self.ships.append(t)
        g.toasts.add(f"Emergency SOS ({reason}) — Corps wing inbound!", (120, 255, 160), 3.5, icon="scanner")
        g.audio.play("relic", 0.5)

    def _false_alarm(self) -> None:
        from ..scenes.choice import ChoiceScene
        g, st = self.game, self.game.state
        body = (f"No emergency detected on your sensors!\n"
                f"False-alarm dispatch carries a {PENALTY_FEE} cr penalty "
                f"(strikes: {st.corps_strikes}/{MAX_STRIKES}).")
        opts = [
            (f"Pay penalty now ({PENALTY_FEE} cr)", self._pay_penalty_now,
             "Settle immediately (insufficient credits = ban)"),
            ("Refuse / Pay later", self._refuse_penalty,
             f"Corps won't help until paid ({MAX_STRIKES} unpaid = ban)"),
        ]
        g.scenes.push(ChoiceScene(g, "settler:7:Corps Dispatch", "False Alarm Penalty", body, opts, can_cancel=False))

    def _pay_penalty_now(self) -> None:
        g, st = self.game, self.game.state
        if st.credits >= PENALTY_FEE:
            st.credits -= PENALTY_FEE
            st.corps_fine = 0
            g.toasts.add(f"Corps penalty paid (-{PENALTY_FEE} cr)", (255, 190, 90), 3)
            g.audio.play("pickup", 0.6)
        else:
            st.corps_banned = True
            st.corps_fine = PENALTY_FEE
            g.toasts.add("Insufficient credits! Corps banned you — buy a licence at a station.",
                         (255, 90, 90), 4.5, icon="skull")
            g.audio.play("deny", 0.8)

    def _refuse_penalty(self) -> None:
        g, st = self.game, self.game.state
        st.corps_fine = PENALTY_FEE
        st.corps_strikes += 1
        if st.corps_strikes >= MAX_STRIKES:
            st.corps_banned = True
            g.toasts.add("3 unpaid penalties! Corps licence revoked — buy a new licence at a station.",
                         (255, 90, 90), 4.5, icon="skull")
        else:
            g.toasts.add(f"Unpaid penalty ({PENALTY_FEE} cr, strike {st.corps_strikes}/{MAX_STRIKES}). "
                         "Corps won't help until paid.", (255, 160, 80), 4)
        g.audio.play("deny", 0.7)

    def _settle_fine(self) -> None:
        g, st = self.game, self.game.state
        if st.credits >= st.corps_fine:
            st.credits -= st.corps_fine
            st.corps_fine = 0
            g.toasts.add("Corps penalty cleared! Channel restored.", (120, 255, 160), 3)
            g.audio.play("pickup", 0.6)
        else:
            st.corps_banned = True
            g.toasts.add("Insufficient credits! Corps banned you — buy a licence at a station.",
                         (255, 90, 90), 4.5, icon="skull")
            g.audio.play("deny", 0.8)

    def _buy(self, key, pay):
        def go():
            g, st = self.game, self.game.state
            merit, cr = price(st, key)
            if pay == "free":
                st.corps_free_day = int(st.world_time // career.DAY)
            elif pay == "merit":
                if st.corps_merit < merit:
                    return
                st.corps_merit -= merit
            else:
                if st.credits < cr:
                    g.toasts.add("Not enough credits", (255, 120, 120), 2)
                    g.audio.play("deny")
                    return
                st.credits -= cr
            self.call(key)
        return go

    def call(self, key: str) -> None:
        """Dispatch a ship for ``key`` (fuel, repair, tow, escort)."""
        g = self.game
        st = g.state
        self.hail_cd = HAIL_COOLDOWN * (0.5 if career.rank(st) >= 2 else 1)
        st.bump("corps_calls")
        if key in ("escort", "strike"):
            n = 4 if key == "strike" else (3 if career.rank(st) >= 2 else 2)
            names = random.sample(NAMES, n)
            for k in range(n):
                s = CorpsShip(g, self._ring(1600, 2000), "fighter", "escort", self._danger() + (1 if key == "strike"
                                                                                               else 0), names[k])
                s.timer = 90.0 if key == "strike" else 180.0
                s.offset = Vector2((-150, 150, -260, 260)[k], (120, 120, -60, -60)[k])
                self.ships.append(s)
            g.toasts.add("Strike wing inbound!" if key == "strike" else "Escort wing inbound", (255, 190, 90), 3,
                         icon="scanner")
            return
        s = CorpsShip(g, self._ring(1800, 2300), "tender", "service", self._danger(), "KST Mule")
        s.service = key
        self.ships.append(s)
        g.toasts.add(f"Tender dispatched: {SERVICES[key][0].lower()}", (255, 190, 90), 3, icon="scanner")

    def _deliver(self, s) -> None:
        g, st, sc = self.game, self.game.state, self.scene
        key = s.service
        s.mode, s.service = "depart", None
        if key == "fuel":
            st.fuel = st.max_fuel
            g.banner.show("Tank full", "The Corps tender pumps you full and peels away", 2.5)
        elif key == "repair":
            st.hull = st.max_hull
            st.shield = st.max_shield
            g.banner.show("Hull restored", "Corps engineers patch you up in a hurry", 2.5)
        elif key == "tow":
            station = self._nearest_station()
            if station is not None:
                t = sc.t
                sc.place_ship(station.pos(t) + Vector2(140, 0), station.vel(t))
                s.pos = sc.ship.pos + Vector2(-200, 80)
                st.fuel = max(st.fuel, st.max_fuel * 0.25)
                g.banner.show("Towed to safety", f"The tender drops you beside {station.name}", 3)
        g.audio.play("relic", 0.5)

    def _nearest_station(self):
        sc = self.scene
        t = sc.t
        best = None
        for sec in sc.sectors:
            for b in sec.bodies:
                if b.kind == "station":
                    d = b.pos(t).distance_to(sc.ship.pos)
                    if best is None or d < best[0]:
                        best = (d, b)
        if best is not None:
            return best[1]
        return self.game.universe.find_body("0,0:st")


THANKS = ["Thanks for the assist, pilot. The Corps won't forget it.",
          "Good shooting! Drinks are on us at the next station. Well - Merit's on us.",
          "We had them, we totally had them. ...Thank you.",
          "Pilot, you're welcome in Corps space any time. Hail us if you need a hand."]
