"""Hardening tests: catalogue duplicates beyond the old scan window, WS limits,
settings broadcast, and oversized frames.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder
from backend.adapters.retrieval.sqlite_faq import (SqliteFaqMatcher,
                                                   SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database
from backend.config.constants import BLOCK, SAMPLE_RATE
from backend.config.settings import Settings
from backend.domain.faq.models import FaqEntry
from backend.main import create_app
from backend.services.engines import available_engines
from backend.services.event_service import EventBus
from backend.services.faq_service import FaqService
from backend.services.transcription_service import LivePipeline

SPEECH = np.full(BLOCK, 0.2, dtype=np.float32)
SILENCE = np.zeros(BLOCK, dtype=np.float32)


class FakeEngine:
    def transcribe(self, audio: np.ndarray, config=None):
        return "xin chào", 0.05

    def describe(self) -> dict:
        return {"name": "fake"}


@pytest.fixture()
def client(tmp_path: Path):
    settings = Settings(tmp_path / "settings.json", catalog=available_engines)
    settings.apply_cli({"mode": "accurate", "silence_hang": 0.7})
    base = LivePipeline(FakeEngine(), EventBus(), settings)
    app = create_app(settings, base, None, None, tmp_path,  # type: ignore[arg-type]
                     db_path=tmp_path / "app.db",
                     embedder=HashingEmbedder())
    with TestClient(app) as instance:
        yield instance


def test_duplicate_detected_beyond_200_entries(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    repo = SqliteFaqRepository(database)
    embedder = HashingEmbedder()
    service = FaqService(repo, SqliteFaqMatcher(repo, embedder), embedder)

    for index in range(205):
        repo.upsert(FaqEntry(id="", tenant_id="local",
                             question=f"Câu hỏi số {index}?",
                             answer="Đáp án."))

    with pytest.raises(ValueError, match="đã có trong kho"):
        service.create("local", "  câu hỏi số 204?  ", "Đáp án khác.")


def test_oversized_frame_is_ignored(client: TestClient) -> None:
    with client.websocket_connect("/ws/audio?sample_rate=16000") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_bytes(b"\x00\x00" * 40_000)  # 80 KB > 64 KB guard
        warning = ws.receive_json()
        while warning.get("type") != "warning":
            warning = ws.receive_json()
        assert "quá lớn" in warning["detail"]


def test_session_limit_closes_with_1013(client: TestClient) -> None:
    client.app.state.audio_hub._max_sessions = 1
    with client.websocket_connect("/ws/audio?sample_rate=16000") as first:
        assert first.receive_json()["type"] == "ready"
        with client.websocket_connect("/ws/audio?sample_rate=16000") as second:
            event = second.receive_json()
            assert event["type"] == "error"
            assert "phiên" in event["detail"]


def test_settings_change_notifies_open_session(client: TestClient) -> None:
    with client.websocket_connect("/ws/audio?sample_rate=16000") as ws:
        assert ws.receive_json()["type"] == "ready"
        client.post("/api/settings", json={"silence_hang": 0.9})
        for _ in range(30):
            event = ws.receive_json()
            if event.get("type") == "settings_changed":
                break
        else:
            raise AssertionError("không nhận được settings_changed")
