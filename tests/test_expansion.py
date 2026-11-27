"""Expansion systems: events, derelicts, caves, planet bosses, grapple, outposts,
stations, weapons, autopilot, rebinding, daily runs and the two endings."""
import pygame
import pytest
from conftest import key, run

from stellar_forge.core.game_state import GameState
from stellar_forge.scenes.space import SpaceScene
from stellar_forge.scenes.surface import SurfaceScene


def _space(game):
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    game.dialogue.queue.clear()
    game.state.hints_seen = ["*"] + [h for h in game.state.hints_seen]
    game.settings.show_hints = False
    return game.space


def _invulnerable(monkeypatch):
    from stellar_forge.entities.ship import PlayerShip
    from stellar_forge.surface.player import Pilot
    monkeypatch.setattr(PlayerShip, "damage", lambda self, *a, **k: None)
    monkeypatch.setattr(Pilot, "hurt", lambda self, *a, **k: False)
    monkeypatch.setattr(Pilot, "hazard", lambda self, *a, **k: None)


def _find(game, pred, radius=6):
    u = game.universe
    for r in range(radius + 1):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                for b in u.sector(dx, dy).bodies:
                    if pred(b):
                        return b
    raise AssertionError("nothing matched")


def test_space_events_resolve(game, monkeypatch):
    from stellar_forge.systems import space_events as ev
    _invulnerable(monkeypatch)
    sp = _space(game)
    st = game.state
    st.chapter = 3
    # rescue
    b = sp.director.spawn(ev.Beacon)
    b.trap = False
    cr = st.credits
    b._help()
    assert st.credits > cr and not b.alive
    # trap
    b = sp.director.spawn(ev.Beacon)
    b.trap = True
    n = len(sp.enemies)
    b._help()
    assert len(sp.enemies) == n + 3
    sp.enemies.clear()
    # cargo pod: tow and deliver at Haven
    pod = sp.director.spawn(ev.CargoPod)
    pod._tow()
    run(game, 0.5)
    assert pod.towed and sp.towing is pod
    stn = game.universe.find_body("0,0:st")
    sp.place_ship(stn.pos(st.world_time) + pygame.Vector2(120, 0), stn.vel(st.world_time))
    run(game, 0.1)
    cr = st.credits
    run(game, 0.3, [key(pygame.K_e)])
    assert st.credits > cr and not pod.alive
    run(game, 0.2, [key(pygame.K_ESCAPE)])
    # comets
    sp.director.events.clear()
    shower = sp.director.spawn(ev.CometShower)
    shower.timer = 0
    run(game, 0.2)
    assert sp.comets
    c = sp.comets[0]
    sp._comet_destroyed(c)
    assert any(p.kind == "fuel" for p in sp.pickups)
    # solar flare runs its course
    sp.director.events.clear()
    sp.place_ship(sp.system.star.pos(st.world_time) + pygame.Vector2(5000, 0))
    flare = sp.director.spawn(ev.SolarFlare)
    assert flare is not None
    for _ in range(12):
        run(game, 1.0)
    assert not flare.alive
    # pirates: pay them off
    sp.director.events.clear()
    st.credits = 5000
    pirates = sp.director.spawn(ev.PirateHail)
    run(game, 0.3)
    assert type(game.scenes.top).__name__ == "ChoiceScene"
    run(game, 0.5, [key(pygame.K_RETURN)])        # first option = pay
    assert st.credits == 5000 - pirates.demand
    assert not any(getattr(e, "pirate", False) and e.alive for e in sp.enemies)


def test_board_derelict_and_open_vault(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    d = _find(game, lambda b: b.kind == "derelict")
    t = game.state.world_time
    sp.place_ship(d.pos(t) + pygame.Vector2(80, 0))
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    ds = game.scenes.top
    assert type(ds).__name__ == "DerelictScene"
    run(game, 1.0)
    tx, _tid = ds.terminals[0]
    ds.pilot.x, ds.pilot.y = tx, ds.layout.floor(tx)
    run(game, 0.2, [key(pygame.K_e)])
    assert game.state.logs, "terminal should give a crew log"
    mods = len(game.state.mods)
    ds.pilot.x, ds.pilot.y = ds.vault_x, ds.layout.floor(ds.vault_x)
    run(game, 0.2)
    run(game, 0.2, [key(pygame.K_e)])
    assert d.id in game.state.derelicts_looted and len(game.state.mods) == mods + 1
    ds.pilot.x, ds.pilot.y = -400, ds.layout.floor(-400)
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    assert isinstance(game.scenes.top, SpaceScene)


def _land_on(game, planet):
    game.scenes.switch(SurfaceScene(game, planet), fade=False)
    run(game, 0.3)
    game.dialogue.queue.clear()
    return game.scenes.top


def test_cave_geode_and_exit(game, monkeypatch):
    _invulnerable(monkeypatch)
    pl = _find(game, lambda b: b.kind == "planet" and b.cave and b.biome_id != "gas")
    s = _land_on(game, pl)
    s.pilot.x = s.terrain.cave_x
    s.pilot.y = s.terrain.height(s.pilot.x)
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    cave = game.scenes.top
    assert type(cave).__name__ == "CaveScene"
    run(game, 0.5)
    p = cave.pilot
    assert p.y - p.H >= cave.terrain.ceiling(p.x) - 1     # head under the ceiling
    # find and crack a geode
    gid, gx = next(g for c in range(1, 60) for g in cave.terrain.geodes(c))
    p.x, p.y = gx, cave.terrain.height(gx)
    cr = game.state.credits
    run(game, 0.2, [key(pygame.K_e)])
    assert gid in game.state.collected and game.state.credits > cr
    p.x, p.y = 0, cave.terrain.height(0)
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    assert type(game.scenes.top).__name__ == "SurfaceScene"


@pytest.mark.parametrize("biome", ["desert", "ice", "volcanic", "crystal", "ocean"])
def test_planet_boss_fight_and_trophy(game, monkeypatch, biome):
    _invulnerable(monkeypatch)
    pl = _find(game, lambda b: b.kind == "planet" and b.lair and b.biome_id == biome, radius=8)
    s = _land_on(game, pl)
    s.pilot.x = s.terrain.lair_x - 300
    s.pilot.y = s.terrain.height(s.pilot.x)
    run(game, 0.5)
    boss = s.boss
    assert boss is not None and boss.alive
    for _ in range(12):        # exercise every attack pattern
        run(game, 1.0)
        boss.hp = max(boss.hp, boss.max_hp * 0.3)
    assert boss.alive
    s._hit_boss(boss.max_hp * 10, boss.home, s.terrain.height(boss.home))
    run(game, 2.0)
    st = game.state
    assert pl.id in st.lairs_cleared and biome in st.trophies
    assert any(m["rarity"] in ("epic", "legendary") for m in st.mods)


def test_outpost_production_and_warp(game):
    st = game.state
    st.credits = 10_000
    st.chapter = 3
    s = game.scenes.top
    run(game, 0.1, [key(pygame.K_o)])
    o = game.scenes.top
    assert type(o).__name__ == "OutpostScene"
    o._claim()
    o._drill()
    o._pump()
    o._beacon()
    assert st.outposts[s.planet.id]["drill"] == 1 and st.outposts[s.planet.id]["beacon"]
    run(game, 0.1, [key(pygame.K_ESCAPE)])
    st.world_time += 600            # ten minutes away
    ore = st.ore
    run(game, 0.1, [key(pygame.K_o)])
    assert st.ore > ore
    run(game, 0.1, [key(pygame.K_ESCAPE)])
    # a second beacon elsewhere, then warp to it
    other = _find(game, lambda b: b.kind == "planet" and b.landable and b.id != s.planet.id)
    st.outposts[other.id] = {"t": st.world_time, "drill": 0, "pump": 0, "beacon": True, "name": other.name,
                             "biome": other.biome.name}
    from stellar_forge.scenes.outpost import warp_to
    warp_to(game, other.id)
    run(game, 1.0)
    assert isinstance(game.scenes.top, SpaceScene)
    assert game.space.ship.pos.distance_to(other.pos(st.world_time)) < 2000


def test_station_tabs_trade_ships_mods(game):
    sp = _space(game)
    st = game.state
    st.credits = 50_000
    st.chapter = 3
    from stellar_forge.systems.items import roll_mod
    import random
    st.mods = [roll_mod(random.Random(i)) for i in range(4)]
    stn = game.universe.find_body("0,0:st")
    sp.place_ship(stn.pos(st.world_time) + pygame.Vector2(120, 0), stn.vel(st.world_time))
    run(game, 0.1)
    run(game, 0.3, [key(pygame.K_e)])
    ss = game.scenes.top
    assert type(ss).__name__ == "StationScene"
    for _ in range(5):           # draw every tab
        run(game, 0.05, [key(pygame.K_RIGHT)])
    ss.tab = 2
    ss._buy_ship("gunship")
    assert st.ship == "gunship" and "gunship" in st.ships_owned
    hull_before = st.max_hull
    ss._toggle_mod(st.mods[0])
    assert st.mods[0]["id"] in st.equipped
    ss._sell_mod(st.mods[-1])
    assert len(st.mods) == 3
    ss._buy_weapon("missile")
    ss._buy_weapon("boomerang")
    assert "missile" in st.weapons and st.foot_weapon == "boomerang"
    ss.tab = 4
    run(game, 0.05)
    assert st.max_hull >= hull_before * 0.9
    run(game, 0.2, [key(pygame.K_ESCAPE)])


def test_ship_weapon_missiles(game, monkeypatch):
    from stellar_forge.entities.enemies import Raider
    _invulnerable(monkeypatch)
    sp = _space(game)
    st = game.state
    st.weapons = ["blaster", "missile"]
    sp.place_ship(pygame.Vector2(30000, 30000))
    run(game, 0.1)
    keys_held = set()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: type("K", (), {"__getitem__": lambda s, k: k in keys_held})())
    for weapon in ("missile",):
        st.weapon = weapon
        r = Raider(game, sp.ship.pos + sp.ship.forward * 400, 1.0)
        r.max_hp = r.hp = 3
        sp.enemies = [r]
        keys_held.add(pygame.K_SPACE)
        run(game, 0.2)
        keys_held.clear()
        run(game, 2.5)
        assert not r.alive, weapon


def test_autopilot_reaches_waypoint(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    st = game.state
    start = pygame.Vector2(200000, 200000)
    sp.place_ship(start)
    st.waypoint = [start.x + 6000, start.y, "Test point"]
    run(game, 0.1, [key(pygame.K_p)])
    assert sp.autopilot is not None
    for _ in range(40):
        run(game, 1.0)
        if sp.autopilot is None:
            break
    assert sp.ship.pos.distance_to(pygame.Vector2(start.x + 6000, start.y)) < 900


def test_key_rebinding(game):
    s = game.scenes.top
    game.settings.bindings = {"thrust": pygame.K_i}
    game.input.rebuild_bindings()
    from conftest import FakeKeys
    fk = FakeKeys()
    import stellar_forge.core.input as inp
    real = pygame.key.get_pressed
    try:
        pygame.key.get_pressed = lambda: fk
        fk.held = {pygame.K_i}
        assert game.input.pressed()[pygame.K_w]
        fk.held = {pygame.K_w}
        assert not game.input.pressed()[pygame.K_w]
    finally:
        pygame.key.get_pressed = real
    ev = game.input.remap(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, mod=0, unicode="i"))
    assert ev.key == pygame.K_w
    assert inp.ACTION_DEFAULT["thrust"] == pygame.K_w and s is not None


def test_new_save_fields_round_trip(game, tmp_path):
    st = game.state
    st.trophies = ["ice"]
    st.logs = ["c1"]
    st.rep["traders"] = 33
    st.outposts["x"] = {"drill": 2}
    p = tmp_path / "rt.json"
    st.save(p)
    back = GameState.load(p)
    assert back.trophies == ["ice"] and back.logs == ["c1"] and back.rep["traders"] == 33
    assert back.outposts["x"]["drill"] == 2


def test_destroy_ending_and_the_bell(game):
    from stellar_forge.core.game_state import SHARD_BIOMES
    st = game.state
    st.relics = ["desert", "ice", "forest"]
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.5)
    st.chapter = 5
    game.events.emit("boss_defeated")
    for b in SHARD_BIOMES:
        game.events.emit("shard_collected", biome=b)
    game.dialogue.queue.clear()
    danger = game.universe.danger_at(3, 3)
    game.start_ending("destroy")
    run(game, 1.0)
    e = game.scenes.top
    assert type(e).__name__ == "EndingScene" and e.ending == "destroy"
    run(game, 0.2, [key(pygame.K_RETURN)])
    run(game, 0.2, [key(pygame.K_RETURN)])
    run(game, 1.0)
    assert st.ending == "destroy" and game.universe.danger_at(3, 3) < danger
    assert game.universe.find_body("0,0:earth") is None
    from stellar_forge.systems.quests import signal_position
    game.dialogue.queue.clear()
    game.space.place_ship(signal_position(game.universe))
    run(game, 1.0)
    assert type(game.scenes.top).__name__ == "BellScene" and st.signal_found
    run(game, 0.2, [key(pygame.K_RETURN)])
    run(game, 0.2, [key(pygame.K_RETURN)])
    run(game, 1.0)
    assert isinstance(game.scenes.top, SpaceScene)


def test_difficulty_scales_damage(game):
    st = game.state
    st.difficulty = "hard"
    hp = st.pilot_hp
    game.scenes.top.pilot.hurt(10)
    assert hp - st.pilot_hp == pytest.approx(15)


def test_plasma_boomerang_flight(game):
    from stellar_forge.surface.player import Pilot
    st = game.state
    st.weapons.append("boomerang")
    st.foot_weapon = "boomerang"
    p = Pilot(game, 0.0, lambda x: 0.0)
    p.facing = 1
    from collections import defaultdict
    keys_attack = defaultdict(bool, {pygame.K_SPACE: True})
    keys_idle = defaultdict(bool)
    p.update(0.016, keys_attack)
    assert p.boom_active and p.boom_phase == "out"
    assert p.sword_rect() is not None
    start_x = p.boom_x
    for _ in range(15):
        p.update(0.02, keys_idle)
    assert p.boom_x > start_x
    # Simulate until return phase and catch
    saw_return = False
    for _ in range(80):
        p.update(0.02, keys_idle)
        if p.boom_phase == "return":
            saw_return = True
        if not p.boom_active:
            break
    assert saw_return and not p.boom_active
    assert p.sword_rect() is None


def test_space_enemy_spawns_aggroed_in_range(game, monkeypatch):
    sp = _space(game)
    game.state.chapter = 3   # "keys" chapter: free-roam spawning active
    sp.enemies.clear()
    sp.in_nebula = False
    monkeypatch.setattr("random.random", lambda: 0.0)
    sp.spawn_timer = 0.0
    sp._spawn(0.016)
    assert sp.enemies
    for e in sp.enemies:
        assert e.aggro
        assert e.pos.distance_to(sp.ship.pos) <= 2500
