"""Value objects for the FAQ catalogue. No persistence, no embedding math."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


DEFAULT_THRESHOLD = 0.88   # tuned on multilingual-e5-small: in-domain ≥0.90,
DEFAULT_NEAR = 0.86        # off-topic ≤0.82, so "near" is the answer floor

MAX_DOCUMENT_NAME_CHARS = 120
CONTENT_HASH_PREFIX = 12  # short fingerprint shown in API payloads


class FaqEntryNotFound(ValueError):
    """The requested entry does not exist in this tenant's catalogue."""


class FaqDocumentNotFound(ValueError):
    """The requested question set does not exist in this tenant's catalogue."""


@dataclass(frozen=True)
class FaqOutline:
    """One question/answer pair read from an uploaded outline document.

    Transport- and format-agnostic on purpose: the parser adapter produces these,
    the catalogue service validates and stores them.
    """

    code: str
    category: str
    question: str
    answer: str


def outline_fingerprint(pairs: Sequence[FaqOutline]) -> str:
    """Stable hash of the parsed content, independent of the file's bytes.

    Word rewrites zip metadata every save, so hashing the upload would treat an
    unchanged document as new. Hashing the extracted pairs recognises identical
    content even after "save as" or a rename.
    """
    payload = "\n".join(
        f"{pair.code}\u0000{pair.question}\u0000{pair.answer}" for pair in pairs)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FaqDocument:
    """One uploaded question set owned by a tenant."""

    id: str
    tenant_id: str
    name: str
    content_hash: str = ""
    entry_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0


def document_to_dict(document: FaqDocument) -> dict[str, Any]:
    """One wire shape for a question set (import report and list endpoint)."""
    return {
        "id": document.id,
        "name": document.name,
        "entry_count": document.entry_count,
        "content_hash": document.content_hash[:CONTENT_HASH_PREFIX],
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


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
    # Text actually embedded: the question stripped of outline wording. Empty
    # means "derive from question", so rows written before this column keep working.
    search_text: str = ""
    # Provenance of imported entries (file + code inside that file). Used to
    # update instead of duplicating on re-import; never embedded, never shown
    # on the answer screen.
    source_file: str = ""
    source_ref: str = ""
    # The question set this entry belongs to; empty for manually added rows.
    document_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def score_percent(score: float) -> int:
    """Cosine score (0..1) as the integer percentage shown in the UI.

    One conversion point: the API, the session history and ``FaqMatch.percent``
    must all render the same number for the same score.
    """
    return round(max(0.0, min(1.0, float(score))) * 100)


@dataclass(frozen=True)
class FaqMatch:
    """An entry plus the cosine similarity that selected it."""

    entry: FaqEntry
    score: float

    @property
    def percent(self) -> int:
        return score_percent(self.score)


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


__all__ = [
    "CONTENT_HASH_PREFIX",
    "DEFAULT_NEAR",
    "DEFAULT_THRESHOLD",
    "FaqDocument",
    "FaqDocumentNotFound",
    "FaqEntry",
    "FaqEntryNotFound",
    "FaqMatch",
    "FaqOutline",
    "FaqResult",
    "MAX_DOCUMENT_NAME_CHARS",
    "document_to_dict",
    "outline_fingerprint",
    "score_percent",
]
