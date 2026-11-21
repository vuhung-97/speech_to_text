"""Docx outline parser + question-set import: structure, cleaning, idempotency."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx_builder import docx, outline, paragraph, table  # noqa: E402

from backend.adapters.embedding.hashing import HashingEmbedder  # noqa: E402
from backend.adapters.importer.docx_faq import (DocxFormatError,  # noqa: E402
                                                parse_docx)
from backend.adapters.retrieval.sqlite_faq import (  # noqa: E402
    SqliteFaqMatcher, SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database  # noqa: E402
from backend.adapters.storage.sqlite_faq_documents import (  # noqa: E402
    SqliteFaqDocumentRepository)
from backend.services.faq_documents import FaqDocumentsService  # noqa: E402
from backend.services.faq_service import FaqService  # noqa: E402


def make_services(tmp_path: Path):
    database = Database(tmp_path / "app.db")
    repository = SqliteFaqRepository(database)
    embedder = HashingEmbedder()
    matcher = SqliteFaqMatcher(repository, embedder)
    catalogue = FaqService(repository, matcher, embedder)
    documents = FaqDocumentsService(SqliteFaqDocumentRepository(database),
                                    repository, catalogue, matcher)
    return catalogue, repository, matcher, documents


def import_docx(documents: FaqDocumentsService, data: bytes, name: str) -> dict:
    """Parse then import, mirroring what the HTTP layer does."""
    return documents.import_document("local", name, parse_docx(data))


# ----------------------------------------------------------------------- parser
def test_parse_tables_cleans_points_and_reads_inline_question() -> None:
    entries = parse_docx(outline())

    assert [item.code for item in entries] == ["Câu I.1.1", "Câu 2"]
    assert entries[0].category == "I.1"
    assert entries[0].question.startswith("Đồng chí hãy trình bày")
    assert entries[0].answer == "Nội dung một.\nNội dung hai."
    assert "0.5đ" not in entries[0].answer
    assert entries[1].category == ""
    assert entries[1].question == "Thủ đô Việt Nam là gì?"
    assert entries[1].answer == "Hà Nội."


def test_parse_paragraph_mode_when_no_tables() -> None:
    data = docx(
        paragraph("Câu 1"),
        paragraph("Thủ đô Việt Nam là gì?"),
        paragraph("4 đ"),
        paragraph("Đáp án:"),
        paragraph("Hà Nội."),
        paragraph("0.5đ"),
    )
    entries = parse_docx(data)
    assert len(entries) == 1
    assert entries[0].question == "Thủ đô Việt Nam là gì?"
    assert entries[0].answer == "Hà Nội."


def test_parse_rejects_non_docx_and_empty_outline() -> None:
    with pytest.raises(DocxFormatError, match="không phải .docx"):
        parse_docx("không phải zip".encode("utf-8"))
    with pytest.raises(DocxFormatError, match="không đọc được câu hỏi"):
        parse_docx(docx(paragraph("Chỉ có lời cảm ơn.")))


# ----------------------------------------------------------------------- import
def test_import_creates_a_question_set(tmp_path: Path) -> None:
    _, repository, _, documents = make_services(tmp_path)

    report = import_docx(documents, outline(), "de_cuong.docx")
    assert report["reason"] == "created"
    assert (report["total"], report["added"], report["updated"]) == (2, 2, 0)
    assert repository.stats("local")["entries"] == 2

    document = report["document"]
    stored = repository.find_by_source("local", document["id"], "Câu I.1.1")
    assert stored is not None
    assert stored.document_id == document["id"]
    assert stored.category == "I.1"
    assert stored.search_text == "tự động hóa chỉ huy"
    assert document["entry_count"] == 2


def test_import_unchanged_content_is_skipped(tmp_path: Path) -> None:
    _, repository, _, documents = make_services(tmp_path)
    import_docx(documents, outline(), "de_cuong.docx")

    again = import_docx(documents, outline(), "de_cuong.docx")
    assert again["reason"] == "unchanged"
    assert (again["added"], again["updated"], again["skipped"]) == (0, 0, 2)
    assert repository.stats("local")["entries"] == 2


def test_import_edited_content_updates_and_deactivates_stale(tmp_path: Path) -> None:
    _, repository, _, documents = make_services(tmp_path)
    import_docx(documents, outline(), "de_cuong.docx")

    # Drop one table question entirely: its entry must be switched off.
    edited = docx(
        paragraph("Câu I.1.1"),
        table([
            ["Đồng chí hãy trình bày khái niệm “Tự động hóa chỉ huy”?", "4 đ"],
            ["Đáp án", ""],
            ["Nội dung mới.", "0.5đ"],
            ["Nội dung hai.", "0.5đ"],
        ]),
    )
    changed = import_docx(documents, edited, "de_cuong.docx")

    assert changed["reason"] == "updated"
    assert (changed["added"], changed["updated"]) == (0, 1)
    assert changed["changed"]
    assert changed["stale"] == 1
    assert repository.stats("local")["entries"] == 2

    document_id = changed["document"]["id"]
    updated = repository.find_by_source("local", document_id, "Câu I.1.1")
    assert updated is not None and updated.answer.startswith("Nội dung mới.")
    gone = repository.find_by_source("local", document_id, "Câu 2")
    assert gone is not None and gone.active is False


def test_import_same_content_under_another_name_is_unchanged(tmp_path: Path) -> None:
    _, repository, _, documents = make_services(tmp_path)
    import_docx(documents, outline(), "de_cuong.docx")

    renamed = import_docx(documents, outline(), "bản_sao.docx")
    assert renamed["reason"] == "unchanged"
    assert renamed["document"]["name"] == "de_cuong.docx"
    assert len(documents.list("local")) == 1
    assert repository.stats("local")["entries"] == 2


def test_import_edited_content_under_new_name_creates_a_new_set(tmp_path: Path) -> None:
    _, repository, _, documents = make_services(tmp_path)
    import_docx(documents, outline(), "de_cuong.docx")

    edited = outline(answer="Nội dung mới.")
    changed = import_docx(documents, edited, "bản_sao.docx")
    assert changed["reason"] == "created"
    assert (changed["added"], changed["updated"]) == (2, 0)
    assert len(documents.list("local")) == 2
    assert repository.stats("local")["entries"] == 4


def test_import_embeds_new_entries(tmp_path: Path) -> None:
    _, _, matcher, documents = make_services(tmp_path)
    import_docx(documents, outline(), "de_cuong.docx")

    result = matcher.match("tự động hóa chỉ huy là gì", "local")
    assert result.matched is not None
    assert result.matched.entry.source_ref == "Câu I.1.1"
    assert result.matched.entry.answer.startswith("Nội dung một.")


def test_import_does_not_merge_near_duplicate_questions(tmp_path: Path) -> None:
    """Two different codes may carry almost identical wording; both must survive."""
    data = docx(
        paragraph("Câu I.1.7"),
        table([["Đồng chí hãy trình bày vai trò của hệ thống C2?", "2 đ"],
               ["Đáp án", ""], ["Vai trò.", "2đ"]]),
        paragraph("Câu I.1.8"),
        table([["Đồng chí hãy trình bày chức năng của hệ thống C2?", "2 đ"],
               ["Đáp án", ""], ["Chức năng.", "2đ"]]),
    )
    _, repository, _, documents = make_services(tmp_path)
    report = import_docx(documents, data, "de_cuong.docx")

    assert report["added"] == 2
    assert repository.stats("local")["entries"] == 2


def test_import_is_tenant_scoped(tmp_path: Path) -> None:
    _, _, matcher, documents = make_services(tmp_path)
    import_docx(documents, outline(), "de_cuong.docx")

    assert documents.list("acme") == []
    assert matcher.match("tự động hóa chỉ huy là gì", "acme").matched is None
