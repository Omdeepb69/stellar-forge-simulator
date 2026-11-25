"""1D value noise + fractal sums for terrain and parallax mountains."""
from __future__ import annotations

from .rng import int_hash


def _smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def value_noise(x: float, seed: int) -> float:
    """Smooth noise in [-1, 1]."""
    xi = int(x // 1)
    t = _smooth(x - xi)
    a = int_hash(xi, seed)
    b = int_hash(xi + 1, seed)
    return (a + (b - a) * t) * 2 - 1


def fbm(x: float, seed: int, octaves: int = 4, lacunarity: float = 2.0, gain: float = 0.5) -> float:
    amp, freq, total, norm = 1.0, 1.0, 0.0, 0.0
    for i in range(octaves):
        total += value_noise(x * freq, seed + i * 1013) * amp
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm


def ridged(x: float, seed: int, octaves: int = 3) -> float:
    """Sharp mountain-like noise in [0, 1]."""
    amp, freq, total, norm = 1.0, 1.0, 0.0, 0.0
    for i in range(octaves):
        n = 1 - abs(value_noise(x * freq, seed + i * 7919))
        total += n * n * amp
        norm += amp
        amp *= 0.5
        freq *= 2.1
    return total / norm
