"""Procedurally synthesised sound effects (no audio files needed).

If the mixer cannot start (headless CI, no sound card) everything
silently becomes a no-op.
"""
from __future__ import annotations

import os

import numpy as np
import pygame

RATE = 22050


def _env(n, attack=0.01, release=0.6):
    t = np.linspace(0, 1, n)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.clip((1 - t) / max(release, 1e-4), 0, 1)
    return a * r


def _tone(freq_start, freq_end, dur, wave="square", noise=0.0, vol=0.4):
    n = int(RATE * dur)
    freqs = np.linspace(freq_start, freq_end, n)
    phase = np.cumsum(freqs) / RATE * 2 * np.pi
    if wave == "square":
        sig = np.sign(np.sin(phase))
    elif wave == "saw":
        sig = 2 * ((phase / (2 * np.pi)) % 1) - 1
    else:
        sig = np.sin(phase)
    if noise:
        sig = sig * (1 - noise) + np.random.uniform(-1, 1, n) * noise
    return sig * _env(n) * vol


class Audio:
    def __init__(self):
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.volume = 0.5
        try:
            self._init_mixer()
            self.channels = pygame.mixer.get_init()[2]
            self._build()
            self.enabled = True
        except Exception as exc:  # pragma: no cover - depends on hardware
            print(f"[audio] disabled: {exc}")

    @staticmethod
    def _init_mixer() -> None:
        cur = pygame.mixer.get_init()
        if cur and cur[0] == RATE:
            return
        if cur:
            pygame.mixer.quit()
        try:
            pygame.mixer.init(RATE, -16, 2, 512)
            return
        except pygame.error:
            if os.environ.get("SDL_AUDIODRIVER"):
                raise
        # Try common Linux/desktop SDL audio backends if the default failed
        last_err: Exception | None = None
        for drv in ("pulseaudio", "pipewire", "alsa", "dsp"):
            os.environ["SDL_AUDIODRIVER"] = drv
            try:
                pygame.mixer.init(RATE, -16, 2, 512)
                return
            except pygame.error as exc:
                last_err = exc
        os.environ.pop("SDL_AUDIODRIVER", None)
        if last_err:
            raise last_err

    def _make(self, data: np.ndarray) -> pygame.mixer.Sound:
        pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
        if self.channels == 2:
            pcm = np.column_stack([pcm, pcm])
        return pygame.sndarray.make_sound(np.ascontiguousarray(pcm))

    def _build(self) -> None:
        np.random.seed(7)
        s = self.sounds
        s["laser"] = self._make(_tone(1400, 380, 0.12, "square", vol=0.18))
        s["enemy_laser"] = self._make(_tone(700, 200, 0.16, "saw", vol=0.15))
        s["explosion"] = self._make(_tone(160, 30, 0.7, "saw", noise=0.85, vol=0.5))
        s["hit"] = self._make(_tone(300, 90, 0.12, "square", noise=0.5, vol=0.3))
        s["pickup"] = self._make(np.concatenate([_tone(660, 660, 0.06, "sine", vol=0.3),
                                                 _tone(990, 990, 0.09, "sine", vol=0.3)]))
        s["jump"] = self._make(_tone(300, 620, 0.12, "square", vol=0.14))
        s["swing"] = self._make(_tone(900, 200, 0.13, "sine", noise=0.6, vol=0.22))
        s["land"] = self._make(_tone(120, 60, 0.25, "sine", noise=0.4, vol=0.35))
        s["ui"] = self._make(_tone(880, 880, 0.05, "square", vol=0.12))
        s["deny"] = self._make(_tone(200, 140, 0.15, "square", vol=0.16))
        s["relic"] = self._make(np.concatenate([_tone(f, f, 0.12, "sine", vol=0.32)
                                                for f in (523, 659, 784, 1046)]))
        s["warp"] = self._make(_tone(80, 1400, 1.0, "saw", noise=0.3, vol=0.3))
        s["alarm"] = self._make(np.concatenate([_tone(880, 880, 0.12, "square", vol=0.12),
                                                _tone(660, 660, 0.12, "square", vol=0.12)]))
        s["discover"] = self._make(np.concatenate([_tone(440, 440, 0.1, "sine", vol=0.25),
                                                   _tone(660, 660, 0.18, "sine", vol=0.25)]))
        thrust = np.random.uniform(-1, 1, RATE) * 0.12
        thrust = np.convolve(thrust, np.ones(30) / 30, mode="same")
        s["thrust"] = self._make(thrust * 3)

    def play(self, name: str, volume: float = 1.0) -> None:
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd:
            snd.set_volume(self.volume * volume)
            snd.play()

    def loop(self, name: str, on: bool, volume: float = 0.5) -> None:
        """Start/stop a looping sound on a dedicated channel."""
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if not snd:
            return
        if on and snd.get_num_channels() == 0:
            snd.set_volume(self.volume * volume)
            snd.play(-1)
        elif not on and snd.get_num_channels():
            snd.stop()

    def stop_all(self) -> None:
        if self.enabled:
            pygame.mixer.stop()
