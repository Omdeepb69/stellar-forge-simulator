"""Points of interest on planet surfaces, and the settlers' quests.

Every landable world gets a handful of places worth walking to, placed
deterministically from the planet seed:

* camp   - settlers with a job for you (hunt, fetch a lost crate, bring materials)
* pod    - a crashed escape pod to salvage
* ruin   - an Architect ruin: read the tablet, light the pillars in its order
* vein   - a rich deposit of the world's material (several hits to mine out)

Progress lives in ``GameState.poi_state`` (poi id -> dict), so it survives
saves and leaving the planet.
"""
from __future__ import annotations

import random

from . import materials as M
from . import species as SP

KINDS = {"camp": ("Settler camp", "camp", (120, 230, 200)),
         "pod": ("Escape pod", "pod", (200, 220, 255)),
         "ruin": ("Architect ruin", "ruin", (120, 220, 255)),
         "vein": ("Material vein", None, (255, 220, 120))}

# padding (flat ground) each kind needs
PAD = {"camp": 300.0, "pod": 170.0, "ruin": 460.0, "vein": 130.0, "crate": 90.0}
PILLAR_DX = (-390, -210, 210, 390)
VEIN_HITS = 3
CAMP_JOBS = 3          # jobs each camp offers in a row before it is "done"



def generate(terrain, planet, rng, taken: list) -> list[dict]:
    """Place this planet's POIs. ``taken`` holds x positions already used."""
    def free_spot(lo, hi, gap=1500):
        for _ in range(30):
            x = rng.choice([-1, 1]) * rng.uniform(lo, hi)
            if all(abs(x - t) > gap for t in taken):
                taken.append(x)
                return round(x)
        return None

    kinds = []
    if planet.id == "0,0:0" or rng.random() < 0.6:
        kinds.append("camp")
    kinds += ["pod"] * rng.choice([1, 1, 2])
    if rng.random() < 0.75:
        kinds.append("ruin")
    kinds += ["vein", "vein"]
    out = []
    for k, kind in enumerate(kinds):
        lo, hi = (1500, 3200) if (kind == "camp" and planet.id == "0,0:0") else (1300, 9500)
        x = free_spot(lo, hi)
        if x is None:
            continue
        poi = {"id": f"{planet.id}:poi:{k}", "kind": kind, "x": x, "seed": rng.randrange(1 << 30),
               "biome": planet.biome.id}
        if kind == "ruin":
            glyphs = list(range(4))
            rng.shuffle(glyphs)
            poi["glyphs"] = glyphs                                   # glyph shown on each pillar
            poi["order"] = rng.sample(range(4), 3)                   # pillar indices to light, in order
        if kind == "camp":
            poi["crate_x"] = free_spot(1800, 6000, gap=900)
            poi["settler"] = rng.randrange(4)
        out.append(poi)
    return out


def state(game, poi_id: str) -> dict:
    return game.state.poi_state.setdefault(poi_id, {})


def done(game, poi_id: str) -> bool:
    return bool(game.state.poi_state.get(poi_id, {}).get("done"))


# ---------------------------------------------------------------- settler quests
def make_quest(planet, poi, round_: int = 0, used: tuple = ()) -> dict:
    """Job number ``round_`` at this camp. ``used`` lists job kinds already given
    (the lost crate only goes missing once)."""
    name = SP.name_for(SP.giver_look(poi), poi["seed"])             # same settler every round
    rng = random.Random(poi["seed"] + 101 * round_)
    kinds = ["hunt", "fetch", "gather"]
    if poi.get("crate_x") is None or "fetch" in used:
        kinds.remove("fetch")
    if used and used[-1] in kinds and len(kinds) > 1:
        kinds.remove(used[-1])                                      # never the same job twice running
    kind = "hunt" if (planet.id == "0,0:0" and round_ == 0) else rng.choice(kinds)
    others = [b for b in M.MATERIALS if b != planet.biome.id]
    q = {"kind": kind, "have": 0, "stage": "new", "name": name, "round": round_, "species": SP.giver_look(poi)}
    if kind == "hunt":
        q["need"] = rng.choice([4, 5, 6]) + 2 * round_
    elif kind == "fetch":
        q["need"] = 1
    else:
        q["need"] = rng.choice([3, 4]) + 2 * round_
        # early worlds ask for something you can find in the home system
        q["mat"] = rng.choice(["forest", "desert", "barren", "crystal"] if planet.sector == (0, 0) else others)
        if q["mat"] == planet.biome.id:
            q["mat"] = others[0]
    return q


def quest(game, planet, poi) -> dict:
    st = state(game, poi["id"])
    if "quest" not in st:
        st["quest"] = make_quest(planet, poi)
    q = st["quest"]
    if "species" not in q:                       # saves from before the frontier peoples: rename to fit
        q["species"] = SP.giver_look(poi)
        q["name"] = SP.name_for(q["species"], poi["seed"])
    return q


def jobs_done(game, poi_id: str) -> int:
    return len(game.state.poi_state.get(poi_id, {}).get("history", []))


def quest_text(q: dict) -> str:
    if q["kind"] == "hunt":
        return f"defeat creatures {q['have']}/{q['need']}"
    if q["kind"] == "fetch":
        return "bring back the supply crate" if not q["have"] else "return the crate to camp"
    return f"bring {q['need']} {M.name(q['mat'])}"


def intro_lines(planet, q) -> list[str]:
    b = planet.biome.name.lower()
    if q.get("round", 0) > 0:
        return [_FOLLOW_UP[q["kind"]][0].format(b=b, mat=M.name(q["mat"]) if "mat" in q else ""),
                _FOLLOW_UP[q["kind"]][1].format(n=q["need"], mat=M.name(q["mat"]) if "mat" in q else "")]
    if q["kind"] == "hunt":
        return ["The creatures here keep tearing into our hydroponics.",
                f"Thin them out for us - {q['need']} should do - and I'll make it worth your while."]
    if q["kind"] == "fetch":
        return ["Our last supply drop came down off-course. The beacon's still pinging out there.",
                "Bring the crate back and you can have a share of what's inside."]
    return [f"Our water purifier is cracked, and nothing on this {b} rock will patch it.",
            f"{M.name(q['mat'])} would. Bring me {q['need']} and I'll pay you in what we dig up here."]


_FOLLOW_UP = {
    "hunt": ("Word got around that you're good with that sword. The nests are back, and bigger.",
             "Clear out {n} of them and the camp can sleep again."),
    "fetch": ("A second drop went astray in the last storm. Same beacon, different crater.",
              "Bring it home and we'll split it with you."),
    "gather": ("Now that we're not starving, we can actually build. This {b} rock won't do it alone.",
               "We need {n} {mat} for the new shelter frame."),
}


def talk(game, planet, poi, scene) -> None:
    """Talk to the settler at a camp: offer, progress, or hand in."""
    q = quest(game, planet, poi)
    name = q["name"]
    layer = getattr(scene, "pois", None)
    spk = layer.speaker(poi, name) if layer is not None and hasattr(layer, "speaker") else None

    def say(lines):
        if spk:   # the dialogue box shows the settler's face and name, so drop the "Name: " prefix
            lines = [(spk, t.split(": ", 1)[1] if t.startswith(name + ": ") else t) for _s, t in lines]
        game.dialogue.say(lines)
    if q["stage"] == "done":
        say([("survivor", f"{name}: Safe skies, Voyager. The camp's doing fine thanks to you.")])
        return
    if q["stage"] == "new":
        q["stage"] = "active"
        greet = [SP.SPECIES[q["species"]]["greet"]] if q.get("round", 0) == 0 else []
        say([("survivor", f"{name}: " + ln) for ln in greet + intro_lines(planet, q)])
        game.toasts.add(f"Settler job: {quest_text(q)}", (120, 230, 200), 4, icon="camp")
        return
    ready = False
    if q["kind"] == "gather":
        need = {q["mat"]: q["need"]}
        ready = M.take(game.state, need)
    else:
        ready = q["have"] >= q["need"]
    if not ready:
        say([("survivor", f"{name}: Still need you to {quest_text(q)}.")])
        return
    st = state(game, poi["id"])
    history = st.setdefault("history", [])
    history.append(q["kind"])
    reward(game, planet, poi, scene, len(history) - 1)
    if len(history) >= CAMP_JOBS:
        q["stage"] = "done"
        st["done"] = True
        say([("survivor", f"{name}: You've done more for this camp than anyone. Take this - and come back any time.")])
        game.save()
        return
    st["quest"] = make_quest(planet, poi, len(history), tuple(history))  # next job, offered on the next talk
    st["quest"]["name"] = name
    say([("survivor", f"{name}: You did it! Here - take this."),
         ("survivor", f"{name}: ...if you've got a moment later, there's something else.")])
    game.save()


def reward(game, planet, poi, scene, round_: int = 0) -> None:
    st = game.state
    rng = random.Random(poi["seed"] + 1 + 31 * round_)
    cr = int((140 * scene.danger + 80) * (1 + 0.5 * round_))
    st.earn(cr)
    local = planet.biome.id if planet.biome.id in M.MATERIALS else rng.choice(list(M.MATERIALS))
    M.give(game, local, 5 + 2 * round_)
    other = rng.choice([b for b in M.MATERIALS if b != local])
    M.give(game, other, 2 + round_)
    if round_ == CAMP_JOBS - 1:                                      # the last job pays a mod too
        from .items import roll_mod
        mod = roll_mod(rng, min_rarity=1, luck=0.1)
        st.mods.append(mod)
        game.toasts.add(mod["name"], (200, 160, 255), 3, icon="star")
    st.add_rep("haven", 6)
    st.bump("settlers")
    game.toasts.add(f"+{cr} cr", (255, 230, 120), 2.5, icon="coin")
    game.events.emit("settler_helped")
    game.audio.play("relic", 0.7)


def on_kill(game, planet) -> None:
    """Hunt quests count creatures killed on that quest's own world."""
    for poi in getattr(planet, "_pois", []) or []:
        if poi["kind"] != "camp":
            continue
        q = game.state.poi_state.get(poi["id"], {}).get("quest")
        if q and q["stage"] == "active" and q["kind"] == "hunt" and q["have"] < q["need"]:
            q["have"] += 1
            if q["have"] >= q["need"]:
                game.toasts.add("Settler job done - return to the camp", (120, 230, 200), 3, icon="camp")


def objective_line(game) -> str | None:
    """The settler job for the world you're standing on, for the HUD."""
    scene = game.scenes.top
    planet = getattr(scene, "planet", None)
    if planet is None:
        return None
    for poi in getattr(planet, "_pois", []) or []:
        q = game.state.poi_state.get(poi["id"], {}).get("quest")
        if poi["kind"] == "camp" and q and q["stage"] == "active":
            ready = q["have"] >= q["need"] if q["kind"] != "gather" else \
                game.state.materials.get(q["mat"], 0) >= q["need"]
            n = f" ({q.get('round', 0) + 1}/{CAMP_JOBS})"
            return f"{SP.short(q['name'])}{n}: " + ("return to camp" if ready else quest_text(q))
    return None
