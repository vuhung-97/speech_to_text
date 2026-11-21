"""Sessions, turns and answers with strict tenant scoping."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from ...domain.faq.models import score_percent
from ...domain.qa.models import (Answer, Question, SessionNotFound,
                                 TurnNotFound)
from .ids import new_id

if TYPE_CHECKING:  # avoids a runtime cycle with ``Database``
    from .sqlite import Database


def _answer_payload(row: sqlite3.Row) -> dict[str, Any] | None:
    """One saved answer in the same shape as the live ``ask`` response.

    ``matched`` is rebuilt from the entry the answer points at, so reopening a
    session shows the same evidence chip as the original response.
    """
    if row["answer_id"] is None:
        return None
    entry_id = row["entry_id"]
    score = row["score"]
    matched = None
    if entry_id and row["matched_question"] is not None:
        matched = {
            "id": entry_id,
            "question": row["matched_question"],
            "category": row["matched_category"] or "",
            "score": score,
            "percent": score_percent(score or 0.0),
        }
    return {
        "id": row["answer_id"],
        "text": row["text"],
        "status": row["status"],
        "answered": row["status"] in ("matched", "near_miss"),
        "entry_id": entry_id,
        "score": score,
        "seconds": row["seconds"],
        "created_at": row["answered_at"],
        "matched": matched,
        "candidates": [],
    }


class SqliteSessionRepository:
    """Sessions, turns and answers with strict tenant scoping."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # ------------------------------------------------------------- sessions
    def create_session(self, tenant: str, title: str = "") -> str:
        session_id = new_id()
        now = time.time()
        with self._db.connect() as connection:
            connection.execute(
                "INSERT INTO sessions (id, tenant_id, title, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (session_id, tenant, (title or "").strip()[:120], now, now),
            )
        return session_id

    def list_sessions(self, tenant: str, *, limit: int = 50,
                      offset: int = 0) -> Sequence[dict[str, Any]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.title, s.created_at, s.updated_at,
                       (SELECT COUNT(*) FROM turns t WHERE t.session_id = s.id) AS turns,
                       (SELECT t.question FROM turns t WHERE t.session_id = s.id
                        ORDER BY t.created_at ASC LIMIT 1) AS first_question
                FROM sessions s
                WHERE s.tenant_id = ?
                ORDER BY s.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (tenant, max(1, min(int(limit), 200)), max(0, int(offset))),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: str, tenant: str) -> dict[str, Any] | None:
        with self._db.connect() as connection:
            session = connection.execute(
                "SELECT id, title, created_at, updated_at FROM sessions"
                " WHERE id = ? AND tenant_id = ?",
                (session_id, tenant),
            ).fetchone()
            if session is None:
                return None
            rows = connection.execute(
                """
                SELECT t.id AS turn_id, t.question, t.source, t.created_at AS asked_at,
                       a.id AS answer_id, a.text, a.status, a.entry_id, a.score,
                       a.seconds, a.created_at AS answered_at,
                       e.question AS matched_question,
                       e.category AS matched_category
                FROM turns t
                LEFT JOIN answers a ON a.turn_id = t.id
                LEFT JOIN faq_entries e ON e.id = a.entry_id
                WHERE t.session_id = ? AND t.tenant_id = ?
                ORDER BY t.created_at ASC
                """,
                (session_id, tenant),
            ).fetchall()

        payload = dict(session)
        payload["turns"] = [
            {
                "id": row["turn_id"],
                "question": row["question"],
                "source": row["source"],
                "created_at": row["asked_at"],
                "answer": _answer_payload(row),
            }
            for row in rows
        ]
        return payload

    def delete_session(self, session_id: str, tenant: str) -> bool:
        with self._db.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM sessions WHERE id = ? AND tenant_id = ?",
                (session_id, tenant),
            )
            return cursor.rowcount > 0

    # ---------------------------------------------------------------- turns
    def add_turn(self, session_id: str, tenant: str, question: Question) -> str:
        turn_id = new_id()
        now = time.time()
        with self._db.connect() as connection:
            owned = connection.execute(
                "SELECT 1 FROM sessions WHERE id = ? AND tenant_id = ?",
                (session_id, tenant),
            ).fetchone()
            if owned is None:
                raise SessionNotFound("không tìm thấy phiên hội thoại")
            connection.execute(
                "INSERT INTO turns (id, session_id, tenant_id, question, source,"
                " created_at, state) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
                (turn_id, session_id, tenant, question.text,
                 question.source, now),
            )
            connection.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        return turn_id

    def save_answer(self, turn_id: str, tenant: str, answer: Answer) -> Answer:
        now = time.time()
        with self._db.connect() as connection:
            owned = connection.execute(
                "SELECT 1 FROM turns WHERE id = ? AND tenant_id = ?",
                (turn_id, tenant),
            ).fetchone()
            if owned is None:
                raise TurnNotFound("không tìm thấy lượt hỏi")
            connection.execute(
                """
                INSERT INTO answers (id, turn_id, tenant_id, text, entry_id, score,
                                     status, seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(turn_id) DO UPDATE SET
                    text = excluded.text,
                    entry_id = excluded.entry_id,
                    score = excluded.score,
                    status = excluded.status,
                    seconds = excluded.seconds
                """,
                (answer.id, turn_id, tenant, answer.text, answer.entry_id,
                 answer.score, str(answer.status), answer.seconds, now),
            )
            connection.execute(
                "UPDATE turns SET state = ? WHERE id = ?",
                ("answered" if answer.answered else "unanswered", turn_id),
            )
        return answer

    def get_answer(self, answer_id: str, tenant: str) -> dict[str, Any] | None:
        with self._db.connect() as connection:
            row = connection.execute(
                """
                SELECT a.id, a.turn_id, a.text, a.entry_id, a.score,
                       a.seconds, a.status, a.created_at,
                       t.session_id, t.question
                FROM answers a
                JOIN turns t ON t.id = a.turn_id
                WHERE a.id = ? AND a.tenant_id = ?
                """,
                (answer_id, tenant),
            ).fetchone()
        return dict(row) if row else None


__all__ = ["SqliteSessionRepository"]
