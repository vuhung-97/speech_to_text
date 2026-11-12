"""State snapshot (polled by the client) and the SSE event stream."""

from __future__ import annotations

import asyncio
import json
import queue
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .deps import BusDep, PipelineDep

HEARTBEAT_SECONDS = 15.0

router = APIRouter(tags=["state"])
events_router = APIRouter(tags=["stream"])


@router.get("/state")
def state(pipeline: PipelineDep) -> dict[str, object]:
    return pipeline.snapshot()


def _frame(event: dict[str, object]) -> bytes:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")


@events_router.get("/events")
async def events(bus: BusDep, pipeline: PipelineDep) -> StreamingResponse:
    subscriber = bus.subscribe()

    async def generator() -> AsyncIterator[bytes]:
        try:
            yield _frame(pipeline.status_event())
            yield b": connected\n\n"
            while True:
                try:
                    event = await asyncio.to_thread(subscriber.get, True, HEARTBEAT_SECONDS)
                except queue.Empty:
                    yield b": ping\n\n"
                    continue
                yield _frame(event)
        except asyncio.CancelledError:
            raise
        finally:
            bus.unsubscribe(subscriber)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
