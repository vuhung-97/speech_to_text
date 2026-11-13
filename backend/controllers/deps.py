"""FastAPI dependencies: expose the services created in the app lifespan."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, Header, Request

from ..config.settings import Settings
from ..services.event_service import EventBus
from ..services.replay_service import ReplayService
from ..services.transcription_service import LivePipeline
from ..services.tts_service import TtsService
from ..utils.errors import ApiError

DEFAULT_TENANT = "local"
_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def get_pipeline(request: Request) -> LivePipeline:
    return request.app.state.pipeline


def get_settings_store(request: Request) -> Settings:
    return request.app.state.settings


def get_replay(request: Request) -> ReplayService:
    return request.app.state.replay


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus


def get_tts(request: Request) -> TtsService:
    return request.app.state.tts


def current_tenant(
    x_workspace: str | None = Header(default=None, alias="X-Workspace"),
) -> str:
    """Resolve the tenant from the request, defaulting to the local workspace.

    The header is a UX hint, never an authorisation claim: once real accounts
    exist this dependency must resolve the tenant from the authenticated
    identity and ignore the header value.
    """
    value = (x_workspace or DEFAULT_TENANT).strip().lower()
    if not _TENANT_RE.match(value):
        raise ApiError("workspace không hợp lệ", status_code=400)
    return value


PipelineDep = Annotated[LivePipeline, Depends(get_pipeline)]
SettingsDep = Annotated[Settings, Depends(get_settings_store)]
ReplayDep = Annotated[ReplayService, Depends(get_replay)]
BusDep = Annotated[EventBus, Depends(get_bus)]
TtsDep = Annotated[TtsService, Depends(get_tts)]
TenantDep = Annotated[str, Depends(current_tenant)]
