"""Route table: one place that knows every URL the API exposes."""

from __future__ import annotations

from fastapi import APIRouter

from ..controllers import (devices, health, samples, session, settings_ctl, state)


def build_router() -> APIRouter:
    root = APIRouter()
    api = APIRouter(prefix="/api")
    api.include_router(health.router)
    api.include_router(state.router)
    api.include_router(settings_ctl.router)
    api.include_router(devices.router)
    api.include_router(samples.router)
    api.include_router(session.router)
    root.include_router(api)
    root.include_router(state.events_router)  # /events (SSE, no /api prefix)
    return root
