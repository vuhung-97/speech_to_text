"""FastAPI dependencies: expose the services created in the app lifespan."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from ..config.settings import Settings
from ..services.event_service import EventBus
from ..services.replay_service import ReplayService
from ..services.transcription_service import LivePipeline


def get_pipeline(request: Request) -> LivePipeline:
    return request.app.state.pipeline


def get_settings_store(request: Request) -> Settings:
    return request.app.state.settings


def get_replay(request: Request) -> ReplayService:
    return request.app.state.replay


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus


PipelineDep = Annotated[LivePipeline, Depends(get_pipeline)]
SettingsDep = Annotated[Settings, Depends(get_settings_store)]
ReplayDep = Annotated[ReplayService, Depends(get_replay)]
BusDep = Annotated[EventBus, Depends(get_bus)]
