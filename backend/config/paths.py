"""One responsibility: resolve every filesystem location the app touches."""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MODELS_DIR = BASE_DIR / "models"
SHERPA_DIR = MODELS_DIR / "sherpa"
SAMPLES_DIR = BASE_DIR / "samples"
SETTINGS_PATH = BASE_DIR / "settings.json"
FRONTEND_DIR = BASE_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
