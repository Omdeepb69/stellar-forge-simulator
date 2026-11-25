"""Procedural names for stars, planets and stations."""
import random

_START = ["Ae", "Al", "Ar", "Bel", "Cor", "Cy", "Da", "El", "Ka", "Ke", "Ly", "Mi", "No", "Or",
          "Pha", "Qu", "Rho", "Sa", "Sel", "Ta", "Tha", "Ul", "Ve", "Xi", "Za", "Zo", "Ny", "Ix"]
_MID = ["ra", "lo", "ne", "ri", "tha", "go", "vi", "ma", "ce", "dra", "lu", "phi", "so", "ka", "ny"]
_END = ["on", "us", "ia", "ar", "is", "os", "a", "ex", "ion", "ae", "or", "yx", "um", "eth"]
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_STATION = ["Outpost", "Station", "Waypoint", "Depot", "Bastion", "Relay", "Harbor"]


def star_name(rng: random.Random) -> str:
    name = rng.choice(_START) + rng.choice(_MID) + rng.choice(_END)
    if rng.random() < 0.3:
        name += f"-{rng.randint(2, 999)}"
    return name


def planet_name(star: str, index: int, rng: random.Random) -> str:
    if rng.random() < 0.35:
        return rng.choice(_START) + rng.choice(_END)
    return f"{star.split('-')[0]} {_ROMAN[index % len(_ROMAN)]}"


def station_name(rng: random.Random) -> str:
    return f"{rng.choice(_START)}{rng.choice(_END)} {rng.choice(_STATION)}"

_SHIP_A = ["Silent", "Broken", "Wandering", "Last", "Crimson", "Hollow", "Distant", "Iron", "Pale", "Sleeping"]
_SHIP_B = ["Promise", "Horizon", "Lantern", "Covenant", "Meridian", "Sparrow", "Anvil", "Mercy", "Tide", "Hymn"]


def derelict_name(rng: random.Random) -> str:
    return f"Wreck of the {rng.choice(_SHIP_A)} {rng.choice(_SHIP_B)}"
