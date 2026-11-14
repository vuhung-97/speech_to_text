"""Dictation session controls: pause/resume and clear."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from .deps import PipelineDep

router = APIRouter(tags=["session"])


class PauseRequest(BaseModel):
    paused: bool = True


class CaptureRequest(BaseModel):
    listening: bool = False


@router.post("/pause")
def set_paused(pipeline: PipelineDep, request: PauseRequest) -> dict[str, Any]:
    return {"ok": True, "paused": pipeline.set_paused(request.paused)}


@router.post("/capture")
def set_capture(pipeline: PipelineDep, request: CaptureRequest) -> dict[str, Any]:
    """Open/close the microphone; ``listening=false`` releases the device."""
    listening = pipeline.set_listening(request.listening)
    return {"ok": True, "listening": listening}


@router.post("/clear")
def clear(pipeline: PipelineDep) -> dict[str, Any]:
    pipeline.clear()
    return {"ok": True}
