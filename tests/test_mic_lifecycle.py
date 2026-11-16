"""Microphone lifecycle: closed unless the user asks to listen.

The capture loop must not even open the device while paused, so reading aloud
and listening can never overlap. These tests use a fake mic factory, no audio
hardware and no model.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.settings import Settings
from backend.main import create_app
from backend.services.audio_sessions import AudioSessionHub, SessionLimitReached
from backend.services.engines import available_engines
from backend.services.ws_mic import WebSocketMic
from backend.services.event_service import EventBus
from backend.services.transcription_service import LivePipeline


class FakeEngine:
    def transcribe(self, audio: np.ndarray):
        return "xin chào", 0.01

    def describe(self) -> dict:
        return {"name": "fake"}


class CountingMic:
    """Records open/close so tests can assert the device is released."""

    def __init__(self, log: list[str]) -> None:
        self._log = log

    def __enter__(self):
        self._log.append("open")
        return self

    def __exit__(self, *exc):
        self._log.append("close")

    def read(self, timeout: float = 0.2):
        time.sleep(0.01)
        return None

    def stats(self) -> dict:
        return {}


def make_settings(tmp_path: Path) -> Settings:
    return Settings(tmp_path / "settings.json", catalog=available_engines)


def make_pipeline(tmp_path: Path, log: list[str]) -> LivePipeline:
    bus = EventBus()
    return LivePipeline(
        FakeEngine(), bus, make_settings(tmp_path),
        mic_factory=lambda device: CountingMic(log),
        engine_factory=lambda values: FakeEngine(),
    )


def wait_for(predicate, timeout: float = 1.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_device_stays_closed_until_listening(tmp_path: Path) -> None:
    log: list[str] = []
    pipeline = make_pipeline(tmp_path, log)
    pipeline.set_paused(True)
    pipeline.start()
    try:
        time.sleep(0.35)
        assert log == [], "mic opened while paused"
        assert pipeline.status_event()["listening"] is False

        assert pipeline.set_listening(True) is True
        assert wait_for(lambda: "open" in log), "mic did not open"

        assert pipeline.set_listening(False) is False
        assert wait_for(lambda: "close" in log), "mic did not close"
        assert pipeline.status_event()["listening"] is False
    finally:
        pipeline.stop()


def test_pause_releases_device_and_resume_reopens(tmp_path: Path) -> None:
    log: list[str] = []
    pipeline = make_pipeline(tmp_path, log)
    pipeline.start()
    try:
        assert wait_for(lambda: "open" in log)

        pipeline.set_paused(True)
        assert wait_for(lambda: "close" in log)
        closed_at = len(log)

        pipeline.set_paused(False)
        assert wait_for(lambda: len(log) > closed_at)
        assert log.count("open") >= 2
        assert pipeline.status_event()["listening"] is True
    finally:
        pipeline.stop()


class StubPipeline:
    def __init__(self) -> None:
        self.calls: list[bool] = []
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None: ...
    def set_paused(self, paused: bool) -> bool:
        self.calls.append(paused)
        return paused
    def set_listening(self, listening: bool) -> bool:
        self.calls.append(not listening)
        return listening
    def snapshot(self) -> dict:
        return {"ok": True, "engine": {}, "queue": 0}
    def status_event(self) -> dict:
        return {"type": "status", "state": "listening"}


def test_app_starts_with_microphone_off(tmp_path: Path) -> None:
    pipeline = StubPipeline()
    app = create_app(None, pipeline, None, None, tmp_path,  # type: ignore[arg-type]
                     db_path=tmp_path / "app.db")
    with TestClient(app):
        assert pipeline.calls[:1] == [True], "lifespan must pause the mic"
        assert pipeline.started is False, "server must not start capture threads"


def test_audio_session_hub_enforces_limit(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    engine = FakeEngine()
    hub = AudioSessionHub(lambda: engine, lambda: settings, threading.Lock(),
                          max_sessions=1)
    mic = WebSocketMic(16000)
    session = hub.open(mic)
    session.start()
    try:
        with pytest.raises(SessionLimitReached):
            hub.open(WebSocketMic(16000))
    finally:
        asyncio.run(hub.close(session))
    assert hub.active == 0
