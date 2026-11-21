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

from ..domain.faq.models import (FaqDocument, FaqEntry, FaqOutline,
                                 FaqResult)


class FaqMatcher(Protocol):
    """Find the curated question that best matches what the user just said."""

    def match(self, question: str, tenant: str, k: int = 3,
              document_id: str | None = None) -> FaqResult:
        """Return the best match (if any) plus ``k`` nearest candidates.

        When ``document_id`` is given, only that question set is searched.
        """
        ...


class FaqIndex(Protocol):
    """Search index used by the admin service: refresh, invalidate, describe."""

    threshold: float
    near_threshold: float

    @property
    def model_id(self) -> str: ...

    @property
    def version(self) -> int: ...

    @property
    def dim(self) -> int: ...

    def ensure_index(self, tenant: str) -> tuple[Sequence[FaqEntry], np.ndarray]: ...

    def invalidate(self, tenant: str) -> None: ...


class FaqOutlineParser(Protocol):
    """Turn an uploaded outline document into ordered question/answer pairs."""

    def __call__(self, data: bytes) -> Sequence[FaqOutline]:
        """Raise ``ValueError`` when the file is not a readable outline."""
        ...


class FaqRepository(Protocol):
    """Tenant-scoped storage for curated entries and their vectors."""

    def get(self, entry_id: str, tenant: str) -> FaqEntry | None: ...

    def find_by_norm(self, tenant: str, norm: str) -> FaqEntry | None: ...

    def find_by_norm_in_document(self, tenant: str, document_id: str,
                                 norm: str) -> FaqEntry | None: ...

    def find_by_source(self, tenant: str, document_id: str,
                       source_ref: str) -> FaqEntry | None: ...

    def list(
        self,
        tenant: str,
        *,
        query: str | None = None,
        category: str | None = None,
        active: bool | None = None,
        document_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[FaqEntry]: ...

    def upsert(self, entry: FaqEntry) -> FaqEntry: ...

    def delete(self, entry_id: str, tenant: str) -> bool: ...

    def all_active(self, tenant: str) -> Sequence[FaqEntry]: ...

    def pending_embeddings(self, tenant: str, model: str,
                           version: int) -> Sequence[FaqEntry]: ...

    def set_embedding(self, entry_id: str, tenant: str, embedding: np.ndarray,
                      model: str, version: int) -> None: ...

    def embeddings(self, tenant: str) -> Sequence[tuple[FaqEntry, np.ndarray]]: ...

    def index_signature(self, tenant: str) -> tuple[int, float, int]: ...

    def stats(self, tenant: str) -> dict[str, object]: ...

    def count_in_document(self, tenant: str, document_id: str) -> int: ...

    def deactivate_missing(self, tenant: str, document_id: str,
                           keep_refs: set[str]) -> int: ...

    def delete_by_document(self, tenant: str, document_id: str) -> list[str]: ...


class FaqDocumentRepository(Protocol):
    """Tenant-scoped storage for uploaded question sets."""

    def get(self, document_id: str, tenant: str) -> FaqDocument | None: ...

    def list(self, tenant: str) -> Sequence[FaqDocument]: ...

    def find_by_name(self, tenant: str, name: str) -> FaqDocument | None: ...

    def find_by_hash(self, tenant: str, content_hash: str) -> FaqDocument | None: ...

    def create(self, tenant: str, name: str, content_hash: str) -> FaqDocument: ...

    def update(self, document_id: str, tenant: str, *, name: str | None = None,
               content_hash: str | None = None,
               entry_count: int | None = None) -> FaqDocument | None: ...

    def delete(self, document_id: str, tenant: str) -> bool: ...


class FaqAudioRepository(Protocol):
    """Tenant-scoped cache of pre-rendered answer audio."""

    def get_audio(self, entry_id: str, tenant: str,
                  voice: str) -> dict[str, object] | None: ...

    def put_audio(self, entry_id: str, tenant: str, *, voice: str,
                  sample_rate: int, path: str, seconds: float,
                  bytes_: int) -> None: ...

    def delete_audio(self, entry_id: str, tenant: str,
                     voice: str | None = None) -> None: ...

    def audio_usage(self, tenant: str) -> int: ...

    def oldest_audio(self, tenant: str,
                     limit: int = 20) -> Sequence[dict[str, object]]: ...


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


__all__ = [
    "FaqAudioRepository",
    "FaqDocumentRepository",
    "FaqIndex",
    "FaqMatcher",
    "FaqOutlineParser",
    "FaqRepository",
    "QueryLog",
]
