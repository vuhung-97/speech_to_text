"""Text-to-speech endpoints: voice catalog, short WAV and long-form streaming.

Short text keeps the original in-memory contract. Long text is streamed as
PCM16 while it is written to a temp WAV, so RAM stays flat regardless of length;
the finished file is then available with HTTP Range support for seeking.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from ..domain.text.limits import (MAX_TTS_STREAM_CHARS, MAX_TTS_WORDS,
                                  TextTooLong)
from ..services.tts_service import (MAX_TTS_CHARS, SAMPLE_RATE, TtsBusy,
                                    TtsStorageError, TtsUnavailable)
from ..utils.errors import ApiError
from .deps import TtsDep
from .payload import ok

router = APIRouter(tags=["tts"])


class TtsRequest(BaseModel):
    text: str = ""
    voice: str | None = None


@router.get("/tts/voices")
def list_voices(tts: TtsDep) -> dict[str, Any]:
    voices, default = tts.voices()
    available, reason = tts.available()
    return ok(
        voices=voices,
        default=default,
        available=available,
        reason=reason,
        max_chars=MAX_TTS_CHARS,
        max_words=MAX_TTS_WORDS,
        status=tts.status(),
    )


@router.post("/tts/preload")
def preload_tts(request: TtsRequest, tts: TtsDep) -> dict[str, Any]:
    """Warm the engine/voice in RAM; poll ``/tts/status`` for progress."""
    ready, reason = tts.available()
    if not ready:
        raise ApiError(reason, status_code=503)
    try:
        voice = tts.resolve_voice(request.voice)
    except ValueError as exc:
        raise ApiError(str(exc), status_code=400) from exc
    tts.preload_async(synthesize=True, voice=voice)
    return ok(preloading=True, voice=voice)


@router.get("/tts/status")
def tts_status(tts: TtsDep) -> dict[str, Any]:
    return ok(**tts.status())


@router.get("/tts/limits")
def limits(tts: TtsDep) -> dict[str, Any]:
    """Everything the UI needs to validate before submitting, in one call."""
    return ok(
        sample_rate=SAMPLE_RATE,
        max_quick_chars=MAX_TTS_CHARS,
        max_words=MAX_TTS_WORDS,
        max_stream_chars=MAX_TTS_STREAM_CHARS,
        busy=tts.busy,
    )


@router.post("/tts")
def synthesize(request: TtsRequest, tts: TtsDep) -> Response:
    """Short path (≤1000 characters): one in-memory WAV, unchanged contract."""
    try:
        audio, seconds = tts.synthesize(request.text, request.voice)
    except TtsUnavailable as exc:
        raise ApiError(str(exc), status_code=503) from exc
    except ValueError as exc:
        raise ApiError(str(exc), status_code=400) from exc
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "X-Audio-Seconds": f"{seconds:.2f}"},
    )


@router.post("/tts/stream")
def stream_speech(request: TtsRequest, tts: TtsDep) -> StreamingResponse:
    """Long path (≤2000 words): PCM16 blocks, written to disk as they are made."""
    try:
        job = tts.prepare_stream(request.text, request.voice)
    except TtsUnavailable as exc:
        raise ApiError(str(exc), status_code=503) from exc
    except TtsBusy as exc:
        raise ApiError(str(exc), status_code=409) from exc
    except TextTooLong as exc:
        raise ApiError(str(exc), status_code=413) from exc
    except TtsStorageError as exc:
        raise ApiError(str(exc), status_code=507) from exc

    return StreamingResponse(
        tts.stream_job(job),
        media_type="audio/L16",
        headers={
            "Cache-Control": "no-store",
            "X-Tts-Session": job.id,
            "X-Sample-Rate": str(SAMPLE_RATE),
            "X-Estimated-Seconds": f"{job.estimated_seconds:.1f}",
        },
    )


@router.get("/tts/sessions/{job_id}.wav")
def session_wav(job_id: str, tts: TtsDep) -> FileResponse:
    """Finished WAV with Range support (seek, resume, download)."""
    path = tts.job_path(job_id)
    if path is None:
        raise ApiError("âm thanh chưa sẵn sàng hoặc đã bị xoá", status_code=425)
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=f"doc-{job_id}.wav",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/tts/sessions/{job_id}")
def session_status(job_id: str, tts: TtsDep) -> dict[str, Any]:
    status = tts.job_status(job_id)
    if status is None:
        raise ApiError("không tìm thấy phiên đọc", status_code=404)
    return ok(**status)


@router.delete("/tts/sessions/{job_id}")
def session_delete(job_id: str, tts: TtsDep) -> dict[str, Any]:
    if not tts.cancel(job_id):
        raise ApiError("không tìm thấy phiên đọc", status_code=404)
    return ok(cancelled=job_id)
