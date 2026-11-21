"""Append-only logs: sensitive actions and FAQ lookup history."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from ...domain.faq.normalize import normalize_question
from .ids import new_id

if TYPE_CHECKING:  # avoids a runtime cycle with ``Database``
    from .sqlite import Database


class SqliteAuditLog:
    """Sensitive actions (delete, import, reindex) with tenant context."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def record(self, *, tenant: str, action: str, target: str = "",
               detail: str = "") -> None:
        with self._db.connect() as connection:
            connection.execute(
                "INSERT INTO audit_log (id, tenant_id, action, target, detail,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), tenant, action, target or "", detail or "", time.time()),
            )

    def list(self, tenant: str, limit: int = 50) -> Sequence[dict[str, Any]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                "SELECT id, action, target, detail, created_at FROM audit_log"
                " WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant, max(1, min(int(limit), 200))),
            ).fetchall()
        return [dict(row) for row in rows]


class SqliteQueryLog:
    """Lookup history: tuning input today, unanswered worklist for the operator."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def record(self, *, tenant: str, session_id: str | None, question: str,
               matched_entry_id: str | None, score: float | None,
               answered: bool) -> None:
        with self._db.connect() as connection:
            connection.execute(
                "INSERT INTO faq_queries (id, tenant_id, session_id, question,"
                " question_norm, matched_entry_id, score, answered, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id(), tenant, session_id, question,
                 normalize_question(question), matched_entry_id, score,
                 1 if answered else 0, time.time()),
            )

    def unanswered(self, tenant: str, limit: int = 50) -> Sequence[dict[str, Any]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                """
                SELECT question_norm, COUNT(*) AS asks, MAX(created_at) AS last_asked,
                       MAX(question) AS sample
                FROM faq_queries
                WHERE tenant_id = ? AND answered = 0
                GROUP BY question_norm
                ORDER BY asks DESC, last_asked DESC
                LIMIT ?
                """,
                (tenant, max(1, min(int(limit), 200))),
            ).fetchall()
        return [dict(row) for row in rows]


__all__ = ["SqliteAuditLog", "SqliteQueryLog"]
