"""TTS runtime settings: engine is rebuilt lazily when precision/threads change."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.settings import Settings  # noqa: E402
from backend.services.tts_service import TtsService  # noqa: E402


class FakeEngine:
    pass


class FakeLoader:
    def __init__(self, precision: str, threads: int,
                 created: list[tuple[str, int, FakeEngine]]) -> None:
        self.precision = precision
        self.threads = threads
        self.created = created

    def local_model(self):
        return None, None, False

    def create(self):
        engine = FakeEngine()
        self.created.append((self.precision, self.threads, engine))
        return engine, 0.25


@pytest.fixture()
def service(tmp_path: Path):
    settings = Settings(tmp_path / "settings.json", catalog=lambda: {})
    item = TtsService(temp_root=tmp_path, settings=settings)
    item.available = lambda: (True, "")  # noqa: ARG005 - test double
    created: list[tuple[str, int, FakeEngine]] = []
    item._new_loader = lambda precision, threads: FakeLoader(precision, threads, created)
    yield item, settings, created
    item.shutdown()


def test_engine_is_built_once_while_settings_do_not_change(service) -> None:
    item, _settings, created = service

    assert item._ensure_engine() is item._ensure_engine()
    assert len(created) == 1
    assert item.status()["threads"] == 0


def test_changing_threads_rebuilds_on_next_use(service) -> None:
    item, settings, created = service
    first = item._ensure_engine()

    settings.update({"tts_threads": 4})
    rebuilt = item._ensure_engine()

    assert len(created) == 2
    assert created[-1][:2] == ("fp32", 4)
    assert rebuilt is not first


def test_changing_precision_is_reported_in_status(service) -> None:
    item, settings, _created = service
    item._ensure_engine()

    settings.update({"tts_precision": "int8"})

    status = item.status()
    assert status["precision"] == "int8"
    assert status["precision_effective"] == "fp32", "no int8 files in the fake loader"
