"""Gamepad support layered on top of the keyboard controls.

Every scene already reads the keyboard, so instead of teaching each scene
about controllers, pad input is translated into *virtual keys*:

* held buttons/sticks are merged into ``Input.pressed()`` (a drop-in for
  ``pygame.key.get_pressed()``), and
* button presses become synthetic ``KEYDOWN`` events, so menus, docking,
  landing and dialogue just work.

Layout (Xbox naming, SDL's standard indices):
    left stick / d-pad  move, steer, menu navigation   (arrow keys + WASD)
    A                   fire / confirm / advance dialogue (Space)
    B                   back / pause                    (Esc)
    X                   interact: dock, mine, board     (E)
    Y                   land                            (L)
    on foot: A jump, X sword, Y interact, RB blaster, LB grapple, View scan
    LB / RB             boost / blaster                 (Shift / F)
    LT / RT             brake / thrust                  (S / W)
    Back / View         galaxy map                      (M)
    Start / Menu        pause                           (Esc)
    right-stick click   logbook                         (B)
"""
from __future__ import annotations

import pygame

DEADZONE = 0.45

BUTTONS = {
    0: (pygame.K_SPACE,),
    1: (pygame.K_ESCAPE,),
    2: (pygame.K_e,),
    3: (pygame.K_l,),
    4: (pygame.K_LSHIFT,),
    5: (pygame.K_f,),
    6: (pygame.K_m,),
    7: (pygame.K_ESCAPE,),
    8: (pygame.K_v,),          # Back / View: camera distance
    9: (pygame.K_c,),          # left stick click: hail the Corps
    10: (pygame.K_b,),
}
# on foot the face buttons are remapped: A jump, X sword, Y interact, RB blaster
ON_FOOT = {0: (pygame.K_w,), 2: (pygame.K_SPACE,), 3: (pygame.K_e,), 5: (pygame.K_f,), 4: (pygame.K_g,)}
# keys that should only ever be tapped (never reported as held)
TAP_ONLY = {pygame.K_ESCAPE, pygame.K_m, pygame.K_b, pygame.K_l, pygame.K_v, pygame.K_c, pygame.K_h}

# Rebindable actions: (id, label, default key). Scenes keep reading the
# default key; the input layer maps whatever the player bound onto it.
ACTIONS = [
    ("thrust", "Thrust / jump", pygame.K_w), ("brake", "Brake / down", pygame.K_s),
    ("left", "Turn / walk left", pygame.K_a), ("right", "Turn / walk right", pygame.K_d),
    ("fire", "Fire / sword", pygame.K_SPACE), ("interact", "Interact / dock / mine", pygame.K_e),
    ("land", "Land", pygame.K_l), ("blaster", "Blaster (on foot)", pygame.K_f),
    ("heal", "Use medkit (on foot)", pygame.K_h),
    ("boost", "Boost", pygame.K_LSHIFT), ("weapon", "Switch weapon", pygame.K_q),
    ("autopilot", "Autopilot", pygame.K_p),
    ("outpost", "Outpost menu", pygame.K_o),
    ("map", "Galaxy map", pygame.K_m), ("logbook", "Logbook", pygame.K_b),
    ("camera", "Camera distance", pygame.K_v), ("corps", "Hail the Survey Corps", pygame.K_c),
]
ACTION_DEFAULT = {a: k for a, _l, k in ACTIONS}

DIRS = {"left": (pygame.K_LEFT, pygame.K_a), "right": (pygame.K_RIGHT, pygame.K_d),
        "up": (pygame.K_UP, pygame.K_w), "down": (pygame.K_DOWN, pygame.K_s)}


class _Merged:
    """Indexable like pygame's ScancodeWrapper, merging keyboard + pad and
    applying the player's key bindings."""

    __slots__ = ("keys", "virtual", "to_phys", "blocked")

    def __init__(self, keys, virtual, to_phys=None, blocked=()):
        self.keys = keys
        self.virtual = virtual
        self.to_phys = to_phys or {}
        self.blocked = blocked

    def __getitem__(self, k):
        if k in self.virtual:
            return True
        phys = self.to_phys.get(k)
        if phys is not None:
            return bool(self.keys[phys])
        if k in self.blocked:
            return False
        return bool(self.keys[k])


class Input:
    def __init__(self, game):
        self.game = game
        self.pads: dict[int, pygame.joystick.JoystickType] = {}
        self.held: set[int] = set()          # virtual keys from buttons
        self.dirs: set[str] = set()          # from stick / hat
        self.triggers: set[int] = set()
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                self._add(i, quiet=True)
        except pygame.error:
            pass

    # ---- key bindings ---------------------------------------------------
    def rebuild_bindings(self) -> None:
        """canonical key <-> physical key tables from the settings."""
        binds = getattr(self.game.settings, "bindings", {}) or {}
        self.to_phys: dict[int, int] = {}
        self.to_canon: dict[int, int] = {}
        for action, phys in binds.items():
            canon = ACTION_DEFAULT.get(action)
            if canon is None or phys == canon:
                continue
            self.to_phys[canon] = phys
            self.to_canon[phys] = canon
        # a default key that now belongs to nothing is ignored
        self.blocked = {c for c in self.to_phys if c not in self.to_canon}

    def remap(self, event):
        if not hasattr(self, "to_canon"):
            self.rebuild_bindings()
        if event.type in (pygame.KEYDOWN, pygame.KEYUP) and not getattr(event, "from_pad", False):
            canon = self.to_canon.get(event.key)
            if canon is not None:
                d = dict(event.dict)
                d["key"] = canon
                return pygame.event.Event(event.type, d)
            if event.key in self.blocked:
                return None
        return event

    def key_for(self, action: str) -> int:
        return (getattr(self.game.settings, "bindings", {}) or {}).get(action, ACTION_DEFAULT[action])

    def key_name(self, action: str) -> str:
        return pygame.key.name(self.key_for(action)).upper()

    @property
    def connected(self) -> bool:
        return bool(self.pads)

    def _add(self, index: int, quiet=False) -> None:
        try:
            js = pygame.joystick.Joystick(index)
            name = js.get_name() or ""
            # Android exposes device accelerometer/gyro sensors as SDL joysticks
            if any(k in name.lower() for k in ("accelerometer", "gyro", "sensor")):
                return
            js.init()
        except pygame.error:
            return
        self.pads[js.get_instance_id()] = js
        if not quiet:
            self.game.toasts.add(f"Controller connected: {name[:28]}", (140, 220, 255))

    # ------------------------------------------------------------------
    def pressed(self) -> _Merged:
        virtual = {k for k in self.held if k not in TAP_ONLY} | self.triggers
        for d in self.dirs:
            virtual.update(DIRS[d])
        # Merge touch-overlay held keys
        touch = getattr(self.game, "touch", None)
        if touch is not None and touch.enabled:
            virtual |= {k for k in touch.held if k not in TAP_ONLY}
        if not hasattr(self, "to_phys"):
            self.rebuild_bindings()
        return _Merged(pygame.key.get_pressed(), virtual, self.to_phys, self.blocked)

    def translate(self, event) -> list:
        """Turn one pad event into zero or more synthetic keyboard events."""
        t = event.type
        out = []
        if t == pygame.JOYDEVICEADDED:
            self._add(event.device_index)
        elif t == pygame.JOYDEVICEREMOVED:
            self.pads.pop(event.instance_id, None)
            self.held.clear()
            self.dirs.clear()
            self.triggers.clear()
            self.game.toasts.add("Controller disconnected", (255, 190, 70))
        elif t == pygame.JOYBUTTONDOWN:
            if event.button == 0 and self.game.dialogue.active:
                self.game.dialogue.advance()     # A always advances dialogue first
                return out
            for k in self._map(event.button):
                self.held.add(k)
                out.append(_key(pygame.KEYDOWN, k))
        elif t == pygame.JOYBUTTONUP:
            for k in set(BUTTONS.get(event.button, ())) | set(ON_FOOT.get(event.button, ())):
                if k in self.held:
                    self.held.discard(k)
                    out.append(_key(pygame.KEYUP, k))
        elif t == pygame.JOYHATMOTION:
            x, y = event.value
            out += self._set_dirs("hat", {"left"} if x < 0 else {"right"} if x > 0 else set(),
                                  {"up"} if y > 0 else {"down"} if y < 0 else set())
        elif t == pygame.JOYAXISMOTION:
            v = event.value
            if event.axis in (0, 1):
                js = self.pads.get(event.instance_id)
                ax = js.get_axis(0) if js else (v if event.axis == 0 else 0)
                ay = js.get_axis(1) if js else (v if event.axis == 1 else 0)
                out += self._set_dirs("stick", {"left"} if ax < -DEADZONE else {"right"} if ax > DEADZONE else set(),
                                      {"up"} if ay < -DEADZONE else {"down"} if ay > DEADZONE else set())
            elif event.axis in (4, 5):   # triggers rest at -1 on most pads
                key = pygame.K_s if event.axis == 4 else pygame.K_w
                if v > 0.2 and key not in self.triggers:
                    self.triggers.add(key)
                elif v <= 0.2:
                    self.triggers.discard(key)
        return out

    def _map(self, button: int):
        top = self.game.scenes.top
        if getattr(top, "on_foot", False) and button in ON_FOOT:
            return ON_FOOT[button]
        return BUTTONS.get(button, ())

    def _set_dirs(self, source: str, horiz: set, vert: set) -> list:
        new = horiz | vert
        out = []
        for d in new - self.dirs:
            out.append(_key(pygame.KEYDOWN, DIRS[d][0]))
        for d in self.dirs - new:
            out.append(_key(pygame.KEYUP, DIRS[d][0]))
        self.dirs = new
        return out


def _key(kind, k):
    return pygame.event.Event(kind, key=k, mod=0, unicode="", scancode=0, from_pad=True)
