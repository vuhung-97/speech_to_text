"""SQLite catalogue repository: CRUD plus embedding storage, tenant-scoped."""

from __future__ import annotations

import time
from collections.abc import Sequence

import numpy as np

from ...domain.faq.models import FaqEntry
from ...domain.faq.normalize import normalize_question
from ...domain.faq.query import focus_question
from ..storage.ids import new_id
from ..storage.sqlite import Database

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
        entry_id = entry.id or new_id()
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
                f"SELECT {_COLUMNS} FROM faq_entries"
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


__all__ = ["SqliteFaqRepository"]
