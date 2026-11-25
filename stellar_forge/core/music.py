"""Procedural soundtrack: every track is synthesised with numpy at runtime.

Each track is a seamless loop built from the same small toolkit (warm
detuned pads, soft plucked arpeggios, a sub bass and optional drums) so the
whole game shares one sonic identity. Tracks are rendered on a background
thread and cross-faded on two reserved mixer channels.
"""
from __future__ import annotations

import threading

import numpy as np
import pygame

RATE = 22050


def _note(n: int) -> float:
    """MIDI note number to Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


def _lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    spec *= 1 / (1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def _pad(freqs, dur, rng, bright=0.35):
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.13):
            ff = f * 2 ** (det / 12)
            ph = rng.uniform(0, 6.28)
            saw = 2 * ((t * ff + ph / 6.28) % 1) - 1
            out += saw * bright + np.sin(2 * np.pi * ff * t + ph) * (1 - bright)
    env = np.minimum(1, np.minimum(t / 1.2, (dur - t) / 1.2).clip(0))
    return out * env / (len(freqs) * 3)


def _pluck(f, dur, decay=3.0, harm=0.3):
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    sig = np.sin(2 * np.pi * f * t) + harm * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)
    env = np.exp(-t * decay) * np.minimum(1, t / 0.005)
    return sig * env


def _kick(dur=0.35):
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    f = 45 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 9)


def _noise_hit(dur, decay, cutoff, rng):
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    x = rng.uniform(-1, 1, n)
    x = _lowpass(x, cutoff) if cutoff else x
    return x * np.exp(-t * decay)


def _place(buf, sig, start):
    i = int(start * RATE) % len(buf)
    end = i + len(sig)
    if end <= len(buf):
        buf[i:end] += sig
    else:  # wrap around so loops are seamless
        k = len(buf) - i
        buf[i:] += sig[:k]
        buf[:end - len(buf)] += sig[k:]


def _echo(x, delay, feedback=0.35, taps=3):
    out = x.copy()
    d = int(delay * RATE)
    for k in range(1, taps + 1):
        out += np.roll(x, d * k) * feedback ** k
    return out


# chord = list of MIDI notes; progression of (chord, bars)
TRACKS = {
    "title": dict(bpm=70, prog=[[57, 64, 67, 71, 74], [53, 60, 64, 67, 72], [48, 55, 64, 67, 71], [55, 59, 62, 66, 69]],
                  arp=True, arp_oct=24, bass=True, drums=False, cutoff=2400, seed=1, bright=0.35),
    "space": dict(bpm=64, prog=[[50, 57, 60, 64, 69], [46, 53, 57, 62, 65], [53, 57, 60, 64, 67], [48, 55, 60, 62, 67]],
                  arp=True, arp_oct=24, sparse=True, bass=True, drums=False, cutoff=1800, seed=2, bright=0.25),
    "surface": dict(bpm=84, prog=[[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 55, 59]],
                    arp=True, arp_oct=24, melody=True, bass=True, drums="soft", cutoff=3200, seed=3, bright=0.3),
    "stronghold": dict(bpm=76, prog=[[52, 59, 62, 67], [48, 55, 59, 64], [50, 57, 62, 66], [47, 54, 59, 62]],
                       arp=True, arp_oct=12, sparse=True, bass=True, drums="tick", cutoff=1500, seed=4, bright=0.4),
    "boss": dict(bpm=138, prog=[[50, 57, 62, 65], [46, 53, 58, 62], [48, 55, 60, 64], [45, 52, 57, 61]],
                 arp=True, arp_oct=24, fast=True, bass="drive", drums="full", cutoff=4200, seed=5, bright=0.6),
    "ending": dict(bpm=60, prog=[[48, 55, 60, 64, 67], [43, 50, 59, 62, 67], [45, 52, 60, 64, 69], [41, 48, 57, 60, 65]],
                   arp=True, arp_oct=24, melody=True, bass=True, drums=False, cutoff=2600, seed=6, bright=0.3),
}


def render_track(name: str) -> np.ndarray:
    spec = TRACKS[name]
    rng = np.random.default_rng(spec["seed"])
    beat = 60 / spec["bpm"]
    bar = beat * 4
    bars_per_chord = 2 if spec["bpm"] < 100 else 1
    total = bar * bars_per_chord * len(spec["prog"])
    if spec["bpm"] >= 100:
        total *= 2  # longer loop for fast tracks
    n = int(total * RATE)
    left, right = np.zeros(n), np.zeros(n)
    chord_len = bar * bars_per_chord
    n_chords = int(round(total / chord_len))
    scale = sorted({(p % 12) for ch in spec["prog"] for p in ch})

    for ci in range(n_chords):
        chord = spec["prog"][ci % len(spec["prog"])]
        start = ci * chord_len
        pad = _pad([_note(p) for p in chord], chord_len + 1.0, rng, spec["bright"])
        _place(left, pad * 0.9, start)
        _place(right, np.roll(pad, 300) * 0.9, start)
        # bass
        if spec["bass"] == "drive":
            for k in range(int(chord_len / (beat / 2))):
                s = _pluck(_note(chord[0] - 12), beat / 2, decay=6, harm=0.8) * 0.5
                _place(left, s, start + k * beat / 2)
                _place(right, s, start + k * beat / 2)
        elif spec["bass"]:
            s = _pluck(_note(chord[0] - 12), chord_len, decay=0.9, harm=0.15) * 0.55
            _place(left, s, start)
            _place(right, s, start)
        # arpeggio
        if spec.get("arp"):
            step = beat / (4 if spec.get("fast") else 2)
            notes = [p + spec["arp_oct"] - 12 for p in chord]
            pattern = notes + notes[-2:0:-1]
            for k in range(int(chord_len / step)):
                if spec.get("sparse") and rng.random() < 0.45:
                    continue
                p = pattern[k % len(pattern)]
                s = _pluck(_note(p), step * 3, decay=5 if spec.get("fast") else 2.6) * (0.16 if spec.get("fast") else 0.2)
                pan = 0.5 + 0.35 * np.sin(k * 0.9)
                _place(left, s * (1 - pan) * 1.4, start + k * step)
                _place(right, s * pan * 1.4, start + k * step)
        # simple pentatonic-ish melody on top
        if spec.get("melody"):
            pool = [p for p in range(chord[0] + 24, chord[0] + 40) if p % 12 in scale]
            t0 = start
            while t0 < start + chord_len - beat:
                dur = beat * rng.choice([1, 1, 2, 0.5])
                if rng.random() < 0.7:
                    p = int(rng.choice(pool))
                    s = _pluck(_note(p), dur * 2.5, decay=1.6, harm=0.15) * 0.14
                    _place(left, s, t0)
                    _place(right, s, t0 + 0.012)
                t0 += dur

    # drums
    if spec["drums"]:
        beats = int(total / beat)
        for b in range(beats):
            t0 = b * beat
            if spec["drums"] == "full":
                if b % 2 == 0:
                    k = _kick() * 0.7
                    _place(left, k, t0)
                    _place(right, k, t0)
                else:
                    sn = _noise_hit(0.25, 14, 3500, rng) * 0.35
                    _place(left, sn, t0)
                    _place(right, sn, t0)
                for h in range(2):
                    hh = _noise_hit(0.05, 60, 0, rng) * 0.06
                    _place(left if h else right, hh, t0 + h * beat / 2)
            elif spec["drums"] == "soft":
                if b % 4 == 0:
                    k = _kick() * 0.35
                    _place(left, k, t0)
                    _place(right, k, t0)
                hh = _noise_hit(0.04, 70, 0, rng) * 0.035
                _place(left, hh, t0 + beat / 2)
                _place(right, hh, t0 + beat / 2)
            elif spec["drums"] == "tick":
                hh = _noise_hit(0.03, 90, 0, rng) * 0.05
                _place(left if b % 2 else right, hh, t0)

    left = _echo(_lowpass(left, spec["cutoff"]), beat * 0.75)
    right = _echo(_lowpass(right, spec["cutoff"]), beat * 0.75 + 0.02)
    peak = max(np.abs(left).max(), np.abs(right).max(), 1e-6)
    stereo = np.stack([left, right], axis=1) / peak * 0.8
    return stereo


class Music:
    """Cross-fading jukebox. ``play(name)`` is cheap to call every frame."""

    FADE = 1.6

    def __init__(self, audio):
        self.audio = audio
        self.enabled = audio.enabled
        self.volume = 0.5
        self.current: str | None = None
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._lock = threading.Lock()
        self._pending: set[str] = set()
        self.channels = []
        self.levels = [0.0, 0.0]
        self.targets = [0.0, 0.0]
        self.active = 0
        if self.enabled:
            try:
                pygame.mixer.set_num_channels(max(24, pygame.mixer.get_num_channels()))
                pygame.mixer.set_reserved(2)
                self.channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            except pygame.error:
                self.enabled = False

    def prewarm(self, names) -> None:
        if not self.enabled:
            return
        for n in names:
            self._request(n)

    def _request(self, name: str) -> None:
        with self._lock:
            if name in self.sounds or name in self._pending:
                return
            self._pending.add(name)
        threading.Thread(target=self._build, args=(name,), daemon=True).start()

    def _build(self, name: str) -> None:
        try:
            data = render_track(name)
            ch = self.audio.channels
            pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
            if ch == 1:
                pcm = pcm.mean(axis=1).astype(np.int16)
            snd = pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
            with self._lock:
                self.sounds[name] = snd
        except Exception as exc:  # pragma: no cover - hardware/driver dependent
            print(f"[music] could not build {name}: {exc}")
        finally:
            with self._lock:
                self._pending.discard(name)

    def play(self, name: str | None) -> None:
        if not self.enabled or name == self.current:
            return
        if name is not None and name not in self.sounds:
            self._request(name)
            if self.current is None:
                return  # start once it's ready
        self.current = name
        old = self.active
        self.targets[old] = 0.0
        if name is None or name not in self.sounds:
            return
        self.active = 1 - old
        ch = self.channels[self.active]
        ch.stop()
        ch.set_volume(0.0)
        self.levels[self.active] = 0.0
        ch.play(self.sounds[name], loops=-1)
        self.targets[self.active] = 1.0

    def update(self, dt: float) -> None:
        if not self.enabled:
            return
        # a requested track finished rendering: start it now
        if self.current is not None and self.targets[self.active] == 0.0 and self.current in self.sounds:
            name, self.current = self.current, None
            self.play(name)
        step = dt / self.FADE
        for i, ch in enumerate(self.channels):
            lvl = self.levels[i]
            tgt = self.targets[i]
            lvl = min(tgt, lvl + step) if lvl < tgt else max(tgt, lvl - step)
            self.levels[i] = lvl
            ch.set_volume(lvl * self.volume)
            if lvl <= 0 and tgt <= 0 and ch.get_busy():
                ch.stop()

    def stop(self) -> None:
        self.play(None)
