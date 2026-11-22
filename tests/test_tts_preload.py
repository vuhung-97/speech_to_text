"""TTS preload: the model is in RAM before the first read."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.tts_service import TtsService, TtsUnavailable


class FakeTts(TtsService):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(temp_root=tmp_path)
        self.loads = 0

    def _ensure_engine(self):
        self.loads += 1
        self._engine = object()
        self._load_seconds = 0.01
        return self._engine


def test_warmup_loads_engine_once(tmp_path: Path) -> None:
    service = FakeTts(tmp_path)
    assert service.warmup() is True
    assert service._engine is not None
    assert service.status()["loaded"] is True

    assert service.warmup() is True
    assert service.loads == 1, "warmup must not reload an already loaded engine"


def test_preload_async_runs_in_background(tmp_path: Path) -> None:
    service = FakeTts(tmp_path)
    thread = service.preload_async()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert service._engine is not None
    assert service.status()["preloading"] is False


def test_preload_async_warms_the_selected_voice(tmp_path: Path) -> None:
    class Recording(FakeTts):
        def warmup(self, *, synthesize: bool = False,
                   voice: str | None = None) -> bool:
            self.warmed = (synthesize, voice)
            return True

    service = Recording(tmp_path)
    thread = service.preload_async(synthesize=True, voice="Mai Anh")
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert service.warmed == (True, "Mai Anh")
    assert service.status()["preloading"] is False


def test_warmup_reports_unavailable(tmp_path: Path) -> None:
    class MissingTts(FakeTts):
        @staticmethod
        def package_installed() -> bool:
            return False

    assert MissingTts(tmp_path).warmup() is False


def test_warmup_survives_missing_model(tmp_path: Path) -> None:
    class BrokenTts(FakeTts):
        def _ensure_engine(self):
            raise TtsUnavailable("thiếu model")

    assert BrokenTts(tmp_path).warmup() is False
