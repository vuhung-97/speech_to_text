"""FaqService: validation, duplicates, update, CSV import, reindex, stats."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.embedding.hashing import HashingEmbedder
from backend.adapters.retrieval.sqlite_faq import (SqliteFaqMatcher,
                                                   SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database
from backend.domain.faq.rules import DUPLICATE_THRESHOLD
from backend.domain.text.limits import MAX_TTS_WORDS
from backend.services.faq_service import FaqService


@pytest.fixture()
def catalogue(tmp_path: Path):
    database = Database(tmp_path / "app.db")
    repo = SqliteFaqRepository(database)
    embedder = HashingEmbedder()
    matcher = SqliteFaqMatcher(repo, embedder)
    return FaqService(repo, matcher, embedder), matcher


@pytest.fixture()
def faq(catalogue) -> FaqService:
    return catalogue[0]


@pytest.fixture()
def matcher(catalogue):
    return catalogue[1]


def test_create_validates_and_persists(faq: FaqService) -> None:
    entry = faq.create("local", "  Thủ đô Việt Nam là gì?  ", " Hà Nội. ", "địa lý")
    assert entry.question == "Thủ đô Việt Nam là gì?"
    assert entry.answer == "Hà Nội."
    assert entry.category == "địa lý"
    assert faq.stats("local")["entries"] == 1


@pytest.mark.parametrize("question,answer,message", [
    ("", "đáp án", "câu hỏi không được để trống"),
    ("hỏi", "   ", "câu trả lời không được để trống"),
    ("a" * 501, "đáp án", "câu hỏi quá dài"),
    ("hỏi", "từ " * (MAX_TTS_WORDS + 1), "câu trả lời quá dài"),
])
def test_create_rejects_invalid(faq: FaqService, question: str, answer: str,
                                message: str) -> None:
    with pytest.raises(ValueError, match=message):
        faq.create("local", question, answer)


def test_duplicate_question_is_rejected(faq: FaqService) -> None:
    faq.create("local", "Quy trình đăng ký?", "Ba bước.")
    with pytest.raises(ValueError, match="đã có trong kho"):
        faq.create("local", "  Quy trình đăng ký?  ", "Khác.")


def test_update_reembeds_and_matches_new_answer(faq: FaqService, matcher) -> None:
    entry = faq.create("local", "Thủ đô Việt Nam là gì?", "Hà Nội.")
    assert matcher.match("Thủ đô Việt Nam là gì", "local").matched

    updated = faq.update(entry.id, "local", {"answer": "Thủ đô là Hà Nội."})
    assert updated.answer == "Thủ đô là Hà Nội."

    result = matcher.match("Thủ đô Việt Nam là gì", "local")
    assert result.matched.entry.answer == "Thủ đô là Hà Nội."


def test_update_missing_entry_raises(faq: FaqService) -> None:
    with pytest.raises(ValueError, match="không tìm thấy"):
        faq.update("missing", "local", {"answer": "x"})


def test_delete(faq: FaqService, matcher) -> None:
    entry = faq.create("local", "Câu hỏi?", "Đáp án.")
    assert faq.delete(entry.id, "local") is True
    assert faq.delete(entry.id, "local") is False
    assert matcher.match("Câu hỏi?", "local").matched is None


def test_import_csv_report(faq: FaqService) -> None:
    faq.create("local", "Đã có trong kho?", "Đáp án cũ.")
    content = (
        "question,answer,category\n"
        "Câu mới một?,Đáp án một.,chung\n"
        "Đã có trong kho?,Đáp án khác.,chung\n"
        "Câu lỗi?,   ,chung\n"
        "Câu mới hai?,Đáp án hai.,\n"
    )

    report = faq.import_csv("local", content)

    assert report["total"] == 4
    assert report["added"] == 2
    assert len(report["duplicates"]) == 1
    assert len(report["errors"]) == 1
    assert report["errors"][0]["row"] == 4
    assert faq.stats("local")["entries"] == 3


def test_import_skips_near_duplicates(faq: FaqService) -> None:
    faq.create("local", "Thủ đô Việt Nam là gì?", "Hà Nội.")
    report = faq.import_csv(
        "local", "question,answer\nThủ đô Việt Nam là gì,Đáp án khác\n")
    assert report["added"] == 0
    assert report["duplicates"][0]["score"] >= DUPLICATE_THRESHOLD


def test_reindex_and_stats(faq: FaqService) -> None:
    faq.create("local", "Câu một?", "Đáp án một.")
    faq.create("local", "Câu hai?", "Đáp án hai.")

    result = faq.reindex("local")
    assert result["indexed"] == 2
    assert result["dim"] == HashingEmbedder.dim
    assert result["model"] == "hashing-char3"

    stats = faq.stats("local")
    assert stats["entries"] == 2
    assert stats["embedded"] == 2
    assert stats["threshold"] == pytest.approx(0.88)
