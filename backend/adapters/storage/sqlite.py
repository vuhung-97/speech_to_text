"""SQLite adapter: schema, migration and tenant-scoped repositories.

One file owns the database so no service knows SQL. Every query filters by
``tenant_id``; the local build uses ``local`` but the column is already in place
so accounts can be added without a data migration.

Connections are opened per operation (cheap for a desktop app, safe across the
FastAPI thread pool) with WAL enabled and a busy timeout.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ...domain.faq.models import score_percent
from ...domain.faq.normalize import normalize_question
from ...domain.faq.query import focus_question
from ...domain.qa.models import (Answer, Question, SessionNotFound,
                                 TurnNotFound)

SCHEMA_VERSION = 6

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    title      TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_tenant_updated
    ON sessions(tenant_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS turns (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id  TEXT NOT NULL,
    question   TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'voice',
    created_at REAL NOT NULL,
    state      TEXT NOT NULL DEFAULT 'answered'
);
CREATE INDEX IF NOT EXISTS idx_turns_session
    ON turns(session_id, created_at);

CREATE TABLE IF NOT EXISTS answers (
    id         TEXT PRIMARY KEY,
    turn_id    TEXT NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    tenant_id  TEXT NOT NULL,
    text       TEXT NOT NULL,
    entry_id   TEXT,
    score      REAL,
    status     TEXT NOT NULL,
    voice      TEXT,
    audio_path TEXT,
    seconds    REAL,
    created_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_turn ON answers(turn_id);

CREATE TABLE IF NOT EXISTS faq_queries (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    session_id       TEXT,
    question         TEXT NOT NULL,
    question_norm    TEXT NOT NULL,
    matched_entry_id TEXT,
    score            REAL,
    answered         INTEGER NOT NULL,
    created_at       REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_faq_queries_tenant
    ON faq_queries(tenant_id, created_at DESC);
"""

_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS faq_entries (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL,
    question      TEXT NOT NULL,
    answer        TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT '',
    active        INTEGER NOT NULL DEFAULT 1,
    embedding     BLOB,
    embed_model   TEXT,
    embed_version INTEGER NOT NULL DEFAULT 0,
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_faq_entries_tenant
    ON faq_entries(tenant_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_faq_entries_active
    ON faq_entries(tenant_id, active);

CREATE TABLE IF NOT EXISTS faq_audio (
    entry_id    TEXT NOT NULL,
    voice       TEXT NOT NULL,
    sample_rate INTEGER NOT NULL,
    path        TEXT NOT NULL,
    seconds     REAL NOT NULL,
    bytes       INTEGER NOT NULL,
    created_at  REAL NOT NULL,
    PRIMARY KEY (entry_id, voice)
);
"""

_SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS audit_log (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    action     TEXT NOT NULL,
    target     TEXT NOT NULL DEFAULT '',
    detail     TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant
    ON audit_log(tenant_id, created_at DESC);
"""

_SCHEMA_V4 = """
ALTER TABLE faq_entries ADD COLUMN question_norm TEXT;
CREATE INDEX IF NOT EXISTS idx_faq_entries_norm
    ON faq_entries(tenant_id, question_norm);
"""

# V5: what the embedder actually sees plus provenance for re-imported files.
# Each statement is applied separately (``_add_column``) because a previous run
# may have been interrupted halfway through the migration.
_SCHEMA_V5_COLUMNS = (
    "ALTER TABLE faq_entries ADD COLUMN search_text TEXT",
    "ALTER TABLE faq_entries ADD COLUMN source_file TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE faq_entries ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
)
_SCHEMA_V5_INDEX = """
CREATE INDEX IF NOT EXISTS idx_faq_entries_source
    ON faq_entries(tenant_id, source_file, source_ref);
"""

# V6: question sets (uploaded documents) own their entries.
_SCHEMA_V6_TABLES = """
CREATE TABLE IF NOT EXISTS faq_documents (
    id           TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    name         TEXT NOT NULL,
    content_hash TEXT NOT NULL DEFAULT '',
    entry_count  INTEGER NOT NULL DEFAULT 0,
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_faq_documents_name
    ON faq_documents(tenant_id, name);
"""
_SCHEMA_V6_COLUMNS = (
    "ALTER TABLE faq_entries ADD COLUMN document_id TEXT NOT NULL DEFAULT ''",
)
_SCHEMA_V6_INDEX = """
CREATE INDEX IF NOT EXISTS idx_faq_entries_document
    ON faq_entries(tenant_id, document_id, source_ref);
"""


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _add_column(connection: sqlite3.Connection, statement: str) -> None:
    """Apply one ``ALTER TABLE ADD COLUMN``; tolerate a half-finished migration."""
    try:
        connection.execute(statement)
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


class Database:
    """Owns the schema; callers use repositories, never SQL.

    The schema is created lazily on first connection so importing the app (or
    running unrelated tests) never touches the filesystem.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._ready = False
        self._lock = threading.Lock()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self._ensure()
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5.0)
            try:
                connection.execute("PRAGMA journal_mode = WAL")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version < 1:
                    connection.executescript(_SCHEMA_V1)
                    connection.execute("PRAGMA user_version = 1")
                    version = 1
                if version < 2:
                    connection.executescript(_SCHEMA_V2)
                    connection.execute("PRAGMA user_version = 2")
                    version = 2
                if version < 3:
                    connection.executescript(_SCHEMA_V3)
                    connection.execute("PRAGMA user_version = 3")
                    version = 3
                if version < 4:
                    try:
                        connection.executescript(_SCHEMA_V4)
                    except sqlite3.OperationalError:
                        pass  # column already added by an interrupted run
                    rows = connection.execute(
                        "SELECT id, question FROM faq_entries").fetchall()
                    for row in rows:
                        connection.execute(
                            "UPDATE faq_entries SET question_norm = ? WHERE id = ?",
                            (normalize_question(row["question"]), row["id"]),
                        )
                    connection.execute("PRAGMA user_version = 4")
                if version < 5:
                    for statement in _SCHEMA_V5_COLUMNS:
                        _add_column(connection, statement)
                    connection.executescript(_SCHEMA_V5_INDEX)
                    rows = connection.execute(
                        "SELECT id, question, search_text FROM faq_entries"
                    ).fetchall()
                    for row in rows:
                        search_text = focus_question(row["question"])
                        connection.execute(
                            "UPDATE faq_entries SET search_text = ? WHERE id = ?",
                            (search_text, row["id"]),
                        )
                    connection.execute("PRAGMA user_version = 5")
                if version < 6:
                    connection.executescript(_SCHEMA_V6_TABLES)
                    for statement in _SCHEMA_V6_COLUMNS:
                        _add_column(connection, statement)
                    connection.executescript(_SCHEMA_V6_INDEX)
                    self._backfill_documents_v6(connection)
                    connection.execute("PRAGMA user_version = 6")
                connection.commit()
            finally:
                connection.close()
            self._ready = True

    def initialize(self) -> None:
        self._ensure()

    @property
    def schema_version(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    def _backfill_documents_v6(self, connection: sqlite3.Connection) -> None:
        """Group pre-existing rows per (tenant, source_file) into documents."""
        rows = connection.execute(
            "SELECT tenant_id, source_file FROM faq_entries"
            " WHERE source_file != ''"
            " GROUP BY tenant_id, source_file"
        ).fetchall()
        for row in rows:
            tenant_id, source_file = row[0], row[1]
            document_id = _new_id()
            now = time.time()
            entries = connection.execute(
                "SELECT id, question, answer FROM faq_entries"
                " WHERE tenant_id = ? AND source_file = ?"
                " ORDER BY created_at ASC",
                (tenant_id, source_file),
            ).fetchall()
            payload = "\n".join(
                f"{item[1]}\u0000{item[2]}" for item in entries)
            fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            connection.execute(
                "INSERT INTO faq_documents (id, tenant_id, name, content_hash,"
                " entry_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (document_id, tenant_id, source_file, fingerprint,
                 len(entries), now, now),
            )
            for item in entries:
                connection.execute(
                    "UPDATE faq_entries SET document_id = ? WHERE id = ?",
                    (document_id, item[0]),
                )


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
        session_id = _new_id()
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
        turn_id = _new_id()
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
                (_new_id(), tenant, action, target or "", detail or "", time.time()),
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
                (_new_id(), tenant, session_id, question, normalize_question(question),
                 matched_entry_id, score, 1 if answered else 0, time.time()),
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


__all__ = [
    "Database",
    "SCHEMA_VERSION",
    "SqliteAuditLog",
    "SqliteQueryLog",
    "SqliteSessionRepository",
]
