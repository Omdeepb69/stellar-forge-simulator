"""Achievements and pilot ranks: long-term goals for the endless galaxy.

Each achievement is a pure check on ``GameState`` so it works on old saves
too; the tracker polls once a second and announces anything new.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from ..core.game_state import GameState


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    desc: str
    check: Callable[[GameState], bool]
    progress: Callable[[GameState], tuple[float, float]] | None = None
    secret: bool = False


def _count(attr, n):
    return (lambda s: len(getattr(s, attr)) >= n, lambda s: (min(n, len(getattr(s, attr))), n))


def _stat(key, n):
    return (lambda s: s.stats.get(key, 0) >= n, lambda s: (min(n, s.stats.get(key, 0)), n))


LANDABLE = ("desert", "ice", "forest", "ocean", "volcanic", "toxic", "crystal", "barren")

ACHIEVEMENTS = [
    Achievement("liftoff", "Liftoff", "Board your rocket and leave Aster", lambda s: s.chapter >= 1),
    Achievement("harbour", "Safe Harbour", "Dock at Haven Station", lambda s: s.chapter >= 2),
    Achievement("ace", "Ace Pilot", "Destroy 25 raiders",
                lambda s: s.kills >= 25, lambda s: (min(25, s.kills), 25)),
    Achievement("scourge", "Scourge of Raiders", "Destroy 150 raiders",
                lambda s: s.kills >= 150, lambda s: (min(150, s.kills), 150)),
    Achievement("keeper", "Keeper of Keys", "Recover all three Ancient Keys", *_count("relics", 3)),
    Achievement("bane", "Warlord's Bane", "Defeat the Warlord", lambda s: s.boss_defeated),
    Achievement("warden", "Warden Breaker", "Destroy a Remnant Warden", *_count("wardens_killed", 1)),
    Achievement("shards", "Shard Bearer", "Recover all five Forge Shards", *_count("shards", 5)),
    Achievement("worldsmith", "Worldsmith", "Reignite the Stellar Forge", lambda s: s.forge_restored),
    Achievement("flagship", "Flagship Hunter", "Destroy 3 roaming Remnant flagships", *_stat("flagships", 3)),
    Achievement("cartographer", "Cartographer", "Discover 10 star systems", *_count("discovered_systems", 11)),
    Achievement("atlas", "Star Atlas", "Discover 40 star systems", *_count("discovered_systems", 41)),
    Achievement("walker", "World Walker", "Set foot on 10 different worlds", *_count("landed_planets", 10)),
    Achievement("horizons", "Every Horizon", "Walk on all 8 kinds of landable world",
                lambda s: all(b in s.biomes_visited for b in LANDABLE),
                lambda s: (sum(b in s.biomes_visited for b in LANDABLE), len(LANDABLE))),
    Achievement("prospector", "Prospector", "Collect 150 ore", *_stat("ore_total", 150)),
    Achievement("xeno", "Xenohunter", "Defeat 50 alien creatures", *_stat("creatures", 50)),
    Achievement("vaults", "Tomb Raider", "Loot 8 ancient strongholds", *_count("looted_strongholds", 8)),
    Achievement("freelancer", "Freelancer", "Complete 10 station contracts",
                lambda s: s.contracts_done >= 10, lambda s: (min(10, s.contracts_done), 10)),
    Achievement("tycoon", "Tycoon", "Hold 10,000 credits at once",
                lambda s: s.credits >= 10_000, lambda s: (min(10_000, s.credits), 10_000)),
    Achievement("kitted", "Fully Kitted", "Raise any upgrade to max level",
                lambda s: max(s.upgrades.values(), default=0) >= 5),
    Achievement("abyss", "Into the Abyss", "Fly 12 sectors away from Haven", *_stat("max_distance", 12)),
    Achievement("boarder", "Boarding Party", "Open a captain's vault on a derelict", *_count("derelicts_looted", 1)),
    Achievement("salvager", "Salvage King", "Loot 8 derelicts", *_count("derelicts_looted", 8)),
    Achievement("beast", "Beastslayer", "Slay a legendary planet boss", *_count("lairs_cleared", 1)),
    Achievement("trophies", "Trophy Hall", "Claim all five boss trophies", *_count("trophies", 5)),
    Achievement("xenologist", "Xenologist", "Defeat 10 different kinds of creature", *_count("scanned", 10)),
    Achievement("archivist", "Archivist", "Recover all 30 lore logs", *_count("logs", 30)),
    Achievement("landlord", "Homesteader", "Found an outpost",
                lambda s: len(s.outposts) >= 1, lambda s: (min(1, len(s.outposts)), 1)),
    Achievement("network", "Warp Network", "Link two outposts with warp beacons",
                lambda s: sum(1 for o in s.outposts.values() if o.get("beacon")) >= 2,
                lambda s: (min(2, sum(1 for o in s.outposts.values() if o.get("beacon"))), 2)),
    Achievement("eventful", "Eventful Voyage", "Resolve 10 random encounters", *_stat("events", 10)),
    Achievement("fleet", "Fleet Admiral", "Own three ships", *_count("ships_owned", 3)),
    Achievement("legendary", "Ancient Power", "Find a legendary mod",
                lambda s: any(m["rarity"] == "legendary" for m in s.mods)),
    Achievement("exalted", "Exalted", "Reach Exalted standing with any faction",
                lambda s: max(s.rep.get("haven", 0), s.rep.get("traders", 0)) >= 80),
    Achievement("choice", "The Choice", "Decide the fate of the Forge", lambda s: s.ending is not None,
                secret=True),
    Achievement("bell", "Signal Received", "Answer the bell at the galaxy's rim", lambda s: s.signal_found,
                secret=True),
    Achievement("legend", "Second Voyage", "Start a New Game+", lambda s: s.ng_plus >= 1, secret=True),
    # ---- the frontier, the Corps and Act III
    Achievement("neighbour", "Good Neighbour", "Finish 10 settler jobs", *_stat("settlers", 10)),
    Achievement("riddler", "Ruin Reader", "Solve 5 Architect ruins", *_stat("ruins", 5)),
    Achievement("delver", "Deep Delver", "Open 3 cave vaults", *_stat("vaults", 3)),
    Achievement("company", "Good Company", "Meet all four roaming groups",
                lambda s: sum(1 for k in ("survey", "caravan", "pilgrims", "gang") if s.groups.get(k, {}).get("met")) >= 4,
                lambda s: (sum(1 for k in ("survey", "caravan", "pilgrims", "gang")
                               if s.groups.get(k, {}).get("met")), 4)),
    Achievement("commander", "Corps Commander", "Reach the Survey Corps' highest rank",
                lambda s: s.corps_merit_total >= 450, lambda s: (min(450, s.corps_merit_total), 450)),
    Achievement("contractor", "On Contract", "Complete 5 Corps contracts", *_stat("corps_jobs", 5)),
    Achievement("ark", "New Dawn", "Bring the ark New Dawn home to Haven",
                lambda s: s.saga.get("ark") == "rescued"),
    Achievement("mercy", "Mercy", "Spare the Penitent or escort 3 Remnant defectors to Haven",
                lambda s: s.saga.get("penitent") == "spared" or s.saga.get("defectors", 0) >= 3),
    Achievement("makers", "Maker Road", "Pass all three waystone trials",
                lambda s: len(s.saga.get("waystones", [])) >= 3, secret=True),
    Achievement("eternal", "Voyager Eternal", "Face the Last Smith and hear the Makers' verdict",
                lambda s: bool(s.saga.get("verdict")), secret=True),
]
BY_ID = {a.id: a for a in ACHIEVEMENTS}

RANKS = [(0, "Cadet"), (4, "Pilot"), (8, "Navigator"), (13, "Ace"), (19, "Commander"),
         (26, "Star Captain"), (33, "Legend")]


def rank(state: GameState) -> str:
    n = len(state.achievements)
    name = RANKS[0][1]
    for need, title in RANKS:
        if n >= need:
            name = title
    return name + (f" +{state.ng_plus}" if state.ng_plus else "")


class AchievementTracker:
    def __init__(self, game):
        self.game = game
        self.timer = 0.0

    def update(self, dt: float) -> None:
        st = self.game.state
        if st is None:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        self.timer = 1.0
        for a in ACHIEVEMENTS:
            if a.id not in st.achievements and a.check(st):
                st.achievements.append(a.id)
                self.game.toasts.add(f"Achievement: {a.name}", (255, 215, 110), 4.5, icon="trophy")
                self.game.audio.play("discover", 0.7)


def distance_sectors(pos, sector_size) -> int:
    return int(max(abs(math.floor(pos[0] / sector_size + 0.5)), abs(math.floor(pos[1] / sector_size + 0.5))))
