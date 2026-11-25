"""The peoples you meet in camps out on the frontier worlds.

Far-future settlers are rarely human any more. Each species has its own look
(painted in tools/art/npc.py, same index), naming style and voice.
"""
from __future__ import annotations

import random

SPECIES = [
    dict(key="lumen", label="Lumen", float=True,
         names=["Ilu-Ve", "Soshé", "Nhae", "Lir-of-the-Fourth-Current", "Aumi", "Vesh-Lo"],
         greet="*the jelly inside the dome glows brighter* Oh - a visitor. The currents said someone would come.",
         chatter=["I brought my ocean with me. It's in the dome. It's a very small ocean.",
                  "When I'm happy I glow pink. When I'm hungry I also glow pink. It's confusing for everyone.",
                  "Your kind has bones? All the time? That sounds exhausting.",
                  "The dome fogs up when I laugh. Please don't be funny.",
                  "I drifted between stars for eleven years to get here. The view was mostly black."]),
    dict(key="mossback", label="Mossback", float=False,
         names=["Old Grummet", "Basalt-Who-Waits", "Tor", "Mother Lichen", "Slowstep", "Granitha"],
         greet="Hrrm. ...Hrrm. A small fast one. Sit, if you like. I have been sitting for ninety years.",
         chatter=["The sapling on my back is my granddaughter. Or a tree. We are still deciding.",
                  "You walk so quickly. Where does it get you? Hrrm. Here, apparently.",
                  "I remember when this hill was a mountain. It was rude then, too.",
                  "Moss grows on the north side of me. I have used this to get lost many times.",
                  "Hrrm. Hrrm. ...Sorry. I was thinking. It takes a while."]),
    dict(key="tik", label="Tik", float=False,
         names=["Tik-7", "Rivet", "Sprocket-Nine", "Unit Hum", "Clank Prime", "Wrenna"],
         greet="*whirr-click* HELLO ORGANIC. Wait - you are also a robot? HELLO COUSIN. *happy beeping*",
         chatter=["I collect bolts. I have 4,112 bolts. I am looking for bolt 4,113.",
                  "My previous owner went to the stars. I went to the junkyard. I like the junkyard better.",
                  "Do not touch the red wire. I do not know what the red wire does. Nobody touches the red wire.",
                  "*click* Scanning you... you are 87% cool. Very good score.",
                  "My stilts were spaghetti tongs once. Now they are legs. Everything can be legs."]),
    dict(key="sporeling", label="Sporeling", float=False,
         names=["Puffa", "Morel", "Little Cap", "Gill", "Brim", "Old Fairyring"],
         greet="*poof* Oh! Sorry, spores. I do that when I'm nervous. Hello! Hello hello.",
         chatter=["We're all one big root network under here. I can hear my cousin three hills away. She says hi.",
                  "Don't worry, the spores are friendly. Mostly. Don't breathe through your nose.",
                  "I was planted here as a joke. Now look at me. A whole person.",
                  "Rain is the best day. Rain is a party. You should see us when it rains.",
                  "*poof* ...That one was a sneeze."]),
    dict(key="shardkin", label="Shardkin", float=True,
         names=["Ka'reth", "Prism-of-Nine-Faces", "Vell", "Quartzine", "Lumi-Facet", "Edge"],
         greet="*chiming* You are refracting oddly, traveller. Come closer. Let me see your colours.",
         chatter=["My head floats because it doesn't trust my body. They had a disagreement in 3200.",
                  "We grow one facet per century. I am rather young. Barely twelve faces.",
                  "Your light is warm. Most visitors are... blue. Sad blue.",
                  "If I shatter, gather the pieces and plant them. I'll be back in a few hundred years.",
                  "*soft chime* That was a laugh. We laugh in A-flat."]),
    dict(key="hollow", label="Hollow", float=True,
         names=["The Lanternkeeper", "Nobody-in-Particular", "Wick", "Hush", "The Quiet One", "Sable"],
         greet="...You can see me? Few can. Sit by the fire, small light. I have kept it burning for you.",
         chatter=["Inside my hood is a sky that ended long ago. I keep it so it isn't lonely.",
                  "I do not have a face. I have a view. It's better.",
                  "The lantern holds the last ember of my home star. Please do not blow on it.",
                  "I walk between worlds. Mostly I walk between this tent and that rock.",
                  "Stars die. Stories don't. Tell me one before you go."]),
    dict(key="gillwright", label="Gillwright", float=False,
         names=["Bloop", "Captain Wetherby", "Sallie Mander", "Glub-Ka", "Fen", "Axel"],
         greet="*bubbles* Ahoy! Ha - forgive the bowl. Dry air makes my gills itchy. Welcome to camp!",
         chatter=["I change the water in my helmet every Tuesday. Today is not Tuesday. You can tell.",
                  "If I lose a hand, it grows back. I've lost this one six times. Same hand. Clumsy.",
                  "Back home I was a deep-sea welder. Out here I'm a shallow-sea everything.",
                  "Don't mind the smile. It's just how my face is. I'm also smiling inside.",
                  "*bubble* *bubble* ...sorry, hiccups. Happens when I'm excited."]),
    dict(key="echo", label="Echo", float=False,
         names=["ECHO-Mira", "Professor Lattice", "Remnant-of-Ada", "Vox", "Kestrel.bak", "Dr. Halloway (copy 3)"],
         greet="*hologram flickers on* Ah, a visitor! Forgive the jar - I uploaded in a hurry. The legs were on sale.",
         chatter=["I used to have a body. Then I had a better idea. Then the idea needed legs.",
                  "There are four of me running right now. I'm the friendly one. Allegedly.",
                  "Please don't shake the jar. It took me ages to get the bubbles just right.",
                  "I remember Earth. Well - I remember a file about Earth. Same thing, honestly.",
                  "My face is a projection. So is yours, if you think about it. Don't think about it."]),
]
# ---------------------------------------------------------------- natives: two per kind of world
def _n(key, label, home, names, greet, chatter, float_=False):
    return dict(key=key, label=label, home=home, float=float_, names=names, greet=greet, chatter=chatter)


SPECIES += [
    _n("barkling", "Barkling", "forest", ["Oakum", "Little Burl", "Grandmother Knot", "Sap", "Rowan-Who-Leans", "Bough"],
       "*creak* Oh! You startled my leaves. Welcome, welcome - mind the roots, they're mine.",
       ["We plant our children. Then we wait. Then we wait some more. Then: children!",
        "If you hear creaking at night, that's just us stretching. Probably.",
        "Fire is a rude word here. Please don't say it. Ah. You didn't. Good."]),
    _n("mothkin", "Mothkin", "forest", ["Dusk", "Lantern-Lover", "Velvet", "Pale Wing", "Hush-Hush", "Nocta"],
       "*flutter* Ooh, your eyes glow! Can I sit near them? Just for a moment? They're so lovely.",
       ["Don't leave a light on near me. I can't be held responsible.",
        "Our wings are full of dust. The dust is full of stories. Sneeze and you'll learn something.",
        "Daytime is for sleeping upside down. You do that too, right? No?"]),
    _n("dunestrider", "Dunestrider", "desert", ["Sirocco", "Old Shell", "Kessa Sandstep", "Duna", "Mirage-Eater", "Haboob"],
       "*sniff sniff* You smell of starship and ozone. Hah! Sit in the shade, wanderer. The sand can wait.",
       ["When the storm comes, we roll up and let it pass. Recommend it. Very relaxing.",
        "These goggles were my grandmother's. And her grandmother's. Same scratches.",
        "Water is money out here. Want to hear about the time I was rich? Rained once."]),
    _n("cactling", "Cactling", "desert", ["Prickle", "Bloom", "Mister Spines", "Agave", "Saguara", "Needle"],
       "Hi hi hi! Don't hug me! Everybody wants to hug me. Don't. Hi!",
       ["I flower once a year! It's next Tuesday! You should come!",
        "I drink once a month. Today is not the day. Please stop offering.",
        "The spines are for protection. Also fashion. Mostly fashion."]),
    _n("frostmane", "Frostmane", "ice", ["Big Bergo", "Whiteout", "Hoarfrost", "Old Tusky", "Flurry", "Mum Glacier"],
       "HRAWR! ...Ha ha, sorry. We say hello loudly here. The wind eats quiet words.",
       ["My fur has three layers. The bottom layer has never seen the sun. It's shy.",
        "Snowball fight? No? Shame. I'm undefeated. Mostly because nobody accepts.",
        "We don't hibernate. We 'rest our eyes'. For four months. Different thing."]),
    _n("tuxar", "Tuxar", "ice", ["Pip", "Admiral Waddle", "Slide", "Neve", "Captain Flipper", "Brr"],
       "*waddle waddle* Ahoy-hoy! Mind the ice - I've slid down this hill eleven times today. Twelve!",
       ["My aunt knitted this scarf. And the hat. And the other scarf under this scarf.",
        "Belly sliding is the fastest way to travel. I've done the maths. On my belly.",
        "We huddle when it's cold. It's always cold. We're always huddling. It's lovely."]),
    _n("emberkin", "Emberkin", "volcanic", ["Cinder", "Spark", "Old Magma", "Flicker", "Pyra", "Ashwick"],
       "*crackle* Oh! Don't stand too close - unless you're cold? Then stand close. I'm very warm.",
       ["When I'm angry I go blue. Very hot blue. Try not to make me angry. I like orange.",
        "Rain is the worst. Rain is our ghost story.",
        "I cook breakfast by thinking about it. It's efficient, but everything's a bit charred."]),
    _n("salamandrite", "Salamandrite", "volcanic", ["Scorchtail", "Vessa", "Igni", "Old Crest", "Brand", "Kiln"],
       "Hsss - welcome, warm-blood. Well. Lukewarm-blood. Come, the lava's lovely this time of year.",
       ["I swim in the lava flows. Builds character. And scales.",
        "This plate was forged in the Great Vent. It's also where I dropped my lunch. Twice.",
        "When my tail falls off, it grows back. When yours does... oh. It doesn't? Sorry."]),
    _n("geodite", "Geodite", "crystal", ["Druze", "Agate", "Little Vug", "Amethea", "Crack", "Old Nodule"],
       "*clack* Hello, outside-person! Yes, I'm the shiny one inside. The rock is just my coat.",
       ["We grow crystals inside. It tickles. You get used to it after a few centuries.",
        "Please don't crack me open to look. It's rude. Ask nicely and I'll show you.",
        "Rolling is faster than walking, but you arrive very dizzy."]),
    _n("facet_snail", "Facet Snail", "crystal", ["Glissand", "Slow Shine", "Lady Spiral", "Trail", "Moonslime", "Gemma"],
       "Oh, hello. I've been moving toward this camp for three weeks. Lovely to finally arrive.",
       ["My shell grows a new crystal every year. I'm forty-one crystals old.",
        "The trail behind me hardens into glass. The others use it as a road. You're welcome.",
        "Hurry? I don't know that word. Is it a kind of snack?"]),
    _n("blobbin", "Blobbin", "toxic", ["Gloop", "Splorch", "Little Ooze", "Wobble", "Bubbles", "Sir Squelch"],
       "*blorp* Hiya! Don't worry, I don't eat visitors. I only ate one bolt today and it was an accident.",
       ["I can see the bolt in me too. It's my friend now. His name is Bolt.",
        "Acid rain is just a bath with extra steps.",
        "If you poke me I'll wobble for an hour. Go on. No? You're no fun."]),
    _n("toadwarden", "Toadwarden", "toxic", ["Old Croak", "Warden Bogsworth", "Fennimore", "Ribbit-Rix", "Marsh", "Toady"],
       "Hrrumph. Another traveller. Wipe your feet - no, not there, that's my nephew.",
       ["I've guarded this marsh for sixty years. From what? Nobody's said. I'm still guarding.",
        "The hat? It grew. I let it. Looks distinguished, doesn't it?",
        "In my day we didn't have spaceships. We had a big lily pad and a strong wind."]),
    _n("crabbit", "Crabbit", "ocean", ["Pinch", "Clack-Clack", "Sideways Sal", "Coral", "Big Mitt", "Shelby"],
       "*click click* Hello, hello! Sorry, I walk sideways, so I'm technically waving with my back. Hi!",
       ["The big claw is for opening shellfish. The small claw is for waving. Very important.",
        "I've moved shell four times. This one has a view.",
        "Low tide is the best tide. All the good stuff's on the floor."]),
    _n("octavian", "Octavian", "ocean", ["Professor Inkwell", "Lady Eightsworth", "Tentaculus", "Squill", "Mantle", "Doctor Siphon"],
       "Ah, a visitor! Do forgive the monocle - I'm short-sighted in seven of my eight eyes. Charmed.",
       ["I'm writing a history of this world. With all eight arms. It's going quickly.",
        "When I'm embarrassed I change colour. Let's not discuss what colour.",
        "I could squeeze through a keyhole. I don't, of course. Manners."]),
    _n("moonmole", "Moonmole", "barren", ["Digby", "Old Burrow", "Lumpkin", "Grit", "Tunneller Pell", "Moss-less"],
       "*sniff* Eh? Someone's here? Hang on - *adjusts headlamp* - oh! A big blue someone. Hello!",
       ["I can't see much. That's what the lamp's for. Also I like the lamp.",
        "There are tunnels under this whole world. I dug forty percent of them. On a lunch break.",
        "The surface is so... open. Gives me the shivers. Back in the hole soon."]),
    _n("dishhead", "Dishhead", "barren", ["Relay-6", "Old Static", "Uplink", "Beacon", "Ping", "Ground Control"],
       "*bzzt* SIGNAL RECEIVED. Hello. I was a satellite once. Fell down. Liked it here. Stayed.",
       ["I can hear radio from fifty light years away. Mostly it's ads.",
        "My panels drink sunlight. Night is very long and very hungry.",
        "I still send reports to my old base. They never answer. I tell them about the weather anyway."]),
]
LOOKS = len(SPECIES)
TRAVELLERS = [k for k, sp in enumerate(SPECIES) if not sp.get("home")]


def natives_of(biome: str) -> list[int]:
    return [k for k, sp in enumerate(SPECIES) if sp.get("home") == biome]


# ---------------------------------------------------------------- roaming groups
# Named bands that travel a route of worlds, a couple of days on each, and
# remember you. ``members`` are species indices with their own names.
GROUPS = [
    dict(key="survey", name="Kestrel Survey Team", icon="scanner", color=(255, 190, 90),
         blurb="Cartographers of the Survey Corps, mapping every world in the sector.",
         members=[(7, "Professor Lattice"), (2, "Tik-Theodolite"), (0, "Ilu-Ve"), (1, "Basalt")],
         speed=50, stops=True),
    dict(key="caravan", name="Gloam Caravan", icon="coin", color=(240, 210, 120),
         blurb="Wandering traders and their patient Grumblebeast, buying and selling between worlds.",
         members=[(6, "Quartermaster Bloop"), ("beast", "Grumblebeast"), (3, "Morel"), (21, "Squill")],
         speed=40, stops=True),
    dict(key="pilgrims", name="Pilgrims of the Ember Road", icon="star", color=(200, 170, 255),
         blurb="A lantern procession carrying the last ember of a dead star from world to world.",
         members=[(5, "The Lanternkeeper"), (14, "Cinder"), (5, "Wick"), (5, "Hush")],
         speed=32, stops=False),
    dict(key="gang", name="Rustwhistle Gang", icon="gear", color=(230, 140, 90),
         blurb="Scavenger drones under an old satellite. They buy ore and sell what they find.",
         members=[(23, "Big Static"), (2, "Rivet"), (2, "Sprocket-Nine"), (2, "Clank Prime")],
         speed=58, stops=True),
]
GROUP_DAYS = 2           # in-game days a group spends on each world of its route


def portrait_ok(look) -> bool:
    return isinstance(look, int)



def giver_look(poi, biome: str | None = None) -> int:
    """Which species runs this camp's jobs: usually a native of the world."""
    seed = int(poi["seed"])
    natives = natives_of(biome or poi.get("biome", ""))
    if natives and (seed // 3) % 4:
        return natives[(seed // 7) % len(natives)]
    return TRAVELLERS[(seed // 7) % len(TRAVELLERS)]


def name_for(look: int, seed: int) -> str:
    return random.Random(seed * 31 + look).choice(SPECIES[look]["names"])


def short(name: str) -> str:
    """How the HUD names them: the first part of a name, minus a leading 'The'."""
    if name.startswith("The "):
        return name[4:]
    return name.split()[0] if " " in name and not name.startswith("Dr.") else name
