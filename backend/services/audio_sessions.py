"""One recognition session per browser connection, with hard limits.

The hub is the only place that knows how a browser session is built: it borrows
the shared engine and settings from the application pipeline, enforces the
session cap, and stops sessions off the event loop (thread joins must never
block request handling).
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import Any

from .event_service import EventBus
from .transcription_service import LivePipeline

MAX_SESSIONS = 8
STOP_TIMEOUT_SECONDS = 1.0


class SessionLimitReached(RuntimeError):
    """Every browser session slot is in use."""


class AudioSessionHub:
    def __init__(
        self,
        engine_provider: Callable[[], Any],
        settings_provider: Callable[[], Any],
        transcribe_lock: threading.Lock,
        max_sessions: int = MAX_SESSIONS,
    ) -> None:
        self._engine_provider = engine_provider
        self._settings_provider = settings_provider
        self._transcribe_lock = transcribe_lock
        self._max_sessions = max(1, int(max_sessions))
        self._sessions: set[LivePipeline] = set()
        self._lock = threading.Lock()

    @property
    def active(self) -> int:
        with self._lock:
            return len(self._sessions)

    def open(self, mic: Any) -> LivePipeline:
        engine = self._engine_provider()
        settings = self._settings_provider()
        if engine is None or settings is None:
            raise RuntimeError("engine chưa nạp xong")
        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                raise SessionLimitReached(
                    f"đã đủ {self._max_sessions} phiên nhận dạng")
            pipeline = LivePipeline(
                engine,
                EventBus(),
                settings,
                mic_factory=lambda _device: mic,
                engine_factory=lambda _values: engine,
                transcribe_lock=self._transcribe_lock,
                start_listening=False,
            )
            self._sessions.add(pipeline)
        return pipeline

    async def close(self, pipeline: LivePipeline) -> None:
        with self._lock:
            self._sessions.discard(pipeline)
        await asyncio.to_thread(pipeline.stop, STOP_TIMEOUT_SECONDS)

    def broadcast(self, event: dict[str, Any]) -> None:
        with self._lock:
            sessions = list(self._sessions)
        for pipeline in sessions:
            pipeline.bus.publish(event)


__all__ = ["AudioSessionHub", "MAX_SESSIONS", "SessionLimitReached"]
