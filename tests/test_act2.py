"""Act II (Forge Shards, Wardens, the Forge), achievements, menus and settings."""
import pygame
import pytest
from conftest import key, run

from stellar_forge.core.game_state import SHARD_BIOMES, GameState
from stellar_forge.entities.enemies import Dreadnought
from stellar_forge.scenes.space import SpaceScene
from stellar_forge.scenes.stronghold import StrongholdScene
from stellar_forge.scenes.surface import SurfaceScene
from stellar_forge.world.universe import Universe


@pytest.mark.parametrize("seed", range(1, 31))
def test_shard_sites_are_reachable_and_distinct(seed):
    u = Universe(seed)
    assert sorted(u.shard_sites.values()) == sorted(SHARD_BIOMES)
    assert not set(u.shard_sites) & set(u.relic_sites)
    for (sx, sy), biome in u.shard_sites.items():
        assert 3 <= max(abs(sx), abs(sy)) <= 5
        pl = u.sector(sx, sy).shard_planet
        assert pl is not None and pl.biome_id == biome and pl.stronghold and pl.shard == biome
        assert u.shard_planet(biome) is pl


def test_forge_exists_at_haven(game):
    forge = game.universe.find_body("0,0:forge")
    assert forge is not None and forge.kind == "forge"


def _start_act2(game):
    st = game.state
    st.relics = ["desert", "ice", "forest"]
    game.launch(game.universe.find_body("0,0:0"))
    run(game, 0.5)
    st.boss_defeated = False
    st.chapter = 5
    game.events.emit("boss_defeated")
    run(game, 0.2)
    assert game.quests.cid == "shards"


def test_warden_blocks_shard_world_until_destroyed(game, monkeypatch):
    _start_act2(game)
    st, sp = game.state, game.space
    monkeypatch.setattr(type(sp.ship), "damage", lambda self, *a, **k: None)
    planet = game.universe.shard_planet("crystal")
    t = st.world_time
    sp.place_ship(planet.pos(t) + pygame.Vector2(0, -(planet.radius + 150)), planet.vel(t))
    sp.spawn_timer = 0
    run(game, 0.5)
    wardens = [e for e in sp.enemies if isinstance(e, Dreadnought)]
    assert len(wardens) == 1 and wardens[0].warden == f"{planet.sector[0]},{planet.sector[1]}"
    run(game, 0.2, [key(pygame.K_l)])
    assert isinstance(game.scenes.top, SpaceScene)        # landing refused
    sp.place_ship(planet.pos(st.world_time) + pygame.Vector2(0, -(planet.radius + 150)), planet.vel(st.world_time))
    w = wardens[0]
    w.hurt(w.max_hp + 1)
    sp._enemy_killed(w)
    run(game, 0.2)
    assert w.warden in st.wardens_killed
    run(game, 2.0)                                       # boss-kill slow motion
    game.dialogue.queue.clear()
    sp.place_ship(planet.pos(st.world_time) + pygame.Vector2(0, -(planet.radius + 150)), planet.vel(st.world_time))
    run(game, 0.1)
    run(game, 0.8, [key(pygame.K_l)])
    surf = game.scenes.top
    assert isinstance(surf, SurfaceScene) and surf.planet is planet
    surf.pilot.x = surf.terrain.stronghold_x
    surf.pilot.y = surf.terrain.height(surf.pilot.x)
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    sh = game.scenes.top
    assert isinstance(sh, StrongholdScene) and sh.shard == "crystal" and len(sh.sequence) == 6
    for d in sh.sequence:
        sh._through_door(d)
    sh.pos = pygame.Vector2(sh.room_rect.center)
    run(game, 0.3)
    assert "crystal" in st.shards


def test_all_shards_then_forge_ending_then_ng_plus(game):
    _start_act2(game)
    st = game.state
    for b in SHARD_BIOMES:
        game.events.emit("shard_collected", biome=b)
    assert game.quests.cid == "forge"
    sp = game.space
    forge = game.universe.find_body("0,0:forge")
    sp.place_ship(forge.pos(st.world_time) + pygame.Vector2(80, 0), forge.vel(st.world_time))
    run(game, 0.2)
    game.dialogue.queue.clear()
    run(game, 0.5, [key(pygame.K_e)])
    assert type(game.scenes.top).__name__ == "ChoiceScene"     # the Forge asks: rebuild or destroy?
    run(game, 1.0, [key(pygame.K_RETURN)])
    assert type(game.scenes.top).__name__ == "EndingScene"
    run(game, 3.0)
    run(game, 0.5, [key(pygame.K_RETURN)])   # skip to credits
    run(game, 0.5, [key(pygame.K_RETURN)])   # leave
    run(game, 1.0)
    assert st.forge_restored and game.quests.cid == "free" and st.ending == "rebuild"
    assert isinstance(game.scenes.top, SpaceScene)
    assert game.universe.find_body("0,0:earth") is not None   # Earth-Prime orbits Haven again
    st.upgrades["engine"] = 3
    st.credits = 1234
    game.save()
    old_seed = st.seed
    assert game.new_game_plus()
    run(game, 0.5)
    ns = game.state
    assert ns.ng_plus == 1 and ns.upgrades["engine"] == 3 and ns.credits == 1234
    assert ns.seed != old_seed and ns.chapter == 0 and not ns.relics
    assert game.universe.danger_at(0, 0) > 2.0


def test_achievements_unlock(game):
    st = game.state
    st.kills = 30
    st.relics = ["desert", "ice", "forest"]
    run(game, 1.2)
    assert {"ace", "keeper"} <= set(st.achievements)
    assert "bane" not in st.achievements


def test_old_save_upgrades_into_act2(tmp_path):
    from stellar_forge.systems.quests import CHAPTERS
    p = tmp_path / "old.json"
    import json
    json.dump({"seed": 5, "chapter": 6, "boss_defeated": True, "relics": ["desert", "ice", "forest"]},
              p.open("w"))
    st = GameState.load(p)
    assert CHAPTERS[st.chapter]["id"] == "shards"
    assert st.stats["creatures"] == 0 and st.shards == []


def test_title_menus_and_settings(game, tmp_path):
    from stellar_forge import config
    from stellar_forge.scenes.menus import (CreditsScene, NewGameScene, SettingsScene, TitleScene)
    game.save()
    game.scenes.switch(TitleScene(game), fade=False)
    assert not game.dialogue.active      # leftover story lines must not eat Enter
    run(game, 2.0)
    t = game.scenes.top
    assert t.save is not None and t.menu.items[0][0] == "Continue"
    labels = [i[0] for i in t.menu.items]
    t.menu.index = labels.index("Settings")
    run(game, 0.1, [key(pygame.K_RETURN)])
    s = game.scenes.top
    assert isinstance(s, SettingsScene)
    before = game.settings.music
    run(game, 0.1, [key(pygame.K_DOWN)])
    run(game, 0.1, [key(pygame.K_LEFT)])
    assert game.settings.music == pytest.approx(before - 0.1)
    run(game, 0.1, [key(pygame.K_ESCAPE)])
    assert config.SETTINGS_FILE.exists()
    t.menu.index = labels.index("Credits")
    run(game, 0.1, [key(pygame.K_RETURN)])
    assert isinstance(game.scenes.top, CreditsScene)
    run(game, 1.0)
    run(game, 0.1, [key(pygame.K_ESCAPE)])
    t.menu.index = labels.index("Logbook")
    run(game, 0.1, [key(pygame.K_RETURN)])
    lb = game.scenes.top
    for _ in range(4):
        run(game, 0.1, [key(pygame.K_RIGHT)])
    run(game, 0.1, [key(pygame.K_ESCAPE)])
    t.menu.index = labels.index("New Game")
    run(game, 0.1, [key(pygame.K_RETURN)])
    assert type(game.scenes.top).__name__ == "SlotScene"
    run(game, 0.1, [key(pygame.K_RIGHT)])
    run(game, 0.1, [key(pygame.K_RETURN)])
    ng = game.scenes.top
    assert isinstance(ng, NewGameScene)
    ng.seed = ""
    for ch in "777":
        run(game, 0.02, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_7, mod=0, unicode=ch)])
    run(game, 0.1, [key(pygame.K_RETURN)])
    run(game, 1.0)
    assert game.state.seed == 777 and isinstance(game.scenes.top, SurfaceScene)
    assert config.SAVE_FILE.name == "savegame_2.json"           # slot 2
    assert lb is not None


def test_logbook_renders_every_tab_in_game(game):
    game.state.biomes_visited = ["forest", "desert"]
    run(game, 0.1, [key(pygame.K_b)])
    assert type(game.scenes.top).__name__ == "LogbookScene"
    for _ in range(4):
        run(game, 0.1, [key(pygame.K_RIGHT), ])
        run(game, 0.05, [key(pygame.K_DOWN)])
    run(game, 0.1, [key(pygame.K_b)])
    assert isinstance(game.scenes.top, SurfaceScene)


def test_music_tracks_render_seamless_stereo():
    import numpy as np
    from stellar_forge.core.music import TRACKS, render_track
    for name in TRACKS:
        x = render_track(name)
        assert x.ndim == 2 and x.shape[1] == 2 and np.isfinite(x).all()
        assert 0.05 < float(np.abs(x).max()) <= 1.0
