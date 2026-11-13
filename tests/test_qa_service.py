"""QaService: validation, match statuses, fallback and lookup logging."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.retrieval.null import NullFaqMatcher
from backend.adapters.storage.sqlite import (Database, SqliteQueryLog,
                                             SqliteSessionRepository)
from backend.domain.faq.models import FaqEntry, FaqMatch, FaqResult
from backend.domain.qa.models import (FALLBACK_TEXT, MAX_QUESTION_CHARS,
                                      AnswerStatus, SessionNotFound)
from backend.services.qa_service import QaService


class FixedMatcher:
    """Returns a canned result so the service logic is tested in isolation."""

    def __init__(self, score: float | None, answered: bool = True) -> None:
        self.score = score
        self._answered = answered
        self.calls: list[tuple[str, str]] = []

    def match(self, question: str, tenant: str, k: int = 3) -> FaqResult:
        self.calls.append((question, tenant))
        if self.score is None:
            return FaqResult(matched=None, candidates=())
        entry = FaqEntry(id="e1", tenant_id=tenant, question="Câu hỏi gốc",
                         answer="Câu trả lời đã duyệt.", category="chung")
        match = FaqMatch(entry=entry, score=self.score)
        return FaqResult(matched=match, candidates=(match,))


def make(tmp_path: Path, matcher):
    database = Database(tmp_path / "app.db")
    sessions = SqliteSessionRepository(database)
    log = SqliteQueryLog(database)
    return QaService(matcher, sessions, log), sessions, log


def test_unanswered_uses_fallback_and_logs(tmp_path: Path) -> None:
    service, sessions, log = make(tmp_path, NullFaqMatcher())

    outcome = service.ask("Thủ đô Việt Nam là gì?", tenant="local")

    assert outcome.answer.status is AnswerStatus.UNANSWERED
    assert outcome.answer.text == FALLBACK_TEXT
    assert outcome.answer.matched is None
    assert outcome.session_id
    detail = sessions.get_session(outcome.session_id, "local")
    assert detail["turns"][0]["answer"]["status"] == "unanswered"
    assert log.unanswered("local")[0]["question_norm"] == "thủ đô việt nam là gì"


def test_confident_match_returns_curated_text(tmp_path: Path) -> None:
    matcher = FixedMatcher(score=0.93)
    service, sessions, log = make(tmp_path, matcher)

    outcome = service.ask("Câu hỏi gốc", tenant="local")

    assert outcome.answer.status is AnswerStatus.MATCHED
    assert outcome.answer.text == "Câu trả lời đã duyệt."
    assert outcome.answer.entry_id == "e1"
    assert outcome.answer.score == pytest.approx(0.93)
    assert matcher.calls == [("Câu hỏi gốc", "local")]
    assert log.unanswered("local") == []
    assert sessions.get_session(outcome.session_id, "local")["turns"][0]["answer"]["score"] == pytest.approx(0.93)


def test_near_miss_answers_but_flags_the_turn(tmp_path: Path) -> None:
    service, _, _ = make(tmp_path, FixedMatcher(score=0.80))

    outcome = service.ask("Câu hỏi gần đúng", tenant="local")

    assert outcome.answer.status is AnswerStatus.NEAR_MISS
    assert outcome.answer.text == "Câu trả lời đã duyệt."
    assert outcome.answer.answered is True


def test_empty_and_oversized_questions_are_rejected(tmp_path: Path) -> None:
    service, _, _ = make(tmp_path, NullFaqMatcher())

    with pytest.raises(ValueError, match="chưa có câu hỏi"):
        service.ask("   ", tenant="local")
    with pytest.raises(ValueError, match="quá dài"):
        service.ask("a" * (MAX_QUESTION_CHARS + 1), tenant="local")


def test_session_is_reused_and_title_kept(tmp_path: Path) -> None:
    service, sessions, _ = make(tmp_path, NullFaqMatcher())

    first = service.ask("Câu thứ nhất", tenant="local")
    second = service.ask("Câu thứ hai", tenant="local",
                         session_id=first.session_id)

    assert second.session_id == first.session_id
    detail = sessions.get_session(first.session_id, "local")
    assert [turn["question"] for turn in detail["turns"]] == [
        "Câu thứ nhất", "Câu thứ hai"]
    assert detail["title"] == "Câu thứ nhất"

    with pytest.raises(SessionNotFound):
        service.ask("Câu mồ côi", tenant="local", session_id="khong-ton-tai")


def test_tenant_scope_is_forwarded(tmp_path: Path) -> None:
    matcher = FixedMatcher(score=0.9)
    service, sessions, _ = make(tmp_path, matcher)

    service.ask("câu hỏi", tenant="acme")
    assert matcher.calls[0][1] == "acme"
    assert sessions.list_sessions("local") == []
    assert len(sessions.list_sessions("acme")) == 1
