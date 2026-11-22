"""HTTP contract for long-form speech: status codes, headers, Range, cancel."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.domain.text.limits import MAX_TTS_WORDS
from backend.main import create_app
from backend.services.tts_service import TtsService

SAMPLE_RATE = 48_000


class StubPipeline:
    def start(self) -> None: ...
    def stop(self) -> None: ...


class FakeEngine:
    sample_rate = SAMPLE_RATE

    def infer_stream(self, text: str, voice=None, **kwargs):
        for _ in range(2):
            yield np.full(48_000, 0.2, dtype=np.float32)

    def infer(self, text: str, voice=None, **kwargs):
        return np.zeros(48_000, dtype=np.float32)


class FakeTts(TtsService):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(temp_root=tmp_path)
        self.engine = FakeEngine()
        self.preloaded = None

    def available(self):
        return True, ""

    def voices(self):
        return ([{"id": "Mai Anh"}], "Mai Anh")

    def _ensure_engine(self):
        return self.engine

    def preload_async(self, *, synthesize=False, voice=None):
        self.preloaded = (synthesize, voice)
        return None


@pytest.fixture()
def tts(tmp_path: Path):
    service = FakeTts(tmp_path)
    yield service
    service.shutdown()


@pytest.fixture()
def client(tmp_path: Path, tts: FakeTts):
    app = create_app(None, StubPipeline(), None, None, tmp_path, tts=tts)  # type: ignore[arg-type]
    with TestClient(app) as instance:
        yield instance


def test_preload_warms_the_selected_voice(client: TestClient,
                                          tts: FakeTts) -> None:
    response = client.post("/api/v1/tts/preload", json={"voice": "Mai Anh"})
    assert response.status_code == 200
    assert response.json()["preloading"] is True
    assert tts.preloaded == (True, "Mai Anh")

    status = client.get("/api/v1/tts/status")
    assert status.status_code == 200
    assert "preloading" in status.json()


def test_stream_returns_pcm_with_headers(client: TestClient) -> None:
    response = client.post("/api/v1/tts/stream", json={"text": "xin chào"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/L16")
    assert response.headers["x-sample-rate"] == str(SAMPLE_RATE)
    assert response.headers["x-tts-session"]
    assert len(response.content) == 2 * 48_000 * 2  # 2 blocks of 1 s, PCM16


def test_stream_rejects_too_many_words(client: TestClient) -> None:
    text = " ".join(["từ"] * (MAX_TTS_WORDS + 1))
    response = client.post("/api/v1/tts/stream", json={"text": text})
    assert response.status_code == 413
    assert response.json()["ok"] is False
    assert "2000" in response.json()["error"]


def test_stream_rejects_empty_text(client: TestClient) -> None:
    response = client.post("/api/v1/tts/stream", json={"text": "  "})
    assert response.status_code == 400


def test_stream_is_409_while_busy(client: TestClient, tts: FakeTts) -> None:
    tts.prepare_stream("đang đọc")
    response = client.post("/api/v1/tts/stream", json={"text": "câu khác"})
    assert response.status_code == 409


def test_wav_425_then_200_with_range(client: TestClient) -> None:
    stream = client.post("/api/v1/tts/stream", json={"text": "xin chào"})
    job_id = stream.headers["x-tts-session"]

    ready = client.get(f"/api/v1/tts/sessions/{job_id}.wav")
    assert ready.status_code == 200
    assert ready.headers["content-type"] == "audio/wav"

    partial = client.get(
        f"/api/v1/tts/sessions/{job_id}.wav", headers={"Range": "bytes=0-99"})
    assert partial.status_code == 206
    assert len(partial.content) == 100
    assert partial.headers["content-range"].startswith("bytes 0-99/")


def test_wav_is_425_while_generating(client: TestClient, tts: FakeTts) -> None:
    job = tts.prepare_stream("chưa xong")
    response = client.get(f"/api/v1/tts/sessions/{job.id}.wav")
    assert response.status_code == 425


def test_session_status_and_delete(client: TestClient) -> None:
    stream = client.post("/api/v1/tts/stream", json={"text": "xin chào"})
    job_id = stream.headers["x-tts-session"]

    status = client.get(f"/api/v1/tts/sessions/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["finalized"] is True
    assert body["seconds"] == pytest.approx(2.0, abs=0.01)
    assert body["bytes"] == 2 * 48_000 * 2

    removed = client.delete(f"/api/v1/tts/sessions/{job_id}")
    assert removed.status_code == 200
    assert client.get(f"/api/v1/tts/sessions/{job_id}").status_code == 404
    assert client.get(f"/api/v1/tts/sessions/{job_id}.wav").status_code == 425


def test_unknown_session_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/tts/sessions/nope").status_code == 404
    assert client.delete("/api/v1/tts/sessions/nope").status_code == 404


def test_limits_endpoint(client: TestClient) -> None:
    body = client.get("/api/v1/tts/limits").json()
    assert body["max_words"] == MAX_TTS_WORDS
    assert body["max_quick_chars"] == 1_000
    assert body["sample_rate"] == SAMPLE_RATE
    assert body["busy"] is False
