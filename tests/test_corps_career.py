"""Corps rank, perks and contracts; the Kestrel lander."""
import pygame
from conftest import run
from test_expansion import _invulnerable, _land_on, _space

from stellar_forge.core.game_state import GameState
from stellar_forge.systems import corps as C
from stellar_forge.systems import corps_career as K
from stellar_forge.systems import groups as G
from stellar_forge.systems import species as SP
from stellar_forge.world.universe import Universe


def test_rank_rises_with_lifetime_merit_and_unlocks_perks(game):
    st = game.state
    assert K.rank_name(st) == "Contact"
    assert C.price(st, "fuel") == (12, 160)
    K.earn(game, 45)
    assert K.rank_name(st) == "Associate" and C.price(st, "fuel") == (10, 128)    # 20% off
    st.corps_merit = 0                                                           # spending doesn't demote
    assert K.rank(st) == 1
    K.earn(game, 500)
    assert K.rank_name(st) == "Commander" and C.free_refuel(game)


def test_strike_wing_needs_rank(game):
    sp = _space(game)
    st = game.state
    st.corps_merit_total = 1
    sp.corps.hail()
    labels = [o[0] for o in game.scenes.top.menu.items]
    assert not any("Strike" in t for t in labels) and any("contracts" in t for t in labels)
    game.scenes.pop()
    K.earn(game, 300)
    sp.corps.hail_cd = 0
    sp.corps.hail()
    assert any("Strike" in o[0] for o in game.scenes.top.menu.items)
    game.scenes.pop()
    sp.corps.call("strike")
    assert sum(1 for s in sp.corps.ships if s.mode == "escort") == 4


def test_bounty_contract_pays_on_kills(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    job = next(j for j in K.offers(game) if j["kind"] == "bounty")
    K.accept(game, job)
    cr = game.state.credits
    for _ in range(job["need"]):
        game.events.emit("enemy_destroyed", quest=False, elite=False)
    assert game.state.corps_job is None and game.state.credits == cr + job["cr"]
    assert game.state.corps_merit_total == job["merit"] and game.state.stats["corps_jobs"] == 1
    assert sp is game.space


def test_chart_contract_counts_new_worlds(game):
    job = next(j for j in K.offers(game) if j["kind"] == "chart")
    K.accept(game, job)
    K.progress(game, "chart", planet_id="0,0:0")              # home doesn't count
    for pid in ("1,0:1", "1,0:2", "1,0:2", "0,1:1"):
        K.progress(game, "chart", planet_id=pid)
    assert game.state.corps_job is None and game.state.stats["corps_jobs"] == 1


def test_captain_hunt(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    job = next(j for j in K.offers(game) if j["kind"] == "captain")
    K.accept(game, job)
    assert "Captain" in K.objective_line(game)
    sx, sy = job["sector"]
    from stellar_forge import config
    centre = pygame.Vector2((sx + 0.5) * config.SECTOR_SIZE, (sy + 0.5) * config.SECTOR_SIZE)
    sp.place_ship(centre)
    assert list(Universe.sector_coords(sp.ship.pos)) == [sx, sy]
    sp.enemies.clear()
    run(game, 0.2)
    cap = sp.corps.captain()
    assert cap is not None and cap.name == f"Captain {job['name']}"
    mods = len(game.state.mods)
    cap.hurt(99999)
    sp._enemy_killed(cap)
    assert game.state.corps_job is None and len(game.state.mods) == mods + 1


def test_kestrel_lander_has_the_contracts_board(game):
    grp = next(g for g in SP.GROUPS if g["key"] == "survey")
    for d in range(200):
        game.state.world_time = d * G.DAY + 30
        if G.where(game, grp) == "0,0:0":
            break
    s = _land_on(game, game.universe.find_body("0,0:0"))
    assert s.pois.lander_x is not None
    for w in s.pois.walkers:                       # keep the team away so the lander is the nearest thing
        for m in w.members:
            m.x += 3000
    s.pilot.x = s.pois.lander_x
    assert "contracts" in s.pois.prompt()[0]
    s.pois.interact()
    assert game.scenes.top.title == "Corps contracts"


def test_meeting_the_survey_team_is_first_contact(game):
    grp = next(g for g in SP.GROUPS if g["key"] == "survey")
    for d in range(200):
        game.state.world_time = d * G.DAY + 30
        if G.where(game, grp) == "0,0:0":
            break
    s = _land_on(game, game.universe.find_body("0,0:0"))
    assert not C.has_contact(game.state)
    G.talk(game, s, grp, 7, "Professor Lattice")
    assert C.has_contact(game.state) and game.state.corps_merit == 5


def test_career_round_trips(tmp_path):
    st = GameState(seed=1)
    st.corps_merit_total = 130
    st.corps_job = {"kind": "bounty", "desc": "x", "need": 4, "have": 2, "merit": 1, "cr": 1}
    st.save(tmp_path / "s.json")
    back = GameState.load(tmp_path / "s.json")
    assert back.corps_merit_total == 130 and back.corps_job["have"] == 2 and K.rank_name(back) == "Field Agent"
