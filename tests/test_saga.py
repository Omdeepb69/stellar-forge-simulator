"""Act III, the side arcs, the camera, nebula memory and crash recovery."""
import pygame
from conftest import key, run
from test_expansion import _invulnerable, _space

from stellar_forge import config
from stellar_forge.systems import quests as Q
from stellar_forge.systems import saga as S


def test_chapter_indices_line_up():
    ids = [c["id"] for c in Q.CHAPTERS]
    assert ids[Q.FREE] == "free" and ids[Q.FREE + 1:] == ["road", "judgment", "legend"]


def test_close_camera_in_a_nebula_keeps_memory_flat(game, monkeypatch):
    from stellar_forge.entities import bodies
    _invulnerable(monkeypatch)
    sp = _space(game)
    neb = next(n for dx in range(-4, 5) for dy in range(-4, 5) for n in game.universe.sector(dx, dy).nebulae)
    sp.set_camera(0)
    for off in (0, neb.radius * 0.5, neb.radius):
        sp.place_ship(neb.center + pygame.Vector2(off, 0))
        sp.ship.vel *= 0
        run(game, 0.5)
    assert bodies._SCALED_PX <= bodies._CACHE_BUDGET
    assert all(s.get_width() <= 4096 for s in bodies._SCALED.values())


def test_three_camera_distances(game):
    sp = _space(game)
    modes = []
    for _ in range(3):
        run(game, 0.05, [key(pygame.K_v)])
        modes.append(sp.cam_mode)
    assert sorted(set(modes)) == [0, 1, 2] and game.settings.camera == sp.cam_mode
    zooms = [z for _n, z in __import__("stellar_forge.scenes.space", fromlist=["x"]).CAMERAS]
    assert zooms[0] > zooms[1] > zooms[2]


def _act_three(game):
    st = game.state
    st.boss_defeated = True
    st.ending = "rebuild"
    st.forge_restored = True
    st.signal_found = True
    st.chapter = Q.FREE
    game.quests.start_act_three()
    assert game.quests.cid == "road"
    game.dialogue.queue.clear()


def test_maker_road_trials_and_the_last_smith(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    _act_three(game)
    saga = sp.saga
    assert len(saga.waystones()) == 3
    # Memory: a wrong answer costs hull, right answers pass
    hull = game.state.hull
    assert isinstance(saga._answer(0, False), tuple) and game.state.hull < hull
    for k in range(3):
        saga._answer(k, True)
    assert "memory" in S.data(game.state)["waystones"]
    # Making: hold the waystone for the full time
    sp.place_ship(S.waystone_pos(game.universe, "making"))
    saga._begin("making")
    saga.trial["t"] = S.MAKING_TIME - 0.1
    run(game, 0.3)
    assert "making" in S.data(game.state)["waystones"]
    # Mercy: spare the Penitent
    sp.place_ship(S.waystone_pos(game.universe, "mercy"))
    saga._mercy()
    game.dialogue.queue.clear()
    saga._mercy_choice()
    game.scenes.top.menu.items[0][1]()
    assert S.data(game.state)["penitent"] == "spared" and game.quests.cid == "judgment"
    # the Bell: allies answer, the Last Smith falls, the verdict is given
    game.dialogue.queue.clear()
    sp.place_ship(saga.bell_pos())
    sp.enemies.clear()
    saga._ring()
    boss = saga.final
    assert boss is not None and any(s.name.startswith("Remnant Free Fleet") for s in sp.corps.ships)
    boss.hurt(10 ** 9)
    sp._enemy_killed(boss)
    assert game.quests.cid == "legend" and S.data(game.state)["verdict"] in ("stay", "watch", "leave")


def test_new_dawn_escort(game, monkeypatch):
    _invulnerable(monkeypatch)
    sp = _space(game)
    game.state.boss_defeated = True
    S.data(game.state)["ark"] = "known"
    sp.place_ship(S.ark_pos(game.universe))
    sp.enemies.clear()
    assert "New Dawn" in sp.saga.prompt()[0]
    S.data(game.state)["ark"] = "escort"
    run(game, 0.2)
    ark = sp.saga.ark
    assert ark is not None and ark in sp.corps.ships
    ark.pos = sp.saga._haven() + pygame.Vector2(300, 0)
    run(game, 0.1)
    assert S.data(game.state)["ark"] == "rescued"


def test_defectors_raise_remnant_standing(game, monkeypatch):
    from stellar_forge.systems.space_events import Defector
    _invulnerable(monkeypatch)
    sp = _space(game)
    game.state.boss_defeated = True
    ev = sp.director.spawn(Defector)
    rep = game.state.rep["remnant"]
    ev._escort()
    d = sp.saga.convoy[0]
    d.pos = sp.saga._haven() + pygame.Vector2(200, 0)
    run(game, 0.1)
    assert game.state.rep["remnant"] == rep + 15 and S.data(game.state)["defectors"] == 1


def test_homecoming_town_on_earth_prime(game):
    from stellar_forge.scenes.surface import SurfaceScene
    game.state.ending = "rebuild"
    S.data(game.state)["ark"] = "rescued"
    game.universe.earth = True
    game.universe.rebuild_home()
    earth = next(b for b in game.universe.sector(0, 0).bodies if getattr(b, "name", "") == "Earth-Prime")
    s = SurfaceScene(game, earth)
    town = next(w for w in s.pois.walkers if w.group["name"] == "Homecoming")
    assert len(town.members) >= 3 and S.data(game.state)["homecoming"]


def test_crash_recovery_logs_and_returns(game, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_FILE", tmp_path / "save.json")
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        game._recover(5)
    assert "boom" in (tmp_path / "crash.log").read_text()


def test_solar_flare_after_leaving_the_system_does_not_crash(game, monkeypatch):
    from stellar_forge.systems.space_events import SolarFlare
    _invulnerable(monkeypatch)
    sp = _space(game)
    ev = sp.director.spawn(SolarFlare)
    if ev is None:
        return
    sp.place_ship(sp.ship.pos + pygame.Vector2(config.SECTOR_SIZE * 3, 0))   # flown / towed far away
    run(game, 0.5)
    assert not ev.alive


def test_boss_arena_is_the_original_and_never_shakes(game):
    from stellar_forge.scenes.boss import FLOOR, BossScene
    b = BossScene(game)
    game.scenes.switch(b, fade=False, force=True)
    run(game, 0.2)
    assert b.img_bg.get_size() == (config.SCREEN_W, config.SCREEN_H)     # background fills the screen
    assert b.img_pillar.get_size() == (120, 300) and FLOOR == config.SCREEN_H - 80
    game.shake(30)
    b.pilot.hurt(10, 1)
    run(game, 0.1)
    assert b.camera.ox == 0 and b.camera.oy == 0
