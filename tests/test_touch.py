"""Tests for the touch control overlay and Android config."""
import os
import sys
from collections import defaultdict
from unittest.mock import MagicMock, patch

import pygame
import pytest

# ---------------------------------------------------------------------------
# Touch overlay unit tests
# ---------------------------------------------------------------------------

def _make_game():
    """Lightweight Game-like stub for touch tests."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((1280, 720))

    from stellar_forge.core.game import Game
    game = Game(headless=True)
    game.new_game(seed=1)
    game.scenes.stack = [game.space]
    return game


class TestTouchOverlay:
    def test_overlay_exists_on_game(self):
        game = _make_game()
        from stellar_forge.ui.touch import TouchOverlay
        assert isinstance(game.touch, TouchOverlay)

    def test_overlay_disabled_by_default_on_desktop(self):
        game = _make_game()
        # On a normal desktop, touch should be disabled unless setting is on
        assert game.touch.enabled is False or os.environ.get("ANDROID_ARGUMENT")

    def test_enable_via_settings(self):
        game = _make_game()
        game.settings.touch_controls = True
        game.apply_settings()
        assert game.touch.enabled is True

    def test_finger_down_produces_virtual_key(self):
        game = _make_game()
        game.touch.enabled = True
        # Simulate a FINGERDOWN in the FIRE button zone (right side, bottom)
        from stellar_forge import config
        from stellar_forge.ui.touch import _RB_X, _RB_Y
        # Normalise to 0..1 range (what SDL provides)
        nx = _RB_X / config.SCREEN_W
        ny = _RB_Y / config.SCREEN_H
        event = pygame.event.Event(pygame.FINGERDOWN, x=nx, y=ny,
                                   finger_id=1, dx=0.0, dy=0.0, pressure=1.0)
        consumed = game.touch.handle_event(event)
        assert consumed is True
        assert pygame.K_SPACE in game.touch.held

    def test_finger_up_releases_key(self):
        game = _make_game()
        game.touch.enabled = True
        from stellar_forge import config
        from stellar_forge.ui.touch import _RB_X, _RB_Y
        nx = _RB_X / config.SCREEN_W
        ny = _RB_Y / config.SCREEN_H
        down = pygame.event.Event(pygame.FINGERDOWN, x=nx, y=ny,
                                  finger_id=2, dx=0.0, dy=0.0, pressure=1.0)
        game.touch.handle_event(down)
        assert pygame.K_SPACE in game.touch.held
        up = pygame.event.Event(pygame.FINGERUP, x=nx, y=ny,
                                finger_id=2, dx=0.0, dy=0.0, pressure=0.0)
        game.touch.handle_event(up)
        assert pygame.K_SPACE not in game.touch.held

    def test_joystick_produces_directional_keys(self):
        game = _make_game()
        game.touch.enabled = True
        from stellar_forge import config
        from stellar_forge.ui.touch import _JOY_CX, _JOY_CY
        # Finger down in the joystick zone, then move right
        cx_norm = _JOY_CX / config.SCREEN_W
        cy_norm = _JOY_CY / config.SCREEN_H
        down = pygame.event.Event(pygame.FINGERDOWN, x=cx_norm, y=cy_norm,
                                  finger_id=3, dx=0.0, dy=0.0, pressure=1.0)
        game.touch.handle_event(down)
        # Move right
        right_x = (_JOY_CX + 70) / config.SCREEN_W
        move = pygame.event.Event(pygame.FINGERMOTION, x=right_x, y=cy_norm,
                                  finger_id=3, dx=0.01, dy=0.0, pressure=1.0)
        game.touch.handle_event(move)
        assert pygame.K_d in game.touch.held

    def test_draw_does_not_crash(self):
        game = _make_game()
        game.touch.enabled = True
        surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
        # Should not raise in either mode
        game.touch.draw(surf)
        # Switch to on-foot scene stub
        game.scenes.top.on_foot = True
        game.touch.draw(surf)

    def test_touch_held_merged_into_input_pressed(self):
        game = _make_game()
        game.touch.enabled = True
        game.touch.held.add(pygame.K_w)
        pressed = game.input.pressed()
        assert pressed[pygame.K_w]

    def test_non_touch_event_not_consumed(self):
        game = _make_game()
        game.touch.enabled = True
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0,
                                   unicode=" ", scancode=0)
        consumed = game.touch.handle_event(event)
        assert consumed is False


class TestAndroidConfig:
    def test_is_android_false_on_desktop(self):
        from stellar_forge.ui.touch import is_android
        assert is_android() is False

    def test_config_is_android_flag(self):
        from stellar_forge import config
        assert config.IS_ANDROID is False

    def test_touch_controls_in_settings(self):
        from stellar_forge.core.settings import Settings
        s = Settings()
        assert hasattr(s, "touch_controls")
        assert s.touch_controls is False
