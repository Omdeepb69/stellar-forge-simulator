[app]
title = Stellar Forge
package.name = stellarforge
package.domain = com.stellarforge
source.dir = .
source.include_exts = py,png,json,txt,md
source.include_patterns = assets/**
source.exclude_dirs = tests,docs,.git,.github,stella,saves,__pycache__,.mypy_cache,.pytest_cache,.buildozer,bin
source.exclude_patterns = *.pyc,*.pyo

version = 0.1.12

requirements = python3,pygame==2.5.2,numpy

orientation = landscape
fullscreen = 1

# Android permissions (INTERNET for multiplayer)
android.permissions = INTERNET

# Target / min API levels
android.api = 33
android.minapi = 24
android.ndk = 25b

# Pin python-for-android to v2024.01.21 (Python 3.11.5 + compatible numpy/pygame)
p4a.bootstrap = sdl2
p4a.branch = v2024.01.21

# App icon
presplash.filename = assets/generated/ui/icon_256.png
icon.filename = assets/generated/ui/icon_256.png

# Entry point
entrypoint = main.py

# Build configuration
android.accept_sdk_license = True
android.archs = arm64-v8a

# Optimise for size
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1

