"""HTTP health probe."""

from __future__ import annotations

from fastapi import APIRouter

from .deps import PipelineDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(pipeline: PipelineDep) -> dict[str, object]:
    return {"ok": True, "engine": pipeline.engine_info()}
