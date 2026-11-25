"""Rebuild every generated asset in the house style (docs/ART_STYLE.md).

    python tools/build_art.py

Writes assets/generated/** (world, bosses, ships, items, portraits, icons) and
assets/ui/** (the Console interface kit). The output is committed, so the game
never runs this itself.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pygame  # noqa: E402

ROOT = HERE.parent


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    gen = ROOT / "assets" / "generated"
    if gen.exists():            # start clean: no leftovers from the old vector-style art
        shutil.rmtree(gen)
    import ui_kit
    from art import logo, npc, poi, things, world
    ui_kit.build()
    n = len(world.build_all()) + len(npc.build_all()) + len(poi.build_all()) + len(things.build_all())
    n += len(logo.build_all())
    print(f"painted {n} world/object sprites + the UI kit -> {gen}")


if __name__ == "__main__":
    main()
