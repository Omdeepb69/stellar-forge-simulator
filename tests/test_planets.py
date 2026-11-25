"""Planet gameplay: points of interest, settler jobs, materials and cave dungeons."""
import pygame
from conftest import key, run
from test_expansion import _find, _invulnerable, _land_on

from stellar_forge.core.game_state import GameState
from stellar_forge.systems import materials as M
from stellar_forge.systems import poi as P


def _home(game):
    return game.universe.find_body("0,0:0")


def _stand(scene, x):
    scene.pilot.x = x
    scene.pilot.y = scene.terrain.height(x)
    scene.pilot.vx = scene.pilot.vy = 0


def test_pois_are_deterministic_and_home_has_a_camp(game):
    s = _land_on(game, _home(game))
    kinds = [p["kind"] for p in s.terrain.pois]
    assert "camp" in kinds and kinds.count("vein") == 2
    again = [(p["kind"], p["x"]) for p in s.terrain.__class__(s.planet, s.planet.seed).pois]
    assert again == [(p["kind"], p["x"]) for p in s.terrain.pois]
    xs = sorted([0] + [p["x"] for p in s.terrain.pois])
    assert all(b - a > 1000 for a, b in zip(xs, xs[1:]))      # never piled on each other


def test_settler_hunt_job(game, monkeypatch):
    _invulnerable(monkeypatch)
    s = _land_on(game, _home(game))
    camp = next(p for p in s.terrain.pois if p["kind"] == "camp")
    _stand(s, s.pois._camp_parts(camp)["settler"])
    run(game, 0.1)
    run(game, 0.1, [key(pygame.K_e)])
    q = game.state.poi_state[camp["id"]]["quest"]
    assert q["kind"] == "hunt" and q["stage"] == "active"
    assert P.SP.short(q["name"]) in P.objective_line(game)
    for _ in range(q["need"]):
        P.on_kill(game, s.planet)
    game.dialogue.queue.clear()
    cr = game.state.credits
    run(game, 0.1, [key(pygame.K_e)])
    assert game.state.credits > cr and game.state.materials.get("forest", 0) >= 5
    nxt = game.state.poi_state[camp["id"]]["quest"]            # the settler has a follow-up job
    assert nxt["round"] == 1 and nxt["stage"] == "new" and nxt["name"] == q["name"]
    assert not P.done(game, camp["id"])


def test_camp_job_chain_finishes(game):
    s = _land_on(game, _home(game))
    camp = next(p for p in s.terrain.pois if p["kind"] == "camp")
    kinds = []
    for _ in range(P.CAMP_JOBS):
        q = P.quest(game, s.planet, camp)
        P.talk(game, s.planet, camp, s)                         # accept
        assert q["stage"] == "active"
        kinds.append(q["kind"])
        if q["kind"] == "gather":
            game.state.materials[q["mat"]] = q["need"]
        else:
            q["have"] = q["need"]
        P.talk(game, s.planet, camp, s)                         # hand in
    assert P.done(game, camp["id"]) and P.jobs_done(game, camp["id"]) == P.CAMP_JOBS
    assert all(a != b for a, b in zip(kinds, kinds[1:])) and kinds.count("fetch") <= 1


def test_gather_job_consumes_materials(game):
    s = _land_on(game, _home(game))
    camp = next(p for p in s.terrain.pois if p["kind"] == "camp")
    q = P.quest(game, s.planet, camp)
    q.update(kind="gather", mat="desert", need=3, stage="active")
    game.state.materials["desert"] = 4
    P.talk(game, s.planet, camp, s)
    assert P.jobs_done(game, camp["id"]) == 1 and game.state.materials["desert"] == 1


def test_vein_mines_out(game, monkeypatch):
    _invulnerable(monkeypatch)
    s = _land_on(game, _home(game))
    vein = next(p for p in s.terrain.pois if p["kind"] == "vein")
    _stand(s, vein["x"])
    for _ in range(P.VEIN_HITS):
        run(game, 0.1, [key(pygame.K_e)])
        run(game, 0.4)
    assert P.done(game, vein["id"])
    assert game.state.materials["forest"] >= 6


def test_ruin_puzzle_order(game, monkeypatch):
    _invulnerable(monkeypatch)
    pl = _find(game, lambda b: b.kind == "planet" and b.biome_id in M.MATERIALS and not b.is_moon
               and any(p["kind"] == "ruin" for p in __import__("stellar_forge.surface.terrain", fromlist=["x"])
                       .Terrain(b, b.seed).pois))
    s = _land_on(game, pl)
    ruin = next(p for p in s.terrain.pois if p["kind"] == "ruin")
    wrong = next(i for i in range(4) if i != ruin["order"][0])
    s.pois._pillar(ruin, wrong)
    assert s.pois.seq.get(ruin["id"]) == [] and any(k.startswith("guard:") for k in s.creatures)
    s.pois._pillar(ruin, ruin["order"][0])
    assert game.state.poi_state[ruin["id"]]["seq"] == [ruin["order"][0]]   # saved, not scene-local
    s.pois.seq[ruin["id"]] = []
    mods = len(game.state.mods)
    for i in ruin["order"]:
        s.pois._pillar(ruin, i)
    assert P.done(game, ruin["id"]) and len(game.state.mods) == mods + 1


def test_upgrades_need_materials(game):
    st = game.state
    assert st.upgrade_mats("engine") == {}                  # level 1: credits only
    st.upgrades["engine"] = 2
    need = st.upgrade_mats("engine")
    assert need == {"volcanic": 6, "desert": 2}
    assert not M.take(st, need)
    st.materials.update(volcanic=6, desert=5)
    assert M.take(st, need) and st.materials == {"volcanic": 0, "desert": 3}


def test_cave_dungeon_vault(game, monkeypatch):
    _invulnerable(monkeypatch)
    pl = _find(game, lambda b: b.kind == "planet" and b.cave and b.biome_id in M.MATERIALS)
    s = _land_on(game, pl)
    _stand(s, s.terrain.cave_x)
    run(game, 0.2)
    run(game, 0.8, [key(pygame.K_e)])
    cave = game.scenes.top
    game.dialogue.queue.clear()
    t = cave.terrain
    _stand(cave, t.end + 900)                    # can't leave through the far wall
    run(game, 0.1)
    assert cave.pilot.x <= t.end + 40
    _stand(cave, t.vault_x)
    run(game, 0.1, [key(pygame.K_e)])
    assert pl.id not in game.state.caves_cleared   # sockets empty
    for sx in t.sigils:
        _stand(cave, sx)
        run(game, 0.15)
    assert cave.sigils_held() == 3
    _stand(cave, t.vault_x)
    run(game, 0.1, [key(pygame.K_e)])
    assert pl.id in game.state.caves_cleared and game.state.stats["vaults"] == 1


def test_new_fields_round_trip(tmp_path):
    st = GameState(seed=5)
    st.materials = {"ice": 3}
    st.poi_state = {"x:poi:0": {"done": True}}
    st.caves_cleared = ["x"]
    st.save(tmp_path / "s.json")
    back = GameState.load(tmp_path / "s.json")
    assert back.materials == {"ice": 3} and back.poi_state["x:poi:0"]["done"] and back.caves_cleared == ["x"]
