"""Scene base class and a stack-based scene manager with fade transitions."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pygame

if TYPE_CHECKING:
    from .game import Game


class Scene:
    """Base class for every screen in the game.

    Subclasses override the hooks they need. ``is_overlay`` scenes (pause,
    station menus, map) draw on top of the scene underneath them.
    """

    is_overlay = False
    menu = False            # menus don't count towards play time
    music: str | None = None  # track name, "silence", or None to inherit from below

    def __init__(self, game: "Game"):
        self.game = game

    # lifecycle ---------------------------------------------------------
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def on_resume(self) -> None: ...   # a scene above us was popped
    def on_pause(self) -> None: ...    # a scene was pushed above us

    # frame -------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def draw(self, surf: pygame.Surface) -> None: ...


class SceneManager:
    """Owns the scene stack and guarantees transitions always finish.

    Every change is queued and applied while the screen is fully black,
    so no scene ever sees a half-switched world (the old ``fade_direction``
    bookkeeping could get stuck forever).
    """

    FADE_TIME = 0.35

    def __init__(self, game: "Game"):
        self.game = game
        self.stack: list[Scene] = []
        self._pending: Callable[[], None] | None = None
        self._fade = 0.0          # 0 = clear, 1 = black
        self._fading_out = False

    @property
    def top(self) -> Scene | None:
        return self.stack[-1] if self.stack else None

    @property
    def transitioning(self) -> bool:
        return self._pending is not None or self._fade > 0

    # public API ----------------------------------------------------------
    def switch(self, scene: Scene, fade: bool = True, force: bool = False) -> None:
        """Replace the whole stack with ``scene`` (``force``: see push)."""
        def op():
            while self.stack:
                self.stack.pop().on_exit()
            self.stack.append(scene)
            scene.on_enter()
        self._queue(op, fade, force)

    def replace(self, scene: Scene, fade: bool = True) -> None:
        """Replace only the top scene."""
        def op():
            if self.stack:
                self.stack.pop().on_exit()
            self.stack.append(scene)
            scene.on_enter()
        self._queue(op, fade)

    def push(self, scene: Scene, fade: bool = False, force: bool = False) -> None:
        """``force``: a scene that must not be lost (story beats) waits for any running
        transition instead of being dropped as a double trigger."""
        def op():
            if self.stack:
                self.stack[-1].on_pause()
            self.stack.append(scene)
            scene.on_enter()
        self._queue(op, fade, force)

    def pop(self, fade: bool = False) -> None:
        def op():
            if self.stack:
                self.stack.pop().on_exit()
            if self.stack:
                self.stack[-1].on_resume()
        self._queue(op, fade)

    def _queue(self, op: Callable[[], None], fade: bool, force: bool = False) -> None:
        if self._pending is not None:
            if force:                     # run it right after the transition already under way
                first = self._pending

                def chained():
                    first()
                    op()
                self._pending = chained
            return  # otherwise one transition at a time; ignore double triggers
        if fade:
            self._pending = op
            self._fading_out = True
        else:
            op()

    # frame ---------------------------------------------------------------
    def handle_event(self, event) -> None:
        if self._pending is None and self.top:
            self.top.handle_event(event)

    def update(self, dt: float) -> None:
        if self._pending is not None:
            self._fade = min(1.0, self._fade + dt / self.FADE_TIME)
            if self._fade >= 1.0:
                op, self._pending = self._pending, None
                op()
                self._fading_out = False
            return
        if self._fade > 0:
            self._fade = max(0.0, self._fade - dt / self.FADE_TIME)
        if self.top:
            self.top.update(dt)

    def draw(self, surf: pygame.Surface) -> None:
        # draw from the last opaque scene upwards
        start = len(self.stack) - 1
        while start > 0 and self.stack[start].is_overlay:
            start -= 1
        for scene in self.stack[max(start, 0):]:
            scene.draw(surf)
        if self._fade > 0:
            veil = pygame.Surface(surf.get_size())
            veil.set_alpha(int(255 * self._fade))
            surf.blit(veil, (0, 0))
