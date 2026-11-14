"""Sessions/turns/answers and the query log: schema, scoping, lifecycle."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.storage.sqlite import (Database, SqliteQueryLog,
                                             SqliteSessionRepository)
from backend.domain.qa.models import (Answer, AnswerStatus, Question,
                                      SessionNotFound, TurnNotFound)


def make(tmp_path: Path):
    database = Database(tmp_path / "app.db")
    return database, SqliteSessionRepository(database), SqliteQueryLog(database)


def test_schema_is_created_lazily(tmp_path: Path) -> None:
    path = tmp_path / "lazy.db"
    database = Database(path)
    assert not path.exists()  # importing/constructing must not touch disk
    database.initialize()
    assert path.exists()
    assert database.schema_version == 3


def test_session_lifecycle(tmp_path: Path) -> None:
    _, sessions, _ = make(tmp_path)

    session_id = sessions.create_session("local", title="Quy trình đăng ký")
    listed = sessions.list_sessions("local")
    assert [row["id"] for row in listed] == [session_id]
    assert listed[0]["title"] == "Quy trình đăng ký"
    assert listed[0]["turns"] == 0

    turn_id = sessions.add_turn(
        session_id, "local", Question("Quy trình gồm mấy bước?", session_id))
    assert turn_id

    detail = sessions.get_session(session_id, "local")
    assert detail is not None
    assert detail["turns"][0]["question"] == "Quy trình gồm mấy bước?"
    assert detail["turns"][0]["answer"] is None

    answer = Answer(id="a1", turn_id=turn_id, text="Ba bước.",
                    status=AnswerStatus.MATCHED, session_id=session_id)
    sessions.save_answer(turn_id, "local", answer)

    detail = sessions.get_session(session_id, "local")
    assert detail["turns"][0]["answer"]["text"] == "Ba bước."
    assert detail["turns"][0]["answer"]["status"] == "matched"

    assert sessions.delete_session(session_id, "local") is True
    assert sessions.get_session(session_id, "local") is None
    assert sessions.delete_session(session_id, "local") is False


def test_tenants_cannot_see_each_other(tmp_path: Path) -> None:
    _, sessions, _ = make(tmp_path)
    session_id = sessions.create_session("acme")

    assert sessions.get_session(session_id, "local") is None
    assert sessions.delete_session(session_id, "local") is False
    with pytest.raises(SessionNotFound):
        sessions.add_turn(session_id, "local", Question("xin chào"))

    assert sessions.list_sessions("local") == []
    assert [row["id"] for row in sessions.list_sessions("acme")] == [session_id]


def test_turn_and_answer_scoping(tmp_path: Path) -> None:
    _, sessions, _ = make(tmp_path)
    session_id = sessions.create_session("acme")
    turn_id = sessions.add_turn(session_id, "acme", Question("hỏi"))

    with pytest.raises(TurnNotFound):
        sessions.save_answer(turn_id, "local", Answer(
            id="a1", turn_id=turn_id, text="x", status=AnswerStatus.UNANSWERED))
    with pytest.raises(SessionNotFound):
        sessions.add_turn("missing", "acme", Question("hỏi"))


def test_save_answer_is_idempotent_per_turn(tmp_path: Path) -> None:
    _, sessions, _ = make(tmp_path)
    session_id = sessions.create_session("local")
    turn_id = sessions.add_turn(session_id, "local", Question("hỏi"))

    sessions.save_answer(turn_id, "local", Answer(
        id="a1", turn_id=turn_id, text="cũ", status=AnswerStatus.UNANSWERED))
    sessions.save_answer(turn_id, "local", Answer(
        id="a2", turn_id=turn_id, text="mới", status=AnswerStatus.MATCHED,
        entry_id="e1", score=0.91))

    detail = sessions.get_session(session_id, "local")
    turns = detail["turns"]
    assert len(turns) == 1
    assert turns[0]["answer"]["text"] == "mới"
    assert turns[0]["answer"]["entry_id"] == "e1"


def test_update_answer_audio(tmp_path: Path) -> None:
    _, sessions, _ = make(tmp_path)
    session_id = sessions.create_session("local")
    turn_id = sessions.add_turn(session_id, "local", Question("hỏi"))
    sessions.save_answer(turn_id, "local", Answer(
        id="a1", turn_id=turn_id, text="x", status=AnswerStatus.MATCHED))

    sessions.update_answer_audio("a1", "local", voice="Mai Anh",
                                 audio_path="/tmp/a.wav", seconds=1.5)
    detail = sessions.get_session(session_id, "local")
    assert detail["turns"][0]["answer"]["seconds"] == 1.5


def test_query_log_unanswered(tmp_path: Path) -> None:
    _, _, log = make(tmp_path)
    log.record(tenant="local", session_id=None, question="Hỏi một?",
               matched_entry_id=None, score=None, answered=False)
    log.record(tenant="local", session_id=None, question="hỏi một",
               matched_entry_id=None, score=None, answered=False)
    log.record(tenant="local", session_id=None, question="Đã trả lời",
               matched_entry_id="e1", score=0.9, answered=True)
    log.record(tenant="acme", session_id=None, question="Của acme",
               matched_entry_id=None, score=None, answered=False)

    items = log.unanswered("local")
    assert len(items) == 1
    assert items[0]["question_norm"] == "hỏi một"
    assert items[0]["asks"] == 2
    assert [item["question_norm"] for item in log.unanswered("acme")] == ["của acme"]
