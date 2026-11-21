"""SQLite schema and forward-only migrations.

Everything that changes the on-disk shape lives here: the DDL for each schema
version and the migration runner that brings an older database up to date.
Repositories only write queries against the resulting tables.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time

from ...domain.faq.normalize import normalize_question
from ...domain.faq.query import focus_question
from .ids import new_id

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


def _add_column(connection: sqlite3.Connection, statement: str) -> None:
    """Apply one ``ALTER TABLE ADD COLUMN``; tolerate a half-finished migration."""
    try:
        connection.execute(statement)
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def ensure_schema(connection: sqlite3.Connection) -> None:
    """Bring ``connection``'s database to ``SCHEMA_VERSION`` (idempotent)."""
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
            connection.execute(
                "UPDATE faq_entries SET search_text = ? WHERE id = ?",
                (focus_question(row["question"]), row["id"]),
            )
        connection.execute("PRAGMA user_version = 5")
    if version < 6:
        connection.executescript(_SCHEMA_V6_TABLES)
        for statement in _SCHEMA_V6_COLUMNS:
            _add_column(connection, statement)
        connection.executescript(_SCHEMA_V6_INDEX)
        _backfill_documents_v6(connection)
        connection.execute("PRAGMA user_version = 6")


def _backfill_documents_v6(connection: sqlite3.Connection) -> None:
    """Group pre-existing rows per (tenant, source_file) into documents."""
    rows = connection.execute(
        "SELECT tenant_id, source_file FROM faq_entries"
        " WHERE source_file != ''"
        " GROUP BY tenant_id, source_file"
    ).fetchall()
    for row in rows:
        tenant_id, source_file = row[0], row[1]
        document_id = new_id()
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


__all__ = ["SCHEMA_VERSION", "ensure_schema"]
