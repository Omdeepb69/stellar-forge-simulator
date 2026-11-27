"""Touch-screen controls for Android (and desktop testing).

Two HUD layouts, automatically selected by the active scene:

**Space HUD** – left virtual joystick (thrust/steer/brake) plus right-side
action buttons: Fire, Boost, Dock, Land, Map, Camera, Corps, Autopilot, Pause.

**On-Foot HUD** – left D-pad (move left/right, jump) plus right-side buttons:
Sword/Boomerang, Blaster, Swap Weapon, Medkit, Interact, Outpost, Pause.

Touch events (``FINGERDOWN / FINGERUP / FINGERMOTION``) are translated into
virtual keys via the existing ``Input._Merged`` system.  The overlay auto-
enables on Android; on desktop it can be toggled in Settings for testing.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from .. import config

if TYPE_CHECKING:
    from ..core.game import Game

# ---------------------------------------------------------------------------
# Android detection
# ---------------------------------------------------------------------------

def is_android() -> bool:
    """Return *True* when running inside a python-for-android environment."""
    try:
        import android  # noqa: F401 – python-for-android injects this module
        return True
    except ImportError:
        pass
    import os
    return bool(os.environ.get("ANDROID_ARGUMENT") or os.environ.get("P4A_BOOTSTRAP"))


# ---------------------------------------------------------------------------
# Layout constants  (designed for 1280x720 landscape, thumb-reachable)
# ---------------------------------------------------------------------------
_BTN_R = 42          # button circle radius
_BTN_R2 = 36         # smaller secondary button
_JOY_R = 90          # outer joystick circle
_JOY_DEAD = 0.22     # joystick deadzone fraction
_ALPHA = 110          # overlay opacity (0-255)
_ALPHA_PRESSED = 170

# Left-side joystick / D-pad centre
_JOY_CX = 150
_JOY_CY = config.SCREEN_H - 180

# Right-side button clusters
_RB_X = config.SCREEN_W - 150    # primary action column
_RB_X2 = config.SCREEN_W - 260   # secondary column
_RB_Y = config.SCREEN_H - 180    # bottom row Y


# ---------------------------------------------------------------------------
# Button definitions: (key, label, x, y, radius)
# ---------------------------------------------------------------------------
def _space_buttons() -> list[tuple[int, str, int, int, int]]:
    """Buttons visible during space flight."""
    return [
        (pygame.K_SPACE,  "FIRE",  _RB_X, _RB_Y,       _BTN_R),
        (pygame.K_LSHIFT, "BOOST", _RB_X2, _RB_Y,      _BTN_R2),
        (pygame.K_e,      "DOCK",  _RB_X, _RB_Y - 100,  _BTN_R2),
        (pygame.K_l,      "LAND",  _RB_X2, _RB_Y - 100, _BTN_R2),
        (pygame.K_m,      "MAP",   _RB_X, _RB_Y - 195,  _BTN_R2),
        (pygame.K_v,      "CAM",   _RB_X2, _RB_Y - 195, _BTN_R2),
        (pygame.K_c,      "CORPS", config.SCREEN_W - 70, _RB_Y - 275, _BTN_R2),
        (pygame.K_p,      "AUTO",  config.SCREEN_W - 170, _RB_Y - 275, _BTN_R2),
        (pygame.K_ESCAPE, "||",    config.SCREEN_W - 55, 55, 30),
    ]


def _foot_buttons() -> list[tuple[int, str, int, int, int]]:
    """Buttons visible while on foot (surface / cave)."""
    return [
        (pygame.K_SPACE,  "SWORD", _RB_X, _RB_Y,        _BTN_R),
        (pygame.K_f,      "GUN",   _RB_X2, _RB_Y,       _BTN_R2),
        (pygame.K_q,      "SWAP",  _RB_X, _RB_Y - 100,   _BTN_R2),
        (pygame.K_h,      "MED",   _RB_X2, _RB_Y - 100,  _BTN_R2),
        (pygame.K_e,      "USE",   _RB_X, _RB_Y - 195,   _BTN_R2),
        (pygame.K_o,      "BASE",  _RB_X2, _RB_Y - 195,  _BTN_R2),
        (pygame.K_ESCAPE, "||",    config.SCREEN_W - 55, 55, 30),
    ]


# D-pad arrows for on-foot
_DPAD_LEFT  = (pygame.K_a, "◀", _JOY_CX - 75, _JOY_CY, 38)
_DPAD_RIGHT = (pygame.K_d, "▶", _JOY_CX + 75, _JOY_CY, 38)
_DPAD_JUMP  = (pygame.K_w, "▲", _JOY_CX,      _JOY_CY - 75, 38)


# ---------------------------------------------------------------------------
# Touch overlay
# ---------------------------------------------------------------------------
class TouchOverlay:
    """Renders semi-transparent controls and converts touch → virtual keys."""

    def __init__(self, game: Game):
        self.game = game
        self.enabled = is_android()
        # finger_id → assigned widget ("joy", "btn:<key>", "dpad:<key>")
        self._fingers: dict[int, str] = {}
        # joystick state
        self._joy_dx = 0.0
        self._joy_dy = 0.0
        # which virtual keys are currently held by touch
        self.held: set[int] = set()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a FINGER* event.  Returns True if consumed."""
        if not self.enabled:
            return False
        t = event.type
        if t not in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            return False

        # SDL gives finger coords as 0..1 fractions of the window
        px = event.x * config.SCREEN_W
        py = event.y * config.SCREEN_H
        fid = event.finger_id

        if t == pygame.FINGERDOWN:
            self._on_down(fid, px, py)
        elif t == pygame.FINGERMOTION:
            self._on_move(fid, px, py)
        elif t == pygame.FINGERUP:
            self._on_up(fid)
        return True

    def update(self, _dt: float) -> None:
        """Push joystick / D-pad / button state into the Input layer."""
        pass  # held set is already maintained by _on_down/_on_up

    def draw(self, surf: pygame.Surface) -> None:
        """Draw semi-transparent touch HUD on top of the scene."""
        if not self.enabled:
            return

        on_foot = getattr(self.game.scenes.top, "on_foot", False)
        pressed = self.held

        if on_foot:
            self._draw_dpad(surf, pressed)
            buttons = _foot_buttons()
        else:
            self._draw_joystick(surf, pressed)
            buttons = _space_buttons()

        for key, label, bx, by, br in buttons:
            active = key in pressed
            self._draw_button(surf, bx, by, br, label, active)

    # ------------------------------------------------------------------
    # internal: input routing
    # ------------------------------------------------------------------
    def _buttons(self) -> list[tuple[int, str, int, int, int]]:
        on_foot = getattr(self.game.scenes.top, "on_foot", False)
        return _foot_buttons() if on_foot else _space_buttons()

    def _on_down(self, fid: int, px: float, py: float) -> None:
        on_foot = getattr(self.game.scenes.top, "on_foot", False)

        # check buttons first (right side of screen)
        for key, _lbl, bx, by, br in self._buttons():
            if (px - bx) ** 2 + (py - by) ** 2 <= (br + 12) ** 2:
                self._fingers[fid] = f"btn:{key}"
                self._press(key)
                return

        if on_foot:
            # D-pad regions
            for key, _lbl, dx, dy, dr in (_DPAD_LEFT, _DPAD_RIGHT, _DPAD_JUMP):
                if (px - dx) ** 2 + (py - dy) ** 2 <= (dr + 14) ** 2:
                    self._fingers[fid] = f"dpad:{key}"
                    self._press(key)
                    return
        else:
            # joystick zone (left side)
            if (px - _JOY_CX) ** 2 + (py - _JOY_CY) ** 2 <= (_JOY_R + 40) ** 2:
                self._fingers[fid] = "joy"
                self._update_joy(px, py)
                return

    def _on_move(self, fid: int, px: float, py: float) -> None:
        widget = self._fingers.get(fid)
        if widget == "joy":
            self._update_joy(px, py)

    def _on_up(self, fid: int) -> None:
        widget = self._fingers.pop(fid, None)
        if widget is None:
            return
        if widget == "joy":
            self._release_joy()
        elif widget.startswith("btn:") or widget.startswith("dpad:"):
            key = int(widget.split(":", 1)[1])
            self._release(key)

    # --- virtual key helpers ---
    def _press(self, key: int) -> None:
        if key not in self.held:
            self.held.add(key)
            evt = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="",
                                    scancode=0, from_touch=True)
            pygame.event.post(evt)

    def _release(self, key: int) -> None:
        if key in self.held:
            self.held.discard(key)
            evt = pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode="",
                                    scancode=0, from_touch=True)
            pygame.event.post(evt)

    # --- joystick ---
    def _update_joy(self, px: float, py: float) -> None:
        dx = (px - _JOY_CX) / _JOY_R
        dy = (py - _JOY_CY) / _JOY_R
        mag = math.hypot(dx, dy)
        if mag > 1.0:
            dx /= mag
            dy /= mag

        self._joy_dx = dx
        self._joy_dy = dy

        # Map joystick to virtual keys:
        #   up = thrust (W), down = brake (S), left/right = steer (A/D)
        new_held: set[int] = set()
        if dy < -_JOY_DEAD:
            new_held.add(pygame.K_w)
        if dy > _JOY_DEAD:
            new_held.add(pygame.K_s)
        if dx < -_JOY_DEAD:
            new_held.add(pygame.K_a)
        if dx > _JOY_DEAD:
            new_held.add(pygame.K_d)

        joy_keys = {pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d}
        for k in joy_keys:
            if k in new_held and k not in self.held:
                self._press(k)
            elif k not in new_held and k in self.held:
                # only release if the key belongs to the joystick
                # (not pressed by a separate button widget)
                any_other = any(w.startswith("btn:") and int(w.split(":")[1]) == k
                                for w in self._fingers.values())
                if not any_other:
                    self._release(k)

    def _release_joy(self) -> None:
        self._joy_dx = 0.0
        self._joy_dy = 0.0
        joy_keys = {pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d}
        for k in joy_keys & self.held:
            any_other = any(w.startswith("btn:") and int(w.split(":")[1]) == k
                            for w in self._fingers.values())
            if not any_other:
                self._release(k)

    # ------------------------------------------------------------------
    # drawing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _draw_button(surf: pygame.Surface, x: int, y: int, r: int,
                     label: str, active: bool) -> None:
        alpha = _ALPHA_PRESSED if active else _ALPHA
        circle = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        col = (255, 210, 100, alpha) if active else (200, 220, 240, alpha)
        pygame.draw.circle(circle, col, (r + 2, r + 2), r)
        border_col = (255, 230, 150, min(255, alpha + 50)) if active else (160, 180, 200, min(255, alpha + 30))
        pygame.draw.circle(circle, border_col, (r + 2, r + 2), r, 2)
        surf.blit(circle, (x - r - 2, y - r - 2))
        from .text import text as draw_text
        fsz = 11 if len(label) > 3 else 13
        draw_text(surf, label, (x, y), fsz,
                  (40, 30, 20) if active else (220, 230, 245),
                  anchor="center", bold=active)

    def _draw_joystick(self, surf: pygame.Surface, pressed: set[int]) -> None:
        """Draw the left-side virtual joystick."""
        # Outer ring
        ring = pygame.Surface((_JOY_R * 2 + 8, _JOY_R * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(ring, (180, 200, 220, _ALPHA // 2), (_JOY_R + 4, _JOY_R + 4), _JOY_R, 3)
        surf.blit(ring, (_JOY_CX - _JOY_R - 4, _JOY_CY - _JOY_R - 4))
        # Inner nub
        nub_x = _JOY_CX + int(self._joy_dx * _JOY_R * 0.6)
        nub_y = _JOY_CY + int(self._joy_dy * _JOY_R * 0.6)
        nub_r = 32
        nub = pygame.Surface((nub_r * 2 + 4, nub_r * 2 + 4), pygame.SRCALPHA)
        active = bool(pressed & {pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d})
        col = (255, 220, 130, _ALPHA_PRESSED) if active else (200, 215, 230, _ALPHA)
        pygame.draw.circle(nub, col, (nub_r + 2, nub_r + 2), nub_r)
        pygame.draw.circle(nub, (230, 240, 250, min(255, _ALPHA + 40)), (nub_r + 2, nub_r + 2), nub_r, 2)
        surf.blit(nub, (nub_x - nub_r - 2, nub_y - nub_r - 2))

    @staticmethod
    def _draw_dpad(surf: pygame.Surface, pressed: set[int]) -> None:
        """Draw the left-side D-pad for on-foot controls."""
        for key, label, dx, dy, dr in (_DPAD_LEFT, _DPAD_RIGHT, _DPAD_JUMP):
            active = key in pressed
            alpha = _ALPHA_PRESSED if active else _ALPHA
            pad = pygame.Surface((dr * 2 + 4, dr * 2 + 4), pygame.SRCALPHA)
            col = (255, 210, 100, alpha) if active else (180, 200, 220, alpha)
            pygame.draw.circle(pad, col, (dr + 2, dr + 2), dr)
            pygame.draw.circle(pad, (220, 230, 240, min(255, alpha + 30)), (dr + 2, dr + 2), dr, 2)
            surf.blit(pad, (dx - dr - 2, dy - dr - 2))
            from .text import text as draw_text
            draw_text(surf, label, (dx, dy), 18,
                      (40, 30, 20) if active else (220, 230, 245),
                      anchor="center", bold=active)

