"""Value objects for the FAQ catalogue. No persistence, no embedding math."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DEFAULT_THRESHOLD = 0.88   # tuned on multilingual-e5-small: in-domain ≥0.89,
DEFAULT_NEAR = 0.88        # off-topic ≤0.87, so no "answer with warning" band


@dataclass(frozen=True)
class FaqEntry:
    """One curated question/answer pair owned by a tenant."""

    id: str
    tenant_id: str
    question: str
    answer: str
    category: str = ""
    active: bool = True
    embed_model: str = ""
    embed_version: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def words(self) -> int:
        from ..text.limits import word_count

        return word_count(self.answer)


@dataclass(frozen=True)
class FaqMatch:
    """An entry plus the cosine similarity that selected it."""

    entry: FaqEntry
    score: float

    @property
    def percent(self) -> int:
        return round(max(0.0, min(1.0, self.score)) * 100)


@dataclass(frozen=True)
class FaqResult:
    """Outcome of one lookup.

    ``matched`` is the best entry when it clears ``near_threshold``: the caller
    answers it, and marks the turn NEAR_MISS when it is still below the stricter
    ``threshold`` so the UI can show a warning chip. Below ``near_threshold``
    the question is unanswered and only suggestions are returned.
    """

    matched: FaqMatch | None
    candidates: tuple[FaqMatch, ...] = ()
    threshold: float = DEFAULT_THRESHOLD
    near_threshold: float = DEFAULT_NEAR

    @property
    def accepted(self) -> bool:
        """True when the best score clears the strict threshold."""
        return bool(self.matched and self.matched.score >= self.threshold)

    @property
    def near_miss(self) -> bool:
        return bool(self.matched and not self.accepted)

    @property
    def best_score(self) -> float:
        if self.matched:
            return self.matched.score
        if self.candidates:
            return self.candidates[0].score
        return 0.0


__all__ = ["DEFAULT_NEAR", "DEFAULT_THRESHOLD", "FaqEntry", "FaqMatch", "FaqResult"]
