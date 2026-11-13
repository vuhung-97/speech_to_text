"""Value objects for one question → answer exchange.

They stay framework-free so the QA service and the future FAQ matcher can be
tested without FastAPI, SQLite or the speech engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..faq.models import FaqMatch


class AnswerStatus(StrEnum):
    MATCHED = "matched"
    NEAR_MISS = "near_miss"
    UNANSWERED = "unanswered"


@dataclass(frozen=True)
class Question:
    """A single question as heard (or typed)."""

    text: str
    session_id: str | None = None
    source: str = "voice"  # voice | typed


@dataclass(frozen=True)
class Answer:
    """What the UI renders: approved text, match metadata and speech handles."""

    id: str
    turn_id: str
    text: str
    status: AnswerStatus
    matched: FaqMatch | None = None
    candidates: tuple[FaqMatch, ...] = ()
    entry_id: str | None = None
    score: float | None = None
    audio_url: str | None = None
    seconds: float | None = None
    meta: dict[str, object] = field(default_factory=dict)

    @property
    def answered(self) -> bool:
        return self.status in (AnswerStatus.MATCHED, AnswerStatus.NEAR_MISS)


FALLBACK_TEXT = (
    "Tôi chưa có câu trả lời cho câu hỏi này. "
    "Bạn có thể hỏi lại theo cách khác, hoặc thêm câu trả lời vào kho câu hỏi."
)


__all__ = ["Answer", "AnswerStatus", "FALLBACK_TEXT", "Question"]
