"""Your career with the Survey Corps: Merit, rank and contracts.

* Merit is earned in Corps battles, by assisting patrols, by contracts and by
  meeting the Kestrel Survey Team. Lifetime Merit sets your rank.
* Each rank unlocks a perk (see RANKS): cheaper services, a faster channel and a
  bigger escort, the strike wing, and a free daily refuel.
* Contracts: one at a time, offered on the hailing channel [C] and on the
  Kestrel team's lander. Bounties, raider-captain hunts and charting runs.
  They pay out the moment they're done - no need to report back.
"""
from __future__ import annotations

import math
import random

from ..world.universe import Universe

RANKS = [  # (lifetime Merit, title, perk unlocked at this rank)
    (0, "Contact", "Access to the Corps channel"),
    (40, "Associate", "Corps services cost 20% less"),
    (120, "Field Agent", "The channel is ready twice as fast, and escorts fly three fighters"),
    (260, "Wing Officer", "Strike wing unlocked: four fighters for a hard fight"),
    (450, "Commander", "One free refuel every day, and Corps patrols fly more often"),
]
CAPTAINS = ["Vex Morrow", "Old Scratch", "Kael the Red", "Mother Rust", "Duke Sallow", "Ines Blackwake",
            "Gutter Jax", "The Widow Fenn"]
DAY = 240.0


def rank(state) -> int:
    k = 0
    for i, (need, _t, _p) in enumerate(RANKS):
        if state.corps_merit_total >= need:
            k = i
    return k


def rank_name(state) -> str:
    return RANKS[rank(state)][1]


def next_rank(state):
    k = rank(state)
    return RANKS[k + 1] if k + 1 < len(RANKS) else None


def earn(game, n: int, floater_pos=None) -> None:
    """Add Merit (spendable and lifetime); announce a promotion."""
    if n <= 0:
        return
    st = game.state
    before = rank(st)
    st.corps_merit += n
    st.corps_merit_total += n
    after = rank(st)
    if after > before:
        _need, title, perk = RANKS[after]
        game.banner.show(f"Promoted: Corps {title}", perk, 4.0)
        game.audio.play("relic", 0.9)
        game.toasts.add(f"Corps rank: {title}", (255, 190, 90), 4, icon="scanner")


# ---------------------------------------------------------------- contracts
def _here(game):
    sp = getattr(game, "_space_scene", None)
    if sp is not None and getattr(sp, "ship", None) is not None:
        return Universe.sector_coords(sp.ship.pos)
    return (0, 0)


def offers(game) -> list[dict]:
    """Three contracts on offer today (they change daily and as you complete them)."""
    st = game.state
    day = int(st.world_time // DAY)
    rng = random.Random(game.universe.seed * 31 + day * 7 + st.stats.get("corps_jobs", 0))
    hx, hy = _here(game)
    out = []
    n = rng.randint(4, 7)
    out.append(dict(kind="bounty", desc=f"Down {n} raiders", need=n, have=0, merit=12 + 3 * n, cr=50 * n))
    for _ in range(20):
        sx, sy = hx + rng.randint(-2, 2), hy + rng.randint(-2, 2)
        if (sx, sy) not in ((0, 0), (hx, hy)):
            break
    name = rng.choice(CAPTAINS)
    out.append(dict(kind="captain", desc=f"Hunt Captain {name}", name=name, sector=[sx, sy], need=1, have=0,
                    merit=40, cr=450))
    out.append(dict(kind="chart", desc="Chart 3 new worlds for the Corps", need=3, have=0, worlds=[],
                    merit=25, cr=280))
    return out


def accept(game, job: dict) -> None:
    game.state.corps_job = dict(job)
    game.toasts.add(f"Corps contract: {job['desc']}", (255, 190, 90), 3.5, icon="scanner")
    game.audio.play("ui", 0.6)


def abandon(game) -> None:
    game.state.corps_job = None
    game.toasts.add("Corps contract abandoned", (200, 200, 200), 2.5)


def progress(game, kind: str, amount: int = 1, planet_id: str | None = None) -> None:
    job = game.state.corps_job
    if not job or job["kind"] != kind:
        return
    if kind == "chart":
        if planet_id is None or planet_id == "0,0:0" or planet_id in job["worlds"] or \
                planet_id in game.state.groups.get("survey", {}).get("planets", []):
            return
        job["worlds"].append(planet_id)
        game.toasts.add(f"World charted for the Corps ({len(job['worlds'])}/{job['need']})", (255, 190, 90), 3,
                        icon="scanner")
    job["have"] = min(job["need"], job["have"] + amount)
    if job["have"] >= job["need"]:
        complete(game)


def complete(game) -> None:
    st = game.state
    job = st.corps_job
    if not job:
        return
    st.corps_job = None
    st.bump("corps_jobs")
    st.earn(job["cr"])
    extra = ""
    if job["kind"] == "captain":
        from .items import roll_mod
        mod = roll_mod(random.Random(game.universe.seed + st.stats.get("corps_jobs", 0) * 13), min_rarity=1,
                       luck=0.15)
        st.mods.append(mod)
        extra = f"  ·  {mod['name']}"
    game.banner.show("Corps contract complete", f"+{job['merit']} Merit  ·  +{job['cr']} cr{extra}", 3.5)
    earn(game, job["merit"])
    game.save()


def objective_line(game) -> str | None:
    job = game.state.corps_job
    if not job:
        return None
    if job["kind"] == "captain":
        hx, hy = _here(game)
        sx, sy = job["sector"]
        if (hx, hy) == (sx, sy):
            return f"Corps: hunt Captain {job['name']} - they're in this sector"
        d = max(abs(sx - hx), abs(sy - hy))
        ang = math.degrees(math.atan2(sy - hy, sx - hx))
        dirs = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]
        return f"Corps: hunt Captain {job['name']} - sector ({sx},{sy}), {d} away {dirs[int(((ang + 22.5) % 360) // 45)]}"
    return f"Corps: {job['desc'].lower()}  {job['have']}/{job['need']}"


def menu(game):
    """(title, body, options) for the contracts board - used by the channel and the lander."""
    st = game.state
    opts = []
    if st.corps_job:
        job = st.corps_job
        opts.append((f"Abandon: {job['desc']}", lambda: abandon(game), "no penalty, no pay"))
    else:
        for job in offers(game):
            opts.append((f"{job['desc']}", (lambda j=job: accept(game, j)), f"{job['merit']} Merit  ·  {job['cr']} cr"
                         + ("  ·  a rare mod" if job["kind"] == "captain" else "")))
    opts.append(("Back", None))
    nxt = next_rank(st)
    body = (f"Rank: {rank_name(st)}  ·  {st.corps_merit_total} lifetime Merit" +
            (f"  ·  {nxt[0] - st.corps_merit_total} to {nxt[1]}" if nxt else "  ·  highest rank") +
            (".  Your contract: " + objective_line(game).split(": ", 1)[1] if st.corps_job else
             ".  One contract at a time - it pays the moment it's done."))
    return "Corps contracts", body, opts


def install(game) -> None:
    """Listen for the things contracts count."""
    def on_kill(**data):
        progress(game, "bounty")

    def on_land(planet_id=None, **_):
        progress(game, "chart", planet_id=planet_id)
    game.events.on("enemy_destroyed", on_kill)
    game.events.on("planet_landed", on_land)
