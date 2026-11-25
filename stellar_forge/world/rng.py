"""Deterministic hashing helpers: the backbone of the infinite universe.

Every generated thing derives its randomness from ``seed_of(world_seed, ...)``
so the same coordinates always rebuild exactly the same content and nothing
but player-made changes ever needs saving.
"""
from __future__ import annotations

import hashlib
import random


def seed_of(*parts) -> int:
    text = "|".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.blake2b(text, digest_size=8).digest(), "little")


def rng_of(*parts) -> random.Random:
    return random.Random(seed_of(*parts))


def hash01(*parts) -> float:
    return (seed_of(*parts) & 0xFFFFFFFF) / 0xFFFFFFFF


def int_hash(x: int, seed: int) -> float:
    """Fast integer hash -> [0, 1). Used by noise in hot loops."""
    h = (x * 374761393 + seed * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / 0x1000000


def int_hash2(x: int, y: int, seed: int) -> float:
    return int_hash(x * 73856093 ^ y * 19349663, seed)
