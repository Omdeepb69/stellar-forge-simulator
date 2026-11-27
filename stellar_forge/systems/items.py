"""Static game data for the long-term systems: ships, weapons, loot mods,
boss trophies, trade goods and factions."""
from __future__ import annotations

import random

# ---------------------------------------------------------------- ships
SHIPS = {
    "voyager": dict(name="Voyager", price=0, sprite="rocket/rocket.png", thrust=1.0, fuel=1.0, hull=1.0,
                    shield=1.0, turn=1.0, cargo=20, damage=1.0,
                    desc="Your old, rusty, reliable rocket. Balanced in every way."),
    "scout": dict(name="Pathfinder Scout", price=2600, sprite="generated/ships/scout.png", thrust=1.45, fuel=1.35,
                  hull=0.7, shield=0.9, turn=1.35, cargo=10, damage=0.9,
                  desc="Fast and long-legged. Fragile, but nothing catches it."),
    "gunship": dict(name="Bastion Gunship", price=4200, sprite="generated/ships/gunship.png", thrust=0.85,
                    fuel=0.9, hull=1.6, shield=1.4, turn=0.85, cargo=15, damage=1.35,
                    desc="Heavy armour and twin cannons. Built to break Wardens."),
    "hauler": dict(name="Mule Hauler", price=3200, sprite="generated/ships/hauler.png", thrust=0.8, fuel=2.0,
                   hull=1.3, shield=1.0, turn=0.8, cargo=60, damage=0.9,
                   desc="Twice the fuel of anything else. Built for the long dark."),
}

# ---------------------------------------------------------------- weapons
WEAPONS = {
    "blaster": dict(name="Pulse Blaster", price=0, icon="w_blaster",
                    desc="Rapid bolts. Upgrades at the station add damage and spread."),
    "missile": dict(name="Seeker Missiles", price=900, icon="w_missile",
                    desc="Slow to reload, but they hunt their target."),
}
FOOT_WEAPONS = {
    "sword": dict(name="Voyager's Blade", desc="Fast arcs. Reflects energy orbs."),
    "boomerang": dict(name="Plasma Boomerang", desc="Flies forward and returns, slicing enemies both ways."),
}

# ---------------------------------------------------------------- loot mods
RARITIES = [("common", 1.0, (200, 200, 210)), ("rare", 2.0, (90, 170, 255)),
            ("epic", 3.5, (200, 110, 255)), ("legendary", 6.0, (255, 190, 60))]
RARITY = {r: (m, c) for r, m, c in RARITIES}
MOD_STATS = {
    "damage": ("Overcharged Capacitor", "weapon damage", 0.05),
    "fire_rate": ("Cycler Coil", "fire rate", 0.04),
    "hull": ("Reinforced Plating", "hull", 0.05),
    "shield": ("Shield Lattice", "shield", 0.06),
    "thrust": ("Afterburner Nozzle", "thrust", 0.04),
    "fuel": ("Expanded Tanks", "fuel capacity", 0.06),
    "melee": ("Monomolecular Edge", "melee damage", 0.08),
}
MOD_SLOTS = 3


def roll_mod(rng: random.Random, min_rarity: int = 0, luck: float = 0.0) -> dict:
    roll = rng.random() + luck
    idx = 0 if roll < 0.6 else 1 if roll < 0.88 else 2 if roll < 0.98 else 3
    idx = max(idx, min_rarity)
    rarity, mult, _c = RARITIES[idx]
    stat = rng.choice(list(MOD_STATS))
    name, label, base = MOD_STATS[stat]
    value = round(base * mult, 3)
    prefix = {"common": "", "rare": "Fine ", "epic": "Masterwork ", "legendary": "Ancient "}[rarity]
    return {"id": f"m{rng.randrange(1 << 30)}", "name": prefix + name, "rarity": rarity, "stat": stat,
            "value": value, "label": f"+{value * 100:.0f}% {label}"}


def mod_value(mod: dict) -> int:
    return int(120 * RARITY[mod["rarity"]][0] ** 1.4)

# ---------------------------------------------------------------- planet bosses
BOSSES = {
    "desert": dict(id="wyrm", name="Sand Wyrm", trophy="Wyrm Scale", icon="t_wyrm",
                   perk="+20% hull integrity"),
    "ice": dict(id="golem", name="Frost Golem", trophy="Frost Core", icon="t_golem",
                perk="+30% shield capacity"),
    "volcanic": dict(id="titan", name="Magma Titan", trophy="Magma Heart", icon="t_titan",
                     perk="Immune to lava, heat and hot vents"),
    "crystal": dict(id="queen", name="Hive Queen", trophy="Prism Crown", icon="t_queen",
                    perk="+25% weapon damage"),
    "ocean": dict(id="leviathan", name="Leviathan", trophy="Abyssal Pearl", icon="t_leviathan",
                  perk="Swim fast, breathe acid, double jetpack in water"),
}

# ---------------------------------------------------------------- factions
FACTIONS = {
    "haven": ("Haven Coalition", "generated/factions/haven.png", (110, 170, 255)),
    "traders": ("Free Traders", "generated/factions/traders.png", (255, 210, 90)),
    "remnant": ("The Remnant", "generated/factions/remnant.png", (120, 230, 140)),
}


def standing(rep: float) -> str:
    if rep <= -60:
        return "Hated"
    if rep <= -20:
        return "Hostile"
    if rep < 20:
        return "Neutral"
    if rep < 50:
        return "Friendly"
    if rep < 80:
        return "Honored"
    return "Exalted"


def price_mult(rep: float) -> float:
    """Better standing = better prices (from +20% down to -20%)."""
    return max(0.8, min(1.2, 1.0 - rep * 0.002))

# ---------------------------------------------------------------- difficulty
DIFFICULTY = {
    "story": dict(name="Story", taken=0.5, enemy_hp=0.7, desc="Relaxed: enemies hit half as hard."),
    "normal": dict(name="Voyager", taken=1.0, enemy_hp=1.0, desc="The intended experience."),
    "hard": dict(name="Hardened", taken=1.5, enemy_hp=1.3, desc="Everything bites harder. Bigger rewards."),
}
