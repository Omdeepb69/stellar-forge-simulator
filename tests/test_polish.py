"""Gamepad layer, Act II intro, New Game+ Warlord and animation."""
import pygame
from conftest import run

from stellar_forge.scenes.surface import SurfaceScene


def pad(kind, **kw):
    kw.setdefault("instance_id", 0)
    kw.setdefault("joy", 0)
    return pygame.event.Event(kind, **kw)


def test_pad_a_advances_dialogue_then_jumps_on_foot(game):
    s = game.scenes.top
    assert isinstance(s, SurfaceScene)
    game.dialogue.say([("ai", "one"), ("ai", "two")])
    game.dialogue.chars = 99
    n = len(game.dialogue.queue)
    run(game, 0.05, [pad(pygame.JOYBUTTONDOWN, button=0)])
    assert len(game.dialogue.queue) == n - 1
    game.dialogue.queue.clear()
    run(game, 0.05, [pad(pygame.JOYBUTTONUP, button=0)])
    y0 = s.pilot.y
    run(game, 0.05, [pad(pygame.JOYBUTTONDOWN, button=0)])
    run(game, 0.15)
    assert s.pilot.y < y0 - 5          # A = jump on foot
    run(game, 0.05, [pad(pygame.JOYBUTTONUP, button=0)])


def test_pad_stick_walks_and_menus_navigate(game):
    s = game.scenes.top
    game.dialogue.queue.clear()
    x0 = s.pilot.x
    run(game, 0.6, [pad(pygame.JOYHATMOTION, hat=0, value=(1, 0))])
    assert s.pilot.x > x0 + 50
    run(game, 0.05, [pad(pygame.JOYHATMOTION, hat=0, value=(0, 0))])
    run(game, 0.1, [pad(pygame.JOYBUTTONDOWN, button=7)])       # Start = pause
    menu = game.scenes.top
    assert type(menu).__name__ == "PauseScene"
    run(game, 0.05, [pad(pygame.JOYHATMOTION, hat=0, value=(0, -1))])
    assert menu.menu.index == 1
    run(game, 0.05, [pad(pygame.JOYHATMOTION, hat=0, value=(0, 0))])
    run(game, 0.1, [pad(pygame.JOYBUTTONDOWN, button=1)])       # B = back
    assert isinstance(game.scenes.top, SurfaceScene)


def test_quitting_during_act2_intro_resumes_in_act2(game):
    st = game.state
    st.relics = ["desert", "ice", "forest"]
    st.chapter = 5
    game.return_to_space_after_boss()
    run(game, 1.0)
    assert type(game.scenes.top).__name__ == "ActTwoScene"
    assert game.continue_game()           # e.g. the window was closed mid-cutscene
    run(game, 1.0)
    assert game.state.boss_defeated and game.quests.cid == "shards"


def test_warlord_is_tougher_in_new_game_plus(game, monkeypatch):
    from stellar_forge.scenes.boss import BossScene
    from stellar_forge.surface.player import Pilot
    monkeypatch.setattr(Pilot, "hurt", lambda self, *a, **k: False)
    game.state.ng_plus = 2
    game.scenes.switch(BossScene(game), fade=False)
    b = game.scenes.top
    assert len(b.minions) == 10
    b.start_phase(2)
    assert b.boss_max == round(7 * 1.8)


def test_pilot_animation_poses(game):
    p = game.scenes.top.pilot
    base = p.idle
    p.on_ground, p.vx = True, 250
    p.walk_anim = 1.0
    img, bob = p._animate(base)
    assert img is not base and bob < 0
    p.land_squash = 1.0
    img, _ = p._animate(base)
    assert img.get_width() > base.get_width()
