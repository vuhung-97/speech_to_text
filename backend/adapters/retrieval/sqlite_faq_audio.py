"""SQLite adapter for pre-rendered FAQ answer audio.

Tenant scoping is enforced by joining ``faq_entries``: every query starts from
an entry owned by the caller's tenant, so an audio row can never be read or
deleted through another tenant's catalogue.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from ..storage.sqlite import Database


class SqliteFaqAudioRepository:
    def __init__(self, database: Database) -> None:
        self._db = database

    # ------------------------------------------------------------------ audio
    def get_audio(self, entry_id: str, tenant: str,
                  voice: str) -> dict[str, object] | None:
        with self._db.connect() as connection:
            row = connection.execute(
                """
                SELECT a.entry_id, a.voice, a.sample_rate, a.path, a.seconds, a.bytes
                FROM faq_audio a
                JOIN faq_entries e ON e.id = a.entry_id
                WHERE a.entry_id = ? AND a.voice = ? AND e.tenant_id = ?
                """,
                (entry_id, voice, tenant),
            ).fetchone()
        return dict(row) if row else None

    def put_audio(self, entry_id: str, tenant: str, *, voice: str,
                  sample_rate: int, path: str, seconds: float,
                  bytes_: int) -> None:
        with self._db.connect() as connection:
            owned = connection.execute(
                "SELECT 1 FROM faq_entries WHERE id = ? AND tenant_id = ?",
                (entry_id, tenant),
            ).fetchone()
            if owned is None:
                raise ValueError("không tìm thấy câu hỏi")
            connection.execute(
                """
                INSERT INTO faq_audio (entry_id, voice, sample_rate, path, seconds,
                                       bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_id, voice) DO UPDATE SET
                    sample_rate = excluded.sample_rate,
                    path = excluded.path,
                    seconds = excluded.seconds,
                    bytes = excluded.bytes,
                    created_at = excluded.created_at
                """,
                (entry_id, voice, int(sample_rate), path, float(seconds),
                 int(bytes_), time.time()),
            )

    def delete_audio(self, entry_id: str, tenant: str,
                     voice: str | None = None) -> None:
        sql = ("SELECT a.path FROM faq_audio a JOIN faq_entries e"
               " ON e.id = a.entry_id WHERE a.entry_id = ? AND e.tenant_id = ?")
        params: list[object] = [entry_id, tenant]
        if voice is not None:
            sql += " AND a.voice = ?"
            params.append(voice)
        with self._db.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
            delete_sql = ("DELETE FROM faq_audio WHERE entry_id IN"
                          " (SELECT id FROM faq_entries WHERE id = ? AND tenant_id = ?)")
            delete_params: list[object] = [entry_id, tenant]
            if voice is not None:
                delete_sql += " AND voice = ?"
                delete_params.append(voice)
            connection.execute(delete_sql, delete_params)
        for row in rows:
            try:
                Path(row["path"]).unlink(missing_ok=True)
            except OSError:
                pass

    def audio_usage(self, tenant: str) -> int:
        with self._db.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(a.bytes), 0) AS total FROM faq_audio a"
                " JOIN faq_entries e ON e.id = a.entry_id WHERE e.tenant_id = ?",
                (tenant,),
            ).fetchone()
        return int(row["total"] or 0)

    def oldest_audio(self, tenant: str, limit: int = 20) -> Sequence[dict[str, object]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                "SELECT a.entry_id, a.voice, a.path, a.bytes FROM faq_audio a"
                " JOIN faq_entries e ON e.id = a.entry_id WHERE e.tenant_id = ?"
                " ORDER BY a.created_at ASC LIMIT ?",
                (tenant, max(1, int(limit))),
            ).fetchall()
        return [dict(row) for row in rows]


__all__ = ["SqliteFaqAudioRepository"]
