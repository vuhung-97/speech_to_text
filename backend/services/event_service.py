"""One responsibility: fan out pipeline events to every connected subscriber.

Publishing never blocks and never raises: a slow client (or a closed tab) must
not be able to stall microphone capture.
"""

from __future__ import annotations

import queue
import threading
from typing import Any

Event = dict[str, Any]


class EventBus:
    """A tiny broadcast channel: one publisher, N subscribers, lossy on overflow."""

    def __init__(self, queue_size: int = 128) -> None:
        self._queue_size = queue_size
        self._subscribers: list[queue.Queue[Event]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[Event]:
        q: queue.Queue[Event] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[Event]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event: Event) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                try:  # drop the oldest frame so live text keeps flowing
                    q.get_nowait()
                    q.put_nowait(event)
                except (queue.Empty, queue.Full):
                    pass
