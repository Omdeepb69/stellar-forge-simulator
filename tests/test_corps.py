"""The Survey Corps in space: battles, Merit and the hailing channel."""
import pygame
from conftest import key, run
from test_expansion import _invulnerable, _space

from stellar_forge.core.game_state import GameState
from stellar_forge.entities.allies import CorpsShip
from stellar_forge.systems import corps as C


def test_corps_fighters_shoot_raiders(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    sp.enemies.clear()
    from stellar_forge.entities.enemies import Raider
    pos = sp.ship.pos + pygame.Vector2(3000, 0)
    r = Raider(game, pos, 1.0)
    r.aggro = True
    # Pin all random attrs so the test is deterministic across Python versions / RNG seeds.
    # The Raider orbits the CorpsShip; zero accel keeps it nearly stationary so ally
    # bullets reliably connect within the 4-second window.
    r.vel = pygame.Vector2(0, 0)
    r.accel = 0.0          # can't accelerate away from the fighter
    r.preferred = 350.0    # orbit at exactly the starting separation
    r.orbit_dir = 1
    sp.enemies.append(r)
    s = CorpsShip(game, pos + pygame.Vector2(-350, 0), "fighter", "patrol", 1.0)
    s.fire_timer = 0.0     # skip random warm-up delay so first shot fires immediately
    s.preferred = 350.0    # preferred orbit distance = current separation; fighter stays and fires
    sp.corps.ships.append(s)
    hp = r.hp
    run(game, 4)
    assert r.hp < hp or not r.alive                  # the Corps ship is fighting on its own
    assert sp.corps.target_for(r, sp.ship) is s       # and the raider turns on the nearer Corps ship


def test_joining_a_battle_earns_merit(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    sp.enemies.clear()
    b = sp.corps.start_battle(sp.ship.pos + pygame.Vector2(900, 0))
    st = game.state
    assert len(b["raiders"]) >= 3 and len(b["allies"]) >= 2
    for r in list(b["raiders"]):                      # the player downs every raider
        r.hurt(9999)
        sp._enemy_killed(r)
    sp.enemies = [e for e in sp.enemies if e.alive]
    run(game, 0.2)
    assert sp.corps.battle is None
    assert st.corps_merit >= 6 * 3 + 20 and st.stats["corps_battles"] == 1
    assert C.has_contact(st)


def test_hail_needs_contact(game):
    sp = _space(game)
    run(game, 0.1, [key(pygame.K_c)])
    assert game.scenes.top is not sp                  # emergency channel is always reachable
    assert "Emergency Channel" in game.scenes.top.title
    game.scenes.pop()
    game.state.groups["survey"] = {"met": 1, "planets": [], "last_day": 0}
    run(game, 0.1, [key(pygame.K_c)])
    assert game.scenes.top is not sp                  # full Corps channel opens once contact is made
    assert game.scenes.top.title == "Survey Corps channel"
    game.scenes.pop()


def test_tender_refuels_and_tows(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    sp.enemies.clear()
    st = game.state
    st.corps_merit = 100
    st.fuel = 5
    sp.corps._buy("fuel", "merit")()
    assert st.corps_merit == 100 - C.SERVICES["fuel"][1]
    tender = next(s for s in sp.corps.ships if s.role == "tender")
    for _ in range(40):
        run(game, 0.5)
        if tender.mode == "depart":
            break
    assert st.fuel == st.max_fuel
    # a tow takes you to the nearest station
    sp.corps.hail_cd = 0
    sp.place_ship(sp.ship.pos + pygame.Vector2(20000, 0))
    sp.corps.call("tow")
    tender = next(s for s in sp.corps.ships if s.service == "tow")
    tender.pos = sp.ship.pos + pygame.Vector2(100, 0)
    run(game, 0.1)
    stn = sp.corps._nearest_station()
    assert sp.ship.pos.distance_to(stn.pos(sp.t)) < 400


def test_escort_wing_flies_with_you(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    sp.enemies.clear()
    sp.corps.call("escort")
    wing = [s for s in sp.corps.ships if s.mode == "escort"]
    assert len(wing) == 2
    run(game, 8)
    assert all(s.pos.distance_to(sp.ship.pos) < 900 for s in wing)


def test_merit_round_trips(tmp_path):
    st = GameState(seed=2)
    st.corps_merit = 42
    st.save(tmp_path / "s.json")
    assert GameState.load(tmp_path / "s.json").corps_merit == 42


def test_emergency_sos_and_false_alarm_penalties(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    st = game.state
    st.groups["survey"] = {"met": 1, "planets": [], "last_day": 0}
    sp.enemies.clear()

    # 1. Real emergency (3+ attackers): dispatches fighters for free, no penalty
    from stellar_forge.entities.enemies import Raider
    for k in range(3):
        sp.enemies.append(Raider(game, sp.ship.pos + pygame.Vector2(400 + k * 80, 0), 1.0))
    st.credits = 500
    sp.corps.emergency_sos()
    assert len([s for s in sp.corps.ships if s.mode == "escort"]) == 2
    assert st.corps_fine == 0 and not st.corps_banned

    # 2. Real emergency (low fuel): also dispatches a free fuel tender
    sp.enemies.clear()
    sp.corps.ships.clear()
    st.fuel = 10
    sp.corps.emergency_sos()
    assert any(s.role == "tender" and s.service == "fuel" for s in sp.corps.ships)
    assert st.corps_fine == 0

    # 3. False alarm with enough credits -> pay now
    st.fuel = st.max_fuel
    st.hull = st.max_hull
    st.credits = 500
    sp.corps.emergency_sos()
    assert game.scenes.top is not sp
    sp.corps._pay_penalty_now()
    game.scenes.pop()
    assert st.credits == 500 - C.PENALTY_FEE
    assert st.corps_fine == 0 and not st.corps_banned

    # 4. Refuse 3 times -> banned, then buy licence at station
    for strike in range(1, C.MAX_STRIKES):
        sp.corps._refuse_penalty()
        assert st.corps_fine == C.PENALTY_FEE
        assert st.corps_strikes == strike
        assert not st.corps_banned
        # While fine is unpaid, hailing shows the penalty screen instead of normal services
        sp.corps.hail()
        assert "Unpaid Penalty" in game.scenes.top.title
        game.scenes.pop()
    # Pay off an unpaid fine once
    st.credits = 500
    sp.corps._settle_fine()
    assert st.corps_fine == 0 and st.credits == 500 - C.PENALTY_FEE
    # 3rd refusal -> banned!
    sp.corps._refuse_penalty()
    assert st.corps_strikes == C.MAX_STRIKES and st.corps_banned is True
    sp.corps.hail()
    assert "Banned" in game.scenes.top.title
    game.scenes.pop()

    # 5. Station lets player buy back their Survey Corps licence
    from stellar_forge.scenes.station import StationScene
    stn = game.universe.find_body("0,0:st")
    scene = StationScene(game, stn)
    labels = [r.label for r in scene.rows()]
    assert "Buy Survey Corps licence" in labels
    st.credits = 2000
    scene._buy_corps_licence()
    assert not st.corps_banned and st.corps_strikes == 0 and st.corps_fine == 0


def test_false_alarm_insufficient_credits_bans_immediately(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    st = game.state
    st.groups["survey"] = {"met": 1, "planets": [], "last_day": 0}
    sp.enemies.clear()
    st.fuel = st.max_fuel
    st.hull = st.max_hull
    st.credits = 10
    sp.corps._pay_penalty_now()
    assert st.corps_banned is True
    assert st.corps_fine == C.PENALTY_FEE
