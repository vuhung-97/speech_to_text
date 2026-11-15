"""WebSocket audio ingestion: the browser's microphone feeds the recogniser.

One connection = one independent recognition session (own segmenter, own event
bus) while all sessions share the single ONNX engine behind one lock.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config.constants import SAMPLE_RATE
from ..services.ws_mic import WebSocketMic

router = APIRouter(tags=["audio"])

HEARTBEAT_SECONDS = 10.0
NO_AUDIO_WARNING_SECONDS = 3.0
DEBUG_TEXT = os.environ.get("STT_WS_DEBUG") == "1"
logger = logging.getLogger("stt_binh.ws")


async def _fail(websocket: WebSocket, detail: str, code: int = 1011) -> None:
    try:
        await websocket.send_json({"type": "error", "detail": detail})
        await websocket.close(code=code)
    except Exception:
        pass


@router.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket, sample_rate: int = SAMPLE_RATE) -> None:
    await websocket.accept()
    if int(sample_rate or 0) != SAMPLE_RATE:
        await _fail(websocket, f"chỉ hỗ trợ {SAMPLE_RATE} Hz", 1003)
        return

    factory = getattr(websocket.app.state, "make_audio_session", None)
    if not callable(factory):
        await _fail(websocket, "server chưa sẵn sàng nhận audio")
        return

    mic = WebSocketMic(SAMPLE_RATE)
    try:
        pipeline = factory(mic)
    except Exception as exc:  # engine missing, settings not ready…
        await _fail(websocket, str(exc) or "không tạo được phiên nhận dạng")
        return

    subscriber = pipeline.bus.subscribe()
    pipeline.start()
    pipeline.set_paused(False)
    logger.info("ws audio open mode=%s", pipeline.mode)
    await websocket.send_json({
        "type": "ready",
        "sample_rate": SAMPLE_RATE,
        "mode": pipeline.mode,
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
            if data:
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
        try:
            await forward_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await watch_task
        except (asyncio.CancelledError, Exception):
            pass
        pipeline.stop()
        mic.close()
        pipeline.bus.unsubscribe(subscriber)
        stats = mic.stats()
        logger.info("ws audio close frames=%s dropped=%s coverage=%s",
                    stats["frames"], stats["dropped"], stats["coverage"])


__all__ = ["router"]
