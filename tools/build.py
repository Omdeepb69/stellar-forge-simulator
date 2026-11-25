"""Build a stand-alone executable with PyInstaller.

    pip install pyinstaller
    python tools/build.py            # -> dist/StellarForge(.exe)

The game's assets are bundled inside the executable; saves and settings
go to the user's data folder (%APPDATA%/StellarForge or
~/.local/share/StellarForge), see ``config.py``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        print("PyInstaller is not installed: pip install pyinstaller")
        return 1
    sep = ";" if os.name == "nt" else ":"
    args = [
        str(ROOT / "main.py"),
        "--name", "StellarForge",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--icon", str(ROOT / "assets" / "generated" / "items" / "shard_crystal.png"),
        "--exclude-module", "pytest",
        "--exclude-module", "tkinter",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]
    if "--no-ml" in sys.argv:   # smaller build: the planet model falls back to numpy
        args += ["--exclude-module", "sklearn", "--exclude-module", "scipy"]
    if "--no-video" in sys.argv:
        args += ["--exclude-module", "cv2"]
    pyi.run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
