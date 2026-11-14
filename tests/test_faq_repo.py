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


def test_schema_upgrades_to_v2(tmp_path: Path) -> None:
    database, _ = make(tmp_path)
    assert database.schema_version == 3


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
