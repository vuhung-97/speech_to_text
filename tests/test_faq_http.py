"""FAQ administration + end-to-end matching over HTTP."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx_builder import outline  # noqa: E402

from backend.adapters.embedding.hashing import HashingEmbedder  # noqa: E402
from backend.main import create_app  # noqa: E402

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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


def test_import_docx_outline(client: TestClient) -> None:
    response = client.post(
        "/api/v1/faq/import-docx",
        files={"file": ("de_cuong.docx", outline(), _DOCX_MIME)},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert (report["added"], report["total"]) == (2, 2)
    assert report["reason"] == "created"
    document = report["document"]
    assert document["name"] == "de_cuong.docx"
    assert document["entry_count"] == 2

    items = client.get("/api/v1/faq/entries").json()["items"]
    assert {item["source_ref"] for item in items} == {"Câu I.1.1", "Câu 2"}
    assert {item["document_id"] for item in items} == {document["id"]}

    answer = client.post("/api/v1/qa/ask", json={
        "question": "tự động hóa chỉ huy là gì"}).json()["answer"]
    assert answer["status"] == "matched"
    assert answer["text"].startswith("Nội dung một.")

    # Re-uploading identical bytes must skip, not duplicate.
    again = client.post(
        "/api/v1/faq/import-docx",
        files={"file": ("de_cuong.docx", outline(), _DOCX_MIME)},
    ).json()
    assert again["reason"] == "unchanged"
    assert again["skipped"] == 2


def test_documents_crud_and_filtered_search(client: TestClient) -> None:
    first = client.post(
        "/api/v1/faq/import-docx",
        files={"file": ("de_a.docx", outline(), _DOCX_MIME)},
    ).json()
    second = client.post(
        "/api/v1/faq/import-docx",
        files={"file": ("de_b.docx", outline(answer="khác."), _DOCX_MIME)},
    ).json()
    first_id = first["document"]["id"]
    second_id = second["document"]["id"]

    listed = client.get("/api/v1/faq/documents").json()["items"]
    assert {item["id"] for item in listed} == {first_id, second_id}

    renamed = client.patch(f"/api/v1/faq/documents/{first_id}",
                           json={"name": "Đề A"}).json()
    assert renamed["document"]["name"] == "Đề A"

    scoped = client.get(f"/api/v1/faq/entries?document_id={first_id}").json()["items"]
    assert len(scoped) == 2
    assert all(item["document_id"] == first_id for item in scoped)

    # Searching inside one set answers only from that set.
    answer = client.post("/api/v1/qa/ask", json={
        "question": "tự động hóa chỉ huy là gì",
        "document_id": second_id}).json()["answer"]
    assert answer["status"] == "matched"
    assert answer["text"].startswith("khác.")

    deleted = client.delete(f"/api/v1/faq/documents/{first_id}").json()
    assert deleted["deleted_entries"] == 2
    assert client.get("/api/v1/faq/entries?document_id={first_id}").json()["items"] == []
    assert client.delete(f"/api/v1/faq/documents/{first_id}").status_code == 404


def test_import_docx_rejects_wrong_extension(client: TestClient) -> None:
    response = client.post(
        "/api/v1/faq/import-docx",
        files={"file": ("faq.csv", b"question,answer\n", "text/csv")},
    )
    assert response.status_code == 400
    assert ".docx" in response.json()["error"]


def test_import_docx_rejects_broken_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/faq/import-docx",
        files={"file": ("hỏng.docx", b"not a zip", _DOCX_MIME)},
    )
    assert response.status_code == 400


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
