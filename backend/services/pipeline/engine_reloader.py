"""Background ASR engine swap: one token, one thread, no partial state.

The pipeline keeps decoding with the old engine until the new one is built.
A newer reload supersedes an older one via a monotonic token; every state
change is published on the event bus so the UI can show "đang nạp…".
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from ...utils import priority
from ..event_service import EventBus


class EngineReloader:
    """Owns the current engine, its description and the reload lifecycle."""

    def __init__(self, engine: Any, factory: Callable[[dict[str, Any]], Any],
                 bus: EventBus) -> None:
        self._engine = engine
        self._factory = factory
        self._bus = bus
        self._info = self._describe(engine)
        self._state = "ready"
        self._token = 0
        self._lock = threading.Lock()

    @staticmethod
    def _describe(engine: Any) -> dict[str, Any]:
        return engine.describe() if hasattr(engine, "describe") else {}

    @property
    def engine(self) -> Any:
        return self._engine

    @property
    def state(self) -> str:
        return self._state

    @property
    def info(self) -> dict[str, Any]:
        return {**self._info, "state": self._state}

    def reload(self, values: dict[str, Any]) -> None:
        """Build a replacement engine on a background thread and swap it in."""
        with self._lock:
            self._token += 1
            token = self._token
            self._state = "loading"
        self._bus.publish({"type": "engine", "state": "loading"})

        threading.Thread(target=self._run, args=(token, values),
                         name="stt-reload", daemon=True).start()

    def _run(self, token: int, values: dict[str, Any]) -> None:
        priority.lowest_for_background()
        started = time.perf_counter()
        try:
            engine = self._factory(values)
        except Exception as exc:
            with self._lock:
                if token != self._token:
                    return  # superseded by a newer reload
                self._state = "error"
            self._bus.publish({
                "type": "engine",
                "state": "error",
                "detail": str(exc).splitlines()[0] if str(exc) else "reload failed",
            })
            return

        with self._lock:
            if token != self._token:
                return
            info = self._describe(engine)
            info["reload_seconds"] = round(time.perf_counter() - started, 2)
            self._engine = engine
            self._info = info
            self._state = "ready"
        self._bus.publish({"type": "engine", "state": "ready", **info})


__all__ = ["EngineReloader"]
