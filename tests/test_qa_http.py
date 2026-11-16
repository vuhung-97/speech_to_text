"""HTTP surface for Q&A and conversation sessions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import create_app


class StubPipeline:
    def start(self) -> None: ...
    def stop(self) -> None: ...


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(None, StubPipeline(), None, None, tmp_path,  # type: ignore[arg-type]
                     db_path=tmp_path / "app.db")
    with TestClient(app) as instance:
        yield instance


def test_ask_returns_answer_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/qa/ask",
                           json={"question": "Thủ đô Việt Nam là gì?"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["question"] == "Thủ đô Việt Nam là gì?"
    assert body["session_id"]
    answer = body["answer"]
    assert answer["status"] == "unanswered"
    assert answer["answered"] is False
    assert answer["matched"] is None
    assert answer["candidates"] == []
    assert answer["text"]


def test_ask_reuses_session(client: TestClient) -> None:
    first = client.post("/api/v1/qa/ask", json={"question": "Câu một"}).json()
    second = client.post("/api/v1/qa/ask", json={
        "question": "Câu hai", "session_id": first["session_id"]}).json()
    assert second["session_id"] == first["session_id"]

    detail = client.get(f"/api/v1/sessions/{first['session_id']}").json()
    assert [turn["question"] for turn in detail["turns"]] == ["Câu một", "Câu hai"]


def test_ask_rejects_empty_and_unknown_session(client: TestClient) -> None:
    empty = client.post("/api/v1/qa/ask", json={"question": "   "})
    assert empty.status_code == 400
    assert empty.json()["ok"] is False

    unknown = client.post("/api/v1/qa/ask", json={
        "question": "hỏi", "session_id": "khong-ton-tai"})
    assert unknown.status_code == 404


def test_sessions_list_detail_delete(client: TestClient) -> None:
    asked = client.post("/api/v1/qa/ask", json={"question": "Câu hỏi đầu"}).json()
    session_id = asked["session_id"]

    listed = client.get("/api/v1/sessions").json()
    assert listed["ok"] is True
    assert [item["id"] for item in listed["items"]] == [session_id]
    assert listed["items"][0]["turns"] == 1

    detail = client.get(f"/api/v1/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["turns"][0]["answer"]["status"] == "unanswered"

    assert client.delete(f"/api/v1/sessions/{session_id}").status_code == 200
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404
    assert client.delete(f"/api/v1/sessions/{session_id}").status_code == 404


def test_sessions_are_tenant_scoped(client: TestClient) -> None:
    asked = client.post("/api/v1/qa/ask",
                        json={"question": "câu của acme"},
                        headers={"X-Workspace": "acme"}).json()
    assert asked["session_id"]

    assert client.get("/api/v1/sessions").json()["items"] == []
    assert client.get(f"/api/v1/sessions/{asked['session_id']}").status_code == 404

    acme = client.get("/api/v1/sessions", headers={"X-Workspace": "acme"}).json()
    assert len(acme["items"]) == 1


def test_invalid_workspace_header_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/sessions", headers={"X-Workspace": "../etc"})
    assert response.status_code == 400


def test_unanswered_worklist(client: TestClient) -> None:
    client.post("/api/v1/qa/ask", json={"question": "Chưa có đáp án"})
    items = client.get("/api/v1/qa/unanswered").json()["items"]
    assert items and items[0]["question_norm"] == "chưa có đáp án"
    assert items[0]["asks"] == 1


def test_legacy_prefix_still_works(client: TestClient) -> None:
    legacy = client.post("/api/qa/ask", json={"question": "hỏi qua /api"})
    versioned = client.post("/api/v1/qa/ask", json={"question": "hỏi qua v1"})
    assert legacy.status_code == versioned.status_code == 200
