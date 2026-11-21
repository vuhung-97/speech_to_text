"""SQLite persistence for uploaded question sets (``faq_documents``).

One document owns many entries; the identity that keeps re-imports idempotent
is ``(tenant_id, name)`` for versioning and ``content_hash`` for recognising the
same content under another name. Everything stays tenant-scoped.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Sequence

from ...domain.faq.models import FaqDocument
from .sqlite import Database

_COLUMNS = "id, tenant_id, name, content_hash, entry_count, created_at, updated_at"


def _row_to_document(row) -> FaqDocument:
    return FaqDocument(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        content_hash=row["content_hash"] or "",
        entry_count=int(row["entry_count"] or 0),
        created_at=float(row["created_at"]),
        updated_at=float(row["updated_at"]),
    )


class SqliteFaqDocumentRepository:
    def __init__(self, database: Database) -> None:
        self._db = database

    # ------------------------------------------------------------------- CRUD
    def get(self, document_id: str, tenant: str) -> FaqDocument | None:
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_documents"
                " WHERE id = ? AND tenant_id = ?",
                (document_id, tenant),
            ).fetchone()
        return _row_to_document(row) if row else None

    def list(self, tenant: str) -> Sequence[FaqDocument]:
        with self._db.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_documents WHERE tenant_id = ?"
                " ORDER BY updated_at DESC",
                (tenant,),
            ).fetchall()
        return [_row_to_document(row) for row in rows]

    def find_by_name(self, tenant: str, name: str) -> FaqDocument | None:
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_documents"
                " WHERE tenant_id = ? AND name = ? LIMIT 1",
                (tenant, name),
            ).fetchone()
        return _row_to_document(row) if row else None

    def find_by_hash(self, tenant: str, content_hash: str) -> FaqDocument | None:
        with self._db.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM faq_documents"
                " WHERE tenant_id = ? AND content_hash = ? LIMIT 1",
                (tenant, content_hash),
            ).fetchone()
        return _row_to_document(row) if row else None

    def create(self, tenant: str, name: str, content_hash: str) -> FaqDocument:
        document_id = uuid.uuid4().hex[:16]
        now = time.time()
        with self._db.connect() as connection:
            connection.execute(
                "INSERT INTO faq_documents (id, tenant_id, name, content_hash,"
                " entry_count, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?)",
                (document_id, tenant, name, content_hash, now, now),
            )
        return FaqDocument(id=document_id, tenant_id=tenant, name=name,
                           content_hash=content_hash, entry_count=0,
                           created_at=now, updated_at=now)

    def update(self, document_id: str, tenant: str, *, name: str | None = None,
               content_hash: str | None = None,
               entry_count: int | None = None) -> FaqDocument | None:
        existing = self.get(document_id, tenant)
        if existing is None:
            return None
        now = time.time()
        with self._db.connect() as connection:
            connection.execute(
                """
                UPDATE faq_documents SET
                    name = ?,
                    content_hash = ?,
                    entry_count = ?,
                    updated_at = ?
                WHERE id = ? AND tenant_id = ?
                """,
                (name if name is not None else existing.name,
                 content_hash if content_hash is not None else existing.content_hash,
                 entry_count if entry_count is not None else existing.entry_count,
                 now, document_id, tenant),
            )
        return self.get(document_id, tenant)

    def delete(self, document_id: str, tenant: str) -> bool:
        with self._db.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM faq_documents WHERE id = ? AND tenant_id = ?",
                (document_id, tenant),
            )
            return cursor.rowcount > 0


__all__ = ["SqliteFaqDocumentRepository"]
