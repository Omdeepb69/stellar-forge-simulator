"""Data-driven biome registry.

Adding a new kind of planet = adding one ``Biome`` entry. The surface
scene, planet renderer and generator all read from here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prop:
    sprite: str | None          # asset path, or None for procedural ``kind``
    height: int                 # on-screen height in px
    weight: float = 1.0
    hazard: float = 0.0         # contact damage per second
    kind: str = "sprite"        # sprite | crystal | spire | mushroom
    tint: tuple | None = None
    front: bool = False         # draw in front of the player
    mult: int = 1               # whole-number multiple of config.ART_SCALE (original big canvases use 1)


@dataclass(frozen=True)
class Biome:
    id: str
    name: str
    landable: bool
    sky_top: tuple
    sky_bottom: tuple
    ground: tuple
    ground_dark: tuple
    ground_top: tuple
    mountains: tuple
    planet_palette: tuple       # (dark, mid, light) for the space sprite
    gravity: float = 1.0
    roughness: float = 1.0
    props: tuple = ()
    prop_density: float = 1.0
    far_bg: str | None = None
    stronghold_sprite: str = "desert/cave.png"
    stronghold_height: int = 260
    weather: str | None = None
    liquid: str | None = None   # water | lava | acid
    liquid_level: float = 0.0   # 0..1 of terrain amplitude that floods
    friction: float = 1.0
    creature_tint: tuple = (255, 255, 255)
    ore_color: tuple = (120, 255, 220)
    relic: bool = False
    description: str = ""
    creature_sprites: tuple = ("alien/alien.png", "alien/alien.png")   # (hopper, flyer)
    stronghold_mult: float = 1.0
    fringe: str = ""            # ground-top tile
    soil: str = ""              # seamless underground tile


LIQUIDS = {
    "water": {"color": (60, 130, 220, 150), "damage": 0, "drag": 0.55},
    "lava": {"color": (255, 100, 20, 220), "damage": 45, "drag": 0.35},
    "acid": {"color": (140, 255, 60, 170), "damage": 22, "drag": 0.5},
}


BIOMES: dict[str, Biome] = {b.id: b for b in [
    Biome(
        "desert", "Desert", True,
        sky_top=(250, 150, 80), sky_bottom=(255, 222, 170),
        ground=(222, 178, 108), ground_dark=(140, 96, 54), ground_top=(244, 208, 140),
        mountains=(214, 140, 92), planet_palette=((150, 90, 45), (220, 165, 95), (250, 215, 150)),
        gravity=0.9, roughness=0.8,
        props=(Prop("desert/cactus1.png", 120, 1, 14), Prop("desert/cactus2.png", 130, 1, 14),
               Prop("desert/cactus3.png", 70, 1, 14), Prop("desert/cactus4.png", 140, 0.8, 14),
               Prop("desert/rock1.png", 70, 1.2), Prop("desert/rock2.png", 80, 1)),
        prop_density=0.9, far_bg="desert/desertBackground.png",
        stronghold_sprite="desert/pyramid.png", stronghold_height=360,
        weather="sand", creature_tint=(255, 210, 140), ore_color=(255, 200, 80), relic=True,
        description="Scorched dunes under a blazing sun. Watch the cacti.",
    ),
    Biome(
        "ice", "Frozen", True,
        sky_top=(110, 160, 225), sky_bottom=(225, 242, 255),
        ground=(226, 240, 250), ground_dark=(120, 160, 195), ground_top=(255, 255, 255),
        mountains=(170, 200, 230), planet_palette=((120, 160, 200), (200, 225, 245), (250, 252, 255)),
        gravity=0.75, roughness=1.1, friction=0.25,
        props=(Prop("icy/snowStone1.png", 60, 1), Prop("icy/snowStone2.png", 70, 1),
               Prop("icy/snowStone3.png", 50, 1), Prop("icy/snowman.png", 110, 0.4),
               Prop("generated/props/crystal/cluster2.png", 110, 0.5, tint=(200, 240, 255))),
        far_bg="icy/snowyMountains.png", stronghold_sprite="icy/igloo.png", stronghold_height=220,
        weather="snow", creature_tint=(170, 220, 255), ore_color=(140, 230, 255), relic=True,
        description="Glacial plains. The ground is slick, momentum is king.",
    ),
    Biome(
        "forest", "Verdant", True,
        sky_top=(80, 160, 230), sky_bottom=(205, 238, 255),
        ground=(98, 66, 38), ground_dark=(48, 32, 20), ground_top=(76, 176, 64),
        mountains=(80, 140, 110), planet_palette=((30, 80, 50), (60, 150, 70), (150, 210, 120)),
        gravity=1.0, roughness=1.0,
        props=(Prop("forest/Tree1.png", 260, 1), Prop("forest/Tree2.png", 240, 1),
               Prop("forest/Tree3.png", 230, 0.8), Prop("forest/brokentree.png", 170, 0.5),
               Prop("forest/log.png", 50, 0.6, front=True)),
        prop_density=1.3, far_bg="forest/forestbackground.png",
        stronghold_sprite="forest/cave.png", stronghold_height=300,
        weather="spores", liquid="water", liquid_level=0.18,
        creature_tint=(150, 255, 150), ore_color=(160, 255, 120), relic=True,
        description="Ancient woodland teeming with life - and with things that bite.",
    ),
    Biome(
        "ocean", "Oceanic", True,
        sky_top=(70, 130, 200), sky_bottom=(190, 225, 245),
        ground=(214, 200, 150), ground_dark=(120, 108, 80), ground_top=(232, 222, 170),
        mountains=(110, 150, 180), planet_palette=((20, 50, 120), (40, 110, 200), (200, 220, 170)),
        gravity=0.95, roughness=1.3,
        props=(Prop("forest/Tree3.png", 210, 1), Prop("generated/props/ocean/coral.png", 90, 0.8),
               Prop("generated/props/ocean/shell.png", 40, 0.7, front=True),
               Prop("generated/props/ocean/kelp.png", 120, 0.8), Prop("desert/rock1.png", 60, 0.5)),
        prop_density=0.75, weather="rain", liquid="water", liquid_level=0.55,
        stronghold_sprite="generated/strongholds/ocean.png", stronghold_height=230,
        creature_tint=(255, 170, 140), ore_color=(90, 200, 255),
        creature_sprites=("generated/creatures/crab.png", "generated/creatures/jelly.png"),
        description="Scattered islands in an endless sea. Swim or jetpack between them.",
    ),
    Biome(
        "volcanic", "Volcanic", True,
        sky_top=(50, 12, 12), sky_bottom=(190, 70, 30),
        ground=(62, 44, 44), ground_dark=(24, 14, 14), ground_top=(96, 62, 56),
        mountains=(90, 35, 30), planet_palette=((40, 15, 10), (120, 40, 20), (255, 120, 40)),
        gravity=1.15, roughness=1.4,
        props=(Prop("generated/props/volcanic/basalt.png", 170, 1),
               Prop("generated/props/volcanic/vent.png", 90, 0.8, hazard=10),
               Prop("generated/props/volcanic/obsidian.png", 80, 1),
               Prop("desert/rock2.png", 90, 0.6, tint=(110, 70, 70))),
        weather="ash", liquid="lava", liquid_level=0.3,
        stronghold_sprite="generated/strongholds/volcanic.png", stronghold_height=240,
        creature_tint=(255, 130, 90), ore_color=(255, 90, 40),
        creature_sprites=("generated/creatures/beetle.png", "alien/alien.png"),
        description="Rivers of magma. Rich in ore, poor in mercy.",
    ),
    Biome(
        "toxic", "Toxic", True,
        sky_top=(50, 80, 30), sky_bottom=(170, 200, 90),
        ground=(84, 90, 58), ground_dark=(36, 44, 26), ground_top=(150, 200, 60),
        mountains=(90, 120, 60), planet_palette=((50, 70, 20), (120, 160, 40), (210, 240, 110)),
        gravity=1.05, roughness=1.1,
        props=(Prop("forest/brokentree.png", 160, 0.7, tint=(150, 200, 110)),
               Prop("generated/props/toxic/shroom1.png", 150, 1.2),
               Prop("generated/props/toxic/shroom2.png", 110, 1.0),
               Prop("generated/props/toxic/pod.png", 60, 0.8, hazard=8, front=True)),
        weather="spores", liquid="acid", liquid_level=0.28,
        stronghold_sprite="generated/strongholds/toxic.png", stronghold_height=220,
        creature_tint=(200, 255, 90), ore_color=(220, 255, 60),
        creature_sprites=("generated/creatures/beetle.png", "generated/creatures/jelly.png"),
        description="Caustic swamps and giant fungi. Don't swim.",
    ),
    Biome(
        "crystal", "Crystalline", True,
        sky_top=(30, 14, 70), sky_bottom=(140, 90, 210),
        ground=(70, 60, 112), ground_dark=(32, 28, 58), ground_top=(176, 146, 255),
        mountains=(90, 70, 150), planet_palette=((50, 30, 90), (120, 80, 200), (220, 180, 255)),
        gravity=0.6, roughness=1.5,
        props=(Prop("generated/props/crystal/cluster1.png", 150, 1.3),
               Prop("generated/props/crystal/cluster2.png", 120, 1.0),
               Prop("generated/props/crystal/cluster3.png", 100, 0.8),
               Prop("generated/props/crystal/geode.png", 70, 0.7)),
        weather="sparkle", creature_tint=(220, 170, 255), ore_color=(255, 140, 255),
        stronghold_sprite="generated/strongholds/crystal.png", stronghold_height=300,
        creature_sprites=("generated/creatures/beetle.png", "generated/creatures/jelly.png"),
        description="Singing crystal fields in low gravity. Jump high.",
    ),
    Biome(
        "barren", "Barren", True,
        sky_top=(6, 6, 16), sky_bottom=(40, 40, 60),
        ground=(130, 126, 120), ground_dark=(66, 64, 62), ground_top=(165, 160, 152),
        mountains=(70, 70, 80), planet_palette=((70, 68, 66), (130, 126, 120), (190, 186, 180)),
        gravity=0.45, roughness=0.9,
        props=(Prop("generated/props/barren/boulder.png", 70, 1),
               Prop("generated/props/barren/crater_rock.png", 60, 1),
               Prop("generated/props/barren/antenna.png", 130, 0.25),
               Prop("desert/rock2.png", 80, 0.6, tint=(150, 150, 150))),
        prop_density=0.6, creature_tint=(210, 210, 220), ore_color=(200, 255, 255),
        stronghold_sprite="generated/strongholds/barren.png", stronghold_height=150,
        creature_sprites=("generated/creatures/crab.png", "alien/alien.png"),
        description="An airless rock. Low gravity, long jumps, rich ore.",
    ),
    Biome(
        "gas", "Gas Giant", False,
        sky_top=(0, 0, 0), sky_bottom=(0, 0, 0),
        ground=(0, 0, 0), ground_dark=(0, 0, 0), ground_top=(0, 0, 0), mountains=(0, 0, 0),
        planet_palette=((120, 80, 50), (200, 150, 100), (240, 220, 180)),
        description="No solid surface. Its gravity makes a fine slingshot.",
    ),
]}


# ---------------------------------------------------------------------------------------------
# Art pass (docs/ART_STYLE.md): every biome uses painted props at true proportions,
# its own ground tiles, creatures and stronghold. Heights here are only used for hazards;
# sprites are always drawn at config.ART_SCALE.
def _p(path, w=1.0, hazard=0.0, front=False, mult=1):
    return Prop(path, 0, w, hazard, "sprite", None, front, mult)


G = "generated/"
_ART = {
    "desert": dict(props=(_p(G + "props/desert/cactus1.png", 1, 14), _p(G + "props/desert/cactus2.png", 1, 14),
                          _p(G + "props/desert/cactus3.png", 1, 14), _p(G + "props/desert/cactus4.png", 0.8, 14),
                          _p("desert/rock1.png", 1.2), _p("desert/rock2.png", 1),
                          _p(G + "props/desert/dune_grass.png", 1.4, front=True), _p(G + "props/desert/bush.png", 0.6)),
                   stronghold_mult=0.5, creature_sprites=("alien/alien.png", "alien/alien.png")),
    "ice": dict(props=(_p("icy/snowStone1.png"), _p("icy/snowStone2.png"), _p("icy/snowStone3.png"),
                       _p("icy/snowman.png", 0.3), _p(G + "props/ice/pine.png", 1.2), _p(G + "props/ice/spikes.png", 0.8),
                       _p(G + "props/ice/snow_rock.png", 0.8))),
    "forest": dict(props=(_p("forest/Tree1.png", 0.7), _p("forest/Tree2.png", 0.7), _p("forest/Tree3.png", 0.5),
                          _p(G + "props/forest/tall_tree1.png", 1.2), _p(G + "props/forest/tall_tree2.png", 1.0),
                          _p("forest/brokentree.png", 0.4), _p("forest/log.png", 0.5, front=True),
                          _p(G + "props/forest/bush.png", 1.0), _p(G + "props/forest/mushroom.png", 0.6))),
    "ocean": dict(props=(_p("forest/Tree3.png", 1), _p(G + "props/ocean/coral.png", 0.8),
                         _p(G + "props/ocean/shell.png", 0.8, front=True), _p(G + "props/ocean/kelp.png", 0.8),
                         _p("desert/rock1.png", 0.4)),
                  stronghold_sprite=G + "strongholds/ocean.png",
                  creature_sprites=(G + "creatures/ocean_hopper.png", G + "creatures/ocean_flyer.png")),
    "volcanic": dict(props=(_p(G + "props/volcanic/basalt.png", 1), _p(G + "props/volcanic/vent.png", 0.7, 10),
                            _p(G + "props/volcanic/obsidian.png", 1), _p(G + "props/volcanic/charred_tree.png", 0.7)),
                     stronghold_sprite=G + "strongholds/volcanic.png",
                     creature_sprites=(G + "creatures/volcanic_hopper.png", G + "creatures/volcanic_flyer.png")),
    "toxic": dict(props=(_p(G + "props/toxic/giant_fungus.png", 0.6), _p(G + "props/toxic/shroom1.png", 1.2),
                         _p(G + "props/toxic/shroom2.png", 1.0), _p(G + "props/toxic/pod.png", 0.7, 8, front=True),
                         _p(G + "props/toxic/bush.png", 0.8), _p("forest/brokentree.png", 0.4)),
                  stronghold_sprite=G + "strongholds/toxic.png",
                  creature_sprites=(G + "creatures/toxic_hopper.png", G + "creatures/toxic_flyer.png")),
    "crystal": dict(props=(_p(G + "props/crystal/cluster1.png", 1.2), _p(G + "props/crystal/cluster2.png", 0.8),
                           _p(G + "props/crystal/cluster3.png", 1.0), _p(G + "props/crystal/geode.png", 0.6)),
                    stronghold_sprite=G + "strongholds/crystal.png",
                    creature_sprites=(G + "creatures/crystal_hopper.png", G + "creatures/crystal_flyer.png")),
    "barren": dict(props=(_p(G + "props/barren/boulder.png", 1), _p(G + "props/barren/crater_rock.png", 1),
                          _p(G + "props/barren/antenna.png", 0.25)),
                   stronghold_sprite=G + "strongholds/barren.png",
                   creature_sprites=(G + "creatures/barren_hopper.png", G + "creatures/barren_flyer.png")),
}
for _bid, _over in _ART.items():
    _over.setdefault("fringe", f"{G}terrain/{_bid}/fringe.png")
    _over.setdefault("soil", f"{G}terrain/{_bid}/underground.png")
    if _bid not in ("desert", "ice", "forest"):
        _over.setdefault("far_bg", f"{G}terrain/{_bid}/backdrop.png")
    from dataclasses import replace as _replace
    BIOMES[_bid] = _replace(BIOMES[_bid], **_over)


def choose_biome(temperature: float, size: float, rng) -> str:
    """Pick a biome from physical properties.

    temperature: ~0 (frozen) .. 1 (scorching); size: 0..1 relative radius.
    """
    if size > 0.72 and rng.random() < 0.7:
        return "gas"
    if size < 0.18:
        return "barren" if rng.random() < 0.7 else "ice"
    table = []
    if temperature > 0.75:
        table = [("volcanic", 3), ("desert", 4), ("barren", 1)]
    elif temperature > 0.55:
        table = [("desert", 4), ("toxic", 2), ("forest", 2), ("volcanic", 1)]
    elif temperature > 0.38:
        table = [("forest", 4), ("ocean", 3), ("toxic", 1.5), ("desert", 1)]
    elif temperature > 0.2:
        table = [("ice", 3), ("crystal", 2), ("forest", 1), ("ocean", 1), ("barren", 1)]
    else:
        table = [("ice", 4), ("crystal", 2), ("barren", 2)]
    total = sum(w for _, w in table)
    r = rng.random() * total
    for name, w in table:
        r -= w
        if r <= 0:
            return name
    return table[-1][0]
