"""Sample audio files: list, upload, replay."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from ..config.constants import BYTES_PER_MB
from ..services.replay_service import MAX_UPLOAD_BYTES
from ..utils.errors import ApiError
from .deps import ReplayDep
from .payload import ok

router = APIRouter(tags=["samples"])


class ReplayRequest(BaseModel):
    name: str
    segment: bool = False


@router.get("/samples")
def list_samples(replay: ReplayDep) -> dict[str, Any]:
    return {"samples": replay.list_samples()}


@router.post("/samples")
async def upload_sample(replay: ReplayDep, file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(f"file quá lớn (tối đa {MAX_UPLOAD_BYTES // BYTES_PER_MB} MB)")
    try:
        entry = replay.save_upload(file.filename or "", data)
    except ValueError as exc:
        raise ApiError(str(exc)) from exc
    return ok(**entry)


@router.post("/replay")
def replay_file(replay: ReplayDep, request: ReplayRequest) -> dict[str, Any]:
    try:
        result = replay.run(request.name, segment=request.segment)
    except (ValueError, FileNotFoundError) as exc:
        raise ApiError(str(exc), status_code=400) from exc
    return ok(**result.to_dict())
