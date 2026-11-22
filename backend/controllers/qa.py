"""Q&A endpoints: ask a question, detect one, read the worklist."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter
from pydantic import BaseModel

from ..domain.faq.models import FaqMatch, score_percent
from ..domain.qa.models import Answer, SessionNotFound
from ..services.qa_service import QaOutcome
from ..utils.errors import ApiError, NotFoundError
from .deps import (FaqAudioDep, QaDep, QueryLogDep, SessionsRepoDep, TenantDep)
from .payload import ok

router = APIRouter(tags=["qa"])


class AskRequest(BaseModel):
    question: str = ""
    session_id: str | None = None
    source: str = "voice"
    document_id: str | None = None


class SpeechRequest(BaseModel):
    voice: str | None = None


def _match_json(match: FaqMatch | None) -> dict[str, Any] | None:
    if match is None:
        return None
    return {
        "id": match.entry.id,
        "question": match.entry.question,
        "category": match.entry.category,
        "score": round(match.score, 4),
        "percent": score_percent(match.score),
    }


def answer_json(outcome: QaOutcome) -> dict[str, Any]:
    answer: Answer = outcome.answer
    return ok(
        session_id=outcome.session_id,
        question=outcome.question,
        answer={
            "id": answer.id,
            "turn_id": answer.turn_id,
            "session_id": outcome.session_id,
            "text": answer.text,
            "status": str(answer.status),
            "answered": answer.answered,
            "entry_id": answer.entry_id,
            "score": None if answer.score is None else round(answer.score, 4),
            "matched": _match_json(answer.matched),
            "candidates": [_match_json(item) for item in answer.candidates],
        },
    )


@router.post("/qa/ask")
def ask(request: AskRequest, qa: QaDep, tenant: TenantDep) -> dict[str, Any]:
    try:
        outcome = qa.ask(
            request.question,
            tenant=tenant,
            session_id=request.session_id,
            source=request.source or "voice",
            document_id=request.document_id or None,
        )
    except SessionNotFound as exc:
        raise ApiError(str(exc), status_code=404) from exc
    return answer_json(outcome)


@router.get("/qa/unanswered")
def unanswered(log: QueryLogDep, tenant: TenantDep, limit: int = 50) -> dict[str, Any]:
    return ok(items=list(log.unanswered(tenant, limit=limit)))


@router.post("/qa/answers/{answer_id}/speech")
def answer_speech(answer_id: str, request: SpeechRequest, sessions: SessionsRepoDep,
                  audio: FaqAudioDep, tenant: TenantDep) -> dict[str, Any]:
    """Return the cached WAV when it exists, otherwise the text to stream."""
    row = sessions.get_answer(answer_id, tenant)
    if row is None:
        raise NotFoundError("không tìm thấy câu trả lời")
    voice = audio.resolve_voice(request.voice)
    entry_id = row.get("entry_id")
    if entry_id and voice:
        cached = audio.cached(str(entry_id), tenant, voice)
        if cached:
            url = (f"/api/v1/faq/entries/{entry_id}/audio"
                   f"?voice={quote(str(voice))}")
            return ok(mode="cached", url=url,
                      seconds=cached["seconds"], voice=voice)
    return ok(mode="stream", text=row["text"], voice=voice)
