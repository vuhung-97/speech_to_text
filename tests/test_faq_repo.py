"""FAQ repository: CRUD, tenant scope, embedding storage, signature, stats."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.retrieval.sqlite_faq import SqliteFaqRepository
from backend.adapters.storage.sqlite import Database
from backend.domain.faq.models import FaqEntry


def make(tmp_path: Path):
    database = Database(tmp_path / "app.db")
    return database, SqliteFaqRepository(database)


def entry(tenant: str = "local", question: str = "Câu hỏi?",
          answer: str = "Câu trả lời.", entry_id: str = "",
          category: str = "") -> FaqEntry:
    return FaqEntry(id=entry_id, tenant_id=tenant, question=question,
                    answer=answer, category=category)


def test_schema_upgrades_to_v5(tmp_path: Path) -> None:
    database, _ = make(tmp_path)
    assert database.schema_version == 6


def test_crud_and_tenant_scope(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    saved = repo.upsert(entry())
    assert saved.id

    assert repo.get(saved.id, "local").question == "Câu hỏi?"
    assert repo.get(saved.id, "acme") is None
    assert repo.list("acme") == []

    updated = repo.upsert(FaqEntry(id=saved.id, tenant_id="local",
                                   question="Câu mới?", answer="Đáp mới.",
                                   category="chung", active=False))
    assert updated.created_at == saved.created_at
    assert repo.get(saved.id, "local").question == "Câu mới?"
    assert repo.list("local", active=True) == []
    assert len(repo.list("local", active=False)) == 1

    assert repo.delete(saved.id, "acme") is False
    assert repo.delete(saved.id, "local") is True
    assert repo.get(saved.id, "local") is None


def test_search_filter(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    repo.upsert(entry(question="Quy trình đăng ký", category="thủ tục"))
    repo.upsert(entry(question="Giờ làm việc", category="chung"))

    assert len(repo.list("local", query="đăng ký")) == 1
    assert len(repo.list("local", category="chung")) == 1
    assert len(repo.list("local", query="không có")) == 0


def test_embeddings_are_stored_and_read_back(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    saved = repo.upsert(entry())

    vector = np.arange(1, 5, dtype=np.float32)
    repo.set_embedding(saved.id, "local", vector, "fake", 1)

    rows = repo.embeddings("local")
    assert len(rows) == 1
    stored_entry, stored_vector = rows[0]
    assert stored_entry.id == saved.id
    assert stored_vector.tolist() == pytest.approx(vector.tolist())

    pending = repo.pending_embeddings("local", "fake", 1)
    assert pending == []
    assert repo.pending_embeddings("local", "fake", 2)  # version bump re-embeds


def test_upsert_invalidates_embedding(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    saved = repo.upsert(entry())
    repo.set_embedding(saved.id, "local", np.ones(4, dtype=np.float32), "fake", 1)

    repo.upsert(FaqEntry(id=saved.id, tenant_id="local",
                         question="Đổi câu hỏi", answer="Đổi đáp"))
    assert repo.embeddings("local") == []
    assert len(repo.pending_embeddings("local", "fake", 1)) == 1


def test_search_text_and_source_provenance(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    saved = repo.upsert(FaqEntry(
        id="", tenant_id="local",
        question="Đồng chí hãy trình bày khái niệm “Tự động hóa chỉ huy”?",
        answer="Đáp án.", source_file="de_cuong.docx", source_ref="Câu I.1.1",
        document_id="doc-1"))

    assert saved.search_text == "tự động hóa chỉ huy"
    stored = repo.find_by_source("local", "doc-1", "Câu I.1.1")
    assert stored is not None and stored.id == saved.id
    assert repo.find_by_source("local", "doc-2", "Câu I.1.1") is None

    # A manual edit keeps the provenance it did not supply.
    edited = repo.upsert(FaqEntry(id=saved.id, tenant_id="local",
                                  question=saved.question, answer="Đáp án mới."))
    assert edited.source_file == "de_cuong.docx"
    assert edited.source_ref == "Câu I.1.1"
    assert edited.document_id == "doc-1"


def test_document_scoped_entry_management(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    first = repo.upsert(FaqEntry(id="", tenant_id="local", question="một?",
                                 answer="a", source_ref="Câu 1", document_id="d1"))
    repo.upsert(FaqEntry(id="", tenant_id="local", question="hai?",
                         answer="b", source_ref="Câu 2", document_id="d1"))
    repo.upsert(FaqEntry(id="", tenant_id="local", question="ba?",
                         answer="c", source_ref="Câu 1", document_id="d2"))

    assert repo.count_in_document("local", "d1") == 2
    assert [item.question for item in repo.list("local", document_id="d2")] == ["ba?"]

    turned_off = repo.deactivate_missing("local", "d1", {"Câu 1"})
    assert turned_off == 1
    assert repo.find_by_source("local", "d1", "Câu 2").active is False

    second = repo.find_by_source("local", "d1", "Câu 2")
    deleted = repo.delete_by_document("local", "d1")
    assert sorted(deleted) == sorted([first.id, second.id])
    assert repo.count_in_document("local", "d1") == 0
    assert repo.count_in_document("local", "d2") == 1


def test_deactivate_missing_handles_large_outlines(tmp_path: Path) -> None:
    """Big outlines must not break the SQL parameter cap — or skip a batch."""
    _, repo = make(tmp_path)
    total = 1_050
    for number in range(total):
        repo.upsert(FaqEntry(id="", tenant_id="local", question=f"hỏi {number}?",
                             answer="đáp", source_ref=f"Câu {number}",
                             document_id="big"))

    keep = {f"Câu {number}" for number in range(total - 10)}
    assert repo.deactivate_missing("local", "big", keep) == 10

    assert repo.count_in_document("local", "big") == total
    assert repo.find_by_source("local", "big", "Câu 0").active is True
    assert repo.find_by_source("local", "big", f"Câu {total - 1}").active is False


def test_v6_backfill_groups_entries_by_source_file(tmp_path: Path) -> None:
    """Upgrading a v5 database turns (tenant, source_file) groups into documents."""
    path = tmp_path / "app.db"
    initial = Database(path)
    repository = SqliteFaqRepository(initial)
    saved = repository.upsert(FaqEntry(
        id="", tenant_id="local", question="một?", answer="a.",
        source_file="de_cuong.docx", source_ref="Câu I.1.1"))

    # Rewind to the v5 shape: no documents table, no document_id column.
    with initial.connect() as connection:
        connection.execute("DROP INDEX IF EXISTS idx_faq_entries_document")
        connection.execute("ALTER TABLE faq_entries DROP COLUMN document_id")
        connection.execute("DROP TABLE faq_documents")
        connection.execute("PRAGMA user_version = 5")

    # A fresh connection migrates to v6 and backfills the document.
    migrated_db = Database(path)
    from backend.adapters.storage.sqlite_faq_documents import (
        SqliteFaqDocumentRepository)
    documents = SqliteFaqDocumentRepository(migrated_db).list("local")
    assert len(documents) == 1
    assert documents[0].name == "de_cuong.docx"

    entry = SqliteFaqRepository(migrated_db).get(saved.id, "local")
    assert entry.document_id == documents[0].id


def test_signature_and_stats(tmp_path: Path) -> None:
    _, repo = make(tmp_path)
    assert repo.index_signature("local") == (0, 0.0, 0)

    saved = repo.upsert(entry())
    count, updated, version = repo.index_signature("local")
    assert count == 1 and updated > 0 and version == 0

    repo.set_embedding(saved.id, "local", np.ones(4, dtype=np.float32), "fake", 1)
    assert repo.index_signature("local")[2] == 1
    assert repo.stats("local") == {
        "entries": 1, "active": 1, "embedded": 1, "categories": 0}
