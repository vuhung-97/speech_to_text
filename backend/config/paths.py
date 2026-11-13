"""One responsibility: resolve every filesystem location the app touches."""

from __future__ import annotations

import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MODELS_DIR = BASE_DIR / "models"
SHERPA_DIR = MODELS_DIR / "sherpa"
SAMPLES_DIR = BASE_DIR / "samples"
SETTINGS_PATH = BASE_DIR / "settings.json"
FRONTEND_DIR = BASE_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

# Long-form speech is written here (PCM16 WAV) instead of RAM. It lives in the
# OS temp folder so a crash never leaves gigabytes inside the project.
TTS_TEMP_DIR = Path(tempfile.gettempdir()) / "stt_binh" / "tts"
TTS_DISK_QUOTA_MB = 512

# Embedding model for the FAQ catalogue (vendored, offline) and the app database.
EMBED_DIR = MODELS_DIR / "embed"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

# VieNeu-TTS (optional TTS feature): the installed app keeps its Hugging Face
# cache and cloned voices here, so the backend can run fully offline.
VIENEU_DIR = MODELS_DIR / "vieneu"
VIENEU_HF_CACHE = VIENEU_DIR / "vieneu" / "hf_cache"
VIENEU_CUSTOM_VOICES = VIENEU_DIR / "vieneu" / "custom_voices.json"
