"""Audio input device catalog."""

from __future__ import annotations

from fastapi import APIRouter

from ..services.device_service import list_input_devices

router = APIRouter(tags=["devices"])


@router.get("/devices")
def devices() -> dict[str, object]:
    return {"devices": list_input_devices()}
