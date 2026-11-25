"""Planet materials: every landable biome yields one, and ship upgrades past
level 1 need them. That is what makes landing on many different worlds pay."""
from __future__ import annotations

# biome -> (name, map/ui colour)
MATERIALS = {
    "forest": ("Heartwood", (230, 170, 80)),
    "desert": ("Sunglass", (240, 220, 90)),
    "ice": ("Cryo Crystal", (110, 220, 255)),
    "volcanic": ("Magmite", (255, 140, 60)),
    "crystal": ("Prism Dust", (200, 140, 255)),
    "toxic": ("Spore Resin", (170, 240, 70)),
    "ocean": ("Tide Coral", (255, 120, 150)),
    "barren": ("Void Iron", (150, 150, 255)),
}

# upgrade -> (primary material, secondary material)
UPGRADE_MATS = {
    "engine": ("volcanic", "desert"),
    "tank": ("toxic", "ocean"),
    "hull": ("barren", "volcanic"),
    "shield": ("ice", "ocean"),
    "blaster": ("crystal", "volcanic"),
    "scanner": ("desert", "ice"),
    "suit": ("forest", "toxic"),
}


def name(biome: str) -> str:
    return MATERIALS[biome][0]


def color(biome: str):
    return MATERIALS[biome][1]


def upgrade_materials(key: str, level: int) -> dict:
    """Materials needed to buy ``level`` (1-based) of an upgrade. Level 1 is credits only."""
    if key not in UPGRADE_MATS or level <= 1:
        return {}
    a, b = UPGRADE_MATS[key]
    need = {a: 3 * (level - 1)}
    if level >= 3:
        need[b] = need.get(b, 0) + 2 * (level - 2)
    return need


def has(state, need: dict) -> bool:
    return all(state.materials.get(b, 0) >= n for b, n in need.items())


def take(state, need: dict) -> bool:
    if not has(state, need):
        return False
    for b, n in need.items():
        state.materials[b] = state.materials.get(b, 0) - n
    return True


def give(game, biome: str, n: int, toast: bool = True) -> None:
    if biome not in MATERIALS or n <= 0:
        return
    st = game.state
    st.materials[biome] = st.materials.get(biome, 0) + n
    if toast:
        game.toasts.add(f"+{n} {name(biome)}", color(biome), 2.0, icon=f"mat_{biome}")


def describe(need: dict) -> str:
    return ", ".join(f"{n} {name(b)}" for b, n in need.items())
