"""Route table: one place that knows every URL the API exposes.

``/api`` is the historical prefix; ``/api/v1`` mounts the same routers so the
Q&A client can use a versioned contract while the dictation UI keeps working.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..controllers import (audio_ws, audit, faq, health, qa, samples,
                           sessions, settings_ctl, state, tts)

_ROUTERS = (health, state, settings_ctl, samples, tts, qa, sessions, faq, audit)


def _api_prefix(prefix: str) -> APIRouter:
    api = APIRouter(prefix=prefix)
    for module in _ROUTERS:
        api.include_router(module.router)
    return api


def build_router() -> APIRouter:
    root = APIRouter()
    root.include_router(_api_prefix("/api"))
    root.include_router(_api_prefix("/api/v1"))
    root.include_router(state.events_router)  # /events (SSE, no /api prefix)
    root.include_router(audio_ws.router)      # /ws/audio (no /api prefix)
    return root


__all__ = ["build_router"]
