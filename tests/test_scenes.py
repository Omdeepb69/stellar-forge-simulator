"""Headless smoke tests that drive every scene through real frames."""
import pygame
from conftest import key, run

from stellar_forge.scenes.boss import BossScene
from stellar_forge.scenes.space import SpaceScene
from stellar_forge.scenes.station import StationScene
from stellar_forge.scenes.stronghold import StrongholdScene
from stellar_forge.scenes.surface import SurfaceScene


def test_starts_on_aster_next_to_rocket(game):
    s = game.scenes.top
    assert isinstance(s, SurfaceScene)
    assert s.planet.id == "0,0:0"
    assert abs(s.pilot.x) < 400


def test_walk_board_and_launch(game, keys):
    s = game.scenes.top
    keys.held.add(pygame.K_LEFT)
    run(game, 0.5)
    keys.held.clear()
    run(game, 1.0, [key(pygame.K_e)])
    assert isinstance(game.scenes.top, SpaceScene)
    assert game.quests.cid == "signal"
    assert game.space.ship.pos.distance_to(s.planet.pos(game.state.world_time)) < 1500


def test_thrust_uses_fuel_and_moves(game, keys):
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    fuel = game.state.fuel
    p0 = pygame.Vector2(game.space.ship.pos)
    keys.held.add(pygame.K_w)
    run(game, 1.5)
    keys.held.clear()
    assert game.state.fuel < fuel
    assert game.space.ship.pos.distance_to(p0) > 100


def test_dock_advances_story_and_opens_station(game):
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    sp = game.space
    st = game.universe.find_body("0,0:st")
    t = game.state.world_time
    sp.place_ship(st.pos(t) + pygame.Vector2(120, 0), st.vel(t))
    run(game, 0.1)
    run(game, 0.3, [key(pygame.K_e)])
    assert isinstance(game.scenes.top, StationScene)
    assert game.quests.cid == "raiders"
    run(game, 0.3, [key(pygame.K_ESCAPE)])
    assert isinstance(game.scenes.top, SpaceScene)


def test_land_on_relic_world_and_clear_stronghold(game):
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    (site, biome), *_ = game.universe.relic_sites.items()
    planet = [p for p in game.universe.sector(*site).planets if p.biome_id == biome and p.stronghold][0]
    t = game.state.world_time
    game.space.place_ship(planet.pos(t) + pygame.Vector2(0, -(planet.radius + 120)), planet.vel(t))
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_l)])
    surf = game.scenes.top
    assert isinstance(surf, SurfaceScene) and surf.planet is planet
    surf.pilot.x = surf.terrain.stronghold_x
    surf.pilot.y = surf.terrain.height(surf.pilot.x)
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    sh = game.scenes.top
    assert isinstance(sh, StrongholdScene)
    # wrong door resets progress
    wrong = next(d for d in "tlrb" if d != sh.sequence[0])
    sh._through_door(wrong)
    assert sh.step == 0
    for d in sh.sequence:
        sh._through_door(d)
    assert sh.complete
    sh.pos = pygame.Vector2(sh.room_rect.center)
    run(game, 0.3)
    assert biome in game.state.relics
    assert planet.id in game.state.looted_strongholds


def test_surface_walk_far_is_stable(game, keys):
    surf = game.scenes.top
    keys.held.add(pygame.K_RIGHT)
    surf.pilot.x = 50_000   # far along the infinite surface
    surf.pilot.y = surf.terrain.height(50_000) - 5
    run(game, 2.0)
    keys.held.clear()
    assert surf.pilot.x > 50_000
    assert abs(surf.pilot.y - surf.terrain.height(surf.pilot.x)) < 400


def test_boss_scene_runs_and_victory_returns_to_space(game, monkeypatch):
    from stellar_forge.surface.player import Pilot
    monkeypatch.setattr(Pilot, "hurt", lambda self, *a, **k: False)
    game.state.relics = ["desert", "ice", "forest"]
    game.state.chapter = 5
    game.scenes.switch(BossScene(game), fade=False)
    b = game.scenes.top
    run(game, 1.0)
    b.minions.clear()
    run(game, 2.0)
    assert b.phase == 2
    b.boss_hp = 0
    run(game, 2.0)
    assert b.phase == 3
    b.boss_hp = 0
    run(game, 8.5, [key(pygame.K_RETURN)])
    run(game, 1.0)
    assert type(game.scenes.top).__name__ == "ActTwoScene"
    run(game, 2.0)
    run(game, 0.2, [key(pygame.K_RETURN)])   # skip to the title card
    run(game, 0.2, [key(pygame.K_RETURN)])   # and past it
    run(game, 1.0)
    assert game.state.boss_defeated
    assert isinstance(game.scenes.top, SpaceScene)
    assert game.quests.cid == "shards"   # Act II begins


def test_save_and_continue(game):
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    game.state.credits = 777
    game.save()
    assert game.continue_game()
    run(game, 0.6)
    assert game.state.credits == 777
    assert isinstance(game.scenes.top, SpaceScene)


def test_death_in_space_goes_to_game_over(game):
    from stellar_forge.scenes.menus import GameOverScene
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    game.state.hull = 0
    run(game, 2.5)
    assert isinstance(game.scenes.top, GameOverScene)


def test_pause_map_overlays(game):
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.6)
    run(game, 0.1, [key(pygame.K_m)])
    assert type(game.scenes.top).__name__ == "MapScene"
    run(game, 0.1, [key(pygame.K_m)])
    run(game, 0.1, [key(pygame.K_ESCAPE)])
    assert type(game.scenes.top).__name__ == "PauseScene"
    t = game.state.world_time
    run(game, 0.5)
    assert game.state.world_time == t   # paused means paused
