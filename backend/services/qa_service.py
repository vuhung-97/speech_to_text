"""Question → catalogue lookup → answer orchestration.

One responsibility: turn a question into a persisted, renderable answer. The
matcher decides *what* the answer is; this service owns validation, session and
turn bookkeeping, the fallback text and the lookup log. It deliberately knows
nothing about HTTP or speech.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ..domain.qa.models import (MAX_QUESTION_CHARS, Answer, AnswerStatus,
                                FALLBACK_TEXT, Question)
from ..ports.faq import FaqMatcher, QueryLog
from ..ports.sessions import SessionRepository


@dataclass(frozen=True)
class QaOutcome:
    """Everything the controller needs for one exchange."""

    answer: Answer
    session_id: str
    question: str


class QaService:
    def __init__(self, matcher: FaqMatcher, sessions: SessionRepository,
                 query_log: QueryLog) -> None:
        self._matcher = matcher
        self._sessions = sessions
        self._log = query_log

    def ask(
        self,
        question: str,
        *,
        tenant: str,
        session_id: str | None = None,
        source: str = "voice",
    ) -> QaOutcome:
        value = (question or "").strip()
        if not value:
            raise ValueError("chưa có câu hỏi nào")
        if len(value) > MAX_QUESTION_CHARS:
            raise ValueError(
                f"câu hỏi quá dài ({len(value)} ký tự, tối đa {MAX_QUESTION_CHARS})")

        session = session_id or self._sessions.create_session(tenant, title=value)
        turn_id = self._sessions.add_turn(
            session, tenant, Question(text=value, session_id=session, source=source))

        result = self._matcher.match(value, tenant)
        if result.matched is not None:
            status = (AnswerStatus.MATCHED if result.accepted
                      else AnswerStatus.NEAR_MISS)
            text = result.matched.entry.answer
            entry_id = result.matched.entry.id
            score: float | None = result.matched.score
        else:
            status = AnswerStatus.UNANSWERED
            text = FALLBACK_TEXT
            entry_id = None
            score = result.best_score or None

        answer = Answer(
            id=uuid.uuid4().hex[:16],
            turn_id=turn_id,
            text=text,
            status=status,
            matched=result.matched,
            candidates=result.candidates,
            entry_id=entry_id,
            score=score,
            session_id=session,
        )
        self._sessions.save_answer(turn_id, tenant, answer)
        self._log.record(
            tenant=tenant,
            session_id=session,
            question=value,
            matched_entry_id=entry_id,
            score=score,
            answered=answer.answered,
        )
        return QaOutcome(answer=answer, session_id=session, question=value)


__all__ = ["QaOutcome", "QaService"]
