"""P6: request ids, audit trail, prerendered audio cache and cached playback."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder
from backend.adapters.storage.sqlite import Database
from backend.main import create_app
from backend.services.tts_service import TtsService


class StubPipeline:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def engine_info(self) -> dict:
        return {}


class FakeEngine:
    sample_rate = 48_000

    def infer_stream(self, text: str, voice=None, **kwargs):
        for _ in range(2):
            yield np.full(48_000, 0.2, dtype=np.float32)

    def infer(self, text: str, voice=None, **kwargs):
        return np.zeros(48_000, dtype=np.float32)


class FakeTts(TtsService):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(temp_root=tmp_path)
        self.engine = FakeEngine()

    def available(self):
        return True, ""

    def voices(self):
        return ([{"id": "Mai Anh"}], "Mai Anh")

    def _ensure_engine(self):
        return self.engine


@pytest.fixture()
def client(tmp_path: Path):
    tts = FakeTts(tmp_path / "tts")
    app = create_app(
        None, StubPipeline(), None, None, tmp_path,  # type: ignore[arg-type]
        db_path=tmp_path / "app.db",
        embedder=HashingEmbedder(),
        tts=tts,
        audio_cache_dir=tmp_path / "audio",
    )
    with TestClient(app) as instance:
        yield instance
    tts.shutdown()


def create_entry(client: TestClient, question: str = "Thủ đô Việt Nam là gì?",
                 answer: str = "Hà Nội.") -> dict:
    response = client.post("/api/v1/faq/entries", json={
        "question": question, "answer": answer, "category": "chung"})
    assert response.status_code == 200, response.text
    return response.json()["entry"]


def ask(client: TestClient, question: str) -> dict:
    return client.post("/api/v1/qa/ask", json={"question": question}).json()["answer"]


def wait_job(client: TestClient, job_id: str, timeout: float = 8.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        status = client.get(f"/api/v1/faq/prerender/{job_id}").json()
        if status["status"] != "running":
            return status
        time.sleep(0.05)
    raise AssertionError("prerender không kết thúc")


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/api/v1/health",
                          headers={"X-Request-ID": "abc123"})
    assert response.headers["x-request-id"] == "abc123"

    generated = client.get("/api/v1/health")
    assert generated.headers["x-request-id"]


def test_audit_records_sensitive_actions(client: TestClient) -> None:
    entry = create_entry(client)
    asked = client.post("/api/v1/qa/ask", json={
        "question": "Thủ đô Việt Nam là gì?"}).json()
    client.delete(f"/api/v1/sessions/{asked['session_id']}")
    client.delete(f"/api/v1/faq/entries/{entry['id']}")

    items = client.get("/api/v1/audit").json()["items"]
    actions = [item["action"] for item in items]
    assert "faq.create" in actions
    assert "session.delete" in actions
    assert "faq.delete" in actions
    assert items[0]["action"] == "faq.delete"


def test_prerender_caches_and_serves_audio(client: TestClient,
                                           tmp_path: Path) -> None:
    entry = create_entry(client)
    answer = ask(client, "Thủ đô Việt Nam là gì?")

    started = client.post(f"/api/v1/faq/entries/{entry['id']}/prerender", json={})
    assert started.status_code == 200
    job = started.json()["job"]
    assert job["status"] != "error", job.get("error")

    finished = wait_job(client, job["id"])
    assert finished["status"] == "done", finished
    assert finished["seconds"] == pytest.approx(2.0, abs=0.05)

    audio = client.get(f"/api/v1/faq/entries/{entry['id']}/audio",
                       params={"voice": "Mai Anh"})
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/wav"
    assert audio.content[:4] == b"RIFF"
    assert list((tmp_path / "audio").glob("*.wav"))

    speech = client.post(f"/api/v1/qa/answers/{answer['id']}/speech",
                         json={"voice": "Mai Anh"}).json()
    assert speech["mode"] == "cached"
    assert speech["url"].startswith("/api/v1/faq/entries/")


def test_speech_falls_back_to_stream_without_cache(client: TestClient) -> None:
    create_entry(client)
    answer = ask(client, "Thủ đô Việt Nam là gì?")
    speech = client.post(f"/api/v1/qa/answers/{answer['id']}/speech",
                         json={}).json()
    assert speech["mode"] == "stream"
    assert speech["text"] == "Hà Nội."
    assert speech["voice"] == "Mai Anh"


def test_prerender_unknown_entry_is_404(client: TestClient) -> None:
    response = client.post("/api/v1/faq/entries/khong-co/prerender", json={})
    assert response.status_code == 404
    assert client.get("/api/v1/faq/prerender/khong-co").status_code == 404
    assert client.get("/api/v1/faq/entries/khong-co/audio").status_code == 404


def test_cached_audio_is_tenant_scoped(client: TestClient) -> None:
    entry = create_entry(client)
    job = client.post(f"/api/v1/faq/entries/{entry['id']}/prerender", json={}).json()["job"]
    wait_job(client, job["id"])

    other = client.get(f"/api/v1/faq/entries/{entry['id']}/audio",
                       params={"voice": "Mai Anh"},
                       headers={"X-Workspace": "acme"})
    assert other.status_code == 404


def test_schema_v3(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    assert database.schema_version == 4
