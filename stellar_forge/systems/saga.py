"""Act III ("The Makers") and the side arcs that feed it.

* The Bell's reveal: the Voyager and ORA are Maker-built seedwalkers.
* The Maker Road: three waystones far out, each with a trial -
    Making  (hold the waystone while it wakes, against raider waves)
    Memory  (answer the Makers' three questions - the answers are in the story)
    Mercy   (decide the fate of the crippled Remnant ship "Penitent")
* The Last Smith: ring the Bell again and fight the Makers' judge. Who flies with
  you depends on what you did: Corps rank, Remnant mercy, the New Dawn ark, the
  settlers you helped. The verdict afterwards weighs it all.
* Side arcs: the New Dawn ark (escort 2,000 survivors - and Vey's brother - home),
  Remnant defectors (escort them to Haven: the Remnant can change), and a
  homecoming town on Earth-Prime (or Aster, if the Forge was destroyed).

State lives in ``GameState.saga``.
"""
from __future__ import annotations

import math
import random

from pygame.math import Vector2

from .. import config
from ..world.rng import rng_of

WAYSTONES = ("making", "memory", "mercy")
WAY_INFO = {
    "making": ("Waystone of Making", "Hold the waystone while it wakes", (255, 190, 110)),
    "memory": ("Waystone of Memory", "Answer the Makers' questions", (120, 255, 230)),
    "mercy": ("Waystone of Mercy", "Decide the fate of the Penitent", (200, 170, 255)),
}
MAKING_TIME = 60.0

BELL_LINES = [
    (1.5, "At the rim of everything charted, a structure older than the stars."),
    (5.0, "You touch it, and it rings once."),
    (8.5, "Far beyond, something that remembers making worlds turns towards the sound."),
]

ACT_THREE = [
    ("ai", "Voyager... the Bell is speaking. Not to Haven. To us. It knows our names."),
    ("ai", "'Seedwalker V-7, and its warden-mind ORA.' That's what it calls us."),
    ("pilot", "Seedwalker? ORA, I was a Fleet pilot. I remember Earth-Prime."),
    ("ai", "You remember what you were made to remember. The cryo pod, the wake condition, my own code - "
           "none of it was human. The Smiths of Anvar left us here, to wake if a Forge ever stirred."),
    ("ai", "They're coming to judge what the younger peoples did with their machine. Before they arrive, the "
           "Bell shows a road: three waystones, three trials. I've marked them in teal."),
    ("vey", "...Voyager, I heard all of that. Whatever you are - you're still the one who saved Haven. Go."),
]

MEMORY_QUESTIONS = [
    ("Who first turned the Forge against a world?",
     [("Dr. Kael Dravos", True), ("Commander Vey", False), ("The Smiths of Anvar", False)]),
    ("When a Key's bearer falls, where does the Key go?",
     [("Into the Forge", False), ("Home, to its own lock", True), ("It shatters", False)]),
    ("How many songs grew the Forge's heart?",
     [("Three", False), ("Seven", False), ("Five", True)]),
]

PENITENT_LINES = [
    ("pirate", "This is Exarch Sonn of the Remnant ship Penitent. Our engines are dead. We won't fight you."),
    ("pirate", "I was at Earth-Prime. I cheered. I've spent every night since trying to un-hear myself."),
    ("pirate", "The Makers' stone asked us what we are now. We didn't have an answer. Maybe you do."),
]

ARK_HAIL = [
    ("survivor", "This is Lieutenant Tomas Vey, acting captain of the ark New Dawn. Two thousand souls in cryo."),
    ("survivor", "Our drive is half-dead and the raiders have been circling for weeks. Is Haven... still there?"),
]
ARK_HOME = [
    ("vey", "Tomas? TOMAS. ...I kept it, you know. All of it. I never stopped looking."),
    ("survivor", "Asha. I heard your voice on every channel for a year. I thought I was dreaming it."),
    ("vey", "Voyager - two thousand people. Thank you. Haven will never forget this."),
]

DEFECTOR_HAIL = ("Remnant defectors",
                 "A battered Remnant ship hails on an open channel: \"Please - we want out. The Warlord is dead and "
                 "the Wardens shoot deserters. Haven might take us, if someone vouched for us.\"")


def data(st) -> dict:
    s = st.saga
    s.setdefault("waystones", [])
    s.setdefault("ark", "unknown")          # unknown | known | escort | rescued
    s.setdefault("defectors", 0)
    return s


# ---------------------------------------------------------------- places
def waystone_pos(universe, kind: str) -> Vector2:
    rng = rng_of(universe.seed, "waystones")
    base = rng.uniform(0, math.tau)
    k = WAYSTONES.index(kind)
    a = base + k * math.tau / 3 + k * 0.17            # three directions, roughly a third of a turn apart
    r = (5.2 + k * 0.9) * config.SECTOR_SIZE
    c = Vector2(config.SECTOR_SIZE / 2, config.SECTOR_SIZE / 2)
    return c + Vector2(math.cos(a), math.sin(a)) * r


def ark_pos(universe) -> Vector2:
    """Deep inside a nebula 3-5 sectors out ('beyond the Veil')."""
    rng = random.Random(universe.seed * 13 + 7)
    rings = [(dx, dy) for dx in range(-5, 6) for dy in range(-5, 6) if 3 <= max(abs(dx), abs(dy)) <= 5]
    rng.shuffle(rings)
    for dx, dy in rings[:60]:
        sec = universe.sector(dx, dy)
        if sec.nebulae:
            return Vector2(sec.nebulae[0].center)
    dx, dy = rings[0]
    return Vector2((dx + 0.5) * config.SECTOR_SIZE, (dy + 0.5) * config.SECTOR_SIZE)


# ---------------------------------------------------------------- the verdict
def deeds(game) -> dict:
    st = game.state
    from . import corps_career
    s = data(st)
    return {
        "settlers": st.stats.get("settlers", 0),
        "groups": sum(1 for v in st.groups.values() if v.get("met")),
        "corps": corps_career.rank(st),
        "remnant": st.rep.get("remnant", -60),
        "mercy": s.get("penitent") == "spared",
        "defectors": s.get("defectors", 0),
        "ark": s.get("ark") == "rescued",
        "ending": st.ending,
    }


def allies_for(game) -> list[tuple[str, str, int]]:
    """(who, label, count) that answer the final call."""
    d = deeds(game)
    out = [("corps", "Survey Corps wing", 1 + min(2, d["corps"]))]
    if d["mercy"] or d["remnant"] >= 0 or d["defectors"] >= 2:
        out.append(("free", "Remnant Free Fleet", 2))
    if d["ark"]:
        out.append(("ark", "New Dawn lancers", 1))
    if d["settlers"] >= 3:
        out.append(("frontier", "Frontier militia", 1 if d["settlers"] < 8 else 2))
    return out


def verdict(game) -> tuple[str, list[str]]:
    d = deeds(game)
    score = (min(d["settlers"], 10) + d["groups"] * 2 + d["corps"] * 2 + (4 if d["mercy"] else 0)
             + min(d["defectors"], 3) * 2 + (5 if d["ark"] else 0))
    lines = []
    if d["ending"] == "rebuild":
        lines.append("Earth-Prime turns again in Haven's sky - a world remade by a machine built to make worlds.")
    else:
        lines.append("The Forge is gone. No hand will ever turn it on a world again - not even yours.")
    if d["ark"]:
        lines.append("Two thousand sleepers of the New Dawn woke to a sunrise. Asha and Tomas Vey watched it together.")
    else:
        lines.append("Somewhere beyond a nebula, an ark still drifts, waiting for a pilot who never came.")
    if d["mercy"] or d["defectors"]:
        lines.append("The Remnant learned it could be something else. Some of them came home.")
    else:
        lines.append("The Remnant remained what Dravos made them, and the frontier stayed dangerous.")
    if d["settlers"] >= 3:
        lines.append(f"{d['settlers']} frontier camps remember a blue pilot who stopped to help.")
    if d["corps"] >= 2:
        lines.append("The Survey Corps flies the Voyager's colours on every wing.")
    if score >= 24:
        tier = "stay"
        lines.append("The Last Smith lowers its hammer. 'You did not need us. So we will stay - and learn from you.'")
    elif score >= 12:
        tier = "watch"
        lines.append("The Last Smith turns away. 'Not yet. But soon. We will watch, and wait.'")
    else:
        tier = "leave"
        lines.append("The Last Smith is silent for a long time. 'Then it is yours. Make better of it than we did.'")
    return tier, lines


def install(game) -> None:
    """Saves made before Act III existed: if the Bell already rang, open the road now."""
    st = game.state
    data(st)
    if st.boss_defeated and st.saga.get("ark") == "unknown":
        st.saga["ark"] = "known"
    from .quests import FREE
    if st.signal_found and st.chapter == FREE:
        game.quests.start_act_three()
