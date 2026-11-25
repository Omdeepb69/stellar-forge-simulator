# Stellar Forge art style guide

These rules were measured from the original hand-made sprites in `assets/`. Every new
asset, generated or hand-drawn, must follow them. If something new looks out of place
next to `player/mainCharStill.png`, the tree or the cactus, the asset is wrong.

## 1. Resolution and scale
- Sprites are small paintings. Subjects are **40–78 px tall** (characters, props,
  creatures) on canvases of up to 80×80. Big structures (the pyramid) go up to about
  260 px.
- They are **never smoothed**. Always scale them with nearest-neighbour.
- **On-screen scale is fixed** (`config.ART_SCALE`). Every sprite is drawn at that
  scale, so all pixels on screen are the same size. Never stretch a sprite to a target
  height, and never randomise its size.
- Size differences come from how big the art is drawn: a tree is drawn taller than a
  rock. Scaling one up does not count.

## 2. Colour
- Each material has its **own ramp: 3–5 tones of one hue**, saturated in the middle
  tones, plus one pale highlight. Examples taken from the originals:
  - Pilot blue: `#003B85 → #0B61A5 → #1874C9 → #1691C8` and highlight `#EDFAFA`.
  - Alien green: `#001F04 → #063F0D → #00580B → #09981C` and highlight `#96B49A`.
  - Cactus green: `#06BC13 → #1FD72C → #44E550`.
  - Stone grey: `#4C4646 → #5D5D5D → #787878 → #949494`.
  - Pyramid sand: `#904E17 → #B16B29 → #D38B4A → #E69C5A`.
- **No black outlines.** The darkest tone of the object's own ramp works as a soft rim
  on the shadow side.
- Accents are small, bright spots: cyan eyes, a gold antenna, a yellow lamp.

## 3. Shading
- **Light comes from the top-left.** Forms are *pillow-shaded*: lighter towards the
  upper-left inside of the shape, darker towards the lower-right edge.
- Highlights are **broad soft blobs** or a few brush dabs, not hard geometric shapes.
- Add a little texture: mottling, a few darker strokes (bark lines, rust spots, cactus
  ridges). Never a smooth gradient.
- Edges are slightly soft: about 1 px of partial alpha, as with a painting brush.

## 4. Shapes
- Shapes are organic, rounded and a little wobbly, as if painted by hand. Avoid
  perfect circles, ruler-straight polygons and symmetrical vector shapes.
- Silhouettes are simple and readable: one main mass plus one or two features.

## 5. Interface
- The interface comes from `dialog/mainCharDialogBox.png`:
  - a **black panel**;
  - a thick **coloured frame** (blue for the player and friends, dark green for the
    enemy, gold for rewards);
  - a thin **grey inner line**;
  - the speaker's sprite **overlapping the top-left corner**.
- Text uses the game's own **pixel font** (`ui/pixelfont.py`), always drawn at a whole
  multiple of its size, with a 1 px dark shadow. No anti-aliased system fonts.
- Keep the screen quiet: one compact status bar, at most two messages at a time, and
  no translucent glass panels.

## 6. Pipeline
- New art is painted by `tools/pixelkit.py`. It shapes forms with signed distance
  fields at native resolution, adds hand-like wobble, pillow shading from the
  top-left, quantises to a ramp, adds brush mottling and dark rims in the same hue,
  and gives soft 1 px edges.
- Sample sheets are reviewed **next to the original sprites, at game scale**, before
  any batch of art goes into the game.
