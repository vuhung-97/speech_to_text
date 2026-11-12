"""Dictation session controls: pause/resume and clear."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from .deps import PipelineDep

router = APIRouter(tags=["session"])


class PauseRequest(BaseModel):
    paused: bool = True


@router.post("/pause")
def set_paused(pipeline: PipelineDep, request: PauseRequest) -> dict[str, Any]:
    return {"ok": True, "paused": pipeline.set_paused(request.paused)}


@router.post("/clear")
def clear(pipeline: PipelineDep) -> dict[str, Any]:
    pipeline.clear()
    return {"ok": True}
