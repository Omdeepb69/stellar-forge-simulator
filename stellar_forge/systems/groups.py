"""Roaming groups: named bands that travel a route of worlds and remember you.

Where a group is depends only on the universe seed and the world clock, so it is
the same every time you look (and the same after loading a save). What you have
done with each group lives in ``GameState.groups``.
"""
from __future__ import annotations

import random

from . import materials as M
from . import species as SP

DAY = 240.0                     # world-time seconds per day (matches the surface day/night cycle)
_ROUTES: dict = {}

SURVEY_ARC = [
    ["Professor Lattice: Ah - a pilot! We're the Kestrel Survey Team, Survey Corps, Sector Nine.",
     "Professor Lattice: We chart every world we land on. Here - have this one's survey. Free of charge, first time."],
    ["Professor Lattice: You again! Splendid. Tik-Theodolite has been calibrating all morning.",
     "Tik-Theodolite: *whirr* CALIBRATION 99.8%. THE OTHER 0.2% IS VIBES."],
    ["Ilu-Ve: *glows* We keep finding the same glyphs on every world. Fourth-current glyphs. Architect glyphs.",
     "Professor Lattice: They line up, you know. World to world. As if someone drew a road across the sector."],
    ["Basalt: Hrrm. ...The road points somewhere. Hrrm.",
     "Professor Lattice: Away from the Forge, oddly. Out to the rim - to something the oldest charts only "
     "call 'the Bell'."],
    ["Professor Lattice: We've finished the chart, pilot. Every glyph, every world. It's yours.",
     "Professor Lattice: Go and see where the road ends. Someone should - and you're the one with the ship."],
]
PILGRIM_LINES = [
    "The Lanternkeeper: Walk with us a while, small light. The ember is warm tonight.",
    "Cinder: *crackle* I carry the spark. They carry the songs. It's a good arrangement.",
    "Wick: Every world we cross, the ember burns a little brighter. Or we're walking closer to something.",
    "Hush: ...",
    "The Lanternkeeper: The star we came from is gone. Its light is not. Remember that, when it's dark.",
]


def _stable(text: str) -> int:
    return sum((i + 1) * ord(c) for i, c in enumerate(text))


def route(game, key: str) -> list[str]:
    """The worlds a group visits, in order (home world included, so you meet them early)."""
    cache_key = (game.universe.seed, key)
    if cache_key in _ROUTES:
        return _ROUTES[cache_key]
    worlds = []
    for r in range(0, 3):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                for b in game.universe.sector(dx, dy).bodies:
                    if b.kind == "planet" and b.biome.landable and b.biome_id in M.MATERIALS:
                        worlds.append(b.id)
    worlds = sorted(set(worlds))
    rng = random.Random(game.universe.seed * 7 + _stable(key))
    picks = rng.sample([w for w in worlds if w != "0,0:0"], min(5, max(0, len(worlds) - 1)))
    slot = _stable(key) % (len(picks) + 1)
    picks.insert(slot, "0,0:0")
    _ROUTES[cache_key] = picks
    return picks


def day(game) -> int:
    return int(game.state.world_time // DAY)


def where(game, group) -> str:
    r = route(game, group["key"])
    return r[(day(game) // SP.GROUP_DAYS) % len(r)] if r else ""


def on_world(game, planet_id: str) -> list[dict]:
    return [g for g in SP.GROUPS if where(game, g) == planet_id]


def band_for(planet) -> dict | None:
    """A family of natives that wanders this world (no route; they live here)."""
    natives = SP.natives_of(planet.biome.id)
    if not natives:
        return None
    rng = random.Random(planet.seed * 3 + 11)
    look = rng.choice(natives)
    n = rng.choice([2, 3, 3])
    sp = SP.SPECIES[look]
    names = rng.sample(sp["names"], n)
    return dict(key=f"band:{planet.id}", name=f"{sp['label']} wanderers", icon=None, color=(170, 210, 200),
                members=[(look, nm) for nm in names], speed=42, stops=True, local=True)


def mem(game, key: str) -> dict:
    return game.state.groups.setdefault(key, {"met": 0, "planets": [], "last_day": -1})


# ---------------------------------------------------------------- talking to a group
def talk(game, scene, group, member_look, member_name) -> None:
    key = group["key"]
    if group.get("local"):
        sp = SP.SPECIES[member_look]
        line = sp["chatter"][(scene.planet.seed + mem(game, key)["met"]) % len(sp["chatter"])]
        mem(game, key)["met"] += 1
        game.dialogue.say([(speaker(member_look, member_name), line)])
        return
    m = mem(game, key)
    first_today = m["last_day"] != day(game)
    if first_today:
        m["met"] += 1
        m["last_day"] = day(game)
        game.state.bump("groups_met")
    {"survey": _survey, "caravan": _caravan, "pilgrims": _pilgrims, "gang": _gang}[key](game, scene, group, m,
                                                                                    first_today)


def speaker(look, name) -> str:
    return f"settler:{look}:{name}" if SP.portrait_ok(look) else "survivor"


def _lines(group, texts):
    """'Name: text' lines -> dialogue tuples with the right portrait."""
    by_name = {nm: look for look, nm in group["members"]}
    out = []
    for t in texts:
        name, _, body = t.partition(": ")
        out.append((speaker(by_name.get(name, group["members"][0][0]), name), body))
    return out


def _survey(game, scene, group, m, first_today) -> None:
    pid = scene.planet.id
    lines = SURVEY_ARC[min(m["met"], len(SURVEY_ARC)) - 1] if first_today else \
        ["Professor Lattice: Still here? We'll be packing up the tripod soon. Mind the legs."]
    game.dialogue.say(_lines(group, lines))
    from . import corps_career
    if first_today and m["met"] == 1:
        corps_career.earn(game, 5)                    # first contact with the Corps
        game.toasts.add("Survey Corps contact made - press [C] in space to hail them", (255, 190, 90), 4,
                        icon="scanner")
    if pid not in m["planets"]:
        m["planets"].append(pid)
        pois = getattr(scene.terrain, "pois", []) or []
        for poi in pois:
            game.state.poi_state.setdefault(poi["id"], {})["seen"] = True
        game.toasts.add(f"Survey data: {len(pois)} sites charted on {scene.planet.name}", group["color"], 3.5,
                        icon="scanner")
        game.audio.play("discover", 0.6)
    if m["met"] >= len(SURVEY_ARC) and not m.get("rewarded"):
        m["rewarded"] = True
        from .items import roll_mod
        mod = roll_mod(random.Random(game.universe.seed + 99), min_rarity=2, luck=0.2)
        game.state.mods.append(mod)
        game.state.earn(400)
        corps_career.earn(game, 30)
        game.banner.show("The Survey Corps chart", f"{mod['name']}  ·  +400 cr", 3.5)
    game.save()


def _offers(game, scene) -> list:
    rng = random.Random(game.universe.seed + day(game) * 13)
    local = scene.planet.biome.id
    mats = rng.sample([b for b in M.MATERIALS if b != local], 3)
    return [(b, 3, rng.choice([90, 105, 120])) for b in mats]


def _caravan(game, scene, group, m, first_today) -> None:
    from ..scenes.choice import ChoiceScene
    st = game.state

    def buy(b, n, price):
        def go():
            if st.credits < price:
                game.audio.play("deny")
                game.toasts.add("Not enough credits", (255, 120, 120), 2)
                return None
            st.credits -= price
            M.give(game, b, n)
            game.audio.play("pickup", 0.6)
            return None
        return go

    opts = [(f"Buy {n} {M.name(b)}  -  {price} cr", buy(b, n, price), f"you have {st.materials.get(b, 0)}")
            for b, n, price in _offers(game, scene)]
    if st.ore >= 5:
        def sell():
            st.ore -= 5
            st.earn(70)
            game.toasts.add("+70 cr", (255, 230, 120), 2, icon="coin")
        opts.append(("Sell 5 ore  -  70 cr", sell, f"you have {st.ore} ore"))
    opts.append(("Just looking", None))
    hello = "Ahoy, pilot! Grumblebeast's loaded heavy today. Fresh from other worlds - have a look." if first_today \
        else "Back for more? The beast approves. Probably. Hard to tell with the beast."
    game.scenes.push(ChoiceScene(game, speaker(6, "Quartermaster Bloop"), group["name"], hello, opts,
                                 can_cancel=True))


def _pilgrims(game, scene, group, m, first_today) -> None:
    st = game.state
    line = PILGRIM_LINES[(m["met"] - 1) % len(PILGRIM_LINES)]
    game.dialogue.say(_lines(group, [line]))
    if first_today:
        st.pilot_hp = st.max_pilot_hp
        if hasattr(scene, "pilot"):
            scene.pilot.jet = st.jetpack_capacity
        game.toasts.add("The Ember Road's blessing: fully restored", group["color"], 3, icon="star")
        game.audio.play("relic", 0.5)


def _gang(game, scene, group, m, first_today) -> None:
    from ..scenes.choice import ChoiceScene
    from .items import roll_mod
    st = game.state

    def sell_all():
        n = st.ore
        st.ore = 0
        st.earn(n * 14)
        game.toasts.add(f"Sold {n} ore  ·  +{n * 14} cr", (255, 230, 120), 2.5, icon="coin")

    def salvage():
        if st.credits < 280:
            game.audio.play("deny")
            game.toasts.add("Not enough credits", (255, 120, 120), 2)
            return
        st.credits -= 280
        mod = roll_mod(random.Random(game.universe.seed + day(game) * 7 + st.stats.get("groups_met", 0)), luck=0.15)
        st.mods.append(mod)
        game.toasts.add(f"Salvage: {mod['name']}", (200, 160, 255), 3, icon="gear")

    opts = []
    if st.ore > 0:
        opts.append((f"Sell all ore ({st.ore})  -  {st.ore * 14} cr", sell_all, "better than the station pays"))
    opts.append(("Buy a crate of salvage  -  280 cr", salvage, "a random ship mod"))
    opts.append(("Leave them to it", None))
    hello = "*BZZT* ORGANIC-SHAPED ROBOT DETECTED. WE BUY ORE. WE SELL... THINGS. ALL THINGS ARE FINE." \
        if first_today else "*bzzt* RETURNING CUSTOMER. LOYALTY PROGRAMME: WE REMEMBER YOU. THAT IS THE PROGRAMME."
    game.scenes.push(ChoiceScene(game, speaker(23, "Big Static"), group["name"], hello, opts, can_cancel=True))
