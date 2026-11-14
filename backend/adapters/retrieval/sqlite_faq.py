"""SQLite catalogue repository and the in-RAM cosine index.

Repository: CRUD plus embedding storage, always tenant-scoped.
Matcher: keeps one L2-normalised ``(N, dim)`` matrix per tenant in RAM, so a
lookup is a single dot product. The matrix is rebuilt only when the catalogue
signature changes (count / updated_at / embed_version), and entries missing an
embedding are embedded lazily the first time they are needed.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Sequence

import numpy as np

from ...domain.faq.models import (DEFAULT_NEAR, DEFAULT_THRESHOLD, FaqEntry,
                                   FaqMatch, FaqResult)
from ...domain.faq.normalize import normalize_question
from ...ports.embedding import Embedder
from ..storage.sqlite import Database

_COLUMNS = ("id, tenant_id, question, answer, category, active, embed_model,"
            " embed_version, created_at, updated_at")


def _row_to_entry(row) -> FaqEntry:
    return FaqEntry(
        id=row["id"],
        tenant_id=row["tenant_id"],
        question=row["question"],
        answer=row["answer"],
        category=row["category"],
        active=bool(row["active"]),
        embed_model=row["embed_model"] or "",
        embed_version=int(row["embed_version"] or 0),
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
    )


class SqliteFaqRepository:
    def __init__(self, database: Database) -> None:
        self._db = database

    # ------------------------------------------------------------------- CRUD
    def get(self, entry_id: str, tenant: str) -> FaqEntry | None:
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_entries WHERE id = ? AND tenant_id = ?",
                (entry_id, tenant),
            ).fetchone()
        return _row_to_entry(row) if row else None

    def list(self, tenant: str, *, query: str | None = None,
             category: str | None = None, active: bool | None = None,
             limit: int = 50, offset: int = 0) -> Sequence[FaqEntry]:
        sql = [f"SELECT {_COLUMNS} FROM faq_entries WHERE tenant_id = ?"]
        params: list[object] = [tenant]
        if query:
            sql.append("AND (question LIKE ? OR answer LIKE ?)")
            needle = f"%{query.strip()}%"
            params.extend([needle, needle])
        if category:
            sql.append("AND category = ?")
            params.append(category)
        if active is not None:
            sql.append("AND active = ?")
            params.append(1 if active else 0)
        sql.append("ORDER BY updated_at DESC LIMIT ? OFFSET ?")
        params.extend([max(1, min(int(limit), 200)), max(0, int(offset))])
        with self._db.connect() as connection:
            rows = connection.execute(" ".join(sql), params).fetchall()
        return [_row_to_entry(row) for row in rows]

    def upsert(self, entry: FaqEntry) -> FaqEntry:
        now = time.time()
        entry_id = entry.id or uuid.uuid4().hex[:16]
        with self._db.connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM faq_entries WHERE id = ? AND tenant_id = ?",
                (entry_id, entry.tenant_id),
            ).fetchone()
            created = float(existing["created_at"]) if existing else now
            connection.execute(
                """
                INSERT INTO faq_entries (id, tenant_id, question, answer, category,
                                         active, embedding, embed_model,
                                         embed_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 0, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    question = excluded.question,
                    answer = excluded.answer,
                    category = excluded.category,
                    active = excluded.active,
                    embedding = NULL,
                    embed_model = NULL,
                    embed_version = 0,
                    updated_at = excluded.updated_at
                """,
                (entry_id, entry.tenant_id, entry.question, entry.answer,
                 entry.category, 1 if entry.active else 0, created, now),
            )
        return FaqEntry(
            id=entry_id,
            tenant_id=entry.tenant_id,
            question=entry.question,
            answer=entry.answer,
            category=entry.category,
            active=entry.active,
            created_at=created,
            updated_at=now,
        )

    def delete(self, entry_id: str, tenant: str) -> bool:
        with self._db.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM faq_entries WHERE id = ? AND tenant_id = ?",
                (entry_id, tenant),
            )
            return cursor.rowcount > 0

    # -------------------------------------------------------------- embeddings
    def all_active(self, tenant: str) -> Sequence[FaqEntry]:
        with self._db.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_entries"
                " WHERE tenant_id = ? AND active = 1 ORDER BY updated_at DESC",
                (tenant,),
            ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def pending_embeddings(self, tenant: str, model: str,
                           version: int) -> Sequence[FaqEntry]:
        with self._db.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS}, embedding FROM faq_entries"
                " WHERE tenant_id = ? AND active = 1 AND ("
                "   embedding IS NULL OR embed_model IS NOT ? OR embed_version IS NOT ?)",
                (tenant, model, version),
            ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def set_embedding(self, entry_id: str, tenant: str, embedding: np.ndarray,
                      model: str, version: int) -> None:
        payload = np.asarray(embedding, dtype="<f4").tobytes()
        with self._db.connect() as connection:
            connection.execute(
                "UPDATE faq_entries SET embedding = ?, embed_model = ?,"
                " embed_version = ? WHERE id = ? AND tenant_id = ?",
                (payload, model, int(version), entry_id, tenant),
            )

    def embeddings(self, tenant: str) -> Sequence[tuple[FaqEntry, np.ndarray]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS}, embedding FROM faq_entries"
                " WHERE tenant_id = ? AND active = 1 AND embedding IS NOT NULL"
                " ORDER BY updated_at DESC",
                (tenant,),
            ).fetchall()
        result: list[tuple[FaqEntry, np.ndarray]] = []
        for row in rows:
            vector = np.frombuffer(row["embedding"], dtype="<f4")
            if vector.size:
                result.append((_row_to_entry(row), vector.astype(np.float32)))
        return result

    def index_signature(self, tenant: str) -> tuple[int, float, int]:
        with self._db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total, COALESCE(MAX(updated_at), 0) AS updated,"
                " COALESCE(MAX(embed_version), 0) AS version"
                " FROM faq_entries WHERE tenant_id = ? AND active = 1",
                (tenant,),
            ).fetchone()
        return int(row["total"]), float(row["updated"]), int(row["version"])

    def stats(self, tenant: str) -> dict[str, object]:
        with self._db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS entries,"
                " SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active,"
                " SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded,"
                " COUNT(DISTINCT NULLIF(category, '')) AS categories"
                " FROM faq_entries WHERE tenant_id = ?",
                (tenant,),
            ).fetchone()
        return {
            "entries": int(row["entries"] or 0),
            "active": int(row["active"] or 0),
            "embedded": int(row["embedded"] or 0),
            "categories": int(row["categories"] or 0),
        }


class SqliteFaqMatcher:
    """Cosine search over an in-RAM matrix, refreshed only on catalogue change."""

    def __init__(self, repository: SqliteFaqRepository, embedder: Embedder,
                 threshold: float = DEFAULT_THRESHOLD,
                 near_threshold: float = DEFAULT_NEAR,
                 batch_size: int = 32) -> None:
        self._repo = repository
        self._embedder = embedder
        self.threshold = float(threshold)
        self.near_threshold = float(near_threshold)
        self._batch = max(1, int(batch_size))
        self._cache: dict[str, tuple[tuple[int, float, int], list[FaqEntry], np.ndarray]] = {}
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
        signature = self._repo.index_signature(tenant)
        cached = self._cache.get(tenant)
        if cached and cached[0] == signature:
            return cached[1], cached[2]

        with self._lock:
            signature = self._repo.index_signature(tenant)
            cached = self._cache.get(tenant)
            if cached and cached[0] == signature:
                return cached[1], cached[2]

            pending = self._repo.pending_embeddings(
                tenant, self.model_id, self.version)
            for start in range(0, len(pending), self._batch):
                chunk = pending[start:start + self._batch]
                vectors = self._embedder.embed_documents(
                    [item.question for item in chunk])
                for item, vector in zip(chunk, vectors):
                    self._repo.set_embedding(item.id, tenant, vector,
                                             self.model_id, self.version)

            rows = self._repo.embeddings(tenant)
            entries = [entry for entry, _ in rows]
            if rows:
                matrix = np.vstack([vector for _, vector in rows]).astype(np.float32)
            else:
                matrix = np.zeros((0, self.dim), dtype=np.float32)
            self._cache[tenant] = (self._repo.index_signature(tenant), entries, matrix)
            return entries, matrix

    def invalidate(self, tenant: str) -> None:
        with self._lock:
            self._cache.pop(tenant, None)

    # ------------------------------------------------------------------ match
    def match(self, question: str, tenant: str, k: int = 3) -> FaqResult:
        entries, matrix = self.ensure_index(tenant)
        if not entries or matrix.size == 0:
            return FaqResult(matched=None, candidates=(),
                             threshold=self.threshold,
                             near_threshold=self.near_threshold)

        query = np.asarray(self._embedder.embed_query(question), dtype=np.float32)
        if query.size != matrix.shape[1]:
            return FaqResult(matched=None, candidates=(),
                             threshold=self.threshold,
                             near_threshold=self.near_threshold)

        scores = matrix @ query
        order = np.argsort(-scores)[: max(1, int(k)) + 1]
        matches = [FaqMatch(entry=entries[index], score=float(scores[index]))
                   for index in order]
        best = matches[0]
        if best.score >= self.near_threshold:
            return FaqResult(matched=best, candidates=tuple(matches[1:k + 1]),
                             threshold=self.threshold,
                             near_threshold=self.near_threshold)
        return FaqResult(matched=None, candidates=tuple(matches[:k]),
                         threshold=self.threshold,
                         near_threshold=self.near_threshold)


__all__ = ["SqliteFaqMatcher", "SqliteFaqRepository", "normalize_question"]
