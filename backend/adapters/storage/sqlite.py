"""SQLite adapter: lazy schema bootstrap, one connection per operation.

The schema and its forward-only migrations live in :mod:`.schema`; the
repositories live in :mod:`.sessions` and :mod:`.logs`. This module stays the
public entry point (``Database`` plus re-exports) so existing imports keep
working while the internals are split by responsibility.

Connections are opened per operation (cheap for a desktop app, safe across the
FastAPI thread pool) with WAL enabled and a busy timeout.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .logs import SqliteAuditLog, SqliteQueryLog
from .schema import SCHEMA_VERSION, ensure_schema
from .sessions import SqliteSessionRepository


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
            # Migrations read columns by name (``row["question"]``), so the
            # bootstrap connection needs the same row factory as ``connect``.
            connection.row_factory = sqlite3.Row
            try:
                connection.execute("PRAGMA journal_mode = WAL")
                ensure_schema(connection)
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


__all__ = [
    "Database",
    "SCHEMA_VERSION",
    "SqliteAuditLog",
    "SqliteQueryLog",
    "SqliteSessionRepository",
]
