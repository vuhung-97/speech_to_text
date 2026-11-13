"""Value objects for the FAQ catalogue. No persistence, no embedding math."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    """Outcome of one lookup, threshold included so the caller never guesses."""

    matched: FaqMatch | None
    candidates: tuple[FaqMatch, ...] = ()
    threshold: float = 0.84
    near_threshold: float = 0.78

    @property
    def near_miss(self) -> bool:
        """True when the best score is close enough that the UI should warn."""
        best = self.matched.score if self.matched else (
            self.candidates[0].score if self.candidates else 0.0)
        return best >= self.near_threshold and best < self.threshold


__all__ = ["FaqEntry", "FaqMatch", "FaqResult"]
