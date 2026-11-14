"""A microphone whose audio arrives over a WebSocket.

The browser owns the device; the server only sees 16 kHz mono PCM16. Frames are
re-assembled into the 100 ms blocks the segmenter expects, with a bounded queue
so a slow model drops audio instead of growing memory.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any

import numpy as np

from ..config.constants import BLOCK, SAMPLE_RATE

MAX_FRAMES = 100  # 10 s of 100 ms blocks


class WebSocketMic:
    """Drop-in replacement for ``MicStream`` used by one WebSocket session."""

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        rate = int(sample_rate or SAMPLE_RATE)
        if rate != SAMPLE_RATE:
            raise ValueError(f"chỉ hỗ trợ {SAMPLE_RATE} Hz, nhận {rate} Hz")
        self.sample_rate = SAMPLE_RATE
        self._frames: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=MAX_FRAMES)
        self._pending = np.zeros(0, dtype=np.float32)
        self._lock = threading.Lock()
        self._closed = threading.Event()
        self._started = time.perf_counter()
        self._received = 0
        self._dropped = 0
        self._frames_done = 0

    # ------------------------------------------------------------- lifecycle
    def __enter__(self) -> "WebSocketMic":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._closed.set()
        try:
            self._frames.put_nowait(None)
        except queue.Full:
            pass

    # ------------------------------------------------------------------ input
    def push(self, data: bytes) -> int:
        """Append PCM16LE bytes; returns how many blocks were dropped."""
        if not data or self._closed.is_set():
            return 0
        usable = len(data) - (len(data) % 2)
        if usable <= 0:
            return 0
        pcm = np.frombuffer(data[:usable], dtype="<i2").astype(np.float32) / 32768.0
        dropped = 0
        with self._lock:
            self._received += pcm.size
            self._pending = (
                np.concatenate([self._pending, pcm]) if self._pending.size else pcm)
            while self._pending.size >= BLOCK:
                frame = self._pending[:BLOCK]
                self._pending = self._pending[BLOCK:]
                try:
                    self._frames.put_nowait(frame)
                    self._frames_done += 1
                except queue.Full:
                    try:
                        self._frames.get_nowait()
                    except queue.Empty:
                        pass
                    self._frames.put_nowait(frame)
                    self._frames_done += 1
                    self._dropped += 1
                    dropped += 1
        return dropped

    # ----------------------------------------------------------------- output
    def read(self, timeout: float = 0.2) -> np.ndarray | None:
        try:
            frame = self._frames.get(timeout=timeout)
        except queue.Empty:
            return None
        return frame

    def stats(self) -> dict[str, Any]:
        elapsed = max(time.perf_counter() - self._started, 1e-6)
        with self._lock:
            received = self._received
            dropped = self._dropped
            frames = self._frames_done
        return {
            "backend": "websocket",
            "device": "browser",
            "rate": self.sample_rate,
            "frames": frames,
            "frames_per_sec": round(frames / elapsed, 1),
            "coverage": round(received / (elapsed * self.sample_rate), 3),
            "dropped": dropped,
            "xruns": 0,
        }


__all__ = ["MAX_FRAMES", "WebSocketMic"]
