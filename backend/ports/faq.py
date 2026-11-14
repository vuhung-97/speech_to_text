"""Catalogue lookup contracts.

``FaqMatcher`` answers one question; ``FaqRepository`` owns curated entries and
their embeddings; ``QueryLog`` records every lookup so the operator can see what
users actually ask and which questions have no answer yet. Splitting the log
from the catalogue keeps the matcher free of write concerns.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from ..domain.faq.models import FaqEntry, FaqResult


class FaqMatcher(Protocol):
    """Find the curated question that best matches what the user just said."""

    def match(self, question: str, tenant: str, k: int = 3) -> FaqResult:
        """Return the best match (if any) plus ``k`` nearest candidates."""
        ...


class FaqRepository(Protocol):
    """Tenant-scoped storage for curated entries and their vectors."""

    def get(self, entry_id: str, tenant: str) -> FaqEntry | None: ...

    def list(
        self,
        tenant: str,
        *,
        query: str | None = None,
        category: str | None = None,
        active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[FaqEntry]: ...

    def upsert(self, entry: FaqEntry) -> FaqEntry: ...

    def delete(self, entry_id: str, tenant: str) -> None: ...

    def all_active(self, tenant: str) -> Sequence[FaqEntry]: ...

    def pending_embeddings(self, tenant: str, model: str,
                           version: int) -> Sequence[FaqEntry]: ...

    def set_embedding(self, entry_id: str, tenant: str, embedding: np.ndarray,
                      model: str, version: int) -> None: ...

    def embeddings(self, tenant: str) -> Sequence[tuple[FaqEntry, np.ndarray]]: ...

    def index_signature(self, tenant: str) -> tuple[int, float, int]: ...

    def stats(self, tenant: str) -> dict[str, object]: ...


class QueryLog(Protocol):
    """Every question asked, with the outcome, for tuning and follow-up."""

    def record(
        self,
        *,
        tenant: str,
        session_id: str | None,
        question: str,
        matched_entry_id: str | None,
        score: float | None,
        answered: bool,
    ) -> None: ...

    def unanswered(self, tenant: str, limit: int = 50) -> Sequence[dict[str, object]]:
        """Questions that found no answer, newest first."""
        ...


__all__ = ["FaqMatcher", "FaqRepository", "QueryLog"]
