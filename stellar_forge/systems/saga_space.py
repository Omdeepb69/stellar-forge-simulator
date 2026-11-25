"""Act III and the side arcs, as they play out in space (see systems/saga.py)."""
from __future__ import annotations

import random

from pygame.math import Vector2

from . import saga as S

TEAL = (120, 255, 230)
ARK_COL = (255, 220, 150)
HOME_STATION = "0,0:st"


class SagaSpace:
    def __init__(self, scene):
        self.scene = scene
        self.game = scene.game
        self.trial = None            # {"kind": "making", "t": seconds held, "wave": countdown}
        self.ark = None              # the New Dawn while it follows you home
        self.convoy = []             # Remnant defectors following you to Haven
        self.wave_t = 8.0
        self.penitent = None
        self.final = None

    @property
    def st(self):
        return self.game.state

    @property
    def s(self) -> dict:
        return S.data(self.game.state)

    def cid(self) -> str:
        return self.game.quests.cid

    # ---------------------------------------------------------------- places
    def waystones(self) -> list:
        """[(kind, pos, done)] once the road is open."""
        if self.cid() not in ("road", "judgment", "legend"):
            return []
        u = self.game.universe
        return [(k, S.waystone_pos(u, k), k in self.s["waystones"]) for k in S.WAYSTONES]

    def bell_pos(self) -> Vector2:
        from .quests import signal_position
        return signal_position(self.game.universe)

    def ark_pos(self) -> Vector2:
        return S.ark_pos(self.game.universe)

    # ---------------------------------------------------------------- per frame
    def update(self, dt) -> None:
        sc = self.scene
        s = self.s
        if s["ark"] == "escort":
            self._update_ark(dt)
        for d in list(self.convoy):
            if not d.alive or d.gone:
                self.convoy.remove(d)
                if not d.alive:
                    self.game.toasts.add("The defectors didn't make it.", (255, 140, 100), 3)
                continue
            if d.pos.distance_to(self._haven()) < 1600:
                self.convoy.remove(d)
                d.mode = "depart"
                s["defectors"] = s.get("defectors", 0) + 1
                self.st.add_rep("remnant", 15)
                self.st.earn(150)
                self.game.banner.show("Defectors safe at Haven", "+15 Remnant standing  ·  +150 cr", 3.0)
                self.game.audio.play("relic", 0.5)
                if self.st.rep.get("remnant", -60) >= 0 and not s.get("free_fleet"):
                    s["free_fleet"] = True
                    self.game.toasts.add("The Remnant Free Fleet now counts you a friend", (130, 255, 150), 4)
        if self.trial is not None and self.trial["kind"] == "making":
            self._update_making(dt)
        if self.final is not None and not self.final.alive and self.final not in sc.enemies:
            self.final = None

    def _haven(self) -> Vector2:
        return self.game.universe.find_body(HOME_STATION).pos(self.scene.t)

    def _spawn_raiders(self, around: Vector2, n: int, prefer_allies: bool = False) -> None:
        from ..entities.enemies import Raider
        danger = max(1.5, self.scene.sector_danger())
        for k in range(n):
            pos = around + Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(1800, 2400)
            r = Raider(self.game, pos, danger)
            r.aggro = True
            r.prefer_allies = prefer_allies
            self.scene.enemies.append(r)

    def _update_ark(self, dt) -> None:
        s = self.s
        if self.ark is None:
            from ..entities.allies import CorpsShip
            sc = self.scene
            self.ark = CorpsShip(self.game, sc.ship.pos - sc.ship.forward * 400, "tender", "follow", 2.0,
                                 "New Dawn", art="generated/ships/hauler.png", tint=(230, 225, 210), hp=900,
                                 colour=ARK_COL)
            self.ark.radius = 60
            sc.corps.ships.append(self.ark)
        if not self.ark.alive:
            self.ark = None
            s["ark"] = "known"
            self.game.banner.show("The ark's shields failed", "It limped back into the nebula. Try again.", 3.5)
            return
        self.wave_t -= dt
        if self.wave_t <= 0:
            self.wave_t = random.uniform(20, 28)
            self._spawn_raiders(self.ark.pos, random.randint(2, 3), prefer_allies=True)
            self.game.toasts.add("Raiders closing on the ark!", (255, 140, 100), 2.5)
        if self.ark.pos.distance_to(self._haven()) < 1600:
            self.ark.mode = "depart"
            self.ark.gone = True
            self.ark = None
            s["ark"] = "rescued"
            st = self.st
            st.earn(1500)
            st.add_rep("haven", 20)
            self.game.dialogue.say(S.ARK_HOME)
            self.game.banner.show("The New Dawn is home", "2,000 survivors safe  ·  +1500 cr", 4.0)
            self.game.audio.play("relic", 1.0)
            self.game.save()

    def _update_making(self, dt) -> None:
        tr = self.trial
        pos = S.waystone_pos(self.game.universe, "making")
        if self.scene.ship.pos.distance_to(pos) > 4200:
            self.trial = None
            self.game.toasts.add("You left the waystone - its light fades. Return to try again.", TEAL, 3.5)
            return
        tr["t"] += dt
        tr["wave"] -= dt
        if tr["wave"] <= 0:
            tr["wave"] = 9.0
            self._spawn_raiders(pos, 2 + int(tr["t"] // 20))
        if tr["t"] >= S.MAKING_TIME:
            self.trial = None
            self._complete("making")

    # ---------------------------------------------------------------- interaction
    def prompt(self):
        """(label, colour) for the nearest saga thing in reach, or None."""
        hit = self._near()
        return None if hit is None else (hit[0], hit[1])

    def interact(self) -> bool:
        hit = self._near()
        if hit is None:
            return False
        hit[2]()
        return True

    def _near(self):
        ship = self.scene.ship.pos
        s = self.s
        for kind, pos, done in self.waystones():
            if pos.distance_to(ship) < 700:
                name = S.WAY_INFO[kind][0]
                if done:
                    return (f"{name} (its trial is passed)", (150, 160, 170), lambda: None)
                if self.trial is not None:
                    return (f"{name} - hold on! {S.MAKING_TIME - self.trial['t']:.0f} s", TEAL, lambda: None)
                return (f"[E] Touch the {name}", S.WAY_INFO[kind][2], lambda k=kind: self._begin(k))
        if s["ark"] == "known" and self.ark_pos().distance_to(ship) < 800:
            return ("[E] Hail the ark New Dawn", ARK_COL, self._hail_ark)
        if self.cid() == "judgment" and self.final is None and self.bell_pos().distance_to(ship) < 900:
            return ("[E] Ring the Bell - call the Makers", TEAL, self._ring)
        return None

    def _begin(self, kind: str) -> None:
        g = self.game
        g.audio.play("relic", 0.6)
        if kind == "making":
            self.trial = {"kind": "making", "t": 0.0, "wave": 3.0}
            g.banner.show("Trial of Making", f"Hold the waystone for {S.MAKING_TIME:.0f} seconds", 3.0)
            g.dialogue.say([("ai", "It's waking - and every raider in range can hear it. Stay close and hold.")])
        elif kind == "memory":
            from ..scenes.choice import ChoiceScene
            title, body, opts = self._question(0, "")
            g.scenes.push(ChoiceScene(g, "ai", title, body, opts))
        else:
            self._mercy()

    def _question(self, k: int, prefix: str):
        q, answers = S.MEMORY_QUESTIONS[k]
        opts = []
        for label, right in answers:
            opts.append((label, (lambda r=right: self._answer(k, r))))
        return (f"Trial of Memory  ({k + 1}/3)", prefix + "The waystone asks: " + q, opts)

    def _answer(self, k: int, right: bool):
        if not right:
            st = self.st
            st.hull = max(1.0, st.hull - st.max_hull * 0.12)
            self.game.audio.play("deny")
            return self._question(k, "The waystone dims and the hull groans. ")
        self.game.audio.play("relic", 0.4 + 0.2 * k)
        if k + 1 < len(S.MEMORY_QUESTIONS):
            return self._question(k + 1, "A glyph lights. ")
        self._complete("memory")
        return None

    def _mercy(self) -> None:
        from ..entities.enemies import Dreadnought
        g = self.game
        if self.penitent is not None and self.penitent.alive:
            return
        pos = S.waystone_pos(g.universe, "mercy") + Vector2(600, -200)
        p = Dreadnought(g, pos, max(2.5, self.scene.sector_danger()) + 1.0, name="The Penitent")
        p.hp = p.max_hp * 0.45
        p.passive = True
        p.saga_role = "penitent"
        self.scene.enemies.append(p)
        self.penitent = p
        g.dialogue.say(S.PENITENT_LINES, on_done=self._mercy_choice)

    def _mercy_choice(self) -> None:
        from ..scenes.choice import ChoiceScene
        g = self.game

        def spare():
            p = self.penitent
            if p is not None:
                p.alive = False
                self.scene.particles.burst(p.pos.x, p.pos.y, 40, 300, [(200, 170, 255), (255, 255, 255)])
            self.st.add_rep("remnant", 30)
            self.s["penitent"] = "spared"
            g.dialogue.say([("pirate", "...Thank you. If you ever need us, Voyager, the Free Fleet will come.")])
            self._complete("mercy")

        def destroy():
            p = self.penitent
            if p is not None:
                p.passive = False
                p.aggro = True
            g.dialogue.say([("pirate", "Then we'll go down fighting. Remnant, to arms!")])
        g.scenes.push(ChoiceScene(g, "pirate", "Trial of Mercy",
                                  "The Penitent drifts, engines dead, guns cold. The waystone waits for your answer.",
                                  [("Spare them - let the Penitent go", spare, "the Remnant will remember"),
                                   ("Destroy them - they burned Earth-Prime", destroy, "a hard fight")]))

    def on_kill(self, e) -> None:
        role = getattr(e, "saga_role", None)
        if role == "penitent":
            self.s["penitent"] = "destroyed"
            self.penitent = None
            self._complete("mercy")
        elif role == "last_smith":
            self._victory()

    def _complete(self, kind: str) -> None:
        g, s = self.game, self.s
        if kind in s["waystones"]:
            return
        s["waystones"].append(kind)
        g.banner.show(f"{S.WAY_INFO[kind][0]}: trial passed", f"{len(s['waystones'])}/3 waystones", 3.5)
        g.audio.play("relic", 0.9)
        g.state.chapter_progress = len(s["waystones"])
        if len(s["waystones"]) >= 3 and self.cid() == "road":
            g.dialogue.say([("ai", "All three waystones answer. The Bell is ringing on its own now."),
                            ("ai", "The Makers are here, Voyager. Go back to the Bell and ring it once more.")])
            g.quests.advance()
        g.save()

    def _hail_ark(self) -> None:
        from ..scenes.choice import ChoiceScene
        g = self.game

        def escort():
            self.s["ark"] = "escort"
            self.wave_t = 6.0
            g.dialogue.say([("survivor", "Haven's alive? Then lead the way, Voyager. We'll stay right behind you.")])
        g.dialogue.say(S.ARK_HAIL, on_done=lambda: g.scenes.push(ChoiceScene(
            g, "survivor", "The New Dawn",
            "Two thousand sleepers and a crew of nine. Their drive can just about follow you - if you keep the "
            "raiders off them.",
            [("Escort the ark home to Haven", escort, "they follow you; raiders will come"),
             ("Not yet - I'll come back", None, "")])))

    def _ring(self) -> None:
        from ..entities.allies import CorpsShip
        from ..entities.enemies import Dreadnought
        g, sc = self.game, self.scene
        pos = self.bell_pos() + Vector2(0, -1400)
        boss = Dreadnought(g, pos, 5.5, name="The Last Smith")
        boss.max_hp *= 2.2
        boss.hp = boss.max_hp
        boss.aggro = True
        boss.saga_role = "last_smith"
        boss.sprite = g.assets.image("generated/ships/dreadnought.png", tint=(150, 255, 235))
        sc.enemies.append(boss)
        self.final = boss
        art = {"corps": (None, None, (255, 190, 90)),
               "free": ("alien/alien_ship/alienShip.png", (150, 230, 170), (130, 255, 150)),
               "ark": ("generated/ships/scout.png", (230, 225, 210), (200, 220, 255)),
               "frontier": ("generated/ships/corps_fighter.png", (190, 255, 190), (170, 255, 170))}
        lines = [("ai", "The Last Smith. It isn't here to destroy us - it's here to see who stands with us.")]
        say = {"corps": ("settler:7:Professor Lattice", "Kestrel wing on your flank, Voyager! The Corps flies with you."),
               "free": ("pirate", "Exarch Sonn, Free Fleet. We remember mercy. Weapons hot!"),
               "ark": ("survivor", "New Dawn lancers - for Earth-Prime, and for Asha!"),
               "frontier": ("settler:2:Rivet", "*BZZT* FRONTIER MILITIA ONLINE. WE BROUGHT FRIENDS. AND BOLTS.")}
        for who, label, n in S.allies_for(g):
            a, tint, colour = art[who]
            for k in range(n):
                ally = CorpsShip(g, sc.ship.pos + Vector2(1, 0).rotate(random.uniform(0, 360)) * 500, "fighter",
                                 "escort", 4.0, f"{label} {k + 1}", art=a, tint=tint, colour=colour)
                ally.timer = 900.0
                sc.corps.ships.append(ally)
            lines.append(say[who])
        g.dialogue.say(lines)
        g.audio.play("alarm", 0.8)

    def _victory(self) -> None:
        g = self.game
        tier, lines = S.verdict(g)
        self.s["verdict"] = tier
        for a in self.scene.corps.ships:
            a.mode = "depart"
        g.quests.advance()                    # -> "legend"
        g.state.bump("act3_done")
        from ..scenes.act_two import CaptionScene
        caps = [("The Last Smith lowers its hammer, and speaks with a voice like a bell.", (210, 240, 235)),
                ("'Seedwalker. We planted you to wake if a Forge stirred. We did not expect you to choose.'",
                 (210, 240, 235))] + [(ln, (225, 230, 245)) for ln in lines]
        g.scenes.push(CaptionScene(g, caps, "VOYAGER ETERNAL", "the end of the Makers' road"), fade=True,
                      force=True)
        g.save()

    # ---------------------------------------------------------------- drawing
    def draw(self, surf, cam) -> None:
        from ..entities.bodies import blit_pix
        for kind, pos, done in self.waystones():
            if not cam.visible(pos, 400):
                continue
            col = (110, 120, 130) if done else S.WAY_INFO[kind][2]
            img = self.game.assets.image("generated/ships/forge_gate.png", tint=col)
            sx, sy = cam.to_screen(pos)
            blit_pix(surf, img, (sx, sy), max(24, 420 * cam.zoom), key=("way", kind, done))
        if self.s["ark"] == "known":
            pos = self.ark_pos()
            if cam.visible(pos, 300):
                img = self.game.assets.image("generated/ships/hauler.png", tint=(230, 225, 210))
                blit_pix(surf, img, cam.to_screen(pos), max(16, 220 * cam.zoom), key=("ark",))

    def arrows(self, surf, cam) -> None:
        from ..ui import hud
        ship = self.scene.ship.pos
        for kind, pos, done in self.waystones():
            if not done and not cam.visible(pos, 60, 0):
                hud.edge_arrow(surf, cam.to_screen(pos), S.WAY_INFO[kind][2], S.WAY_INFO[kind][0],
                               pos.distance_to(ship))
        s = self.s
        if s["ark"] == "known":
            pos = self.ark_pos()
            if not cam.visible(pos, 60, 0):
                hud.edge_arrow(surf, cam.to_screen(pos), ARK_COL, "New Dawn ark (rumour)", pos.distance_to(ship))
        elif s["ark"] == "escort":
            pos = self._haven()
            if not cam.visible(pos, 60, 0):
                hud.edge_arrow(surf, cam.to_screen(pos), ARK_COL, "Haven: bring the ark home", pos.distance_to(ship))
        if self.cid() == "judgment" and self.final is None:
            pos = self.bell_pos()
            if not cam.visible(pos, 60, 0):
                hud.edge_arrow(surf, cam.to_screen(pos), TEAL, "The Bell", pos.distance_to(ship))

    def objective_line(self) -> str | None:
        s = self.s
        if s["ark"] == "escort" and self.ark is not None:
            return f"New Dawn: lead the ark home to Haven (hull {self.ark.hp / self.ark.max_hp * 100:.0f}%)"
        if self.trial is not None:
            return f"Trial of Making: hold the waystone ({S.MAKING_TIME - self.trial['t']:.0f} s)"
        if s["ark"] == "known" and self.game.state.boss_defeated:
            return "Side: find the New Dawn ark, hidden in a nebula"
        return None
