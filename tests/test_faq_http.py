"""FAQ administration + end-to-end matching over HTTP."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder
from backend.main import create_app


class StubPipeline:
    def start(self) -> None: ...
    def stop(self) -> None: ...


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(
        None, StubPipeline(), None, None, tmp_path,  # type: ignore[arg-type]
        db_path=tmp_path / "app.db",
        embedder=HashingEmbedder(),
    )
    with TestClient(app) as instance:
        yield instance


def create(client: TestClient, question: str, answer: str,
           category: str = "", tenant: str = "local") -> dict:
    response = client.post("/api/v1/faq/entries",
                           json={"question": question, "answer": answer,
                                 "category": category},
                           headers={"X-Workspace": tenant})
    assert response.status_code == 200, response.text
    return response.json()["entry"]


def test_create_list_patch_delete(client: TestClient) -> None:
    entry = create(client, "Thủ đô Việt Nam là gì?", "Hà Nội.", "địa lý")

    listed = client.get("/api/v1/faq/entries").json()
    assert [item["id"] for item in listed["items"]] == [entry["id"]]
    assert listed["items"][0]["category"] == "địa lý"

    patched = client.patch(f"/api/v1/faq/entries/{entry['id']}",
                           json={"answer": "Thủ đô là Hà Nội."})
    assert patched.status_code == 200
    assert patched.json()["entry"]["answer"] == "Thủ đô là Hà Nội."

    assert client.delete(f"/api/v1/faq/entries/{entry['id']}").status_code == 200
    assert client.get("/api/v1/faq/entries").json()["items"] == []
    assert client.delete(f"/api/v1/faq/entries/{entry['id']}").status_code == 404


def test_ask_matches_catalogue(client: TestClient) -> None:
    create(client, "Thủ đô Việt Nam là gì?", "Hà Nội.")

    response = client.post("/api/v1/qa/ask",
                           json={"question": "Thủ đô Việt Nam là gì?"})
    answer = response.json()["answer"]
    assert answer["status"] == "matched"
    assert answer["answered"] is True
    assert answer["text"] == "Hà Nội."
    assert answer["matched"]["question"] == "Thủ đô Việt Nam là gì?"
    assert answer["score"] > 0.99


def test_unrelated_question_stays_unanswered(client: TestClient) -> None:
    create(client, "Thủ đô Việt Nam là gì?", "Hà Nội.")
    answer = client.post("/api/v1/qa/ask", json={
        "question": "Cách nấu phở bò ngon tại nhà"}).json()["answer"]
    assert answer["status"] == "unanswered"
    assert answer["candidates"]


def test_patch_changes_what_is_read(client: TestClient) -> None:
    entry = create(client, "Giờ làm việc thế nào?", "8h.")
    client.patch(f"/api/v1/faq/entries/{entry['id']}",
                 json={"answer": "Từ 8h đến 17h."})
    answer = client.post("/api/v1/qa/ask", json={
        "question": "Giờ làm việc thế nào?"}).json()["answer"]
    assert answer["text"] == "Từ 8h đến 17h."


def test_import_csv(client: TestClient) -> None:
    payload = (
        "question,answer,category\n"
        "Câu một?,Đáp án một.,chung\n"
        "Câu hai?,Đáp án hai.,chung\n"
        ",Thiếu câu hỏi,chung\n"
    ).encode("utf-8")
    response = client.post(
        "/api/v1/faq/import",
        files={"file": ("faq.csv", payload, "text/csv")},
    )
    assert response.status_code == 200
    report = response.json()
    assert report["added"] == 2
    assert len(report["errors"]) == 1

    items = client.get("/api/v1/faq/entries").json()["items"]
    assert len(items) == 2


def test_reindex_and_stats(client: TestClient) -> None:
    create(client, "Câu hỏi?", "Đáp án.")
    reindex = client.post("/api/v1/faq/reindex").json()
    assert reindex["indexed"] == 1
    assert reindex["model"] == "hashing-char3"

    stats = client.get("/api/v1/faq/stats").json()
    assert stats["entries"] == 1
    assert stats["embedded"] == 1
    assert stats["threshold"] == pytest.approx(0.88)
    assert stats["embed_note"] == ""


def test_catalogue_is_tenant_scoped(client: TestClient) -> None:
    create(client, "Câu của acme", "Đáp án acme", tenant="acme")

    assert client.get("/api/v1/faq/entries").json()["items"] == []
    answer = client.post("/api/v1/qa/ask", json={
        "question": "Câu của acme"}).json()["answer"]
    assert answer["status"] == "unanswered"

    acme = client.get("/api/v1/faq/entries", headers={"X-Workspace": "acme"})
    assert len(acme.json()["items"]) == 1
