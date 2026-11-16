"""Settings endpoints: schema + values, partial update, reset."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

from .deps import AudioHubDep, PipelineDep, SettingsDep

router = APIRouter(prefix="/settings", tags=["settings"])


def _payload(settings: SettingsDep, pipeline: PipelineDep) -> dict[str, Any]:
    return {
        "values": settings.values(),
        "fields": settings.schema(),
        "warnings": settings.warnings(),
        "engine": pipeline.engine_info(),
        "capture": pipeline.capture_stats().to_dict(),
        "engines": [spec.to_dict() for spec in settings.engine_specs().values()],
    }


@router.get("")
def read_settings(settings: SettingsDep, pipeline: PipelineDep) -> dict[str, Any]:
    return _payload(settings, pipeline)


@router.post("")
def update_settings(settings: SettingsDep, pipeline: PipelineDep,
                    hub: AudioHubDep,
                    patch: dict[str, Any] = Body(...)) -> dict[str, Any]:
    result = pipeline.apply(patch)
    result["fields"] = settings.schema()  # the model switching may change the schema
    result["engines"] = [spec.to_dict() for spec in settings.engine_specs().values()]
    hub.broadcast({"type": "settings_changed"})
    return result


@router.post("/reset")
def reset_settings(settings: SettingsDep, pipeline: PipelineDep,
                   hub: AudioHubDep) -> dict[str, Any]:
    result = pipeline.reset_settings()
    result["fields"] = settings.schema()
    result["engines"] = [spec.to_dict() for spec in settings.engine_specs().values()]
    hub.broadcast({"type": "settings_changed"})
    return result
