"""Tiny publish/subscribe bus so systems stay decoupled.

Scenes emit gameplay facts ("enemy_destroyed", "relic_collected" ...);
quests, contracts, audio and the HUD react without scenes knowing them.
"""
from collections import defaultdict
from typing import Callable


class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Callable]] = defaultdict(list)

    def on(self, name: str, fn: Callable) -> None:
        self._subs[name].append(fn)

    def emit(self, name: str, **data) -> None:
        for fn in list(self._subs.get(name, ())):
            fn(**data)
        for fn in list(self._subs.get("*", ())):
            fn(name=name, **data)
