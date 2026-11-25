"""Frontier peoples: natives on every world and the roaming groups."""
from conftest import run
from test_expansion import _land_on

from stellar_forge.core.game_state import GameState
from stellar_forge.systems import groups as G
from stellar_forge.systems import materials as M
from stellar_forge.systems import species as SP


def _home(game):
    return game.universe.find_body("0,0:0")


def _day_with(game, key):
    grp = next(g for g in SP.GROUPS if g["key"] == key)
    for d in range(200):
        game.state.world_time = d * G.DAY + 30
        if G.where(game, grp) == "0,0:0":
            return grp
    raise AssertionError("group never visits home")


def test_every_world_type_has_two_native_peoples():
    for biome in M.MATERIALS:
        assert len(SP.natives_of(biome)) == 2
    assert len(SP.TRAVELLERS) == 8 and SP.LOOKS == 24


def test_groups_follow_a_route_that_includes_home(game):
    for grp in SP.GROUPS:
        r = G.route(game, grp["key"])
        assert "0,0:0" in r and len(r) >= 3
        assert G.route(game, grp["key"]) == r                  # deterministic
    a = G.where(game, SP.GROUPS[0])
    game.state.world_time += G.DAY * SP.GROUP_DAYS
    assert G.where(game, SP.GROUPS[0]) != a or len(set(G.route(game, "survey"))) == 1


def test_survey_team_charts_the_world(game):
    _day_with(game, "survey")
    s = _land_on(game, _home(game))
    w = next(w for w in s.pois.walkers if w.group["key"] == "survey")
    assert len(w.members) == 4
    G.talk(game, s, w.group, w.leader.look, w.leader.name)
    assert all(game.state.poi_state[p["id"]].get("seen") for p in s.terrain.pois)
    assert game.state.groups["survey"]["met"] == 1


def test_caravan_sells_materials(game):
    _day_with(game, "caravan")
    s = _land_on(game, _home(game))
    w = next(w for w in s.pois.walkers if w.group["key"] == "caravan")
    assert any(m.look == "beast" for m in w.members)
    game.state.credits = 1000
    G.talk(game, s, w.group, 6, "Quartermaster Bloop")
    choice = game.scenes.top
    b, n, price = G._offers(game, s)[0]
    choice.menu.items[0][1]()
    assert game.state.materials.get(b) == n and game.state.credits == 1000 - price


def test_pilgrims_heal(game):
    _day_with(game, "pilgrims")
    s = _land_on(game, _home(game))
    w = next(w for w in s.pois.walkers if w.group["key"] == "pilgrims")
    game.state.pilot_hp = 10
    G.talk(game, s, w.group, 5, "The Lanternkeeper")
    assert game.state.pilot_hp == game.state.max_pilot_hp


def test_gang_buys_ore(game):
    _day_with(game, "gang")
    s = _land_on(game, _home(game))
    w = next(w for w in s.pois.walkers if w.group["key"] == "gang")
    game.state.ore = 10
    cr = game.state.credits
    G.talk(game, s, w.group, 23, "Big Static")
    game.scenes.top.menu.items[0][1]()
    assert game.state.ore == 0 and game.state.credits == cr + 140


def test_native_family_roams_and_chats(game):
    s = _land_on(game, _home(game))
    band = next(w for w in s.pois.walkers if w.group.get("local"))
    assert all(SP.SPECIES[m.look].get("home") == "forest" for m in band.members)
    x0 = band.leader.x
    s.pilot.x = x0 + 1500
    s.pilot.y = s.terrain.height(s.pilot.x)
    run(game, 25)
    assert abs(band.leader.x - x0) > 50
    game.dialogue.queue.clear()
    G.talk(game, s, band.group, band.leader.look, band.leader.name)
    assert game.dialogue.queue[0][0].startswith("settler:")


def test_groups_memory_round_trips(tmp_path):
    st = GameState(seed=3)
    st.groups = {"survey": {"met": 2, "planets": ["0,0:0"], "last_day": 4}}
    st.save(tmp_path / "s.json")
    assert GameState.load(tmp_path / "s.json").groups["survey"]["met"] == 2
