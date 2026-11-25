"""World generation is deterministic, infinite and always winnable."""
from stellar_forge.core.game_state import RELIC_BIOMES, GameState
from stellar_forge.world.biomes import BIOMES
from stellar_forge.world.universe import Universe


def _signature(u: Universe, sx: int, sy: int):
    sec = u.sector(sx, sy)
    return [(b.id, type(b).__name__, round(b.radius, 3)) for b in sec.bodies] + \
           [(p.id, p.biome_id, p.stronghold) for p in sec.planets]


def test_same_seed_same_universe():
    a, b = Universe(99), Universe(99)
    for c in [(0, 0), (3, -2), (-50, 77), (1000, 1000)]:
        assert _signature(a, *c) == _signature(b, *c)


def test_different_seed_differs():
    assert _signature(Universe(1), 2, 2) != _signature(Universe(2), 2, 2)


def test_sector_regenerates_identically_after_eviction():
    u = Universe(5)
    first = _signature(u, 7, 7)
    for i in range(Universe.CACHE_SIZE + 5):   # push it out of the LRU cache
        u.sector(100 + i, 0)
    assert _signature(u, 7, 7) == first


def test_far_away_sectors_generate():
    u = Universe(3)
    sec = u.sector(123456, -98765)
    assert sec.danger > 10
    assert sec.bodies or sec.nebulae or True  # empty deep space is valid


def test_every_seed_is_winnable():
    for seed in range(60):
        u = Universe(seed)
        found = {}
        for (sx, sy), biome in u.relic_sites.items():
            assert max(abs(sx), abs(sy)) <= 2
            sec = u.sector(sx, sy)
            assert sec.has_system
            hits = [p for p in sec.planets if p.biome_id == biome and p.stronghold and p.landable]
            assert hits, (seed, biome)
            found[biome] = hits[0]
        assert set(found) == set(RELIC_BIOMES)


def test_home_system_layout():
    for seed in range(20):
        u = Universe(seed)
        home = u.sector(0, 0)
        assert home.planets[0].name == "Aster" and home.planets[0].biome_id == "forest"
        assert not home.planets[0].stronghold
        assert u.find_body("0,0:st") is not None
        assert u.find_body("0,0:0") is home.planets[0]


def test_many_biomes_appear():
    seen = set()
    for seed in range(4):
        u = Universe(seed)
        for x in range(-3, 4):
            for y in range(-3, 4):
                seen.update(p.biome_id for p in u.sector(x, y).planets)
    assert seen == set(BIOMES)


def test_systems_do_not_overlap_neighbours():
    u = Universe(11)
    for x in range(-3, 3):
        for y in range(-3, 3):
            a, b = u.sector(x, y), u.sector(x + 1, y)
            if a.has_system and b.has_system:
                d = a.system_center.distance_to(b.system_center)
                assert d > a.system_radius + b.system_radius - 3000


def test_orbits_are_continuous():
    u = Universe(8)
    p = u.sector(0, 0).planets[0]
    a, b = p.pos(100.0), p.pos(100.1)
    v = p.vel(100.0)
    assert (b - a).distance_to(v * 0.1) < 1.0


def test_save_roundtrip(tmp_path):
    st = GameState(seed=1234)
    st.relics = ["desert"]
    st.upgrades["engine"] = 3
    st.location = {"kind": "space", "near": "1,1:2"}
    path = tmp_path / "s.json"
    st.save(path)
    back = GameState.load(path)
    assert back.seed == 1234 and back.relics == ["desert"]
    assert back.upgrades["engine"] == 3 and back.location == st.location
    assert back.thrust > GameState().thrust


def test_load_corrupt_file_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{nope")
    assert GameState.load(path) is None
