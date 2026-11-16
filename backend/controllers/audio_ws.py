"""WebSocket audio ingestion: the browser's microphone feeds the recogniser.

One connection = one session from ``AudioSessionHub`` (own segmenter and event
bus, shared engine behind one lock). Guardrails: bounded frame size, bounded
session count, same-origin check, and session shutdown off the event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config.constants import SAMPLE_RATE
from ..services.audio_sessions import SessionLimitReached
from ..services.ws_mic import WebSocketMic

router = APIRouter(tags=["audio"])

HEARTBEAT_SECONDS = 10.0
NO_AUDIO_WARNING_SECONDS = 3.0
MAX_FRAME_BYTES = 64 * 1024  # 2 s of 16 kHz PCM16
DEBUG_TEXT = os.environ.get("STT_WS_DEBUG") == "1"
logger = logging.getLogger("stt_binh.ws")


def _origin_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if not origin:
        return True  # native client / tests
    parsed = urlparse(origin)
    host = websocket.headers.get("host", "")
    return parsed.netloc == host or parsed.hostname in ("localhost", "127.0.0.1")


async def _fail(websocket: WebSocket, detail: str, code: int = 1011) -> None:
    try:
        await websocket.send_json({"type": "error", "detail": detail})
        await websocket.close(code=code, reason=detail[:120])
    except Exception:
        pass


@router.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket, sample_rate: int = SAMPLE_RATE) -> None:
    await websocket.accept()
    if not _origin_allowed(websocket):
        await _fail(websocket, "origin không được phép", 1008)
        return
    if int(sample_rate or 0) != SAMPLE_RATE:
        await _fail(websocket, f"chỉ hỗ trợ {SAMPLE_RATE} Hz", 1003)
        return

    hub = getattr(websocket.app.state, "audio_hub", None)
    if hub is None:
        await _fail(websocket, "server chưa sẵn sàng nhận audio")
        return

    mic = WebSocketMic(SAMPLE_RATE)
    try:
        pipeline = hub.open(mic)
    except SessionLimitReached as exc:
        await _fail(websocket, str(exc), 1013)
        return
    except Exception as exc:  # engine missing, settings not ready…
        await _fail(websocket, str(exc) or "không tạo được phiên nhận dạng")
        return

    subscriber = pipeline.bus.subscribe()
    pipeline.start()
    pipeline.set_paused(False)
    logger.info("ws audio open mode=%s active=%s", pipeline.mode, hub.active)
    await websocket.send_json({
        "type": "ready",
        "sample_rate": SAMPLE_RATE,
        "mode": pipeline.mode,
        "max_frame_bytes": MAX_FRAME_BYTES,
    })

    async def watch_audio() -> None:
        await asyncio.sleep(NO_AUDIO_WARNING_SECONDS)
        if mic.stats()["frames"] == 0:
            logger.warning("ws audio: no frames after %.0fs", NO_AUDIO_WARNING_SECONDS)
            try:
                await websocket.send_json({
                    "type": "warning",
                    "detail": "chưa nhận được audio từ micro — kiểm tra quyền mic / HTTPS",
                })
            except Exception:
                pass

    async def forward() -> None:
        while True:
            try:
                event = await asyncio.to_thread(subscriber.get, True, HEARTBEAT_SECONDS)
            except queue.Empty:
                continue
            if event.get("type") == "settings_changed":
                try:
                    await websocket.send_json(event)
                except Exception:
                    return
                return  # client reconnects with the new settings
            if DEBUG_TEXT and event.get("type") in ("partial", "final"):
                if event["type"] == "final":
                    logger.info("ws final %r", event.get("text", ""))
                else:
                    logger.info("ws partial %r | %r", event.get("stable", ""),
                                event.get("tentative", ""))
            try:
                await websocket.send_json(event)
            except Exception:
                return

    async def receive() -> None:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                return
            data = message.get("bytes")
            if data is not None:
                if len(data) > MAX_FRAME_BYTES:
                    logger.warning("ws audio: oversized frame %s bytes", len(data))
                    try:
                        await websocket.send_json({
                            "type": "warning",
                            "detail": "gói audio quá lớn — đã bỏ qua",
                        })
                    except Exception:
                        return
                    continue
                mic.push(data)
                continue
            text = message.get("text")
            if not text:
                continue
            try:
                payload = json.loads(text)
            except ValueError:
                continue
            if payload.get("type") == "stop":
                return

    forward_task = asyncio.create_task(forward())
    watch_task = asyncio.create_task(watch_audio())
    try:
        await receive()
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        watch_task.cancel()
        for task in (forward_task, watch_task):
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        await hub.close(pipeline)
        mic.close()
        pipeline.bus.unsubscribe(subscriber)
        stats = mic.stats()
        logger.info("ws audio close frames=%s dropped=%s coverage=%s",
                    stats["frames"], stats["dropped"], stats["coverage"])


__all__ = ["router"]
