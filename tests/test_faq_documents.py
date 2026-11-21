"""Question-set administration: rename, delete, tenant scope and versioning."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx_builder import outline, paragraph, table, docx  # noqa: E402

from backend.adapters.embedding.hashing import HashingEmbedder  # noqa: E402
from backend.adapters.importer.docx_faq import parse_docx  # noqa: E402
from backend.adapters.retrieval.sqlite_faq import (  # noqa: E402
    SqliteFaqMatcher, SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database  # noqa: E402
from backend.adapters.storage.sqlite_faq_documents import (  # noqa: E402
    SqliteFaqDocumentRepository)
from backend.domain.faq.models import FaqDocumentNotFound  # noqa: E402
from backend.services.faq_documents import FaqDocumentsService  # noqa: E402
from backend.services.faq_service import FaqService  # noqa: E402


def make_services(tmp_path: Path):
    database = Database(tmp_path / "app.db")
    repository = SqliteFaqRepository(database)
    documents_repo = SqliteFaqDocumentRepository(database)
    embedder = HashingEmbedder()
    matcher = SqliteFaqMatcher(repository, embedder)
    catalogue = FaqService(repository, matcher, embedder)
    documents = FaqDocumentsService(documents_repo, repository, catalogue, matcher)
    return catalogue, repository, matcher, documents


def pairs(data: bytes):
    return parse_docx(data)


def test_rename_and_duplicate_name_guard(tmp_path: Path) -> None:
    _, _, _, documents = make_services(tmp_path)
    first = documents.import_document("local", "de_a.docx", pairs(outline()))
    second = documents.import_document("local", "de_b.docx", pairs(outline(answer="khác.")))

    renamed = documents.rename(first["document"]["id"], "local", "Đề A - TĐHCH")
    assert renamed.name == "Đề A - TĐHCH"
    assert renamed.id == first["document"]["id"]

    with pytest.raises(ValueError, match="trùng tên"):
        documents.rename(second["document"]["id"], "local", renamed.name)

    with pytest.raises(FaqDocumentNotFound):
        documents.rename("missing", "local", "tên mới")


def test_delete_removes_set_and_entries(tmp_path: Path) -> None:
    _, repository, matcher, documents = make_services(tmp_path)
    report = documents.import_document("local", "de_a.docx", pairs(outline()))

    result = documents.delete(report["document"]["id"], "local")
    assert result["deleted_entries"] == 2

    assert repository.stats("local")["entries"] == 0
    assert matcher.match("tự động hóa chỉ huy", "local").matched is None
    assert documents.list("local") == []

    with pytest.raises(FaqDocumentNotFound):
        documents.delete(report["document"]["id"], "local")


def test_version_update_keeps_one_set_and_reports_stale(tmp_path: Path) -> None:
    _, repository, _, documents = make_services(tmp_path)
    documents.import_document("local", "de_a.docx", pairs(outline()))

    shortened = docx(
        paragraph("Câu I.1.1"),
        table([
            ["Đồng chí hãy trình bày khái niệm “Tự động hóa chỉ huy”?", "4 đ"],
            ["Đáp án", ""],
            ["Nội dung mới.", "0.5đ"],
        ]),
    )
    report = documents.import_document("local", "de_a.docx", pairs(shortened))

    assert report["reason"] == "updated"
    assert report["stale"] == 1
    assert len(documents.list("local")) == 1
    assert repository.stats("local")["entries"] == 2
    assert report["document"]["entry_count"] == 2


def test_documents_are_tenant_scoped(tmp_path: Path) -> None:
    _, _, _, documents = make_services(tmp_path)
    documents.import_document("local", "de_a.docx", pairs(outline()))
    documents.import_document("acme", "de_a.docx", pairs(outline(answer="khác.")))

    assert len(documents.list("local")) == 1
    assert len(documents.list("acme")) == 1
    assert documents.list("local")[0].id != documents.list("acme")[0].id
