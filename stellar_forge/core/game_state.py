"""Persistent player/campaign state shared by every scene.

This replaces the old pattern of deep-copying the whole world (which
crashed on pygame Surfaces) and threading ``rocket_state`` dicts around.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field

from .. import config

UPGRADES = {
    "engine":  ("Ion Engine",     "+18% thrust per level"),
    "tank":    ("Fuel Tank",      "+35% fuel capacity"),
    "hull":    ("Hull Plating",   "+30% hull integrity"),
    "shield":  ("Shield Emitter", "+40% shield capacity"),
    "blaster": ("Pulse Blaster",  "More damage, faster fire"),
    "scanner": ("Deep Scanner",   "Longer radar + relic compass range"),
    "suit":    ("Exo Suit",       "More pilot HP and jetpack fuel"),
}

RELIC_BIOMES = ("desert", "ice", "forest")
RELIC_NAMES = {"desert": "Sun Key", "ice": "Frost Key", "forest": "Verdant Key"}

# Act II: the Forge's core shattered into five Shards when the Warlord fell
SHARD_BIOMES = ("crystal", "volcanic", "toxic", "ocean", "barren")
SHARD_NAMES = {"crystal": "Prism Shard", "volcanic": "Ember Shard", "toxic": "Blight Shard",
               "ocean": "Tide Shard", "barren": "Void Shard"}
SHARD_COLORS = {"crystal": (200, 140, 255), "volcanic": (255, 120, 40), "toxic": (170, 255, 60),
                "ocean": (80, 190, 255), "barren": (230, 230, 240)}


@dataclass
class GameState:
    seed: int = field(default_factory=lambda: random.randint(1, 2**31 - 1))
    world_time: float = 0.0
    credits: int = 150
    ore: int = 0
    scan_data: int = 0
    fuel: float = config.SHIP_BASE_FUEL
    hull: float = config.SHIP_BASE_HULL
    shield: float = config.SHIP_BASE_SHIELD
    pilot_hp: float = 100.0
    medkits: int = 2
    upgrades: dict = field(default_factory=lambda: {k: 0 for k in UPGRADES})
    relics: list = field(default_factory=list)
    chapter: int = 0
    chapter_progress: int = 0
    boss_defeated: bool = False
    discovered_systems: list = field(default_factory=list)   # [sector_key, ...]
    landed_planets: list = field(default_factory=list)       # planet ids
    looted_strongholds: list = field(default_factory=list)   # planet ids
    collected: list = field(default_factory=list)            # surface pickups ids
    destroyed: list = field(default_factory=list)            # asteroid ids
    contract: dict | None = None
    contracts_done: int = 0
    kills: int = 0
    location: dict = field(default_factory=lambda: {"kind": "surface", "planet": "0,0:0"})
    # --- Act II and long-term progression ---
    play_time: float = 0.0
    shards: list = field(default_factory=list)               # biome ids
    wardens_killed: list = field(default_factory=list)       # sector keys
    forge_restored: bool = False
    ng_plus: int = 0
    achievements: list = field(default_factory=list)
    biomes_visited: list = field(default_factory=list)
    stats: dict = field(default_factory=lambda: {"creatures": 0, "ore_total": 0, "flagships": 0,
                                                 "max_distance": 0, "strongholds": 0, "credits_earned": 0,
                                                 "events": 0, "derelicts": 0, "trades": 0, "bosses": 0,
                                                 "settlers": 0, "ruins": 0, "pods": 0, "vaults": 0})
    # --- quality of life ---
    difficulty: str = "normal"
    waypoint: list | None = None                             # [x, y, label]
    hints_seen: list = field(default_factory=list)
    # --- exploration & lore ---
    logs: list = field(default_factory=list)                 # lore log ids found
    scanned: list = field(default_factory=list)              # "biome:kind" fauna met and defeated
    derelicts_looted: list = field(default_factory=list)
    lairs_cleared: list = field(default_factory=list)        # planet ids
    trophies: list = field(default_factory=list)             # biome ids of slain planet bosses
    # --- economy & gear ---
    outposts: dict = field(default_factory=dict)             # planet id -> buildings
    ship: str = "voyager"
    ships_owned: list = field(default_factory=lambda: ["voyager"])
    weapons: list = field(default_factory=lambda: ["blaster"])
    weapon: str = "blaster"
    foot_weapon: str = "sword"
    mods: list = field(default_factory=list)                 # all mods owned
    equipped: list = field(default_factory=list)             # mod ids (max 3)
    rep: dict = field(default_factory=lambda: {"haven": 10, "traders": 0, "remnant": -60})
    # --- story ---
    ending: str | None = None                                # "rebuild" | "destroy"
    saga: dict = field(default_factory=dict)                 # Act III + side arcs (see systems/saga.py)
    signal_found: bool = False
    # --- planets: materials and points of interest ---
    materials: dict = field(default_factory=dict)            # biome id -> count
    poi_state: dict = field(default_factory=dict)
    corps_merit: int = 0                                     # Survey Corps Merit, earned helping Corps ships
    corps_merit_total: int = 0                               # lifetime Merit: sets your Corps rank
    corps_job: dict | None = None                            # the active Corps contract
    corps_free_day: int = -1                                 # Commander perk: last day of the free refuel
    groups: dict = field(default_factory=dict)              # roaming group key -> {"met", "planets", ...}
    caves_cleared: list = field(default_factory=list)        # planet ids whose cave vault is open            # poi id -> {"seen", "done", "hits", "quest", ...}

    # ---- derived stats -------------------------------------------------
    def lvl(self, key: str) -> int:
        return self.upgrades.get(key, 0)

    def hull_spec(self, key: str) -> float:
        from ..systems.items import SHIPS
        return SHIPS.get(self.ship, SHIPS["voyager"])[key]

    def mod_bonus(self, stat: str) -> float:
        return sum(m["value"] for m in self.mods if m["id"] in self.equipped and m["stat"] == stat)

    @property
    def diff(self) -> dict:
        from ..systems.items import DIFFICULTY
        return DIFFICULTY.get(self.difficulty, DIFFICULTY["normal"])

    @property
    def damage_taken(self) -> float:
        return self.diff["taken"]

    @property
    def enemy_hp_mult(self) -> float:
        return self.diff["enemy_hp"]

    @property
    def thrust(self) -> float:
        return (config.SHIP_BASE_THRUST * (1 + 0.18 * self.lvl("engine")) * self.hull_spec("thrust")
                * (1 + self.mod_bonus("thrust")))

    @property
    def turn_mult(self) -> float:
        return self.hull_spec("turn")

    @property
    def max_fuel(self) -> float:
        return (config.SHIP_BASE_FUEL * (1 + 0.35 * self.lvl("tank")) * self.hull_spec("fuel")
                * (1 + self.mod_bonus("fuel")))

    @property
    def max_hull(self) -> float:
        trophy = 1.2 if "desert" in self.trophies else 1.0
        return (config.SHIP_BASE_HULL * (1 + 0.30 * self.lvl("hull")) * self.hull_spec("hull")
                * (1 + self.mod_bonus("hull")) * trophy)

    @property
    def max_shield(self) -> float:
        trophy = 1.3 if "ice" in self.trophies else 1.0
        return (config.SHIP_BASE_SHIELD * (1 + 0.40 * self.lvl("shield")) * self.hull_spec("shield")
                * (1 + self.mod_bonus("shield")) * trophy)

    @property
    def weapon_mult(self) -> float:
        trophy = 1.25 if "crystal" in self.trophies else 1.0
        return self.hull_spec("damage") * (1 + self.mod_bonus("damage")) * trophy

    @property
    def blaster_damage(self) -> float:
        return (1.0 + 0.55 * self.lvl("blaster")) * self.weapon_mult

    @property
    def melee_damage(self) -> float:
        return (2 + 0.5 * self.lvl("suit")) * (1 + self.mod_bonus("melee")) * \
            (1.25 if "crystal" in self.trophies else 1.0)

    @property
    def fire_delay(self) -> float:
        return 0.2 * (0.86 ** self.lvl("blaster")) / (1 + self.mod_bonus("fire_rate"))

    def add_rep(self, faction: str, amount: float) -> None:
        self.rep[faction] = max(-100.0, min(100.0, self.rep.get(faction, 0) + amount))

    @property
    def scanner_range(self) -> float:
        return 6000 * (1 + 0.5 * self.lvl("scanner"))

    @property
    def max_pilot_hp(self) -> float:
        return 100 * (1 + 0.25 * self.lvl("suit"))

    @property
    def jetpack_capacity(self) -> float:
        return config.JETPACK_CAPACITY * (1 + 0.3 * self.lvl("suit"))

    def upgrade_cost(self, key: str) -> int:
        return int(140 * (self.lvl(key) + 1) ** 1.7)

    def upgrade_mats(self, key: str) -> dict:
        """Planet materials the next level of an upgrade needs (none for level 1)."""
        from ..systems.materials import upgrade_materials
        return upgrade_materials(key, self.lvl(key) + 1)

    # ---- helpers ---------------------------------------------------------
    def spend(self, amount: int) -> bool:
        if self.credits >= amount:
            self.credits -= amount
            return True
        return False

    def has_all_relics(self) -> bool:
        return all(b in self.relics for b in RELIC_BIOMES)

    def has_all_shards(self) -> bool:
        return all(b in self.shards for b in SHARD_BIOMES)

    def bump(self, stat: str, amount: float = 1) -> None:
        self.stats[stat] = self.stats.get(stat, 0) + amount

    def earn(self, amount: int) -> None:
        self.credits += int(amount)
        self.bump("credits_earned", int(amount))

    def new_game_plus(self) -> "GameState":
        """A fresh galaxy that keeps the pilot's gear, wallet and legend."""
        nxt = GameState(credits=self.credits, upgrades=dict(self.upgrades), ng_plus=self.ng_plus + 1,
                        achievements=list(self.achievements), stats=dict(self.stats),
                        play_time=self.play_time, kills=self.kills, contracts_done=self.contracts_done,
                        difficulty=self.difficulty, ship=self.ship, ships_owned=list(self.ships_owned),
                        weapons=list(self.weapons), weapon=self.weapon, foot_weapon=self.foot_weapon,
                        mods=[dict(m) for m in self.mods], equipped=list(self.equipped),
                        trophies=list(self.trophies), logs=list(self.logs), scanned=list(self.scanned),
                        hints_seen=list(self.hints_seen), materials=dict(self.materials),
                        medkits=self.medkits)
        nxt.fuel, nxt.hull, nxt.shield = nxt.max_fuel, nxt.max_hull, nxt.max_shield
        nxt.pilot_hp = nxt.max_pilot_hp
        return nxt

    def mark(self, list_name: str, key: str) -> None:
        lst = getattr(self, list_name)
        if key not in lst:
            lst.append(key)

    # ---- persistence -------------------------------------------------------
    def save(self, path=None) -> None:
        path = path or config.SAVE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=1))
        tmp.replace(path)

    @classmethod
    def load(cls, path=None) -> "GameState | None":
        path = path or config.SAVE_FILE
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        state = cls()
        for k, v in data.items():
            if hasattr(state, k):
                setattr(state, k, v)
        for k in UPGRADES:
            state.upgrades.setdefault(k, 0)
        for name in ("stats", "rep"):
            defaults = cls.__dataclass_fields__[name].default_factory()
            for k, v in defaults.items():
                getattr(state, name).setdefault(k, v)
        return state


SLOTS = 3


def slot_path(n: int):
    """Save file for slot ``n`` (slot 0 keeps the original file name)."""
    base = config.SAVE_FILE.parent
    return base / ("savegame.json" if n == 0 else f"savegame_{n + 1}.json")

