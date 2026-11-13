"""Conversation persistence contract, always tenant-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..domain.qa.models import Answer, Question


class SessionRepository(Protocol):
    """Sessions, turns and answers for the Q&A screen."""

    def create_session(self, tenant: str, title: str = "") -> str: ...

    def list_sessions(self, tenant: str, *, limit: int = 50,
                      offset: int = 0) -> Sequence[dict[str, object]]: ...

    def delete_session(self, session_id: str, tenant: str) -> None: ...

    def add_turn(self, session_id: str, tenant: str, question: Question) -> str: ...

    def save_answer(self, turn_id: str, tenant: str, answer: Answer) -> Answer: ...


__all__ = ["SessionRepository"]
