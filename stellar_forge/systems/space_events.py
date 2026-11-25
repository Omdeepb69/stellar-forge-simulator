"""Random encounters that keep the infinite galaxy surprising.

The director rolls a new event every minute or so once the campaign has
opened up: distress beacons (or traps), drifting cargo pods, comet showers,
solar flares and pirates who would rather be paid than fight.
"""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from .. import config
from ..core.assets import glow
from ..entities.enemies import Raider
from ..entities.projectiles import Pickup
from ..systems.items import roll_mod
from ..ui.text import text
from ..core.assets import rot as _rot


class SpaceEvent:
    label = ""
    interact_range = 360

    def __init__(self, scene, pos):
        self.scene = scene
        self.game = scene.game
        self.pos = Vector2(pos)
        self.alive = True

    def prompt(self) -> str | None:
        return None

    def interact(self) -> None: ...
    def update(self, dt) -> None: ...
    def draw(self, surf, cam, clock) -> None: ...

    def near(self) -> bool:
        return self.pos.distance_to(self.scene.ship.pos) < self.interact_range


# ----------------------------------------------------------------------------
class Beacon(SpaceEvent):
    label = "Distress beacon"

    def __init__(self, scene, pos):
        super().__init__(scene, pos)
        self.trap = random.random() < 0.4
        self.scanned = False
        self.img = self.game.assets.image("generated/space/beacon.png", crop=True)

    def prompt(self):
        return "[E] Answer the distress call" if self.near() else None

    def draw(self, surf, cam, clock):
        sx, sy = cam.to_screen(self.pos)
        z = 2 if cam.zoom > 0.45 else 1
        for k in range(3):
            r = ((clock * 90 + k * 60) % 180) * z
            pygame.draw.circle(surf, (255, 90, 70), (sx, sy), r, 1)
        img = _rot(self.img, math.sin(clock) * 10, z)
        surf.blit(img, img.get_rect(center=(sx, sy)))

    def interact(self):
        from ..scenes.choice import ChoiceScene
        self.game.scenes.push(ChoiceScene(self.game, "survivor", "Distress Call",
                                          "\"...anyone? Life support failing. Please...\" The signal is weak "
                                          "and keeps cutting out.", self._options()))

    def _options(self):
        st = self.game.state
        opts = [("Dock and help", self._help, "Could be genuine. Could be bait.")]
        if not self.scanned:
            opts.append(("Scan the vessel first (3 scan data)", self._scan if st.scan_data >= 3 else self._no_data,
                         "Spend data to read the transponders"))
        opts.append(("Leave them", self._leave, ""))
        return opts

    def _no_data(self):
        self.game.audio.play("deny")
        return ("Distress Call", "Not enough scan data. Sell less, scan more.", self._options())

    def _scan(self):
        self.game.state.scan_data -= 3
        self.scanned = True
        body = ("Scan complete: raider transponders are hidden under the distress signal. It's a trap."
                if self.trap else "Scan complete: one life sign, faint but real. They need you.")
        return ("Scan Results", body, self._options())

    def _leave(self):
        self.alive = False
        if not self.trap:
            self.game.state.add_rep("haven", -2)

    def _help(self):
        st, sc = self.game.state, self.scene
        self.alive = False
        st.bump("events")
        if self.trap:
            self.game.toasts.add("It's a trap! Raiders decloaking!", config.UI_DANGER, 3)
            self.game.audio.play("alarm", 0.8)
            danger = sc.sector_danger()
            for k in range(3):
                r = Raider(self.game, self.pos + Vector2(500, 0).rotate(k * 120), danger, elite=k == 0)
                r.aggro = True
                sc.enemies.append(r)
            return
        reward = int(140 * sc.sector_danger())
        st.earn(reward)
        st.add_rep("haven", 6)
        self.game.audio.play("relic", 0.6)
        self.game.dialogue.say([("survivor", "You came! I'd given up. Take this - it's all I have.")])
        msg = f"+{reward} cr  ·  Haven Coalition +6"
        if random.random() < 0.35:
            mod = roll_mod(random.Random(), luck=0.1)
            st.mods.append(mod)
            msg += f"  ·  {mod['name']}"
        self.game.banner.show("Pilot rescued", msg)


class CargoPod(SpaceEvent):
    label = "Cargo pod"

    def __init__(self, scene, pos):
        super().__init__(scene, pos)
        self.vel = Vector2(random.uniform(-40, 40), random.uniform(-40, 40))
        self.towed = False
        self.spin = random.uniform(-40, 40)
        self.angle = 0.0
        self.img = self.game.assets.image("generated/space/cargo_pod.png", crop=True)

    def prompt(self):
        return "[E] Secure the cargo pod" if self.near() and not self.towed else None

    def update(self, dt):
        self.angle += self.spin * dt
        if self.towed:
            ship = self.scene.ship
            anchor = ship.pos - ship.forward * 110
            d = anchor - self.pos
            self.vel += d * 6 * dt
            self.vel *= max(0.0, 1 - 3 * dt)
            self.vel += (ship.vel - self.vel) * min(1.0, 2 * dt)
        self.pos += self.vel * dt

    def draw(self, surf, cam, clock):
        sx, sy = cam.to_screen(self.pos)
        if self.towed:
            pygame.draw.line(surf, (200, 200, 210), (sx, sy), cam.to_screen(self.scene.ship.pos), 2)
        z = 2 if cam.zoom > 0.45 else 1
        img = _rot(self.img, self.angle, z)
        surf.blit(img, img.get_rect(center=(sx, sy)))

    def interact(self):
        from ..scenes.choice import ChoiceScene
        self.game.scenes.push(ChoiceScene(
            self.game, "ai", "Drifting Cargo Pod",
            "Free Traders markings. The manifest says it was lost in a raider attack. The lock is flimsy.",
            [("Tow it to any station", self._tow, "The Traders pay finders well"),
             ("Crack it open here", self._crack, "Keep the goods. The Traders won't love it."),
             ("Leave it", lambda: None, "")]))

    def _tow(self):
        self.towed = True
        self.scene.towing = self
        self.game.toasts.add("Cargo pod in tow. Dock at any station to deliver.", (255, 210, 90), 4)

    def _crack(self):
        st = self.game.state
        self.alive = False
        st.add_rep("traders", -5)
        st.bump("events")
        n = random.randint(4, 9)
        st.ore += n
        st.earn(140)
        self.game.banner.show("Cargo cracked", f"+140 cr  ·  +{n} ore  ·  Free Traders -5")
        self.game.audio.play("pickup")

    def deliver(self):
        st = self.game.state
        reward = int(260 * self.scene.sector_danger())
        st.earn(reward)
        st.add_rep("traders", 7)
        st.bump("events")
        self.alive = False
        self.scene.towing = None
        self.game.banner.show("Cargo delivered", f"+{reward} cr  ·  Free Traders +7")
        self.game.audio.play("relic", 0.6)


class Comet:
    """A shootable comet with a glowing tail: ice for fuel, rock for ore."""

    def __init__(self, game, pos, vel):
        self.game = game
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.hp = 5.0
        self.alive = True
        self.radius = 34
        self.life = 26.0
        self.spin = random.uniform(-90, 90)
        self.angle = 0.0
        self.img = game.assets.image("generated/space/comet.png", crop=True)

    def update(self, dt, particles):
        self.pos += self.vel * dt
        self.angle += self.spin * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False
        if random.random() < 0.9:
            back = -self.vel.normalize()
            p = self.pos + back * 20 + Vector2(random.uniform(-10, 10), random.uniform(-10, 10))
            v = back * random.uniform(60, 160)
            particles.emit(p.x, p.y, v.x, v.y, random.uniform(0.6, 1.4), random.uniform(3, 7),
                           random.choice([(170, 220, 255), (230, 245, 255), (120, 180, 255)]), drag=0.8, glow=True)

    def draw(self, surf, cam, clock):
        sx, sy = cam.to_screen(self.pos)
        if not (-80 < sx < cam.w + 80 and -80 < sy < cam.h + 80):
            return
        z = 2 if cam.zoom > 0.45 else 1
        g = glow(int(60 * z) + 8, (140, 200, 255), 0.5)
        surf.blit(g, g.get_rect(center=(sx, sy)), special_flags=pygame.BLEND_ADD)
        img = _rot(self.img, self.angle, z)
        surf.blit(img, img.get_rect(center=(sx, sy)))


class CometShower(SpaceEvent):
    label = "Comet shower"

    def __init__(self, scene, pos):
        super().__init__(scene, pos)
        self.left = random.randint(7, 11)
        self.timer = 0.0
        self.game.banner.show("Comet shower!", "Shoot comets for ice (fuel) and ore", 3.0)
        self.game.audio.play("discover", 0.6)

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0 and self.left > 0:
            self.left -= 1
            self.timer = random.uniform(1.2, 2.6)
            ship = self.scene.ship
            side = Vector2(1, 0).rotate(random.uniform(0, 360))
            start = ship.pos + side * 2600
            aim = ship.pos + Vector2(random.uniform(-900, 900), random.uniform(-900, 900))
            vel = (aim - start).normalize() * random.uniform(260, 420)
            self.scene.comets.append(Comet(self.game, start, vel))
        if self.left <= 0 and self.timer <= -6:
            self.alive = False
            self.game.state.bump("events")


class SolarFlare(SpaceEvent):
    label = "Solar flare"
    WARN, BLAST = 8.0, 3.0

    def __init__(self, scene, pos):
        super().__init__(scene, pos)
        self.t = 0.0
        self.star = scene.system.star if scene.system else None
        self.planets = list(scene.system.planets) if scene.system else []   # cover, even if we leave the system
        self.hit = False
        self.game.audio.play("alarm", 0.8)
        self.game.hint("flare", "Solar flare incoming! Put a planet between us and the star, or hide in a nebula.")

    def shielded(self) -> bool:
        sc = self.scene
        if sc.in_nebula or self.star is None:
            return True
        t = sc.t
        a, b = self.star.pos(t), sc.ship.pos
        ab = b - a
        L2 = ab.length_squared() or 1
        for p in self.planets:
            c = p.pos(t)
            k = max(0.0, min(1.0, (c - a).dot(ab) / L2))
            if (a + ab * k).distance_to(c) < p.radius * 1.25 and k < 0.999:
                return True
        return False

    def update(self, dt):
        self.t += dt
        if self.star is None:
            self.alive = False
            return
        sc = self.scene
        if sc.system is None or sc.system.star is not self.star:      # flown, warped or towed out of reach
            self.alive = False
            self.game.toasts.add("Out of the flare's reach.", config.UI_GOOD)
            return
        if self.WARN <= self.t < self.WARN + self.BLAST:
            if not self.shielded():
                self.scene.ship.damage(24 * dt, shake=False)
                self.hit = True
                self.scene.warnings.append("SOLAR FLARE - FIND COVER")
            if self.t - dt < self.WARN:
                self.game.audio.play("warp", 0.8)
                self.game.shake(16)
        if self.t >= self.WARN + self.BLAST:
            self.alive = False
            self.game.state.bump("events")
            if not self.hit:
                self.game.toasts.add("Flare weathered without a scratch.", config.UI_GOOD)

    def overlay(self, surf):
        if self.t < self.WARN:
            n = int(self.WARN - self.t) + 1
            if int(self.t * 3) % 2 == 0:
                text(surf, f"SOLAR FLARE IN {n}", (config.SCREEN_W // 2, 210), 26, (255, 180, 60), bold=True,
                     anchor="center")
            safe = self.shielded()
            text(surf, "In cover" if safe else "Exposed: get behind a planet!", (config.SCREEN_W // 2, 240), 16,
                 config.UI_GOOD if safe else config.UI_WARN, bold=True, anchor="center")
        elif self.t < self.WARN + self.BLAST:
            k = 1 - (self.t - self.WARN) / self.BLAST
            fl = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            fl.fill((255, 190, 90, int(110 * k * (0.4 if self.shielded() else 1))))
            surf.blit(fl, (0, 0))


class PirateHail(SpaceEvent):
    label = "Pirates"

    def __init__(self, scene, pos):
        super().__init__(scene, pos)
        danger = scene.sector_danger()
        self.demand = int(120 + danger * 90)
        self.pirates = []
        base = scene.ship.pos + Vector2(1, 0).rotate(random.uniform(0, 360)) * 700
        for k in range(3):
            r = Raider(self.game, base + Vector2(120, 0).rotate(k * 120), danger, elite=k == 0)
            r.sprite = self.game.assets.image("alien/alien_ship/alienShip.png", crop=True,
                                              tint=(255, 200, 110))
            r.pirate = True
            r.aggro = False
            r.fire_timer = 99
            self.pirates.append(r)
            scene.enemies.append(r)
        self.asked = False

    def update(self, dt):
        for r in self.pirates:   # hold position until the talking is over
            if not self.asked:
                r.vel *= 0.9
                r.fire_timer = 99
        if not self.asked and not self.game.scenes.transitioning:
            self.asked = True
            from ..scenes.choice import ChoiceScene
            st = self.game.state
            self.game.audio.play("alarm", 0.6)
            opts = []
            if st.credits >= self.demand:
                opts.append((f"Pay {self.demand} credits", self._pay, "Cheapest way out. Free Traders +2"))
            opts += [("Bluff: \"Haven's fleet is right behind me\"", self._bluff,
                      f"Chance: {int(self._bluff_chance() * 100)}%"),
                     ("Fight", self._fight, "Three ships, one elite")]
            self.game.scenes.push(ChoiceScene(self.game, "pirate", "Pirates!",
                                              f"\"Nice ship. Shame if it got holes in it. {self.demand} credits "
                                              "and we never met.\"", opts))
        if self.asked and all(not r.alive for r in self.pirates):
            self.alive = False

    def _bluff_chance(self) -> float:
        st = self.game.state
        return max(0.1, min(0.9, 0.35 + st.rep.get("haven", 0) / 200 + (0.2 if st.ship == "gunship" else 0)))

    def _leave(self):
        for r in self.pirates:
            r.aggro = False
            r.vel = (r.pos - self.scene.ship.pos).normalize() * 600
            r.alive = False
            self.scene.particles.burst(r.pos.x, r.pos.y, 20, 200, [(255, 220, 140), (255, 255, 255)])
        self.game.audio.play("warp", 0.4)
        self.alive = False
        self.game.state.bump("events")

    def _pay(self):
        st = self.game.state
        st.credits -= self.demand
        st.add_rep("traders", 2)
        self.game.toasts.add(f"-{self.demand} cr. The pirates jump away laughing.", config.UI_WARN)
        self._leave()

    def _bluff(self):
        if random.random() < self._bluff_chance():
            self.game.toasts.add("\"...Not worth it. Let's go!\" The bluff worked.", config.UI_GOOD, 3)
            self.game.state.add_rep("haven", 1)
            self._leave()
        else:
            self.game.toasts.add("\"Nice try.\" They open fire!", config.UI_DANGER, 3)
            self._fight(angry=True)

    def _fight(self, angry=False):
        for r in self.pirates:
            r.aggro = True
            r.fire_timer = 0.5
            if angry:
                r.damage *= 1.2
        self.game.state.bump("events")


class Defector(SpaceEvent):
    """A battered Remnant ship that wants out (Act II onwards). Escort it to Haven and the Remnant
    learn they can change; enough of them and a Free Fleet will answer your call at the end."""
    label = "Remnant defectors"
    interact_range = 420

    def __init__(self, scene, pos):
        super().__init__(scene, pos)
        self.img = self.game.assets.image("alien/alien_ship/alienShip.png", crop=True, tint=(170, 190, 175))
        self.answered = False

    def prompt(self):
        return "[E] Answer the defectors' hail" if self.near() and not self.answered else None

    def draw(self, surf, cam, clock):
        if self.answered:
            return
        sx, sy = cam.to_screen(self.pos)
        z = 1.5 if cam.zoom > 0.45 else 1
        r = ((clock * 70) % 140) * z
        pygame.draw.circle(surf, (130, 255, 150), (sx, sy), r, 1)
        img = _rot(self.img, clock * 6 % 360, z)
        surf.blit(img, img.get_rect(center=(sx, sy)))

    def interact(self):
        from ..scenes.choice import ChoiceScene
        from . import saga
        title, body = saga.DEFECTOR_HAIL
        self.game.scenes.push(ChoiceScene(self.game, "pirate", title, body, [
            ("Escort them to Haven", self._escort, "they follow you; Remnant standing rises"),
            ("Let them go their own way", self._release, "a little goodwill"),
            ("Open fire", self._attack, "they burned Earth-Prime...")]))

    def _done(self):
        self.answered = True
        self.alive = False
        self.game.state.bump("events")

    def _escort(self):
        from ..entities.allies import CorpsShip
        sc = self.scene
        d = CorpsShip(self.game, self.pos, "tender", "follow", 2.0, "Defector", art="alien/alien_ship/alienShip.png",
                      tint=(170, 190, 175), hp=220, colour=(130, 255, 150))
        sc.corps.ships.append(d)
        sc.saga.convoy.append(d)
        self.game.toasts.add("Defectors following - lead them to Haven", (130, 255, 150), 3)
        self._done()

    def _release(self):
        self.game.state.add_rep("remnant", 5)
        self.scene.particles.burst(self.pos.x, self.pos.y, 20, 200, [(130, 255, 150), (255, 255, 255)])
        self.game.toasts.add("\"We won't forget this.\" They jump away.", (130, 255, 150), 3)
        self._done()

    def _attack(self):
        r = Raider(self.game, self.pos, max(1.0, self.scene.sector_danger()))
        r.sprite = self.img
        r.aggro = True
        self.scene.enemies.append(r)
        self.game.state.add_rep("remnant", -10)
        self._done()


EVENTS = [(Beacon, 3), (CargoPod, 3), (CometShower, 2), (SolarFlare, 2), (PirateHail, 2), (Defector, 2)]


class EventDirector:
    def __init__(self, scene):
        self.scene = scene
        self.events: list[SpaceEvent] = []
        self.timer = random.uniform(40, 70)

    def update(self, dt) -> None:
        sc = self.scene
        for e in self.events:
            e.update(dt)
        self.events = [e for e in self.events if e.alive]
        q = sc.game.quests
        if q.cid in ("awaken", "signal", "raiders", "boss") or self.events:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        self.timer = random.uniform(55, 95)
        self.spawn()

    def spawn(self, kind=None) -> SpaceEvent | None:
        sc = self.scene
        choices = [(c, w) for c, w in EVENTS if (c is not SolarFlare or (sc.system and sc.system.star))
                   and (c is not Defector or sc.game.state.boss_defeated)]
        if kind is None:
            kind = random.choices([c for c, _ in choices], weights=[w for _, w in choices])[0]
        pos = sc.ship.pos + Vector2(1, 0).rotate(random.uniform(0, 360)) * random.uniform(1800, 2600)
        if kind is SolarFlare and not (sc.system and sc.system.star):
            return None
        ev = kind(sc, pos)
        self.events.append(ev)
        if kind in (Beacon, CargoPod, Defector):
            sc.game.toasts.add(f"{kind.label} detected nearby", (255, 210, 120), 3)
            sc.game.audio.play("discover", 0.5)
        return ev

    def nearest_prompt(self):
        best = None
        for e in self.events:
            p = e.prompt()
            if p:
                best = (p, e)
        return best

    def draw(self, surf, cam, clock) -> None:
        for e in self.events:
            e.draw(surf, cam, clock)

    def overlay(self, surf) -> None:
        for e in self.events:
            if hasattr(e, "overlay"):
                e.overlay(surf)

    def drop_comet_loot(self, comet) -> None:
        sc = self.scene
        sc.pickups.append(Pickup(comet.pos, "fuel", random.randint(50, 90)))
        sc.pickups.append(Pickup(comet.pos + Vector2(20, 0), "ore", random.randint(2, 4)))
        if random.random() < 0.3:
            sc.pickups.append(Pickup(comet.pos - Vector2(20, 0), "data", 3))
