"""Browser audio over WebSocket: one session per connection, isolated events."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder
from backend.config.constants import BLOCK, SAMPLE_RATE
from backend.config.settings import Settings
from backend.main import create_app
from backend.services.engines import available_engines
from backend.services.event_service import EventBus
from backend.services.transcription_service import LivePipeline

SPEECH = np.full(BLOCK, 0.2, dtype=np.float32)
SILENCE = np.zeros(BLOCK, dtype=np.float32)


def pcm(frames: list[np.ndarray]) -> bytes:
    data = np.concatenate(frames)
    return (data * 32767).astype("<i2").tobytes()


class FakeEngine:
    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, audio: np.ndarray, config=None):
        self.calls += 1
        return "xin chào", 0.05

    def describe(self) -> dict:
        return {"name": "fake"}


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(tmp_path / "settings.json", catalog=available_engines)
    settings.apply_cli({"mode": "accurate", "silence_hang": 0.7})
    base = LivePipeline(FakeEngine(), EventBus(), settings)
    app = create_app(None, base, None, None, tmp_path,  # type: ignore[arg-type]
                     db_path=tmp_path / "app.db",
                     embedder=HashingEmbedder())
    with TestClient(app) as instance:
        yield instance


def drain_until_final(websocket, limit: int = 120) -> dict:
    for _ in range(limit):
        event = websocket.receive_json()
        if event.get("type") == "final":
            return event
    raise AssertionError("không nhận được final")


def send_pcm(websocket, data: bytes, chunk: int = 640) -> None:
    """Send audio in 20 ms frames, like the browser worklet does."""
    for start in range(0, len(data), chunk):
        websocket.send_bytes(data[start:start + chunk])


def test_websocket_stream_produces_final(client: TestClient) -> None:
    with client.websocket_connect("/ws/audio?sample_rate=16000") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert ready["sample_rate"] == SAMPLE_RATE

        send_pcm(ws, pcm([SILENCE] * 2 + [SPEECH] * 20 + [SILENCE] * 10))
        final = drain_until_final(ws)
        assert final["text"] == "xin chào"
        assert final["hard"] is True


def test_websocket_rejects_wrong_sample_rate(client: TestClient) -> None:
    with client.websocket_connect("/ws/audio?sample_rate=8000") as ws:
        event = ws.receive_json()
        assert event["type"] == "error"
        assert "16000" in event["detail"]


def test_websocket_reconnect_works(client: TestClient) -> None:
    with client.websocket_connect("/ws/audio?sample_rate=16000") as ws:
        assert ws.receive_json()["type"] == "ready"
        send_pcm(ws, pcm([SILENCE] * 2 + [SPEECH] * 20 + [SILENCE] * 10))
        assert drain_until_final(ws)["text"] == "xin chào"

    # The session is gone; a new connection must start cleanly.
    with client.websocket_connect("/ws/audio?sample_rate=16000") as second:
        assert second.receive_json()["type"] == "ready"


def test_frames_split_mid_sample_are_safe(client: TestClient) -> None:
    payload = pcm([SILENCE] * 2 + [SPEECH] * 20 + [SILENCE] * 10)
    with client.websocket_connect("/ws/audio?sample_rate=16000") as ws:
        assert ws.receive_json()["type"] == "ready"
        # Send odd-sized chunks so a sample straddles two WebSocket frames.
        for start in range(0, len(payload), 333):
            ws.send_bytes(payload[start:start + 333])
        assert drain_until_final(ws)["text"] == "xin chào"
