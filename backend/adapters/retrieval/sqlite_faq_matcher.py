"""In-RAM cosine index over the SQLite catalogue, reranked with BM25.

Keeps one L2-normalised ``(N, dim)`` matrix per tenant in RAM, so a lookup is a
single dot product, then reranks the cosine neighbourhood with a BM25 index
over the same entries (cheap, pure Python, no extra dependency). The index is
rebuilt only when the catalogue signature changes (count / updated_at /
embed_version); entries missing an embedding are embedded lazily the first time
they are needed.
"""

from __future__ import annotations

import threading

import numpy as np

from ...domain.faq.lexical import Bm25Index
from ...domain.faq.models import (DEFAULT_NEAR, DEFAULT_THRESHOLD, FaqEntry,
                                   FaqMatch, FaqResult)
from ...domain.faq.query import focus_question
from ...ports.embedding import Embedder
from .sqlite_faq_repo import SqliteFaqRepository

# Cosine picks the neighbourhood, BM25 only reorders it: the embedding decides
# whether we answer, the lexical score decides which near-identical wording wins.
LEXICAL_WEIGHT = 0.2
RERANK_POOL = 10


class SqliteFaqMatcher:
    """Cosine search over an in-RAM matrix, reranked with BM25, refreshed on change."""

    def __init__(self, repository: SqliteFaqRepository, embedder: Embedder,
                 threshold: float = DEFAULT_THRESHOLD,
                 near_threshold: float = DEFAULT_NEAR,
                 batch_size: int = 32) -> None:
        self._repo = repository
        self._embedder = embedder
        self.threshold = float(threshold)
        self.near_threshold = float(near_threshold)
        self._batch = max(1, int(batch_size))
        self._cache: dict[str, tuple[tuple[int, float, int], list[FaqEntry],
                                     np.ndarray, Bm25Index]] = {}
        self._lock = threading.Lock()

    @property
    def model_id(self) -> str:
        return getattr(self._embedder, "model_id", "unknown")

    @property
    def version(self) -> int:
        return int(getattr(self._embedder, "version", 0))

    @property
    def dim(self) -> int:
        return int(getattr(self._embedder, "dim", 0))

    # ------------------------------------------------------------------ index
    def ensure_index(self, tenant: str) -> tuple[list[FaqEntry], np.ndarray]:
        """Embed anything pending, then return the current matrix snapshot."""
        entries, matrix, _ = self._snapshot(tenant)
        return entries, matrix

    def _snapshot(self, tenant: str) -> tuple[list[FaqEntry], np.ndarray,
                                              Bm25Index]:
        signature = self._repo.index_signature(tenant)
        cached = self._cache.get(tenant)
        if cached and cached[0] == signature:
            return cached[1], cached[2], cached[3]

        with self._lock:
            signature = self._repo.index_signature(tenant)
            cached = self._cache.get(tenant)
            if cached and cached[0] == signature:
                return cached[1], cached[2], cached[3]

            pending = self._repo.pending_embeddings(
                tenant, self.model_id, self.version)
            for start in range(0, len(pending), self._batch):
                chunk = pending[start:start + self._batch]
                vectors = self._embedder.embed_documents(
                    [_search_text(item) for item in chunk])
                for item, vector in zip(chunk, vectors):
                    self._repo.set_embedding(item.id, tenant, vector,
                                             self.model_id, self.version)

            rows = self._repo.embeddings(tenant)
            entries = [entry for entry, _ in rows]
            if rows:
                matrix = np.vstack([vector for _, vector in rows]).astype(np.float32)
            else:
                matrix = np.zeros((0, self.dim), dtype=np.float32)
            lexical = Bm25Index([_search_text(entry) for entry in entries])
            self._cache[tenant] = (self._repo.index_signature(tenant), entries,
                                   matrix, lexical)
            return entries, matrix, lexical

    def invalidate(self, tenant: str) -> None:
        with self._lock:
            self._cache.pop(tenant, None)

    # ------------------------------------------------------------------ match
    def match(self, question: str, tenant: str, k: int = 3,
              document_id: str | None = None) -> FaqResult:
        """Best match (optionally inside one question set) plus candidates."""
        entries, matrix, lexical = self._snapshot(tenant)
        if document_id:
            subset = [index for index, entry in enumerate(entries)
                      if entry.document_id == document_id]
            if not subset:
                return self._empty_result()
            entries = [entries[index] for index in subset]
            matrix = matrix[subset]
            lexical = Bm25Index([_search_text(entry) for entry in entries])
        if not entries or matrix.size == 0:
            return self._empty_result()

        query_text = focus_question(question)
        query = np.asarray(self._embedder.embed_query(query_text), dtype=np.float32)
        if query.size != matrix.shape[1]:
            return self._empty_result()

        cosine = matrix @ query
        pool = min(len(entries), max(RERANK_POOL, int(k) + 1))
        candidates = np.argsort(-cosine)[:pool]

        # Cosine gates acceptance; BM25 only decides the order inside the pool.
        relevance = lexical.scores(query_text)[candidates]
        normalised = (relevance / relevance.max()) if relevance.max() > 0 else relevance
        ranking = (1.0 - LEXICAL_WEIGHT) * cosine[candidates] + LEXICAL_WEIGHT * normalised
        order = candidates[np.argsort(-ranking)]

        matches = [FaqMatch(entry=entries[index], score=float(cosine[index]))
                   for index in order]
        best = matches[0]
        if best.score >= self.near_threshold:
            return FaqResult(matched=best, candidates=tuple(matches[1:k + 1]),
                             threshold=self.threshold,
                             near_threshold=self.near_threshold)
        return FaqResult(matched=None, candidates=tuple(matches[:k]),
                         threshold=self.threshold,
                         near_threshold=self.near_threshold)

    def _empty_result(self) -> FaqResult:
        return FaqResult(matched=None, candidates=(),
                         threshold=self.threshold,
                         near_threshold=self.near_threshold)


def _search_text(entry: FaqEntry) -> str:
    """Text the embedder and BM25 index see; older rows fall back to the question."""
    return entry.search_text or entry.question


__all__ = ["LEXICAL_WEIGHT", "RERANK_POOL", "SqliteFaqMatcher"]
