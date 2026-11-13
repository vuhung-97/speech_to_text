"""Catalogue lookup and storage contracts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..domain.faq.models import FaqEntry, FaqResult


class FaqMatcher(Protocol):
    """Find the curated question that best matches what the user just said."""

    def match(self, question: str, tenant: str, k: int = 3) -> FaqResult:
        """Return the best match (if any) plus ``k`` nearest candidates."""
        ...


class FaqRepository(Protocol):
    """Tenant-scoped persistence for curated entries and query logs."""

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

    def log_query(
        self,
        *,
        tenant: str,
        session_id: str | None,
        question: str,
        matched_entry_id: str | None,
        score: float | None,
    ) -> None: ...

    def unanswered(self, tenant: str, limit: int = 50) -> Sequence[dict[str, object]]:
        """Questions that found no answer, newest first."""
        ...


__all__ = ["FaqMatcher", "FaqRepository"]
