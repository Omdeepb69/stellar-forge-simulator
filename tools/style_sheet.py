"""Builds the style-approval sheets:

1. ``compare.png``  new sprites next to the originals at 4x zoom
2. ``planet.png``   an in-game mock of a planet surface at real game scale
3. ``space_ui.png`` a pixel planet in space plus the new interface pieces

    python tools/style_sheet.py [output_dir] [art_scale]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame  # noqa: E402
import style_sample  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"


def load(p):
    return pygame.image.load(str(A / p)).convert_alpha()


def crop(img):
    return img.subsurface(img.get_bounding_rect()).copy()


def scaled(img, k):
    img = crop(img)
    return pygame.transform.scale(img, (round(img.get_width() * k), round(img.get_height() * k)))


def sheet_compare(new, out):
    """Top: originals. Middle: new sprites at the same zoom. Bottom: everything
    standing on one baseline at game scale, so proportions can be judged."""
    from stellar_forge.ui import pixelfont
    k = 3
    s = pygame.Surface((1500, 980))
    s.fill((70, 72, 92))
    pixelfont.draw(s, "ORIGINAL SPRITES", (14, 10), 3, (255, 214, 90))
    x = 14
    for p in ("player/mainCharStill.png", "alien/alien.png", "desert/cactus2.png", "desert/rock2.png",
              "forest/Tree3.png", "stronghold/device.png", "icy/igloo.png"):
        im = scaled(load(p), k)
        s.blit(im, (x, 44))
        x += im.get_width() + 22
    pixelfont.draw(s, "NEW SPRITES  (matte, many hues, same intensity)", (14, 300), 3, (255, 214, 90))
    x = 14
    for name in ("crawler", "mushroom", "bush", "crystals", "basalt_rock", "vey", "planet"):
        im = scaled(new[name], k)
        s.blit(im, (x, 336))
        x += im.get_width() + 22
    pixelfont.draw(s, "PROPORTIONS  (all at the same pixel scale, standing on one line)", (14, 560), 3,
                   (255, 214, 90))
    base = 960
    x = 14
    for item in ("player/mainCharStill.png", "crawler", "mushroom", "bush", "crystals", "basalt_rock",
                 "alien/alien.png", "giant_fungus", "forest/Tree3.png", "shrine"):
        img = load(item) if "/" in item else new[item]
        im = scaled(img, 2.4)
        s.blit(im, im.get_rect(bottomleft=(x, base)))
        x += im.get_width() + 14
    pygame.draw.line(s, (255, 214, 90), (0, base), (1500, base), 2)
    pygame.image.save(s, str(out))


def sheet_underground(new, out):
    s = pygame.Surface((1280, 520))
    ug = pygame.transform.scale(new["underground"], (480, 360))
    fr = pygame.transform.scale(new["fringe"], (240, 54))
    for x in range(0, 1280, 480):
        s.blit(ug, (x, 150))
    for x in range(0, 1280, 240):
        s.blit(fr, (x, 110))
    s.fill((150, 190, 120), (0, 0, 1280, 112))
    pygame.image.save(s, str(out))


def main():
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "style"
    out.mkdir(parents=True, exist_ok=True)
    new = style_sample.build()
    sheet_compare(new, out / "compare.png")
    sheet_underground(new, out / "underground.png")
    print("sheets written to", out)


if __name__ == "__main__":
    main()
