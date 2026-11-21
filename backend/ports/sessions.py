"""Conversation persistence contract, always tenant-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from ..domain.qa.models import Answer, Question


class SessionRepository(Protocol):
    """Sessions, turns and answers for the Q&A screen."""

    def create_session(self, tenant: str, title: str = "") -> str: ...

    def list_sessions(self, tenant: str, *, limit: int = 50,
                      offset: int = 0) -> Sequence[dict[str, object]]: ...

    def get_session(self, session_id: str,
                    tenant: str) -> dict[str, Any] | None: ...

    def delete_session(self, session_id: str, tenant: str) -> bool: ...

    def add_turn(self, session_id: str, tenant: str, question: Question) -> str: ...

    def save_answer(self, turn_id: str, tenant: str, answer: Answer) -> Answer: ...

    def get_answer(self, answer_id: str,
                   tenant: str) -> dict[str, Any] | None: ...


__all__ = ["SessionRepository"]
