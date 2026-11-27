"""Global tunables for Stellar Forge.

Everything gameplay-relevant lives here so balancing never requires
hunting through scene code.
"""
import os
import sys
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
ASSET_DIR = PROJECT_DIR / "assets"
SAVE_DIR = PROJECT_DIR / "saves"

# --- Android detection -----------------------------------------------------
def _is_android() -> bool:
    try:
        import android  # noqa: F401
        return True
    except ImportError:
        pass
    return bool(os.environ.get("ANDROID_ARGUMENT") or os.environ.get("P4A_BOOTSTRAP"))

IS_ANDROID = _is_android()

if IS_ANDROID:
    # python-for-android: assets are bundled next to the script, saves go to app-private storage
    try:
        from android.storage import app_storage_path  # type: ignore[import]
        _android_base = Path(app_storage_path())
    except Exception:
        _android_base = Path(os.environ.get("ANDROID_PRIVATE", "."))
    ASSET_DIR = _android_base / "assets"
    SAVE_DIR = _android_base / "saves"
elif getattr(sys, "frozen", False):
    # packaged build (PyInstaller): assets ship inside the bundle, saves go to the user's data folder
    ASSET_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR)) / "assets"
    base = Path(os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    SAVE_DIR = base / "StellarForge"
SAVE_FILE = SAVE_DIR / "savegame.json"
SETTINGS_FILE = SAVE_DIR / "settings.json"

# --- Display ----------------------------------------------------------------
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
MAX_DT = 1 / 20  # clamp long frames so physics never explodes
TITLE = "Stellar Forge: The Last Voyager"

# --- Universe -----------------------------------------------------------------
SECTOR_SIZE = 40_000          # world units per sector edge
SECTOR_LOAD_RADIUS = 1        # 3x3 sectors are live around the player
SYSTEM_CHANCE = 0.72          # chance a sector contains a star system
ORBIT_TIME_SCALE = 0.35       # slows planet orbits so landing is pleasant
GRAVITY_SOFTENING = 400.0     # avoids singularities near body centres

# --- Ship ---------------------------------------------------------------------
SHIP_BASE_THRUST = 230.0      # px/s^2
SHIP_TURN_SPEED = 230.0       # deg/s
SHIP_BOOST_MULT = 2.1
SHIP_BASE_FUEL = 800.0
SHIP_FUEL_BURN = 6.0          # fuel/s while thrusting
SHIP_BOOST_BURN = 3.0         # extra multiplier while boosting
SHIP_BASE_HULL = 100.0
SHIP_BASE_SHIELD = 40.0
SHIP_SHIELD_REGEN = 4.0       # per second after delay
SHIP_SHIELD_DELAY = 3.0
SHIP_MAX_SPEED = 2600.0
SAFE_LANDING_SPEED = 160.0    # relative speed for a soft touchdown
LANDING_ASSIST_RANGE = 2.4    # multiples of planet radius where [L] works
EMERGENCY_FUEL = 60.0         # solar trickle never lets you hard-lock

# --- Combat ---------------------------------------------------------------------
BULLET_SPEED = 1100.0
BULLET_LIFETIME = 1.3
ENEMY_BULLET_SPEED = 620.0

# --- Art -------------------------------------------------------------------------
ART_SCALE = 2                 # every world sprite is drawn at this whole-number scale (docs/ART_STYLE.md)
UI_SCALE = 2                  # interface pixels

# --- Surface --------------------------------------------------------------------
# (tuned for the 2x world: the pilot is ~156 px tall)
SURFACE_GRAVITY = 2100.0      # px/s^2 at gravity multiplier 1.0
PLAYER_SPEED = 430.0
PLAYER_JUMP = 900.0          # ~190 px hop: a bit over the pilot's own height
JETPACK_FORCE = 3300.0
JETPACK_CAPACITY = 2.6        # seconds of thrust
JETPACK_REGEN = 2.2           # seconds of thrust regained per second on the ground
SAFE_FALL = 1400.0            # px you can drop (big pilot) before a hard landing hurts: cliffs, not hops
MEDKIT_HEAL = 45.0            # minimum HP restored per Nano-Medkit (or 45% max HP)
MAX_MEDKITS = 6               # max Nano-Medkits carried at once
MEDKIT_PRICE = 45             # base station price per Nano-Medkit
TERRAIN_CHUNK = 1024
TERRAIN_STEP = 8
STRONGHOLD_MIN_DIST = 2600
STRONGHOLD_MAX_DIST = 6000

# --- Economy --------------------------------------------------------------------
FUEL_PRICE = 0.5              # credits per unit of fuel
REPAIR_PRICE = 1.5            # credits per hull point
ORE_VALUE = 12
DISCOVERY_REWARD = 60
UPGRADE_MAX_LEVEL = 5
NG_PLUS_DANGER = 1.5           # extra danger per New Game+ cycle

# --- Colours --------------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
UI_ACCENT = (110, 220, 255)
UI_WARN = (255, 190, 70)
UI_DANGER = (255, 80, 80)
UI_GOOD = (120, 255, 150)
UI_PANEL = (8, 14, 30, 200)
UI_GOLD = (255, 210, 120)
UI_TEXT = (220, 230, 245)
UI_DIM = (150, 160, 190)
UI_VIOLET = (200, 150, 255)
SPACE_BG = (3, 4, 12)
