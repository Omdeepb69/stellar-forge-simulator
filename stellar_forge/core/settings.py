"""Player preferences, stored separately from the campaign save."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .. import config


@dataclass
class Settings:
    master: float = 0.8
    music: float = 0.6
    sfx: float = 0.8
    fullscreen: bool = False
    shake: float = 1.0          # 0 = off, 0.5 = reduced, 1 = full
    show_fps: bool = False
    show_hints: bool = True     # control hints along the bottom of the screen
    colorblind: bool = False    # swap red/green signals for orange/blue
    touch_controls: bool = False  # show on-screen touch buttons (auto-enabled on Android)
    bindings: dict = field(default_factory=dict)   # action -> pygame key code
    last_slot: int = 0
    camera: int = 1             # space camera distance: 0 close, 1 medium, 2 far

    @classmethod
    def load(cls, path=None) -> "Settings":
        path = path or config.SETTINGS_FILE
        s = cls()
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return s
        for k, v in data.items():
            if hasattr(s, k) and isinstance(v, type(getattr(s, k))):
                setattr(s, k, v)
        return s

    def save(self, path=None) -> None:
        path = path or config.SETTINGS_FILE
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), indent=1))
        except OSError:
            pass
