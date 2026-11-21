"""SQLite catalogue repository and the in-RAM search index.

Repository: CRUD plus embedding storage, always tenant-scoped.
Matcher: keeps one L2-normalised ``(N, dim)`` matrix per tenant in RAM, so a
lookup is a single dot product, then reranks the cosine neighbourhood with a
BM25 index over the same entries (cheap, pure Python, no extra dependency).
Both are rebuilt only when the catalogue signature changes (count / updated_at
/ embed_version), and entries missing an embedding are embedded lazily the
first time they are needed.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Sequence

import numpy as np

from ...domain.faq.models import (DEFAULT_NEAR, DEFAULT_THRESHOLD, FaqEntry,
                                   FaqMatch, FaqResult)
from ...domain.faq.lexical import Bm25Index
from ...domain.faq.normalize import normalize_question
from ...domain.faq.query import focus_question
from ...ports.embedding import Embedder
from ..storage.sqlite import Database

# Cosine picks the neighbourhood, BM25 only reorders it: the embedding decides
# whether we answer, the lexical score decides which near-identical wording wins.
LEXICAL_WEIGHT = 0.2
RERANK_POOL = 10

_COLUMNS = ("id, tenant_id, question, answer, category, active, embed_model,"
            " embed_version, created_at, updated_at, search_text,"
            " source_file, source_ref, document_id")


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
        search_text=row["search_text"] or "",
        source_file=row["source_file"] or "",
        source_ref=row["source_ref"] or "",
        document_id=row["document_id"] or "",
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
             document_id: str | None = None,
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
        if document_id is not None:
            sql.append("AND document_id = ?")
            params.append(document_id)
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
        norm = normalize_question(entry.question)
        # One derivation point: the search text follows the question unless the
        # caller supplies an explicit one (e.g. a curated short form).
        search_text = entry.search_text or focus_question(entry.question)
        with self._db.connect() as connection:
            existing = connection.execute(
                "SELECT created_at, source_file, source_ref, document_id"
                " FROM faq_entries WHERE id = ? AND tenant_id = ?",
                (entry_id, entry.tenant_id),
            ).fetchone()
            created = float(existing["created_at"]) if existing else now
            # Manual edits do not carry provenance; keep what the import stored.
            source_file = entry.source_file or (
                existing["source_file"] if existing else "")
            source_ref = entry.source_ref or (
                existing["source_ref"] if existing else "")
            document_id = entry.document_id or (
                existing["document_id"] if existing else "")
            connection.execute(
                """
                INSERT INTO faq_entries (id, tenant_id, question, answer, category,
                                         active, embedding, embed_model,
                                         embed_version, updated_at, created_at,
                                         question_norm, search_text, source_file,
                                         source_ref, document_id)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 0, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    question = excluded.question,
                    question_norm = excluded.question_norm,
                    answer = excluded.answer,
                    category = excluded.category,
                    active = excluded.active,
                    embedding = NULL,
                    embed_model = NULL,
                    embed_version = 0,
                    updated_at = excluded.updated_at,
                    search_text = excluded.search_text,
                    source_file = excluded.source_file,
                    source_ref = excluded.source_ref,
                    document_id = excluded.document_id
                """,
                (entry_id, entry.tenant_id, entry.question, entry.answer,
                 entry.category, 1 if entry.active else 0, now, created, norm,
                 search_text, source_file, source_ref, document_id),
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
            search_text=search_text,
            source_file=source_file,
            source_ref=source_ref,
            document_id=document_id,
        )

    def find_by_norm(self, tenant: str, norm: str) -> FaqEntry | None:
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_entries"
                " WHERE tenant_id = ? AND question_norm = ? LIMIT 1",
                (tenant, norm),
            ).fetchone()
        return _row_to_entry(row) if row else None

    def find_by_norm_in_document(self, tenant: str, document_id: str,
                                 norm: str) -> FaqEntry | None:
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_entries"
                " WHERE tenant_id = ? AND document_id = ? AND question_norm = ?"
                " LIMIT 1",
                (tenant, document_id, norm),
            ).fetchone()
        return _row_to_entry(row) if row else None

    def find_by_source(self, tenant: str, document_id: str,
                       source_ref: str) -> FaqEntry | None:
        if not document_id or not source_ref:
            return None
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_entries"
                " WHERE tenant_id = ? AND document_id = ? AND source_ref = ?"
                " LIMIT 1",
                (tenant, document_id, source_ref),
            ).fetchone()
        return _row_to_entry(row) if row else None

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

    # ------------------------------------------------------------- documents
    def count_in_document(self, tenant: str, document_id: str) -> int:
        with self._db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM faq_entries"
                " WHERE tenant_id = ? AND document_id = ?",
                (tenant, document_id),
            ).fetchone()
        return int(row["total"] or 0)

    def deactivate_missing(self, tenant: str, document_id: str,
                           keep_refs: set[str]) -> int:
        """Turn off entries of the document whose codes left the new file.

        Re-enabling them later is the operator's call; they are not deleted.
        """
        if not keep_refs:
            return 0
        placeholders = ",".join("?" for _ in keep_refs)
        with self._db.connect() as connection:
            cursor = connection.execute(
                f"UPDATE faq_entries SET active = 0, embedding = NULL,"
                f" embed_model = NULL, embed_version = 0"
                f" WHERE tenant_id = ? AND document_id = ? AND source_ref != ''"
                f" AND source_ref NOT IN ({placeholders})",
                (tenant, document_id, *sorted(keep_refs)),
            )
            return int(cursor.rowcount or 0)

    def delete_by_document(self, tenant: str,
                           document_id: str) -> list[str]:
        """Remove every entry of a document; returns the deleted ids."""
        with self._db.connect() as connection:
            rows = connection.execute(
                "SELECT id FROM faq_entries WHERE tenant_id = ? AND document_id = ?",
                (tenant, document_id),
            ).fetchall()
            connection.execute(
                "DELETE FROM faq_entries WHERE tenant_id = ? AND document_id = ?",
                (tenant, document_id),
            )
            return [str(row["id"]) for row in rows]


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


__all__ = ["LEXICAL_WEIGHT", "RERANK_POOL", "SqliteFaqMatcher",
           "SqliteFaqRepository", "normalize_question"]
