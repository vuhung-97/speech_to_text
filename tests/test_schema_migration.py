"""Forward migrations must upgrade an older database without losing rows."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.storage import schema
from backend.adapters.storage.sqlite import Database


def test_v3_database_migrates_with_existing_entries(tmp_path: Path) -> None:
    """The v4/v5 backfills read columns by name, even on the bootstrap connection."""
    path = tmp_path / "old.db"
    connection = sqlite3.connect(path)
    try:
        connection.executescript(schema._SCHEMA_V1)
        connection.executescript(schema._SCHEMA_V2)
        connection.executescript(schema._SCHEMA_V3)
        connection.execute("PRAGMA user_version = 3")
        connection.execute(
            "INSERT INTO faq_entries (id, tenant_id, question, answer, category,"
            " active, embedding, embed_model, embed_version, created_at, updated_at)"
            " VALUES ('e1', 'local', '  Thủ đô   Việt Nam? ', 'Hà Nội.', '', 1,"
            " NULL, NULL, 0, 1.0, 1.0)")
        connection.commit()
    finally:
        connection.close()

    database = Database(path)
    database.initialize()

    assert database.schema_version == 6
    with database.connect() as connection:
        row = connection.execute(
            "SELECT question_norm, search_text, source_file, document_id"
            " FROM faq_entries WHERE id = 'e1'").fetchone()

    assert row["question_norm"] == "thủ đô việt nam"
    assert row["search_text"] == "thủ đô việt nam"
    assert row["source_file"] == ""
    assert row["document_id"] == ""
