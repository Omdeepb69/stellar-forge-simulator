"""Draws and runs a planet's points of interest (see systems/poi.py)."""
from __future__ import annotations

import math
import random

import pygame

from .. import config
from ..systems import lore
from ..systems import materials as M
from ..systems import poi as P
from ..systems.items import roll_mod
from .creatures import Creature
from ..systems import groups as G
from .npcs import GroupWalker, camp_npcs

TALK_R = 170
TOWN_X = 1150                     # the homecoming town on Earth-Prime / Aster
POD_R = 180
PILLAR_R = 90
VEIN_R = 120
CRATE_R = 130


class _SeqView:
    """Ruin pillar progress, stored in ``poi_state`` so it survives leaving the planet."""

    def __init__(self, game):
        self.game = game

    def get(self, poi_id, default=None):
        s = self.game.state.poi_state.get(poi_id, {})
        return s["seq"] if "seq" in s else default

    def setdefault(self, poi_id, default):
        return P.state(self.game, poi_id).setdefault("seq", default)

    def __setitem__(self, poi_id, value):
        P.state(self.game, poi_id)["seq"] = value


class PoiLayer:
    def __init__(self, scene):
        self.scene = scene
        self.game = scene.game
        self.pois = getattr(scene.terrain, "pois", []) or []
        sp = self.game.assets.sprite
        self.img = {k: sp(f"generated/poi/{k}.png") for k in
                    ("tent", "campfire0", "campfire1", "pod", "pod_open", "tablet", "pillar", "pillar_lit", "chest",
                     "chest_open", "supply_crate")}
        self.npcs = {poi["id"]: camp_npcs(self, poi) for poi in self.pois if poi["kind"] == "camp"}
        self.tripod_img = sp("generated/poi/tripod.png")
        self.town_x = None
        self.lander_img = sp("generated/poi/corps_lander.png")
        self.walkers = self._spawn_groups()
        survey = next((w for w in self.walkers if w.group["key"] == "survey"), None)
        # the Kestrel team's ship, parked at the edge of the ground they're surveying
        self.lander_x = None
        if survey is not None:
            for x in (survey.hi + 260, survey.lo - 260):
                if not self.scene.terrain.in_pad(x, 200):
                    self.lander_x = x
                    break
        self.glyph = [sp(f"generated/poi/glyph{k}.png") for k in range(4)]
        self.glyph_big = [pygame.transform.scale(g, (g.get_width() * 2, g.get_height() * 2)) for g in self.glyph]
        b = scene.biome.id
        self.vein_img = sp(f"generated/poi/vein_{b}.png") if b in M.MATERIALS else None
        self.vein_dead = None
        if self.vein_img is not None:
            self.vein_dead = self.vein_img.copy()
            self.vein_dead.fill((70, 64, 76, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.seq = _SeqView(self.game)          # ruin id -> pillar indices lit so far
        self.cool = 0.0
        self.flash = {}                        # ruin id -> seconds of red "wrong" flash

    # ------------------------------------------------------------------ helpers
    @property
    def st(self):
        return self.game.state

    def gy(self, x):
        return self.scene.terrain.height(x)

    def _q(self, poi):
        return P.quest(self.game, self.scene.planet, poi)

    def npc_img(self, look, pose, flip):
        return self.game.assets.sprite(f"generated/poi/npc/{look}_{pose}.png", flip_x=flip)

    def _spawn_groups(self) -> list:
        """Roaming groups whose route has them on this world today, plus a family of natives."""
        planet = self.scene.planet
        if self.scene.biome.id not in M.MATERIALS:
            return []
        found = list(G.on_world(self.game, planet.id))
        band = G.band_for(planet)
        if band is not None:
            found.append(band)
        out = []
        busy = [0.0] + [p["x"] for p in self.pois if p["kind"] in ("camp", "ruin")]
        lanes = []
        home = self._homecoming()
        if home is not None:                          # the homecoming town, just past the rocket
            self.town_x = TOWN_X
            lanes.append(TOWN_X)
            busy.append(TOWN_X)
            out.append(GroupWalker(self, home, TOWN_X, 420, planet.seed + 77))
        for k, grp in enumerate(found):
            rng = random.Random(planet.seed * 17 + G.day(self.game) * 5 + k * 101)
            x = None
            for _ in range(40):                       # each group gets its own stretch of the world
                c = rng.choice([-1, 1]) * rng.uniform(1600, 8000)
                if all(abs(c - b) > 1100 for b in busy) and all(abs(c - l) > 3200 for l in lanes):
                    x = c
                    break
            if x is None:
                continue
            lanes.append(x)
            out.append(GroupWalker(self, grp, x, 1300, rng.randrange(1 << 30)))
            if not grp.get("local"):
                self.game.toasts.add(f"{grp['name']} is on this world", grp["color"], 4, icon=grp["icon"])
        return out

    def _homecoming(self):
        """Earth-Prime reborn (or Aster, if the Forge was destroyed and the ark came home): a town of the
        people you helped. None anywhere else."""
        from ..systems import saga
        st = self.st
        planet = self.scene.planet
        ark = saga.data(st).get("ark") == "rescued"
        if not (planet.name == "Earth-Prime" or (planet.id == "0,0:0" and st.ending == "destroy" and ark)):
            return None
        looks = []
        for ps in st.poi_state.values():                # the species of every camp you helped
            q = ps.get("quest") or {}
            if ps.get("history") and isinstance(q.get("species"), int) and q["species"] not in looks:
                looks.append(q["species"])
        rng = random.Random(planet.seed + 5)
        pool = [k for k in P.SP.TRAVELLERS if k not in looks]
        rng.shuffle(pool)
        looks = looks[:4] + pool[:max(0, (3 if ark else 2) - len(looks[:4]))]
        if ark:
            looks += pool[3:5]
        members = [(k, P.SP.name_for(k, planet.seed + i)) for i, k in enumerate(looks)]
        if not saga.data(st).get("homecoming"):
            saga.data(st)["homecoming"] = True
            g = self.game
            lines = [("vey", "Voyager... look. Real rain, real soil. The first sunrise over this town."
                      if planet.name == "Earth-Prime" else
                      "Voyager. It isn't Earth-Prime - but Aster is ours now, and it's beautiful."),
                     ("vey", "Everyone you helped out there came to see it. They say the town should have your name.")]
            if ark:
                lines.append(("survivor", "Tomas here. Two thousand people woke up today. We named the main "
                                          "street after you, Voyager. Asha insisted."))
            g.dialogue.say(lines)
            g.banner.show("Homecoming", "A town of everyone you helped", 4.0)
        return dict(key=f"home:{planet.id}", name="Homecoming", icon=None, color=(255, 220, 150), members=members,
                    speed=36, stops=True, local=True)

    def group_hit(self):
        px = self.scene.pilot.x
        best = None
        for w in self.walkers:
            hit = w.nearest(px)
            if hit and (best is None or hit[1] < best[2]):
                best = (w, hit[0], hit[1])
        return best

    def speaker(self, poi, name, npc=None):
        npc = npc or self.giver(poi)
        return f"settler:{npc.look}:{name}"

    def giver(self, poi):
        return self.npcs[poi["id"]][0]

    def _camp_parts(self, poi):
        x = poi["x"]
        return {"tent": x - 150, "fire": x - 10, "settler": x + 90}

    # ------------------------------------------------------------------ update
    def update(self, dt) -> None:
        p = self.scene.pilot
        self.cool = max(0.0, self.cool - dt)
        for w in self.walkers:
            if abs(w.leader.x - p.x) < 4000:
                w.update(dt, p.x)
        for k in list(self.flash):
            self.flash[k] -= dt
            if self.flash[k] <= 0:
                del self.flash[k]
        for poi in self.pois:
            if abs(p.x - poi["x"]) < 1000:
                s = P.state(self.game, poi["id"])
                if not s.get("seen"):
                    s["seen"] = True
                    name, icon, col = P.KINDS[poi["kind"]]
                    if poi["kind"] == "vein":
                        name = f"{M.name(self.scene.biome.id)} vein"
                    self.game.toasts.add(f"Discovered: {name}", col, 3, icon=icon or f"mat_{self.scene.biome.id}")
                    self.game.audio.play("discover", 0.4)
            if poi["kind"] == "vein":
                self._vein_sword(poi)
            elif poi["kind"] == "camp" and abs(p.x - poi["x"]) < 2600:
                for npc in self.npcs[poi["id"]]:
                    npc.update(dt, p.x)

    def _vein_sword(self, poi) -> None:
        p = self.scene.pilot
        sword = p.sword_rect()
        if not sword or P.done(self.game, poi["id"]) or poi["id"] in p.swing_hit:
            return
        x = poi["x"]
        r = pygame.Rect(x - 50, self.gy(x) - 70, 100, 70)
        if sword.colliderect(r):
            p.swing_hit.add(poi["id"])
            self._mine_vein(poi)

    def _mine_vein(self, poi) -> None:
        s = P.state(self.game, poi["id"])
        s["hits"] = s.get("hits", 0) + 1
        b = self.scene.biome.id
        n = 2 if s["hits"] < P.VEIN_HITS else 3
        M.give(self.game, b, n, toast=False)
        x = poi["x"]
        self.scene.floaters.add(x, self.gy(x) - 90, f"+{n} {M.name(b)}", M.color(b))
        self.scene.particles.burst(x, self.gy(x) - 30, 18, 240, [M.color(b), (255, 255, 255)], life=(0.3, 0.8),
                                   gravity=600)
        self.game.audio.play("pickup", 0.7)
        self.game.shake(3)
        if s["hits"] >= P.VEIN_HITS:
            s["done"] = True
            self.game.toasts.add(f"Vein mined out  ·  {M.name(b)} ×{self.st.materials.get(b, 0)}", M.color(b), 2.5,
                                 icon=f"mat_{b}")

    # ------------------------------------------------------------------ prompts & interaction
    def nearest(self):
        """(poi, part, distance) for the closest interactable thing, or None."""
        p = self.scene.pilot
        best = None
        for poi in self.pois:
            for part, x, r in self._parts(poi):
                d = abs(p.x - x)
                if d < r and (best is None or d < best[2]):
                    best = (poi, part, d)
        return best

    def _parts(self, poi):
        kind = poi["kind"]
        if kind == "camp":
            crowd = self.npcs[poi["id"]]
            yield "settler", crowd[0].x, TALK_R
            for i, npc in enumerate(crowd[1:], 1):
                yield ("npc", i), npc.x, 110
            q = self.st.poi_state.get(poi["id"], {}).get("quest")
            if q and q["kind"] == "fetch" and q["stage"] == "active" and not q["have"] and poi.get("crate_x") is not None:
                yield "crate", poi["crate_x"], CRATE_R
        elif kind == "pod":
            yield "pod", poi["x"], POD_R
        elif kind == "ruin":
            for i, dx in enumerate(P.PILLAR_DX):
                yield ("pillar", i), poi["x"] + dx, PILLAR_R
            yield "tablet", poi["x"], 110
        elif kind == "vein":
            yield "vein", poi["x"], VEIN_R

    def near_lander(self) -> bool:
        return self.lander_x is not None and abs(self.scene.pilot.x - self.lander_x) < 170

    def prompt(self):
        if self.near_lander() and self.group_hit() is None:
            return ("[E] Kestrel lander: Corps contracts board", (255, 190, 90))
        gh = self.group_hit()
        if gh is not None:
            w, m, _d = gh
            if w.group.get("local"):
                return (f"[E] Chat with the {P.SP.SPECIES[m.look]['label']}", (170, 210, 200))
            return (f"[E] Talk to the {w.group['name']}", w.group["color"])
        hit = self.nearest()
        if hit is None:
            return None
        poi, part, _d = hit
        done = P.done(self.game, poi["id"])
        if part == "settler":
            q = self._q(poi)
            return ("[E] Talk to " + P.SP.short(q["name"]), (120, 230, 200))
        if isinstance(part, tuple) and part[0] == "npc":
            npc = self.npcs[poi["id"]][part[1]]
            return (f"[E] Chat with the {P.SP.SPECIES[npc.look]['label']}", (170, 210, 200))
        if part == "crate":
            return ("[E] Pick up the supply crate", (255, 220, 150))
        if part == "pod":
            return (("[E] Salvage the escape pod", (200, 220, 255)) if not done else
                    ("Escape pod (salvaged)", (170, 170, 170)))
        if part == "tablet":
            return (("Architect tablet: light the pillars in this order", (120, 220, 255)) if not done else
                    ("The ruin is quiet now", (170, 170, 170)))
        if isinstance(part, tuple):
            return None if done else ("[E] Touch the pillar", (120, 220, 255))
        if part == "vein":
            return None if done else ("[E] or sword: mine the vein", M.color(self.scene.biome.id))
        return None

    def interact(self) -> bool:
        if self.near_lander() and self.group_hit() is None:
            from ..scenes.choice import ChoiceScene
            from ..systems import corps_career
            title, body, opts = corps_career.menu(self.game)
            self.game.scenes.push(ChoiceScene(self.game, "settler:7:Professor Lattice", title, body, opts,
                                              can_cancel=True))
            return True
        gh = self.group_hit()
        if gh is not None:
            w, m, _d = gh
            m.talk_t = 4.0
            G.talk(self.game, self.scene, w.group, m.look, m.name)
            return True
        hit = self.nearest()
        if hit is None:
            return False
        poi, part, _d = hit
        if part == "settler":
            self.giver(poi).talk_t = 4.0
            P.talk(self.game, self.scene.planet, poi, self.scene)
        elif isinstance(part, tuple) and part[0] == "npc":
            npc = self.npcs[poi["id"]][part[1]]
            look_id = npc.look if isinstance(npc.look, int) else 0
            name = P.SP.name_for(look_id, int(poi["seed"]) + look_id)
            self.game.dialogue.say([(self.speaker(poi, name, npc), npc.say())])
        elif part == "crate":
            q = self._q(poi)
            q["have"] = 1
            self.game.audio.play("pickup")
            self.game.toasts.add("Supply crate recovered - return it to the camp", (255, 220, 150), 3, icon="camp")
        elif part == "pod":
            if P.done(self.game, poi["id"]):
                return True
            self._salvage(poi)
        elif isinstance(part, tuple):
            self._pillar(poi, part[1])
        elif part == "vein":
            if not P.done(self.game, poi["id"]) and self.cool <= 0:
                self.cool = 0.35
                self._mine_vein(poi)
        else:
            return part == "tablet"
        return True

    def _salvage(self, poi) -> None:
        g, st = self.game, self.st
        P.state(g, poi["id"])["done"] = True
        st.bump("pods")
        rng = random.Random(poi["seed"])
        cr = int(60 * self.scene.danger + 40)
        st.earn(cr)
        b = self.scene.biome.id
        M.give(g, b, 2)
        M.give(g, rng.choice([k for k in M.MATERIALS if k != b]), 1)
        msgs = [f"+{cr} cr"]
        if rng.random() < 0.4:
            mod = roll_mod(rng, luck=0.05)
            st.mods.append(mod)
            msgs.append(mod["name"])
        x = poi["x"]
        self.scene.particles.burst(x, self.gy(x) - 40, 26, 220, [(200, 220, 255), (255, 255, 255)],
                                   life=(0.3, 0.9), gravity=400)
        g.audio.play("relic", 0.5)
        g.banner.show("Escape pod salvaged", "  ·  ".join(msgs), 3.0)
        if rng.random() < 0.5:
            lore.announce(g, lore.next_log(st, "crew"))

    def _pillar(self, poi, i) -> None:
        g = self.game
        if P.done(g, poi["id"]):
            return
        seq = self.seq.setdefault(poi["id"], [])
        if i in seq:
            return
        want = poi["order"][len(seq)]
        x = poi["x"] + P.PILLAR_DX[i]
        if i != want:
            self.seq[poi["id"]] = []
            self.flash[poi["id"]] = 0.8
            g.audio.play("deny")
            g.shake(6)
            g.toasts.add("Wrong glyph! The ruin's guardians wake...", config.UI_DANGER, 2.5)
            sc = self.scene
            for k in range(2):
                uid = f"guard:{poi['id']}:{random.randrange(1 << 20)}"
                sc.creatures[uid] = Creature(g, uid, x + (k * 2 - 1) * 260, "flyer", sc.terrain.height,
                                             sc.biome.creature_tint, sc.danger + 0.5,
                                             sprites=sc.biome.creature_sprites)
            return
        seq.append(i)
        g.audio.play("relic", 0.35 + 0.15 * len(seq))
        self.scene.particles.burst(x, self.gy(x) - 130, 14, 160, [(120, 230, 255), (255, 255, 255)],
                                   life=(0.3, 0.7))
        if len(seq) == len(poi["order"]):
            self._solve(poi)

    def _solve(self, poi) -> None:
        g, st = self.game, self.st
        P.state(g, poi["id"])["done"] = True
        st.bump("ruins")
        rng = random.Random(poi["seed"] + 7)
        b = self.scene.biome.id
        M.give(g, b, 4)
        M.give(g, rng.choice([k for k in M.MATERIALS if k != b]), 2)
        mod = roll_mod(rng, min_rarity=1, luck=0.1)
        st.mods.append(mod)
        cr = int(120 * self.scene.danger + 60)
        st.earn(cr)
        g.shake(8)
        g.audio.play("relic", 1.0)
        x = poi["x"]
        self.scene.particles.burst(x, self.gy(x) - 60, 40, 300, [(120, 230, 255), (255, 255, 255), (255, 220, 120)],
                                   life=(0.4, 1.1), gravity=300)
        g.banner.show("The ruin opens", f"{mod['name']}  ·  +{cr} cr", 3.5)
        lore.announce(g, lore.next_log(st, "architect"))
        g.save()

    # ------------------------------------------------------------------ drawing
    def draw(self, surf, ox, oy) -> None:
        """Behind the ground line, like structures."""
        W = config.SCREEN_W
        t = self.scene.scene_clock if hasattr(self.scene, "scene_clock") else self.scene.clock
        for poi in self.pois:
            x = poi["x"]
            if not (-700 < x - ox < W + 700):
                if poi["kind"] == "camp" and poi.get("crate_x") is not None:
                    self._draw_crate(surf, poi, ox, oy, t)
                continue
            kind = poi["kind"]
            done = P.done(self.game, poi["id"])
            if kind == "camp":
                parts = self._camp_parts(poi)
                self._blit(surf, self.img["tent"], parts["tent"], ox, oy)
                self._blit(surf, self.img["campfire0" if int(t * 5) % 2 else "campfire1"], parts["fire"], ox, oy)
                self._draw_settler(surf, poi, ox, oy, t)
                self._draw_crate(surf, poi, ox, oy, t)
            elif kind == "pod":
                self._blit(surf, self.img["pod_open" if done else "pod"], x, ox, oy, sink=14)
                if not done and int(t * 2) % 2:
                    sx, sy = int(x - ox) // 2 * 2, int(self.gy(x) - oy - 76) // 2 * 2
                    surf.fill((255, 90, 80), (sx + 40, sy, 4, 4))
            elif kind == "ruin":
                self._draw_ruin(surf, poi, ox, oy, t, done)
            elif kind == "vein" and self.vein_img is not None:
                self._blit(surf, self.vein_dead if done else self.vein_img, x, ox, oy)
        if self.town_x is not None and -900 < self.town_x - ox < W + 900:     # the town's tents
            for k, dx in enumerate((-360, -120, 200, 420)):
                self._blit(surf, self.img["tent"], self.town_x + dx, ox, oy)
            self._blit(surf, self.img["campfire0" if int(t * 5) % 2 else "campfire1"], self.town_x + 60, ox, oy)
        if self.lander_x is not None and -400 < self.lander_x - ox < W + 400:
            self._blit(surf, self.lander_img, self.lander_x, ox, oy, sink=6)
        for w in self.walkers:
            w.draw(surf, ox, oy, self.npc_img, self.tripod_img, self.scene.pilot.x)

    def _blit(self, surf, img, x, ox, oy, sink=8):
        surf.blit(img, img.get_rect(midbottom=(x - ox, self.gy(x) - oy + sink)))

    def _draw_settler(self, surf, poi, ox, oy, t):
        q = self.st.poi_state.get(poi["id"], {}).get("quest")
        crowd = self.npcs[poi["id"]]
        for npc in sorted(crowd[1:], key=lambda n: n.role != "sitter"):
            npc.draw(surf, ox, oy, self.npc_img)
        r = crowd[0].draw(surf, ox, oy, self.npc_img)
        mark = None
        if q is None or q["stage"] == "new":
            mark = "!"
        elif q["stage"] == "active":
            ready = q["have"] >= q["need"] if q["kind"] != "gather" else \
                self.st.materials.get(q["mat"], 0) >= q["need"]
            mark = "?" if ready else None
        if mark:
            from ..ui.text import text
            bob = int(math.sin(t * 4) * 3) // 2 * 2
            text(surf, mark, (r.centerx, r.top - 8 + bob), 34, (255, 214, 90), anchor="midbottom", outline=True)

    def _draw_crate(self, surf, poi, ox, oy, t):
        cx = poi.get("crate_x")
        if cx is None:
            return
        q = self.st.poi_state.get(poi["id"], {}).get("quest")
        if not q or q["kind"] != "fetch" or q["stage"] != "active" or q["have"]:
            return
        if not (-200 < cx - ox < config.SCREEN_W + 200):
            return
        self._blit(surf, self.img["supply_crate"], cx, ox, oy)
        if int(t * 3) % 2:
            sx, sy = int(cx - ox) // 2 * 2, int(self.gy(cx) - oy - 64) // 2 * 2
            surf.fill((120, 255, 200), (sx - 2, sy, 4, 4))

    def _draw_ruin(self, surf, poi, ox, oy, t, done):
        x = poi["x"]
        seq = self.seq.get(poi["id"], [])
        flash = poi["id"] in self.flash and int(t * 12) % 2
        self._blit(surf, self.img["chest_open" if done else "tablet"], x, ox, oy)
        for i, dx in enumerate(P.PILLAR_DX):
            px = x + dx
            lit = done or i in seq
            img = self.img["pillar_lit" if lit else "pillar"]
            r = img.get_rect(midbottom=(px - ox, self.gy(px) - oy + 8))
            surf.blit(img, r)
            g = self.glyph[poi["glyphs"][i]]
            gr = g.get_rect(center=(r.centerx, r.y + 30 * config.ART_SCALE))
            if flash:
                tinted = g.copy()
                tinted.fill((255, 80, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(tinted, gr)
            else:
                surf.blit(g, gr)

    def draw_overlay(self, surf, ox, oy) -> None:
        """The tablet's glyph order, floating above it while you're close."""
        p = self.scene.pilot
        for poi in self.pois:
            if poi["kind"] != "ruin" or P.done(self.game, poi["id"]) or abs(p.x - poi["x"]) > 560:
                continue
            from ..ui.text import theme
            th = theme()
            x = poi["x"]
            seq = self.seq.get(poi["id"], [])
            w = 3 * 56 + 28
            r = pygame.Rect(0, 0, w, 64)
            r.midbottom = (int(x - ox), int(self.gy(x) - oy - 130))
            th.plate(surf, r)
            for k, pillar_i in enumerate(poi["order"]):
                g = self.glyph_big[poi["glyphs"][pillar_i]]
                gr = g.get_rect(center=(r.x + 42 + k * 56, r.centery))
                if k < len(seq):
                    surf.fill((40, 120, 140), gr.inflate(8, 8))
                surf.blit(g, gr)

    def lights(self, L, ox, oy) -> None:
        for poi in self.pois:
            x = poi["x"]
            if not (-500 < x - ox < config.SCREEN_W + 500):
                continue
            kind = poi["kind"]
            done = P.done(self.game, poi["id"])
            gy = self.gy(x) - oy
            if kind == "camp":
                L.add(x - 10 - ox, gy - 30, 300, (255, 170, 80), 1.0)
            elif kind == "ruin":
                seq = self.seq.get(poi["id"], [])
                for i, dx in enumerate(P.PILLAR_DX):
                    if done or i in seq:
                        L.add(x + dx - ox, self.gy(x + dx) - oy - 120, 170, (120, 220, 255), 0.8)
                L.add(x - ox, gy - 60, 140, (120, 220, 255), 0.6)
            elif kind == "pod" and not done:
                L.add(x - ox, gy - 40, 150, (150, 220, 255), 0.7)
            elif kind == "vein" and not done:
                L.add(x - ox, gy - 30, 170, M.color(self.scene.biome.id), 0.8)

    # ------------------------------------------------------------------ strip map
    def marks(self) -> list:
        out = [(w.leader.x, w.group["icon"], False) for w in self.walkers if w.group.get("icon")]
        if self.lander_x is not None:
            out.append((self.lander_x, "ship", False))
        b = self.scene.biome.id
        for poi in self.pois:
            s = self.st.poi_state.get(poi["id"], {})
            done = bool(s.get("done"))
            icon = (P.KINDS[poi["kind"]][1] or f"mat_{b}") if s.get("seen") else "unknown"
            out.append((poi["x"], icon, done))
            q = s.get("quest")
            if q and q["kind"] == "fetch" and q["stage"] == "active" and not q["have"]:
                out.append((poi["crate_x"], "folder", False))
        return out
