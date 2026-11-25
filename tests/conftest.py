import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeKeys:
    def __init__(self):
        self.held = set()

    def __getitem__(self, k):
        return k in self.held


@pytest.fixture
def keys(monkeypatch):
    import pygame
    fk = FakeKeys()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: fk)
    return fk


@pytest.fixture
def game(tmp_path, monkeypatch, keys):
    from stellar_forge import config
    monkeypatch.setattr(config, "SAVE_FILE", tmp_path / "save.json")
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    from stellar_forge.core import game_state
    monkeypatch.setattr(game_state.config, "SAVE_FILE", tmp_path / "save.json")
    from stellar_forge.core.game import Game
    g = Game(headless=True)
    g.new_game(seed=4242)
    run(g, 0.8)
    return g


def run(g, seconds, events=()):
    events = list(events)
    for i in range(int(seconds * 60)):
        g.step(1 / 60, events if i == 0 else [])


def key(k):
    import pygame
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")
