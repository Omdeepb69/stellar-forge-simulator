"""People of the frontier on a planet surface.

* Camp folk (Npc): wander the camp, sit by the fire, turn to look at you, wave
  when you arrive and gesture while they talk.
* Groups (GroupWalker): a named band - the Survey Corps, a trade caravan, a
  pilgrim procession, a scavenger gang, a family of natives - walking the world
  together in a line, stopping now and then (the surveyors set up a tripod).
"""
from __future__ import annotations

import random

import pygame

from .. import config
from ..systems.species import SPECIES, TRAVELLERS, giver_look, natives_of

WALK_SPEED = 70.0
NOTICE_R = 520          # they stop and look at you inside this range
WAVE_R = 700            # ...and wave once when you first come this close
GROUP_TALK_R = 150


class Npc:
    def __init__(self, layer, poi, role: str, look, home: float, roam: float, rng: random.Random,
                 name: str = "", speed: float = WALK_SPEED):
        self.layer = layer
        self.poi = poi
        self.role = role                 # giver | camper | sitter | group
        self.look = look                 # species index, or "beast"
        self.name = name
        self.home, self.roam = home, roam
        self.speed = speed
        self.x = home
        self.target = None
        self.facing = rng.choice([-1, 1])
        self.rng = rng
        self.timer = rng.uniform(0.5, 3.0)
        self.anim = rng.uniform(0, 10)
        self.blink = rng.uniform(1.5, 4.0)
        self.wave_t = 0.0
        self.talk_t = 0.0
        self.waved = False
        self.line = 0
        self.held = False                # a group walker is holding everyone still

    # ---------------------------------------------------------------- behaviour
    def update(self, dt, pilot_x: float) -> None:
        self.anim += dt
        self.blink -= dt
        if self.blink < -0.12:
            self.blink = self.rng.uniform(2.0, 5.0)
        self.wave_t = max(0.0, self.wave_t - dt)
        self.talk_t = max(0.0, self.talk_t - dt)
        d = pilot_x - self.x
        near = abs(d) < NOTICE_R
        if self.look != "beast":
            if abs(d) > WAVE_R * 1.6:
                self.waved = False               # wave again next time you come back
            elif abs(d) < WAVE_R and not self.waved:
                self.waved = True
                self.wave_t = 1.4
        if self.talk_t > 0 or self.wave_t > 0 or (near and self.look != "beast") or self.held:
            self.target = None
            if self.look != "beast" or near:
                self.facing = 1 if d > 0 else -1
            return
        if self.role == "sitter":
            self.facing = 1 if self.layer._camp_parts(self.poi)["fire"] > self.x else -1
            return
        if self.target is None:
            if self.role == "group":
                return                           # the group walker hands out targets
            self.timer -= dt
            if self.timer <= 0:
                fire = self.layer._camp_parts(self.poi)["fire"]
                for _ in range(6):
                    t = self.home + self.rng.uniform(-self.roam, self.roam)
                    if abs(t - fire) > 50 and abs(t - self.x) > 40:
                        self.target = t
                        break
                self.timer = self.rng.uniform(2.0, 5.5)
            return
        step = self.speed * dt
        diff = self.target - self.x
        self.facing = 1 if diff > 0 else -1
        if abs(diff) <= step:
            self.x = self.target
            self.target = None
        else:
            self.x += step * self.facing

    def say(self) -> str:
        if not isinstance(self.look, int) or not (0 <= self.look < len(SPECIES)):
            return "..."
        pool = SPECIES[self.look]["chatter"]
        seed = int(self.poi["seed"]) if self.poi else 0
        line = pool[(seed + self.look * 3 + self.line) % len(pool)]
        self.line += 1
        self.talk_t = 3.5
        return line

    # ---------------------------------------------------------------- drawing
    def pose(self) -> str:
        if self.look == "beast":
            return f"walk{int(self.anim * 5) % 4}" if self.target is not None else f"idle{int(self.anim * 0.7) % 2}"
        if self.talk_t > 0:
            return f"talk{int(self.anim * 5) % 2}"
        if self.wave_t > 0:
            return f"wave{int(self.anim * 6) % 2}"
        if self.role == "sitter":
            return f"sit{int(self.anim * 0.8) % 2}"
        if self.target is not None:
            return f"walk{int(self.anim * 7) % 4}"
        if self.blink < 0:
            return "blink"
        return f"idle{int(self.anim * 0.9) % 2}"

    def draw(self, surf, ox, oy, imgs) -> pygame.Rect:
        img = imgs(self.look, self.pose(), self.facing < 0)
        gy = self.layer.gy(self.x)
        r = img.get_rect(midbottom=(int(self.x - ox) // config.ART_SCALE * config.ART_SCALE, gy - oy + 6))
        surf.blit(img, r)
        self.rect = r
        return r


def camp_npcs(layer, poi) -> list[Npc]:
    """The job-giver plus one or two others: natives of this world and a traveller passing through."""
    rng = random.Random(poi["seed"] + 5)
    parts = layer._camp_parts(poi)
    first = giver_look(poi)
    natives = [k for k in natives_of(poi.get("biome", "")) if k != first]
    travellers = [k for k in TRAVELLERS if k != first]
    rng.shuffle(travellers)
    others = natives[:1] + travellers[:1]
    rng.shuffle(others)
    out = [Npc(layer, poi, "giver", first, parts["settler"], 60, rng)]
    if others and rng.random() < 0.8:
        out.append(Npc(layer, poi, "sitter", others.pop(), parts["fire"] - 74, 0, rng))
    if others and rng.random() < 0.75:
        out.append(Npc(layer, poi, "camper", others.pop(), poi["x"] - 40, 230, rng))
    return out


class GroupWalker:
    """Moves a group as one: the leader picks a destination, the rest follow in a line."""

    def __init__(self, layer, group: dict, x: float, span: float, seed: int):
        self.layer = layer
        self.group = group
        self.rng = random.Random(seed)
        self.lo, self.hi = x - span, x + span
        self.members = []
        self.gaps = []                  # distance behind the leader for each member
        back = 0.0
        for k, (look, name) in enumerate(group["members"]):
            if k:
                back += 190 if look == "beast" or group["members"][k - 1][0] == "beast" else 112
            m = Npc(layer, None, "group", look, x - back, 0, self.rng, name=name, speed=group["speed"] * 1.25)
            self.members.append(m)
            self.gaps.append(back)
        self.leader = self.members[0]
        self.leader.speed = group["speed"]
        self.pause = self.rng.uniform(1.0, 4.0)
        self.tripod = None              # where the survey team set up its instrument

    def update(self, dt, pilot_x: float) -> None:
        lead = self.leader
        near = any(abs(pilot_x - m.x) < NOTICE_R for m in self.members)
        if lead.target is None and not near:
            self.pause -= dt
            if self.pause <= 0:
                for _ in range(8):
                    t = self.rng.uniform(self.lo, self.hi)
                    if abs(t - lead.x) > 500 and not self.layer.scene.terrain.in_pad(t, 0):
                        lead.target = t
                        self.tripod = None
                        break
                self.pause = self.rng.uniform(6.0, 12.0) if self.group.get("stops") else self.rng.uniform(0.5, 1.5)
            elif self.group["key"] == "survey" and self.tripod is None and self.pause < 9:
                self.tripod = lead.x + 60 * lead.facing
        moving = lead.target is not None
        for i, m in enumerate(self.members[1:], 1):
            m.held = near and abs(pilot_x - m.x) < NOTICE_R * 1.4
            if not m.held:
                want = lead.x - lead.facing * self.gaps[i] if moving else m.x
                if abs(want - m.x) > 12:
                    m.target = want
        for m in self.members:
            m.update(dt, pilot_x)

    def nearest(self, px: float):
        best = None
        for m in self.members:
            if m.look == "beast":
                continue
            d = abs(px - m.x)
            if d < GROUP_TALK_R and (best is None or d < best[1]):
                best = (m, d)
        return best

    def draw(self, surf, ox, oy, imgs, tripod_img, pilot_x: float) -> None:
        if not (-800 < self.leader.x - ox < config.SCREEN_W + 800):
            return
        if self.tripod is not None and tripod_img is not None:
            gy = self.layer.gy(self.tripod)
            surf.blit(tripod_img, tripod_img.get_rect(midbottom=(self.tripod - ox, gy - oy + 6)))
        for m in sorted(self.members, key=lambda m: m.look != "beast"):     # the beast walks behind
            m.draw(surf, ox, oy, imgs)
        if abs(pilot_x - self.leader.x) < 900 and not self.group.get("local"):
            from ..ui.text import text
            r = self.leader.rect
            pole = (r.centerx - 30, r.top - 14)
            surf.fill((90, 70, 50), (pole[0], pole[1], 2, 30))                     # the group's pennant
            col = self.group["color"]
            for k in range(6):
                surf.fill(col, (pole[0] + 2, pole[1] + k * 2, 14 - k * 2, 2))
            text(surf, self.group["name"], (r.centerx, pole[1] - 4), 14, col, anchor="midbottom", outline=True)
