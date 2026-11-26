"""Story campaign ("The Last Voyager") and endless station contracts.

The quest manager only listens to events on the bus, so scenes never
need to know which chapter is active.
"""
from __future__ import annotations

import math

from pygame.math import Vector2

from .. import config
from ..core.game_state import RELIC_BIOMES, RELIC_NAMES, SHARD_BIOMES, SHARD_NAMES
from ..world.rng import rng_of

HOME_STATION = "0,0:st"
FORGE = "0,0:forge"

CHAPTERS = [
    {"id": "awaken", "title": "Awakening",
     "objective": "Walk to your rocket and press [E] to board it"},
    {"id": "signal", "title": "Distress Signal",
     "objective": "Fly to Haven Station and dock with [E]"},
    {"id": "raiders", "title": "Defensive Maneuvers",
     "objective": "Destroy the raiders around Haven", "count": 5},
    {"id": "keys", "title": "The Three Keys",
     "objective": "Recover the Ancient Keys from strongholds", "count": 3},
    {"id": "return", "title": "Return to Haven",
     "objective": "Bring the Keys to Haven Station"},
    {"id": "boss", "title": "The Warlord",
     "objective": "Defeat the Warlord"},
    # ---- Act II: The Shattered Forge ----
    {"id": "shards", "title": "The Shattered Forge",
     "objective": "Destroy the Remnant Wardens and recover the Forge Shards", "count": 5},
    {"id": "forge", "title": "Worldsmith",
     "objective": "Bring the five Shards to the Stellar Forge near Haven, press [E] and decide its fate"},
    {"id": "free", "title": "Legend of the Voyager",
     "objective": "Follow the bell signal to the rim of the galaxy (teal compass) - or roam free"},
    # ---- Act III: The Makers ----
    {"id": "road", "title": "The Maker Road",
     "objective": "Find the three Maker waystones and pass their trials", "count": 3},
    {"id": "judgment", "title": "The Last Smith",
     "objective": "Return to the Bell, ring it, and face the Makers' judgment"},
    {"id": "legend", "title": "Voyager Eternal",
     "objective": "The galaxy remembers you. Chart it, guard it, live in it."},
]
FREE = 8          # index of "free" (after the Forge); Act III follows it
ACT2_START = 6

INTRO = [
    ("ai", "Cryo-sleep terminated. Pilot vitals... stable. Welcome back, Voyager."),
    ("pilot", "Aster... I came down hard. How long was I out?"),
    ("ai", "Unknown. Picking up a faint distress signal from orbit: Haven Station."),
    ("ai", "Arrow keys or A/D to walk, W or Up to jump, hold it to use the jetpack. [E] boards the rocket."),
]

SIGNAL_DONE = [
    ("vey", "Voyager?! You're alive. We thought the whole Fleet burned with Earth-Prime."),
    ("vey", "Haven was Earth-Prime's harbour once. Now it's a Coalition of anyone who fled the Warlord - "
            "humans, Lumen, Tik, Mossbacks, all of us."),
    ("vey", "That broken ring off our bow is the Stellar Forge. Dravos woke it with a single Key and turned it on "
            "our world. Haven was built to watch it sleep."),
    ("vey", "His raiders hit us an hour ago. They're hunting the three Ancient Keys that command it."),
    ("vey", "First things first: clear out the raiders circling the station. Station services are yours, free of charge."),
]

RAIDERS_DONE = [
    ("vey", "That's the last of them. One of the wrecks carried star charts."),
    ("vey", "When Earth-Prime fell, the Sun Key tore itself from Dravos's hand and went home. The Keys always "
            "return to their locks."),
    ("vey", "So all three lie in their ancient strongholds again - on Desert, Frozen and Verdant worlds."),
    ("vey", "Out on the frontier, the Survey Corps charts those worlds. If you meet their Kestrel team, they'll "
            "share what they know. So will the settlers - help them and they'll help you."),
    ("ai", "Scanner recalibrated. Ancient signals will show on the relic compass (gold arrow)."),
    ("vey", "Land, find the stronghold on the surface, and solve the door sequence. Good hunting."),
]

KEY_LINES = {
    "desert": [("pilot", "The Sun Key. It's warm, like holding a star."),
               ("ai", "Key fragment decoded: 'The Forge was built to make worlds, not end them.'")],
    "ice": [("pilot", "The Frost Key. Something is etched inside the ice... a map?"),
            ("ai", "Key fragment decoded: 'Its maker sealed it with three locks and fled.'")],
    "forest": [("pilot", "The Verdant Key. Roots are still growing around it."),
               ("ai", "Key fragment decoded: 'Whoever holds all three commands the Forge.'")],
}

RETURN_DONE = [
    ("vey", "All three Keys... they're resonating. I've never seen anything like it."),
    ("vey", "Wait - something is coming through the Forge gate. Brace!"),
    ("warlord", "LITTLE VOYAGER. YOU HAVE BROUGHT ME MY KEYS."),
    ("warlord", "I BURNED YOUR WORLD WITH ONE KEY. IMAGINE WHAT I WILL DO WITH THREE."),
]

EPILOGUE = [
    ("pilot", "It's over. The Warlord is gone."),
    ("vey", "One more thing, Voyager. A rumour from the deep: an ark called New Dawn, two thousand of our people "
            "in cryo, hiding beyond a nebula. My brother was on the crew list. Find them, if you can."),
    ("ai", "Not entirely. When he fell, the Forge's core shattered. Five Shards were flung across the galaxy."),
    ("vey", "His Remnant fleet is already hunting them. Each Shard vault is guarded by a Warden - a dreadnought."),
    ("vey", "The Forge was built to make worlds. With the Keys AND the Shards... it could make yours again."),
    ("ai", "Shard signals plotted (violet compass). Crystalline, Volcanic, Toxic, Oceanic and Barren worlds, far out."),
    ("ai", "Tip: upgrade your hull, shield and blaster at stations before taking on a Warden. [B] opens the Logbook."),
]

SHARD_LINES = {
    "crystal": [("ai", "Prism Shard secured. It hums in a key no instrument has ever played.")],
    "volcanic": [("ai", "Ember Shard secured. Still hot after a thousand years of sleep.")],
    "toxic": [("ai", "Blight Shard secured. The rot around the vault is already receding.")],
    "ocean": [("ai", "Tide Shard secured. Listen... it sounds like waves on a beach that no longer exists.")],
    "barren": [("ai", "Void Shard secured. It's cold. Not like ice - like the space between stars.")],
}

ALL_SHARDS = [
    ("vey", "All five Shards. Bring them home, Voyager - the Forge is waiting at Haven."),
    ("ai", "The Forge gate is marked on your compass. Fly close and press [E]."),
]

LEGEND = [
    ("vey", "A new Earth-Prime... I never thought I'd live to see a sunrise there."),
    ("vey", "It's orbiting Haven now. Land on it, Voyager. You've earned that much."),
    ("ai", "Something else: the moment the Forge made a world, a signal answered from the galactic rim."),
    ("ai", "A single tone, like a bell. I've marked it (teal). It's very, very far."),
    ("ai", "New Game+ is unlocked on the title screen: a new galaxy, harder foes, and you keep your gear."),
]

LEGEND_DESTROY = [
    ("vey", "It's gone. All of it. No one will ever burn a world with that machine again."),
    ("vey", "If New Dawn's people ever come home, Aster will have to be home enough. It's a good world."),
    ("vey", "Earth-Prime stays a memory... but a safe one. The Remnant are already scattering."),
    ("ai", "As the Forge died, its last pulse was answered from the galactic rim. A single tone, like a bell."),
    ("ai", "I've marked it (teal). Whoever built the Forge may have felt it break."),
    ("ai", "New Game+ is unlocked on the title screen: a new galaxy, harder foes, and you keep your gear."),
]

FORGE_CHOICE = ("The Stellar Forge",
                "Five Shards hum in their sockets. Vey's voice crackles over comms: \"Voyager... with this we "
                "could raise Earth-Prime from the dust. Or we could end the Forge forever, so no one ever uses it "
                "as Dravos did. It's your call.\"")


def signal_position(universe) -> Vector2:
    """Act III teaser: the Makers' bell, at the rim of the charted galaxy."""
    rng = rng_of(universe.seed, "bell")
    a = rng.uniform(0, math.tau)
    r = 9.5 * config.SECTOR_SIZE
    return Vector2(math.cos(a) * r, math.sin(a) * r) + Vector2(config.SECTOR_SIZE / 2, config.SECTOR_SIZE / 2)


class QuestManager:
    def __init__(self, game):
        self.game = game
        self.state = game.state
        bus = game.events
        bus.on("launched", self._on_launched)
        bus.on("docked", self._on_docked)
        bus.on("enemy_destroyed", self._on_kill)
        bus.on("relic_collected", self._on_relic)
        bus.on("boss_defeated", self._on_boss)
        bus.on("planet_landed", self._on_landed)
        bus.on("system_discovered", self._on_discovered)
        bus.on("ore_collected", self._on_ore)
        bus.on("shard_collected", self._on_shard)
        bus.on("forge_restored", self._on_forge)
        bus.on("creature_killed", self._on_creature)

    @property
    def chapter(self) -> dict:
        return CHAPTERS[min(self.state.chapter, len(CHAPTERS) - 1)]

    @property
    def cid(self) -> str:
        return self.chapter["id"]

    def start(self) -> None:
        if self.state.chapter == 0:
            self.game.dialogue.say(INTRO)

    def advance(self) -> None:
        self.state.chapter += 1
        self.state.chapter_progress = 0
        ch = self.chapter
        if self.cid == "keys" and self.state.has_all_relics():
            self.state.chapter += 1  # keys were found early: skip straight on
            ch = self.chapter
        label = "ACT II" if self.cid == "shards" else "ACT III" if self.cid == "road" else \
            f"Chapter {self.state.chapter + 1}"
        self.game.banner.show(f"{label}: {ch['title']}", ch["objective"], 4.0)
        self.game.audio.play("discover")
        self.game.save()

    # --- event handlers ---------------------------------------------------
    def _on_launched(self, **_):
        if self.cid == "awaken":
            self.advance()

    def _on_docked(self, station_id: str, **_):
        if self.cid == "signal" and station_id == HOME_STATION:
            self.game.dialogue.say(SIGNAL_DONE)
            self.advance()
        elif self.cid == "return" and station_id == HOME_STATION and self.state.has_all_relics():
            self.game.dialogue.say(RETURN_DONE, on_done=self.game.start_boss_sequence)
            self.state.chapter = CHAPTERS.index(next(c for c in CHAPTERS if c["id"] == "boss"))

    def _on_kill(self, quest: bool = False, warden: str | None = None, flagship: bool = False, **_):
        self.state.kills += 1
        if warden and warden not in self.state.wardens_killed:
            self.state.wardens_killed.append(warden)
            pl = self.game.universe.sector(*map(int, warden.split(","))).shard_planet
            where = pl.name if pl else "the planet below"
            self.game.banner.show("Remnant Warden destroyed", f"The vault on {where} is unguarded", 4.0)
            self._contract_progress("hunt")
        elif flagship:
            self.state.bump("flagships")
            self._contract_progress("hunt")
        if self.cid == "raiders":
            self.state.chapter_progress += 1
            left = self.chapter["count"] - self.state.chapter_progress
            if left <= 0:
                self.game.dialogue.say(RAIDERS_DONE)
                self.advance()
            else:
                self.game.toasts.add(f"Raider down - {left} remaining", (255, 200, 120))
        self._contract_progress("bounty")

    def _on_relic(self, biome: str, **_):
        if biome in self.state.relics:
            return
        self.state.relics.append(biome)
        self.game.banner.show(f"{RELIC_NAMES[biome]} recovered!", f"{len(self.state.relics)}/3 Ancient Keys")
        self.game.audio.play("relic")
        self.game.dialogue.say(KEY_LINES[biome])
        if self.cid == "keys":
            self.state.chapter_progress = len(self.state.relics)
            if self.state.has_all_relics():
                self.advance()

    def _on_boss(self, **_):
        self.state.boss_defeated = True
        from . import saga
        if saga.data(self.state)["ark"] == "unknown":
            self.state.saga["ark"] = "known"          # Vey's rumour of the New Dawn
        self.state.chapter = ACT2_START - 1
        self.game.dialogue.say(EPILOGUE)
        self.advance()
        if self.cid == "shards" and self.state.has_all_shards():
            self.advance()

    def _on_shard(self, biome: str, **_):
        st = self.state
        if biome in st.shards:
            return
        st.shards.append(biome)
        self.game.banner.show(f"{SHARD_NAMES[biome]} recovered!", f"{len(st.shards)}/5 Forge Shards", 4.0)
        self.game.audio.play("relic")
        self.game.dialogue.say(SHARD_LINES[biome])
        if self.cid == "shards":
            st.chapter_progress = len(st.shards)
            if st.has_all_shards():
                self.game.dialogue.say(ALL_SHARDS)
                self.advance()

    def _on_forge(self, ending: str = "rebuild", **_):
        self.state.forge_restored = True
        self.state.ending = ending
        self.state.chapter = FREE
        self.state.chapter_progress = 0
        self.game.dialogue.say(LEGEND if ending == "rebuild" else LEGEND_DESTROY)

    def _on_creature(self, **_):
        self.state.bump("creatures")

    def _on_landed(self, planet_id: str, new: bool, **_):
        if new:
            self._contract_progress("survey")

    def _on_discovered(self, **_):
        self._contract_progress("explore")

    def _on_ore(self, amount: int = 1, **_):
        self.state.bump("ore_total", amount)
        self._contract_progress("mining", amount)

    # --- objective info for the HUD ---------------------------------------
    def objective_text(self) -> str:
        ch = self.chapter
        txt = ch["objective"]
        if self.cid == "raiders":
            txt += f" ({self.state.chapter_progress}/{ch['count']})"
        elif self.cid == "keys":
            have = ", ".join(RELIC_NAMES[b] for b in self.state.relics) or "none yet"
            txt += f" ({len(self.state.relics)}/3: {have})"
        elif self.cid == "shards":
            txt += f" ({len(self.state.shards)}/5)"
        return txt

    def missing_relics(self) -> list[str]:
        return [b for b in RELIC_BIOMES if b not in self.state.relics]

    def missing_shards(self) -> list[str]:
        return [b for b in SHARD_BIOMES if b not in self.state.shards]

    def warden_alive(self, planet) -> bool:
        """Is this Shard world still blockaded by its Remnant Warden?"""
        if planet is None or not planet.shard or not self.state.boss_defeated:
            return False
        key = f"{planet.sector[0]},{planet.sector[1]}"
        return key not in self.state.wardens_killed and planet.shard not in self.state.shards

    def target(self):
        """(label, body) the compass should point at, or None."""
        u = self.game.universe
        if self.cid == "return":
            return "Haven Station", u.find_body(HOME_STATION)
        if self.cid == "forge":
            return "The Stellar Forge", u.find_body(FORGE)
        return None

    def start_act_three(self) -> None:
        """Called when the Bell has rung: the Makers' road opens."""
        from . import saga
        st = self.state
        if st.chapter > FREE:
            return
        st.chapter = FREE
        self.advance()
        self.game.banner.show("ACT III: The Makers", self.chapter["objective"], 5.0)
        self.game.dialogue.say(saga.ACT_THREE)

    def shard_target(self, pos):
        """Nearest vault still holding a Shard (the violet compass)."""
        best, best_d = None, float("inf")
        t = self.state.world_time
        for b in self.missing_shards():
            pl = self.game.universe.shard_planet(b)
            if pl is None:
                continue
            d = pl.pos(t).distance_to(pos)
            if d < best_d:
                best, best_d = pl, d
        return best

    # --- contracts (endless side content) ---------------------------------------
    CONTRACT_KINDS = {
        "bounty": ("Bounty", "Destroy {n} raiders", (4, 9), 70),
        "survey": ("Survey", "Land on {n} planets you haven't visited", (2, 4), 160),
        "explore": ("Cartography", "Discover {n} new star systems", (2, 4), 220),
        "mining": ("Mining", "Collect {n} ore", (8, 20), 22),
        "hunt": ("Remnant Hunt", "Destroy {n} Remnant flagship(s)", (1, 2), 900),
    }

    def offers(self, station_id: str) -> list[dict]:
        rng = rng_of(self.game.universe.seed, station_id, self.state.contracts_done)
        out = []
        sec = self.game.universe.find_body(station_id)
        danger = 1.0
        if sec is not None:
            sx, sy = (int(v) for v in station_id.split(":")[0].split(","))
            danger = self.game.universe.danger_at(sx, sy)
        kinds = [k for k in self.CONTRACT_KINDS if k != "hunt" or self.state.boss_defeated]
        for kind in rng.sample(kinds, 3):
            title, desc, (lo, hi), per = self.CONTRACT_KINDS[kind]
            n = rng.randint(lo, hi)
            out.append({"kind": kind, "title": title, "desc": desc.format(n=n), "need": n,
                        "have": 0, "reward": int(n * per * (0.8 + 0.25 * danger))})
        return out

    def accept(self, contract: dict) -> None:
        self.state.contract = dict(contract)
        self.game.toasts.add(f"Contract accepted: {contract['desc']}", (200, 220, 255))

    def _contract_progress(self, kind: str, amount: int = 1) -> None:
        c = self.state.contract
        if not c or c["kind"] != kind:
            return
        c["have"] = min(c["need"], c["have"] + amount)
        if c["have"] >= c["need"]:
            self.state.earn(c["reward"])
            self.state.add_rep(c.get("faction", "haven"), 4)
            self.state.contracts_done += 1
            self.state.contract = None
            self.game.banner.show("Contract complete", f"+{c['reward']} credits")
            self.game.audio.play("relic")
        else:
            self.game.toasts.add(f"{c['title']}: {c['have']}/{c['need']}", (200, 220, 255), 2.0)
