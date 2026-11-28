"""Movement feel, scenery scatter and camp settlers."""
import pygame
from conftest import key, run
from test_expansion import _land_on

from stellar_forge import config
from stellar_forge.surface.terrain import Terrain


def _home(game):
    return game.universe.find_body("0,0:0")


def _hold_jump(monkeypatch, held):
    class K:
        def __getitem__(self, k):
            return held[0] and k in (pygame.K_w, pygame.K_UP)
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: K())


def test_plain_jump_never_hurts(game, monkeypatch):
    s = _land_on(game, _home(game))
    s.creatures.clear()
    for _ in range(5):
        hp = game.state.pilot_hp
        run(game, 0.05, [key(pygame.K_w)])
        run(game, 1.2)
        assert game.state.pilot_hp == hp


def test_jetpack_lasts_and_hops_are_safe(game, monkeypatch):
    s = _land_on(game, _home(game))
    s.creatures.clear()
    p = s.pilot
    assert game.state.jetpack_capacity >= 2.5
    held = [True]
    _hold_jump(monkeypatch, held)
    run(game, 1.0)                              # a full second of jetpacking...
    assert p.jet > 0.8                          # ...still leaves fuel
    held[0] = False
    hp = game.state.pilot_hp
    run(game, 2.5)
    assert p.on_ground and game.state.pilot_hp == hp


def test_a_real_drop_still_hurts(game):
    s = _land_on(game, _home(game))
    p = s.pilot
    hp = game.state.pilot_hp
    p.y = s.terrain.height(p.x) - config.SAFE_FALL - 500
    p.peak_y = p.y
    p.on_ground = False
    run(game, 2.0)
    assert game.state.pilot_hp < hp


def test_scatter_groves_logs_and_spacing(game):
    pl = _home(game)
    t = Terrain(pl, pl.seed)
    roles = t.roles()
    trees, logs = [], []
    for c in range(-12, 12):
        for x, idx, _s, _f in t.props(c):
            assert not t.in_pad(x, 60)
            if idx in roles["tree"]:
                trees.append(x)
            if idx in roles["log"]:
                logs.append(x)
                assert t.flat_enough(x, 70, 14)          # never balanced on a steep slope
    trees.sort()
    assert trees and all(b - a > 140 for a, b in zip(trees, trees[1:]))
    assert t.back_props(0) is not None


def test_camp_settlers_live(game, monkeypatch):
    s = _land_on(game, _home(game))
    camp = next(p for p in s.terrain.pois if p["kind"] == "camp")
    crowd = s.pois.npcs[camp["id"]]
    assert crowd[0].role == "giver" and len({n.look for n in crowd}) == len(crowd)
    s.pilot.x = camp["x"] + 1500
    s.pilot.y = s.terrain.height(s.pilot.x)
    start = [n.x for n in crowd]
    moved = False
    for _ in range(24):
        run(game, 0.5)
        moved = moved or any(abs(n.x - x0) > 1 for n, x0 in zip(crowd, start) if n.role != "sitter")
    assert moved                                         # they wander when you're away
    giver = crowd[0]
    s.pilot.x = giver.x + 300
    s.pilot.y = s.terrain.height(s.pilot.x)
    run(game, 0.3)
    assert giver.facing == 1 and giver.target is None    # ...and stop to look at you
    s.pilot.x = giver.x + 60
    game.dialogue.queue.clear()
    run(game, 0.05, [key(pygame.K_e)])
    spk = game.dialogue.queue[0][0]
    assert spk.startswith("settler:") and giver.pose().startswith("talk")
