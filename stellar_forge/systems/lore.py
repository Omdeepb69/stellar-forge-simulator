"""The Archive: thirty lore logs that tell the story behind the story.

Three pools, found in different places:
  architect - inscriptions in strongholds and caves (who built the Forge)
  crew      - logs on derelict ships (how Earth-Prime fell)
  remnant   - datapads dropped by Remnant flagships and Wardens (the enemy)
Together they foreshadow Act III: the Makers are not gone.
"""
from __future__ import annotations

LOGS = {
    # ---------------------------------------------------------------- architect
    "a1": ("architect", "Inscription: The First Seed",
           "We were the Smiths of Anvar. We did not conquer stars. We planted them, and from their light we grew "
           "worlds."),
    "a2": ("architect", "Inscription: The Forge",
           "The Forge takes nothing and gives a world. It must never be turned the other way. Turned the other "
           "way, it takes a world and gives nothing."),
    "a3": ("architect", "Inscription: Three Locks",
           "Sun, Frost and Verdant: three Keys for three temperaments. No single hand may hold the Forge, for no "
           "single heart is wise enough."),
    "a4": ("architect", "Inscription: The Vaults",
           "Let the vaults test memory, not strength. Those who remember the way are those who will remember why."),
    "a5": ("architect", "Inscription: The Heart",
           "The Forge's heart is one crystal grown from five songs. Should it ever break, the songs will scatter "
           "to the worlds that sing them."),
    "a6": ("architect", "Survey Note (cave wall)",
           "Seedbed 4471: a deep world, warm underground. Life began here three times. We stopped counting after "
           "that."),
    "a7": ("architect", "Inscription: On Leaving",
           "We go beyond the last nebula to listen. A Forge that is woken will be heard there. We will know."),
    "a8": ("architect", "Inscription: The Guardians",
           "We left great beasts on the seedworlds, not as wardens but as gardeners. Their anger is our own, "
           "kept for us."),
    "a9": ("architect", "Inscription: Warning",
           "If a world is taken by the Forge, take care what you build in its place. A world remembers."),
    "a10": ("architect", "Inscription: The Signal",
            "When a Forge makes a world again - or is unmade - the bell at the rim will ring. Ring it once more "
            "and we will come home to judge what you have made of yourselves."),
    # ---------------------------------------------------------------- crew
    "c1": ("crew", "Captain's Log, ESV Meridian",
           "Day 212 of the Exodus run. Earth-Prime's sky was green when we left. Kael says the Key is the "
           "find of the century. I don't like how he holds it."),
    "c2": ("crew", "Science Officer's Note",
           "The Sun Key resonates with something far away. Dr. Kael Dravos has stopped sleeping. He calls it "
           "'listening'."),
    "c3": ("crew", "Distress Recording",
           "This is the freighter Sparrow. The sky over Earth-Prime just... folded. Continents are lifting. "
           "Oh god, the oceans are lifting. Anyone receiving..."),
    "c4": ("crew", "Fleet Order 9",
           "All Fleet vessels: scatter. Do not regroup. The Warlord - Dravos - is hunting survivors. Hide "
           "anywhere you can. Haven will take who it can."),
    "c5": ("crew", "Personal Log, Lt. Asha Vey",
           "My brother's ship didn't make the jump. Commander Ithri says grief is a luxury. I'm keeping it "
           "anyway. I'm keeping all of it."),
    "c6": ("crew", "Cryo Bay Manifest",
           "Pilot V. - priority cryo, Aster drop pod. Ship AI 'ORA' paired to the pod. Wake condition: "
           "Forge signature detected nearby."),
    "c7": ("crew", "Engineer's Scrawl",
           "If you're reading this, the hull held longer than I did. The reactor's still warm. Take what you "
           "need. Tell my kid I fixed the coolant leak."),
    "c8": ("crew", "Ark Coordinates (fragment)",
           "...New Dawn ark holding beyond the Veil Nebula, 2,000 survivors in cryo. Do not broadcast. Do NOT "
           "let Dravos..."),
    "c9": ("crew", "Last Entry, ESV Hollow Hymn",
           "We found a ringing in the dark at the edge of the charts. Not a pulsar. A bell. Turning back now."),
    "c10": ("crew", "ORA Diagnostic",
            "Origin of this AI core: unknown. Architecture: non-human. Note from the technician: 'It wrote "
            "half of itself. Do we keep it?' Reply: 'Keep it.'"),
    # ---------------------------------------------------------------- remnant
    "r1": ("remnant", "Remnant Creed",
           "The Forge chose Dravos. The weak call it destruction. We call it pruning."),
    "r2": ("remnant", "Warden Orders",
           "Guard the Shard. Do not touch it. Those who touched it are not with us anymore."),
    "r3": ("remnant", "Intercepted Transmission",
           "The Voyager killed the Warlord with a sword. A SWORD. Who sent a pilot with a sword?"),
    "r4": ("remnant", "Quartermaster's Ledger",
           "Hull plating: short. Morale: shorter. The new recruits keep asking what happens after we get the "
           "Shards. Nobody answers."),
    "r5": ("remnant", "Dravos's Journal (copy)",
           "One Key was enough to unmake a world. Three will remake the galaxy in my image. I hear them "
           "listening, at the rim. Let them watch."),
    "r6": ("remnant", "Deserter's Note",
           "I'm going to Haven. If they shoot me, at least it will be for something I chose."),
    "r7": ("remnant", "Flagship Tactical Memo",
           "The Voyager's ship turns faster than ours. Do not chase. Lay out torpedoes and wait."),
    "r8": ("remnant", "Remnant Star Chart",
           "Marked in red: a structure at the galactic rim labelled only 'THE BELL'. Orders: avoid."),
    "r9": ("remnant", "Lieutenant's Confession",
           "I was at Earth-Prime when it fell. I cheered. I have spent every night since trying to un-hear "
           "myself."),
    "r10": ("remnant", "Final Broadcast",
            "To all Remnant: the Warlord is dead. Whatever we were, we are free now to be something else."),
}

POOLS = {k: [lid for lid, (pool, _t, _b) in LOGS.items() if pool == k] for k in ("architect", "crew", "remnant")}


def next_log(state, pool: str) -> str | None:
    """Give the player the next unread log from a pool (None if exhausted)."""
    for lid in POOLS[pool]:
        if lid not in state.logs:
            state.logs.append(lid)
            return lid
    return None


def announce(game, lid: str | None) -> None:
    if lid is None:
        return
    pool, title, _body = LOGS[lid]
    game.toasts.add(f"Log found: {title}  ({len(game.state.logs)}/{len(LOGS)})", (140, 255, 200), 4, icon=None)
    game.audio.play("discover", 0.5)
    game.hint("logs", "Recovered a data log. Read it any time in the Logbook's Archive tab [B].")
